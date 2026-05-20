# SPDX-License-Identifier: GPL-3.0-or-later
"""ChatPickerDialog — 대화방 multiselect modal (cycle 169.75 신설).

사용자 directive 회수 — telegram desktop image 82 안 대화방 추가 click chain.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ChatPickerDialog(QDialog):
    """대화방 multiselect — folder 포함/제외 entry picker."""

    chats_selected = pyqtSignal(list)  # selected (kind, target_id, name) tuple list

    def __init__(
        self,
        chat_entries: List,
        mode: str = "include",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        title_text = "포함할 대화방" if mode == "include" else "제외할 대화방"
        self.setWindowTitle(f"TooTalk · {title_text}")
        self.setModal(True)
        self.setFixedSize(420, 560)
        self._entries = chat_entries

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(12)

        title = QLabel(title_text)
        title.setStyleSheet("color: #e5e7eb; font-size: 16px; font-weight: 700;")
        outer.addWidget(title)

        # 검색 input
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍 검색")
        self._search_edit.setMinimumHeight(36)
        self._search_edit.textChanged.connect(self._on_search_changed)  # type: ignore[arg-type]
        outer.addWidget(self._search_edit)

        # multiselect list
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for entry in self._entries:
            label = f"{entry.name}  ({entry.kind})"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self._list.addItem(item)
        outer.addWidget(self._list, stretch=1)

        # 버튼
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("취소")
        cancel_btn.setStyleSheet("color: #9ca3af; background: transparent; border: none; font-size: 14px;")
        cancel_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton("확인")
        ok_btn.setStyleSheet(
            "QPushButton {"
            " color: #0066FF; background: transparent; border: none;"
            " font-size: 14px; font-weight: 700; padding: 8px 16px;"
            "}"
        )
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self._on_ok)  # type: ignore[arg-type]
        btn_row.addWidget(ok_btn)
        outer.addLayout(btn_row)

    def _on_search_changed(self, text: str) -> None:
        """검색 input 의 의 list filter."""
        lower = text.strip().lower()
        for i in range(self._list.count()):
            item = self._list.item(i)
            entry = item.data(Qt.ItemDataRole.UserRole)
            visible = (not lower) or (lower in entry.name.lower())
            item.setHidden(not visible)

    def _on_ok(self) -> None:
        """확인 click — selected entry list emit."""
        selected = []
        for item in self._list.selectedItems():
            entry = item.data(Qt.ItemDataRole.UserRole)
            selected.append(entry)
        self.chats_selected.emit(selected)
        self.accept()
