# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — message persistence + MESSAGE_SEND audit chain (cycle 141).

역할 — 룸 메시지의 적재·구간/페이지 조회·단건 조회·soft delete 를 처리하고,
발신 시 MESSAGE_SEND audit + (DM) push 알림을 건다. 권한은 룸 owner/활성 peer 로
판정한다.

계층 위치 — server API handler 계층(정본 §E). auth_middleware Bearer 통과
(`request["user_id"]`) 후 진입하며, 적재/조회는 `messages`/`rooms` repository,
audit 는 `user_activity`, push 는 device_tokens 경로에 위임한다.

의존성 — aiohttp `web` + `request.app["db_pool"]` + `messages`/`rooms` repository
+ `user_activity`(audit) + push notification 경로 + `activity` 미들웨어.

범위 한계 — 메시지 CRUD + audit + push 트리거만. 실시간 broadcast(signaling/mesh)·
E2EE 본문 암복호는 별개 경로. delete 는 soft(body NULL tombstone).

엔드포인트 카탈로그(실 함수 5 + helper 7 + register, Bearer 검증 의무):

- `handle_list_messages_in_range`  GET    /api/messages                  — 구간 lazy.
- `handle_post_message`            POST   /api/rooms/{room_id}/messages   — INSERT+audit.
- `handle_list_room_messages`      GET    /api/rooms/{room_id}/messages   — paginated.
- `handle_get_message`             GET    /api/messages/{message_id}      — 단건.
- `handle_delete_message`          DELETE /api/messages/{message_id}      — soft delete.
- helper: `_audit_message`/`_fire_push_notification`/`_parse_int_query`/
  `_ms_to_datetime`/`_parse_path_int`/`_read_json`/`_message_row_to_wire`.

audit hook
----------
- MESSAGE_SEND — POST 시 의무. target_id = message_id +
  metadata = {room_id, kind, sender_id}.
- pool 부재 = graceful skip + 예외 swallow + log.warning.

설계 결정
---------
- 권한 검증 chain — POST = 활성 peer 검증 (room member 만 송신), DELETE = sender
  자신 또는 room owner 만, GET single/list = 활성 peer 검증.
- cleartext body INSERT 는 임시 — Phase 5 본격 cycle 의 E2EE sealed envelope
  chain 회수 의무 ([[project-phase2-remote-control-differentiator]] 외 별개).
- 모든 endpoint = parameterized SQL + 예외 swallow + auth user_id 정합.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from aiohttp import web

from server.db.repositories import messages as messages_repo
from server.db.repositories import rooms as rooms_repo
from server.db.repositories.user_activity import ActivityAction, log_activity
from server.middleware.activity import extract_client_ip

log = logging.getLogger(__name__)

# query string 의 limit default + 상한 (memory release 정합).
_DEFAULT_LIMIT = 1000
_MAX_LIMIT = 5000

# paginated list endpoint 의 default + 상한.
_PAGE_DEFAULT_LIMIT = 50
_PAGE_MAX_LIMIT = 500

# message body 의 최대 길이 (MEDIUMTEXT 의 caller-side guard).
_MAX_BODY_LEN = 65535


# ─── audit helper ───────────────────────────────────────────────────────────


async def _audit_message(
    request: web.Request,
    *,
    user_id: int,
    action: ActivityAction,
    target_id: Optional[int],
    metadata: Optional[dict] = None,
) -> None:
    """MESSAGE_* audit hook — pool 부재 graceful + 예외 swallow.

    user_activity_log INSERT 실패 시 endpoint 응답 무영향 (log.warning 만).
    """

    pool = request.app.get("db_pool")
    if pool is None:
        return
    try:
        ua = (request.headers.get("User-Agent", "") or "")[:255]
        await log_activity(
            pool,
            user_id=user_id,
            action=action,
            target_id=target_id,
            ip_address=extract_client_ip(request),
            user_agent=ua,
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "message audit 실패 user_id=%d action=%s: %s",
            user_id,
            action.value,
            exc,
        )


# ─── 헬퍼 ──────────────────────────────────────────────────────────────────


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


