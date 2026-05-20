# SPDX-License-Identifier: GPL-3.0-or-later
"""ChatHeader — 메인 윈도우 우측 상단 56px header bar (cycle 153 phase 3).

텔레그램 desktop 3 column 의 right column 상단 등가 — avatar + name + status + control button.
정합 = telegram-ui-survey.md §5+§6 + toonation-brand-integration-plan §4.3.

signal:
    search_clicked() — header 안 검색 icon click
    call_clicked() — 통화 icon (cycle 200+ entry)
    menu_clicked() — 메뉴 (⋯) icon click
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._icons import load_icon, load_pixmap


class ChatHeader(QFrame):
    """우측 상단 header bar — avatar + name + status + 3 control button."""

    search_clicked = pyqtSignal()
    call_clicked = pyqtSignal()
    menu_clicked = pyqtSignal()
    sidebar_toggled = pyqtSignal()  # cycle 169.61 — telegram desktop sidebar toggle
    pinned_dismissed = pyqtSignal()  # cycle 169.72 — pinned message close click

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("chatHeader")
        # cycle 169.130 — sub-agent A drift D-32 — 56→60 (qss min-height 정합)
        self.setFixedHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 한글 주석 — cycle 169.52 회수 — SVG avatar placeholder (emoji 폐기)
        self._avatar_label = QLabel()
        self._avatar_label.setFixedSize(40, 40)
        self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_label.setStyleSheet(
            "background-color: #1F2937;"
            " border-radius: 20px;"
        )
        self._avatar_label.setPixmap(load_pixmap("avatar", size=24, color="#67E8F9"))
        layout.addWidget(self._avatar_label)

        # 한글 주석 — name + status vbox
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self._name_label = QLabel("")
        self._name_label.setObjectName("chatHeaderName")
        self._name_label.setStyleSheet("color: #e5e7eb; font-size: 15px; font-weight: 600;")
        info_layout.addWidget(self._name_label)

        self._status_label = QLabel("")
        self._status_label.setObjectName("chatHeaderStatus")
        self._status_label.setStyleSheet("color: #67E8F9; font-size: 12px;")
        info_layout.addWidget(self._status_label)

        layout.addLayout(info_layout, stretch=1)

        # 한글 주석 — cycle 169.61 회수 — 4 control SVG icon (search + phone + sidebar toggle + more)
        for icon_name, signal_attr in [
            ("search", "search_clicked"),
            ("phone", "call_clicked"),
            ("menu", "sidebar_toggled"),
            ("more", "menu_clicked"),
        ]:
            btn = QPushButton()
            btn.setProperty("variant", "ghost")
            btn.setFlat(True)
            btn.setFixedSize(36, 36)
            btn.setIcon(load_icon(icon_name, size=20, color="#9ca3af"))
            btn.setIconSize(QSize(20, 20))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton {"
                " background-color: transparent;"
                " border: none;"
                " border-radius: 18px;"
                "}"
                "QPushButton:hover {"
                " background-color: rgba(0, 102, 255, 0.1);"
                "}"
            )
            sig = getattr(self, signal_attr)
            btn.clicked.connect(lambda _c=False, s=sig: s.emit())  # type: ignore[arg-type]
            layout.addWidget(btn)

    def set_chat(self, name: str, status: str = "", avatar_emoji: str = "") -> None:
        """현 활성 chat 정보 갱신. avatar_emoji arg = legacy compat (무시)."""
        self._name_label.setText(name)
        self._status_label.setText(status)

    def clear_chat(self) -> None:
        """chat 선택 해제 — placeholder text 부재 (cycle 169.100 회수 — 사용자 directive)."""
        self._name_label.setText("")
        self._status_label.setText("")

    def set_pinned_message(self, title: str, preview: str) -> None:
        """pinned message bar title + preview set (cycle 169.72 신설)."""
        # 한글 주석 — pinned widget lazy create
        bar = getattr(self, "_pinned_bar", None)
        if bar is None:
            from PyQt6.QtWidgets import QFrame as _QFrame, QPushButton as _QPushButton
            bar = _QFrame(self.parentWidget() if self.parentWidget() else self)
            bar.setFixedHeight(48)
            bar.setStyleSheet(
                "QFrame { background-color: #131C30; border-left: 3px solid #22D3EE;"
                " border-radius: 0; }"
            )
            b_layout = QHBoxLayout(bar)
            b_layout.setContentsMargins(16, 6, 16, 6)
            b_layout.setSpacing(8)
            col = QVBoxLayout()
            col.setSpacing(2)
            pin_title = QLabel("고정된 메시지", bar)
            pin_title.setStyleSheet("color: #22D3EE; font-size: 11px; font-weight: 700;")
            col.addWidget(pin_title)
            pin_preview = QLabel("", bar)
            pin_preview.setStyleSheet("color: #e5e7eb; font-size: 13px;")
            col.addWidget(pin_preview)
            b_layout.addLayout(col, stretch=1)
            close_btn = _QPushButton("✕", bar)
            close_btn.setFixedSize(28, 28)
            close_btn.setFlat(True)
            close_btn.setStyleSheet("color: #9ca3af; font-size: 14px; border: none;")
            close_btn.clicked.connect(self.pinned_dismissed.emit)  # type: ignore[arg-type]
            b_layout.addWidget(close_btn)
            self._pinned_bar = bar
            self._pinned_title = pin_title
            self._pinned_preview = pin_preview
        self._pinned_title.setText(title or "고정된 메시지")
        self._pinned_preview.setText(preview)
        bar.setVisible(True)

    def hide_pinned(self) -> None:
        """pinned message bar hide."""
        bar = getattr(self, "_pinned_bar", None)
        if bar is not None:
            bar.setVisible(False)
