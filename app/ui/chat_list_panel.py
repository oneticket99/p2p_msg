# SPDX-License-Identifier: GPL-3.0-or-later
"""ChatListPanel — 메인 윈도우 중앙 280px chat list column (cycle 153 phase 3).

텔레그램 desktop 3 column 의 middle 등가 — 검색 bar + 친구 + 방 + 봇 통합 list.
정합 = telegram-ui-survey.md §5 + sidebar_rail.py active tab 연동.

signal:
    chat_selected(str, int) — (kind, target_id) kind ∈ {"friend", "room", "bot"} emit
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class ChatListEntry:
    """chat list 단일 row entry."""

    kind: str  # "friend" / "room" / "bot"
    target_id: int
    name: str
    last_message: str = ""
    last_ts: Optional[datetime] = None
    unread_count: int = 0
    is_pinned: bool = False
    is_online: bool = False


class ChatListPanel(QFrame):
    """중앙 280px chat list — 검색 bar + sortable list + brand selected highlight."""

    chat_selected = pyqtSignal(str, int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("chatListPanel")
        self.setMinimumWidth(280)
        self.setMaximumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 한글 주석 — 검색 bar top
        search_frame = QFrame()
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(12, 12, 12, 8)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍 친구 / 방 / 봇 검색")
        self._search_edit.setMinimumHeight(36)
        self._search_edit.textChanged.connect(self._on_search_changed)  # type: ignore[arg-type]
        search_layout.addWidget(self._search_edit)
        layout.addWidget(search_frame)

        # 한글 주석 — chat list (QListWidget — brand QSS#chatList selector 정합)
        self._list = QListWidget()
        self._list.setObjectName("chatList")
        self._list.setSpacing(0)
        self._list.itemClicked.connect(self._on_item_clicked)  # type: ignore[arg-type]
        layout.addWidget(self._list, stretch=1)

        # 한글 주석 — 빈 상태 placeholder text
        self._empty_label = QLabel("참여 중인 chat 부재")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #6b7280; font-size: 13px; padding: 40px 12px;")
        layout.addWidget(self._empty_label)

        self._entries: list[ChatListEntry] = []
        self._filter_text: str = ""
        self._active_tab: str = "friends"

    def set_active_tab(self, tab_key: str) -> None:
        """sidebar_rail tab_clicked signal 연결 — list re-render."""
        self._active_tab = tab_key
        self._render()

    def set_entries(self, entries: list[ChatListEntry]) -> None:
        """전체 entry 갱신 + sort + render."""
        self._entries = sorted(
            entries,
            key=lambda e: (
                not e.is_pinned,
                -(e.last_ts.timestamp() if e.last_ts else 0),
            ),
        )
        self._render()

    def _on_search_changed(self, text: str) -> None:
        self._filter_text = text.strip().lower()
        self._render()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        kind = item.data(Qt.ItemDataRole.UserRole)
        target_id = item.data(Qt.ItemDataRole.UserRole + 1)
        if kind and target_id is not None:
            self.chat_selected.emit(kind, int(target_id))

    def _matches_tab(self, entry: ChatListEntry) -> bool:
        """active tab kind filter."""
        if self._active_tab == "friends":
            return entry.kind == "friend"
        if self._active_tab == "rooms":
            return entry.kind == "room"
        if self._active_tab == "bots":
            return entry.kind == "bot"
        # settings tab — 별개 panel 의무 (cycle 153.4)
        return False

    def _render(self) -> None:
        """현 active tab + 검색 filter 기반 list 재 렌더."""
        self._list.clear()
        visible = 0
        for entry in self._entries:
            if not self._matches_tab(entry):
                continue
            if self._filter_text and self._filter_text not in entry.name.lower():
                if self._filter_text not in entry.last_message.lower():
                    continue
            pin = "📌 " if entry.is_pinned else ""
            online = "🟢 " if entry.is_online else ""
            display = f"{pin}{online}{entry.name}"
            if entry.last_message:
                display += f"\n    {entry.last_message[:40]}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, entry.kind)
            item.setData(Qt.ItemDataRole.UserRole + 1, entry.target_id)
            if entry.unread_count > 0:
                # 한글 주석 — unread badge 의 tooltip 표기 (cycle 154 inline badge widget 의무)
                item.setToolTip(f"unread {entry.unread_count}")
            self._list.addItem(item)
            visible += 1
        self._empty_label.setVisible(visible == 0)
        self._list.setVisible(visible > 0)
