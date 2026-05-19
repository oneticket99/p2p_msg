# SPDX-License-Identifier: GPL-3.0-or-later
"""OTP 재 송신 use case — 사용자 directive cycle 169.45 회수.

사용자 directive verbatim: "재송신 버튼을 누르면 otp 가 다시 안와".

Flow:
    1. email lookup → 부재 시 UserNotFound (404)
    2. email_verified=1 → EmailAlreadyVerified (409)
    3. 직전 pending OTP `created_at` < RESEND_COOLDOWN_SECONDS → RateLimitExceeded (429)
    4. invalidate_pending (prior OTP consumed_at force)
    5. 신규 OTP 발급 + send_otp_email
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.core.security import generate_otp_code, hash_otp
from server.auth.exceptions import (
    EmailAlreadyVerified,
    RateLimitExceeded,
    UserNotFound,
)
from server.db.repositories import email_verification as otp_repo
from server.db.repositories import users as users_repo
from server.mail.smtp_client import send_otp_email

log = logging.getLogger(__name__)

RESEND_COOLDOWN_SECONDS = 60  # cooldown — abuse 차단


async def resend_signup_otp(pool: Any, *, email: str) -> int:
    """OTP 재 송신 — email 검증 + cooldown + invalidate + 신규 OTP + 발송.

    Returns
    -------
    int
        user_id (audit 의무).

    Raises
    ------
    UserNotFound
        email row 부재.
    EmailAlreadyVerified
        이미 OTP 검증 완료된 사용자.
    RateLimitExceeded
        60초 cooldown 미경과.
    """

    email_norm = email.strip().lower()
    if not email_norm:
        raise UserNotFound(f"email 부재 — {email!r}")

    user = await users_repo.get_user_by_email(pool, email_norm)
    if user is None:
        raise UserNotFound(f"email 부재 — {email_norm}")
    if user.email_verified:
        raise EmailAlreadyVerified(f"이미 검증 완료 — {email_norm}")

    # 한글 주석 — 직전 pending OTP `created_at` cooldown 검증.
    # MariaDB CURRENT_TIMESTAMP = 컨테이너 TZ (Asia/Seoul) naive datetime.
    # datetime.now() no-tz 의 KST naive 정합 — abs() 안전 가드 (clock skew 차단).
    prior = await otp_repo.find_active_otp(pool, email=email_norm, purpose="signup")
    if prior is not None and prior.created_at is not None:
        now = datetime.now()
        created = prior.created_at
        if hasattr(created, "tzinfo") and created.tzinfo is not None:
            created = created.replace(tzinfo=None)
        elapsed = abs((now - created).total_seconds())
        if elapsed < RESEND_COOLDOWN_SECONDS:
            remaining = int(RESEND_COOLDOWN_SECONDS - elapsed)
            raise RateLimitExceeded(f"OTP 재 송신 cooldown — {remaining}초 대기 의무")

    # 한글 주석 — prior pending OTP 강제 무효화
    await otp_repo.invalidate_pending(pool, email=email_norm, purpose="signup")

    otp_code = generate_otp_code()
    await otp_repo.insert_otp(
        pool,
        email=email_norm,
        purpose="signup",
        code_hash=hash_otp(otp_code),
        ttl_seconds=180,
    )
    try:
        await send_otp_email(email_norm, otp_code, "signup")
    except Exception as exc:  # noqa: BLE001
        log.warning("[resend] SMTP 발송 실패 user_id=%d email=%s err=%r", user.id, email_norm, exc)
        raise

    log.info("[resend] user_id=%d email=%s OTP 재 송신 완료", user.id, email_norm)
    return user.id
