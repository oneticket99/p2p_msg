# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — chat history lazy load (Phase 3 entry 사이클 60).

엔드포인트:
- GET /api/messages — 룸 의 [start_ts, end_ts) 구간 timeline fetch (lazy load)

사이클 59 의 `app/ui/chat_history_policy.py` 의 server-side counterpart.
ChatView 의 scroll top 도달 의 server fetch 의 직접 응답.

설계 결정
---------
- auth_middleware 의 Bearer 검증 의무 (PUBLIC_PATHS 외).
- query string = `room_id` (int) + `start_ts_ms` (UNIX epoch ms) + `end_ts_ms` (ms) + `limit` (optional default 1000).
- 응답 = JSON {messages: [...]} + created_at = ISO 8601 string.
- 권한 검증 = 사용자 의 룸 멤버십 의 의 검증 (별개 cycle — 본 cycle = pool query 만).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from aiohttp import web

from server.db.repositories import messages as messages_repo

log = logging.getLogger(__name__)

# query string 의 limit default + 상한 (memory release 정합 [[feedback-chat-accumulation-memory-release-mandatory]])
_DEFAULT_LIMIT = 1000
_MAX_LIMIT = 5000


def _parse_int_query(request: web.Request, key: str, *, required: bool = True) -> int:
    """query string 의 int 파싱 — 누락 / 무효 = 400."""

    raw = request.query.get(key)
    if raw is None:
        if required:
            raise web.HTTPBadRequest(reason=f"query {key} 의무")
        return 0
    try:
        return int(raw)
    except ValueError as exc:
        raise web.HTTPBadRequest(reason=f"query {key} int 의무") from exc


def _ms_to_datetime(ms: int) -> datetime:
    """UNIX epoch ms → UTC datetime."""

    if ms < 0:
        raise web.HTTPBadRequest(reason=f"timestamp_ms 음수 불가 — {ms}")
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def _message_row_to_wire(row: Any) -> Dict[str, Any]:
    """MessageRow → JSON-safe dict."""

    return {
        "id": row.id,
        "room_id": row.room_id,
        "sender_id": row.sender_id,
        "kind": row.kind,
        "body": row.body,
        "file_id": row.file_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def handle_list_messages_in_range(request: web.Request) -> web.Response:
    """GET /api/messages?room_id=X&start_ts_ms=Y&end_ts_ms=Z&limit=L."""

    user_id = request.get("user_id")
    if user_id is None:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")

    room_id = _parse_int_query(request, "room_id")
    start_ts_ms = _parse_int_query(request, "start_ts_ms")
    end_ts_ms = _parse_int_query(request, "end_ts_ms")
    limit_raw = request.query.get("limit")
    if limit_raw is not None:
        try:
            limit = int(limit_raw)
        except ValueError as exc:
            raise web.HTTPBadRequest(reason="query limit int 의무") from exc
    else:
        limit = _DEFAULT_LIMIT
    if limit <= 0 or limit > _MAX_LIMIT:
        raise web.HTTPBadRequest(
            reason=f"limit 의 1 < limit <= {_MAX_LIMIT} 의무 — 실 {limit}"
        )

    start_ts = _ms_to_datetime(start_ts_ms)
    end_ts = _ms_to_datetime(end_ts_ms)
    if end_ts <= start_ts:
        raise web.HTTPBadRequest(
            reason="end_ts 의 start_ts 초과 의무"
        )

    pool = request.app["db_pool"]
    try:
        rows = await messages_repo.list_messages_in_range(
            pool,
            room_id=room_id,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=limit,
        )
    except ValueError as exc:
        raise web.HTTPBadRequest(reason=str(exc)) from exc

    payload: Dict[str, Any] = {
        "messages": [_message_row_to_wire(r) for r in rows],
        "count": len(rows),
        "limit": limit,
    }
    return web.json_response(payload)


def register_messages_routes(app: web.Application) -> None:
    """``server.main`` 의 register entry."""

    app.router.add_get("/api/messages", handle_list_messages_in_range)
