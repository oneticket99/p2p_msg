# SPDX-License-Identifier: GPL-3.0-or-later
"""로그인 다이얼로그 — email + password → 세션 토큰 발급."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.net.auth_client import AuthClient

log = logging.getLogger(__name__)


class LoginDialog(QDialog):
    """로그인 다이얼로그 — 성공 시 세션 토큰 + user_id 보관 후 accept()."""

    def __init__(self, auth_client: AuthClient, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._client = auth_client
        self._token: Optional[str] = None
        self._user_id: Optional[int] = None

        self.setWindowTitle("TooTalk 로그인")
        self.setMinimumWidth(320)

        form = QFormLayout(self)

        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("user@example.com")
        form.addRow("이메일", self._email_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("비밀번호", self._password_edit)

        row = QHBoxLayout()
        btn_login = QPushButton("로그인")
        btn_login.clicked.connect(self._on_login_clicked)  # type: ignore[arg-type]
        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.reject)  # type: ignore[arg-type]
        row.addWidget(btn_cancel)
        row.addWidget(btn_login)
        form.addRow(row)

    @property
    def token(self) -> Optional[str]:
        """로그인 PASS 시 세션 토큰 (accept() 후 caller 단 조회)."""

        return self._token

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id

    def _on_login_clicked(self) -> None:
        email = self._email_edit.text().strip()
        password = self._password_edit.text()
        if not email or not password:
            QMessageBox.warning(self, "TooTalk", "이메일 + 비밀번호 입력 의무")
            return
        asyncio.ensure_future(self._do_login(email, password))

    async def _do_login(self, email: str, password: str) -> None:
        result = await self._client.login(email, password)
        if result.ok:
            self._token = result.token
            self._user_id = result.user_id
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "로그인 실패",
                f"{result.error_code}: {result.error_message}",
            )
