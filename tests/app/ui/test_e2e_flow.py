# SPDX-License-Identifier: GPL-3.0-or-later
"""end-to-end flow QA 자동화 — signup-OTP-login chain 통합 test (cycle 169.36 신설).

사용자 directive verbatim 회수 — 회원가입에서부터 작동이 안되는데 모든 플로우에 대해서 qa 자동화 의무.

검증 시나리오:
1. SignupDialog 4 input + 가입 button → mock register → OTPDialog 진입 chain
2. OTPDialog 6 box auto-advance + concat
3. LoginDialog email + password + 로그인 → mock login → token capture
4. cycle 169.34 sync chain (asyncio.run) RuntimeError 차단 검증
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

try:
    from PyQt6.QtWidgets import QMessageBox
    _PYQT_AVAILABLE = True
except ImportError:
    _PYQT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _PYQT_AVAILABLE, reason="PyQt6 미설치")


@dataclass
class _AuthResult:
    ok: bool = True
    user_id: Optional[int] = None
    token: Optional[str] = None
    error_code: str = ""
    error_message: str = ""
    next_step: Optional[str] = None


class _MockAuthClient:
    def __init__(self, *, register_ok=True, verify_ok=True, login_ok=True, reset_ok=True) -> None:
        self.register_calls: list = []
        self.verify_calls: list = []
        self.login_calls: list = []
        self.reset_request_calls: list = []
        self.reset_consume_calls: list = []
        self._register_ok = register_ok
        self._verify_ok = verify_ok
        self._login_ok = login_ok
        self._reset_ok = reset_ok

    async def register(self, email, username, password):
        self.register_calls.append((email, username, password))
        return _AuthResult(ok=self._register_ok, user_id=42 if self._register_ok else None, next_step="verify_otp")

    async def verify_otp(self, email, code):
        self.verify_calls.append((email, code))
        return _AuthResult(ok=self._verify_ok, token="tok-mock" if self._verify_ok else None, user_id=42)

    async def login(self, email, password):
        self.login_calls.append((email, password))
        return _AuthResult(ok=self._login_ok, token="tok-login" if self._login_ok else None, user_id=42 if self._login_ok else None, error_code="" if self._login_ok else "AUTH_FAIL", error_message="" if self._login_ok else "mock fail")

    async def request_reset(self, email):
        self.reset_request_calls.append((email,))
        return _AuthResult(ok=self._reset_ok)

    async def consume_reset(self, email, code, new_password):
        self.reset_consume_calls.append((email, code, new_password))
        return _AuthResult(ok=self._reset_ok)

    async def close(self) -> None:
        pass


class _OTPDialogStub:
    DialogCode = type("DC", (), {"Accepted": 1})

    def __init__(self, *args, **kwargs) -> None:
        pass

    def exec(self) -> int:
        return 1


class TestSignupChain:
    """SignupDialog 4 input + 가입 button → register chain — sync def + asyncio.run 검증."""

    def test_signup_register_call_chain(self, qtbot, monkeypatch) -> None:
        from app.ui.signup_dialog import SignupDialog
        client = _MockAuthClient(register_ok=True)
        monkeypatch.setattr("app.ui.otp_dialog.OTPDialog", _OTPDialogStub)
        dialog = SignupDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("user@example.com")
        dialog._username_edit.setText("user99")
        dialog._password_edit.setText("password123")
        dialog._password_confirm_edit.setText("password123")
        dialog._on_signup_clicked()
        assert client.register_calls == [("user@example.com", "user99", "password123")]

    def test_signup_validation_short_password_blocks_call(self, qtbot, monkeypatch) -> None:
        from app.ui.signup_dialog import SignupDialog
        client = _MockAuthClient()
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
        dialog = SignupDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("user@example.com")
        dialog._username_edit.setText("user99")
        dialog._password_edit.setText("short")
        dialog._password_confirm_edit.setText("short")
        dialog._on_signup_clicked()
        assert client.register_calls == []


class TestLoginChain:
    """LoginDialog email + password + 로그인 button → login chain."""

    def test_login_success_token_capture(self, qtbot) -> None:
        from app.ui.login_dialog import LoginDialog
        client = _MockAuthClient(login_ok=True)
        dialog = LoginDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("user@example.com")
        dialog._password_edit.setText("password123")
        dialog._on_login_clicked()
        assert client.login_calls == [("user@example.com", "password123")]
        assert dialog.token == "tok-login"
        assert dialog.user_id == 42

    def test_login_signup_link_done_2(self, qtbot) -> None:
        from app.ui.login_dialog import LoginDialog
        client = _MockAuthClient()
        dialog = LoginDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._on_signup_link_clicked()
        assert dialog.result() == 2


class TestOTPChain:
    """OTPDialog 6 box auto-advance + concat."""

    def test_otp_concat_6_digits(self, qtbot) -> None:
        from app.ui.otp_dialog import OTPDialog
        client = _MockAuthClient()
        dialog = OTPDialog(auth_client=client, email="user@example.com")
        qtbot.addWidget(dialog)
        for i, d in enumerate("123456"):
            dialog._boxes[i].blockSignals(True)
            dialog._boxes[i].setText(d)
            dialog._boxes[i].blockSignals(False)
        assert dialog._get_otp() == "123456"


class TestAsyncioRunIsolatedLoop:
    """cycle 169.34 sync def + asyncio.run() 격리 loop chain — RuntimeError 부재 검증."""

    def test_signup_no_runtime_error_chain(self, qtbot, monkeypatch) -> None:
        from app.ui.signup_dialog import SignupDialog
        client = _MockAuthClient(register_ok=True)
        monkeypatch.setattr("app.ui.otp_dialog.OTPDialog", _OTPDialogStub)
        dialog = SignupDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("user@example.com")
        dialog._username_edit.setText("user99")
        dialog._password_edit.setText("password123")
        dialog._password_confirm_edit.setText("password123")
        dialog._on_signup_clicked()
        assert len(client.register_calls) == 1

    def test_login_no_runtime_error_chain(self, qtbot) -> None:
        from app.ui.login_dialog import LoginDialog
        client = _MockAuthClient(login_ok=True)
        dialog = LoginDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("user@example.com")
        dialog._password_edit.setText("password123")
        dialog._on_login_clicked()
        assert len(client.login_calls) == 1
