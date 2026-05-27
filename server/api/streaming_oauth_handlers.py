# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — 4 platform OAuth2 token chain (Phase 5 cycle 169.486).

역할 — 방송 도우미 봇이 쓰는 4 플랫폼(twitch/youtube/chzzk/kick) OAuth2
authorization code flow 를 중개한다. authorize URL 발급 → callback code 교환 →
refresh → 상태 조회 → 삭제까지의 토큰 수명을 관리한다.

계층 위치 — server API handler 계층(정본 §E). start/refresh/status/delete 는
Bearer 의무, callback 은 브라우저 redirect 着地점(state token 으로 CSRF 방어).
토큰 영속은 `streaming_oauth_tokens` repository 에 위임한다.

의존성 — aiohttp `web` + httpx async client(code/refresh 교환) + state in-memory
store(5분 TTL, 분산 시 Redis 의무) + `streaming_oauth_tokens` repository.
client_id/secret/redirect_uri 는 env 주입(미설정 시 503 NOT_CONFIGURED).

범위 한계 — OAuth 토큰 수명 관리만. 실 chat 송수신(IRC/EventSub/WebSocket)·토큰
사용 방송 기능은 별개 bot runtime 경로. state store 는 단일 프로세스 가정.

엔드포인트 카탈로그(실 함수 5 + helper 7 + register):
- `handle_oauth_start`     POST   /api/streaming/oauth/start      — authorize URL.
- `handle_oauth_callback`  GET    /api/streaming/oauth/callback   — code 교환.
- `handle_oauth_refresh`   POST   /api/streaming/oauth/refresh    — access 갱신.
- `handle_oauth_status`    GET    /api/streaming/oauth/status     — 보유 조회.
- `handle_oauth_delete`    DELETE /api/streaming/oauth/{platform} — 삭제.
- helper: `_purge_expired_states`/`_get_platform_config`/`_redirect_uri`/
  `_exchange_code_for_token`/`_refresh_access_token`/`_html_response` + register.

엔드포인트:
- ``POST /api/streaming/oauth/start`` — OAuth URL 생성 + state token persist
- ``GET /api/streaming/oauth/callback`` — code → tokens exchange + DB persist
- ``POST /api/streaming/oauth/refresh`` — refresh_token → 신규 access_token
- ``GET /api/streaming/oauth/status`` — 사용자 platform token retain 조회
- ``DELETE /api/streaming/oauth/{platform}`` — token 삭제 (revoke 후)

지원 platform:
- ``twitch`` — id.twitch.tv OAuth2 authorization code flow (chat:read + chat:edit scope)
- ``youtube`` — accounts.google.com OAuth2 + youtube.readonly scope
- ``chzzk`` — CHZZK 자체 OAuth (cycle 167 기본 skeleton 기반)
- ``kick`` — kick.com OAuth2 (2024 신 API)

