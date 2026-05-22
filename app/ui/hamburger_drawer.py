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
from app.i18n.labels import tr as _tr


class HamburgerDrawer(QFrame):
    """좌상단 햄버거 click → 9 entry menu drawer.

    cycle 169.115 회수 — QDialog popup 폐기 → QFrame child overlay (main_window 내부).
    parent.installEventFilter — outside click 시 close.
    """

    profile_clicked = pyqtSignal()
    new_group_clicked = pyqtSignal()
    new_channel_clicked = pyqtSignal()
    contacts_clicked = pyqtSignal()
    calls_clicked = pyqtSignal()
    saved_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    night_mode_toggled = pyqtSignal(bool)
    logout_clicked = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, username: str = "사용자", nickname: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # cycle 169.303 — width 320 → 256 (사용자 directive 20% 감소)
        self.setFixedWidth(256)
        self.setMinimumHeight(560)
        # 한글 주석 — child overlay 의 의 bg solid + raise_() 의무
        self.setAutoFillBackground(True)
        # cycle 169.248 — objectName specific selector (child QFrame 의 border-right inherit 차단 회수 사용자 critique image #5/6)
        self.setObjectName("hamburgerDrawer")
        self.setStyleSheet(
            "QFrame#hamburgerDrawer { background-color: #0F172A; border-right: 1px solid #1f2937; }"
        )
        # 한글 주석 — parent 의 의 event filter — outside click → close
        if parent is not None:
            parent.installEventFilter(self)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # cycle 169.227 — gradient 폐기 → 단색 Toonation BI #0066FF (사용자 directive image #34)
        header = QFrame()
        header.setStyleSheet("background-color: #0066FF;")
        header.setFixedHeight(120)
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(20, 20, 20, 12)
        h_layout.setSpacing(4)
        # cycle 169.254 — avatar 좌측 정렬 + name avatar 기준 center (사용자 directive image #14)
        from app.ui._avatar_helper import make_initial_pixmap
        avatar = QLabel()
        avatar.setFixedSize(48, 48)
        # cycle 169.403~404 — instance attribute retain + avatar source = nickname 우선 (사용자 critique image #175)
        self._avatar_label = avatar
        avatar_text = nickname or username or "사용자"
        self._username = avatar_text
        avatar.setPixmap(make_initial_pixmap(avatar_text, size=48))
        avatar.setStyleSheet("border-radius: 24px;")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignLeft)
        name_label = QLabel(avatar_text)
        self._name_label = name_label  # cycle 169.403 — update_user_info chain entry
        # cycle 169.254 — fixedWidth=avatar(48) + AlignCenter → name 의 horizontal center = avatar center column align
        name_label.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 600;")
        name_label.setFixedWidth(48)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignLeft)
        # cycle 169.119 — 이모지 상태 설정 폐기 (사용자 directive)
        outer.addWidget(header)

        # 한글 주석 — 9 menu entry
        # cycle 169.409 — 실 기능 정합 SVG icon mapping (사용자 directive image #179)
        # 채널=broadcast, 연락처=contacts, 저장한 메시지=bookmark, 로그아웃=logout 신설 chain.
        menu_defs = [
            ("account", _tr("내_프로필"), self.profile_clicked),
            ("friends", _tr("그룹_만들기"), self.new_group_clicked),
            ("broadcast", _tr("채널_만들기"), self.new_channel_clicked),
            ("contacts", _tr("연락처"), self.contacts_clicked),
            ("phone", _tr("전화"), self.calls_clicked),
            ("bookmark", _tr("저장한_메시지"), self.saved_clicked),
            ("settings", _tr("설정"), self.settings_clicked),
        ]
        for icon_name, label, signal in menu_defs:
            btn = self._build_menu_entry(icon_name, label)
            btn.clicked.connect(signal.emit)  # type: ignore[arg-type]
            outer.addWidget(btn)

        # cycle 169.409~411 — 야간 모드 row 의 click 시점 즉시 toggle (체크박스 폐기, image #179)
        # cycle 169.411 — visual indicator 우측 state badge (켜짐/꺼짐 + color swap)
        self._night_state = True  # default = night mode on
        night_btn = self._build_menu_entry("theme", _tr("야간_모드"))
        night_btn.clicked.connect(self._on_night_toggle)  # type: ignore[arg-type]
        self._night_btn = night_btn
        outer.addWidget(night_btn)
        self._refresh_night_btn_visual()

        outer.addStretch(1)

        # 한글 주석 — 로그아웃 button (하단)
        logout_btn = self._build_menu_entry("logout", _tr("로그아웃"))
        logout_btn.clicked.connect(self.logout_clicked.emit)  # type: ignore[arg-type]
        outer.addWidget(logout_btn)

        # 한글 주석 — footer (TooTalk version)
        footer = QLabel("TooTalk · Phase 1")
        footer.setStyleSheet("color: #6b7280; font-size: 11px; padding: 12px 20px;")
        outer.addWidget(footer)

    def showEvent(self, event):  # type: ignore[override]
        """slide-in animation — left edge 부터 320px width drawer pos animate (cycle 169.114)."""
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

    def eventFilter(self, obj, event):
        """parent main_window outside click → drawer close (cycle 169.115)."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.MouseButtonPress and obj is self.parent():
            pos = event.pos()
            if not self.geometry().contains(pos):
                self.close_drawer()
                return True
        return super().eventFilter(obj, event)

    def close_drawer(self) -> None:
        """cycle 169.303 — slide-out animation (역방향) + close.

        사용자 directive — 외부 click / hamburger re-click 시점 slide-out animation 재생 후 close.
        """
        from PyQt6.QtCore import QPropertyAnimation, QPoint, QEasingCurve
        # 한글 주석 — 중복 close 차단 (animation 중 재진입 회피)
        if getattr(self, "_closing", False):
            return
        self._closing = True
        parent = self.parent()
        if parent is not None:
            parent.removeEventFilter(self)
        current_pos = self.pos()
        end_pos = QPoint(current_pos.x() - self.width(), current_pos.y())
        anim = QPropertyAnimation(self, b"pos", self)
        anim.setDuration(180)
        anim.setStartValue(current_pos)
        anim.setEndValue(end_pos)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)

        def _on_finished():
            self.hide()
            self.closed.emit()
            self.deleteLater()

        anim.finished.connect(_on_finished)  # type: ignore[arg-type]
        anim.start()
        self._slide_out_anim = anim  # GC 차단

    def keyPressEvent(self, event):
        """ESC key → close (cycle 169.115)."""
        if event.key() == Qt.Key.Key_Escape:
            self.close_drawer()
            return
        super().keyPressEvent(event)

    def exec(self) -> int:
        """QDialog compat shim — show + raise (cycle 169.115)."""
        self.show()
        self.raise_()
        self.setFocus()
        return 0

    def _on_night_toggle(self) -> None:
        """cycle 169.409~411 — 야간 모드 row click 시점 즉시 toggle + visual update + signal emit."""
        self._night_state = not self._night_state
        self._refresh_night_btn_visual()
        self.night_mode_toggled.emit(self._night_state)

    def _refresh_night_btn_visual(self) -> None:
        """cycle 169.411 — 야간 모드 button 우측 state badge + icon color swap (visual indicator)."""
        btn = getattr(self, "_night_btn", None)
        if btn is None:
            return
        from app.ui._icons import load_icon as _load_icon
        # 한글 주석 — 켜짐 = Toonation BI #0066FF, 꺼짐 = grey
        on = self._night_state
        icon_color = "#0066FF" if on else "#9ca3af"
        state_text = _tr("켜짐") if on else _tr("꺼짐")
        btn.setIcon(_load_icon("theme", size=20, color=icon_color))
        # 한글 주석 — 라벨 우측 state badge inline 합성 (button text 활용)
        btn.setText(f"  {_tr('야간_모드')}    ·  {state_text}")
        bg_hover = "rgba(0, 102, 255, 0.12)" if on else "rgba(156, 163, 175, 0.08)"
        accent = "#0066FF" if on else "#6b7280"
        btn.setStyleSheet(
            "QPushButton {"
            " text-align: left;"
            " padding-left: 20px;"
            " background-color: transparent;"
            " border: none;"
            f" color: {accent if on else '#e5e7eb'};"
            " font-size: 14px;"
            "}"
            f" QPushButton:hover {{ background-color: {bg_hover}; }}"
        )

    def update_user_info(self, nickname: str) -> None:
        """cycle 169.403 — drawer header username + avatar 동적 갱신 (사용자 critique image #171)."""
        if not nickname:
            return
        self._username = nickname
        if hasattr(self, "_name_label") and self._name_label is not None:
            self._name_label.setText(nickname)
        if hasattr(self, "_avatar_label") and self._avatar_label is not None:
            self._avatar_label.setPixmap(make_initial_pixmap(nickname, size=48))

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