def _parse_path_int(request: web.Request, key: str) -> int:
    """path variable int 파싱 — 무효 = 400."""

    raw = request.match_info.get(key, "").strip()
    if not raw:
        raise web.HTTPBadRequest(reason=f"{key} 경로 변수 부재")
    try:
        val = int(raw)
    except (TypeError, ValueError) as exc:
        raise web.HTTPBadRequest(reason=f"{key} 정수 의무") from exc
    if val <= 0:
        raise web.HTTPBadRequest(reason=f"{key} 양수 의무")
    return val


async def _read_json(request: web.Request) -> dict:
    """body JSON 파싱 — 무효 = 400."""

    try:
        return await request.json()
    except Exception as exc:  # noqa: BLE001
        raise web.HTTPBadRequest(reason="JSON 파싱 실패") from exc


def _message_row_to_wire(row: Any) -> Dict[str, Any]:
    """MessageRow → JSON-safe dict (cycle 169.459 — ts_ms field 추가 사용자 directive 의 ts 정합).

    사용자 critique image #23 — client side ts_ms 부재 시점 datetime.now() fallback retain.
    server side = created_at → ts_ms (epoch ms) 명시 변환 chain.
    """
    ts_ms = 0
    if row.created_at:
        try:
            ts_ms = int(row.created_at.timestamp() * 1000)
        except Exception:
            ts_ms = 0
    return {
        "id": row.id,
        "message_id": row.id,  # cycle 169.459 — client message_id alias retain(호환)
        "room_id": row.room_id,
        "sender_id": row.sender_id,
        "kind": row.kind,
        "body": row.body,
        "file_id": row.file_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "ts_ms": ts_ms,
    }


# ─── 기존 lazy load endpoint (사이클 60) ────────────────────────────────────


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


# ─── 신규 endpoint — cycle 141 ─────────────────────────────────────────────


async def _fire_push_notification(
    request: web.Request, *, room_id: int, sender_id: int, body: str,
) -> None:
    """cycle 169.446 — 메시지 INSERT 직후 recipient push notification fan-out chain.

    DM room 안 peer (sender 아닌 의 user) 의 active device token 전수 fan-out.
    StubNotifier 활성 시점 log only — 실 FCM = service account 활성 시점.
    """
    try:
        pool = request.app.get("db_pool")
        if pool is None:
            return
        # DM room 안 sender 외 peer user_id 추출
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT user_id FROM peers WHERE room_id = %s AND user_id != %s AND left_at IS NULL",
                    (room_id, sender_id),
                )
                rows = await cur.fetchall()
        recipient_ids = [int(r[0]) for r in rows]
        if not recipient_ids:
            return
        from server.fcm import send_to_user
        preview = body[:120] if body else "(파일)"
        for uid in recipient_ids:
            await send_to_user(
                pool, user_id=uid, title="새 메시지", body=preview,
                data={"room_id": str(room_id), "sender_id": str(sender_id)},
            )
    except Exception as exc:  # noqa: BLE001
        import logging as _log
        _log.getLogger(__name__).warning("[push.fan_out] 실패 — %r", exc)


