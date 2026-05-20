# SPDX-License-Identifier: GPL-3.0-or-later
"""MyProfileDialog — telegram desktop 내 프로필 modal (cycle 169.56 신설)."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._icons import load_icon, load_pixmap


class MyProfileDialog(QDialog):
    """내 프로필 — avatar 큰 + 사용자명 + phone + username + 생년월일."""

    edit_requested = pyqtSignal()

    def __init__(
        self,
        username: str = "",
        phone: str = "",
        email: str = "",
        birthdate: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 내 프로필")
        self.setModal(True)
        # cycle 169.121 회수 — frameless modal (텔레그램 align)
        # 사용자 directive image #23/24 — dialog 아닌 modal 의무
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(420, 600)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # header — menu + edit pencil + X
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet("background-color: #1F2937;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 8, 12, 8)
        menu_btn = QPushButton()
        menu_btn.setIcon(load_icon("menu", size=20, color="#9ca3af"))
        menu_btn.setFixedSize(36, 36)
        menu_btn.setFlat(True)
        h_layout.addWidget(menu_btn)
        h_layout.addStretch(1)
        edit_btn = QPushButton()
        edit_btn.setIcon(load_icon("more", size=20, color="#9ca3af"))
        edit_btn.setFixedSize(36, 36)
        edit_btn.setFlat(True)
        edit_btn.clicked.connect(self.edit_requested.emit)  # type: ignore[arg-type]
        h_layout.addWidget(edit_btn)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 36)
        close_btn.setFlat(True)
        close_btn.setStyleSheet("color: #9ca3af; font-size: 16px;")
        close_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        h_layout.addWidget(close_btn)
        outer.addWidget(header)

        # 큰 avatar + name + 온라인
        body = QFrame()
        body.setStyleSheet("background-color: #131C30;")
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(24, 32, 24, 24)
        b_layout.setSpacing(12)

        avatar = QLabel()
        avatar.setFixedSize(140, 140)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setPixmap(load_pixmap("avatar", size=100, color="#67E8F9"))
        avatar.setStyleSheet("background-color: #1F2937; border-radius: 70px;")
        b_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignCenter)

        name_label = QLabel(username or "사용자")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: #e5e7eb; font-size: 22px; font-weight: 700;")
        b_layout.addWidget(name_label)

        status_label = QLabel("온라인")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet("color: #22D3EE; font-size: 14px;")
        b_layout.addWidget(status_label)

        b_layout.addSpacing(20)

        # phone + username + 생년월일 row 3종
        for label_text, value, icon_name in [
            ("전화번호", phone, "phone"),
            ("사용자명", f"@{username}" if username else "", "account"),
            ("이메일", email, "notification"),
            ("생년월일", birthdate or "부재", "data"),
        ]:
            self._build_info_row(b_layout, label_text, value, icon_name)

        b_layout.addStretch(1)
        outer.addWidget(body, stretch=1)

    def _build_info_row(self, layout: QVBoxLayout, label_text: str, value: str, icon_name: str) -> None:
        """단일 info row — icon + label + value (read-only)."""
        row = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(load_pixmap(icon_name, size=20, color="#9ca3af"))
        icon.setFixedWidth(28)
        row.addWidget(icon)
        col = QVBoxLayout()
        col.setSpacing(2)
        val = QLabel(value or "부재")
        val.setStyleSheet("color: #67E8F9; font-size: 14px; font-weight: 600;")
        col.addWidget(val)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
        col.addWidget(lbl)
        row.addLayout(col, stretch=1)
        layout.addLayout(row)
