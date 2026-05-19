# SPDX-License-Identifier: GPL-3.0-or-later
"""e2e button click + auth_client mock chain (cycle 169.38 신설).

사용자 directive verbatim 회수 — qa 자동화 의무.

본격 e2e:
- qtbot.mouseClick(button) 실 simulation
- auth_client mock 안 register/login/verify chain 검증
- SignupDialog/LoginDialog/OTPDialog button qtbot chain
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QMessageBox, QPushButton
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
    def __init__(self) -> None:
        self.register_calls: list = []
        self.verify_calls: list = []
        self.login_calls: list = []

    async def register(self, email, username, password):
        self.register_calls.append((email, username, password))
        return _AuthResult(ok=True, user_id=42, next_step="verify_otp")

    async def verify_otp(self, email, code):
        self.verify_calls.append((email, code))
        return _AuthResult(ok=True, token="tok-mock", user_id=42)

    async def login(self, email, password):
        self.login_calls.append((email, password))
        return _AuthResult(ok=True, token="tok-login", user_id=42)

    async def request_reset(self, email):
        return _AuthResult(ok=True)

    async def consume_reset(self, email, code, new_password):
        return _AuthResult(ok=True)

    async def close(self) -> None:
        pass


class _OTPDialogStub:
    DialogCode = type("DC", (), {"Accepted": 1})

    def __init__(self, *args, **kwargs) -> None:
        pass

    def exec(self) -> int:
        return 1


def _find_primary_button(dialog):
    """dialog 안 variant=primary QPushButton 첫 인스턴스 반환."""
    for btn in dialog.findChildren(QPushButton):
        if btn.property("variant") == "primary":
            return btn
    return None


def _find_button_by_text(dialog, text):
    for btn in dialog.findChildren(QPushButton):
        if btn.text() == text:
            return btn
    return None


class TestSignupButtonClick:
    """SignupDialog 가입 button qtbot.mouseClick simulation."""

    def test_button_click_fires_register(self, qtbot, monkeypatch) -> None:
        from app.ui.signup_dialog import SignupDialog
        client = _MockAuthClient()
        monkeypatch.setattr("app.ui.otp_dialog.OTPDialog", _OTPDialogStub)
        dialog = SignupDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("e2e@example.com")
        dialog._username_edit.setText("e2euser")
        dialog._password_edit.setText("password123")
        dialog._password_confirm_edit.setText("password123")
        btn = _find_primary_button(dialog)
        assert btn is not None
        qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
        assert client.register_calls == [("e2e@example.com", "e2euser", "password123")]

    def test_short_password_button_click_blocks(self, qtbot, monkeypatch) -> None:
        from app.ui.signup_dialog import SignupDialog
        client = _MockAuthClient()
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
        dialog = SignupDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("e2e@example.com")
        dialog._username_edit.setText("e2euser")
        dialog._password_edit.setText("short")
        dialog._password_confirm_edit.setText("short")
        btn = _find_primary_button(dialog)
        qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
        assert client.register_calls == []


class TestLoginButtonClick:
    """LoginDialog 로그인 button qtbot.mouseClick + Enter key simulation."""

    def test_button_click_fires_login(self, qtbot) -> None:
        from app.ui.login_dialog import LoginDialog
        client = _MockAuthClient()
        dialog = LoginDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("e2e@example.com")
        dialog._password_edit.setText("password123")
        btn = _find_primary_button(dialog)
        assert btn is not None
        qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
        assert client.login_calls == [("e2e@example.com", "password123")]
        assert dialog.token == "tok-login"

    def test_enter_key_fires_login(self, qtbot) -> None:
        from app.ui.login_dialog import LoginDialog
        client = _MockAuthClient()
        dialog = LoginDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("e2e@example.com")
        dialog._password_edit.setText("password123")
        qtbot.keyClick(dialog._password_edit, Qt.Key.Key_Return)
        assert client.login_calls == [("e2e@example.com", "password123")]

    def test_signup_link_button_done_2(self, qtbot) -> None:
        from app.ui.login_dialog import LoginDialog
        client = _MockAuthClient()
        dialog = LoginDialog(auth_client=client)
        qtbot.addWidget(dialog)
        btn = _find_button_by_text(dialog, "회원가입")
        assert btn is not None
        qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
        assert dialog.result() == 2
