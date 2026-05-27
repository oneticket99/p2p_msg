# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — 친구 관계 CRUD (cycle 144 신설).

역할 — 친구 관계의 조회·검색·요청·수락·거절·차단·제거를 처리한다. 관계는
단방향 row 모델이며 수락 시 역방향 row 를 동기 생성한다. 모든 변경은 audit.

계층 위치 — server API handler 계층(정본 §E). auth_middleware Bearer 통과
(`request["user_id"]`) 후 진입하며, SQL 은 본 module 안에서 직접 실행한다. audit
는 `user_activity`, IP 는 `activity` 미들웨어.

의존성 — aiohttp `web` + `request.app["db_pool"]` + `user_activity`
(`log_activity`/`ActivityAction`) + `activity`(`extract_client_ip`).

범위 한계 — 친구 관계 CRUD + audit 만. 친구 추천·group/folder 분류·활동 통계는
별개 영역. self 친구 차단은 본 module 검증 분기.

엔드포인트 카탈로그(실 함수 8 + helper 4 + register, Bearer 검증 의무):

- `handle_list_friends`    GET    /api/friends                  — 전체 관계 목록.
- `handle_list_pending`    GET    /api/friends/pending          — 수신 pending.
- `handle_search_user`     GET    /api/friends/search           — username LIKE.
- `handle_request_friend`  POST   /api/friends                  — 요청 발신.
- `handle_accept_friend`   POST   /api/friends/{user_id}/accept — 수락(역 row).
- `handle_reject_friend`   POST   /api/friends/{user_id}/reject — 거절.
- `handle_block_friend`    POST   /api/friends/{user_id}/block  — 차단.
- `handle_remove_friend`   DELETE /api/friends/{user_id}        — 제거(양방향).
- helper: `_audit_friend`/`_read_json`/`_parse_user_id`/`_friend_with_profile_to_wire`.

audit hook
----------
- FRIEND_REQUEST / FRIEND_ACCEPT / FRIEND_REJECT / FRIEND_BLOCK / FRIEND_REMOVE
  의 5 ENUM 정합 (DDL 0007 확장).
- pool 부재 = graceful skip + 예외 swallow + log.warning.

설계 결정
---------
- 단방향 row 모델 — 요청 시 owner → peer 1 row 만 신규 (peer → owner = 별개).
- 수락 시 reverse row INSERT — owner 수락 + peer accepted row 동기 생성.
- 자기 자신 친구 차단 — handle_request_friend 의 검증.
- 모든 endpoint = parameterized SQL + 예외 swallow.

본 module 범위 외
----------------
- 친구 추천 알고리즘 — Phase 5+ 별개.
- 친구 group/folder 분류 — Phase 5+ 별개.
- 친구 활동 통계 (DAU/MAU) — 별개 분석 영역.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from aiohttp import web

from server.db.repositories import friends as friends_repo
from server.db.repositories.user_activity import ActivityAction, log_activity
from server.middleware.activity import extract_client_ip

log = logging.getLogger(__name__)


# ─── audit helper ───────────────────────────────────────────────────────────


async def _audit_friend(
    request: web.Request,
    *,
    user_id: int,
    action: ActivityAction,
    target_id: Optional[int],
    metadata: Optional[dict] = None,
) -> None:
    """FRIEND_* audit hook — pool 부재 graceful + 예외 swallow."""

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
            "friend audit 실패 user_id=%d action=%s: %s",
            user_id,
            action.value,
            exc,
        )


# ─── helper ─────────────────────────────────────────────────────────────────


async def _read_json(request: web.Request) -> dict:
    """body JSON 파싱 — 무효 = 400."""

    try:
        return await request.json()
    except Exception as exc:  # noqa: BLE001
        raise web.HTTPBadRequest(reason="JSON 파싱 실패") from exc


