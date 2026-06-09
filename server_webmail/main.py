# SPDX-License-Identifier: GPL-3.0-or-later
"""webmail.dopa.co.kr aiohttp backend — cycle 169.861 M4 IMAP 결선.

cycle 169.861 (M4) — IMAP imaplib LOGIN + aiohttp_session 안 자격 보관 +
INBOX list / 메일 read 종단 결선.

cycle 169.859 (M3) skeleton 위에서 결선 — /login POST 가 IMAP4_SSL LOGIN 실행 +
세션 안 자격 (encrypted cookie) 보관 + /inbox + /mail/<uid> 결선.

Exec Plan: docs/exec-plans/active/2026-06-09-webmail-python-backend.md M4
"""

from __future__ import annotations

import asyncio
import base64
import html
import logging
import os
import secrets

from aiohttp import web
from aiohttp_session import get_session, setup as session_setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from cryptography import fernet

from server_webmail import imap_service

# 한글 주석: KST timezone + JSON 로그 = server/ 정합 의무 (cycle 169.857 Dovecot 정합)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("webmail")

# 한글 주석: nginx upstream `webmail:8090` 정합 — 8090 listen
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = int(os.environ.get("WEBMAIL_PORT", "8090"))

# 한글 주석: IMAP 서버 (cycle 169.857 Dovecot 정합 — mail.dopa.co.kr:993 SSL/TLS)
IMAP_HOST = os.environ.get("WEBMAIL_IMAP_HOST", "mail.dopa.co.kr")
IMAP_PORT = int(os.environ.get("WEBMAIL_IMAP_PORT", "993"))


def _resolve_session_key() -> bytes:
    """aiohttp_session EncryptedCookieStorage 의 raw 32 byte key 결정.

    한글 주석: EncryptedCookieStorage = raw 32 byte secret 의무 (내부 urlsafe_b64encode 적용).
    production = WEBMAIL_SESSION_KEY env (urlsafe base64 44 char 또는 raw 32 byte hex).
    개발 = secrets.token_bytes(32) ephemeral (재기동 시 모든 세션 무효).
    """

    env_key = os.environ.get("WEBMAIL_SESSION_KEY", "").strip()
    if env_key:
        try:
            # 한글 주석: env key = urlsafe base64 encoded (Fernet 호환) 또는 hex 32 byte
            if len(env_key) == 44:
                # urlsafe base64 → decode → 32 raw bytes
                return base64.urlsafe_b64decode(env_key)
            if len(env_key) == 64:
                # hex 32 byte
                return bytes.fromhex(env_key)
            log.warning("WEBMAIL_SESSION_KEY 길이 오류 — ephemeral key 사용")
        except Exception:
            log.warning("WEBMAIL_SESSION_KEY 형식 오류 — ephemeral key 사용")
    # 한글 주석: 개발 fallback — 매 startup ephemeral 32 byte (재기동 시 logout)
    log.warning(
        "WEBMAIL_SESSION_KEY env 부재 — ephemeral key 사용 (production 의무 설정)"
    )
    return secrets.token_bytes(32)


# ----------------------------------------------------------------------
# HTML render helpers (Jinja2 부재 — inline string render, M5 후속 cycle)
# ----------------------------------------------------------------------


