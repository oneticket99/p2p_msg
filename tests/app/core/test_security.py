# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.core.security`` 단위 테스트.

Phase 1 회원가입 + 이메일 OTP 정합 ([[project-auth-email-otp-required]]) 의
인증 보안 helper 검증.

검증 범위:
- PBKDF2-SHA256 해시 + 검증 round-trip + tampering 차단
- OTP 6자리 generate + zero-pad + 해시 + constant-time 검증
- session token entropy + URL-safe 형식
"""

from __future__ import annotations

import re

import pytest

from app.core.security import (
    constant_time_compare,
    generate_otp_code,
    generate_session_token,
    hash_otp,
    hash_password,
    verify_otp,
    verify_password,
)


# ---------------------------------------------------------------------------
# 1. PBKDF2 비번 해시
# ---------------------------------------------------------------------------


class TestPasswordHash:
    def test_hash_format(self) -> None:
        stored = hash_password("CorrectHorseBatteryStaple")
        # format = scheme$iter$salt$hash
        parts = stored.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2_sha256"
        # iterations = OWASP 2023 권장 600,000 이상
        assert int(parts[1]) >= 600_000
        # salt + hash = base64url no padding
        assert re.match(r"^[A-Za-z0-9_-]+$", parts[2])
        assert re.match(r"^[A-Za-z0-9_-]+$", parts[3])

    def test_hash_unique_per_call(self) -> None:
        # 같은 비번 의 의 의 의 salt 가 random — 매 호출 결과 다름
        a = hash_password("same_password")
        b = hash_password("same_password")
        assert a != b

    def test_verify_correct(self) -> None:
        password = "CorrectHorseBatteryStaple"
        stored = hash_password(password)
        assert verify_password(password, stored) is True

    def test_verify_wrong(self) -> None:
        stored = hash_password("password1")
        assert verify_password("password2", stored) is False

    def test_verify_korean_password(self) -> None:
        # 한글 비번 UTF-8 정합
        password = "안녕하세요TooTalk2026"
        stored = hash_password(password)
        assert verify_password(password, stored) is True

    def test_verify_empty_inputs(self) -> None:
        # 빈 입력 = 항상 False (raise 아님)
        assert verify_password("", "anything") is False
        assert verify_password("anything", "") is False

    def test_verify_malformed_stored(self) -> None:
        # 잘못된 형식 의 stored = False (raise 아님)
        assert verify_password("password", "not-a-hash") is False
        assert verify_password("password", "wrong$1$a$b$c$d") is False
        assert verify_password("password", "wrong$abc$salt$hash") is False

    def test_hash_empty_password_raises(self) -> None:
        with pytest.raises(ValueError, match="password 가 비었음"):
            hash_password("")


# ---------------------------------------------------------------------------
# 2. OTP 생성 + 해싱 + 검증
# ---------------------------------------------------------------------------


class TestOtp:
    def test_otp_is_6_digit_numeric(self) -> None:
        code = generate_otp_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_otp_zero_padding_preserved(self) -> None:
        # 1000회 generate 의 의 의 의 의 leading-zero OTP 등장 가능성 검증 — 모든 결과 길이 = 6
        for _ in range(200):
            code = generate_otp_code()
            assert len(code) == 6

    def test_otp_hash_deterministic(self) -> None:
        # 같은 평문 → 같은 hash (constant-time 비교 가능)
        assert hash_otp("123456") == hash_otp("123456")

    def test_otp_hash_different_per_code(self) -> None:
        assert hash_otp("123456") != hash_otp("123457")

    def test_otp_hash_is_sha256_hex(self) -> None:
        h = hash_otp("123456")
        # SHA-256 hex = 64자
        assert len(h) == 64
        assert re.match(r"^[0-9a-f]{64}$", h)

    def test_verify_otp_correct(self) -> None:
        code = "123456"
        stored = hash_otp(code)
        assert verify_otp(code, stored) is True

    def test_verify_otp_wrong(self) -> None:
        stored = hash_otp("123456")
        assert verify_otp("654321", stored) is False

    def test_verify_otp_empty_inputs(self) -> None:
        assert verify_otp("", "anything") is False
        assert verify_otp("anything", "") is False


# ---------------------------------------------------------------------------
# 3. 세션 토큰
# ---------------------------------------------------------------------------


class TestSessionToken:
    def test_token_format_url_safe(self) -> None:
        token = generate_session_token()
        # URL-safe base64 = A-Z a-z 0-9 - _ (padding `=` 없음 — secrets.token_urlsafe 정합)
        assert re.match(r"^[A-Za-z0-9_-]+$", token)

    def test_token_entropy(self) -> None:
        # 32 byte entropy → base64url 약 43자
        token = generate_session_token()
        assert len(token) >= 32

    def test_token_unique(self) -> None:
        # 100회 generate 의 의 의 의 의 collision 없음 (256 bit entropy)
        tokens = {generate_session_token() for _ in range(100)}
        assert len(tokens) == 100


# ---------------------------------------------------------------------------
# 4. constant_time_compare
# ---------------------------------------------------------------------------


class TestConstantTimeCompare:
    def test_equal_strings(self) -> None:
        assert constant_time_compare("abc123", "abc123") is True

    def test_different_strings(self) -> None:
        assert constant_time_compare("abc123", "abc124") is False

    def test_different_length(self) -> None:
        assert constant_time_compare("short", "much_longer") is False

    def test_empty_inputs(self) -> None:
        assert constant_time_compare("", "any") is False
        assert constant_time_compare("any", "") is False
