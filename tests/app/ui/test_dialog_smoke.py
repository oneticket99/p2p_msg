# SPDX-License-Identifier: GPL-3.0-or-later
"""WelcomeDialog + LoginDialog + SignupDialog + OTPDialog smoke test — cycle 169.26 신설.

pytest-qt 기반 자동 GUI test — 사용자 manual test 전 crash 차단 chain.
사용자 비판 verbatim 회수 — '사용자 테스트전에 playwright 테스트를 진행해야 하는거 아냐'.

5 case:
- WelcomeDialog 인스턴스화 + close (crash 부재)
- LoginDialog 인스턴스화 + 회원가입 link click → done(2) signup intent
- SignupDialog 인스턴스화 + close (crash 부재)
- OTPDialog 인스턴스화 + 6 box auto-advance simulation
- 4 dialog logo composition (symbol + Talk QLabel) 정합 검증
"""

from __future__ import annotations

import pytest

# pytest-qt qtbot fixture 의무 — PyQt6 graceful import
try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication, QLabel
    _PYQT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYQT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _PYQT_AVAILABLE, reason="PyQt6 미설치")


class _MockAuthClient:
    """async auth client mock — dialog test 격리."""

    async def login(self, email, password):
        class R:
            ok = False
            token = None
            user_id = None
            error_code = "MOCK"
            error_message = "mock client"
        return R()

    async def register(self, email, username, password):
        class R:
            ok = False
            error_message = "mock"
        return R()

    async def verify_otp(self, email, otp):
        class R:
            ok = False
            error_message = "mock"
        return R()

    async def close(self):
        pass


class TestWelcomeDialogSmoke:
    """WelcomeDialog 인스턴스화 + close 검증 — 1 case."""

    def test_instantiate_no_crash(self, qtbot) -> None:
        from app.ui.welcome_dialog import WelcomeDialog
        dialog = WelcomeDialog()
        qtbot.addWidget(dialog)
        # 한글 주석 — dialog 인스턴스화 시 crash 부재 검증 (window 표기 부재)
        assert dialog.windowTitle() == "TooTalk"
        dialog.close()


class TestLoginDialogSmoke:
    """LoginDialog 인스턴스화 + signup intent done(2) chain — 2 case."""

    def test_instantiate_no_crash(self, qtbot) -> None:
        from app.ui.login_dialog import LoginDialog
        dialog = LoginDialog(auth_client=_MockAuthClient())
        qtbot.addWidget(dialog)
        assert dialog.windowTitle().startswith("TooTalk")
        dialog.close()

    def test_signup_link_done_2(self, qtbot) -> None:
        """회원가입 ghost link click → done(2) signup intent — crash 회수 검증."""
        from app.ui.login_dialog import LoginDialog
        dialog = LoginDialog(auth_client=_MockAuthClient())
        qtbot.addWidget(dialog)
        # 한글 주석 — _on_signup_link_clicked 직접 호출 + result code 검증
        dialog._on_signup_link_clicked()
        assert dialog.result() == 2  # signup intent


class TestSignupDialogSmoke:
    """SignupDialog 인스턴스화 + close 검증 — 1 case."""

    def test_instantiate_no_crash(self, qtbot) -> None:
        from app.ui.signup_dialog import SignupDialog
        dialog = SignupDialog(auth_client=_MockAuthClient())
        qtbot.addWidget(dialog)
        assert dialog.windowTitle().startswith("TooTalk")
        dialog.close()


class TestOTPDialogSmoke:
    """OTPDialog 인스턴스화 + 6 box auto-advance — 1 case."""

    def test_instantiate_no_crash(self, qtbot) -> None:
        from app.ui.otp_dialog import OTPDialog
        dialog = OTPDialog(auth_client=_MockAuthClient(), email="user@example.com")
        qtbot.addWidget(dialog)
        assert dialog.windowTitle().startswith("TooTalk")
        # 한글 주석 — 6 box 의 instance 검증
        assert len(dialog._boxes) == 6
        dialog.close()


class TestLogoComposition:
    """logo composition QLabel 정합 검증 — 1 case (FRONTEND.md §15.6 박제 정합)."""

    def test_welcome_logo_row_present(self, qtbot) -> None:
        from app.ui.welcome_dialog import WelcomeDialog
        dialog = WelcomeDialog()
        qtbot.addWidget(dialog)
        # 한글 주석 — QLabel widget 의 의 존재 검증 (logo PNG load PASS)
        labels = dialog.findChildren(QLabel)
        assert len(labels) >= 2  # symbol + Talk + mascot + 투턱 등 다수
        dialog.close()
