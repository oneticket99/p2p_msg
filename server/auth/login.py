# SPDX-License-Identifier: GPL-3.0-or-later
"""로그인 use case — 이메일 + 비번 검증 + 세션 토큰 발급."""

from __future__ import annotations

import logging
from typing import Any, Tuple

from app.core.security import generate_session_token, verify_password
from server.auth.exceptions import (
    AccountSuspended,
    EmailNotVerified,
    InvalidCredentials,
)
from server.db.repositories import users as users_repo

log = logging.getLogger(__name__)


async def login_user(
    pool: Any,
    *,
    email: str,
    password: str,
) -> Tuple[int, str]:
    """로그인 — PASS 시 (user_id, session_token) 반환.

    Returns
    -------
    tuple[int, str]
        (user_id, session_token).

    Raises
    ------
    InvalidCredentials
        email 부재 또는 비번 불일치.
    EmailNotVerified
        OTP 미검증 사용자.
    AccountSuspended
        suspended / deleted 계정.
    """

    email_norm = email.strip().lower()
    user_row = await users_repo.get_user_by_email(pool, email_norm)

    # constant-time — 의
    if user_row is None or not verify_password(password, user_row.password_hash):
        raise InvalidCredentials("이메일 또는 비번 불일치")

    if user_row.status != "active":
        raise AccountSuspended(f"status={user_row.status}")

    if not user_row.email_verified:
        raise EmailNotVerified("이메일 OTP 미검증")

    token = generate_session_token()
    await users_repo.update_last_login(pool, user_row.id)

    log.info("[login] user_id=%d email=%s PASS", user_row.id, email_norm)
    return (user_row.id, token)
