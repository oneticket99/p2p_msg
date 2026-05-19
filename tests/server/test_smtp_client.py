# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.mail.smtp_client.build_otp_email`` 단위 테스트.

실 SMTP 전송 = integration 별도 cycle 위탁. 본 module = 메시지 빌더 만 검증.
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

    def test_default_from_address_env_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SMTP_FROM_ADDRESS 신키 → SMTP_FROM 구키 fallback 검증."""

        # SMTP_FROM_ADDRESS 부재 + SMTP_FROM 만 의 환경
        monkeypatch.delenv("SMTP_FROM_ADDRESS", raising=False)
        monkeypatch.setenv("SMTP_FROM", "alias@dopa.co.kr")
        msg = build_otp_email(
            to_email="user@example.com",
            code="111111",
            purpose="signup",
        )
        assert msg["From"] == "alias@dopa.co.kr"

    def test_default_from_address_new_key_priority(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SMTP_FROM_ADDRESS 신키 우선순위 검증 — SMTP_FROM 구키 무시."""

        monkeypatch.setenv("SMTP_FROM_ADDRESS", "new@dopa.co.kr")
        monkeypatch.setenv("SMTP_FROM", "old@dopa.co.kr")
        msg = build_otp_email(
            to_email="user@example.com",
            code="222222",
            purpose="signup",
        )
        assert msg["From"] == "new@dopa.co.kr"


class TestResolveSmtpParams:
    """_resolve_smtp_params + _resolve_from_address 환경변수 alias 검증."""

    def test_password_alias_smtp_pass_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SMTP_PASSWORD 신키 부재 시 SMTP_PASS 구키 fallback."""

        from server.mail.smtp_client import _resolve_smtp_params

        monkeypatch.delenv("SMTP_PASSWORD", raising=False)
        monkeypatch.setenv("SMTP_PASS", "old-password-123")
        _, _, _, password, _ = _resolve_smtp_params()
        assert password == "old-password-123"

    def test_password_smtp_password_priority(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SMTP_PASSWORD 신키 우선 — SMTP_PASS 구키 무시."""

        from server.mail.smtp_client import _resolve_smtp_params

        monkeypatch.setenv("SMTP_PASSWORD", "new-password-456")
        monkeypatch.setenv("SMTP_PASS", "old-password-123")
        _, _, _, password, _ = _resolve_smtp_params()
        assert password == "new-password-456"

    def test_tls_mode_default_starttls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SMTP_TLS 부재 시 STARTTLS default."""

        from server.mail.smtp_client import _resolve_smtp_params

        monkeypatch.delenv("SMTP_TLS", raising=False)
        _, _, _, _, tls_mode = _resolve_smtp_params()
        assert tls_mode == "STARTTLS"

    def test_tls_mode_smtps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SMTP_TLS=SMTPS 명시."""

        from server.mail.smtp_client import _resolve_smtp_params

        monkeypatch.setenv("SMTP_TLS", "smtps")
        _, _, _, _, tls_mode = _resolve_smtp_params()
        # upper() 정규화 검증
        assert tls_mode == "SMTPS"

    def test_host_default_mail_dopa(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SMTP_HOST default = mail.dopa.co.kr."""

        from server.mail.smtp_client import _resolve_smtp_params

        monkeypatch.delenv("SMTP_HOST", raising=False)
        host, port, _, _, _ = _resolve_smtp_params()
        assert host == "mail.dopa.co.kr"
        assert port == 587
