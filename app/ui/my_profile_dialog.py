# SPDX-License-Identifier: GPL-3.0-or-later
"""MyProfileDialog — telegram desktop 내 프로필 modal (cycle 169.243 telegram align rewrite).

사용자 critique 회수 (cycle 169.243):
- image #4 텔레그램 ref ↔ image #5 TooTalk 현 mismatch
- header zone (큰 dark zone) — large avatar center top + name + 온라인 status + edit/close icon top-right
- body zone (lighter slate) — info row 의 value bold + label subtitle pattern
- footer zone — 스토리 placeholder

avatar 복원 (cycle 169.182 폐기 후 cycle 169.243 사용자 directive 회수).
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

from app.ui._icons import load_pixmap


class MyProfileDialog(QDialog):
    """내 프로필 — telegram align (image #4 ref)."""

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
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setFixedSize(420, 600)
        # cycle 169.277 — 사용자 directive image #38/50 회수 — outer QFrame wrap + border (설정 modal 통일)
        # QDialog stylesheet border 의 child widget retain 안 의 의 visual retain 부재 — outer QFrame wrap chain.
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        # cycle 169.277 — outer wrap QFrame (border + 통일 retain)
        wrap = QFrame()
        wrap.setStyleSheet("QFrame { background-color: #131C30; border: 1px solid #1f2937; }")
        outer.addWidget(wrap)
        outer = QVBoxLayout(wrap)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 한글 주석 — header zone (large avatar + name + 온라인 + edit/close 우측 상단)
        header = QFrame()
        header.setStyleSheet("background-color: #1F2937;")
        header.setFixedHeight(260)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        # 한글 주석 — top icon row (edit pencil + close X 우측 상단)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(8, 8, 8, 0)
        top_row.setSpacing(4)
        top_row.addStretch(1)
        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(36, 36)
        edit_btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; color: #9ca3af; font-size: 18px; }"
            " QPushButton:hover { color: #e5e7eb; }"
        )
        edit_btn.clicked.connect(self.edit_requested.emit)  # type: ignore[arg-type]
        top_row.addWidget(edit_btn)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 36)
        close_btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; color: #9ca3af; font-size: 18px; }"
            " QPushButton:hover { color: #e5e7eb; }"
        )
        close_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        top_row.addWidget(close_btn)
        header_layout.addLayout(top_row)

        # 한글 주석 — large avatar center top + nickname initials + palette_solid 랜덤 bg (cycle 169.249)
        from app.ui._avatar_helper import make_initial_pixmap
        avatar = QLabel()
        avatar.setFixedSize(120, 120)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setPixmap(make_initial_pixmap(username, size=120))
        avatar.setStyleSheet("border-radius: 60px;")
        header_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignCenter)

        header_layout.addSpacing(12)

        # 한글 주석 — name (h1 bold center)
        name_label = QLabel(username or "사용자")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: #e5e7eb; font-size: 20px; font-weight: 700;")
        header_layout.addWidget(name_label)

        # 한글 주석 — 온라인 status (Toonation BI #0066FF)
        status_label = QLabel("온라인")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setStyleSheet("color: #0066FF; font-size: 13px;")
        header_layout.addWidget(status_label)

        header_layout.addStretch(1)
        outer.addWidget(header)

        # 한글 주석 — body zone (info rows — value bold + label subtitle)
        body = QFrame()
        body.setStyleSheet("background-color: #131C30;")
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(24, 20, 24, 16)
        b_layout.setSpacing(4)

        # info rows (텔레그램 ref order — 전화번호 + 사용자명 + 생년월일 + 이메일)
        for label_text, value in [
            ("전화번호", phone or "부재"),
            ("사용자명", f"@{username}" if username else "부재"),
            ("생년월일", birthdate or "부재"),
            ("이메일", email or "부재"),
        ]:
            self._build_info_row(b_layout, label_text, value)

        b_layout.addStretch(1)

        # 한글 주석 — footer (story placeholder — 텔레그램 align)
        footer = QFrame()
        footer.setStyleSheet("background-color: #131C30; border-top: 1px solid #1f2937;")
        f_layout = QVBoxLayout(footer)
        f_layout.setContentsMargins(24, 16, 24, 16)
        story_label = QLabel("회원님의 스토리가 여기에 표시됩니다.")
        story_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        story_label.setStyleSheet("color: #6b7280; font-size: 12px;")
        f_layout.addWidget(story_label)
        b_layout.addWidget(footer)

        outer.addWidget(body, stretch=1)

    def _build_info_row(self, layout: QVBoxLayout, label_text: str, value: str) -> None:
        """텔레그램 align info row — value bold + label subtitle (수직 stack)."""
        wrap = QFrame()
        wrap_layout = QVBoxLayout(wrap)
        wrap_layout.setContentsMargins(0, 8, 0, 8)
        wrap_layout.setSpacing(2)
        # 한글 주석 — value (bold + 청색 시점 사용자명 entry)
        is_username = label_text == "사용자명" and value.startswith("@")
        val = QLabel(value)
        val_color = "#0066FF" if is_username else "#e5e7eb"
        val.setStyleSheet(f"color: {val_color}; font-size: 16px; font-weight: 600;")
        wrap_layout.addWidget(val)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #9ca3af; font-size: 12px;")
        wrap_layout.addWidget(lbl)
        layout.addWidget(wrap)
