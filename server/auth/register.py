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
) -> int:
    """회원가입 — 검증 + users insert + OTP 발급 + 이메일 발송.

    Returns
    -------
    int
        신규 user.id.

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

    # 사용자 directive 회수 — email_verified flag 기반 reclaim chain.
    # 1) verified=1 row → 재 가입 절대 차단 (EmailAlreadyRegistered).
    # 2) verified=0 row → reclaim (UPDATE existing row) + prior OTP invalidate.
    # 3) row 부재 → 신규 INSERT.
    existing_email = await users_repo.get_user_by_email(pool, email_norm)
    if existing_email is not None and existing_email.email_verified:
        raise EmailAlreadyRegistered(f"email 중복 — {email_norm}")

    if existing_email is not None:
        # 한글 주석 — unverified row reclaim path. username 중복 check 시 자기 id 제외 의무.
        username_conflict = await users_repo.get_user_by_username_excluding(
            pool, username, exclude_user_id=existing_email.id
        )
        if username_conflict is not None:
            raise UsernameAlreadyTaken(f"username 중복 — {username}")

        ok = await users_repo.reclaim_unverified_user(
            pool,
            user_id=existing_email.id,
            username=username,
            password_hash=password_hash,
        )
        if not ok:
            # 한글 주석 — race condition (다른 request 가 동시 verify 완료) → 재 차단.
            raise EmailAlreadyRegistered(f"email 중복 — {email_norm}")

        # 한글 주석 — prior pending OTP 강제 무효화 (attempt_count abuse + 만료 race 차단).
        await otp_repo.invalidate_pending(pool, email=email_norm, purpose="signup")
        user_id = existing_email.id
        log.info("[register] reclaim user_id=%d email=%s username=%s", user_id, email_norm, username)
    else:
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
    try:
        await send_otp_email(email_norm, otp_code, "signup")
    except Exception as exc:  # noqa: BLE001 - SMTP 오류는 비차단 (사용자 재요청 가능)
        log.warning("[register] SMTP 발송 실패 user_id=%d email=%s err=%r", user_id, email_norm, exc)

    log.info("[register] user_id=%d email=%s username=%s OTP 발송 완료", user_id, email_norm, username)
    return user_id
