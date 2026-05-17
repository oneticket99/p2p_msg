# SPDX-License-Identifier: GPL-3.0-or-later
"""회원가입 다이얼로그 — email + username + password + OTP 검증.

흐름:
1. 사용자 입력 (email/username/password) → AuthClient.register
2. signup 성공 시 OTP 입력 step 진입
3. OTP 입력 → AuthClient.verify_otp
4. PASS → accept(), FAIL → 오류 표시 + 재시도
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.net.auth_client import AuthClient

log = logging.getLogger(__name__)


class SignupDialog(QDialog):
    """회원가입 + OTP 검증 통합 다이얼로그.

    Parameters
    ----------
    auth_client : AuthClient
        REST API client (호출자 측 생성 + 주입).
    parent : QWidget | None
        부모 위젯.
    """

    def __init__(self, auth_client: AuthClient, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._client = auth_client
        self._email: str = ""

        self.setWindowTitle("TooTalk 회원가입")
        self.setMinimumWidth(360)

        # 한글 주석: 2단계 stack — 0=회원가입 form, 1=OTP 입력
        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._build_signup_page())
        self._stack.addWidget(self._build_otp_page())

        outer = QVBoxLayout(self)
        outer.addWidget(self._stack)

    def _build_signup_page(self) -> QWidget:
        """1단계 — email + username + password 입력 form."""

        page = QWidget()
        form = QFormLayout(page)

        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("user@example.com")
        form.addRow("이메일", self._email_edit)

        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("표시 이름 (1~64자)")
        form.addRow("사용자명", self._username_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText("8~128자")
        form.addRow("비밀번호", self._password_edit)

        btn_signup = QPushButton("회원가입 + OTP 발송")
        btn_signup.clicked.connect(self._on_signup_clicked)  # type: ignore[arg-type]
        form.addRow(btn_signup)

        return page

    def _build_otp_page(self) -> QWidget:
        """2단계 — OTP 6자리 입력."""

        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(QLabel("이메일로 발송된 6자리 인증코드를 입력하세요. (3분 유효)"))

        self._otp_edit = QLineEdit()
        self._otp_edit.setMaxLength(6)
        self._otp_edit.setPlaceholderText("123456")
        layout.addWidget(self._otp_edit)

        row = QHBoxLayout()
        btn_verify = QPushButton("인증 + 완료")
        btn_verify.clicked.connect(self._on_verify_clicked)  # type: ignore[arg-type]
        btn_back = QPushButton("이전")
        btn_back.clicked.connect(lambda: self._stack.setCurrentIndex(0))  # type: ignore[arg-type]
        row.addWidget(btn_back)
        row.addWidget(btn_verify)
        layout.addLayout(row)

        return page

    def _on_signup_clicked(self) -> None:
        """회원가입 버튼 클릭 — async task 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 dispatch."""

        email = self._email_edit.text().strip()
        username = self._username_edit.text().strip()
        password = self._password_edit.text()

        if not email or not username or not password:
            QMessageBox.warning(self, "TooTalk", "모든 필드를 입력하세요.")
            return

        self._email = email
        asyncio.ensure_future(self._do_signup(email, username, password))

    async def _do_signup(self, email: str, username: str, password: str) -> None:
        result = await self._client.register(email, username, password)
        if result.ok:
            QMessageBox.information(self, "TooTalk", "OTP 발송. 이메일을 확인하세요.")
            self._stack.setCurrentIndex(1)
        else:
            QMessageBox.critical(
                self,
                "회원가입 실패",
                f"{result.error_code}: {result.error_message}",
            )

    def _on_verify_clicked(self) -> None:
        """OTP 검증 버튼 클릭."""

        code = self._otp_edit.text().strip()
        if len(code) != 6 or not code.isdigit():
            QMessageBox.warning(self, "TooTalk", "6자리 숫자 OTP 를 입력하세요.")
            return

        asyncio.ensure_future(self._do_verify(self._email, code))

    async def _do_verify(self, email: str, code: str) -> None:
        result = await self._client.verify_otp(email, code)
        if result.ok:
            QMessageBox.information(self, "TooTalk", "회원가입 완료. 로그인하세요.")
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "OTP 검증 실패",
                f"{result.error_code}: {result.error_message}",
            )
