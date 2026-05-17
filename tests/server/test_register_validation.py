# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.auth.register`` 검증 함수 단위 테스트.

실 DB 통합 = tests/integration/ 의 별도 cycle. 본 module = 형식 검증 만.
"""

from __future__ import annotations

import pytest

from server.auth.register import (
    _validate_email,
    _validate_password,
    _validate_username,
)


class TestEmailValidation:
    def test_valid_email_lowercase(self) -> None:
        assert _validate_email("user@example.com") == "user@example.com"

    def test_email_normalized_lowercase(self) -> None:
        # 대문자 → 소문자 normalize
        assert _validate_email("User@Example.COM") == "user@example.com"

    def test_email_stripped(self) -> None:
        assert _validate_email("  user@example.com  ") == "user@example.com"

    @pytest.mark.parametrize(
        "bad",
        ["no-at-sign", "@nodomain.com", "user@", "user @example.com", ""],
    )
    def test_invalid_email(self, bad: str) -> None:
        with pytest.raises(ValueError):
            _validate_email(bad)

    def test_email_length_limit(self) -> None:
        # 256자 초과 차단
        long_email = "a" * 250 + "@x.com"
        with pytest.raises(ValueError):
            _validate_email(long_email)


class TestUsernameValidation:
    def test_alphanumeric(self) -> None:
        assert _validate_username("alice123") == "alice123"

    def test_korean(self) -> None:
        assert _validate_username("앨리스") == "앨리스"

    def test_underscore(self) -> None:
        assert _validate_username("alice_bob") == "alice_bob"

    @pytest.mark.parametrize(
        "bad",
        ["", "with space", "with-dash", "with.dot", "x" * 65],
    )
    def test_invalid(self, bad: str) -> None:
        with pytest.raises(ValueError):
            _validate_username(bad)


class TestPasswordValidation:
    def test_min_length(self) -> None:
        # 8자 정확 = PASS (raise 없음)
        _validate_password("abcd1234")

    def test_long_korean_password(self) -> None:
        _validate_password("안녕하세요TooTalk2026")

    def test_too_short(self) -> None:
        with pytest.raises(ValueError, match="최소 8자"):
            _validate_password("short7")

    def test_too_long(self) -> None:
        with pytest.raises(ValueError, match="최대 128자"):
            _validate_password("x" * 129)