_BASE_STYLE = """
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo",
    "Malgun Gothic", sans-serif;
  background: #f3f4f6;
  margin: 0;
  color: #1f2937;
}
.shell { max-width: 960px; margin: 0 auto; padding: 24px 16px; }
header {
  display: flex; justify-content: space-between; align-items: center;
  background: #ffffff; padding: 12px 16px; border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05); margin-bottom: 16px;
}
header h1 { font-size: 16px; margin: 0; color: #2563eb; }
header .user { font-size: 13px; color: #4b5563; }
header form { display: inline; }
header button {
  background: transparent; border: 1px solid #d1d5db; padding: 4px 10px;
  border-radius: 6px; font-size: 12px; color: #4b5563; cursor: pointer;
}
.card { background: #ffffff; border-radius: 8px; padding: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.list { list-style: none; padding: 0; margin: 0; }
.list li {
  padding: 12px 8px; border-bottom: 1px solid #e5e7eb;
  display: flex; gap: 12px; align-items: center;
}
.list li:last-child { border-bottom: 0; }
.list a {
  display: flex; flex: 1; gap: 12px; align-items: center;
  color: #1f2937; text-decoration: none; min-width: 0;
}
.list .from { flex: 0 0 200px; font-weight: 600; font-size: 13px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.list .subj { flex: 1; font-size: 13px; color: #4b5563;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.list .uid { flex: 0 0 60px; font-size: 11px; color: #9ca3af;
  text-align: right; }
pre.body { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-break: break-word;
  background: #f9fafb; padding: 12px; border-radius: 6px; }
.meta { font-size: 12px; color: #6b7280; margin: 0 0 12px; }
.meta strong { color: #374151; }
a.back { font-size: 13px; color: #2563eb; text-decoration: none; }
.empty { color: #9ca3af; font-size: 13px; padding: 20px 0; text-align: center; }
.notice { font-size: 12px; color: #b91c1c; padding: 8px 0; }
"""


def _render_shell(user_label: str, body_html: str) -> str:
    """Header + shell 공통 wrapper."""

    safe_user = html.escape(user_label) if user_label else "guest"
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TooTalk 웹메일 — dopa.co.kr</title>
  <style>{_BASE_STYLE}</style>
</head>
<body>
  <div class="shell">
    <header>
      <h1><a href="/inbox" style="color:#2563eb;text-decoration:none">TooTalk 웹메일</a></h1>
      <div>
        <span class="user">{safe_user}</span>
        <form method="POST" action="/logout" style="display:inline">
          <button type="submit">로그아웃</button>
        </form>
      </div>
    </header>
    {body_html}
  </div>
</body>
</html>"""


def _render_login(error: str = "") -> str:
    """로그인 폼 — 단독 (header 부재)."""

    err_html = f'<p class="notice">{html.escape(error)}</p>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TooTalk 웹메일 — 로그인</title>
  <style>
    {_BASE_STYLE}
    .login-card {{
      background: #ffffff; max-width: 360px; margin: 80px auto;
      padding: 32px; border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }}
    .login-card h1 {{ font-size: 22px; margin: 0 0 8px; color: #1f2937; }}
    .login-card p {{ font-size: 14px; color: #4b5563; margin: 0 0 24px; }}
    label {{ display: block; font-size: 13px; color: #374151; margin-bottom: 6px; }}
    input {{
      width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 8px;
      font-size: 14px; box-sizing: border-box; margin-bottom: 16px;
    }}
    button[type=submit] {{
      width: 100%; padding: 12px; background: #2563eb; color: #ffffff; border: 0;
      border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer;
    }}
  </style>
</head>
<body>
  <form class="login-card" method="POST" action="/login">
    <h1>TooTalk 웹메일</h1>
    <p>dopa.co.kr 계정으로 로그인</p>
    {err_html}
    <label for="user">사용자명</label>
    <input id="user" name="user" type="text" placeholder="예: verify"
      autocomplete="username" required>
    <label for="password">패스워드</label>
    <input id="password" name="password" type="password"
      autocomplete="current-password" required>
    <button type="submit">로그인</button>
  </form>
</body>
</html>"""


