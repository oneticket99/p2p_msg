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
    folder_selected = pyqtSignal(str)  # cycle 169.74 — telegram folder column 통합

    # cycle 169.131 — telegram align tab def (사용자 ack — 채팅/연락처/통화/설정)
    # key retain (main_window mapping 무중단) + label/icon 만 재배치
    TAB_DEFS = [
        ("friends", "채팅", "home"),
        ("rooms", "연락처", "friends"),
        ("bots", "통화", "phone"),
        ("settings", "설정", "settings"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarRail")
        # cycle 169.138 — sub-agent A drift D-1 — width 96 → 72 (telegram desktop align)
        self.setFixedWidth(72)

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
            # cycle 169.138 — sub-agent A drift D-4 — icon size 28→24 (telegram align)
            btn.setIcon(load_icon(icon_name, size=24, color="#9ca3af"))
            btn.setIconSize(QSize(24, 24))
            btn.setToolTip(label)
            btn.setFixedSize(56, 56)
            # cycle 169.111 회수 — inline QSS 폐기 → base-dark.qss QSS#sidebarTab selector delegate
            # hover/active/checked state qss chain 단일 source of truth
            btn.clicked.connect(  # type: ignore[arg-type]
                lambda _checked, key=tab_key: self.tab_clicked.emit(key)
            )
            self._button_group.addButton(btn, i)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self._buttons[tab_key] = btn

        # 한글 주석 — 첫 tab default active
        if self._buttons:
            self._buttons["friends"].setChecked(True)

        # cycle 169.119 회수 — folder_defs (모든대화방/안읽음/편집) 폐기
        # 사용자 비판 image #29~32 — TAB icon (홈/설정) + folder 중복 + 정렬 불일치
        # tab friends/rooms/bots/settings 만 retain — 검색 + folder = drawer 또는 search dialog 의무
        self._folder_buttons: dict[str, QToolButton] = {}

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