async def handle_post_message(request: web.Request) -> web.Response:
    """POST /api/rooms/{room_id}/messages — text message INSERT + MESSAGE_SEND audit.

    body = ``{body: str, kind?: "text"|"system", file_id?: str}``.
    default kind=text. sender_user_id = auth user_id (request['user_id']).
    권한 검증 = 활성 peer (room member) 또는 owner 만 허용.
    """

    user_id = request["user_id"]
    room_id = _parse_path_int(request, "room_id")
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    body_json = await _read_json(request)
    kind = (body_json.get("kind") or "text").strip()
    if kind not in ("text", "file", "system"):
        raise web.HTTPBadRequest(reason="kind = text/file/system 의무")
    msg_body = body_json.get("body")
    file_id = body_json.get("file_id")
    if kind == "text":
        if not isinstance(msg_body, str) or not msg_body.strip():
            raise web.HTTPBadRequest(reason="body 비빈 문자열 의무")
        if len(msg_body) > _MAX_BODY_LEN:
            raise web.HTTPBadRequest(
                reason=f"body 길이 {len(msg_body)} > {_MAX_BODY_LEN} 상한 초과"
            )
    elif kind == "file":
        if not isinstance(file_id, str) or len(file_id) != 32:
            raise web.HTTPBadRequest(reason="file_id 32자 hex 의무")
        msg_body = None
    elif kind == "system":
        if not isinstance(msg_body, str) or not msg_body.strip():
            raise web.HTTPBadRequest(reason="system body 의무")

    # 룸 존재 + 활성 peer (또는 owner) 검증.
    room = await rooms_repo.get_room_by_id(pool, room_id)
    if room is None:
        return web.json_response(
            {"error": "room_not_found", "room_id": room_id}, status=404
        )
    if room.status != "active":
        return web.json_response(
            {"error": "room_closed", "room_id": room_id}, status=409
        )
    peer = await rooms_repo.get_peer(pool, room_id=room_id, user_id=user_id)
    if room.owner_id != user_id and peer is None:
        return web.json_response(
            {"error": "forbidden_not_member", "room_id": room_id}, status=403
        )

    try:
        message_id = await messages_repo.insert_message(
            pool,
            room_id=room_id,
            sender_id=user_id,
            kind=kind,
            body=msg_body,
            file_id=file_id,
        )
    except ValueError as exc:
        raise web.HTTPBadRequest(reason=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception(
            "message INSERT 실패 — room_id=%d sender=%d kind=%s",
            room_id,
            user_id,
            kind,
        )
        raise web.HTTPInternalServerError(reason="message 저장 실패") from exc

    await _audit_message(
        request,
        user_id=user_id,
        action=ActivityAction.MESSAGE_SEND,
        target_id=message_id,
        metadata={
            "room_id": room_id,
            "kind": kind,
            "sender_id": user_id,
        },
    )

    # cycle 169.446 — push notification fan-out (사용자 directive 실시간 FCM)
    # 메시지 INSERT + audit 완료 직후 recipient device tokens 의 fan-out chain
    try:
        await _fire_push_notification(
            request, room_id=room_id, sender_id=user_id, body=msg_body or "",
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("[push.fire] 실패 — %r", exc)

    # created_at 의 server-side ISO 8601 응답 — client UI timeline 의 source.
    inserted = await messages_repo.get_by_id(pool, message_id)
    created_at_iso = (
        inserted.created_at.isoformat()
        if inserted and inserted.created_at
        else None
    )

    return web.json_response(
        {
            "ok": True,
            "message_id": message_id,
            "room_id": room_id,
            "sender_id": user_id,
            "kind": kind,
            "created_at": created_at_iso,
        },
        status=201,
    )


async def handle_list_room_messages(request: web.Request) -> web.Response:
    """GET /api/rooms/{room_id}/messages?limit=50&offset=0 — paginated list.

    권한 검증 = 활성 peer 또는 owner. limit + offset hybrid pagination.
    """

    user_id = request["user_id"]
    room_id = _parse_path_int(request, "room_id")
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    limit_raw = request.query.get("limit")
    if limit_raw is not None:
        try:
            limit = int(limit_raw)
        except ValueError as exc:
            raise web.HTTPBadRequest(reason="query limit int 의무") from exc
    else:
        limit = _PAGE_DEFAULT_LIMIT
    if limit <= 0 or limit > _PAGE_MAX_LIMIT:
        raise web.HTTPBadRequest(
            reason=f"limit 의 1..{_PAGE_MAX_LIMIT} 의무 — 실 {limit}"
        )

    offset_raw = request.query.get("offset")
    if offset_raw is not None:
        try:
            offset = int(offset_raw)
        except ValueError as exc:
            raise web.HTTPBadRequest(reason="query offset int 의무") from exc
    else:
        offset = 0
    if offset < 0:
        raise web.HTTPBadRequest(reason="offset 음수 불가")

    # 권한 검증 — 룸 활성 + (owner 또는 활성 peer).
    room = await rooms_repo.get_room_by_id(pool, room_id)
    if room is None:
        return web.json_response(
            {"error": "room_not_found", "room_id": room_id}, status=404
        )
    peer = await rooms_repo.get_peer(pool, room_id=room_id, user_id=user_id)
    if room.owner_id != user_id and peer is None:
        return web.json_response(
            {"error": "forbidden_not_member", "room_id": room_id}, status=403
        )

    try:
        rows = await messages_repo.list_by_room(
            pool, room_id=room_id, limit=limit, offset=offset
        )
        total = await messages_repo.count_by_room(pool, room_id)
    except ValueError as exc:
        raise web.HTTPBadRequest(reason=str(exc)) from exc

    payload: Dict[str, Any] = {
        "ok": True,
        "room_id": room_id,
        "messages": [_message_row_to_wire(r) for r in rows],
        "count": len(rows),
        "total": total,
        "limit": limit,
        "offset": offset,
    }
    return web.json_response(payload)


async def handle_get_message(request: web.Request) -> web.Response:
    """GET /api/messages/{message_id} — single message detail.

    권한 검증 = sender 자신 또는 room owner 또는 활성 peer.
    """

    user_id = request["user_id"]
    message_id = _parse_path_int(request, "message_id")
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    msg = await messages_repo.get_by_id(pool, message_id)
    if msg is None:
        return web.json_response(
            {"error": "message_not_found", "message_id": message_id}, status=404
        )

    # 권한 — sender 자신 또는 룸 owner 또는 활성 peer.
    room = await rooms_repo.get_room_by_id(pool, msg.room_id)
    if room is None:
        return web.json_response(
            {"error": "room_not_found", "room_id": msg.room_id}, status=404
        )
    peer = await rooms_repo.get_peer(pool, room_id=msg.room_id, user_id=user_id)
    if (
        msg.sender_id != user_id
        and room.owner_id != user_id
        and peer is None
    ):
        return web.json_response(
            {"error": "forbidden_not_member", "message_id": message_id},
            status=403,
        )

    return web.json_response(
        {"ok": True, "message": _message_row_to_wire(msg)}, status=200
    )


async def handle_delete_message(request: web.Request) -> web.Response:
    """DELETE /api/messages/{message_id} — soft delete (body NULL tombstone).

    권한 = sender 자신 또는 room owner 만. 그 외 = 403. 부재 = 404.
    """

    user_id = request["user_id"]
    message_id = _parse_path_int(request, "message_id")
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    msg = await messages_repo.get_by_id(pool, message_id)
    if msg is None:
        return web.json_response(
            {"error": "message_not_found", "message_id": message_id}, status=404
        )

    # sender 자신 또는 룸 owner 만 삭제 가능.
    room = await rooms_repo.get_room_by_id(pool, msg.room_id)
    if room is None:
        return web.json_response(
            {"error": "room_not_found", "room_id": msg.room_id}, status=404
        )
    if msg.sender_id != user_id and room.owner_id != user_id:
        return web.json_response(
            {"error": "forbidden_sender_or_owner_only", "message_id": message_id},
            status=403,
        )

    try:
        rowcount = await messages_repo.soft_delete(pool, message_id)
    except ValueError as exc:
        raise web.HTTPBadRequest(reason=str(exc)) from exc

    if rowcount == 0:
        return web.json_response(
            {"error": "message_not_found", "message_id": message_id}, status=404
        )

    return web.json_response(
        {"ok": True, "message_id": message_id, "deleted": True}, status=200
    )


# ─── route registration ───────────────────────────────────────────────────


def register_messages_routes(app: web.Application) -> None:
    """``server.main`` 의 register entry — 5 endpoint."""

    app.router.add_get("/api/messages", handle_list_messages_in_range)
    # cycle 141 신규 4 endpoint
    app.router.add_post(
        "/api/rooms/{room_id}/messages", handle_post_message
    )
    app.router.add_get(
        "/api/rooms/{room_id}/messages", handle_list_room_messages
    )
    app.router.add_get("/api/messages/{message_id}", handle_get_message)
    app.router.add_delete("/api/messages/{message_id}", handle_delete_message)
