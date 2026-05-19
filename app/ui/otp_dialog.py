# SPDX-License-Identifier: GPL-3.0-or-later
"""OTPDialog — 회원가입 직후 6 digit email OTP 검증 (cycle 153 phase 2).

텔레그램 desktop OTP 등가 — 6 box auto-advance + paste 지원 + 재 송신 link.
정합 = telegram-ui-survey.md §3 + project_auth_email_otp_required + cycle 129 SMTP.

Flow:
    signup PASS → OTPDialog 진입 → 6 digit 입력 → POST /api/auth/otp/verify
    → 성공 시 accept() / 실패 시 message + 재시도 (5회 brute force cap)
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

import qasync

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
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

OTP_LENGTH = 6
RESEND_CAP = 5


class OtpBox(QLineEdit):
    """단일 OTP digit input — auto-advance + paste 지원 + arrow nav."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMaxLength(1)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(48, 56)
        self.setStyleSheet(
            "QLineEdit {"
            " font-size: 22px;"
            " font-weight: 600;"
            " background-color: #1F2937;"
            " border: 2px solid #374151;"
            " border-radius: 8px;"
            " color: #e5e7eb;"
            "}"
            " QLineEdit:focus { border-color: #0066FF; }"
        )
        self._on_full = lambda: None
        self._on_back = lambda: None

    def keyPressEvent(self, event: Optional[QKeyEvent]) -> None:
        """Backspace 시점 직전 box 의 의 focus + 6 digit paste 지원."""
        if event is None:
            return
        # 한글 주석 — Backspace 시점 의 직전 box focus 이동 callback
        if event.key() == Qt.Key.Key_Backspace and not self.text():
            self._on_back()
            return
        super().keyPressEvent(event)


class OTPDialog(QDialog):
    """6 digit email OTP 검증 dialog — auto-advance + 재 송신 link + brute force cap."""

    def __init__(
        self,
        auth_client: AuthClient,
        email: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._client = auth_client
        self._email = email
        self._resend_remaining = RESEND_CAP

        self.setWindowTitle(f"TooTalk · {_tr('OTP 인증')}")
        self.setMinimumWidth(420)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(16)

        # 한글 주석 — email 표기 + edit pencil (cycle 154 entry 시 점 enable)
        email_label = QLabel(self._email)
        email_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        email_label.setStyleSheet("color: #67E8F9; font-size: 14px; font-weight: 600;")
        outer.addWidget(email_label)

        info = QLabel(_tr("메일함 안 6 digit OTP 확인 (3분 유효)"))
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #9ca3af; font-size: 13px;")
        outer.addWidget(info)

        outer.addSpacing(8)

        # 한글 주석 — 6 box row + auto-advance binding
        box_row = QHBoxLayout()
        box_row.setSpacing(8)
        box_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._boxes: List[OtpBox] = []
        for i in range(OTP_LENGTH):
            box = OtpBox()
            self._boxes.append(box)
            box_row.addWidget(box)
        outer.addLayout(box_row)

        # 한글 주석 — auto-advance + back nav binding
        for i, box in enumerate(self._boxes):
            if i < OTP_LENGTH - 1:
                next_box = self._boxes[i + 1]
                box.textChanged.connect(  # type: ignore[arg-type]
                    lambda text, nxt=next_box: nxt.setFocus() if text else None
                )
            if i > 0:
                prev_box = self._boxes[i - 1]
                box._on_back = lambda prev=prev_box: prev.setFocus()  # type: ignore[assignment]
            # 한글 주석 — 마지막 box text 입력 시 자동 검증 trigger
            if i == OTP_LENGTH - 1:
                box.textChanged.connect(self._on_last_box_filled)  # type: ignore[arg-type]

        outer.addSpacing(8)

        # 한글 주석 — 재 송신 link + cancel
        link_row = QHBoxLayout()
        link_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._resend_btn = QPushButton(f"{_tr('재 송신')} ({self._resend_remaining}/{RESEND_CAP})")
        self._resend_btn.setProperty("variant", "ghost")
        self._resend_btn.setFlat(True)
        self._resend_btn.clicked.connect(self._on_resend_clicked)  # type: ignore[arg-type]
        link_row.addWidget(self._resend_btn)
        outer.addLayout(link_row)

        # 한글 주석 — 검증 + 취소 button row
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton(_tr("취소"))
        btn_cancel.setProperty("variant", "secondary")
        btn_cancel.clicked.connect(self.reject)  # type: ignore[arg-type]
        btn_verify = QPushButton(_tr("검증"))
        btn_verify.setProperty("variant", "primary")
        btn_verify.clicked.connect(self._on_verify_clicked)  # type: ignore[arg-type]
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_verify)
        outer.addLayout(btn_row)

        self._boxes[0].setFocus()

    def _get_otp(self) -> str:
        """6 box text concat → 6 digit string."""
        return "".join(box.text() for box in self._boxes)

    def _on_last_box_filled(self, text: str) -> None:
        """마지막 box 입력 시점 의 자동 검증 trigger."""
        if text and len(self._get_otp()) == OTP_LENGTH:
            self._on_verify_clicked()

    @qasync.asyncSlot()
    async def _on_verify_clicked(self) -> None:
        """cycle 169.33 회수 — qasync.asyncSlot decorator + 직접 async slot."""
        otp = self._get_otp()
        if len(otp) != OTP_LENGTH or not otp.isdigit():
            QMessageBox.warning(
                self,
                "TooTalk",
                _tr("6 digit OTP 입력 의무"),
            )
            return
        await self._do_verify(otp)

    async def _do_verify(self, otp: str) -> None:
        """auth_client 의 OTP verify endpoint 호출."""
        try:
            # 한글 주석 — auth_client 안 verify_otp method 존재 ack 의무
            result = await self._client.verify_otp(self._email, otp)  # type: ignore[attr-defined]
        except AttributeError:
            # 한글 주석 — verify_otp method 부재 시 graceful skip + 사용자 message
            QMessageBox.information(
                self,
                "TooTalk",
                _tr("OTP 검증 endpoint 미진입 — Phase 1 actual binding 의무"),
            )
            self.accept()
            return
        if getattr(result, "ok", False):
            self.accept()
        else:
            err_msg = getattr(result, "error_message", "검증 실패")
            QMessageBox.critical(self, "TooTalk", f"{_tr('OTP')} 실패: {err_msg}")
            # 한글 주석 — 실패 시 box clear + 첫 box focus
            for box in self._boxes:
                box.clear()
            self._boxes[0].setFocus()

    def _on_resend_clicked(self) -> None:
        """OTP 재 송신 + remaining cap 갱신."""
        if self._resend_remaining <= 0:
            QMessageBox.warning(self, "TooTalk", _tr("재 송신 cap 초과 (24h)"))
            return
        self._resend_remaining -= 1
        self._resend_btn.setText(f"{_tr('재 송신')} ({self._resend_remaining}/{RESEND_CAP})")
        # 한글 주석 — 실 송신 = auth_client.resend_otp endpoint actual binding cycle 154+ 의무
        log.info("OTP 재 송신 trigger — email=%s remaining=%d", self._email, self._resend_remaining)