def _parse_user_id(request: web.Request) -> int:
    """path variable user_id 정수 파싱 — 무효 = 400."""

    raw = request.match_info.get("user_id", "").strip()
    if not raw:
        raise web.HTTPBadRequest(reason="user_id 경로 변수 부재")
    try:
        uid = int(raw)
    except (TypeError, ValueError) as exc:
        raise web.HTTPBadRequest(reason="user_id 정수 의무") from exc
    if uid <= 0:
        raise web.HTTPBadRequest(reason="user_id 양수 의무")
    return uid


def _friend_with_profile_to_wire(row: Any) -> dict:
    """FriendWithProfile → JSON-safe dict."""

    return {
        "id": row.id,
        "user_id": row.user_id,
        "friend_user_id": row.friend_user_id,
        "status": row.status,
        "nickname": row.nickname,
        "requested_at": (
            row.requested_at.isoformat() if row.requested_at else None
        ),
        "accepted_at": (
            row.accepted_at.isoformat() if row.accepted_at else None
        ),
        "friend_username": row.friend_username,
        "friend_email_verified": bool(row.friend_email_verified),
    }


# ─── handlers ───────────────────────────────────────────────────────────────


async def handle_list_friends(request: web.Request) -> web.Response:
    """GET /api/friends — 친구 list (pending + accepted + blocked).

    removed status = 본 list 부재. caller 의 history 조회 = 별개 endpoint.
    """

    user_id = request["user_id"]
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    rows = await friends_repo.list_by_user(pool, user_id)
    return web.json_response(
        {
            "ok": True,
            "user_id": user_id,
            "friends": [_friend_with_profile_to_wire(r) for r in rows],
            "count": len(rows),
        }
    )


async def handle_list_pending(request: web.Request) -> web.Response:
    """GET /api/friends/pending — user_id 가 수신자 인 pending 요청 list."""

    user_id = request["user_id"]
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    rows = await friends_repo.list_pending_requests(pool, user_id)
    return web.json_response(
        {
            "ok": True,
            "user_id": user_id,
            "pending": [_friend_with_profile_to_wire(r) for r in rows],
            "count": len(rows),
        }
    )


async def handle_search_user(request: web.Request) -> web.Response:
    """GET /api/friends/search?q=keyword&limit=20 — username 부분 매칭 검색.

    keyword 길이 >= 2 의무 (성능 + privacy). limit 50 cap.
    """

    user_id = request["user_id"]
    keyword = (request.query.get("q") or "").strip()
    if len(keyword) < 2:
        raise web.HTTPBadRequest(reason="검색 keyword 2자 이상 의무")
    try:
        limit = int(request.query.get("limit", "20"))
    except ValueError as exc:
        raise web.HTTPBadRequest(reason="limit 정수 의무") from exc
    limit = max(1, min(limit, 50))

    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    results = await friends_repo.search_users_by_username(
        pool, keyword=keyword, limit=limit
    )
    # 자기 PK 제외 — 자기 자신 친구 차단 의 사전 필터.
    filtered = [r for r in results if r["id"] != user_id]
    return web.json_response(
        {
            "ok": True,
            "keyword": keyword,
            "results": filtered,
            "count": len(filtered),
        }
    )


