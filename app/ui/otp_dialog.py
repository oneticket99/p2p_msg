# SPDX-License-Identifier: GPL-3.0-or-later
"""OTPDialog — 회원가입 직후 6 digit email OTP 검증 (cycle 153 phase 2).

텔레그램 desktop OTP 등가 — 6 box auto-advance + paste 지원 + 재 송신 link.
정합 = telegram-ui-survey.md §3 + project_auth_email_otp_required + cycle 129 SMTP.

Flow:
    signup PASS → OTPDialog 진입 → 6 digit 입력 → POST /api/auth/otp/verify
    → 성공 시 accept() / 실패 시 message + 재시도 (5회 brute force cap)
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional


from PyQt6.QtCore import QCoreApplication, Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QKeySequence
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

from app.net.auth_client import AuthClient
from app.ui.confirm_dialog import ConfirmDialog as _ConfirmDialog
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

OTP_LENGTH = 6
RESEND_CAP = 5
OTP_VALID_SECONDS = 180  # 3분 유효 (server SMTP_OTP_TTL 정합)


class OtpBox(QLineEdit):
    """단일 OTP digit input — auto-advance + paste 지원 + arrow nav."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # cycle 169.472 — setModal mis-call 회수 (OtpBox = QLineEdit 의 의 setModal 부재)
        self.setMaxLength(1)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(48, 56)
        self.setStyleSheet(
            "QLineEdit {"
            " font-size: 22px;"
            " font-weight: 600;"
            " background-color: #1F2937;"
            " border: 2px solid #374151;"
            " border-radius: 8px;"
            " color: #e5e7eb;"
            "}"
            " QLineEdit:focus { border-color: #0066FF; }"
        )
        self._on_full = lambda: None
        self._on_back = lambda: None
        # cycle 169.477 — 6 digit paste callback (사용자 directive — 메일 복사 OTP 의 단일 paste 의무)
        self._on_paste: "callable[[str], None]" = lambda _text: None

    def keyPressEvent(self, event: Optional[QKeyEvent]) -> None:
        """Backspace 시점 직전 box 의 의 focus + 6 digit paste 지원."""
        if event is None:
            return
        # cycle 169.477 — Ctrl/Cmd+V paste detect → clipboard 안 6 digit 전 box 분산
        # PyQt6 안 matches() 부재 시점 paste() slot override 안 fallback retain
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste()
            return
        # 한글 주석 — Backspace 시점 의 직전 box focus 이동 callback
        if event.key() == Qt.Key.Key_Backspace and not self.text():
            self._on_back()
            return
        super().keyPressEvent(event)

    def paste(self) -> None:  # type: ignore[override]
        """cycle 169.479 — QLineEdit.paste() slot override (paste 의 single entry).

        Cmd+V / Ctrl+V keyboard shortcut + 우클릭 context menu paste action +
        프로그래밍 paste() 호출 모두 본 메소드 의 single path. maxLength(1) truncate
        bypass 의무 — _on_paste callback 안 6 digit 분산 chain.
        """
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        if clipboard is None:
            return
        text = (clipboard.text() or "").strip()
        if text:
            self._on_paste(text)


