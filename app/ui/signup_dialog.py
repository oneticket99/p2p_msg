# SPDX-License-Identifier: GPL-3.0-or-later
"""SignupDialog — email + username + password + OTP 검증 (cycle 153 phase 2 redesign).

Toonation BI 통합 — logo icon top + Toonation primary CTA + brand 색상.
정합 = FRONTEND.md §15 + telegram-ui-survey.md §2 + OTPDialog (cycle 153 phase 2).

Flow:
    1. email + username + password + confirm 입력 → AuthClient.register
    2. signup PASS → OTPDialog 진입 chain
    3. OTP PASS → accept()
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.net.auth_client import AuthClient

log = logging.getLogger(__name__)
_tr = lambda src: QCoreApplication.translate("MainWindow", src)

_ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "branding" / "tootalk_symbol.png"


class SignupDialog(QDialog):
    """회원가입 dialog — email + username + password + OTPDialog chain."""

    def __init__(self, auth_client: AuthClient, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._client = auth_client
        self._email: Optional[str] = None

        self.setWindowTitle(f"TooTalk · {_tr('회원가입')}")
        self.setMinimumWidth(440)
        self.setMinimumHeight(560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(14)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 한글 주석 — symbol + Talk QHBoxLayout 합성 복원 (cycle 169.16)
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_row.setSpacing(0)
        logo_row.setContentsMargins(0, 0, 0, 0)

        symbol_label = QLabel()
        symbol_label.setStyleSheet("background: transparent;")
        symbol_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        if _ICON_PATH.is_file():
            pixmap = QPixmap(str(_ICON_PATH))
            scaled = pixmap.scaledToHeight(50, Qt.TransformationMode.SmoothTransformation)
            symbol_label.setPixmap(scaled)
        logo_row.addWidget(symbol_label)

        talk_label = QLabel("Talk")
        talk_label.setStyleSheet(
            "background: transparent;"
            " color: #ffffff;"
            " font-family: -apple-system, 'SF Pro Display', 'Inter', sans-serif;"
            " font-size: 55px;"
            " font-weight: 700;"
            " letter-spacing: -1px;"
        )
        logo_row.addWidget(talk_label)
        outer.addLayout(logo_row)

        title = QLabel(_tr("투턱 회원가입"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("background: transparent; color: #e5e7eb; font-size: 22px; font-weight: 700;")
        outer.addWidget(title)

        sub = QLabel(_tr("email + username + password 의무"))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #9ca3af; font-size: 13px;")
        outer.addWidget(sub)

        outer.addSpacing(16)

        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("user@example.com")
        self._email_edit.setMinimumHeight(44)
        outer.addWidget(self._email_edit)

        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText(_tr("username (영문 3~16자)"))
        self._username_edit.setMinimumHeight(44)
        outer.addWidget(self._username_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText(_tr("password (8~32자)"))
        self._password_edit.setMinimumHeight(44)
        outer.addWidget(self._password_edit)

        self._password_confirm_edit = QLineEdit()
        self._password_confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_confirm_edit.setPlaceholderText(_tr("password 확인"))
        self._password_confirm_edit.setMinimumHeight(44)
        outer.addWidget(self._password_confirm_edit)

        outer.addSpacing(8)

        btn_signup = QPushButton(_tr("가입 + OTP 송신"))
        btn_signup.setProperty("variant", "primary")
        btn_signup.setMinimumHeight(44)
        btn_signup.clicked.connect(self._on_signup_clicked)  # type: ignore[arg-type]
        outer.addWidget(btn_signup)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton(_tr("취소"))
        btn_cancel.setProperty("variant", "ghost")
        btn_cancel.setFlat(True)
        btn_cancel.clicked.connect(self.reject)  # type: ignore[arg-type]

        btn_login_link = QPushButton(_tr("로그인"))
        btn_login_link.setProperty("variant", "ghost")
        btn_login_link.setFlat(True)
        btn_login_link.clicked.connect(self.reject)  # type: ignore[arg-type]

        btn_row.addWidget(btn_cancel)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_login_link)
        outer.addLayout(btn_row)

        self._password_confirm_edit.returnPressed.connect(self._on_signup_clicked)  # type: ignore[arg-type]

    @property
    def email(self) -> Optional[str]:
        return self._email

    def _on_signup_clicked(self) -> None:
        email = self._email_edit.text().strip()
        username = self._username_edit.text().strip()
        password = self._password_edit.text()
        confirm = self._password_confirm_edit.text()

        if not email or not username or not password:
            QMessageBox.warning(self, "TooTalk", _tr("4 field 모두 입력 의무"))
            return
        if password != confirm:
            QMessageBox.warning(self, "TooTalk", _tr("password 확인 mismatch"))
            return
        if len(password) < 8 or len(password) > 32:
            QMessageBox.warning(self, "TooTalk", _tr("password 8~32자 의무"))
            return
        if len(username) < 3 or len(username) > 16:
            QMessageBox.warning(self, "TooTalk", _tr("username 3~16자 의무"))
            return

        # cycle 169.31 회수 — qasync loop 의 run_forever 진입 부재 + dialog.exec() nested Qt event loop
        # asyncio.ensure_future = no running loop fail → 별개 loop 의 run_until_complete chain
        self._run_async(self._do_signup(email, username, password))

    def _run_async(self, coro) -> None:
        """async coroutine sync 처리 — qasync loop 부재 graceful."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(coro)
                return
        except RuntimeError:
            pass
        new_loop = asyncio.new_event_loop()
        try:
            new_loop.run_until_complete(coro)
        finally:
            new_loop.close()

    async def _do_signup(self, email: str, username: str, password: str) -> None:
        try:
            result = await self._client.register(email, username, password)  # type: ignore[attr-defined]
        except AttributeError:
            QMessageBox.information(
                self,
                "TooTalk",
                _tr("회원가입 endpoint 미진입 — Phase 1 actual binding 의무"),
            )
            self._email = email
            self.accept()
            return

        if getattr(result, "ok", False):
            from app.ui.otp_dialog import OTPDialog
            otp = OTPDialog(auth_client=self._client, email=email, parent=self)
            if otp.exec() == otp.DialogCode.Accepted:
                self._email = email
                self.accept()
            else:
                QMessageBox.information(self, "TooTalk", _tr("OTP 미인증 — 다음 진입 시 재시도"))
                self.reject()
        else:
            err_msg = getattr(result, "error_message", _tr("가입 실패"))
            QMessageBox.critical(self, f"{_tr('회원가입')} 실패", str(err_msg))
