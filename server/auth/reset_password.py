# SPDX-License-Identifier: GPL-3.0-or-later
"""비번 재설정 use case — 이메일 OTP 비번 재설정.

흐름:
1. request_reset(email) → OTP 발급 + 이메일 발송 (purpose=password_reset)
2. consume_reset(email, otp_code, new_password) → OTP 검증 + 비번 갱신
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.security import (
    generate_otp_code,
    hash_otp,
    hash_password,
    verify_otp,
)
from server.auth.exceptions import OtpInvalid
from server.db.repositories import email_verification as otp_repo
from server.db.repositories import users as users_repo
from server.mail.smtp_client import send_otp_email

log = logging.getLogger(__name__)


async def request_password_reset(pool: Any, email: str) -> None:
    """비번 재설정 OTP 발급 + 이메일 발송.

    Notes
    -----
    email 부재 케이스 = silent success (enumeration 방어).
    """

    email_norm = email.strip().lower()
    user_row = await users_repo.get_user_by_email(pool, email_norm)

    if user_row is None:
        log.info("[reset] email 부재 — silent success email=%s", email_norm)
        return

    otp_code = generate_otp_code()
    await otp_repo.insert_otp(
        pool,
        email=email_norm,
        purpose="password_reset",
        code_hash=hash_otp(otp_code),
        ttl_seconds=180,
    )
    try:
        await send_otp_email(email_norm, otp_code, "password_reset")
    except Exception as exc:  # noqa: BLE001
        log.warning("[reset] SMTP 발송 실패 email=%s err=%r", email_norm, exc)

    log.info("[reset] OTP 발송 완료 user_id=%d email=%s", user_row.id, email_norm)


async def consume_password_reset(
    pool: Any,
    *,
    email: str,
    code: str,
    new_password: str,
) -> int:
    """OTP 검증 PASS + 비번 갱신.

    Returns
    -------
    int
        갱신된 user_id.

    Raises
    ------
    OtpInvalid
        OTP 불일치 / 만료 / 시도 초과.
    ValueError
        비번 형식 오류.
    """

    if len(new_password) < 8 or len(new_password) > 128:
        raise ValueError("비번 8~128자")

    email_norm = email.strip().lower()
    otp_row = await otp_repo.find_active_otp(
        pool, email=email_norm, purpose="password_reset"
    )
    if otp_row is None:
        raise OtpInvalid("OTP 부재 또는 만료")

    new_count = await otp_repo.increment_attempt(pool, otp_row.id)
    if new_count > 5:
        raise OtpInvalid("OTP 시도 초과")

    if not verify_otp(code, otp_row.code_hash):
        raise OtpInvalid("OTP 불일치")

    user_row = await users_repo.get_user_by_email(pool, email_norm)
    if user_row is None:
        raise OtpInvalid("사용자 부재")

    await otp_repo.consume_otp(pool, otp_row.id)
    await users_repo.update_password(pool, user_row.id, hash_password(new_password))

    log.info("[reset] 비번 갱신 완료 user_id=%d", user_row.id)
    return user_row.id
