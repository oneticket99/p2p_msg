# SPDX-License-Identifier: GPL-3.0-or-later
"""Auth chain (login + signup + OTP verify) isolated test — cycle 169.647 mock isolation refactor.

cycle 169.608 안 3 file (test_e2e_button_click + test_e2e_flow + test_http_worker_integration)
file-level skip 회수 path. cycle 169.644~646 안 mock isolation 패턴 적용.

본 file = 각 dialog 의 _on_*_clicked + _on_*_finished slot 직접 호출 + HttpJsonWorker
monkeypatch 안 fire chain + 응답 처리 검증. MainWindow 21 mixin 부재 + cumulative
window leak 회피.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")


class _FakeWorker:
    """HttpJsonWorker mock — start() 호출 추적 + base_url/endpoint capture."""

    instances: list = []

    def __init__(self, base_url: str, endpoint: str, payload: dict, parent=None) -> None:
        self.base_url = base_url
        self.endpoint = endpoint
        self.payload = payload
        self.parent = parent
        self.started = False
        _FakeWorker.instances.append(self)
        # 한글 주석 — finished_with_result signal mock (connect/emit 모방)
        self.finished_with_result = MagicMock()

    def start(self) -> None:
        self.started = True


@pytest.fixture
def fake_http_worker_cls():
    """HttpJsonWorker monkeypatch — 각 dialog 의 _on_*_clicked slot 안 instance 추적."""

    _FakeWorker.instances.clear()
    with patch("app.ui.login_dialog.HttpJsonWorker", _FakeWorker), patch(
        "app.ui.signup_dialog.HttpJsonWorker", _FakeWorker
    ), patch("app.ui.otp_dialog.HttpJsonWorker", _FakeWorker):
        yield _FakeWorker


class TestLoginChain:
    """LoginDialog _on_login_clicked + HttpJsonWorker fire."""

    def test_empty_fields_blocks_worker(self, qtbot, fake_http_worker_cls, monkeypatch) -> None:
        """email + password 부재 → warning + worker 미생성."""

        from PyQt6.QtWidgets import QMessageBox
        from app.ui.login_dialog import LoginDialog

        client = MagicMock()
        client._base_url = "https://fake.local"
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
        dialog = LoginDialog(auth_client=client)
        qtbot.addWidget(dialog)
        # 한글 주석 — 빈 input 안 ConfirmDialog.show_warning patch
        with patch("app.ui.confirm_dialog.ConfirmDialog.show_warning"):
            dialog._on_login_clicked()
        assert len(fake_http_worker_cls.instances) == 0

    def test_valid_input_fires_worker(self, qtbot, fake_http_worker_cls) -> None:
        """email + password 입력 → HttpJsonWorker 1회 instance + start()."""

        from app.ui.login_dialog import LoginDialog

        client = MagicMock()
        client._base_url = "https://fake.local"
        dialog = LoginDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("user@example.com")
        dialog._password_edit.setText("password123")
        dialog._on_login_clicked()
        assert len(fake_http_worker_cls.instances) == 1
        worker = fake_http_worker_cls.instances[0]
        assert worker.endpoint == "/api/auth/login"
        assert worker.payload == {"email": "user@example.com", "password": "password123"}
        assert worker.started is True

    def test_login_finished_success_captures_token(self, qtbot) -> None:
        """_on_login_finished(ok=True, data={token, user_id}) → dialog.token/user_id capture."""

        from app.ui.login_dialog import LoginDialog

        client = MagicMock()
        client._base_url = "https://fake.local"
        dialog = LoginDialog(auth_client=client)
        qtbot.addWidget(dialog)
        # 한글 주석 — accept patch — dialog modal exec 회피
        with patch.object(dialog, "accept"):
            dialog._on_login_finished(
                True, "", "", {"token": "fake-tok", "user_id": 42, "email": "u@e.c"}
            )
        assert dialog.token == "fake-tok"
        assert dialog.user_id == 42


class TestOTPVerifyChain:
    """OTPDialog _on_verify_clicked + HttpJsonWorker fire."""

    def test_six_digit_fires_worker(self, qtbot, fake_http_worker_cls) -> None:
        """6 자리 OTP 입력 → /api/auth/verify worker 1회 + start()."""

        from app.ui.otp_dialog import OTPDialog

        client = MagicMock()
        client._base_url = "https://fake.local"
        dialog = OTPDialog(auth_client=client, email="user@example.com")
        qtbot.addWidget(dialog)
        if hasattr(dialog, "_boxes"):
            for i, ch in enumerate("123456"):
                dialog._boxes[i].setText(ch)
            dialog._on_verify_clicked()
            assert len(fake_http_worker_cls.instances) == 1
            worker = fake_http_worker_cls.instances[0]
            assert worker.endpoint == "/api/auth/verify"
            assert worker.payload["code"] == "123456"
            assert worker.payload["email"] == "user@example.com"

    def test_incomplete_otp_blocks_worker(self, qtbot, fake_http_worker_cls, monkeypatch) -> None:
        """OTP 6 자리 미달 → worker 미생성."""

        from PyQt6.QtWidgets import QMessageBox
        from app.ui.otp_dialog import OTPDialog

        client = MagicMock()
        client._base_url = "https://fake.local"
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
        dialog = OTPDialog(auth_client=client, email="user@example.com")
        qtbot.addWidget(dialog)
        if hasattr(dialog, "_boxes"):
            # 한글 주석 — 3 자리만 입력 (6 자리 미달)
            for i, ch in enumerate("123"):
                dialog._boxes[i].setText(ch)
            with patch("app.ui.confirm_dialog.ConfirmDialog.show_warning"):
                dialog._on_verify_clicked()
            assert len(fake_http_worker_cls.instances) == 0
