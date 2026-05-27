# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — folder management (cycle 169.76 신설).

역할 — 사용자별 chat 폴더(telegram align)의 생성·조회·수정·삭제·초대 링크
발급을 처리한다. 폴더는 included/excluded chat 집합을 포함하며, 한 폴더 갱신은
단일 transaction 으로 묶인다(부분 반영 차단).

계층 위치 — server API handler 계층(정본 §E). auth_middleware Bearer 통과
(`request["user_id"]`) 후 진입하며, 영속화는 `folders` repository 에 위임한다.

의존성 — aiohttp `web` + `request.app["db_pool"]` + `folders` repository
(`insert_folder_with_chats`/`list_folders`/`update_folder_with_chats`/
`delete_folder`/`create_invite`/`fetch_by_folder_id_and_owner`). color_hex
검증 정규식 + invite URL base(env override)는 본 module 모듈 상수.

범위 한계 — 폴더 메타 + chat 멤버십 CRUD + 초대 토큰 발급만. 초대 토큰 수락
(가입자 폴더 합류) chain 은 별도 경로. owner 검증은 repository SQL(owner_id 조건)
에 위임 — 미존재/타 owner 는 404 로 수렴.

엔드포인트 카탈로그(실 함수 5 + register):
- `handle_create_folder`         POST   /api/folders                  — 생성.
- `handle_list_folders`          GET    /api/folders                  — 목록.
- `handle_update_folder`         PATCH  /api/folders/{folder_id}      — 수정(169.411).
- `handle_delete_folder`         DELETE /api/folders/{folder_id}      — 삭제.
- `handle_create_folder_invite`  POST   /api/folders/{folder_id}/invite — 초대 링크.
- `register_folder_routes` — server.main 등록 entry.
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
    """POST /api/folders — folder_id + name + color + included_chats.

    인증 — Bearer 의무(401).
    검증 순서 — (1) user_id 정수 → (2) JSON 파싱 → (3) folder_id + name 비어있지
    않음 → (4) color_hex 제공 시 #RRGGBB 정규식 → repository(단일 transaction).

    Parameters — body ``{folder_id, name, color_name?, color_hex?, included_chats[],
        excluded_chats[]}``. color_hex 는 ``#RRGGBB`` 형식.
    Returns — 201 + ``{ok, folder_id, id}``(id = DB PK).
    Raises — HTTPUnauthorized / HTTPBadRequest(JSON·필수 필드·color_hex 위반).
    부작용 — `insert_folder_with_chats`(folders + folder_chats 단일 transaction INSERT).
    """
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
    """GET /api/folders — owner folder list.

    의도 — 폴더 탭 + 각 폴더의 included/excluded chat 집합을 함께 제공한다.
    인증 — Bearer 의무(401).
    Returns — 200 + ``{ok, folders: [{folder_id, name, color_*, chat_count,
        included_chats, excluded_chats}]}``.
    부작용 — 부재(읽기 전용). 폴더당 멤버십 SELECT 1회 추가(N+1 — 폴더 수는 소규모).
    """
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
    """DELETE /api/folders/{folder_id}.

    인증 — Bearer 의무(401). owner 검증은 repository SQL(owner_id 조건)에 위임.
    Parameters — match_info ``folder_id``.
    Returns — 200 + ``{ok, folder_id}``. 미존재/타 owner 시 404.
    부작용 — `delete_folder`(folders + folder_chats DELETE, owner 한정).
    """
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
    """POST /api/folders/{folder_id}/invite — 초대 link token 생성.

    인증 — Bearer 의무(401). owner 만 초대 발급 — folder 조회(owner 조건) 실패 404.
    Parameters — match_info ``folder_id``.
    Returns — 201 + ``{ok, folder_id, invite_token, invite_url}``.
        invite_url base 는 env ``INVITE_URL_BASE`` override(기본 tootalk.demo).
    부작용 — `create_invite`(folder_invites INSERT, 토큰 발급).
    """
    user_id = request.get("user_id")
    if not isinstance(user_id, int):
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    folder_id = request.match_info.get("folder_id", "")
    pool = request.app["db_pool"]
    # owner 검증 + folder PK 확보를 단일 SQL 로(cycle 169.79 MED-1 — 분리 조회 race 회피)
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
    """server.main entry — folder 5 endpoint(create/list/update/delete/invite) 등록."""
    app.router.add_post("/api/folders", handle_create_folder)
    app.router.add_get("/api/folders", handle_list_folders)
    app.router.add_patch("/api/folders/{folder_id}", handle_update_folder)  # cycle 169.411
    app.router.add_delete("/api/folders/{folder_id}", handle_delete_folder)
    app.router.add_post("/api/folders/{folder_id}/invite", handle_create_folder_invite)
    log.info("[api] folder 4 endpoint 등록 완료")
