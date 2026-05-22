# SPDX-License-Identifier: GPL-3.0-or-later
"""SignupDialog — email + username + password + OTP 검증 (cycle 153 phase 2 redesign).

Toonation BI 통합 — logo icon top + Toonation primary CTA + brand 색상.
정합 = FRONTEND.md §15 + telegram-ui-survey.md §2 + OTPDialog (cycle 153 phase 2).

Flow:
    1. email + username + password + confirm 입력 → AuthClient.register
    2. signup PASS → OTPDialog 진입 chain
    3. OTP PASS → accept()
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
# cycle 169.363 — labels.tr() 우선 lookup + Qt fallback dual chain
from app.i18n import labels as _i18n_labels


def _tr(src: str) -> str:
    import re as _re
    slug = _re.sub(r"[^가-힣A-Za-z0-9]+", "_", src)[:40].strip("_").lower()
    val = _i18n_labels.tr(slug)
    if val != slug:
        return val
    return QCoreApplication.translate("MainWindow", src)

_ICON_PATH = Path(__file__).resolve().parent.parent / "assets" / "branding" / "tootalk_symbol.png"


class SignupDialog(QDialog):
    """회원가입 dialog — email + username + password + OTPDialog chain."""

    def __init__(self, auth_client: AuthClient, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self._client = auth_client
        self._email: Optional[str] = None
        # 한글 주석 — cycle 169.54 회수 — OTP PASS 직후 session token + user_id propagate
        self._token: Optional[str] = None
        self._user_id: Optional[int] = None
        # cycle 169.482 — double-click guard (가입 button 의 race 차단 — server IntegrityError 의 EMAIL_DUPLICATE 응답 차단)
        self._signup_in_flight: bool = False

        self.setWindowTitle(f"TooTalk · {_tr('회원가입')}")
        self.setMinimumWidth(440)
        self.setMinimumHeight(560)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(14)
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
        # cycle 169.471 — theme-aware color (palette windowText 기반 light/dark 자동 분기)
        from PyQt6.QtGui import QPalette as _QPalette
        from PyQt6.QtWidgets import QApplication as _QApp
        _app = _QApp.instance()
        _text_color = "#ffffff"
        if _app is not None:
            _lightness = _app.palette().color(_QPalette.ColorRole.Window).lightness()
            _text_color = "#1f2937" if _lightness >= 128 else "#ffffff"
        talk_label.setStyleSheet(
            "background: transparent;"
            f" color: {_text_color};"
            " font-family: -apple-system, 'SF Pro Display', 'Inter', sans-serif;"
            " font-size: 55px;"
            " font-weight: 700;"
            " letter-spacing: -1px;"
        )
        logo_row.addWidget(talk_label)
        outer.addLayout(logo_row)

        title = QLabel(_tr("투턱 회원가입"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("background: transparent; color: #e5e7eb; font-size: 22px; font-weight: 700;")
        outer.addWidget(title)

        sub = QLabel(_tr("email + username + password 의무"))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color: #9ca3af; font-size: 13px;")
        outer.addWidget(sub)

        outer.addSpacing(16)

        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("user@example.com")
        self._email_edit.setMinimumHeight(44)
        outer.addWidget(self._email_edit)

        self._username_edit = QLineEdit()
        self._username_edit.setPlaceholderText(_tr("username (영문 3~16자)"))
        self._username_edit.setMinimumHeight(44)
        outer.addWidget(self._username_edit)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_edit.setPlaceholderText(_tr("비밀번호"))
        self._password_edit.setMinimumHeight(44)
        outer.addWidget(self._password_edit)

        self._password_confirm_edit = QLineEdit()
        self._password_confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_confirm_edit.setPlaceholderText(_tr("확인"))
        self._password_confirm_edit.setMinimumHeight(44)
        outer.addWidget(self._password_confirm_edit)

        outer.addSpacing(8)

        btn_signup = QPushButton(_tr("가입 + OTP 송신"))
        btn_signup.setProperty("variant", "primary")
        btn_signup.setMinimumHeight(44)
        btn_signup.clicked.connect(self._on_signup_clicked)  # type: ignore[arg-type]
        outer.addWidget(btn_signup)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton(_tr("취소"))
        btn_cancel.setProperty("variant", "ghost")
        btn_cancel.setFlat(True)
        btn_cancel.clicked.connect(self.reject)  # type: ignore[arg-type]

        btn_login_link = QPushButton(_tr("로그인"))
        btn_login_link.setProperty("variant", "ghost")
        btn_login_link.setFlat(True)
        # 한글 주석 — cycle 169.53 회수 — login link click → done(3) (signup → login switch intent)
        # main.py 안 reject 의 어플 종료 차단 + login_dialog 진입 chain 의무
        btn_login_link.clicked.connect(lambda: self.done(3))  # type: ignore[arg-type]

        btn_row.addWidget(btn_cancel)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_login_link)
        outer.addLayout(btn_row)

        self._password_confirm_edit.returnPressed.connect(self._on_signup_clicked)  # type: ignore[arg-type]

    @property
    def email(self) -> Optional[str]:
        return self._email

    @property
    def token(self) -> Optional[str]:
        """cycle 169.54 — OTP PASS 직후 자동 발급 session token."""
        return self._token

    @property
    def user_id(self) -> Optional[int]:
        """cycle 169.54 — OTP PASS 직후 user_id."""
        return self._user_id

    def _on_signup_clicked(self) -> None:
        """cycle 169.34 회수 — sync def + asyncio.run() 격리 loop chain.

        cycle 169.482 — double-click guard (가입 button 의 race 차단 — server IntegrityError
        의 EMAIL_DUPLICATE 응답 차단). _signup_in_flight=True 시점 즉시 return.
        """
        if self._signup_in_flight:
            log.info("[회원가입] double-fire 차단 — _signup_in_flight retain")
            return
        email = self._email_edit.text().strip()
        username = self._username_edit.text().strip()
        password = self._password_edit.text()
        confirm = self._password_confirm_edit.text()

        from app.ui.confirm_dialog import ConfirmDialog
        if not email or not username or not password:
            ConfirmDialog.show_warning(self, "TooTalk", _tr("4 항목 모두 입력 의무"))
            return
        if password != confirm:
            ConfirmDialog.show_warning(self, "TooTalk", _tr("비밀번호 확인 불일치"))
            return
        if len(password) < 8 or len(password) > 32:
            ConfirmDialog.show_warning(self, "TooTalk", _tr("비밀번호 8~32자 의무"))
            return
        if len(username) < 3 or len(username) > 16:
            ConfirmDialog.show_warning(self, "TooTalk", _tr("사용자명 3~16자 의무"))
            return

        # cycle 169.49 회수 — QThread + sync urllib worker fire (asyncio 의존 폐기)
        base_url = getattr(self._client, "_base_url", "")
        if not base_url:
            ConfirmDialog.show_critical(self, "TooTalk", _tr("API endpoint 부재 — 설정 오류"))
            return
        # cycle 169.482 — in-flight flag set + worker fire
        self._signup_in_flight = True
        self._signup_email = email
        self._signup_worker = HttpJsonWorker(
            base_url,
            "/api/auth/register",
            {"email": email, "username": username, "password": password},
            parent=self,
        )
        self._signup_worker.finished_with_result.connect(self._on_signup_finished)
        self._signup_worker.start()

    def _on_signup_finished(self, ok: bool, error_code: str, error_message: str, data: dict) -> None:
        """HttpJsonWorker finished slot — signup 응답 처리 + OTP dialog chain.

        cycle 169.482 — _signup_in_flight reset (재 시도 가능 상태).
        """
        self._signup_in_flight = False
        log.info("[회원가입] finished ok=%s code=%s", ok, error_code)
        email = getattr(self, "_signup_email", "")
        if ok:
            # 한글 주석 — register PASS → OTP dialog 진입 (modal block + cancel 시 signup 잔존)
            from app.ui.otp_dialog import OTPDialog
            otp = OTPDialog(auth_client=self._client, email=email, parent=self)
            if otp.exec() == otp.DialogCode.Accepted:
                # 한글 주석 — cycle 169.54 회수 — OTP PASS 의 자동 발급 token + user_id propagate
                self._email = email
                self._token = otp._token
                self._user_id = otp._user_id
                self.accept()
            # 한글 주석 — OTP 미인증 시 signup dialog 잔존 (재 register / 재 OTP 진입 가능)
            return
        err_map = {
            "EMAIL_DUPLICATE": "이미 가입된 이메일 — 로그인 진입 의무",
            "USERNAME_TAKEN": "이미 사용 중인 사용자명",
            "USERNAME_DUPLICATE": "이미 사용 중인 사용자명",
            "INVALID_EMAIL": "이메일 형식 오류",
            "INVALID_USERNAME": "사용자명 형식 오류",
            "WEAK_PASSWORD": "비밀번호 형식 부재 (8자 이상 + 영문 + 숫자 권장)",
            "VALIDATION": "입력 형식 오류 — 다시 확인 의무",
            "RATE_LIMIT": "회원가입 시도 제한 — 잠시 후 재시도",
            "TIMEOUT": "응답 시간 초과 — 잠시 후 재시도",
            "NETWORK": "네트워크 오류 — 서버 부재 또는 연결 차단",
        }
        err_msg = err_map.get(error_code, error_message or "가입 실패")
        from app.ui.confirm_dialog import ConfirmDialog
        ConfirmDialog.show_critical(self, _tr("회원가입 실패"), str(err_msg))
