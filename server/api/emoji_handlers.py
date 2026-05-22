# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — Phase 5 Item 3 emoji pack share (cycle 132 skeleton).

엔드포인트 5종 (skeleton placeholder, Phase 5 본격 cycle 141~150 본격 binding):
- GET  /api/emoji/packs                       — 공개 + approved 팩 list
- GET  /api/emoji/packs/{slug}                — 단일 팩 + item list
- POST /api/emoji/packs                       — 신규 팩 생성 (owner_user_id 의무)
- POST /api/emoji/packs/{slug}/items          — 팩 안 아이템 추가 (file upload)
- POST /api/emoji/packs/{slug}/moderation     — admin moderation status 갱신

설계 결정
---------
- skeleton 단계 = 200 응답 반환 + Phase 5 본격 cycle 의 actual binding 명문.
- auth_middleware 의 Bearer 검증 의무 (POST 3 endpoint, GET 2 endpoint 는 public).
- moderation endpoint = admin role 검증 의무 (Phase 5 본격 cycle).
- OCR moderation chain = `app.bot.jailbreak_detector_ocr.detect_image` placeholder
  binding (별개 cycle 의 Tesseract / EasyOCR 의 실 검증).
- file upload = multipart/form-data (Phase 5 본격 cycle 의 S3 또는 server volume).

본 cycle 의 범위 외 (별개 cycle 141~150):
- actual DB binding (emoji_packs repository 호출)
- 실 file upload 처리 (S3 또는 volume)
- OCR moderation chain 의 actual 검증
- admin role 검증 + DMCA takedown 의 workflow
- 다운로드 count atomic INCREMENT
- pagination (cursor-based 또는 offset)
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

from aiohttp import web

from server.db.repositories import emoji_packs as _packs_repo

log = logging.getLogger(__name__)

# cycle 169.415 — slug regex (lowercase + hyphen + digit, 2~64 chars)
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")


def _pack_to_dict(p: _packs_repo.EmojiPackRow) -> Dict[str, Any]:
    """EmojiPackRow → JSON dict (cycle 169.415)."""
    return {
        "id": p.id,
        "owner_user_id": p.owner_user_id,
        "name": p.name,
        "slug": p.slug,
        "description": p.description,
        "is_public": p.is_public,
        "moderation_status": p.moderation_status.value,
        "download_count": p.download_count,
    }


def _item_to_dict(i: _packs_repo.EmojiPackItemRow) -> Dict[str, Any]:
    """EmojiPackItemRow → JSON dict."""
    return {
        "id": i.id,
        "pack_id": i.pack_id,
        "shortcode": i.shortcode,
        "file_path": i.file_path,
        "mime_type": i.mime_type,
        "file_size": i.file_size,
        "width": i.width,
        "height": i.height,
        "moderation_status": i.moderation_status.value,
    }


async def handle_list_packs(request: web.Request) -> web.Response:
    """GET /api/emoji/packs — 공개 + approved 팩 list (cycle 169.415 actual binding).

    query: ?limit=50&offset=0 (limit cap=200).
    응답 schema = ``{"packs": [...], "limit": int, "offset": int, "count": int}``.
    """
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"packs": [], "limit": 0, "offset": 0, "count": 0})
    try:
        limit = max(1, min(200, int(request.query.get("limit", "50"))))
        offset = max(0, int(request.query.get("offset", "0")))
    except ValueError:
        raise web.HTTPBadRequest(reason="limit/offset 정수 의무")
    rows = await _packs_repo.list_public_approved(pool, limit=limit, offset=offset)
    payload = [_pack_to_dict(r) for r in rows]
    return web.json_response({
        "packs": payload, "limit": limit, "offset": offset, "count": len(payload),
    })


async def handle_get_pack(request: web.Request) -> web.Response:
    """GET /api/emoji/packs/{slug} — 단일 팩 + item list (cycle 169.415 actual binding).

    응답 schema = ``{"pack": {...} | null, "items": [...]}``.
    """
    slug = request.match_info.get("slug", "")
    if not slug:
        raise web.HTTPBadRequest(reason="slug 의무")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"pack": None, "items": []})
    pack = await _packs_repo.get_pack_by_slug(pool, slug)
    if pack is None:
        raise web.HTTPNotFound(reason=f"pack slug={slug} 부재")
    items = await _packs_repo.list_items(pool, pack_id=pack.id)
    return web.json_response({
        "pack": _pack_to_dict(pack),
        "items": [_item_to_dict(i) for i in items],
    })


