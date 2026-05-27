# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — 읽음 상태 추적 (cycle 169.447~470).

역할 — 사용자별 방 읽음 커서(last_read_msg_id)를 기록하고, 안읽음 개수/마지막
읽음 위치를 배치로 조회한다. chat list 의 unread badge + 진입 시 스크롤 위치 복원
근거가 된다.

계층 위치 — server API handler 계층(정본 §E). auth_middleware 통과(Bearer 의무)
후 진입하며, 영속화는 `read_states` repository 에 위임한다.

의존성 — aiohttp `web` + `request.app["db_pool"]` + `read_states` repository
(`upsert_last_read`/`get_unread_counts`/`get_last_read_batch`).

범위 한계 — 읽음 커서 CRUD 만. 실 메시지 본문/타임라인 조회는 messages 경로,
실시간 read receipt broadcast 는 signaling 경로가 담당한다. db_pool 부재 시 빈
결과(graceful) — 읽음 상태는 비치명 데이터라 503 대신 빈 응답.

엔드포인트 카탈로그(실 함수 3 + register 1):
- `handle_mark_read`         POST /api/rooms/{room_id}/read — last_read UPSERT.
- `handle_unread_counts`     GET  /api/rooms/unread         — 안읽음 개수 batch.
- `handle_last_read_batch`   GET  /api/rooms/last-read      — 읽음 커서 batch(169.470).
- `register_read_routes` — server.main 등록 entry.
"""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web

from server.db.repositories import read_states as _rs_repo

log = logging.getLogger(__name__)


async def handle_mark_read(request: web.Request) -> web.Response:
    """POST /api/rooms/{room_id}/read — last_read_msg_id UPSERT.

    의도 — 사용자가 방을 포커스한 시점의 마지막 읽은 메시지 id 를 기록해 이후
    unread 계산 기준선으로 삼는다.

    인증 — Bearer 의무(401).
    검증 순서 — (1) user_id 유효 → (2) room_id 정수 → (3) body 파싱(실패 시 빈
    dict 로 graceful) → (4) body=dict → (5) last_read_msg_id 0 이상 정수 →
    (6) db_pool 가용(부재 시 503).

    Parameters — match_info ``room_id``(경로 정수), body ``{last_read_msg_id: int}``.
    Returns — 200 + ``{ok, room_id, last_read_msg_id}``.
    Raises — HTTPUnauthorized / HTTPBadRequest(room_id·필드 위반). db_pool 부재 503.
    부작용 — `read_states` UPSERT(DB write) + INFO 로그.
    """
    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    try:
        room_id = int(request.match_info["room_id"])
    except (KeyError, ValueError):
        raise web.HTTPBadRequest(reason="room_id 정수 의무")
    try:
        body = await request.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(reason="body object 의무")
    last_read = body.get("last_read_msg_id")
    if not isinstance(last_read, int) or last_read < 0:
        raise web.HTTPBadRequest(reason="last_read_msg_id 0 이상 정수 의무")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response(
            {"error": "DB_DISABLED"}, status=503,
        )
    await _rs_repo.upsert_last_read(
        pool, user_id=user_id, room_id=room_id, last_read_msg_id=last_read,
    )
    log.info("[read] user=%d room=%d last_read=%d", user_id, room_id, last_read)
    return web.json_response({"ok": True, "room_id": room_id, "last_read_msg_id": last_read})


async def handle_unread_counts(request: web.Request) -> web.Response:
    """GET /api/rooms/unread?room_ids=1,2,3 — multiple room unread count batch.

    의도 — chat list 의 방별 unread badge 를 1회 요청으로 채운다(N+1 회피).

    인증 — Bearer 의무(401).
    검증 순서 — (1) user_id 유효 → (2) room_ids 쿼리 파싱(빈 값/빈 목록 시
    빈 결과 graceful) → (3) 정수 변환(실패 400) → (4) 100개 cap(초과 400) →
    (5) db_pool 가용(부재 시 빈 결과).

    Parameters — query ``room_ids`` = comma-separated 정수(최대 100).
    Returns — 200 + ``{counts: {room_id(str): unread(int)}}``.
    Raises — HTTPUnauthorized / HTTPBadRequest(비정수·cap 초과).
    부작용 — 부재(읽기 전용 SELECT).
    """
    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    raw = request.query.get("room_ids", "").strip()
    if not raw:
        return web.json_response({"counts": {}})
    try:
        room_ids = [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise web.HTTPBadRequest(reason="room_ids = comma-separated 정수 의무")
    if not room_ids:
        return web.json_response({"counts": {}})
    if len(room_ids) > 100:
        raise web.HTTPBadRequest(reason="room_ids 100개 cap")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"counts": {}})
    counts = await _rs_repo.get_unread_counts(
        pool, user_id=user_id, room_ids=room_ids,
    )
    return web.json_response({"counts": {str(k): v for k, v in counts.items()}})


async def handle_last_read_batch(request: web.Request) -> web.Response:
    """GET /api/rooms/last-read?room_ids=1,2,3 — batch last_read_msg_id (cycle 169.470).

    의도 — 방 진입 시 마지막 읽음 위치로 스크롤 복원하기 위해 방별 읽음 커서를
    배치 조회한다(unread 개수와 별개 — 위치 자체가 필요).

    인증 — Bearer 의무(401).
    검증 순서 — (1) user_id 유효 → (2) room_ids 파싱(빈 값 시 빈 결과) →
    (3) 정수 변환(실패 400) → (4) 1~100 cap(빈 목록/초과 400) → (5) db_pool
    가용(부재 시 빈 결과).

    Parameters — query ``room_ids`` = comma-separated 정수(1~100).
    Returns — 200 + ``{last_read: {room_id(str): last_read_msg_id(int)}}``.
    Raises — HTTPUnauthorized / HTTPBadRequest(비정수·cap 위반).
    부작용 — 부재(읽기 전용 SELECT).
    """
    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    raw = request.query.get("room_ids", "").strip()
    if not raw:
        return web.json_response({"last_read": {}})
    try:
        room_ids = [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise web.HTTPBadRequest(reason="room_ids = comma-separated 정수 의무")
    if not room_ids or len(room_ids) > 100:
        raise web.HTTPBadRequest(reason="room_ids 1~100 cap")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"last_read": {}})
    out = await _rs_repo.get_last_read_batch(
        pool, user_id=user_id, room_ids=room_ids,
    )
    return web.json_response({"last_read": {str(k): v for k, v in out.items()}})


def register_read_routes(app: web.Application) -> None:
    """server.main register entry — 3 endpoint 등록."""
    app.router.add_post("/api/rooms/{room_id}/read", handle_mark_read)
    app.router.add_get("/api/rooms/unread", handle_unread_counts)
    app.router.add_get("/api/rooms/last-read", handle_last_read_batch)  # cycle 169.470
    log.info("[api] read 3 endpoint 등록 완료 (cycle 169.447~470)")
