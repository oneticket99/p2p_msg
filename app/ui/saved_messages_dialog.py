# SPDX-License-Identifier: GPL-3.0-or-later
"""SavedMessagesDialog — 저장한 메시지 modal (cycle 169.319).

사용자 directive image #84 — drawer 의 "저장한 메시지" click → 본 dialog.
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
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SavedMessagesDialog(QDialog):
    """저장한 메시지 dialog — 자기 자신과의 메모 chat (telegram saved messages 정합)."""

    message_appended = pyqtSignal(str)  # (text)

    def __init__(self, messages: Optional[list[dict]] = None, parent: Optional[QWidget] = None) -> None:
        # 한글 주석 — telegram align outer wrap + 420x600 strict
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 저장한 메시지")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("savedMessagesWrap")
        wrap.setStyleSheet(
            "QFrame#savedMessagesWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(12)

        # 한글 주석 — header
        header_row = QHBoxLayout()
        title = QLabel("저장한 메시지")
        title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 16px; font-size: 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2c3a52; color: #ffffff; }"
        )
        close_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # 한글 주석 — 메시지 list
        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; }"
            "QListWidget::item { padding: 10px; }"
        )
        body.addWidget(self._list, stretch=1)

        # 한글 주석 — 메시지 입력 row
        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("나에게 메모 남기기")
        self._input.setStyleSheet(
            "QLineEdit { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 8px; }"
        )
        self._input.returnPressed.connect(self._on_send)  # type: ignore[arg-type]
        input_row.addWidget(self._input, stretch=1)
        send_btn = QPushButton("저장")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #3b82f6;"
            " border: 0; border-radius: 8px; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #2563eb; }"
        )
        send_btn.clicked.connect(self._on_send)  # type: ignore[arg-type]
        input_row.addWidget(send_btn)
        body.addLayout(input_row)

        self._populate(messages or [])

    def _populate(self, messages: list[dict]) -> None:
        # 한글 주석 — 저장 메시지 history 주입
        for m in messages:
            ts = m.get("timestamp", "")
            text = m.get("text", "")
            item = QListWidgetItem(f"{ts}\n{text}")
            self._list.addItem(item)
        if not messages:
            empty = QListWidgetItem("저장된 메시지 부재")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(empty)

    def _on_send(self) -> None:
        # 한글 주석 — 메모 추가 signal emit + list 안 append
        text = self._input.text().strip()
        if not text:
            return
        item = QListWidgetItem(text)
        self._list.addItem(item)
        self._list.scrollToBottom()
        self._input.clear()
        self.message_appended.emit(text)
