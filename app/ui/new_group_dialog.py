# SPDX-License-Identifier: GPL-3.0-or-later
"""NewGroupDialog — 그룹 만들기 modal (cycle 169.315).

사용자 directive image #84 — drawer 의 "그룹 만들기" click → 본 dialog.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class NewGroupDialog(QDialog):
    """그룹 만들기 placeholder dialog."""

    group_created = pyqtSignal(str, list)  # (group_name, member_ids)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        # 한글 주석 — telegram align outer wrap + 420x600 strict
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 그룹 만들기")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        # 한글 주석 — outer wrap (border 1px #1f2937 통일)
        wrap = QFrame()
        wrap.setObjectName("newGroupWrap")
        wrap.setStyleSheet(
            "QFrame#newGroupWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(12)

        # 한글 주석 — header (title + close X)
        header_row = QHBoxLayout()
        title = QLabel("그룹 만들기")
        title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 16px; font-size: 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2c3a52; color: #ffffff; }"
        )
        close_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # 한글 주석 — 그룹명 입력
        name_label = QLabel("그룹명")
        name_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        body.addWidget(name_label)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("새 그룹 이름")
        self._name_edit.setStyleSheet(
            "QLineEdit { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 10px; }"
        )
        body.addWidget(self._name_edit)

        # 한글 주석 — 멤버 선택 placeholder
        member_label = QLabel("멤버 선택")
        member_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        body.addWidget(member_label)
        self._member_list = QListWidget()
        self._member_list.setStyleSheet(
            "QListWidget { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; }"
        )
        body.addWidget(self._member_list, stretch=1)

        # 한글 주석 — footer 생성 button
        create_btn = QPushButton("그룹 생성")
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #3b82f6;"
            " border: 0; border-radius: 8px; padding: 12px; font-weight: 600; }"
            "QPushButton:hover { background-color: #2563eb; }"
        )
        create_btn.clicked.connect(self._on_create)  # type: ignore[arg-type]
        body.addWidget(create_btn)

    def _on_create(self) -> None:
        # 한글 주석 — placeholder signal emit + close
        name = self._name_edit.text().strip()
        if name:
            self.group_created.emit(name, [])
        self.accept()