async def handle_request_friend(request: web.Request) -> web.Response:
    """POST /api/friends — 친구 요청 발신.

    body = ``{user_id: int, nickname?: str}``. self-add 차단 + 중복 차단 (409).
    """

    user_id = request["user_id"]
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    body = await _read_json(request)
    target_id = body.get("user_id")
    nickname = body.get("nickname")
    if not isinstance(target_id, int) or target_id <= 0:
        raise web.HTTPBadRequest(reason="user_id 양수 정수 의무")
    if target_id == user_id:
        raise web.HTTPBadRequest(reason="자기 자신 친구 차단")
    if nickname is not None and not isinstance(nickname, str):
        raise web.HTTPBadRequest(reason="nickname 문자열 의무")
    if isinstance(nickname, str):
        nickname = nickname.strip()[:64]
        if not nickname:
            nickname = None

    # 이미 관계 row 가용 시 409 — caller 의 reconcile 의무.
    existing = await friends_repo.get_friend(
        pool, user_id=user_id, friend_user_id=target_id
    )
    if existing is not None and existing.status in ("pending", "accepted", "blocked"):
        return web.json_response(
            {"error": "already_exists", "status": existing.status}, status=409
        )

    try:
        if existing is not None and existing.status == "removed":
            # removed → pending 재요청 — UPDATE 경로 + nickname 갱신.
            await friends_repo.update_status(
                pool,
                user_id=user_id,
                friend_user_id=target_id,
                new_status="pending",
            )
            if nickname is not None:
                await friends_repo.set_nickname(
                    pool,
                    user_id=user_id,
                    friend_user_id=target_id,
                    nickname=nickname,
                )
            friend_id = existing.id
        else:
            friend_id = await friends_repo.insert_friend(
                pool,
                user_id=user_id,
                friend_user_id=target_id,
                status="pending",
                nickname=nickname,
            )
    except Exception as exc:  # noqa: BLE001
        log.exception(
            "friend 요청 실패 — user_id=%d target=%d", user_id, target_id
        )
        raise web.HTTPInternalServerError(reason="friend 요청 실패") from exc

    await _audit_friend(
        request,
        user_id=user_id,
        action=ActivityAction.FRIEND_REQUEST,
        target_id=target_id,
        metadata={"friend_id": friend_id, "nickname": nickname},
    )

    return web.json_response(
        {
            "ok": True,
            "id": friend_id,
            "user_id": user_id,
            "friend_user_id": target_id,
            "status": "pending",
        },
        status=201,
    )


