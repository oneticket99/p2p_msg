# SPDX-License-Identifier: GPL-3.0-or-later
"""RemoteCallDialog — 원격 요청/연결 modal (cycle 169.338 사용자 directive).

CallDialog 등가 단순 modal — avatar + 요청자 name + status + 취소/승인/거절 button.

mode:
- "request" (outgoing) — 사용자 → 친구 원격 요청 발신, ringback loop wav 재생, 종료 button
- "incoming" — 친구 → 사용자 원격 요청 수신, ringtone loop wav 재생, 승인/거절 button
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._close_button import make_close_button
from app.i18n.labels import tr as _tr
from app.ui._avatar_helper import get_initials
from app.ui.avatar_palette import palette_solid

log = logging.getLogger(__name__)


class RemoteCallDialog(QDialog):
    """원격 요청/연결 modal — CallDialog 등가 단순."""

    accepted_signal = pyqtSignal()
    rejected_signal = pyqtSignal()
    cancelled_signal = pyqtSignal()

    def __init__(
        self,
        peer_name: str,
        mode: str = "request",  # "request" outgoing / "incoming"
        parent: Optional[QWidget] = None,
    ) -> None:
        # 한글 주석 — telegram align outer wrap + 420x600 strict
        super().__init__(parent)
        self.setWindowTitle(_tr("tootalk_원격_요청") if mode == "request" else _tr("tootalk_원격_수신"))
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        self._mode = mode
        self._peer_name = peer_name

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("remoteCallWrap")
        wrap.setStyleSheet(
            "QFrame#remoteCallWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # 한글 주석 — close button row
        top = QHBoxLayout()
        top.setContentsMargins(16, 12, 16, 0)
        top.addStretch(1)
        close_btn = make_close_button(self._on_cancel, self)
        top.addWidget(close_btn)
        body.addLayout(top)

        # 한글 주석 — avatar (chat_list entry 등가 palette_solid + initials)
        avatar_label = QLabel()
        avatar_label.setFixedSize(160, 160)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setPixmap(self._make_avatar(peer_name, 160))
        body.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 한글 주석 — peer name
        name_label = QLabel(peer_name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: #e5e7eb; font-size: 22px; font-weight: 700; padding-top: 16px;")
        body.addWidget(name_label)

        # 한글 주석 — status
        status_text = "원격 요청 발신 중…" if mode == "request" else "원격 요청 수신…"
        self._status_label = QLabel(status_text)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #67E8F9; font-size: 14px; padding-top: 8px;")
        body.addWidget(self._status_label)

        body.addStretch(1)

        # 한글 주석 — action button row
        action_row = QHBoxLayout()
        action_row.setContentsMargins(20, 16, 20, 24)
        action_row.setSpacing(16)
        action_row.addStretch(1)
        if mode == "incoming":
            accept_btn = QPushButton("승인")
            accept_btn.setFixedSize(120, 48)
            accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            accept_btn.setStyleSheet(
                "QPushButton { color: #ffffff; background-color: #0066FF;"
                " border: 0; border-radius: 24px; font-size: 15px; font-weight: 600; }"
                "QPushButton:hover { background-color: #0052cc; }"
            )
            accept_btn.clicked.connect(self._on_accept)  # type: ignore[arg-type]
            action_row.addWidget(accept_btn)
            reject_btn = QPushButton("거절")
            reject_btn.setFixedSize(120, 48)
            reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            reject_btn.setStyleSheet(
                "QPushButton { color: #ffffff; background-color: #dc2626;"
                " border: 0; border-radius: 24px; font-size: 15px; font-weight: 600; }"
                "QPushButton:hover { background-color: #b91c1c; }"
            )
            reject_btn.clicked.connect(self._on_reject)  # type: ignore[arg-type]
            action_row.addWidget(reject_btn)
        else:
            cancel_btn = QPushButton("취소")
            cancel_btn.setFixedSize(160, 48)
            cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            cancel_btn.setStyleSheet(
                "QPushButton { color: #ffffff; background-color: #dc2626;"
                " border: 0; border-radius: 24px; font-size: 15px; font-weight: 600; }"
                "QPushButton:hover { background-color: #b91c1c; }"
            )
            cancel_btn.clicked.connect(self._on_cancel)  # type: ignore[arg-type]
            action_row.addWidget(cancel_btn)
        action_row.addStretch(1)
        body.addLayout(action_row)

        # 한글 주석 — cycle 169.338 ring wav play_loop chain (CallDialog 등가)
        self._sound = None
        try:
            from app.sound.ringtone import CallSoundPlayer
            self._sound = CallSoundPlayer(volume=0.6)
            initial_key = "ringtone" if mode == "incoming" else "ringback"
            self._sound.play_loop(initial_key)
        except Exception as exc:
            log.warning("[RemoteCallDialog] sound init fail — %r", exc)

    def _make_avatar(self, name: str, size: int) -> QPixmap:
        # 한글 주석 — chat_list entry 등가 (palette_solid bg + initials)
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(palette_solid(name)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        initials = get_initials(name)
        painter.setPen(QPen(QColor("#ffffff")))
        f = QFont()
        f.setPixelSize(int(size * 0.4))
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        painter.end()
        return pix

    def _on_accept(self) -> None:
        if self._sound is not None:
            self._sound.stop_loop()
            self._sound.play_once("connect")
        self.accepted_signal.emit()
        QTimer.singleShot(1000, self.accept)

    def _on_reject(self) -> None:
        if self._sound is not None:
            self._sound.stop_loop()
            self._sound.play_once("end")
        self.rejected_signal.emit()
        QTimer.singleShot(1500, self.reject)

    def _on_cancel(self) -> None:
        if self._sound is not None:
            self._sound.stop_loop()
            self._sound.play_once("end")
        self.cancelled_signal.emit()
        QTimer.singleShot(1500, self.reject)
