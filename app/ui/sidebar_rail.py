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

    # cycle 169.185 — telegram align (사용자 critique image #20) — home + phone icon 폐기
    # 2 entry only — "모든 대화방" (chat bubble) + "편집" (sliders)
    # folder list (모니터링/업무협조 등) = 별 cycle 본격 binding scope (telegram folder feature)
    TAB_DEFS = [
        ("friends", "모든 대화방", "chat_bubble"),
        ("settings", "편집", "edit"),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebarRail")
        # cycle 169.374 — width 72 → 80 (icon + text label 정합, 사용자 directive image #130)
        self.setFixedWidth(80)

        # cycle 169.182 — top bar 한 라인 align (image #15 critique)
        # hamburger row top = height 60 (chat_list search + chat_header 정합)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 한글 주석 — cycle 169.56 회수 — 좌상단 햄버거 menu button (drawer 진입)
        hamburger_btn = QToolButton()
        hamburger_btn.setIcon(load_icon("menu", size=24, color="#9ca3af"))
        hamburger_btn.setIconSize(QSize(24, 24))
        # cycle 169.182 — height 60 fixed (top bar align)
        hamburger_btn.setFixedSize(56, 60)
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
        # cycle 169.182 — top bar 60 align — border-bottom row separator
        layout.addSpacing(12)

        # 한글 주석 — QButtonGroup 의 mutually exclusive 토글 (one active 의 의무)
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._buttons: dict[str, QToolButton] = {}
        for i, (tab_key, label, icon_name) in enumerate(self.TAB_DEFS):
            btn = QToolButton()
            btn.setObjectName("sidebarTab")
            btn.setCheckable(True)
            # cycle 169.138 — icon size 28→24 + cycle 169.374 image #130 — text label 표시
            btn.setIcon(load_icon(icon_name, size=22, color="#9ca3af"))
            btn.setIconSize(QSize(22, 22))
            btn.setText(self._wrap_label(label))
            btn.setToolTip(label)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setFixedSize(72, 72)
            btn.setStyleSheet(
                "QToolButton#sidebarTab {"
                " color: #9ca3af; background-color: transparent;"
                " border: none; border-radius: 6px; font-size: 10px; font-weight: 500;"
                " padding-top: 4px; padding-bottom: 2px;"
                "}"
                "QToolButton#sidebarTab:hover { background-color: rgba(0, 102, 255, 0.1); color: #e5e7eb; }"
                "QToolButton#sidebarTab:checked { background-color: rgba(0, 102, 255, 0.2); color: #0066FF; }"
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

        # cycle 169.119 회수 — folder_defs (모든대화방/안읽음/편집) 폐기
        # 사용자 비판 image #29~32 — TAB icon (홈/설정) + folder 중복 + 정렬 불일치
        # tab friends/rooms/bots/settings 만 retain — 검색 + folder = drawer 또는 search dialog 의무
        self._folder_buttons: dict[str, QToolButton] = {}

        layout.addStretch(1)

    @staticmethod
    def _wrap_label(text: str) -> str:
        """cycle 169.377 — sidebar label 줄내림 helper (사용자 critique image #132 elided 회수).

        4 char 이하 = single line. 띄어쓰기 안 break (1회). 부재 + 5+ char = mid-split.
        """
        text = text.strip()
        if len(text) <= 4:
            return text
        if " " in text:
            return text.replace(" ", "\n", 1)
        mid = (len(text) + 1) // 2
        return text[:mid] + "\n" + text[mid:8]

    def set_folder_entries(self, folders: list) -> None:
        """cycle 169.376 — user folder entry 동적 갱신 (사용자 critique image #131).

        편집 button 의 sidebar 최하단 위치 의무 — folder button = 편집 button 之前 insert.
        folders = list[dict] (folder_id + name + color_name).
        """
        layout = self.layout()
        # 한글 주석 — 기존 folder button 제거
        for fid, btn in list(self._folder_buttons.items()):
            layout.removeWidget(btn)
            btn.deleteLater()
        self._folder_buttons.clear()
        # cycle 169.376 — 편집 button index detect (folder insert anchor)
        edit_btn = self._buttons.get("settings")
        edit_idx = layout.indexOf(edit_btn) if edit_btn is not None else (layout.count() - 1)
        # 한글 주석 — 신규 folder button 추가 (편집 tab 之前 insert) — cycle 169.374 image #130 정합
        # folder SVG icon (top) + name label (bottom) — QToolButton ToolButtonTextUnderIcon style
        for folder in folders or []:
            fid = str(folder.get("folder_id", ""))
            name = folder.get("name", "?")
            if not fid:
                continue
            btn = QToolButton()
            btn.setObjectName("sidebarFolder")
            btn.setCheckable(True)
            btn.setIcon(load_icon("folder", size=22, color="#9ca3af"))
            btn.setIconSize(QSize(22, 22))
            btn.setText(self._wrap_label(name))
            btn.setToolTip(name)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setFixedSize(72, 72)
            btn.setStyleSheet(
                "QToolButton {"
                " color: #9ca3af; background-color: transparent;"
                " border: none; border-radius: 6px; font-size: 10px; font-weight: 500;"
                " padding-top: 4px; padding-bottom: 2px;"
                "}"
                "QToolButton:hover { background-color: rgba(0, 102, 255, 0.1); color: #e5e7eb; }"
                "QToolButton:checked { background-color: rgba(0, 102, 255, 0.2); color: #0066FF; }"
            )
            btn.clicked.connect(  # type: ignore[arg-type]
                lambda _checked, f=fid: self.folder_selected.emit(f)
            )
            self._button_group.addButton(btn)
            # cycle 169.376 — 편집 button 之前 insert (편집 = 최하단 의무)
            layout.insertWidget(edit_idx, btn, alignment=Qt.AlignmentFlag.AlignCenter)
            edit_idx += 1
            self._folder_buttons[fid] = btn

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