class OTPDialog(QDialog):
    """6 digit email OTP 검증 dialog — auto-advance + 재 송신 link + brute force cap."""

    def __init__(
        self,
        auth_client: AuthClient,
        email: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._client = auth_client
        self._email = email
        self._resend_remaining = RESEND_CAP
        # 한글 주석 — cycle 169.54 회수 — verify PASS 응답 안 session token + user_id 보관
        self._token: Optional[str] = None
        self._user_id: Optional[int] = None
        # cycle 169.480 — double-fire guard (paste 의 textChanged + _on_last_box_filled + explicit verify 의 race 차단)
        self._verify_in_flight: bool = False

        self.setWindowTitle(f"TooTalk · {_tr('OTP 인증')}")
        self.setMinimumWidth(420)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(16)

        # 한글 주석 — email 표기 + edit pencil (cycle 154 entry 시 점 enable)
        email_label = QLabel(self._email)
        email_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        email_label.setStyleSheet("color: #67E8F9; font-size: 14px; font-weight: 600;")
        outer.addWidget(email_label)

        info = QLabel(_tr("메일함 안 6 digit OTP 확인"))
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #9ca3af; font-size: 13px;")
        outer.addWidget(info)

        # 한글 주석 — 유효시간 countdown label (mm:ss decrement)
        self._remaining_seconds: int = OTP_VALID_SECONDS
        self._countdown_label = QLabel()
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown_label.setStyleSheet(
            "color: #22D3EE; font-size: 20px; font-weight: 700;"
            " font-family: 'SF Mono', 'Menlo', monospace;"
        )
        outer.addWidget(self._countdown_label)

        # 한글 주석 — 1초 tick QTimer + countdown decrement chain
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)  # type: ignore[arg-type]
        self._update_countdown_display()
        self._countdown_timer.start()

        outer.addSpacing(8)

        # 한글 주석 — 6 box row + auto-advance binding
        box_row = QHBoxLayout()
        box_row.setSpacing(8)
        box_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._boxes: List[OtpBox] = []
        for i in range(OTP_LENGTH):
            box = OtpBox()
            self._boxes.append(box)
            box_row.addWidget(box)
        outer.addLayout(box_row)

        # 한글 주석 — auto-advance + back nav + paste 분산 binding
        for i, box in enumerate(self._boxes):
            if i < OTP_LENGTH - 1:
                next_box = self._boxes[i + 1]
                box.textChanged.connect(  # type: ignore[arg-type]
                    lambda text, nxt=next_box: nxt.setFocus() if text else None
                )
            if i > 0:
                prev_box = self._boxes[i - 1]
                box._on_back = lambda prev=prev_box: prev.setFocus()  # type: ignore[assignment]
            # 한글 주석 — 마지막 box text 입력 시 자동 검증 trigger
            if i == OTP_LENGTH - 1:
                box.textChanged.connect(self._on_last_box_filled)  # type: ignore[arg-type]
            # cycle 169.477 — paste callback bind (사용자 directive — 메일 복사 OTP 단일 paste)
            box._on_paste = self._distribute_pasted_otp  # type: ignore[assignment]

        outer.addSpacing(8)

        # 한글 주석 — 재 송신 text link (cycle 169.47 회수 — login_dialog 회원가입 link pattern 정합)
        # 사용자 directive verbatim: "재송신은 버튼이 아니라 하단의 로그인, 취소처럼 텍스트 링크로".
        link_row = QHBoxLayout()
        link_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._resend_btn = QPushButton(f"{_tr('재 송신')} ({self._resend_remaining}/{RESEND_CAP})")
        self._resend_btn.setProperty("variant", "ghost")
        self._resend_btn.setFlat(True)
        self._resend_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._resend_btn.setMinimumHeight(32)
        self._resend_btn.setStyleSheet(
            "QPushButton {"
            " color: #22D3EE;"
            " background: transparent;"
            " border: none;"
            " padding: 4px 12px;"
            " font-size: 13px;"
            " font-weight: 600;"
            " text-decoration: underline;"
            "}"
            " QPushButton:hover { color: #67E8F9; }"
            " QPushButton:pressed { color: #0891B2; }"
            " QPushButton:disabled { color: #6b7280; }"
        )
        self._resend_btn.clicked.connect(self._on_resend_clicked)  # type: ignore[arg-type]
        link_row.addWidget(self._resend_btn)
        outer.addLayout(link_row)

        # 한글 주석 — 검증 + 취소 button row
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton(_tr("취소"))
        btn_cancel.setProperty("variant", "secondary")
        btn_cancel.clicked.connect(self.reject)  # type: ignore[arg-type]
        btn_verify = QPushButton(_tr("검증"))
        btn_verify.setProperty("variant", "primary")
        btn_verify.clicked.connect(self._on_verify_clicked)  # type: ignore[arg-type]
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_verify)
        outer.addLayout(btn_row)

        self._boxes[0].setFocus()

    def _distribute_pasted_otp(self, raw: str) -> None:
        """cycle 169.477 — paste text 안 digit 추출 + 6 box 분산 + 자동 검증.

        사용자 directive — "메일 안 복사한 OTP 의 단일 paste 의무". 6 digit 외 문자
        (공백/줄바꿈/dash) 제거 후 6 자리 만 box 분산. 6 자리 충족 시점 자동 verify.
        """
        import re as _re
        digits = _re.sub(r"\D", "", raw)[:OTP_LENGTH]
        if not digits:
            return
        log.info("[OTP paste] digits=%d → box 분산", len(digits))
        for i, box in enumerate(self._boxes):
            box.setText(digits[i] if i < len(digits) else "")
        # 한글 주석 — 마지막 box focus 이동 (auto-advance 정합)
        last_filled = min(len(digits), OTP_LENGTH) - 1
        if last_filled >= 0:
            self._boxes[last_filled].setFocus()
        # 한글 주석 — 6 digit 충족 시점 자동 검증 trigger
        if len(digits) == OTP_LENGTH:
            self._on_verify_clicked()

    def _get_otp(self) -> str:
        """6 box text concat → 6 digit string."""
        return "".join(box.text() for box in self._boxes)

    def _update_countdown_display(self) -> None:
        """remaining_seconds 의 mm:ss 변환 + 색상 갱신 (30s 이하 red)."""
        m, s = divmod(max(self._remaining_seconds, 0), 60)
        self._countdown_label.setText(f"{m}:{s:02d}")
        # 한글 주석 — 30초 이하 시 red, expired (0) = gray
        if self._remaining_seconds <= 0:
            self._countdown_label.setStyleSheet(
                "color: #6b7280; font-size: 20px; font-weight: 700;"
                " font-family: 'SF Mono', 'Menlo', monospace;"
            )
        elif self._remaining_seconds <= 30:
            self._countdown_label.setStyleSheet(
                "color: #ef4444; font-size: 20px; font-weight: 700;"
                " font-family: 'SF Mono', 'Menlo', monospace;"
            )
        else:
            self._countdown_label.setStyleSheet(
                "color: #22D3EE; font-size: 20px; font-weight: 700;"
                " font-family: 'SF Mono', 'Menlo', monospace;"
            )

    def _on_countdown_tick(self) -> None:
        """1초 tick — decrement + display + expired 시 box disable."""
        self._remaining_seconds -= 1
        self._update_countdown_display()
        if self._remaining_seconds <= 0:
            self._countdown_timer.stop()
            # 한글 주석 — expired 시 box disable + 재 송신 prompt
            for box in self._boxes:
                box.setEnabled(False)
            self._countdown_label.setText(_tr("만료 — 재 송신 의무"))

    def _on_last_box_filled(self, text: str) -> None:
        """마지막 box 입력 시점 의 자동 검증 trigger."""
        if text and len(self._get_otp()) == OTP_LENGTH:
            self._on_verify_clicked()

    def _on_verify_clicked(self) -> None:
        """cycle 169.49 회수 — QThread + sync urllib worker.

        cycle 169.480 — double-fire guard (paste 의 자동 verify + textChanged 의 last_box_filled
        의 의 race 차단). _verify_in_flight=True 시점 즉시 return.
        """
        if self._verify_in_flight:
            log.info("[OTP verify] double-fire 차단 — _verify_in_flight retain")
            return
        otp = self._get_otp()
        if len(otp) != OTP_LENGTH or not otp.isdigit():
            _ConfirmDialog.show_warning(self, "TooTalk", _tr("6 digit OTP 입력 의무"))
            return
        base_url = getattr(self._client, "_base_url", "")
        if not base_url:
            _ConfirmDialog.show_critical(self, "TooTalk", _tr("API endpoint 부재 — 설정 오류"))
            return
        self._verify_in_flight = True
        self._verify_worker = HttpJsonWorker(base_url, "/api/auth/verify", {"email": self._email, "code": otp}, parent=self)
        self._verify_worker.finished_with_result.connect(self._on_verify_finished)
        self._verify_worker.start()

    def _on_verify_finished(self, ok: bool, error_code: str, error_message: str, data: dict) -> None:
        """HttpJsonWorker finished slot — verify 응답 처리.

        cycle 169.54 회수 — 응답 안 token + user_id store (회원가입 직후 자동 로그인).
        cycle 169.480 — _verify_in_flight flag reset (재 시도 가능 상태).
        """
        self._verify_in_flight = False
        log.info("[OTP verify] finished ok=%s code=%s", ok, error_code)
        if ok:
            self._token = data.get("token")
            self._user_id = data.get("user_id")
            self.accept()
            return
        err_map = {
            "INVALID_OTP": "OTP 코드 부재 또는 형식 오류",
            "OTP_EXPIRED": "OTP 만료 — 재 송신 의무",
            "OTP_ATTEMPT_EXCEEDED": "시도 횟수 초과 — 재 송신 의무",
            "USER_NOT_FOUND": "사용자 부재 — 회원가입 진입 의무",
            "OTP_INVALID": "OTP 코드 불일치 — 재 입력 의무",
            "TIMEOUT": "응답 시간 초과 — 잠시 후 재시도",
            "NETWORK": "네트워크 오류 — 서버 부재 또는 연결 차단",
        }
        err_msg = err_map.get(error_code, error_message or _tr("검증 실패"))
        _ConfirmDialog.show_critical(self, "TooTalk", f"{_tr('OTP 인증 실패')} — {err_msg}")
        for box in self._boxes:
            box.clear()
        self._boxes[0].setFocus()

    def _on_resend_clicked(self) -> None:
        """OTP 재 송신 — cycle 169.49 QThread + sync urllib 변환.

        qasync nested modal 안 ensure_future dispatch fail 회수.
        background QThread + Qt signal/slot — asyncio 의존 폐기.
        """
        log.info("[OTP resend] button clicked — remaining=%d", self._resend_remaining)
        if self._resend_remaining <= 0:
            _ConfirmDialog.show_warning(self, "TooTalk", _tr("재 송신 횟수 초과 (24시간)"))
            return

        # 한글 주석 — UI 즉시 feedback (사용자 직관 — click → 즉시 cap 차감 + countdown reset)
        self._resend_remaining -= 1
        self._resend_btn.setText(f"{_tr('재 송신')} ({self._resend_remaining}/{RESEND_CAP})")
        self._remaining_seconds = OTP_VALID_SECONDS
        for box in self._boxes:
            box.setEnabled(True)
            box.clear()
        self._boxes[0].setFocus()
        self._update_countdown_display()
        if not self._countdown_timer.isActive():
            self._countdown_timer.start()

        # 한글 주석 — QThread background worker fire (sync urllib + TLS verify off)
        base_url = getattr(self._client, "_base_url", "")
        if not base_url:
            log.warning("[OTP resend] base_url 부재")
            self._rollback_resend()
            _ConfirmDialog.show_critical(self, "TooTalk", _tr("API endpoint 부재 — 설정 오류"))
            return
        self._resend_worker = HttpJsonWorker(base_url, "/api/auth/resend", {"email": self._email}, parent=self)
        self._resend_worker.finished_with_result.connect(self._on_resend_finished)
        self._resend_worker.start()

    def _on_resend_finished(self, ok: bool, error_code: str, error_message: str, data: dict) -> None:
        """HttpJsonWorker finished slot — main thread dispatch."""
        log.info("[OTP resend] finished ok=%s code=%s", ok, error_code)
        if ok:
            _ConfirmDialog.show_info(self, "TooTalk", _tr("OTP 메일 재 송신 완료"))
            return
        err_map = {
            "RATE_LIMIT": "재 송신 cooldown — 60초 대기 의무",
            "USER_NOT_FOUND": "사용자 부재 — 회원가입 진입 의무",
            "EMAIL_ALREADY_VERIFIED": "이미 인증 완료 — 로그인 진입 의무",
            "SMTP_FAILURE": "메일 발송 실패 — 잠시 후 재시도",
            "TIMEOUT": "응답 시간 초과 — 잠시 후 재시도",
            "NETWORK": "네트워크 오류 — 서버 부재 또는 연결 차단",
        }
        msg = err_map.get(error_code, error_message or _tr("재 송신 실패"))
        self._rollback_resend()
        _ConfirmDialog.show_warning(self, "TooTalk", msg)

    def _rollback_resend(self) -> None:
        """send fail 시 cap rollback + button 재 활성."""
        self._resend_remaining = min(self._resend_remaining + 1, RESEND_CAP)
        self._resend_btn.setText(f"{_tr('재 송신')} ({self._resend_remaining}/{RESEND_CAP})")
        self._resend_btn.setEnabled(True)

