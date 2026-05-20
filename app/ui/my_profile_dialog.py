# SPDX-License-Identifier: GPL-3.0-or-later
"""MyProfileDialog — telegram desktop 내 프로필 modal (cycle 169.186 telegram rewrite).

avatar 폐기 + 단순 list row pattern + crash 회수 (load_pixmap chain 폐기).
사용자 image #22 align — title + name + entry list.
"""

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


class MyProfileDialog(QDialog):
    """내 프로필 — telegram align simple list modal."""

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
        # cycle 169.121 — frameless modal (텔레그램 align)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setFixedSize(380, 480)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 한글 주석 — header title + close X (cycle 169.186 — telegram simple)
        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet("background-color: #1F2937;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 8, 0)
        h_layout.setSpacing(0)
        title = QLabel("내 프로필")
        title.setStyleSheet("color: #e5e7eb; font-size: 16px; font-weight: 600;")
        h_layout.addWidget(title)
        h_layout.addStretch(1)
        edit_btn = QPushButton("편집")
        edit_btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; color: #0066FF; font-size: 14px; padding: 6px 10px; }"
            " QPushButton:hover { color: #1a75ff; }"
        )
        edit_btn.clicked.connect(self.edit_requested.emit)  # type: ignore[arg-type]
        h_layout.addWidget(edit_btn)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 36)
        close_btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; color: #9ca3af; font-size: 18px; }"
            " QPushButton:hover { color: #e5e7eb; }"
        )
        close_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        h_layout.addWidget(close_btn)
        outer.addWidget(header)

        # 한글 주석 — body (name + info rows)
        body = QFrame()
        body.setStyleSheet("background-color: #131C30;")
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(24, 32, 24, 24)
        b_layout.setSpacing(8)

        # name large (avatar 폐기 — 사용자 directive cycle 169.182)
        name_label = QLabel(username or "사용자")
        name_label.setStyleSheet("color: #e5e7eb; font-size: 24px; font-weight: 700;")
        b_layout.addWidget(name_label)

        # @username
        if username:
            uname_label = QLabel(f"@{username}")
            uname_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
            b_layout.addWidget(uname_label)

        b_layout.addSpacing(24)

        # info rows (label + value 단일 column)
        for label_text, value in [
            ("전화번호", phone or "부재"),
            ("이메일", email or "부재"),
            ("생년월일", birthdate or "부재"),
        ]:
            self._build_info_row(b_layout, label_text, value)

        b_layout.addStretch(1)
        outer.addWidget(body, stretch=1)

    def _build_info_row(self, layout: QVBoxLayout, label_text: str, value: str) -> None:
        """단일 info row — label + value (vertical stack)."""
        wrap = QFrame()
        wrap_layout = QVBoxLayout(wrap)
        wrap_layout.setContentsMargins(0, 8, 0, 8)
        wrap_layout.setSpacing(2)
        val = QLabel(value)
        val.setStyleSheet("color: #e5e7eb; font-size: 15px;")
        wrap_layout.addWidget(val)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #9ca3af; font-size: 12px;")
        wrap_layout.addWidget(lbl)
        layout.addWidget(wrap)
