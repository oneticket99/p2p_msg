# SPDX-License-Identifier: GPL-3.0-or-later
"""OTP 검증 use case — 회원가입 후 3분 만료 + 5회 시도."""

from __future__ import annotations

import logging
from typing import Any

from app.core.security import verify_otp
from server.auth.exceptions import OtpInvalid
from server.db.repositories import email_verification as otp_repo
from server.db.repositories import users as users_repo

log = logging.getLogger(__name__)


async def verify_signup_otp(
    pool: Any,
    *,
    email: str,
    code: str,
) -> int:
    """signup 의 OTP 검증 — PASS 시 users.email_verified=1.

    Returns
    -------
    int
        검증 PASS 한 user_id.

    Raises
    ------
    OtpInvalid
        OTP 불일치 / 만료 / 시도 초과 / 미발급.
    """

    email_norm = email.strip().lower()

    otp_row = await otp_repo.find_active_otp(pool, email=email_norm, purpose="signup")
    if otp_row is None:
        raise OtpInvalid("OTP 부재 또는 만료")

    # attempt +1 우선 (brute force 차단)
    new_count = await otp_repo.increment_attempt(pool, otp_row.id)
    if new_count > 5:
        raise OtpInvalid("OTP 시도 초과 (5회)")

    if not verify_otp(code, otp_row.code_hash):
        raise OtpInvalid("OTP 불일치")

    # PASS — consume + users.email_verified 갱신
    await otp_repo.consume_otp(pool, otp_row.id)

    user_row = await users_repo.get_user_by_email(pool, email_norm)
    if user_row is None:
        raise OtpInvalid("사용자 부재")
    await users_repo.mark_email_verified(pool, user_row.id)

    log.info("[verify] OTP PASS user_id=%d email=%s", user_row.id, email_norm)
    # cycle 169.452 — telegram align: 가입 시점 reverse contact match propagate
    # 본 사용자 phone 을 contact 에 등록한 사용자들 의 user_contacts.matched_user_id 갱신 + 양방향 정합 시점 자동 friend + system message
    try:
        await _propagate_signup_to_contacts(pool, user_id=user_row.id)
    except Exception as exc:  # noqa: BLE001
        log.warning("[verify] contact propagate 실패 — %r", exc)
    return user_row.id


async def _propagate_signup_to_contacts(pool: Any, *, user_id: int) -> None:
    """cycle 169.452 — 신규 가입 사용자 의 phone 안 reverse contact 매칭 propagate.

    chain:
    1. user.phone 조회
    2. user_contacts WHERE phone = user.phone — 본 사용자 phone 을 contact 안 보유한 owner 전수
    3. 각 owner contact row 의 matched_user_id = user_id UPDATE
    4. 양방향 검증 (owner phone 이 user contact 안 retain) → friends INSERT + system message
    """
    from server.db.repositories import user_contacts as _uc_repo
    from server.db.repositories import friends as _fr_repo
    from server.db.repositories.rooms import find_or_create_dm_room
    from server.db.repositories.messages import insert_text_message

    # step 1 — user phone
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT phone, COALESCE(nickname, username) AS display FROM users WHERE id = %s LIMIT 1",
                (user_id,),
            )
            row = await cur.fetchone()
    if row is None or not row[0]:
        return
    user_phone = str(row[0])
    user_display = str(row[1]) if row[1] else "사용자"

    # step 2 — propagate matched_user_id
    await _uc_repo.update_matched_user_id(
        pool, phone=user_phone, matched_user_id=user_id,
    )
    # 본 사용자 phone 보유 owner 전수 조회
    owners = await _uc_repo.list_owners_with_contact(pool, phone=user_phone)
    if not owners:
        return

    # step 3+4 — 양방향 검증 + friends INSERT + system message
    for owner_id in owners:
        if owner_id == user_id:
            continue
        # owner phone 조회
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT phone FROM users WHERE id = %s LIMIT 1",
                    (owner_id,),
                )
                ow_row = await cur.fetchone()
        if ow_row is None or not ow_row[0]:
            continue
        owner_phone = str(ow_row[0])
        # 신규 사용자 contact 안 owner_phone retain 여부 검증
        reverse_owners = await _uc_repo.list_owners_with_contact(
            pool, phone=owner_phone,
        )
        if user_id not in reverse_owners:
            log.info(
                "[verify.propagate] one-way only — user=%d owner=%d (양방향 부재)",
                user_id, owner_id,
            )
            continue
        # 양방향 정합 — friends INSERT + system message
        try:
            await _fr_repo.insert_friend(
                pool, user_id=user_id, friend_user_id=owner_id, status="accepted",
            )
            await _fr_repo.insert_friend(
                pool, user_id=owner_id, friend_user_id=user_id, status="accepted",
            )
        except Exception as exc:
            log.debug("[verify.propagate] friends INSERT graceful — %r", exc)
        try:
            room_id = await find_or_create_dm_room(pool, owner_id, user_id)
            body = f"{user_display}님이 투턱에 가입하셨습니다."
            await insert_text_message(
                pool, room_id=room_id, sender_id=user_id, body=body,
            )
            log.info(
                "[verify.propagate] 양방향 매칭 PASS — user=%d owner=%d room=%d",
                user_id, owner_id, room_id,
            )
        except Exception as exc:
            log.warning("[verify.propagate] system message 실패 — %r", exc)