async def handle_create_pack(request: web.Request) -> web.Response:
    """POST /api/emoji/packs — 신규 팩 생성 (cycle 169.415 actual binding).

    요청 schema = ``{"name": str, "slug": str, "description": str, "is_public": bool}``.
    응답 schema = ``{"pack_id": int, "slug": str}``.
    """
    user_id = request.get("user_id")
    if user_id is None or not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    try:
        body = await request.json()
    except ValueError as exc:
        raise web.HTTPBadRequest(reason="JSON body 의무") from exc
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(reason="body object 의무")

    name = str(body.get("name", "")).strip()
    slug = str(body.get("slug", "")).strip().lower()
    description = body.get("description")
    is_public = bool(body.get("is_public", False))

    if not name or len(name) > 64:
        raise web.HTTPBadRequest(reason="name 1~64자 의무")
    if not _SLUG_RE.match(slug):
        raise web.HTTPBadRequest(reason="slug 형식 부재 (소문자 + 숫자 + hyphen, 2~64자)")
    if description is not None and not isinstance(description, str):
        raise web.HTTPBadRequest(reason="description string 의무")
    if description is not None and len(description) > 255:
        raise web.HTTPBadRequest(reason="description 255자 cap")

    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response(
            {"error": "DB_DISABLED", "message": "DB pool 비활성"}, status=503
        )
    # slug UNIQUE 사전 검증 (충돌 시점 graceful 409)
    existing = await _packs_repo.get_pack_by_slug(pool, slug)
    if existing is not None:
        return web.json_response(
            {"error": "SLUG_CONFLICT", "message": f"slug={slug} 이미 존재"}, status=409
        )
    try:
        pack_id = await _packs_repo.insert_pack(
            pool, owner_user_id=user_id, name=name, slug=slug,
            description=description, is_public=is_public,
        )
    except ValueError as exc:
        raise web.HTTPBadRequest(reason=str(exc))
    log.info("[emoji_pack] create user_id=%d slug=%s pack_id=%d", user_id, slug, pack_id)
    return web.json_response({"pack_id": pack_id, "slug": slug}, status=201)


async def handle_add_item(request: web.Request) -> web.Response:
    """POST /api/emoji/packs/{slug}/items — 팩 안 아이템 추가 (skeleton).

    Phase 5 본격 cycle: multipart file upload + OCR moderation + insert_item.

    요청 = multipart/form-data (file + shortcode field).
    응답 schema:
        {"item_id": 0, "skeleton": true}
    """

    user_id = request.get("user_id")
    if user_id is None or not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")

    slug = request.match_info.get("slug", "")
    if not slug:
        raise web.HTTPBadRequest(reason="slug 의무")

    # 한글 주석: skeleton — 본격 cycle 의 file upload + OCR detect_image 의 chain
    log.debug("POST /api/emoji/packs/%s/items skeleton user_id=%d", slug, user_id)
    return web.json_response({"item_id": 0, "skeleton": True}, status=200)


async def handle_moderation(request: web.Request) -> web.Response:
    """POST /api/emoji/packs/{slug}/moderation — admin moderation 갱신 (skeleton).

    Phase 5 본격 cycle: admin role 검증 + update_moderation_status + audit log +
    DMCA takedown workflow.

    요청 schema:
        {"moderation_status": "approved" | "rejected" | "dmca_takedown"}
    응답 schema:
        {"updated": true, "skeleton": true}
    """

    user_id = request.get("user_id")
    if user_id is None or not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")

    slug = request.match_info.get("slug", "")
    if not slug:
        raise web.HTTPBadRequest(reason="slug 의무")

    try:
        body = await request.json()
    except ValueError as exc:
        raise web.HTTPBadRequest(reason="JSON body 의무") from exc
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(reason="body object 의무")

    new_status = body.get("moderation_status")
    if new_status not in ("pending", "approved", "rejected", "dmca_takedown"):
        raise web.HTTPBadRequest(reason="moderation_status 4 ENUM 만 허용")

    # 한글 주석: skeleton — 본격 cycle 의 admin role 검증 + update + DMCA workflow
    log.debug(
        "POST /api/emoji/packs/%s/moderation skeleton user_id=%d new=%s",
        slug, user_id, new_status,
    )
    return web.json_response({"updated": True, "skeleton": True}, status=200)


def register_emoji_routes(app: web.Application) -> None:
    """``server.main`` 의 register entry — 5 endpoint 등록.

    Phase 5 본격 cycle 141~150 에서 실 binding 진입. 본 cycle 132 = skeleton 만.
    """

    app.router.add_get("/api/emoji/packs", handle_list_packs)
    app.router.add_get("/api/emoji/packs/{slug}", handle_get_pack)
    app.router.add_post("/api/emoji/packs", handle_create_pack)
    app.router.add_post("/api/emoji/packs/{slug}/items", handle_add_item)
    app.router.add_post("/api/emoji/packs/{slug}/moderation", handle_moderation)
