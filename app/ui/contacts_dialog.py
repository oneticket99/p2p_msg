# SPDX-License-Identifier: GPL-3.0-or-later
"""ContactsDialog — 연락처 modal (cycle 169.317).

사용자 directive image #84 — drawer 의 "연락처" click → 본 dialog (친구 목록 + 추가).
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

from app.ui._close_button import make_close_button


class ContactsDialog(QDialog):
    """연락처 dialog — 친구 list + 신규 친구 추가."""

    contact_added = pyqtSignal(str)  # (user_id_or_email)

    def __init__(self, contacts: Optional[list[dict]] = None, parent: Optional[QWidget] = None) -> None:
        # 한글 주석 — telegram align outer wrap + 420x600 strict
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 연락처")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("contactsWrap")
        wrap.setStyleSheet(
            "QFrame#contactsWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(12)

        # 한글 주석 — header
        header_row = QHBoxLayout()
        title = QLabel("연락처")
        title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        # cycle 169.324 — 공통 close button factory (telegram align)
        close_btn = make_close_button(self.reject, self)
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # 한글 주석 — 친구 추가 input + button
        add_row = QHBoxLayout()
        self._add_edit = QLineEdit()
        self._add_edit.setPlaceholderText("이메일 또는 유저 ID")
        self._add_edit.setStyleSheet(
            "QLineEdit { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 8px; }"
        )
        add_row.addWidget(self._add_edit, stretch=1)
        add_btn = QPushButton("추가")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #3b82f6;"
            " border: 0; border-radius: 8px; padding: 8px 16px; }"
            "QPushButton:hover { background-color: #2563eb; }"
        )
        add_btn.clicked.connect(self._on_add)  # type: ignore[arg-type]
        add_row.addWidget(add_btn)
        body.addLayout(add_row)

        # 한글 주석 — 친구 list
        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; }"
            "QListWidget::item { padding: 10px; }"
            "QListWidget::item:hover { background-color: #2c3a52; }"
        )
        body.addWidget(self._list, stretch=1)

        self._populate(contacts or [])

    def _populate(self, contacts: list[dict]) -> None:
        # 한글 주석 — 외부 친구 list 주입
        for c in contacts:
            name = c.get("name") or c.get("username") or c.get("email", "?")
            item = QListWidgetItem(name)
            self._list.addItem(item)
        if not contacts:
            empty = QListWidgetItem("등록된 연락처 부재")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(empty)

    def _on_add(self) -> None:
        # 한글 주석 — 친구 추가 signal emit
        identifier = self._add_edit.text().strip()
        if identifier:
            self.contact_added.emit(identifier)
            self._add_edit.clear()
