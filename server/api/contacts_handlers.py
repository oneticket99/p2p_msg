# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — telegram align 연락처 + 양방향 매칭 (cycle 169.452 신설).

역할 — 사용자가 등록한 전화번호 연락처를 영속화하고, 같은 번호를 서로 등록한
두 가입자를 자동으로 친구 연결하는 양방향 매칭(telegram align)을 수행한다.

계층 위치 — server API handler 계층(정본 §E). auth_middleware Bearer 통과 후
진입하며, 영속화는 `user_contacts`/`friends`/`rooms`/`messages` repository 에
위임한다(다중 repository 조율 = handler 책임).

의존성 — aiohttp `web` + `request.app["db_pool"]` + repository 4종
(`user_contacts`/`friends` + `rooms.find_or_create_dm_room` +
`messages.insert_text_message`).

범위 한계 — 연락처 CRUD + 매칭 트리거만. 가입 시점(signup)의 역방향 매칭은
별도 chain, 실시간 친구 추가 알림 push 는 push 경로 담당. 매칭 부작용(친구
INSERT·시스템 메시지)은 best-effort(graceful) — 실패해도 연락처 등록은 성공.

엔드포인트 카탈로그(실 함수 2 + 매칭 helper + register):
- `handle_upsert_contact`  POST /api/contacts — 연락처 UPSERT + 매칭 attempt.
- `handle_list_contacts`   GET  /api/contacts — owner 연락처 전수.
- `_attempt_bidirectional_match` — 양방향 정합 시 친구 INSERT + 시스템 메시지.
- `register_contacts_routes` — server.main 등록 entry.
"""

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
    """owner 가 contact_phone 등록 직후 역방향 매칭 시도.

    의도 — 두 가입자가 서로의 번호를 연락처로 등록했을 때만 자동 친구 연결한다
    (단방향 등록은 연결하지 않음 — 상호 동의 근사).

    chain:
    1. contact_phone → users.phone 일치 matched_uid lookup (find_user_by_phone)
    2. matched_uid 부재 = 미가입 — skip (가입 시점의 별도 chain 이 처리)
    3. matched_uid 존재 — owner 의 phone 도 matched_uid 의 연락처에 있는지 검증
    4. 양방향 정합 시 → friends INSERT (양측) + system message INSERT (DM room)

    Parameters — pool(DB), owner_user_id(등록 주체), contact_phone(등록된 번호).
    Returns — None(트리거 함수).
    부작용 — `user_contacts.matched_user_id` UPDATE + (양방향 정합 시) friends
        양측 INSERT + DM room find/create + 시스템 메시지 INSERT. 각 단계 best-effort
        (예외는 debug/warning 로그로 삼킴 — 연락처 등록 자체는 영향 없음).
    """
    matched_uid = await _uc_repo.find_user_by_phone(pool, contact_phone)
    if matched_uid is None or matched_uid == owner_user_id:
        return
    # owner 연락처 row 에 matched_user_id 역참조 갱신(이후 UI 가 가입 여부 표시)
    await _uc_repo.update_matched_user_id(
        pool, phone=contact_phone, matched_user_id=matched_uid,
    )
    # 양방향 판정 위해 owner 의 phone 을 조회 — matched 사용자 연락처에 들어있는지 확인
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
    # matched 사용자 연락처에 owner_phone 이 들어있는 owner 목록 — matched_uid 포함 여부가 양방향 조건
    reverse_owners = await _uc_repo.list_owners_with_contact(pool, phone=owner_phone)
    if matched_uid not in reverse_owners:
        log.info(
            "[contact_match] one-way only — owner=%d matched=%d (양방향 부재)",
            owner_user_id, matched_uid,
        )
        return
    # 양방향 정합 확정 — 친구 관계를 양측 모두 INSERT(한 방향 실패해도 다른 방향 진행)
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
    # DM room 확보 후 "가입 알림" 시스템 메시지 1건 적재(양측 대화 시작점 제공)
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
        # sender_id 는 FK 정합 의무라 0(시스템) 불가 — matched_uid 를 발신자로 사용
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

    인증 — Bearer 의무(401).
    검증 순서 — (1) user_id 유효 → (2) JSON body 파싱 → (3) body=dict →
    (4) phone 비어있지 않음 → (5) db_pool 가용(부재 503).

    Parameters — body ``{phone: str, last_name: str?, first_name: str?}``.
    Returns — 201 + ``{contact_id: int, matched_user_id: int?}``(매칭된 가입자 id).
    Raises — HTTPUnauthorized / HTTPBadRequest(body·phone 위반) / repository
        ValueError → HTTPBadRequest. db_pool 부재 503.
    부작용 — `user_contacts` UPSERT + `_attempt_bidirectional_match` 트리거
        (양방향 정합 시 friends 양측 + 시스템 메시지, best-effort).
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
    """GET /api/contacts — owner contact 전수 list.

    의도 — 연락처 화면 + 가입 여부(matched_user_id) 표시 데이터를 제공한다.
    인증 — Bearer 의무(401). db_pool 부재 시 빈 목록(graceful).
    Returns — 200 + ``{contacts: [{id, phone, last_name, first_name, matched_user_id}]}``.
    부작용 — 부재(읽기 전용 SELECT).
    """
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
