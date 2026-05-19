# SPDX-License-Identifier: GPL-3.0-or-later
"""자동 업데이트 endpoint skeleton — Phase 5 cycle 132.

본 module = GET 최신 버전 + POST 신규 버전 등록 (admin only skeleton).
실 GitHub Release 연동 / CI workflow trigger = 별개 cycle 의 본격 작업.

엔드포인트:
- GET /api/version/latest?platform=macos-arm64 → 200 최신 버전 메타 / 404 부재
- POST /api/version/release (admin only) → 신규 버전 INSERT (skeleton 401 fallback)

설계 결정
---------
- GET = public (auth_middleware bypass 의 의도, _PUBLIC_PATHS 추가 의 후속).
- POST = admin only — ADMIN_TOKEN env 의 Bearer 검증 (skeleton 단순화).
- pool 부재 = graceful 503 (DB_ENABLED=0 dev 정합).
- platform query 의 ENUM 검증 의무 (Platform.from_str 실패 = 400).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from aiohttp import web

from server.db.repositories.app_versions import (
    AppVersionRow,
    Platform,
    get_latest_by_platform,
    insert_version,
)

log = logging.getLogger(__name__)

# 한글 주석: admin Bearer 토큰 env 키 — 실 운영 = secrets manager 의 주입 의무
_ENV_ADMIN_TOKEN = "VERSION_ADMIN_TOKEN"


def _parse_platform(raw: Optional[str]) -> Optional[Platform]:
    """query string 의 platform → Platform ENUM. 무효 시 None 반환."""

    if not raw:
        return None
    try:
        return Platform(raw)
    except ValueError:
        return None


def _row_to_json(row: AppVersionRow) -> dict[str, Any]:
    """AppVersionRow → JSON dict 의 client 응답 base.

    released_at 의 ISO 8601 직렬화 + None 의 보존.
    """

    return {
        "version": row.version,
        "platform": row.platform.value,
        "zip_url": row.zip_url,
        "sha256": row.sha256,
        "file_size": row.file_size,
        "min_compatible_version": row.min_compatible_version,
        "released_at": row.released_at.isoformat() if row.released_at else None,
        "release_notes": row.release_notes,
        "is_latest": row.is_latest,
    }


async def handle_get_latest(req: web.Request) -> web.Response:
    """GET /api/version/latest?platform=<ENUM> — 최신 버전 메타 응답.

    응답 schema:
        200: {version, platform, zip_url, sha256, file_size,
              min_compatible_version, released_at, release_notes, is_latest}
        400: {"error": "platform invalid"} — query 무효
        404: {"error": "no version"} — 해당 platform 의 버전 부재
        503: {"error": "db unavailable"} — pool 부재 graceful
    """

    platform = _parse_platform(req.query.get("platform"))
    if platform is None:
        return web.json_response(
            {"error": "platform invalid", "allowed": [p.value for p in Platform]},
            status=400,
        )

    pool = req.app.get("db_pool")
    if pool is None:
        # 한글 주석: pool 부재 graceful — dev 환경 의 DB_ENABLED=0 정합
        return web.json_response({"error": "db unavailable"}, status=503)

    try:
        row = await get_latest_by_platform(pool, platform)
    except Exception as exc:  # noqa: BLE001
        log.warning("[version] get_latest fail platform=%s err=%r", platform.value, exc)
        return web.json_response({"error": "internal"}, status=500)

    if row is None:
        return web.json_response(
            {"error": "no version", "platform": platform.value}, status=404
        )

    return web.json_response(_row_to_json(row), status=200)


async def handle_post_release(req: web.Request) -> web.Response:
    """POST /api/version/release — 신규 버전 등록 (admin only skeleton).

    Authorization: Bearer <VERSION_ADMIN_TOKEN env> 의 Bearer 의무.
    body schema = {version, platform, zip_url, sha256, file_size?,
                   min_compatible_version?, release_notes?, is_latest?}.

    응답:
        200: {"ok": true, "id": <lastrowid>}
        400: {"error": "..."} — body 무효
        401: {"error": "admin only"} — Bearer 부재 또는 불일치
        503: {"error": "db unavailable"} — pool 부재 graceful
    """

    # 한글 주석: admin Bearer 검증 — env token 부재 시 401 fallback (skeleton 안전)
    admin_token = os.environ.get(_ENV_ADMIN_TOKEN, "").strip()
    if not admin_token:
        return web.json_response(
            {"error": "admin only", "reason": "VERSION_ADMIN_TOKEN unset"}, status=401
        )

    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return web.json_response(
            {"error": "admin only", "reason": "Bearer header missing"}, status=401
        )
    token = auth_header[len("Bearer ") :].strip()
    if token != admin_token:
        return web.json_response(
            {"error": "admin only", "reason": "token mismatch"}, status=401
        )

    pool = req.app.get("db_pool")
    if pool is None:
        return web.json_response({"error": "db unavailable"}, status=503)

    try:
        body = await req.json() if req.content_length else {}
    except Exception:
        return web.json_response({"error": "json invalid"}, status=400)

    version = body.get("version", "")
    platform = _parse_platform(body.get("platform"))
    zip_url = body.get("zip_url", "")
    sha256 = body.get("sha256", "")
    if not version or platform is None or not zip_url or not sha256:
        return web.json_response(
            {
                "error": "body invalid",
                "required": ["version", "platform", "zip_url", "sha256"],
            },
            status=400,
        )

    try:
        new_id = await insert_version(
            pool,
            version=str(version),
            platform=platform,
            zip_url=str(zip_url),
            sha256=str(sha256),
            file_size=int(body.get("file_size", 0)),
            min_compatible_version=body.get("min_compatible_version"),
            release_notes=body.get("release_notes"),
            is_latest=bool(body.get("is_latest", False)),
        )
    except ValueError as exc:
        return web.json_response({"error": str(exc)}, status=400)
    except Exception as exc:  # noqa: BLE001
        log.warning("[version] insert fail err=%r", exc)
        return web.json_response({"error": "internal"}, status=500)

    return web.json_response({"ok": True, "id": new_id}, status=200)


def register_version_routes(app: web.Application) -> None:
    """한글 주석 — server.main entry 의 자동 업데이트 2 endpoint 등록.

    GET /api/version/latest = public + DB 의 latest 조회.
    POST /api/version/release = admin Bearer + DB INSERT (skeleton).
    """

    app.router.add_get("/api/version/latest", handle_get_latest)
    app.router.add_post("/api/version/release", handle_post_release)
    log.info("[api] version 2 endpoint 등록 완료 (skeleton)")