async def handle_accept_friend(request: web.Request) -> web.Response:
    """POST /api/friends/{user_id}/accept — pending → accepted 수락.

    user_id 경로 = 발신자 PK (request 의 friend_user_id). 수락 후 reverse row
    INSERT (accepted 양방향 완성).
    """

    user_id = request["user_id"]
    sender_id = _parse_user_id(request)
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    # pending row 의 친구 = (sender_id → user_id). 수락 = user_id row
    # 의 자기 자신 가입 — friends.user_id = user_id, friend_user_id = sender_id.
    # 본 DB schema 의 row = sender → receiver 단방향. 수락 시 receiver → sender
    # row 의 별개 INSERT (accepted 양방향).
    rowcount = await friends_repo.accept_friend(
        pool, user_id=sender_id, friend_user_id=user_id
    )
    if rowcount == 0:
        return web.json_response(
            {"error": "pending_not_found", "sender_id": sender_id}, status=404
        )

    # reverse direction row INSERT — receiver → sender accepted.
    existing_reverse = await friends_repo.get_friend(
        pool, user_id=user_id, friend_user_id=sender_id
    )
    if existing_reverse is None:
        try:
            await friends_repo.insert_friend(
                pool,
                user_id=user_id,
                friend_user_id=sender_id,
                status="accepted",
                nickname=None,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "reverse friend row INSERT 실패 — user_id=%d sender=%d: %s",
                user_id,
                sender_id,
                exc,
            )
    else:
        await friends_repo.update_status(
            pool,
            user_id=user_id,
            friend_user_id=sender_id,
            new_status="accepted",
        )

    await _audit_friend(
        request,
        user_id=user_id,
        action=ActivityAction.FRIEND_ACCEPT,
        target_id=sender_id,
        metadata=None,
    )

    # cycle 169.832 — 수락 시점 DM room + system message 생성 (요청→수락 시점 이동).
    # 기존 instant-accept 가 요청 시점에 만들던 DM room/notify 를 정식 수락 시점으로 옮겨
    # pending 단계에 DM 이 미리 생기던 부정합을 제거한다.
    room_id = 0
    try:
        from server.db.repositories.rooms import find_or_create_dm_room
        from server.db.repositories.messages import insert_text_message
        room_id = await find_or_create_dm_room(pool, user_id, sender_id)
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COALESCE(nickname, username) AS display FROM users WHERE id = %s LIMIT 1",
                    (user_id,),
                )
                row = await cur.fetchone()
        accepter_display = str(row[0]) if row else "사용자"
        await insert_text_message(
            pool,
            room_id=room_id,
            sender_id=user_id,
            body=f"{accepter_display}님이 친구 요청을 수락했습니다. 이제 대화를 시작할 수 있어요.",
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("[friends accept] DM room/system msg 생성 실패 — %r", exc)

    return web.json_response(
        {"ok": True, "sender_id": sender_id, "user_id": user_id, "room_id": room_id},
        status=200,
    )


async def handle_reject_friend(request: web.Request) -> web.Response:
    """POST /api/friends/{user_id}/reject — pending → removed 거절.

    user_id 경로 = 발신자 PK. enumeration 방어 = 부재 시 404.
    """

    user_id = request["user_id"]
    sender_id = _parse_user_id(request)
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    rowcount = await friends_repo.update_status(
        pool, user_id=sender_id, friend_user_id=user_id, new_status="removed"
    )
    if rowcount == 0:
        return web.json_response(
            {"error": "pending_not_found", "sender_id": sender_id}, status=404
        )

    await _audit_friend(
        request,
        user_id=user_id,
        action=ActivityAction.FRIEND_REJECT,
        target_id=sender_id,
        metadata=None,
    )

    return web.json_response(
        {"ok": True, "sender_id": sender_id}, status=200
    )


async def handle_block_friend(request: web.Request) -> web.Response:
    """POST /api/friends/{user_id}/block — 친구 차단 (status=blocked).

    기존 관계 부재 시 = blocked 상태 의 신규 row INSERT.
    """

    user_id = request["user_id"]
    target_id = _parse_user_id(request)
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    if target_id == user_id:
        raise web.HTTPBadRequest(reason="자기 자신 차단 부재")

    existing = await friends_repo.get_friend(
        pool, user_id=user_id, friend_user_id=target_id
    )
    if existing is None:
        await friends_repo.insert_friend(
            pool,
            user_id=user_id,
            friend_user_id=target_id,
            status="blocked",
        )
    else:
        await friends_repo.update_status(
            pool,
            user_id=user_id,
            friend_user_id=target_id,
            new_status="blocked",
        )

    await _audit_friend(
        request,
        user_id=user_id,
        action=ActivityAction.FRIEND_BLOCK,
        target_id=target_id,
        metadata=None,
    )

    return web.json_response(
        {"ok": True, "target_id": target_id, "status": "blocked"}, status=200
    )


async def handle_remove_friend(request: web.Request) -> web.Response:
    """DELETE /api/friends/{user_id} — 친구 관계 제거 (status=removed).

    soft delete — history 보존. 양방향 row 동시 갱신.
    """

    user_id = request["user_id"]
    target_id = _parse_user_id(request)
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    rowcount = await friends_repo.update_status(
        pool, user_id=user_id, friend_user_id=target_id, new_status="removed"
    )
    # 양방향 동시 정리 — peer row 가용 시 removed 갱신.
    await friends_repo.update_status(
        pool, user_id=target_id, friend_user_id=user_id, new_status="removed"
    )

    if rowcount == 0:
        return web.json_response(
            {"error": "friend_not_found", "target_id": target_id}, status=404
        )

    await _audit_friend(
        request,
        user_id=user_id,
        action=ActivityAction.FRIEND_REMOVE,
        target_id=target_id,
        metadata=None,
    )

    return web.json_response(
        {"ok": True, "target_id": target_id}, status=200
    )


def register_friends_routes(app: web.Application) -> None:
    """aiohttp Application 에 friends 8 endpoint 등록 (cycle 144)."""

    app.router.add_get("/api/friends", handle_list_friends)
    app.router.add_get("/api/friends/pending", handle_list_pending)
    app.router.add_get("/api/friends/search", handle_search_user)
    app.router.add_post("/api/friends", handle_request_friend)
    app.router.add_post(
        "/api/friends/{user_id}/accept", handle_accept_friend
    )
    app.router.add_post(
        "/api/friends/{user_id}/reject", handle_reject_friend
    )
    app.router.add_post(
        "/api/friends/{user_id}/block", handle_block_friend
    )
    app.router.add_delete("/api/friends/{user_id}", handle_remove_friend)
    log.info("[api] friends 8 endpoint 등록 완료 (cycle 144)")
