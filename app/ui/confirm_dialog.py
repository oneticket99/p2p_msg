# SPDX-License-Identifier: GPL-3.0-or-later
"""ConfirmDialog — in-app overlay 모달 (cycle 169.365 / 169.838).

계층 위치 — app/ui dialog(정본 §E). QDialog 위젯 + 정적 헬퍼(show_info/warning/critical/ask) —
앱 전역 40+ 호출 site 가 QMessageBox 대체로 사용하는 공용 얼럿/확인 진입점.

사용자 directive — 모든 dialog 모달 + main center + i18n. QMessageBox.question 등 native
popup 폐기 chain entry. labels.tr() 우선 lookup.
cycle 169.838 — 정적 헬퍼(show_info/warning/critical/ask)가 별도 OS 윈도우 .exec() 대신
exec_modal(parent 체인 walk → MainWindow _exec_dialog_centered 위임)로 메인 레이아웃 안
in-app overlay 모달로 뜬다(부모 부재 시 .exec() 폴백).
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
    """yes / no 확인 + info/warning/critical 모달 — frameless + 420x220 + labels.tr() chain.

    cycle 169.412 — mode parameter 확장 (Phase 1 잔존 QMessageBox 폐기 chain).
    mode = "question" (default, yes/no) | "info" | "warning" | "critical" (단일 확인 button).
    """

    _MODE_COLORS = {
        "question": ("#0066FF", "#0052cc"),  # Toonation BI
        "info": ("#22D3EE", "#0891B2"),  # cyan
        "warning": ("#F59E0B", "#D97706"),  # amber
        "critical": ("#EF4444", "#DC2626"),  # red
    }

    def __init__(
        self,
        title_key: str,
        message_key: str,
        parent: Optional[QWidget] = None,
        mode: str = "question",
        raw_text: bool = False,
    ) -> None:
        # telegram align outer wrap + frameless + 420x220 strict
        super().__init__(parent)
        self._mode = mode if mode in self._MODE_COLORS else "question"
        # raw_text True = 직접 문자열, False = labels.tr() lookup (key 정합)
        resolved_title = title_key if raw_text else _tr(title_key)
        resolved_msg = message_key if raw_text else _tr(message_key)
        self.setWindowTitle(resolved_title)
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

        # header (title + close X)
        header_row = QHBoxLayout()
        title = QLabel(resolved_title)
        # cycle 169.817 text label 배경 투명 (theme QLabel 배경 박스 제거 — wrap 배경에 blend)
        title.setStyleSheet("color: #f3f4f6; font-size: 16px; font-weight: 600; background: transparent;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        close_btn = make_close_button(self.reject, self)
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # message body
        msg_label = QLabel(resolved_msg)
        # cycle 169.817 text label 배경 투명 (theme QLabel 배경 박스 제거)
        msg_label.setStyleSheet("color: #e5e7eb; font-size: 14px; background: transparent;")
        msg_label.setWordWrap(True)
        body.addWidget(msg_label, stretch=1)

        # mode 별 button row 분기 (cycle 169.412)
        primary_color, hover_color = self._MODE_COLORS[self._mode]
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        if self._mode == "question":
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
        else:
            yes_btn = QPushButton(_tr("확인"))
        yes_btn.setFixedSize(96, 40)
        yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        yes_btn.setStyleSheet(
            f"QPushButton {{ color: #ffffff; background-color: {primary_color};"
            " border: 0; border-radius: 8px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: {hover_color}; }}"
        )
        yes_btn.clicked.connect(self.accept)  # type: ignore[arg-type]
        btn_row.addWidget(yes_btn)
        body.addLayout(btn_row)

    @staticmethod
    def show_info(parent, title: str, message: str) -> None:
        """QMessageBox.information swap — in-app overlay 모달 (cycle 169.838)."""
        # cycle 169.838 — 별도 OS 윈도우 .exec() → exec_modal(parent 체인 walk → MainWindow
        # _exec_dialog_centered 위임, 부모 부재 시 .exec() 폴백). 호출 사이트 변경 0.
        from app.ui._modal_helper import exec_modal
        dlg = ConfirmDialog(title, message, parent=parent, mode="info", raw_text=True)
        exec_modal(dlg, parent)

    @staticmethod
    def show_warning(parent, title: str, message: str) -> None:
        """QMessageBox.warning swap — in-app overlay 모달 (cycle 169.838)."""
        from app.ui._modal_helper import exec_modal
        dlg = ConfirmDialog(title, message, parent=parent, mode="warning", raw_text=True)
        exec_modal(dlg, parent)

    @staticmethod
    def show_critical(parent, title: str, message: str) -> None:
        """QMessageBox.critical swap — in-app overlay 모달 (cycle 169.838)."""
        from app.ui._modal_helper import exec_modal
        dlg = ConfirmDialog(title, message, parent=parent, mode="critical", raw_text=True)
        exec_modal(dlg, parent)

    @staticmethod
    def ask(parent, title: str, message: str) -> bool:
        """QMessageBox.question swap — Yes 클릭 → True (in-app overlay 모달, cycle 169.838)."""
        # exec_modal 반환 1(accept)/0(reject) 은 DialogCode.Accepted(=1) 비교와 정합.
        from app.ui._modal_helper import exec_modal
        d = ConfirmDialog(title, message, parent=parent, mode="question", raw_text=True)
        return exec_modal(d, parent) == QDialog.DialogCode.Accepted
