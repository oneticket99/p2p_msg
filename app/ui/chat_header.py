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

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ChatHeader(QFrame):
    """우측 상단 header bar — avatar + name + status + 3 control button."""

    search_clicked = pyqtSignal()
    call_clicked = pyqtSignal()
    menu_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("chatHeader")
        self.setFixedHeight(56)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 한글 주석 — avatar circle placeholder (cycle 154 actual SVG/QPixmap 의무)
        self._avatar_label = QLabel("👤")
        self._avatar_label.setFixedSize(40, 40)
        self._avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._avatar_label.setStyleSheet(
            "background-color: #1F2937;"
            " border-radius: 20px;"
            " font-size: 20px;"
            " color: #67E8F9;"
        )
        layout.addWidget(self._avatar_label)

        # 한글 주석 — name + status vbox
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self._name_label = QLabel("chat 선택 부재")
        self._name_label.setObjectName("chatHeaderName")
        self._name_label.setStyleSheet("color: #e5e7eb; font-size: 15px; font-weight: 600;")
        info_layout.addWidget(self._name_label)

        self._status_label = QLabel("")
        self._status_label.setObjectName("chatHeaderStatus")
        self._status_label.setStyleSheet("color: #67E8F9; font-size: 12px;")
        info_layout.addWidget(self._status_label)

        layout.addLayout(info_layout, stretch=1)

        # 한글 주석 — 3 control button (검색 + 통화 + 메뉴)
        for icon, signal_attr in [
            ("🔍", "search_clicked"),
            ("📞", "call_clicked"),
            ("⋯", "menu_clicked"),
        ]:
            btn = QPushButton(icon)
            btn.setProperty("variant", "ghost")
            btn.setFlat(True)
            btn.setFixedSize(36, 36)
            btn.setStyleSheet(
                "QPushButton {"
                " font-size: 18px;"
                " background-color: transparent;"
                " border: none;"
                " border-radius: 18px;"
                " color: #9ca3af;"
                "}"
                "QPushButton:hover {"
                " background-color: rgba(0, 102, 255, 0.1);"
                " color: #67E8F9;"
                "}"
            )
            sig = getattr(self, signal_attr)
            btn.clicked.connect(lambda _c=False, s=sig: s.emit())  # type: ignore[arg-type]
            layout.addWidget(btn)

    def set_chat(self, name: str, status: str = "", avatar_emoji: str = "👤") -> None:
        """현 활성 chat 정보 갱신."""
        self._name_label.setText(name)
        self._status_label.setText(status)
        self._avatar_label.setText(avatar_emoji)

    def clear_chat(self) -> None:
        """chat 선택 해제 — placeholder text."""
        self._name_label.setText("chat 선택 부재")
        self._status_label.setText("")
        self._avatar_label.setText("👤")
