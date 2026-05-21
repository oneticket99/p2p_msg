# SPDX-License-Identifier: GPL-3.0-or-later
"""RemoteRequestDialog / RemoteConnectDialog — 원격 데스크탑 제어 (cycle 169.331).

사용자 directive image #93 — chat_header 의 원격 제어 icon → dropdown 2 entry:
- 원격 요청 → RemoteRequestDialog (PermissionRequest send)
- 원격 연결 → RemoteConnectDialog (PermissionGrant accept + RemoteSession start)

기존 app/remote/ module chain binding:
- ``PermissionRequest`` / ``PermissionGrant`` (permission.py)
- ``RemoteSession`` (protocol.py)
- ``build_local_screen_info`` (coord_transform.py)
- ``select_capture_backend`` (capture.py)
- ``build_input_dispatch_backend`` (input_dispatch.py)
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ui._close_button import make_close_button

log = logging.getLogger(__name__)


class RemoteRequestDialog(QDialog):
    """원격 요청 dialog — 친구 선택 + mode + duration + reason → PermissionRequest send."""

    request_sent = pyqtSignal(object)  # PermissionRequest

    def __init__(self, friends: Optional[list[dict]] = None, parent: Optional[QWidget] = None) -> None:
        # 한글 주석 — telegram align outer wrap + 420x600 strict
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 원격 요청")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("remoteRequestWrap")
        wrap.setStyleSheet(
            "QFrame#remoteRequestWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(12)

        # 한글 주석 — header
        header_row = QHBoxLayout()
        title = QLabel("원격 요청")
        title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        close_btn = make_close_button(self.reject, self)
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # 한글 주석 — 대상 친구 선택
        target_label = QLabel("대상 사용자")
        target_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        body.addWidget(target_label)
        self._target_combo = QComboBox()
        self._target_combo.setStyleSheet(
            "QComboBox { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 8px; }"
        )
        for f in (friends or []):
            uid = f.get("user_id") or f.get("target_id") or 0
            name = f.get("name", "?")
            self._target_combo.addItem(name, uid)
        if not friends:
            self._target_combo.addItem("등록된 친구 부재", 0)
        body.addWidget(self._target_combo)

        # 한글 주석 — mode 선택 (HELP / CONTROL)
        mode_label = QLabel("권한 mode")
        mode_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        body.addWidget(mode_label)
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("HELP (도움 모드 — view + input)", "help")
        self._mode_combo.addItem("CONTROL (제어 모드 — 2FA 의무)", "control")
        self._mode_combo.setStyleSheet(
            "QComboBox { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 8px; }"
        )
        body.addWidget(self._mode_combo)

        # 한글 주석 — duration 초
        dur_label = QLabel("유효 시간 (초)")
        dur_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        body.addWidget(dur_label)
        self._dur_spin = QSpinBox()
        self._dur_spin.setRange(60, 86400)
        self._dur_spin.setValue(1800)
        self._dur_spin.setStyleSheet(
            "QSpinBox { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 8px; }"
        )
        body.addWidget(self._dur_spin)

        # 한글 주석 — reason input
        reason_label = QLabel("요청 사유")
        reason_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        body.addWidget(reason_label)
        self._reason_edit = QTextEdit()
        self._reason_edit.setPlaceholderText("예: OBS 설정 도움 요청")
        self._reason_edit.setStyleSheet(
            "QTextEdit { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; padding: 8px; }"
        )
        body.addWidget(self._reason_edit, stretch=1)

        # 한글 주석 — send button
        send_btn = QPushButton("요청 보내기")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #0066FF;"
            " border: 0; border-radius: 8px; padding: 12px; font-weight: 600; }"
            "QPushButton:hover { background-color: #0052cc; }"
        )
        send_btn.clicked.connect(self._on_send)  # type: ignore[arg-type]
        body.addWidget(send_btn)

    def _on_send(self) -> None:
        # 한글 주석 — PermissionRequest 생성 + emit (transport binding = 추후 cycle)
        from app.remote.permission import PermissionRequest, PermissionMode
        target_id = self._target_combo.currentData() or 0
        if target_id <= 0:
            log.warning("[remote_request] target_id invalid — skip")
            self.reject()
            return
        mode_val = self._mode_combo.currentData() or "help"
        mode = PermissionMode.HELP if mode_val == "help" else PermissionMode.CONTROL
        duration = self._dur_spin.value()
        reason = self._reason_edit.toPlainText().strip() or "원격 도움 요청"
        try:
            req = PermissionRequest(
                requester_user_id=getattr(self.parent(), "_user_id", 1) or 1,
                target_user_id=int(target_id),
                mode=mode,
                duration_seconds=duration,
                reason=reason,
            )
            log.info("[remote_request] PermissionRequest created — target=%d mode=%s dur=%d",
                     req.target_user_id, req.mode.value, req.duration_seconds)
            self.request_sent.emit(req)
        except ValueError as exc:
            log.warning("[remote_request] PermissionRequest invalid — %r", exc)
        self.accept()


class RemoteConnectDialog(QDialog):
    """원격 연결 dialog — pending PermissionRequest list + accept/reject."""

    request_accepted = pyqtSignal(object)  # PermissionGrant
    request_rejected = pyqtSignal(object)  # PermissionRequest

    def __init__(self, pending: Optional[list] = None, parent: Optional[QWidget] = None) -> None:
        # 한글 주석 — telegram align outer wrap + 420x600 strict
        super().__init__(parent)
        self.setWindowTitle("TooTalk · 원격 연결")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("remoteConnectWrap")
        wrap.setStyleSheet(
            "QFrame#remoteConnectWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(12)

        # 한글 주석 — header
        header_row = QHBoxLayout()
        title = QLabel("원격 연결")
        title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        close_btn = make_close_button(self.reject, self)
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # 한글 주석 — 대기 요청 list
        pending_label = QLabel("대기 중 원격 요청")
        pending_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        body.addWidget(pending_label)
        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; }"
            "QListWidget::item { padding: 12px; }"
            "QListWidget::item:hover { background-color: #2c3a52; }"
        )
        body.addWidget(self._list, stretch=1)

        # 한글 주석 — accept + reject button row
        btn_row = QHBoxLayout()
        accept_btn = QPushButton("승인")
        accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        accept_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #0066FF;"
            " border: 0; border-radius: 8px; padding: 10px; font-weight: 600; }"
            "QPushButton:hover { background-color: #0052cc; }"
        )
        accept_btn.clicked.connect(self._on_accept)  # type: ignore[arg-type]
        btn_row.addWidget(accept_btn)
        reject_btn = QPushButton("거절")
        reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reject_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #4b5563;"
            " border: 0; border-radius: 8px; padding: 10px; font-weight: 600; }"
            "QPushButton:hover { background-color: #374151; }"
        )
        reject_btn.clicked.connect(self._on_reject)  # type: ignore[arg-type]
        btn_row.addWidget(reject_btn)
        body.addLayout(btn_row)

        self._pending: list = list(pending or [])
        self._populate()

    def _populate(self) -> None:
        # 한글 주석 — pending PermissionRequest list 표시
        self._list.clear()
        for req in self._pending:
            requester = getattr(req, "requester_user_id", "?")
            mode = getattr(req, "mode", None)
            mode_val = mode.value if mode is not None else "?"
            dur = getattr(req, "duration_seconds", 0)
            reason = getattr(req, "reason", "")
            item = QListWidgetItem(f"요청자 #{requester}  ·  {mode_val}  ·  {dur}s\n{reason}")
            item.setData(Qt.ItemDataRole.UserRole, req)
            self._list.addItem(item)
        if not self._pending:
            empty = QListWidgetItem("대기 중 요청 부재")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(empty)

    def _on_accept(self) -> None:
        # 한글 주석 — PermissionGrant 생성 + emit + RemoteSession start
        from app.remote.permission import PermissionGrant, derive_revoke_token
        item = self._list.currentItem()
        if item is None:
            return
        req = item.data(Qt.ItemDataRole.UserRole)
        if req is None:
            return
        now_ms = int(time.time() * 1000)
        try:
            grant = PermissionGrant(
                request=req,
                granted_at_ms=now_ms,
                expires_at_ms=now_ms + req.duration_seconds * 1000,
                revoke_token=derive_revoke_token(),
                scope="screen+input" if req.mode.value == "control" else "screen_only",
            )
            log.info("[remote_connect] PermissionGrant — target=%d mode=%s scope=%s",
                     req.target_user_id, req.mode.value, grant.scope)
            self.request_accepted.emit(grant)
        except ValueError as exc:
            log.warning("[remote_connect] PermissionGrant invalid — %r", exc)
        self.accept()

    def _on_reject(self) -> None:
        # 한글 주석 — 요청 거절 emit
        item = self._list.currentItem()
        if item is None:
            self.reject()
            return
        req = item.data(Qt.ItemDataRole.UserRole)
        if req is not None:
            log.info("[remote_connect] 거절 — requester=%d", getattr(req, "requester_user_id", 0))
            self.request_rejected.emit(req)
        self.reject()
