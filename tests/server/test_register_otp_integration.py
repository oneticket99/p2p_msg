# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 1 cycle 131 — register_user 의 send_otp_email actual call chain integration 검증.

mock SMTP 환경에서 send_otp_email 호출 인자 정합:
- 1번 arg = email_norm (소문자 normalize)
- 2번 arg = 6자리 숫자 OTP
- 3번 arg = "signup" purpose

SMTP 실패 graceful 처리 (raise 차단 + warning log emit) + insert_user 가
insert_otp 보다 먼저 호출되는 순서 정합 검증.
"""

from __future__ import annotations

import logging
import re
from unittest.mock import AsyncMock, patch

import pytest

from server.auth.register import register_user

# 한글 주석: register_user 가 import 한 의존성 5종 patch 경로 상수
_P_EMAIL = "server.auth.register.users_repo.get_user_by_email"
_P_UNAME = "server.auth.register.users_repo.get_user_by_username"
_P_INS_USR = "server.auth.register.users_repo.insert_user"
_P_INS_OTP = "server.auth.register.otp_repo.insert_otp"
_P_SEND = "server.auth.register.send_otp_email"


def _repo_mocks(*, user_id: int = 42) -> tuple[AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    """한글 주석: 4개 repo async mock 생성 helper.

    - get_user_by_email → None (중복 부재)
    - get_user_by_username → None (중복 부재)
    - insert_user → user_id 반환
    - insert_otp → 1 (affected rows) 반환
    """
    return (
        AsyncMock(return_value=None),
        AsyncMock(return_value=None),
        AsyncMock(return_value=user_id),
        AsyncMock(return_value=1),
    )


class TestRegisterOtpCallArgs:
    """send_otp_email 호출 인자 정합 검증 (3 test)."""

    @pytest.mark.asyncio
    async def test_send_otp_called_once_with_signup_purpose(self) -> None:
        # 한글 주석: 정상 경로 — send_otp_email 1회 호출 + purpose=signup
        m_email, m_uname, m_ins_usr, m_ins_otp = _repo_mocks(user_id=42)
        m_send = AsyncMock()
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_UNAME, new=m_uname),
            patch(_P_INS_USR, new=m_ins_usr),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            user_id = await register_user(
                None,
                email="alice@example.com",
                username="alice",
                password="secret123",
            )
        assert user_id == 42
        m_send.assert_called_once()
        # 한글 주석: 3번 arg = purpose
        assert m_send.call_args.args[2] == "signup"

    @pytest.mark.asyncio
    async def test_otp_code_is_six_digit_numeric(self) -> None:
        # 한글 주석: 2번 arg = 6자리 숫자 OTP code 정합
        m_email, m_uname, m_ins_usr, m_ins_otp = _repo_mocks(user_id=7)
        m_send = AsyncMock()
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_UNAME, new=m_uname),
            patch(_P_INS_USR, new=m_ins_usr),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            await register_user(
                None,
                email="bob@example.com",
                username="bob",
                password="password1",
            )
        m_send.assert_called_once()
        otp_code = m_send.call_args.args[1]
        assert isinstance(otp_code, str)
        assert re.fullmatch(r"\d{6}", otp_code) is not None

    @pytest.mark.asyncio
    async def test_email_normalized_lowercase_in_send_call(self) -> None:
        # 한글 주석: 입력 mixed-case → send_otp_email 1번 arg 소문자 normalize
        m_email, m_uname, m_ins_usr, m_ins_otp = _repo_mocks(user_id=9)
        m_send = AsyncMock()
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_UNAME, new=m_uname),
            patch(_P_INS_USR, new=m_ins_usr),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            await register_user(
                None,
                email="User@Example.COM",
                username="carol",
                password="secret123",
            )
        m_send.assert_called_once()
        assert m_send.call_args.args[0] == "user@example.com"


class TestRegisterOtpSmtpFailure:
    """SMTP 실패 graceful 처리 검증 (3 test)."""

    @pytest.mark.asyncio
    async def test_smtp_exception_does_not_propagate(self) -> None:
        # 한글 주석: send_otp_email 가 raise → register_user 는 정상 반환
        m_email, m_uname, m_ins_usr, m_ins_otp = _repo_mocks(user_id=11)
        m_send = AsyncMock(side_effect=RuntimeError("SMTP connection refused"))
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_UNAME, new=m_uname),
            patch(_P_INS_USR, new=m_ins_usr),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            user_id = await register_user(
                None,
                email="dave@example.com",
                username="dave",
                password="secret123",
            )
        assert user_id == 11

    @pytest.mark.asyncio
    async def test_smtp_failure_emits_warning_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # 한글 주석: SMTP 실패 시 WARNING level log emit 검증
        m_email, m_uname, m_ins_usr, m_ins_otp = _repo_mocks(user_id=13)
        m_send = AsyncMock(side_effect=RuntimeError("SMTP timeout"))
        caplog.set_level(logging.WARNING, logger="server.auth.register")
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_UNAME, new=m_uname),
            patch(_P_INS_USR, new=m_ins_usr),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            await register_user(
                None,
                email="eve@example.com",
                username="eve",
                password="secret123",
            )
        warnings = [
            rec for rec in caplog.records
            if rec.levelno == logging.WARNING and "SMTP" in rec.getMessage()
        ]
        assert len(warnings) >= 1

    @pytest.mark.asyncio
    async def test_smtp_failure_send_otp_called_once(self) -> None:
        # 한글 주석: SMTP 실패 케이스 또한 send_otp_email 1회 호출 정합
        m_email, m_uname, m_ins_usr, m_ins_otp = _repo_mocks(user_id=17)
        m_send = AsyncMock(side_effect=ConnectionError("network unreachable"))
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_UNAME, new=m_uname),
            patch(_P_INS_USR, new=m_ins_usr),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            await register_user(
                None,
                email="frank@example.com",
                username="frank",
                password="secret123",
            )
        m_send.assert_called_once()


class TestRegisterOtpInsertChain:
    """insert_user → insert_otp 호출 순서 + 인자 정합 (2 test)."""

    @pytest.mark.asyncio
    async def test_insert_user_before_insert_otp(self) -> None:
        # 한글 주석: insert_user 호출 직후 insert_otp 호출 순서 정합
        call_order: list[str] = []
        m_email = AsyncMock(return_value=None)
        m_uname = AsyncMock(return_value=None)

        async def _ins_usr(*args: object, **kwargs: object) -> int:
            call_order.append("insert_user")
            return 23

        async def _ins_otp(*args: object, **kwargs: object) -> int:
            call_order.append("insert_otp")
            return 1

        m_send = AsyncMock()
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_UNAME, new=m_uname),
            patch(_P_INS_USR, new=_ins_usr),
            patch(_P_INS_OTP, new=_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            await register_user(
                None,
                email="grace@example.com",
                username="grace",
                password="secret123",
            )
        assert call_order == ["insert_user", "insert_otp"]

    @pytest.mark.asyncio
    async def test_insert_otp_purpose_and_ttl_kwargs(self) -> None:
        # 한글 주석: insert_otp kwargs — purpose=signup + ttl_seconds=180 정합
        m_email, m_uname, m_ins_usr, m_ins_otp = _repo_mocks(user_id=29)
        m_send = AsyncMock()
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_UNAME, new=m_uname),
            patch(_P_INS_USR, new=m_ins_usr),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            await register_user(
                None,
                email="heidi@example.com",
                username="heidi",
                password="secret123",
            )
        m_ins_otp.assert_called_once()
        kwargs = m_ins_otp.call_args.kwargs
        assert kwargs.get("purpose") == "signup"
        assert kwargs.get("ttl_seconds") == 180
        assert kwargs.get("email") == "heidi@example.com"
        assert "code_hash" in kwargs
