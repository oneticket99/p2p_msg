# SPDX-License-Identifier: GPL-3.0-or-later
"""회원가입 use case — email + username + password 검증 + OTP 발송.

[[project-auth-email-otp-required]] 정합 — 회원가입 직후 email_verified=0,
OTP 검증 PASS 시 verify_otp.py mark_email_verified.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.security import (
    generate_otp_code,
    hash_otp,
    hash_password,
)
from server.auth.exceptions import (
    EmailAlreadyRegistered,
    EmailRaceVerified,
    UsernameAlreadyTaken,
)
from server.db.repositories import email_verification as otp_repo
from server.db.repositories import users as users_repo
from server.mail.smtp_client import send_otp_email

log = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9가-힣_]{1,64}$")


def _validate_email(email: str) -> str:
    """이메일 형식 검증 + 소문자 normalize."""

    normalized = email.strip().lower()
    if not _EMAIL_RE.match(normalized):
        raise ValueError(f"이메일 형식 오류 — email={email!r}")
    if len(normalized) > 255:
        raise ValueError("이메일 길이 초과 (255자 상한)")
    return normalized


def _validate_username(username: str) -> str:
    """username 형식 검증 — 1~64자 영문/한글/숫자/underscore."""

    if not _USERNAME_RE.match(username):
        raise ValueError(f"username 형식 오류 — value={username!r}")
    return username


def _validate_password(password: str) -> None:
    """비번 길이 + 복잡도 검증 (최소 8자, 영문 + 숫자 권장)."""

    if len(password) < 8:
        raise ValueError("비번 최소 8자")
    if len(password) > 128:
        raise ValueError("비번 최대 128자")


async def register_user(
    pool: Any,
    *,
    email: str,
    username: str,
    password: str,
) -> dict:
    """회원가입 — 검증 + users insert + OTP 발급 + 이메일 발송.

    cycle 169.67 회수 — return value 의 dict 확장 (reviewer H-2 + M-3 회수):
    - user_id
    - reclaimed: bool (cycle 169.42 reclaim path 분기)
    - smtp_status: "sent" / "deferred" (SMTP 실패 graceful 가시성)

    Raises
    ------
    ValueError
        형식 검증 실패.
    EmailAlreadyRegistered / UsernameAlreadyTaken
        UNIQUE 위반.
    """

    email_norm = _validate_email(email)
    _validate_username(username)
    _validate_password(password)

    password_hash = hash_password(password)

    # 사용자 directive 회수 — email_verified flag 기반 reclaim chain (H-1 + M-2 atomic 회수).
    # 1) verified=1 row → 재 가입 절대 차단 (EmailAlreadyRegistered).
    # 2) verified=0 row → 단일 transaction reclaim (SELECT FOR UPDATE + invalidate + UPDATE).
    # 3) row 부재 → 신규 INSERT path (별도 username 중복 check).
    status, reclaimed_id = await users_repo.reclaim_unverified_user_atomic(
        pool,
        email=email_norm,
        username=username,
        password_hash=password_hash,
    )

    if status == "verified":
        raise EmailAlreadyRegistered(f"email 중복 — {email_norm}")
    if status == "username_conflict":
        raise UsernameAlreadyTaken(f"username 중복 — {username}")

    reclaimed = (status == "reclaimed")
    if status == "reclaimed":
        user_id = int(reclaimed_id) if reclaimed_id is not None else 0
        log.info("[register] reclaim user_id=%d email=%s username=%s", user_id, email_norm, username)
    else:
        # status == "absent" → 신규 INSERT path
        existing_username = await users_repo.get_user_by_username(pool, username)
        if existing_username is not None:
            raise UsernameAlreadyTaken(f"username 중복 — {username}")

        user_id = await users_repo.insert_user(
            pool,
            email=email_norm,
            username=username,
            password_hash=password_hash,
        )

    # OTP 발급 + 이메일 발송
    otp_code = generate_otp_code()
    await otp_repo.insert_otp(
        pool,
        email=email_norm,
        purpose="signup",
        code_hash=hash_otp(otp_code),
        ttl_seconds=180,
    )
    smtp_status = "sent"
    try:
        await send_otp_email(email_norm, otp_code, "signup")
    except Exception as exc:  # noqa: BLE001 - SMTP 오류는 비차단 (사용자 재요청 가능)
        log.warning("[register] SMTP 발송 실패 user_id=%d email=%s err=%r", user_id, email_norm, exc)
        smtp_status = "deferred"

    log.info("[register] user_id=%d email=%s username=%s OTP 발송=%s", user_id, email_norm, username, smtp_status)
    return {"user_id": user_id, "reclaimed": reclaimed, "smtp_status": smtp_status}
