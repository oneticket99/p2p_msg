# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.mail.smtp_client.build_otp_email`` 단위 테스트.

실 SMTP 전송 = integration 의 의 의 의 의 의 별도 cycle 위탁. 본 module = 메시지 빌더 만 검증.
"""

from __future__ import annotations

import pytest

from server.mail.smtp_client import build_otp_email


class TestBuildOtpEmail:
    def test_signup_email(self) -> None:
        msg = build_otp_email(
            to_email="user@example.com",
            code="123456",
            purpose="signup",
            from_email="no-reply@tootalk.example",
        )
        assert msg["To"] == "user@example.com"
        assert msg["From"] == "no-reply@tootalk.example"
        assert "회원가입" in msg["Subject"]
        body = msg.get_content()
        assert "123456" in body
        assert "3분" in body

    def test_password_reset_email(self) -> None:
        msg = build_otp_email(
            to_email="user@example.com",
            code="987654",
            purpose="password_reset",
        )
        assert "비밀번호" in msg["Subject"]
        assert "987654" in msg.get_content()

    def test_unknown_purpose_raises(self) -> None:
        with pytest.raises(ValueError, match="purpose"):
            build_otp_email(
                to_email="x@y.com",
                code="000000",
                purpose="invalid",
            )

    def test_utf8_korean_body(self) -> None:
        msg = build_otp_email(
            to_email="user@example.com",
            code="555555",
            purpose="signup",
        )
        # 한글 본문 UTF-8 정합
        body = msg.get_content()
        assert "TooTalk" in body
        assert "인증코드" in body
