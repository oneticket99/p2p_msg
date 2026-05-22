# SPDX-License-Identifier: GPL-3.0-or-later
"""AddFriendByUsernameDialog — telegram align 사용자명 입력 친구 추가 (cycle 169.457 신설).

사용자 directive — telegram 친구 추가 2 mode 중 username 입력 path.
- 사용자 사용자명 입력 → server /api/friends/by-username/{username} resolve → friends INSERT.
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._close_button import make_close_button
from app.i18n.labels import tr as _tr

log = logging.getLogger(__name__)


class AddFriendByUsernameDialog(QDialog):
    """telegram align 사용자명 검색 친구 추가 modal.

    Signal
    ------
    friend_added(str)
        성공 시 username payload emit.
    """

    friend_added = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("사용자명 검색")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 280)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("addByUsernameWrap")
        wrap.setStyleSheet(
            "QFrame#addByUsernameWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(28, 24, 28, 24)
        body.setSpacing(16)

        # header
        header_row = QHBoxLayout()
        title = QLabel("사용자명으로 친구 추가")
        title.setStyleSheet("color: #e5e7eb; font-size: 18px; font-weight: 700;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        close_btn = make_close_button(self.reject, wrap)
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        hint = QLabel("상대 사용자명을 입력하세요. 일치 시점 친구 추가됩니다.")
        hint.setStyleSheet("color: #9ca3af; font-size: 12px;")
        hint.setWordWrap(True)
        body.addWidget(hint)

        # username input
        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("@username")
        self._username_edit.setMinimumHeight(40)
        self._username_edit.setStyleSheet(
            "QLineEdit { color: #e5e7eb; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 8px 12px;"
            " font-size: 15px; }"
            "QLineEdit:focus { border: 1px solid #0066FF; }"
        )
        body.addWidget(self._username_edit)

        body.addStretch(1)

        # action row
        action_row = QHBoxLayout()
        action_row.addStretch(1)
        cancel_btn = QPushButton(_tr("취소"))
        cancel_btn.setFixedSize(96, 36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton { color: #e5e7eb; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; font-weight: 500; }"
            "QPushButton:hover { background-color: #2c3a52; }"
        )
        cancel_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        action_row.addWidget(cancel_btn)
        submit_btn = QPushButton("추가")
        submit_btn.setFixedSize(96, 36)
        submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        submit_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #0066FF;"
            " border: 0; border-radius: 8px; font-weight: 600; }"
            "QPushButton:hover { background-color: #0052cc; }"
        )
        submit_btn.clicked.connect(self._on_submit)  # type: ignore[arg-type]
        action_row.addWidget(submit_btn)
        body.addLayout(action_row)

        self._username_edit.returnPressed.connect(self._on_submit)  # type: ignore[arg-type]

    def _on_submit(self) -> None:
        username = self._username_edit.text().strip().lstrip("@")
        if not username or len(username) < 3:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(self, "친구 추가", "사용자명 3자 이상 의무")
            return
        self.friend_added.emit(username)
        self.accept()
