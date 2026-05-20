# SPDX-License-Identifier: GPL-3.0-or-later
"""LoginDialog — email + password 세션 토큰 발급 (cycle 153 phase 2 redesign).

Toonation BI 통합 — logo icon top + primary CTA + 한글 글꼴 통합 + brand 색상.
정합 = FRONTEND.md §15 + telegram-ui-survey.md §2 + toonation-brand-integration-plan §4.2.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.net.auth_client import AuthClient
from app.ui.error_messages import translate_error
from app.ui._http_worker import HttpJsonWorker

log = logging.getLogger(__name__)
_tr = lambda src: QCoreApplication.translate("MainWindow", src)

_ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "branding" / "tootalk_symbol.png"


class LoginDialog(QDialog):
    """로그인 다이얼로그 — Toonation BI 통합 redesign + email + password.

    성공 시 세션 토큰 + user_id 보관 후 accept().
    """

    def __init__(self, auth_client: AuthClient, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._client = auth_client
        self._token: Optional[str] = None
        self._user_id: Optional[int] = None

        self.setWindowTitle(f"TooTalk · {_tr('로그인')
        self.setModal(True)}")
        self.setMinimumWidth(420)
        self.setMinimumHeight(480)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(16)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 한글 주석 — symbol + Talk QHBoxLayout 합성 복원 (cycle 169.16)
        logo_row = QHBoxLayout()
        logo_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_row.setSpacing(0)
        logo_row.setContentsMargins(0, 0, 0, 0)

        symbol_label = QLabel()
        symbol_label.setStyleSheet("background: transparent;")
        symbol_label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        if _ICON_PATH.is_file():
            pixmap = QPixmap(str(_ICON_PATH))
            scaled = pixmap.scaledToHeight(50, Qt.TransformationMode.SmoothTransformation)
            symbol_label.setPixmap(scaled)
        logo_row.addWidget(symbol_label)

        talk_label = QLabel("Talk")
        talk_label.setStyleSheet(
            "background: transparent;"
            " color: #ffffff;"
            " font-family: -apple-system, 'SF Pro Display', 'Inter', sans-serif;"
            " font-size: 55px;"
            " font-weight: 700;"
            " letter-spacing: -1px;"
        )
        logo_row.addWidget(talk_label)
        outer.addLayout(logo_row)

        # 한글 주석 — "투턱 로그인" title (사용자 directive cycle 169.12 — TooTalk → 투턱)
        title = QLabel(_tr("투턱 로그인"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("background: transparent; color: #e5e7eb; font-size: 22px; font-weight: 700;")
        outer.addWidget(title)

        sub = QLabel(_tr("email + password 입력"))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #9ca3af; font-size: 13px;")
        outer.addWidget(sub)

        outer.addSpacing(16)

        # 한글 주석 — email + password input — Toonation 통합 style
        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("user@example.com")
        self._email_edit.setMinimumHeight(44)
        outer.addWidget(self._email_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText(_tr("비밀번호"))
        self._password_edit.setMinimumHeight(44)
        outer.addWidget(self._password_edit)

        outer.addSpacing(8)

        # 한글 주석 — 로그인 button (primary) + cancel (secondary)
        btn_login = QPushButton(_tr("로그인"))
        btn_login.setProperty("variant", "primary")
        btn_login.setMinimumHeight(44)
        btn_login.clicked.connect(self._on_login_clicked)  # type: ignore[arg-type]
        outer.addWidget(btn_login)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton(_tr("취소"))
        btn_cancel.setProperty("variant", "ghost")
        btn_cancel.setFlat(True)
        btn_cancel.clicked.connect(self.reject)  # type: ignore[arg-type]

        btn_signup_link = QPushButton(_tr("회원가입"))
        btn_signup_link.setProperty("variant", "ghost")
        btn_signup_link.setFlat(True)
        btn_signup_link.clicked.connect(self._on_signup_link_clicked)  # type: ignore[arg-type]

        btn_row.addWidget(btn_cancel)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_signup_link)
        outer.addLayout(btn_row)

        # 한글 주석 — Enter key 시 login trigger
        self._password_edit.returnPressed.connect(self._on_login_clicked)  # type: ignore[arg-type]

    @property
    def token(self) -> Optional[str]:
        return self._token

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id

    def _on_login_clicked(self) -> None:
        """cycle 169.49 회수 — QThread + sync urllib worker."""
        email = self._email_edit.text().strip()
        password = self._password_edit.text()
        if not email or not password:
            QMessageBox.warning(self, "TooTalk", f"이메일 + {_tr('비밀번호')} 입력 의무")
            return
        base_url = getattr(self._client, "_base_url", "")
        if not base_url:
            QMessageBox.critical(self, "TooTalk", _tr("API endpoint 부재 — 설정 오류"))
            return
        self._login_worker = HttpJsonWorker(
            base_url,
            "/api/auth/login",
            {"email": email, "password": password},
            parent=self,
        )
        self._login_worker.finished_with_result.connect(self._on_login_finished)
        self._login_worker.start()

    def _on_login_finished(self, ok: bool, error_code: str, error_message: str, data: dict) -> None:
        """HttpJsonWorker finished slot — login 응답 처리."""
        log.info("[로그인] finished ok=%s code=%s", ok, error_code)
        if ok:
            self._token = data.get("token")
            self._user_id = data.get("user_id")
            self.accept()
            return
        err_map = {
            "USER_NOT_FOUND": "사용자 부재 — 회원가입 진입 의무",
            "INVALID_CREDENTIALS": "이메일 또는 비밀번호 불일치",
            "INVALID_PASSWORD": "비밀번호 부재 또는 오류",
            "EMAIL_NOT_VERIFIED": "이메일 미인증 — OTP 검증 의무",
            "ACCOUNT_LOCKED": "계정 잠김 — 운영자 문의 의무",
            "ACCOUNT_SUSPENDED": "계정 정지 — 운영자 문의 의무",
            "RATE_LIMIT": "로그인 시도 제한 — 잠시 후 재시도",
            "TIMEOUT": "응답 시간 초과 — 잠시 후 재시도",
            "NETWORK": "네트워크 오류 — 서버 부재 또는 연결 차단",
        }
        err_msg = err_map.get(error_code, error_message or "자격 정보 부재")
        QMessageBox.critical(self, f"{_tr('로그인 실패')}", err_msg)

    def _on_signup_link_clicked(self) -> None:
        """회원가입 link click — QDialog.done(2) signup intent code 반환."""
        self.done(2)
