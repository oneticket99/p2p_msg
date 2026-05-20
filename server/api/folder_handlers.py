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
from typing import Any

from aiohttp import web

from server.db.repositories import folders as folder_repo

log = logging.getLogger(__name__)


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
    pool = request.app["db_pool"]
    folder_pk = await folder_repo.insert_folder(
        pool,
        folder_id=folder_id,
        owner_id=user_id,
        name=name,
        color_name=color_name,
    )
    # 한글 주석 — included_chats batch INSERT
    for chat in payload.get("included_chats", []):
        await folder_repo.add_folder_chat(
            pool,
            folder_pk=folder_pk,
            chat_kind=str(chat.get("kind", "")),
            chat_target_id=int(chat.get("target_id", 0)),
            mode="include",
        )
    for chat in payload.get("excluded_chats", []):
        await folder_repo.add_folder_chat(
            pool,
            folder_pk=folder_pk,
            chat_kind=str(chat.get("kind", "")),
            chat_target_id=int(chat.get("target_id", 0)),
            mode="exclude",
        )
    return web.json_response({"ok": True, "folder_id": folder_id, "id": folder_pk}, status=201)


async def handle_list_folders(request: web.Request) -> web.Response:
    """GET /api/folders — owner folder list."""
    user_id = request.get("user_id")
    if not isinstance(user_id, int):
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    pool = request.app["db_pool"]
    rows = await folder_repo.list_folders(pool, owner_id=user_id)
    return web.json_response({
        "ok": True,
        "folders": [
            {
                "folder_id": r.folder_id,
                "name": r.name,
                "color_name": r.color_name,
                "color_hex": r.color_hex,
                "chat_count": r.chat_count,
            } for r in rows
        ],
    })


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
    rows = await folder_repo.list_folders(pool, owner_id=user_id)
    folder = next((r for r in rows if r.folder_id == folder_id), None)
    if folder is None:
        raise web.HTTPNotFound(reason="folder 부재")
    token = await folder_repo.create_invite(pool, folder_pk=folder.id, created_by=user_id)
    return web.json_response({
        "ok": True,
        "folder_id": folder_id,
        "invite_token": token,
        "invite_url": f"https://tootalk.demo/folder/{token}",
    }, status=201)


def register_folder_routes(app: web.Application) -> None:
    app.router.add_post("/api/folders", handle_create_folder)
    app.router.add_get("/api/folders", handle_list_folders)
    app.router.add_delete("/api/folders/{folder_id}", handle_delete_folder)
    app.router.add_post("/api/folders/{folder_id}/invite", handle_create_folder_invite)
    log.info("[api] folder 4 endpoint 등록 완료")
