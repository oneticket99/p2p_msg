# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — telegram align 연락처 + 양방향 매칭 (cycle 169.452 신설)."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web

from server.db.repositories import user_contacts as _uc_repo
from server.db.repositories import friends as _fr_repo
from server.db.repositories.rooms import find_or_create_dm_room
from server.db.repositories.messages import insert_text_message

log = logging.getLogger(__name__)


async def _attempt_bidirectional_match(
    pool: Any, *, owner_user_id: int, contact_phone: str,
) -> None:
    """owner 가 contact_phone 등록 직후 reverse match attempt.

    chain:
    1. contact_phone → users.phone 일치 matched_uid lookup (find_user_by_phone)
    2. matched_uid 부재 시점 = 미가입 — skip (signup 시점 별 chain 진입)
    3. matched_uid retain 시점 — 본 사용자 의 phone 도 matched_uid 의 contact 안 retain?
    4. 양방향 정합 시점 → friends INSERT (양측) + system message INSERT (DM room)
    """
    matched_uid = await _uc_repo.find_user_by_phone(pool, contact_phone)
    if matched_uid is None or matched_uid == owner_user_id:
        return
    # 한글 주석 — owner contact row 의 matched_user_id 갱신
    await _uc_repo.update_matched_user_id(
        pool, phone=contact_phone, matched_user_id=matched_uid,
    )
    # 한글 주석 — owner phone 가 matched 사용자 의 contact 안 retain 검증
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT phone FROM users WHERE id = %s LIMIT 1",
                (owner_user_id,),
            )
            row = await cur.fetchone()
    if row is None or not row[0]:
        return
    owner_phone = str(row[0])
    # matched 사용자 의 contact 안 owner_phone retain 검증
    reverse_owners = await _uc_repo.list_owners_with_contact(pool, phone=owner_phone)
    if matched_uid not in reverse_owners:
        log.info(
            "[contact_match] one-way only — owner=%d matched=%d (양방향 부재)",
            owner_user_id, matched_uid,
        )
        return
    # 한글 주석 — 양방향 정합 시점 friends INSERT + system message
    try:
        await _fr_repo.insert_friend(
            pool, user_id=owner_user_id, friend_user_id=matched_uid, status="accepted",
        )
    except Exception as exc:
        log.debug("[contact_match] friends INSERT (one direction) graceful — %r", exc)
    try:
        await _fr_repo.insert_friend(
            pool, user_id=matched_uid, friend_user_id=owner_user_id, status="accepted",
        )
    except Exception as exc:
        log.debug("[contact_match] friends INSERT (reverse) graceful — %r", exc)
    # 한글 주석 — DM room 생성 + system message "님이 투턱에 가입하셨습니다"
    try:
        room_id = await find_or_create_dm_room(pool, owner_user_id, matched_uid)
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COALESCE(nickname, username) AS display FROM users WHERE id = %s LIMIT 1",
                    (matched_uid,),
                )
                name_row = await cur.fetchone()
        display = str(name_row[0]) if name_row else "사용자"
        body = f"{display}님이 투턱에 가입하셨습니다."
        # 한글 주석 — sender_id = 0 (시스템) — 但 FK 정합 의무. fallback = matched_uid 의무
        await insert_text_message(
            pool, room_id=room_id, sender_id=matched_uid, body=body,
        )
        log.info(
            "[contact_match] 양방향 매칭 PASS — owner=%d matched=%d room=%d",
            owner_user_id, matched_uid, room_id,
        )
    except Exception as exc:
        log.warning("[contact_match] system message 실패 — %r", exc)


async def handle_upsert_contact(request: web.Request) -> web.Response:
    """POST /api/contacts — 단일 contact upsert + 양방향 매칭 attempt.

    body = ``{phone: str, last_name: str?, first_name: str?}``.
    응답 = ``{contact_id: int, matched_user_id: int?}``.
    """
    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    try:
        body = await request.json()
    except ValueError:
        raise web.HTTPBadRequest(reason="JSON body 의무")
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(reason="body object 의무")
    phone = str(body.get("phone", "")).strip()
    if not phone:
        raise web.HTTPBadRequest(reason="phone 빈 차단")
    last_name = body.get("last_name")
    first_name = body.get("first_name")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"error": "DB_DISABLED"}, status=503)
    try:
        contact_id = await _uc_repo.upsert_contact(
            pool, owner_user_id=user_id, phone=phone,
            last_name=last_name, first_name=first_name,
        )
    except ValueError as exc:
        raise web.HTTPBadRequest(reason=str(exc))
    # cycle 169.452 — 양방향 매칭 attempt fire (async retain — caller 응답 직후 시작)
    matched_uid = await _uc_repo.find_user_by_phone(pool, phone)
    await _attempt_bidirectional_match(
        pool, owner_user_id=user_id, contact_phone=phone,
    )
    return web.json_response({
        "contact_id": contact_id,
        "matched_user_id": matched_uid,
    }, status=201)


async def handle_list_contacts(request: web.Request) -> web.Response:
    """GET /api/contacts — owner contact 전수 list."""
    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"contacts": []})
    rows = await _uc_repo.list_contacts(pool, owner_user_id=user_id)
    payload = [
        {
            "id": r.id,
            "phone": r.phone,
            "last_name": r.last_name,
            "first_name": r.first_name,
            "matched_user_id": r.matched_user_id,
        }
        for r in rows
    ]
    return web.json_response({"contacts": payload})


def register_contacts_routes(app: web.Application) -> None:
    """server.main register entry — 2 endpoint."""
    app.router.add_post("/api/contacts", handle_upsert_contact)
    app.router.add_get("/api/contacts", handle_list_contacts)
    log.info("[api] contacts 2 endpoint 등록 완료 (cycle 169.452)")