def _render_inbox(user_label: str, summaries: list[imap_service.MailSummary]) -> str:
    """INBOX list HTML."""

    if not summaries:
        rows = '<div class="empty">받은편지함이 비어 있습니다.</div>'
    else:
        rows_html: list[str] = []
        for s in summaries:
            from_s = html.escape(s.from_addr or "(unknown sender)")
            subj_s = html.escape(s.subject or "(no subject)")
            rows_html.append(
                f'<li><a href="/mail/{s.uid}">'
                f'<span class="from">{from_s}</span>'
                f'<span class="subj">{subj_s}</span>'
                f'<span class="uid">#{s.uid}</span>'
                f'</a></li>'
            )
        rows = '<ul class="list">' + "".join(rows_html) + "</ul>"
    body = f'<div class="card"><h2 style="margin:0 0 8px;font-size:15px">INBOX</h2>{rows}</div>'
    return _render_shell(user_label, body)


def _render_mail(user_label: str, body: imap_service.MailBody) -> str:
    """단일 메일 본문 view."""

    meta = (
        f'<p class="meta">'
        f'<strong>보낸이</strong> {html.escape(body.from_addr)} &middot; '
        f'<strong>받는이</strong> {html.escape(body.to_addr)} &middot; '
        f'<strong>날짜</strong> {html.escape(body.date)}'
        f'</p>'
    )
    inner = (
        f'<a class="back" href="/inbox">← 받은편지함</a>'
        f'<h2 style="margin:12px 0 4px;font-size:16px">{html.escape(body.subject)}</h2>'
        f'{meta}'
        f'<pre class="body">{html.escape(body.body_text)}</pre>'
    )
    return _render_shell(user_label, f'<div class="card">{inner}</div>')


# ----------------------------------------------------------------------
# session helpers
# ----------------------------------------------------------------------


def _store_credentials(session, user: str, password: str) -> None:
    """세션 안 IMAP 자격 저장 — encrypted cookie 정합.

    한글 주석: 패스워드 = base64 encoded (Fernet 가 encrypted cookie 안 다시 암호화).
    aiohttp_session EncryptedCookieStorage = HMAC + Fernet 정합.
    """

    session["user"] = user
    session["password_b64"] = base64.b64encode(password.encode("utf-8")).decode("ascii")


def _read_credentials(session) -> tuple[str, str] | None:
    """세션 안 IMAP 자격 복원 — 부재 시 None."""

    user = session.get("user")
    pw_b64 = session.get("password_b64")
    if not user or not pw_b64:
        return None
    try:
        password = base64.b64decode(pw_b64.encode("ascii")).decode("utf-8")
    except Exception:
        return None
    return user, password


# ----------------------------------------------------------------------
# route handlers
# ----------------------------------------------------------------------


async def handle_healthz(request: web.Request) -> web.Response:
    """nginx /healthz 정합 — docker compose healthcheck + 외부 모니터링."""

    return web.json_response(
        {"status": "ok", "cycle": "169.861", "stage": "M4-imap-integrated"}
    )


async def handle_index(request: web.Request) -> web.StreamResponse:
    """루트 = 세션 보유 시 /inbox redirect, 부재 시 /login redirect."""

    session = await get_session(request)
    if _read_credentials(session) is not None:
        return web.HTTPFound("/inbox")
    return web.HTTPFound("/login")


async def handle_login_get(request: web.Request) -> web.Response:
    """로그인 GET — 폼 HTML 응답."""

    return web.Response(
        text=_render_login(), content_type="text/html", charset="utf-8"
    )


async def handle_login_post(request: web.Request) -> web.StreamResponse:
    """로그인 POST — IMAP4_SSL LOGIN 실 검증 + 세션 저장.

    한글 주석: imaplib 동기 호출 → asyncio.to_thread 로 event loop 회피.
    실패 시 _render_login(error) 응답 + 200 (form 재표시 정합).
    """

    form = await request.post()
    raw_user = (form.get("user") or "").strip()
    password = (form.get("password") or "").strip()
    if not raw_user or not password:
        return web.Response(
            text=_render_login("사용자명 + 패스워드 의무 입력"),
            content_type="text/html",
            charset="utf-8",
            status=400,
        )
    # 한글 주석: domain suffix 자동 추가 (`verify` → `verify@dopa.co.kr`)
    user = raw_user if "@" in raw_user else f"{raw_user}@dopa.co.kr"
    try:
        m = await asyncio.to_thread(
            imap_service.connect_and_login,
            IMAP_HOST,
            IMAP_PORT,
            user,
            password,
        )
        await asyncio.to_thread(m.logout)
    except imap_service.IMAPError as exc:
        log.warning("IMAP LOGIN FAIL user=%s — %s", user, exc)
        return web.Response(
            text=_render_login(f"로그인 실패 — {exc}"),
            content_type="text/html",
            charset="utf-8",
            status=401,
        )
    session = await get_session(request)
    _store_credentials(session, user, password)
    return web.HTTPFound("/inbox")


