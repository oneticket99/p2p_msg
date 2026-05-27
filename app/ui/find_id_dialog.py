# SPDX-License-Identifier: GPL-3.0-or-later
"""FindIdDialog — username + phone 입력 → masked email 반환 (cycle 169.410).

계층 위치 — app/ui dialog(정본 §E). QDialog 위젯 — LoginDialog 가 instantiate(아이디 찾기 진입).
서버 POST /api/auth/find/email 호출 + masked email 표시(enumeration 방어는 server 책임).

사용자 directive — 아이디 찾기 미구현 회수.
endpoint: POST /api/auth/find/email
보안 — username AND phone 둘 일치 시점만 server 반환 (enumeration 방어).
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.i18n import labels as _i18n_labels
from app.ui._close_button import make_close_button
from app.ui._http_worker import HttpJsonWorker

log = logging.getLogger(__name__)


def _tr(slug: str) -> str:
    """labels.tr lookup fallback (cycle 169.358 chain)."""
    val = _i18n_labels.tr(slug)
    return val if val != slug else slug


class FindIdDialog(QDialog):
    """아이디 찾기 — username + 전화번호 입력 → masked email 응답 표시 (cycle 169.410)."""

    def __init__(self, base_url: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._base_url = base_url
        self._worker: Optional[HttpJsonWorker] = None

        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setModal(True)
        self.setFixedSize(420, 460)

        # outer wrap frame (border + bg 통일)
        outer_wrap = QVBoxLayout(self)
        outer_wrap.setContentsMargins(0, 0, 0, 0)
        outer_wrap.setSpacing(0)

        wrap_frame = QFrame(self)
        wrap_frame.setStyleSheet(
            "QFrame { background-color: #1f2937; border-radius: 12px; border: 1px solid #374151; }"
        )
        outer_wrap.addWidget(wrap_frame)

        outer = QVBoxLayout(wrap_frame)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(12)

        # header row (title + close)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        title = QLabel(_tr("아이디_찾기"))
        title.setStyleSheet("color: #e5e7eb; font-size: 18px; font-weight: 700;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        close_btn = make_close_button(self.reject, parent=wrap_frame)
        header_row.addWidget(close_btn)
        outer.addLayout(header_row)

        sub = QLabel(_tr("사용자명_전화번호_입력_안내"))
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #9ca3af; font-size: 12px;")
        outer.addWidget(sub)

        outer.addSpacing(8)

        # username input
        lbl_user = QLabel(_tr("사용자명"))
        lbl_user.setStyleSheet("color: #9ca3af; font-size: 12px;")
        outer.addWidget(lbl_user)
        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText("nickname123")
        self._username_edit.setMinimumHeight(40)
        outer.addWidget(self._username_edit)

        # phone input
        lbl_phone = QLabel(_tr("전화번호"))
        lbl_phone.setStyleSheet("color: #9ca3af; font-size: 12px;")
        outer.addWidget(lbl_phone)
        self._phone_edit = QLineEdit()
        self._phone_edit.setPlaceholderText("010-1234-5678")
        self._phone_edit.setMinimumHeight(40)
        outer.addWidget(self._phone_edit)

        outer.addSpacing(8)

        # result label (응답 영역, 초기 hide)
        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setStyleSheet(
            "color: #22D3EE; font-size: 14px; font-weight: 600; padding: 12px;"
            " background-color: #0f172a; border-radius: 8px;"
        )
        self._result_label.setVisible(False)
        outer.addWidget(self._result_label)

        outer.addStretch(1)

        # 찾기 button (primary) + 닫기 (secondary)
        btn_find = QPushButton(_tr("찾기"))
        btn_find.setProperty("variant", "primary")
        btn_find.setMinimumHeight(44)
        btn_find.setStyleSheet(
            "QPushButton { background-color: #0066FF; color: white; border-radius: 8px;"
            " font-size: 15px; font-weight: 600; }"
            "QPushButton:hover { background-color: #0052cc; }"
        )
        btn_find.clicked.connect(self._on_find_clicked)  # type: ignore[arg-type]
        outer.addWidget(btn_find)

        self._phone_edit.returnPressed.connect(self._on_find_clicked)  # type: ignore[arg-type]

    def _on_find_clicked(self) -> None:
        """찾기 button click — username + phone payload POST."""
        username = self._username_edit.text().strip()
        phone = self._phone_edit.text().strip()
        if not username or not phone:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(
                self, "TooTalk", _tr("사용자명_전화번호_입력_의무")
            )
            return
        self._result_label.setVisible(False)
        self._worker = HttpJsonWorker(
            self._base_url,
            "/api/auth/find/email",
            {"username": username, "phone": phone},
            parent=self,
        )
        self._worker.finished_with_result.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self, ok: bool, error_code: str, error_message: str, data: dict) -> None:
        """find/email response handler — masked email 출력 or 오류 표시."""
        log.info("[find_id] finished ok=%s code=%s", ok, error_code)
        if ok and data.get("email_masked"):
            masked = data["email_masked"]
            self._result_label.setText(
                f"{_tr('찾은_이메일')}\n\n{masked}"
            )
            self._result_label.setVisible(True)
            return
        err_map = {
            "NOT_FOUND": "일치 사용자 부재 — 사용자명 + 전화번호 재확인",
            "INVALID_INPUT": "사용자명 + 전화번호 입력 의무",
            "DB_DISABLED": "서버 DB 비활성 — 운영자 문의",
            "TIMEOUT": "응답 시간 초과 — 잠시 후 재시도",
            "NETWORK": "네트워크 오류 — 서버 부재 또는 연결 차단",
        }
        err_msg = err_map.get(error_code, error_message or "조회 실패")
        from app.ui.confirm_dialog import ConfirmDialog
        ConfirmDialog.show_critical(self, _tr("아이디_찾기"), err_msg)
