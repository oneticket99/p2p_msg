# SPDX-License-Identifier: GPL-3.0-or-later
"""비밀번호 재설정 다이얼로그 — email → OTP → 신규 비번 갱신."""

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
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.net.auth_client import AuthClient
from app.ui.confirm_dialog import ConfirmDialog as _ConfirmDialog

log = logging.getLogger(__name__)


class PasswordResetDialog(QDialog):
    """비번 재설정 2단계 stack — email 입력 → OTP + 신규 비번 입력."""

    def __init__(self, auth_client: AuthClient, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self._client = auth_client
        self._email: str = ""

        self.setWindowTitle("TooTalk 비밀번호 재설정")
        self.setMinimumWidth(360)

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._build_email_page())
        self._stack.addWidget(self._build_consume_page())

        outer = QVBoxLayout(self)
        outer.addWidget(self._stack)

    def _build_email_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("user@example.com")
        form.addRow("이메일", self._email_edit)

        btn = QPushButton("OTP 발송")
        btn.clicked.connect(self._on_request_clicked)  # type: ignore[arg-type]
        form.addRow(btn)
        return page

    def _build_consume_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)

        self._otp_edit = QLineEdit()
        self._otp_edit.setMaxLength(6)
        self._otp_edit.setPlaceholderText("6자리 OTP (3분 유효)")
        form.addRow("인증코드", self._otp_edit)

        self._new_pw_edit = QLineEdit()
        self._new_pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._new_pw_edit.setPlaceholderText("8~128자")
        form.addRow("새 비밀번호", self._new_pw_edit)

        row = QHBoxLayout()
        btn_back = QPushButton("이전")
        btn_back.clicked.connect(lambda: self._stack.setCurrentIndex(0))  # type: ignore[arg-type]
        btn_consume = QPushButton("비밀번호 갱신")
        btn_consume.clicked.connect(self._on_consume_clicked)  # type: ignore[arg-type]
        row.addWidget(btn_back)
        row.addWidget(btn_consume)
        form.addRow(row)
        return page

    def _on_request_clicked(self) -> None:
        email = self._email_edit.text().strip()
        if not email:
            _ConfirmDialog.show_warning(self, "TooTalk", "이메일을 입력하세요.")
            return
        self._email = email
        asyncio.ensure_future(self._do_request(email))

    async def _do_request(self, email: str) -> None:
        # silent success 정합 — 응답 무관 동일 메시지 (enumeration 방어)
        await self._client.request_reset(email)
        _ConfirmDialog.show_info(
            self,
            "TooTalk",
            "이메일 등록 시 OTP 가 발송됩니다. 이메일을 확인하세요.",
        )
        self._stack.setCurrentIndex(1)

    def _on_consume_clicked(self) -> None:
        code = self._otp_edit.text().strip()
        new_pw = self._new_pw_edit.text()
        if len(code) != 6 or not code.isdigit():
            _ConfirmDialog.show_warning(self, "TooTalk", "6자리 숫자 OTP 의무")
            return
        if not new_pw:
            _ConfirmDialog.show_warning(self, "TooTalk", "새 비밀번호 입력 의무")
            return
        asyncio.ensure_future(self._do_consume(self._email, code, new_pw))

    async def _do_consume(self, email: str, code: str, new_password: str) -> None:
        result = await self._client.consume_reset(email, code, new_password)
        if result.ok:
            _ConfirmDialog.show_info(self, "TooTalk", "비밀번호 갱신 완료. 로그인하세요.")
            self.accept()
        else:
            _ConfirmDialog.show_critical(
                self,
                "재설정 실패",
                f"{result.error_code}: {result.error_message}",
            )
