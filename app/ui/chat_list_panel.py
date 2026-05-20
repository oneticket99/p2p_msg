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

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
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
    last_sender: str = ""  # cycle 169.73 — group rooms last sender prefix ("나" / 사용자명)


class ChatListItemDelegate(QStyledItemDelegate):
    """telegram desktop chat list item custom paint (cycle 169.68 신설).

    layout: avatar circle 40px + name (15px bold) + last_message (12px gray) + ts (11px gray) + unread badge.
    """

    AVATAR_SIZE = 40
    ROW_HEIGHT = 64
    PADDING = 12

    def sizeHint(self, option: QStyleOptionViewItem, index) -> "QSize":  # type: ignore[override]
        from PyQt6.QtCore import QSize
        return QSize(option.rect.width() if option.rect.width() > 0 else 280, self.ROW_HEIGHT)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # type: ignore[override]
        rect = option.rect
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 한글 주석 — selected highlight (telegram brand 색)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, QColor("#1E3A5F"))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(rect, QColor("#192335"))

        # avatar circle
        entry = index.data(Qt.ItemDataRole.UserRole + 2)
        if entry is None:
            painter.restore()
            return
        avatar_rect = QRect(
            rect.left() + self.PADDING,
            rect.top() + (self.ROW_HEIGHT - self.AVATAR_SIZE) // 2,
            self.AVATAR_SIZE,
            self.AVATAR_SIZE,
        )
        painter.setBrush(QColor("#1F2937"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(avatar_rect)
        # avatar initial char
        initial = (entry.name[:1] if entry.name else "?").upper()
        painter.setPen(QPen(QColor("#67E8F9")))
        f = QFont(); f.setPixelSize(16); f.setBold(True)
        painter.setFont(f)
        painter.drawText(avatar_rect, Qt.AlignmentFlag.AlignCenter, initial)

        # online indicator (right-bottom)
        if entry.is_online:
            painter.setBrush(QColor("#22c55e"))
            painter.setPen(QPen(QColor("#0F172A"), 2))
            painter.drawEllipse(
                avatar_rect.right() - 10, avatar_rect.bottom() - 10, 10, 10
            )

        # name + last_message text area
        text_x = avatar_rect.right() + self.PADDING
        text_w = rect.width() - text_x - self.PADDING - 56  # 56 = right side (ts + badge)

        # name
        painter.setPen(QPen(QColor("#e5e7eb")))
        fn = QFont(); fn.setPixelSize(14); fn.setBold(True)
        painter.setFont(fn)
        name_rect = QRect(text_x, rect.top() + 10, text_w, 20)
        elided_name = painter.fontMetrics().elidedText(
            entry.name, Qt.TextElideMode.ElideRight, text_w
        )
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_name)

        # last_message — group room 의 의 sender prefix ("나: ..." 또는 "{sender}: ...")
        painter.setPen(QPen(QColor("#9ca3af")))
        fm = QFont(); fm.setPixelSize(12)
        painter.setFont(fm)
        msg_rect = QRect(text_x, rect.top() + 32, text_w, 18)
        if entry.last_sender and entry.kind == "room":
            preview_text = f"{entry.last_sender}: {entry.last_message or ''}"
        else:
            preview_text = entry.last_message or ""
        elided_msg = painter.fontMetrics().elidedText(
            preview_text, Qt.TextElideMode.ElideRight, text_w
        )
        painter.drawText(msg_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_msg)

        # ts (right top)
        ts_rect = QRect(rect.right() - 56, rect.top() + 10, 44, 18)
        ts_text = entry.last_ts.strftime("%H:%M") if entry.last_ts else ""
        painter.setPen(QPen(QColor("#6b7280")))
        ft = QFont(); ft.setPixelSize(11)
        painter.setFont(ft)
        painter.drawText(ts_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, ts_text)

        # unread badge (right bottom)
        if entry.unread_count > 0:
            badge_text = str(entry.unread_count) if entry.unread_count < 100 else "99+"
            badge_w = max(20, painter.fontMetrics().horizontalAdvance(badge_text) + 12)
            badge_rect = QRect(rect.right() - 12 - badge_w, rect.top() + 32, badge_w, 20)
            painter.setBrush(QColor("#0066FF"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge_rect, 10, 10)
            painter.setPen(QPen(QColor("white")))
            fb = QFont(); fb.setPixelSize(11); fb.setBold(True)
            painter.setFont(fb)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        # divider line (bottom)
        painter.setPen(QPen(QColor("#1F2937"), 1))
        painter.drawLine(rect.left() + self.PADDING, rect.bottom(), rect.right() - self.PADDING, rect.bottom())

        painter.restore()


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
        # 한글 주석 — cycle 169.68 회수 — custom delegate paint chain (avatar + name + ts + unread badge)
        self._list.setItemDelegate(ChatListItemDelegate(self._list))
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
        self._active_folder: str = "all"  # cycle 169.71

    def set_active_tab(self, tab_key: str) -> None:
        """sidebar_rail tab_clicked signal 연결 — list re-render."""
        self._active_tab = tab_key
        self._render()

    def set_active_folder(self, folder_id: str) -> None:
        """FolderList folder_selected signal 연결 (cycle 169.71)."""
        self._active_folder = folder_id
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
        """active tab + folder filter (cycle 169.71)."""
        # 한글 주석 — folder filter 우선 — unread folder 시 unread_count > 0 만
        if self._active_folder == "unread" and entry.unread_count <= 0:
            return False
        # custom folder (monitor/work/issue 등) entry.folder field 미존재 시 skip 차단 부재
        if self._active_tab == "friends":
            return entry.kind == "friend"
        if self._active_tab == "rooms":
            return entry.kind == "room"
        if self._active_tab == "bots":
            return entry.kind == "bot"
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
            # 한글 주석 — cycle 169.68 delegate paint chain — 빈 text + entry full data UserRole+2 store
            item = QListWidgetItem("")
            item.setData(Qt.ItemDataRole.UserRole, entry.kind)
            item.setData(Qt.ItemDataRole.UserRole + 1, entry.target_id)
            item.setData(Qt.ItemDataRole.UserRole + 2, entry)
            self._list.addItem(item)
            visible += 1
        self._empty_label.setVisible(visible == 0)
        self._list.setVisible(visible > 0)
