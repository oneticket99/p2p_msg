# SPDX-License-Identifier: GPL-3.0-or-later
"""SidebarRail — 메인 윈도우 좌측 64px vertical tab column (cycle 153 phase 3).

텔레그램 desktop 3 column 의 left rail 등가 — 4 tab vertical (친구 + 방 + 봇 + 설정).
정합 = telegram-ui-survey.md §5 + toonation-brand-integration-plan §4.3.

signal:
    tab_clicked(str) — tab key ("friends" / "rooms" / "bots" / "settings") emit
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._icons import load_icon


class SidebarRail(QFrame):
    """좌측 64px vertical tab column — 4 tab + brand 통합 highlight."""

    tab_clicked = pyqtSignal(str)
    hamburger_clicked = pyqtSignal()

    TAB_DEFS = [
        ("friends", "친구", "friends"),
        ("rooms", "방", "home"),
        ("bots", "봇", "bot"),
        ("settings", "설정", "settings"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarRail")
        self.setFixedWidth(64)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 한글 주석 — cycle 169.56 회수 — 좌상단 햄버거 menu button (drawer 진입)
        hamburger_btn = QToolButton()
        hamburger_btn.setIcon(load_icon("menu", size=24, color="#9ca3af"))
        hamburger_btn.setIconSize(QSize(24, 24))
        hamburger_btn.setFixedSize(56, 48)
        hamburger_btn.setToolTip("메뉴")
        hamburger_btn.setStyleSheet(
            "QToolButton {"
            " background-color: transparent;"
            " border: none;"
            " border-radius: 6px;"
            "}"
            " QToolButton:hover { background-color: rgba(0, 102, 255, 0.1); }"
        )
        hamburger_btn.clicked.connect(self.hamburger_clicked.emit)  # type: ignore[arg-type]
        layout.addWidget(hamburger_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(8)

        # 한글 주석 — QButtonGroup 의 mutually exclusive 토글 (one active 의 의무)
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._buttons: dict[str, QToolButton] = {}
        for i, (tab_key, label, icon_name) in enumerate(self.TAB_DEFS):
            btn = QToolButton()
            btn.setObjectName("sidebarTab")
            btn.setCheckable(True)
            # 한글 주석 — cycle 169.51 회수 — SVG icon (gray default + cyan checked)
            btn.setIcon(load_icon(icon_name, size=28, color="#9ca3af"))
            btn.setIconSize(QSize(28, 28))
            btn.setToolTip(label)
            btn.setFixedSize(56, 56)
            btn.setStyleSheet(
                "QToolButton#sidebarTab {"
                " background-color: transparent;"
                " border: none;"
                " border-radius: 6px;"
                "}"
                "QToolButton#sidebarTab:hover {"
                " background-color: rgba(0, 102, 255, 0.1);"
                "}"
                "QToolButton#sidebarTab:checked {"
                " background-color: rgba(0, 102, 255, 0.2);"
                " border-left: 3px solid #0066FF;"
                "}"
            )
            btn.clicked.connect(  # type: ignore[arg-type]
                lambda _checked, key=tab_key: self.tab_clicked.emit(key)
            )
            self._button_group.addButton(btn, i)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self._buttons[tab_key] = btn

        # 한글 주석 — 첫 tab default active
        if self._buttons:
            self._buttons["friends"].setChecked(True)

        layout.addStretch(1)

    def set_active_tab(self, tab_key: str) -> None:
        """외부 단 active tab 변경 — programmatic switch."""
        if tab_key in self._buttons:
            self._buttons[tab_key].setChecked(True)

    def active_tab(self) -> str:
        """현 active tab key."""
        for key, btn in self._buttons.items():
            if btn.isChecked():
                return key
        return "friends"
