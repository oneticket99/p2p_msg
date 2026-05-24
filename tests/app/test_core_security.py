# SPDX-License-Identifier: GPL-3.0-or-later
"""core/security unit — cycle 169.738 신설.

hash_password + verify_password + OTP + session token + constant_time_compare.
"""

from __future__ import annotations

import pytest


class TestHashPassword:
    def test_format(self) -> None:
        from app.core.security import hash_password

        h = hash_password("Passw0rd!")
        # 한글 주석 — pbkdf2_sha256$<iter>$<salt>$<hash> 4 part
        parts = h.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2_sha256"

    def test_empty_raises(self) -> None:
        from app.core.security import hash_password

        with pytest.raises(ValueError, match="password"):
            hash_password("")

    def test_unique_salt(self) -> None:
        # 한글 주석 — 동일 password 도 salt 랜덤 → 해시 다름
        from app.core.security import hash_password

        assert hash_password("same") != hash_password("same")


class TestVerifyPassword:
    def test_round_trip(self) -> None:
        from app.core.security import hash_password, verify_password

        h = hash_password("MySecret123")
        assert verify_password("MySecret123", h) is True

    def test_wrong_password(self) -> None:
        from app.core.security import hash_password, verify_password

        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_empty_inputs(self) -> None:
        from app.core.security import verify_password

        assert verify_password("", "stored") is False
        assert verify_password("pw", "") is False

    def test_malformed_stored(self) -> None:
        from app.core.security import verify_password

        assert verify_password("pw", "notvalidformat") is False
        assert verify_password("pw", "wrong$1$2") is False

    def test_non_int_iterations(self) -> None:
        from app.core.security import verify_password

        assert verify_password("pw", "pbkdf2_sha256$abc$salt$hash") is False


class TestOtp:
    def test_generate_6_digits(self) -> None:
        from app.core.security import generate_otp_code

        code = generate_otp_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_hash_otp_deterministic(self) -> None:
        from app.core.security import hash_otp

        assert hash_otp("123456") == hash_otp("123456")

    def test_verify_otp_round_trip(self) -> None:
        from app.core.security import hash_otp, verify_otp

        h = hash_otp("654321")
        assert verify_otp("654321", h) is True
        assert verify_otp("000000", h) is False

    def test_verify_otp_empty(self) -> None:
        from app.core.security import verify_otp

        assert verify_otp("", "hash") is False
        assert verify_otp("123456", "") is False


class TestSessionToken:
    def test_generate_unique(self) -> None:
        from app.core.security import generate_session_token

        assert generate_session_token() != generate_session_token()

    def test_url_safe(self) -> None:
        from app.core.security import generate_session_token

        token = generate_session_token()
        # 한글 주석 — URL-safe alphabet (A-Z a-z 0-9 - _)
        assert all(c.isalnum() or c in "-_" for c in token)
        assert len(token) > 20


class TestConstantTimeCompare:
    def test_equal(self) -> None:
        from app.core.security import constant_time_compare

        assert constant_time_compare("token123", "token123") is True

    def test_not_equal(self) -> None:
        from app.core.security import constant_time_compare

        assert constant_time_compare("token123", "token456") is False

    def test_empty(self) -> None:
        from app.core.security import constant_time_compare

        assert constant_time_compare("", "x") is False
        assert constant_time_compare("x", "") is False
