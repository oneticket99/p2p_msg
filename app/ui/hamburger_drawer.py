# SPDX-License-Identifier: GPL-3.0-or-later
"""HamburgerDrawer — telegram desktop 좌측 햄버거 menu drawer (cycle 169.56 신설).

사용자 directive verbatim reference image — 햄버거 menu 안 9 entry.
modal QDialog + slide-in 좌측 320px + avatar + 사용자명 + 9 menu action.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._icons import load_icon, load_pixmap


class HamburgerDrawer(QDialog):
    """좌상단 햄버거 click → 9 entry menu drawer (modal)."""

    profile_clicked = pyqtSignal()
    new_group_clicked = pyqtSignal()
    new_channel_clicked = pyqtSignal()
    contacts_clicked = pyqtSignal()
    calls_clicked = pyqtSignal()
    saved_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    night_mode_toggled = pyqtSignal(bool)
    logout_clicked = pyqtSignal()

    def __init__(self, username: str = "사용자", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 메뉴")
        self.setModal(True)
        self.setFixedWidth(320)
        self.setMinimumHeight(560)
        # cycle 169.99 회수 — image #11 별도 OS window decoration 제거
        # frameless + popup → 메인 window 안 sliding panel feel (telegram align)
        from PyQt6.QtCore import Qt as _Qt
        self.setWindowFlags(_Qt.WindowType.FramelessWindowHint | _Qt.WindowType.Popup)
        self.setAttribute(_Qt.WidgetAttribute.WA_TranslucentBackground, False)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 한글 주석 — header (avatar + 사용자명 + 이모지 상태)
        header = QFrame()
        header.setStyleSheet("background-color: #1F2937;")
        header.setFixedHeight(120)
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(20, 20, 20, 12)
        h_layout.setSpacing(4)
        avatar = QLabel()
        avatar.setFixedSize(48, 48)
        avatar.setPixmap(load_pixmap("avatar", size=48, color="#67E8F9"))
        avatar.setStyleSheet("border-radius: 24px; background-color: #0F172A;")
        h_layout.addWidget(avatar)
        name_label = QLabel(username)
        name_label.setStyleSheet("color: #e5e7eb; font-size: 15px; font-weight: 600;")
        h_layout.addWidget(name_label)
        status_label = QLabel("이모지 상태 설정")
        status_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        h_layout.addWidget(status_label)
        outer.addWidget(header)

        # 한글 주석 — 9 menu entry
        menu_defs = [
            ("account", "내 프로필", self.profile_clicked),
            ("friends", "그룹 만들기", self.new_group_clicked),
            ("notification", "채널 만들기", self.new_channel_clicked),
            ("account", "연락처", self.contacts_clicked),
            ("phone", "전화", self.calls_clicked),
            ("data", "저장한 메시지", self.saved_clicked),
            ("settings", "설정", self.settings_clicked),
        ]
        for icon_name, label, signal in menu_defs:
            btn = self._build_menu_entry(icon_name, label)
            btn.clicked.connect(signal.emit)  # type: ignore[arg-type]
            outer.addWidget(btn)

        # 한글 주석 — 야간 모드 toggle row
        night_row = QFrame()
        night_layout = QHBoxLayout(night_row)
        night_layout.setContentsMargins(20, 12, 20, 12)
        night_icon = QLabel()
        night_icon.setPixmap(load_pixmap("theme", size=20, color="#9ca3af"))
        night_layout.addWidget(night_icon)
        night_label = QLabel("야간 모드")
        night_label.setStyleSheet("color: #e5e7eb; font-size: 14px;")
        night_layout.addWidget(night_label, stretch=1)
        self._night_check = QCheckBox()
        self._night_check.setChecked(True)
        self._night_check.toggled.connect(self.night_mode_toggled.emit)  # type: ignore[arg-type]
        night_layout.addWidget(self._night_check)
        outer.addWidget(night_row)

        outer.addStretch(1)

        # 한글 주석 — 로그아웃 button (하단)
        logout_btn = self._build_menu_entry("more", "로그아웃")
        logout_btn.clicked.connect(self.logout_clicked.emit)  # type: ignore[arg-type]
        outer.addWidget(logout_btn)

        # 한글 주석 — footer (TooTalk version)
        footer = QLabel("TooTalk · Phase 1")
        footer.setStyleSheet("color: #6b7280; font-size: 11px; padding: 12px 20px;")
        outer.addWidget(footer)

    def showEvent(self, event):  # type: ignore[override]
        """slide-in animation — left edge 부터 320px width drawer 의 의 pos 의 animate (cycle 169.114)."""
        super().showEvent(event)
        from PyQt6.QtCore import QPropertyAnimation, QPoint, QEasingCurve
        target_pos = self.pos()
        start_pos = QPoint(target_pos.x() - self.width(), target_pos.y())
        self.move(start_pos)
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(220)
        anim.setStartValue(start_pos)
        anim.setEndValue(target_pos)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._slide_anim = anim  # GC 차단 의무 — Python ref 보존

    def _build_menu_entry(self, icon_name: str, label: str) -> QPushButton:
        """단일 menu row button — icon + label."""
        btn = QPushButton(f"  {label}")
        btn.setIcon(load_icon(icon_name, size=20, color="#9ca3af"))
        btn.setIconSize(QSize(20, 20))
        btn.setFixedHeight(48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton {"
            " text-align: left;"
            " padding-left: 20px;"
            " background-color: transparent;"
            " border: none;"
            " color: #e5e7eb;"
            " font-size: 14px;"
            "}"
            " QPushButton:hover { background-color: rgba(0, 102, 255, 0.08); }"
        )
        return btn
