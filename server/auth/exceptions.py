# SPDX-License-Identifier: GPL-3.0-or-later
"""auth use case 의 도메인 예외 — REST 응답 매핑 의 위 base."""

from __future__ import annotations


class AuthError(Exception):
    """auth 도메인 base — caller 가 HTTP 4xx 매핑."""

    code: str = "AUTH_ERROR"
    http_status: int = 400


class EmailAlreadyRegistered(AuthError):
    """이메일 중복 (UNIQUE 위반 의 사전 검증)."""

    code = "EMAIL_DUPLICATE"
    http_status = 409


class UsernameAlreadyTaken(AuthError):
    """username 중복."""

    code = "USERNAME_DUPLICATE"
    http_status = 409


class OtpInvalid(AuthError):
    """OTP 불일치 / 만료 / 시도 초과."""

    code = "OTP_INVALID"
    http_status = 400


class InvalidCredentials(AuthError):
    """이메일 / 비번 불일치."""

    code = "INVALID_CREDENTIALS"
    http_status = 401


class EmailNotVerified(AuthError):
    """이메일 미인증 사용자 의 로그인 시도."""

    code = "EMAIL_NOT_VERIFIED"
    http_status = 403


class AccountSuspended(AuthError):
    """suspended / deleted 계정."""

    code = "ACCOUNT_SUSPENDED"
    http_status = 403


class ResetTokenInvalid(AuthError):
    """비번 재설정 토큰 무효 / 만료 / 소진."""

    code = "RESET_TOKEN_INVALID"
    http_status = 400


class UserNotFound(AuthError):
    """사용자 부재 — resend OTP / 이메일 lookup 등."""

    code = "USER_NOT_FOUND"
    http_status = 404


class RateLimitExceeded(AuthError):
    """rate limit 위반 — OTP resend cooldown 등."""

    code = "RATE_LIMIT"
    http_status = 429


class EmailAlreadyVerified(AuthError):
    """이미 검증 완료된 이메일 — resend 불필요."""

    code = "EMAIL_ALREADY_VERIFIED"
    http_status = 409
