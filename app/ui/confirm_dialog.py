# SPDX-License-Identifier: GPL-3.0-or-later
"""ConfirmDialog — frameless 모달 popup (cycle 169.365).

사용자 directive — 모든 dialog 모달 + main center + i18n. QMessageBox.question 등 native
popup 폐기 chain entry. labels.tr() 우선 lookup.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._close_button import make_close_button
from app.i18n.labels import tr as _tr


class ConfirmDialog(QDialog):
    """yes / no 확인 모달 — frameless + 420x220 + labels.tr() chain."""

    def __init__(
        self,
        title_key: str,
        message_key: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        # 한글 주석 — telegram align outer wrap + frameless + 420x220 strict
        super().__init__(parent)
        self.setWindowTitle(_tr(title_key))
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 220)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("confirmDialogWrap")
        wrap.setStyleSheet(
            "QFrame#confirmDialogWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(12)

        # 한글 주석 — header (title + close X)
        header_row = QHBoxLayout()
        title = QLabel(_tr(title_key))
        title.setStyleSheet("color: #f3f4f6; font-size: 16px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        close_btn = make_close_button(self.reject, self)
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # 한글 주석 — message body
        msg_label = QLabel(_tr(message_key))
        msg_label.setStyleSheet("color: #e5e7eb; font-size: 14px;")
        msg_label.setWordWrap(True)
        body.addWidget(msg_label, stretch=1)

        # 한글 주석 — button row (yes / no)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        no_btn = QPushButton(_tr("아니오"))
        no_btn.setFixedSize(96, 40)
        no_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        no_btn.setStyleSheet(
            "QPushButton { color: #e5e7eb; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; font-weight: 500; }"
            "QPushButton:hover { background-color: #2c3a52; }"
        )
        no_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        btn_row.addWidget(no_btn)
        yes_btn = QPushButton(_tr("예"))
        yes_btn.setFixedSize(96, 40)
        yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        yes_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #0066FF;"
            " border: 0; border-radius: 8px; font-weight: 600; }"
            "QPushButton:hover { background-color: #0052cc; }"
        )
        yes_btn.clicked.connect(self.accept)  # type: ignore[arg-type]
        btn_row.addWidget(yes_btn)
        body.addLayout(btn_row)
