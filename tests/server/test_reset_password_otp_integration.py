# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 1 cycle 131 — request_password_reset 의 send_otp_email actual call chain integration 검증.

mock SMTP 환경에서 send_otp_email 호출 인자 정합:
- 1번 arg = email_norm (소문자 normalize)
- 2번 arg = 6자리 숫자 OTP
- 3번 arg = "password_reset" purpose

email 부재 케이스 silent success (send_otp_email 호출 차단) + SMTP 실패
graceful 처리 (raise 차단 + warning log emit) 검증.
"""

from __future__ import annotations

import logging
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.auth.reset_password import request_password_reset

# 한글 주석: request_password_reset 가 import 한 의존성 3종 patch 경로 상수
_P_EMAIL = "server.auth.reset_password.users_repo.get_user_by_email"
_P_INS_OTP = "server.auth.reset_password.otp_repo.insert_otp"
_P_SEND = "server.auth.reset_password.send_otp_email"


def _user_row(*, user_id: int = 99) -> MagicMock:
    """한글 주석: user_row mock — .id attribute 노출."""
    row = MagicMock()
    row.id = user_id
    return row


class TestResetPasswordOtpCallArgs:
    """send_otp_email 호출 인자 정합 검증 (3 test)."""

    @pytest.mark.asyncio
    async def test_send_otp_called_once_with_reset_purpose(self) -> None:
        # 한글 주석: 정상 경로 — send_otp_email 1회 호출 + purpose=password_reset
        m_email = AsyncMock(return_value=_user_row(user_id=99))
        m_ins_otp = AsyncMock(return_value=1)
        m_send = AsyncMock()
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            await request_password_reset(None, "alice@example.com")
        m_send.assert_called_once()
        assert m_send.call_args.args[2] == "password_reset"

    @pytest.mark.asyncio
    async def test_otp_code_is_six_digit_numeric(self) -> None:
        # 한글 주석: 2번 arg = 6자리 숫자 OTP code 정합
        m_email = AsyncMock(return_value=_user_row(user_id=101))
        m_ins_otp = AsyncMock(return_value=1)
        m_send = AsyncMock()
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            await request_password_reset(None, "bob@example.com")
        m_send.assert_called_once()
        otp_code = m_send.call_args.args[1]
        assert isinstance(otp_code, str)
        assert re.fullmatch(r"\d{6}", otp_code) is not None

    @pytest.mark.asyncio
    async def test_email_normalized_lowercase_in_send_call(self) -> None:
        # 한글 주석: 입력 mixed-case → send_otp_email 1번 arg 소문자 normalize
        m_email = AsyncMock(return_value=_user_row(user_id=103))
        m_ins_otp = AsyncMock(return_value=1)
        m_send = AsyncMock()
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            await request_password_reset(None, "User@Example.COM")
        m_send.assert_called_once()
        assert m_send.call_args.args[0] == "user@example.com"
        # 한글 주석: get_user_by_email 또한 normalized email 인자로 호출
        assert m_email.call_args.args[1] == "user@example.com"


class TestResetPasswordUserNotFound:
    """email 부재 케이스 silent success (1 test)."""

    @pytest.mark.asyncio
    async def test_user_not_found_smtp_not_called(self) -> None:
        # 한글 주석: get_user_by_email → None → send_otp_email 호출 차단
        m_email = AsyncMock(return_value=None)
        m_ins_otp = AsyncMock(return_value=1)
        m_send = AsyncMock()
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            result = await request_password_reset(None, "ghost@example.com")
        assert result is None
        m_send.assert_not_called()
        m_ins_otp.assert_not_called()


class TestResetPasswordSmtpFailure:
    """SMTP 실패 graceful 처리 + insert_otp kwargs 정합 (3 test)."""

    @pytest.mark.asyncio
    async def test_smtp_exception_does_not_propagate(self) -> None:
        # 한글 주석: send_otp_email 가 raise → request_password_reset 정상 반환
        m_email = AsyncMock(return_value=_user_row(user_id=201))
        m_ins_otp = AsyncMock(return_value=1)
        m_send = AsyncMock(side_effect=RuntimeError("SMTP connection refused"))
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            result = await request_password_reset(None, "dave@example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_smtp_failure_emits_warning_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # 한글 주석: SMTP 실패 시 WARNING level log emit 검증
        m_email = AsyncMock(return_value=_user_row(user_id=203))
        m_ins_otp = AsyncMock(return_value=1)
        m_send = AsyncMock(side_effect=RuntimeError("SMTP timeout"))
        caplog.set_level(logging.WARNING, logger="server.auth.reset_password")
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            await request_password_reset(None, "eve@example.com")
        warnings = [
            rec for rec in caplog.records
            if rec.levelno == logging.WARNING and "SMTP" in rec.getMessage()
        ]
        assert len(warnings) >= 1

    @pytest.mark.asyncio
    async def test_insert_otp_purpose_and_ttl_kwargs(self) -> None:
        # 한글 주석: insert_otp kwargs — purpose=password_reset + ttl_seconds=180 정합
        m_email = AsyncMock(return_value=_user_row(user_id=205))
        m_ins_otp = AsyncMock(return_value=1)
        m_send = AsyncMock()
        with (
            patch(_P_EMAIL, new=m_email),
            patch(_P_INS_OTP, new=m_ins_otp),
            patch(_P_SEND, new=m_send),
        ):
            await request_password_reset(None, "heidi@example.com")
        m_ins_otp.assert_called_once()
        kwargs = m_ins_otp.call_args.kwargs
        assert kwargs.get("purpose") == "password_reset"
        assert kwargs.get("ttl_seconds") == 180
        assert kwargs.get("email") == "heidi@example.com"
        assert "code_hash" in kwargs
