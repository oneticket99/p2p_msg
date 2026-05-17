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
    return user_row.id