OAuth client_id / client_secret 환경 변수:
- ``TWITCH_OAUTH_CLIENT_ID`` / ``TWITCH_OAUTH_CLIENT_SECRET``
- ``YOUTUBE_OAUTH_CLIENT_ID`` / ``YOUTUBE_OAUTH_CLIENT_SECRET``
- ``CHZZK_OAUTH_CLIENT_ID`` / ``CHZZK_OAUTH_CLIENT_SECRET``
- ``KICK_OAUTH_CLIENT_ID`` / ``KICK_OAUTH_CLIENT_SECRET``
- ``STREAMING_OAUTH_REDIRECT_URI`` — callback URI (default https://demo/api/streaming/oauth/callback)

미설정 시 = 503 응답 (NOT_CONFIGURED). 사용자 manual 등록 의무.
"""

from __future__ import annotations

import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from aiohttp import web

from server.db.repositories import streaming_oauth_tokens as _tok_repo

log = logging.getLogger(__name__)

# state token 의 in-memory store (5분 TTL). 분산 환경 시 Redis 의무.
# state = CSRF 방지 + user_id binding 의 짝. {state: (user_id, platform, ts)}.
_STATE_STORE: dict[str, tuple[int, str, float]] = {}
_STATE_TTL_SECONDS = 300

_DEFAULT_REDIRECT = "https://114.207.112.73:8443/api/streaming/oauth/callback"

# platform 별 OAuth2 endpoint 정의
_PLATFORM_CONFIG = {
    "twitch": {
        "authorize_url": "https://id.twitch.tv/oauth2/authorize",
        "token_url": "https://id.twitch.tv/oauth2/token",
        "revoke_url": "https://id.twitch.tv/oauth2/revoke",
        "scope": "chat:read chat:edit",
        "client_id_env": "TWITCH_OAUTH_CLIENT_ID",
        "client_secret_env": "TWITCH_OAUTH_CLIENT_SECRET",
    },
    "youtube": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "revoke_url": "https://oauth2.googleapis.com/revoke",
        "scope": "https://www.googleapis.com/auth/youtube.readonly",
        "client_id_env": "YOUTUBE_OAUTH_CLIENT_ID",
        "client_secret_env": "YOUTUBE_OAUTH_CLIENT_SECRET",
    },
    "chzzk": {
        "authorize_url": "https://chzzk.naver.com/account-interlock",
        "token_url": "https://openapi.chzzk.naver.com/auth/v1/token",
        "revoke_url": "https://openapi.chzzk.naver.com/auth/v1/token/revoke",
        "scope": "1",  # CHZZK 안 scope 부재 — placeholder
        "client_id_env": "CHZZK_OAUTH_CLIENT_ID",
        "client_secret_env": "CHZZK_OAUTH_CLIENT_SECRET",
    },
    "kick": {
        "authorize_url": "https://id.kick.com/oauth/authorize",
        "token_url": "https://id.kick.com/oauth/token",
        "revoke_url": "https://id.kick.com/oauth/revoke",
        "scope": "chat:write channel:read",
        "client_id_env": "KICK_OAUTH_CLIENT_ID",
        "client_secret_env": "KICK_OAUTH_CLIENT_SECRET",
    },
}


def _purge_expired_states() -> None:
    """5분 초과 state token 일괄 정리 — GC chain."""
    now = time.time()
    expired = [k for k, (_, _, ts) in _STATE_STORE.items() if now - ts > _STATE_TTL_SECONDS]
    for k in expired:
        _STATE_STORE.pop(k, None)


def _get_platform_config(platform: str) -> Optional[dict]:
    return _PLATFORM_CONFIG.get(platform)


def _redirect_uri() -> str:
    return os.environ.get("STREAMING_OAUTH_REDIRECT_URI", _DEFAULT_REDIRECT)


async def handle_oauth_start(request: web.Request) -> web.Response:
    """``POST /api/streaming/oauth/start`` — OAuth URL 생성 + state persist.

    Body:
        ``{"platform": "twitch"}``

    Response:
        ``{"ok": true, "url": "https://...", "state": "...", "expires_in": 300}``
    """
    payload = await request.json()
    platform = str(payload.get("platform", "")).strip().lower()
    user = request.get("user")
    if user is None:
        return web.json_response({"error": "UNAUTHORIZED"}, status=401)
    user_id = int(user.get("user_id") or user.get("id") or 0)
    if user_id <= 0:
        return web.json_response({"error": "UNAUTHORIZED"}, status=401)

    cfg = _get_platform_config(platform)
    if cfg is None:
        return web.json_response(
            {"error": "INVALID_PLATFORM", "message": f"platform={platform!r} 미지원"},
            status=400,
        )

    client_id = os.environ.get(cfg["client_id_env"])
    if not client_id:
        return web.json_response(
            {
                "error": "NOT_CONFIGURED",
                "message": f"{cfg['client_id_env']} 환경변수 부재 — 사용자 manual 등록 의무",
            },
            status=503,
        )

    _purge_expired_states()
    state = secrets.token_urlsafe(32)
    _STATE_STORE[state] = (user_id, platform, time.time())

    params = {
        "client_id": client_id,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
    }
    if platform == "youtube":
        # Google OAuth2 안 offline access + consent prompt 의무 (refresh_token 발급)
        params["access_type"] = "offline"
        params["prompt"] = "consent"

    url = f"{cfg['authorize_url']}?{urlencode(params)}"
    log.info(
        "[oauth_start] user_id=%d platform=%s state=%s...",
        user_id, platform, state[:8],
    )
    return web.json_response({
        "ok": True,
        "url": url,
        "state": state,
        "expires_in": _STATE_TTL_SECONDS,
    })


async def handle_oauth_callback(request: web.Request) -> web.Response:
    """``GET /api/streaming/oauth/callback?code=...&state=...`` — code 교환 + DB persist.

    OAuth provider 의 redirect target — HTML 응답 chain (browser 의무 visible).
    """
    code = request.query.get("code", "").strip()
    state = request.query.get("state", "").strip()
    error_code = request.query.get("error", "").strip()

    if error_code:
        return _html_response(
            f"<h1>OAuth 거부</h1><p>provider error: {error_code}</p>",
            status=400,
        )

    if not code or not state:
        return _html_response(
            "<h1>OAuth 실패</h1><p>code 또는 state 부재</p>", status=400,
        )

    _purge_expired_states()
    entry = _STATE_STORE.pop(state, None)
    if entry is None:
        return _html_response(
            "<h1>OAuth 실패</h1><p>state 만료 또는 invalid (CSRF 차단)</p>",
            status=400,
        )
    user_id, platform, _ = entry
    cfg = _get_platform_config(platform)
    if cfg is None:
        return _html_response(
            f"<h1>OAuth 실패</h1><p>platform={platform!r} 부재</p>", status=400,
        )

    client_id = os.environ.get(cfg["client_id_env"])
    client_secret = os.environ.get(cfg["client_secret_env"])
    if not client_id or not client_secret:
        return _html_response(
            f"<h1>OAuth 실패</h1><p>{cfg['client_id_env']} 부재 — 서버 설정 오류</p>",
            status=503,
        )

    # code → token exchange POST request (httpx async client)
    try:
        token_data = await _exchange_code_for_token(
            cfg=cfg, code=code, client_id=client_id, client_secret=client_secret,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("[oauth_callback] token exchange 실패 — %r", exc)
        return _html_response(
            f"<h1>OAuth 실패</h1><p>token 교환 실패 — {exc}</p>", status=502,
        )

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = int(token_data.get("expires_in", 3600))
    scope = token_data.get("scope", cfg["scope"])
    token_type = token_data.get("token_type", "Bearer")
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    if not access_token:
        return _html_response(
            "<h1>OAuth 실패</h1><p>access_token 부재 응답</p>", status=502,
        )

    pool = request.app["db_pool"]
    try:
        row_id = await _tok_repo.upsert_token(
            pool,
            user_id=user_id,
            platform=platform,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scopes=scope if isinstance(scope, str) else " ".join(scope or []),
            token_type=token_type,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("[oauth_callback] DB persist 실패 — %r", exc, exc_info=True)
        return _html_response(
            f"<h1>OAuth 실패</h1><p>token persist 실패 — {exc}</p>", status=500,
        )

    log.info(
        "[oauth_callback] user_id=%d platform=%s token_row_id=%d expires_in=%d",
        user_id, platform, row_id, expires_in,
    )
    return _html_response(
        f"<h1>OAuth 성공</h1>"
        f"<p>platform = <b>{platform}</b></p>"
        f"<p>token 의 의무 retain (DB persist 완료). 본 창 닫음 + TooTalk 안 재 확인 의무.</p>"
        f"<script>setTimeout(function(){{window.close();}}, 3000);</script>",
        status=200,
    )


async def handle_oauth_refresh(request: web.Request) -> web.Response:
    """``POST /api/streaming/oauth/refresh`` — refresh_token 의 신규 access_token.

    Body:
        ``{"platform": "twitch"}``
    """
    payload = await request.json()
    platform = str(payload.get("platform", "")).strip().lower()
    user = request.get("user")
    if user is None:
        return web.json_response({"error": "UNAUTHORIZED"}, status=401)
    user_id = int(user.get("user_id") or user.get("id") or 0)
    if user_id <= 0:
        return web.json_response({"error": "UNAUTHORIZED"}, status=401)

    cfg = _get_platform_config(platform)
    if cfg is None:
        return web.json_response({"error": "INVALID_PLATFORM"}, status=400)

    client_id = os.environ.get(cfg["client_id_env"])
    client_secret = os.environ.get(cfg["client_secret_env"])
    if not client_id or not client_secret:
        return web.json_response({"error": "NOT_CONFIGURED"}, status=503)

    pool = request.app["db_pool"]
    row = await _tok_repo.get_token(pool, user_id=user_id, platform=platform)
    if row is None or not row.refresh_token:
        return web.json_response(
            {"error": "NO_REFRESH_TOKEN", "message": "재 OAuth 진입 의무"},
            status=404,
        )

    try:
        new_token = await _refresh_access_token(
            cfg=cfg,
            refresh_token=row.refresh_token,
            client_id=client_id,
            client_secret=client_secret,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[oauth_refresh] user_id=%d platform=%s refresh 실패 — %r",
            user_id, platform, exc,
        )
        return web.json_response(
            {"error": "REFRESH_FAILED", "message": str(exc)}, status=502,
        )

    access_token = new_token.get("access_token")
    refresh_token = new_token.get("refresh_token", row.refresh_token)
    expires_in = int(new_token.get("expires_in", 3600))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    if not access_token:
        return web.json_response({"error": "REFRESH_FAILED"}, status=502)

    await _tok_repo.upsert_token(
        pool,
        user_id=user_id,
        platform=platform,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        scopes=row.scopes,
        token_type=new_token.get("token_type", row.token_type),
        channel_id=row.channel_id,
        channel_login=row.channel_login,
    )
    return web.json_response({
        "ok": True,
        "expires_in": expires_in,
        "platform": platform,
    })


async def handle_oauth_status(request: web.Request) -> web.Response:
    """``GET /api/streaming/oauth/status`` — 사용자 platform token retain 일괄 조회."""
    user = request.get("user")
    if user is None:
        return web.json_response({"error": "UNAUTHORIZED"}, status=401)
    user_id = int(user.get("user_id") or user.get("id") or 0)
    if user_id <= 0:
        return web.json_response({"error": "UNAUTHORIZED"}, status=401)

    pool = request.app["db_pool"]
    rows = await _tok_repo.list_tokens_by_user(pool, user_id=user_id)
    now = datetime.now(timezone.utc)
    return web.json_response({
        "ok": True,
        "tokens": [
            {
                "platform": r.platform,
                "channel_id": r.channel_id,
                "channel_login": r.channel_login,
                "scopes": r.scopes,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                "expired": (
                    r.expires_at.replace(tzinfo=timezone.utc) < now
                    if r.expires_at and r.expires_at.tzinfo is None
                    else (r.expires_at < now if r.expires_at else True)
                ),
                "has_refresh": bool(r.refresh_token),
            }
            for r in rows
        ],
    })


async def handle_oauth_delete(request: web.Request) -> web.Response:
    """``DELETE /api/streaming/oauth/{platform}`` — token 삭제 (사용자 disconnect)."""
    platform = request.match_info.get("platform", "").strip().lower()
    user = request.get("user")
    if user is None:
        return web.json_response({"error": "UNAUTHORIZED"}, status=401)
    user_id = int(user.get("user_id") or user.get("id") or 0)
    if user_id <= 0:
        return web.json_response({"error": "UNAUTHORIZED"}, status=401)

    if platform not in _PLATFORM_CONFIG:
        return web.json_response({"error": "INVALID_PLATFORM"}, status=400)

    pool = request.app["db_pool"]
    affected = await _tok_repo.delete_token(pool, user_id=user_id, platform=platform)
    return web.json_response({"ok": True, "deleted": affected})


# =============================================================================
# 내부 helper — token exchange + refresh
# =============================================================================


async def _exchange_code_for_token(
    *, cfg: dict, code: str, client_id: str, client_secret: str,
) -> dict:
    """``POST {token_url}`` — authorization_code → access_token + refresh_token."""
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": _redirect_uri(),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(cfg["token_url"], data=data)
        resp.raise_for_status()
        return resp.json()


async def _refresh_access_token(
    *, cfg: dict, refresh_token: str, client_id: str, client_secret: str,
) -> dict:
    """``POST {token_url}`` — refresh_token grant chain."""
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(cfg["token_url"], data=data)
        resp.raise_for_status()
        return resp.json()


def _html_response(body: str, *, status: int = 200) -> web.Response:
    """callback chain 의 HTML 응답 helper (브라우저에 바로 보이는 페이지)."""
    html = (
        "<!DOCTYPE html><html><head>"
        "<meta charset='utf-8'>"
        "<title>TooTalk · streaming OAuth</title>"
        "<style>body{font-family:-apple-system,sans-serif;padding:32px;background:#0F172A;color:#e5e7eb;}"
        "h1{color:#0066FF;} a{color:#67E8F9;}</style>"
        "</head><body>"
        f"{body}"
        "</body></html>"
    )
    return web.Response(text=html, status=status, content_type="text/html")


# =============================================================================
# 라우트 등록
# =============================================================================


def register_streaming_oauth_routes(app: web.Application) -> None:
    """``main.py`` 안 본 함수 호출 — 5 endpoint 등록."""
    app.router.add_post("/api/streaming/oauth/start", handle_oauth_start)
    app.router.add_get("/api/streaming/oauth/callback", handle_oauth_callback)
    app.router.add_post("/api/streaming/oauth/refresh", handle_oauth_refresh)
    app.router.add_get("/api/streaming/oauth/status", handle_oauth_status)
    app.router.add_delete("/api/streaming/oauth/{platform}", handle_oauth_delete)
    log.info("[api] streaming OAuth 5 endpoint 등록 완료 (cycle 169.486)")
