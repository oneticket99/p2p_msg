# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — folder management (cycle 169.76 신설).

엔드포인트:
- POST /api/folders — 폴더 생성
- GET /api/folders — 폴더 목록
- DELETE /api/folders/{folder_id} — 폴더 삭제
- POST /api/folders/{folder_id}/invite — 초대 링크 생성
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from aiohttp import web

from server.db.repositories import folders as folder_repo

log = logging.getLogger(__name__)

# cycle 169.79 회수 — color_hex format validation (MED-4)
_COLOR_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
# cycle 169.79 회수 — invite_url env override (LOW-2)
_INVITE_URL_BASE = os.environ.get("INVITE_URL_BASE", "https://tootalk.demo")


async def handle_create_folder(request: web.Request) -> web.Response:
    """POST /api/folders — folder_id + name + color + included_chats."""
    user_id = request.get("user_id")
    if not isinstance(user_id, int):
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    try:
        payload = await request.json()
    except Exception as exc:
        raise web.HTTPBadRequest(reason=f"JSON parse fail: {exc}")
    folder_id = str(payload.get("folder_id", ""))
    name = str(payload.get("name", "")).strip()
    if not folder_id or not name:
        raise web.HTTPBadRequest(reason="folder_id + name 의무")
    color_name = payload.get("color_name") or None
    # cycle 169.79 회수 — color_hex format validation (MED-4)
    color_hex = payload.get("color_hex") or None
    if color_hex is not None and not _COLOR_HEX_RE.match(str(color_hex)):
        raise web.HTTPBadRequest(reason="color_hex 형식 부재 (#RRGGBB)")
    pool = request.app["db_pool"]
    # cycle 169.79 회수 — single transaction aggregate (HIGH-2)
    folder_pk = await folder_repo.insert_folder_with_chats(
        pool,
        folder_id=folder_id,
        owner_id=user_id,
        name=name,
        color_name=color_name,
        color_hex=color_hex,
        included_chats=payload.get("included_chats", []),
        excluded_chats=payload.get("excluded_chats", []),
    )
    return web.json_response({"ok": True, "folder_id": folder_id, "id": folder_pk}, status=201)


async def handle_list_folders(request: web.Request) -> web.Response:
    """GET /api/folders — owner folder list."""
    user_id = request.get("user_id")
    if not isinstance(user_id, int):
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    pool = request.app["db_pool"]
    rows = await folder_repo.list_folders(pool, owner_id=user_id)
    # cycle 169.387 — included_chats / excluded_chats field 추가 (review finding 회수 image #148)
    folders_payload = []
    for r in rows:
        chats = await folder_repo.list_folder_chats(pool, folder_pk=r.id)
        folders_payload.append({
            "folder_id": r.folder_id,
            "name": r.name,
            "color_name": r.color_name,
            "color_hex": r.color_hex,
            "chat_count": r.chat_count,
            "included_chats": chats["included_chats"],
            "excluded_chats": chats["excluded_chats"],
        })
    return web.json_response({
        "ok": True,
        "folders": folders_payload,
    })


async def handle_update_folder(request: web.Request) -> web.Response:
    """PATCH /api/folders/{folder_id} — folder edit mode actual UPDATE (cycle 169.411).

    server folder UPDATE chain — 이전 INSERT/DELETE client-side replace 우회 회수.
    payload schema = create 와 동일 (name + color + included_chats + excluded_chats).
    """
    user_id = request.get("user_id")
    if not isinstance(user_id, int):
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    folder_id = request.match_info.get("folder_id", "")
    if not folder_id:
        raise web.HTTPBadRequest(reason="folder_id path 의무")
    try:
        payload = await request.json()
    except Exception as exc:
        raise web.HTTPBadRequest(reason=f"JSON parse fail: {exc}")
    name = str(payload.get("name", "")).strip()
    if not name:
        raise web.HTTPBadRequest(reason="name 의무")
    color_name = payload.get("color_name") or None
    color_hex = payload.get("color_hex") or None
    if color_hex is not None and not _COLOR_HEX_RE.match(str(color_hex)):
        raise web.HTTPBadRequest(reason="color_hex 형식 부재 (#RRGGBB)")
    pool = request.app["db_pool"]
    ok = await folder_repo.update_folder_with_chats(
        pool,
        folder_id=folder_id,
        owner_id=user_id,
        name=name,
        color_name=color_name,
        color_hex=color_hex,
        included_chats=payload.get("included_chats", []),
        excluded_chats=payload.get("excluded_chats", []),
    )
    if not ok:
        raise web.HTTPNotFound(reason="folder 부재 또는 권한 부재")
    return web.json_response({"ok": True, "folder_id": folder_id})


async def handle_delete_folder(request: web.Request) -> web.Response:
    """DELETE /api/folders/{folder_id}."""
    user_id = request.get("user_id")
    if not isinstance(user_id, int):
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    folder_id = request.match_info.get("folder_id", "")
    pool = request.app["db_pool"]
    ok = await folder_repo.delete_folder(pool, folder_id, user_id)
    if not ok:
        raise web.HTTPNotFound(reason="folder 부재 또는 권한 부재")
    return web.json_response({"ok": True, "folder_id": folder_id})


async def handle_create_folder_invite(request: web.Request) -> web.Response:
    """POST /api/folders/{folder_id}/invite — 초대 link token 생성."""
    user_id = request.get("user_id")
    if not isinstance(user_id, int):
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    folder_id = request.match_info.get("folder_id", "")
    pool = request.app["db_pool"]
    # cycle 169.79 회수 — single SQL owner check (MED-1)
    folder = await folder_repo.fetch_by_folder_id_and_owner(pool, folder_id, user_id)
    if folder is None:
        raise web.HTTPNotFound(reason="folder 부재")
    token = await folder_repo.create_invite(pool, folder_pk=folder.id, created_by=user_id)
    return web.json_response({
        "ok": True,
        "folder_id": folder_id,
        "invite_token": token,
        # cycle 169.79 회수 — invite_url env override (LOW-2)
        "invite_url": f"{_INVITE_URL_BASE}/folder/{token}",
    }, status=201)


def register_folder_routes(app: web.Application) -> None:
    app.router.add_post("/api/folders", handle_create_folder)
    app.router.add_get("/api/folders", handle_list_folders)
    app.router.add_patch("/api/folders/{folder_id}", handle_update_folder)  # cycle 169.411
    app.router.add_delete("/api/folders/{folder_id}", handle_delete_folder)
    app.router.add_post("/api/folders/{folder_id}/invite", handle_create_folder_invite)
    log.info("[api] folder 4 endpoint 등록 완료")