async def handle_logout(request: web.Request) -> web.StreamResponse:
    """로그아웃 — 세션 invalidate."""

    session = await get_session(request)
    session.invalidate()
    return web.HTTPFound("/login")


async def handle_inbox(request: web.Request) -> web.Response:
    """INBOX list — 세션 자격 IMAP 결선 + 최신 50통 paginate."""

    session = await get_session(request)
    creds = _read_credentials(session)
    if creds is None:
        return web.HTTPFound("/login")
    user, password = creds
    try:
        summaries = await asyncio.to_thread(
            imap_service.list_inbox,
            IMAP_HOST,
            IMAP_PORT,
            user,
            password,
            50,
        )
    except imap_service.IMAPError as exc:
        log.warning("IMAP list_inbox FAIL user=%s — %s", user, exc)
        # 한글 주석: 자격 stale 가능성 → 세션 invalidate + /login redirect
        session.invalidate()
        return web.HTTPFound("/login")
    return web.Response(
        text=_render_inbox(user, summaries),
        content_type="text/html",
        charset="utf-8",
    )


async def handle_mail_get(request: web.Request) -> web.Response:
    """단일 메일 view — UID path param + 세션 자격."""

    session = await get_session(request)
    creds = _read_credentials(session)
    if creds is None:
        return web.HTTPFound("/login")
    user, password = creds
    try:
        uid = int(request.match_info["uid"])
    except (KeyError, ValueError):
        return web.HTTPNotFound()
    try:
        body = await asyncio.to_thread(
            imap_service.fetch_body,
            IMAP_HOST,
            IMAP_PORT,
            user,
            password,
            uid,
        )
    except imap_service.IMAPError as exc:
        log.warning("IMAP fetch_body FAIL user=%s uid=%s — %s", user, uid, exc)
        session.invalidate()
        return web.HTTPFound("/login")
    if body is None:
        return web.HTTPNotFound()
    return web.Response(
        text=_render_mail(user, body),
        content_type="text/html",
        charset="utf-8",
    )


def build_app() -> web.Application:
    """aiohttp Application 조립 + aiohttp_session middleware 등록."""

    app = web.Application()
    session_key = _resolve_session_key()
    session_setup(app, EncryptedCookieStorage(session_key, cookie_name="WEBMAIL_SESSION"))
    app.router.add_get("/healthz", handle_healthz)
    app.router.add_get("/", handle_index)
    app.router.add_get("/login", handle_login_get)
    app.router.add_post("/login", handle_login_post)
    app.router.add_post("/logout", handle_logout)
    app.router.add_get("/inbox", handle_inbox)
    app.router.add_get("/mail/{uid}", handle_mail_get)
    return app


def main() -> None:
    """entry point — aiohttp web.run_app 직접 사용."""

    log.info(
        "webmail M4 listen %s:%s — IMAP %s:%s (cycle 169.861)",
        LISTEN_HOST,
        LISTEN_PORT,
        IMAP_HOST,
        IMAP_PORT,
    )
    app = build_app()
    web.run_app(app, host=LISTEN_HOST, port=LISTEN_PORT, access_log=log)


if __name__ == "__main__":
    main()
