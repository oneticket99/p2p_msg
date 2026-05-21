# SPDX-License-Identifier: GPL-3.0-or-later
"""MyAccountDialog — telegram desktop 내 계정 정보 modal (cycle 169.56 신설)."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui._icons import load_icon, load_pixmap


class MyAccountDialog(QDialog):
    """내 계정 — 자기소개 + 이름 + 전화번호 + 사용자명 + 개인 채널 + 생년월일."""

    save_requested = pyqtSignal(dict)

    def __init__(
        self,
        email: str = "",
        username: str = "",
        phone: str = "",
        bio: str = "",
        birthdate: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 내 계정")
        self.setModal(True)
        # cycle 169.242 — frameless modal (사용자 critique image #2 회수 — 별도 window 의 차단)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        # cycle 169.292 — MyProfileDialog 등가 strict (사용자 directive 의 dialog 통일)
        self.setFixedSize(420, 600)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # cycle 169.385 — header (title left + close X right) — 다른 dialog 표준 정합 사용자 critique image #149/150
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet("background-color: #1F2937;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 8, 12, 8)
        title = QLabel("정보")
        title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        h_layout.addWidget(title)
        h_layout.addStretch(1)
        from app.ui._close_button import make_close_button
        close_btn = make_close_button(self.reject, self)
        h_layout.addWidget(close_btn)
        outer.addWidget(header)

        # 한글 주석 — scroll area (content)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #131C30; }")
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(24, 24, 24, 24)
        c_layout.setSpacing(12)

        # 큰 avatar
        avatar = QLabel()
        avatar.setFixedSize(120, 120)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # cycle 169.249 — nickname initials + palette_solid hash 랜덤 bg (사용자 directive image #7/8/9)
        from app.ui._avatar_helper import make_initial_pixmap
        avatar.setPixmap(make_initial_pixmap(username, size=120))
        avatar.setStyleSheet("border-radius: 60px;")
        c_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignCenter)

        name_label = QLabel(username or "사용자")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: #e5e7eb; font-size: 20px; font-weight: 700;")
        c_layout.addWidget(name_label)

        status_label = QLabel("온라인")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # cycle 169.242 — 온라인 status color 통일 (Toonation BI #0066FF)
        status_label.setStyleSheet("color: #0066FF; font-size: 13px;")
        c_layout.addWidget(status_label)

        c_layout.addSpacing(12)

        # 자기소개 section
        bio_label = QLabel("자기소개")
        bio_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        c_layout.addWidget(bio_label)
        self._bio_edit = QTextEdit()
        self._bio_edit.setPlaceholderText("나이와 직업, 도시 따위를 자유롭게 소개하세요.")
        self._bio_edit.setPlainText(bio)
        self._bio_edit.setMaximumHeight(80)
        # cycle 169.332 — 사용자 critique image #96 — input 가능 visible 강화
        self._bio_edit.setStyleSheet(
            "QTextEdit { color: #e5e7eb; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 8px; font-size: 14px; }"
            "QTextEdit:focus { border: 1px solid #0066FF; }"
        )
        c_layout.addWidget(self._bio_edit)

        c_layout.addSpacing(12)

        # cycle 169.266 — 이메일 icon 회수 (notification bell → mail 의미) + 사용자 directive horizontal row
        self._name_edit = self._build_field_row(c_layout, "이름", username, "account")
        self._phone_edit = self._build_field_row(c_layout, "전화번호", phone, "phone")
        # cycle 169.391 — 생년월일 row 추가 (사용자 critique image #157)
        self._birthdate_edit = self._build_field_row(c_layout, "생년월일", birthdate, "info")
        # cycle 169.384 — 이메일 row 제거 (email = ID retain 사용자 directive image #145/146)
        self._email_value = email

        c_layout.addStretch(1)

        # 저장 button
        save_btn = QPushButton("저장")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet(
            "QPushButton {"
            " background-color: #0066FF;"
            " color: white;"
            " border: none;"
            " border-radius: 8px;"
            " font-size: 14px;"
            " font-weight: 600;"
            "}"
            " QPushButton:hover { background-color: #0052CC; }"
        )
        save_btn.clicked.connect(self._on_save)  # type: ignore[arg-type]
        c_layout.addWidget(save_btn)

        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

    def _build_field_row(self, layout: QVBoxLayout, label_text: str, value: str, icon_name: str) -> QLineEdit:
        """cycle 169.266 — 사용자 directive image #28/29/30 회수.

        horizontal row layout: icon (좌측) + label (중앙) + lineedit (우측 stretch).
        """
        row = QHBoxLayout()
        row.setContentsMargins(0, 8, 0, 8)
        row.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(load_pixmap(icon_name, size=20, color="#9ca3af"))
        icon.setFixedWidth(24)
        row.addWidget(icon)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #9ca3af; font-size: 13px;")
        lbl.setFixedWidth(80)
        row.addWidget(lbl)
        edit = QLineEdit(value)
        # cycle 169.332 — 사용자 critique image #96 — input bg + border strict visible
        edit.setStyleSheet(
            "QLineEdit { background-color: #1F2937; border: 1px solid #374151;"
            " border-radius: 6px; color: #e5e7eb; font-size: 14px; padding: 6px 8px; }"
            " QLineEdit:focus { border: 1px solid #0066FF; }"
        )
        row.addWidget(edit, stretch=1)
        layout.addLayout(row)
        return edit

    def _on_save(self) -> None:
        """저장 button — save_requested signal emit.

        cycle 169.387 — review finding 회수 (사용자 critique image #152 HTTP 400 display_name 부재).
        server PUT /api/auth/profile = display_name / username key expect.
        """
        self.save_requested.emit(
            {
                "display_name": self._name_edit.text(),
                "phone": self._phone_edit.text(),
                "email": self._email_value,
                "bio": self._bio_edit.toPlainText(),
                "birthdate": self._birthdate_edit.text(),
            }
        )
        self.accept()
