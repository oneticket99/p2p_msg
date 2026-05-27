# SPDX-License-Identifier: GPL-3.0-or-later
"""NewContactDialog — telegram align 신규 연락처 추가 dialog (cycle 169.450 신설).

계층 위치 — app/ui dialog(정본 §E). QDialog 위젯 — ContactsDialog 가 instantiate(연락처 추가 입력) +
contact_submitted signal 로 회신. 입력 수집(성/이름/전화번호 mask) 전용 — 등록 로직은 caller 책임.

사용자 directive — telegram 연락처 추가 rule 정합:
- 성 (Last Name) input
- 이름 (First Name) input
- 전화번호 input + `+82 __ ____ ____` mask + 글자수 cap

format: 한국 휴대폰 = `+82 NN NNNN NNNN` (총 11자리 — 010 → +82 10).
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
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
from app.ui._icons import load_icon
from app.i18n.labels import tr as _tr

log = logging.getLogger(__name__)


class NewContactDialog(QDialog):
    """신규 연락처 추가 modal — telegram align (성 + 이름 + 전화번호 마스크).

    Signal
    ------
    contact_submitted(dict)
        성공 시 ``{"last_name", "first_name", "phone"}`` payload emit.
    """

    contact_submitted = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_tr("새로운_연락처"))
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(480, 460)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("newContactWrap")
        wrap.setStyleSheet(
            "QFrame#newContactWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(28, 24, 28, 24)
        body.setSpacing(20)

        # header row (title + close)
        header_row = QHBoxLayout()
        title = QLabel(_tr("새로운_연락처"))
        title.setStyleSheet("color: #e5e7eb; font-size: 20px; font-weight: 700;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        close_btn = make_close_button(self.reject, wrap)
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # 성 row (icon + label + input)
        self._last_name_edit = self._build_input_row(
            body, icon_name=None, label=_tr("성"), placeholder="",
        )

        # 이름 row (icon = account)
        self._first_name_edit = self._build_input_row(
            body, icon_name="account", label=_tr("이름"), placeholder="",
        )

        # 전화번호 row (icon = phone + setInputMask telegram align)
        self._phone_edit = self._build_input_row(
            body, icon_name="phone", label=_tr("전화번호"), placeholder="+82",
        )
        # telegram align mask "+82 __ ____ ____" (한국 휴대폰 010 prefix → +82 10)
        # InputMask placeholder = "_". cap = 11 digit (+82 prefix retain — 10 digit input)
        self._phone_edit.setInputMask("+82 99 9999 9999;_")

        body.addStretch(1)

        # action row (취소 + 등록)
        action_row = QHBoxLayout()
        action_row.addStretch(1)
        cancel_btn = QPushButton(_tr("취소"))
        cancel_btn.setFixedHeight(36)
        cancel_btn.setMinimumWidth(80)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(
            "QPushButton { color: #67E8F9; background-color: transparent;"
            " border: 0; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { color: #22D3EE; }"
        )
        cancel_btn.clicked.connect(self.reject)  # type: ignore[arg-type]
        action_row.addWidget(cancel_btn)
        submit_btn = QPushButton(_tr("등록"))
        submit_btn.setFixedHeight(36)
        submit_btn.setMinimumWidth(80)
        submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        submit_btn.setStyleSheet(
            "QPushButton { color: #67E8F9; background-color: transparent;"
            " border: 0; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { color: #22D3EE; }"
        )
        submit_btn.clicked.connect(self._on_submit)  # type: ignore[arg-type]
        action_row.addWidget(submit_btn)
        body.addLayout(action_row)

        # Enter key 시 submit (전화번호 input retain)
        self._phone_edit.returnPressed.connect(self._on_submit)  # type: ignore[arg-type]

    def _build_input_row(
        self,
        parent_layout: QVBoxLayout,
        *,
        icon_name: Optional[str],
        label: str,
        placeholder: str = "",
    ) -> QLineEdit:
        """row = icon + (label + line edit) horizontal layout helper."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(16)
        # icon column (40px) — None 시 빈 spacer
        icon_label = QLabel()
        icon_label.setFixedSize(28, 28)
        if icon_name:
            icon = load_icon(icon_name, size=24, color="#9ca3af")
            icon_label.setPixmap(icon.pixmap(24, 24))
        row.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignBottom)

        # label + input vertical stack
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #67E8F9; font-size: 12px; font-weight: 600;")
        col.addWidget(lbl)
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setStyleSheet(
            "QLineEdit { color: #e5e7eb; background-color: transparent;"
            " border: 0; border-bottom: 1px solid #67E8F9;"
            " padding: 4px 0; font-size: 16px; }"
            "QLineEdit:focus { border-bottom: 2px solid #0066FF; }"
        )
        col.addWidget(edit)
        row.addLayout(col, stretch=1)

        parent_layout.addLayout(row)
        return edit

    def _on_submit(self) -> None:
        """등록 button click — payload 검증 + signal emit."""
        last_name = self._last_name_edit.text().strip()
        first_name = self._first_name_edit.text().strip()
        # phone 의 mask placeholder ('_') 제거 후 검증
        phone_raw = self._phone_edit.text().replace("_", "").strip()
        # 최소 = "+82" 만 = mask placeholder 전수 미입력
        digits_only = "".join(c for c in phone_raw if c.isdigit())
        if not first_name and not last_name:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(self, "연락처 추가", _tr("msg_contact_name_required"))
            return
        if len(digits_only) < 10:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(self, "연락처 추가", _tr("msg_contact_phone_required"))
            return
        payload = {
            "last_name": last_name,
            "first_name": first_name,
            "phone": phone_raw,
        }
        log.info("[new_contact] submit — last=%s first=%s phone=%s",
                 last_name, first_name, phone_raw)
        self.contact_submitted.emit(payload)
        self.accept()
