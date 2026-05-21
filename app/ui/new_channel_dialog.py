# SPDX-License-Identifier: GPL-3.0-or-later
"""NewChannelDialog — 채널 만들기 modal (cycle 169.316).

사용자 directive image #84 — drawer 의 "채널 만들기" click → 본 dialog.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui._close_button import make_close_button


class NewChannelDialog(QDialog):
    """채널 만들기 placeholder dialog."""

    channel_created = pyqtSignal(str, str)  # (channel_name, description)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        # 한글 주석 — telegram align outer wrap + 420x600 strict
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 채널 만들기")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("newChannelWrap")
        wrap.setStyleSheet(
            "QFrame#newChannelWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(12)

        # 한글 주석 — header
        header_row = QHBoxLayout()
        title = QLabel("채널 만들기")
        title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        # cycle 169.324 — 공통 close button factory (telegram align)
        close_btn = make_close_button(self.reject, self)
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # 한글 주석 — 채널명
        name_label = QLabel("채널명")
        name_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        body.addWidget(name_label)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("새 채널 이름")
        self._name_edit.setStyleSheet(
            "QLineEdit { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 10px; }"
        )
        body.addWidget(self._name_edit)

        # 한글 주석 — 채널 설명
        desc_label = QLabel("채널 설명")
        desc_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        body.addWidget(desc_label)
        self._desc_edit = QTextEdit()
        self._desc_edit.setPlaceholderText("채널 소개 (선택)")
        self._desc_edit.setStyleSheet(
            "QTextEdit { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 10px; }"
        )
        body.addWidget(self._desc_edit, stretch=1)

        # 한글 주석 — 생성 button
        create_btn = QPushButton("채널 생성")
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #3b82f6;"
            " border: 0; border-radius: 8px; padding: 12px; font-weight: 600; }"
            "QPushButton:hover { background-color: #2563eb; }"
        )
        create_btn.clicked.connect(self._on_create)  # type: ignore[arg-type]
        body.addWidget(create_btn)

    def _on_create(self) -> None:
        # 한글 주석 — placeholder signal emit + close
        name = self._name_edit.text().strip()
        desc = self._desc_edit.toPlainText().strip()
        if name:
            self.channel_created.emit(name, desc)
        self.accept()
