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
    folder_color: str = ""  # cycle 169.76 — folder 색상 hex (chat_list inline strip)


class ChatListItemDelegate(QStyledItemDelegate):
    """telegram desktop chat list item custom paint (cycle 169.68 신설).

    layout: avatar circle 40px + name (15px bold) + last_message (12px gray) + ts (11px gray) + unread badge.
    """

    # cycle 169.126 — telegram desktop Win11 정합 tune (sub-agent A drift D-6/D-7)
    # avatar 40→54 + row 60→72 + padding 14 retain (telegram align)
    AVATAR_SIZE = 54
    ROW_HEIGHT = 72
    PADDING = 14

    def sizeHint(self, option: QStyleOptionViewItem, index) -> "QSize":  # type: ignore[override]
        from PyQt6.QtCore import QSize
        return QSize(option.rect.width() if option.rect.width() > 0 else 280, self.ROW_HEIGHT)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # type: ignore[override]
        rect = option.rect
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # cycle 169.109 — Figma 정합 hover/selected (qss base-dark.qss chat list align)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, QColor(0, 102, 255, 46))  # rgba(0,102,255,0.18)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(rect, QColor(255, 255, 255, 10))  # rgba(255,255,255,0.04)

        # avatar circle
        entry = index.data(Qt.ItemDataRole.UserRole + 2)
        if entry is None:
            painter.restore()
            return

        # cycle 169.76 회수 — folder 색상 inline strip + cycle 169.79 회수 QColor.isValid 분기 (MED-4)
        if entry.folder_color:
            color = QColor(entry.folder_color)
            if color.isValid():
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRect(rect.left(), rect.top(), 3, rect.height())
        avatar_rect = QRect(
            rect.left() + self.PADDING,
            rect.top() + (self.ROW_HEIGHT - self.AVATAR_SIZE) // 2,
            self.AVATAR_SIZE,
            self.AVATAR_SIZE,
        )
        # cycle 169.140 — telegram per-user palette gradient (sub-agent A drift D-9)
        from app.ui.avatar_palette import palette_pair
        from PyQt6.QtGui import QLinearGradient, QBrush
        c_start, c_end = palette_pair(entry.name or "")
        grad = QLinearGradient(avatar_rect.topLeft().toPointF(), avatar_rect.bottomRight().toPointF())
        grad.setColorAt(0.0, QColor(c_start))
        grad.setColorAt(1.0, QColor(c_end))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(avatar_rect)
        # avatar initial char (white over gradient)
        initial = (entry.name[:1] if entry.name else "?").upper()
        painter.setPen(QPen(QColor("#ffffff")))
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
        name_rect = QRect(text_x, rect.top() + 14, text_w, 22)
        elided_name = painter.fontMetrics().elidedText(
            entry.name, Qt.TextElideMode.ElideRight, text_w
        )
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_name)

        # last_message — group room 의 의 sender prefix ("나: ..." 또는 "{sender}: ...")
        painter.setPen(QPen(QColor("#A1AAB3")))  # cycle 169.109 — Figma Service text token
        fm = QFont(); fm.setPixelSize(12)
        painter.setFont(fm)
        msg_rect = QRect(text_x, rect.top() + 40, text_w, 20)
        if entry.last_sender and entry.kind == "room":
            preview_text = f"{entry.last_sender}: {entry.last_message or ''}"
        else:
            preview_text = entry.last_message or ""
        elided_msg = painter.fontMetrics().elidedText(
            preview_text, Qt.TextElideMode.ElideRight, text_w
        )
        painter.drawText(msg_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_msg)

        # ts (right top)
        ts_rect = QRect(rect.right() - 72, rect.top() + 14, 60, 20)
        # cycle 169.151 — telegram chat list ts 한국어 format
        if entry.last_ts:
            h = entry.last_ts.hour
            m = entry.last_ts.minute
            ap = "오전" if h < 12 else "오후"
            h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
            ts_text = f"{ap} {h12}:{m:02d}"
        else:
            ts_text = ""
        painter.setPen(QPen(QColor("#A1AAB3")))  # cycle 169.109 — Figma Service text token (ts color)
        ft = QFont(); ft.setPixelSize(11)
        painter.setFont(ft)
        painter.drawText(ts_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, ts_text)

        # unread badge (right bottom)
        if entry.unread_count > 0:
            badge_text = str(entry.unread_count) if entry.unread_count < 100 else "99+"
            badge_w = max(20, painter.fontMetrics().horizontalAdvance(badge_text) + 12)
            badge_rect = QRect(rect.right() - 12 - badge_w, rect.top() + 40, badge_w, 20)
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

        # 한글 주석 — 검색 bar top (cycle 169.169 — top bar 한 라인 통합 + bg #0A1019 + height 60)
        search_frame = QFrame()
        search_frame.setObjectName("chatListSearchBar")
        search_frame.setFixedHeight(60)
        search_frame.setStyleSheet(
            "QFrame#chatListSearchBar {"
            " background-color: #0A1019;"
            " border-bottom: 1px solid #1f2937;"
            "}"
        )
        search_layout = QVBoxLayout(search_frame)
        search_layout.setContentsMargins(12, 12, 12, 12)
        search_layout.setSpacing(0)

        self._search_edit = QLineEdit()
        # cycle 169.127 — sub-agent A drift D-8 — emoji prefix 제거 + addAction SVG (telegram align)
        from PyQt6.QtWidgets import QLineEdit as _QLE  # type: ignore
        self._search_edit.setPlaceholderText("검색")
        try:
            from app.ui._icons import load_icon as _li
            self._search_edit.addAction(_li("search", size=16, color="#9ca3af"), _QLE.ActionPosition.LeadingPosition)  # type: ignore[attr-defined]
        except Exception:
            pass
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

        # cycle 169.100 회수 — placeholder text 부재 (사용자 directive — 플레이스홀더 없이 전부 구현)
        self._empty_label = QLabel("")
        self._empty_label.setVisible(False)
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

    def set_current_chat(self, kind: str, target_id: int) -> None:
        """cycle 169.167 — programmatic 진입 path 의 list highlight sync (telegram align image #12).

        profile modal "메시지" click + main_window external chain 의 의 호출 → list selected row 동기.
        """
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is None:
                continue
            i_kind = item.data(Qt.ItemDataRole.UserRole)
            i_target = item.data(Qt.ItemDataRole.UserRole + 1)
            if i_kind == kind and i_target == target_id:
                self._list.setCurrentRow(i)
                return

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
