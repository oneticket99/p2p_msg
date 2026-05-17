# SPDX-License-Identifier: GPL-3.0-or-later
"""인증 보안 유틸 — 비번 해시 + OTP 생성/검증 + 세션 토큰.

본 모듈 = Phase 1 회원가입 + 이메일 OTP 정합 ([[project-auth-email-otp-required]])
의 핵심 helper. 외부 IO 없음 — 순수 함수 + secrets / hashlib / hmac 만.

함수:

- ``hash_password`` — PBKDF2-SHA256 + 16 byte salt (NIST SP800-132)
- ``verify_password`` — constant-time 비교 (hmac.compare_digest)
- ``generate_otp_code`` — 6자리 numeric OTP (secrets.randbelow)
- ``hash_otp`` — OTP 평문 → DB 저장용 hash
- ``generate_session_token`` — URL-safe random token 32 byte
- ``constant_time_compare`` — 일반 string constant-time 비교

비번 해시 포맷: ``pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>``.
역 호환성 = iterations 변경 시 해시 본문에 명시 — verify 시점에서 추출.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from typing import Final

# PBKDF2 iterations — OWASP 2023 권장 (SHA-256 = 600,000 이상)
_PBKDF2_ITERATIONS: Final[int] = 600_000
_PBKDF2_SALT_BYTES: Final[int] = 16
_PBKDF2_HASH_NAME: Final[str] = "sha256"
_PBKDF2_KEY_LEN: Final[int] = 32

_OTP_DIGITS: Final[int] = 6
_OTP_MAX: Final[int] = 10 ** _OTP_DIGITS  # 1,000,000 (000000~999999)

_SESSION_TOKEN_BYTES: Final[int] = 32

_HASH_SCHEME: Final[str] = "pbkdf2_sha256"


# ---------------------------------------------------------------------------
# 비번 해시 / 검증
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """비번 평문 → PBKDF2 해시 문자열.

    반환 형식: ``pbkdf2_sha256$<iter>$<salt_b64>$<hash_b64>`` (db 저장 직접).
    salt = 16 byte 랜덤, iterations = 600,000 (OWASP 2023).

    Raises
    ------
    ValueError
        password 가 빈 문자열인 경우.
    """

    if not password:
        raise ValueError("password 가 비었음 — 회원가입 시 필수 필드")

    salt = secrets.token_bytes(_PBKDF2_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        _PBKDF2_HASH_NAME,
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
        dklen=_PBKDF2_KEY_LEN,
    )
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    hash_b64 = base64.urlsafe_b64encode(derived).decode("ascii").rstrip("=")
    return f"{_HASH_SCHEME}${_PBKDF2_ITERATIONS}${salt_b64}${hash_b64}"


def verify_password(password: str, stored: str) -> bool:
    """비번 평문 vs DB 저장 해시 검증 — constant-time 비교.

    Parameters
    ----------
    password : str
        사용자 입력 비번 평문.
    stored : str
        ``hash_password`` 가 반환한 형식의 DB 저장 문자열.

    Returns
    -------
    bool
        일치 = True, 불일치 또는 형식 오류 = False.
    """

    if not password or not stored:
        return False

    parts = stored.split("$")
    if len(parts) != 4 or parts[0] != _HASH_SCHEME:
        return False

    try:
        iterations = int(parts[1])
    except ValueError:
        return False

    # b64 padding 복원 (rstrip("=") 의 역)
    salt = _b64_decode_padding(parts[2])
    expected = _b64_decode_padding(parts[3])
    if salt is None or expected is None:
        return False

    derived = hashlib.pbkdf2_hmac(
        _PBKDF2_HASH_NAME,
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=len(expected),
    )
    return hmac.compare_digest(derived, expected)


def _b64_decode_padding(raw: str) -> bytes | None:
    """``rstrip("=")`` 한 b64 의 padding 복원 + 디코딩. 실패 = None."""

    pad = "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(raw + pad)
    except (ValueError, base64.binascii.Error):  # type: ignore[attr-defined]
        return None


# ---------------------------------------------------------------------------
# OTP 생성 / 해싱
# ---------------------------------------------------------------------------


def generate_otp_code() -> str:
    """6자리 numeric OTP 평문 생성 (000000~999999, zero-padded).

    secrets.randbelow 사용 — `random` 의 비-암호 PRNG 회피.
    """

    code = secrets.randbelow(_OTP_MAX)
    return f"{code:0{_OTP_DIGITS}d}"


def hash_otp(code: str) -> str:
    """OTP 평문 → SHA-256 hex (DB 저장 + 검증 constant-time 비교).

    OTP = 짧은 6자리 정수 — brute force timing attack 방어 = 해시 후 비교.
    PBKDF2 같이 무거운 KDF 미사용 (만료 3분 + try count 제한 의 의 의 의 의 의 충분).
    """

    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def verify_otp(code: str, stored_hash: str) -> bool:
    """OTP 평문 vs 저장된 hex 해시 constant-time 비교."""

    if not code or not stored_hash:
        return False
    actual = hash_otp(code)
    return hmac.compare_digest(actual, stored_hash)


# ---------------------------------------------------------------------------
# 세션 토큰
# ---------------------------------------------------------------------------


def generate_session_token() -> str:
    """URL-safe 세션 토큰 생성 — 32 byte (256 bit entropy).

    DB ``sessions.token`` 컬럼 저장. 클라이언트 cookie / keychain 보관.
    """

    return secrets.token_urlsafe(_SESSION_TOKEN_BYTES)


def constant_time_compare(a: str, b: str) -> bool:
    """일반 string constant-time 비교 (timing attack 방어).

    토큰 검증 + OTP 검증 외 케이스 (예: 이메일 verification link) 용도.
    """

    if not a or not b:
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
