# SPDX-License-Identifier: GPL-3.0-or-later
"""ChatPickerDialog — 대화방 multiselect modal (cycle 169.370 rewrite).

사용자 critique image #125 — chat_list entry 등가 list format 의무.
ChatListItemDelegate 재사용 + frameless + i18n + _exec_dialog_centered chain.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
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
from app.ui._icons import load_icon
from app.ui.chat_list_panel import ChatListItemDelegate
from app.i18n.labels import tr as _tr


class ChatPickerDialog(QDialog):
    """대화방 multiselect — chat_list entry 등가 format + folder 포함/제외 picker."""

    chats_selected = pyqtSignal(list)

    def __init__(
        self,
        chat_entries: List,
        mode: str = "include",
        parent: Optional[QWidget] = None,
    ) -> None:
        # 한글 주석 — telegram align outer wrap + frameless + 420x600
        super().__init__(parent)
        title_key = "포함할_대화방" if mode == "include" else "제외할_대화방"
        self.setWindowTitle(f"TooTalk · {_tr(title_key)}")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")
        self._entries = chat_entries

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("chatPickerWrap")
        wrap.setStyleSheet(
            "QFrame#chatPickerWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(12)

        # 한글 주석 — header (title + close X)
        header_row = QHBoxLayout()
        title = QLabel(_tr(title_key))
        title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        close_btn = make_close_button(self.reject, self)
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # 한글 주석 — 검색 input (SVG icon + padding-left 32)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText(_tr("검색"))
        self._search_edit.setStyleSheet(
            "QLineEdit { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 8px 8px 8px 32px; }"
        )
        search_action = QAction(self)
        search_action.setIcon(load_icon("search", size=16, color="#9ca3af"))
        self._search_edit.addAction(search_action, QLineEdit.ActionPosition.LeadingPosition)
        self._search_edit.textChanged.connect(self._on_search_changed)  # type: ignore[arg-type]
        body.addWidget(self._search_edit)

        # 한글 주석 — chat_list entry 등가 list (ChatListItemDelegate 재사용)
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._list.setStyleSheet(
            "QListWidget { background-color: transparent; border: 1px solid #374151;"
            " border-radius: 8px; outline: 0; }"
            "QListWidget::item:selected { background-color: rgba(0, 102, 255, 0.2); }"
        )
        self._list.setItemDelegate(ChatListItemDelegate(self._list))
        self._list.setSpacing(0)
        for entry in self._entries:
            item = QListWidgetItem("")
            item.setData(Qt.ItemDataRole.UserRole, entry.kind)
            item.setData(Qt.ItemDataRole.UserRole + 1, entry.target_id)
            item.setData(Qt.ItemDataRole.UserRole + 2, entry)
            self._list.addItem(item)
        body.addWidget(self._list, stretch=1)

        # 한글 주석 — 취소 + 확인 button row
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton(_tr("취소"))
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton { color: #0066FF; background: transparent; border: 0; padding: 8px 16px; font-weight: 600; }"
            "QPushButton:hover { color: #3b82f6; }"
        )
        cancel_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton(_tr("확인"))
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet(
            "QPushButton { color: #0066FF; background: transparent; border: 0; padding: 8px 16px; font-weight: 600; }"
            "QPushButton:hover { color: #3b82f6; }"
        )
        ok_btn.clicked.connect(self._on_ok)  # type: ignore[arg-type]
        btn_row.addWidget(ok_btn)
        body.addLayout(btn_row)

    def _on_search_changed(self, text: str) -> None:
        # 한글 주석 — 검색 input list filter (entry.name lower contains)
        lower = text.strip().lower()
        for i in range(self._list.count()):
            item = self._list.item(i)
            entry = item.data(Qt.ItemDataRole.UserRole + 2)
            name = getattr(entry, "name", "") if entry is not None else ""
            visible = (not lower) or (lower in name.lower())
            item.setHidden(not visible)

    def _on_ok(self) -> None:
        # 한글 주석 — selected entry list emit
        selected = []
        for item in self._list.selectedItems():
            entry = item.data(Qt.ItemDataRole.UserRole + 2)
            if entry is not None:
                selected.append(entry)
        self.chats_selected.emit(selected)
        self.accept()
