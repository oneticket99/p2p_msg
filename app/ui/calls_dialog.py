# SPDX-License-Identifier: GPL-3.0-or-later
"""CallsDialog — 전화 history modal (cycle 169.318).

계층 위치 — app/ui dialog(정본 §E). QDialog 위젯 — DrawerMixin 이 instantiate(통화 history list 표시).
순수 표시 UI — 통화 data 는 caller 가 주입(본 dialog 는 영속/네트워크 책임 없음).

사용자 directive image #84 — drawer 의 "전화" click → 본 dialog (통화 history list).
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._close_button import make_close_button
from app.i18n.labels import tr as _tr


class CallsDialog(QDialog):
    """전화 history dialog — 최근 통화 list."""

    call_initiated = pyqtSignal(str)  # (peer_id)

    def __init__(self, calls: Optional[list[dict]] = None, parent: Optional[QWidget] = None) -> None:
        # telegram align outer wrap + 420x600 strict
        super().__init__(parent)
        self.setWindowTitle(_tr("tootalk_전화"))
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("callsWrap")
        wrap.setStyleSheet(
            "QFrame#callsWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(12)

        # header
        header_row = QHBoxLayout()
        title = QLabel("전화")
        title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        # cycle 169.324 — 공통 close button factory (telegram align)
        close_btn = make_close_button(self.reject, self)
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # 최근 통화 list
        recent_label = QLabel("최근 통화")
        recent_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        body.addWidget(recent_label)
        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; }"
            "QListWidget::item { padding: 10px; }"
            "QListWidget::item:hover { background-color: #2c3a52; }"
        )
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)  # type: ignore[arg-type]
        body.addWidget(self._list, stretch=1)

        self._populate(calls or [])

    def _populate(self, calls: list[dict]) -> None:
        # 통화 history 주입
        for c in calls:
            peer = c.get("peer_name", "?")
            ts = c.get("timestamp", "")
            direction = "↗" if c.get("outgoing", True) else "↙"
            item = QListWidgetItem(f"{direction}  {peer}    {ts}")
            item.setData(Qt.ItemDataRole.UserRole, c.get("peer_id", ""))
            self._list.addItem(item)
        if not calls:
            empty = QListWidgetItem("통화 기록 부재")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(empty)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        # 통화 재개 signal emit
        peer_id = item.data(Qt.ItemDataRole.UserRole)
        if peer_id:
            self.call_initiated.emit(peer_id)
