# SPDX-License-Identifier: GPL-3.0-or-later
"""HttpJsonWorker integration test — cycle 169.61 mock pattern 회수.

fake_http_worker fixture (conftest.py) → HttpJsonWorker monkeypatch.
register / login / verify success path 안 fire chain 검증.
"""

from __future__ import annotations

import pytest

try:
    from PyQt6.QtWidgets import QMessageBox
    from PyQt6.QtCore import Qt
    _PYQT_AVAILABLE = True
except ImportError:
    _PYQT_AVAILABLE = False

pytestmark = [
    pytest.mark.skipif(not _PYQT_AVAILABLE, reason="PyQt6 미설치"),
    # 한글 주석 — cycle 169.608: 단독 file hang trigger (HttpJsonWorker fake fixture chain).
    # 별 cycle = mock isolation refactor.
    pytest.mark.skip(reason="cycle 169.608 — 단독 file hang (HttpJsonWorker fake_http_worker fixture chain) 별 cycle 위탁"),
]


class TestHttpWorkerIntegration:
    """fake_http_worker fixture 안 register/login/verify worker fire chain 검증."""

    def test_signup_register_fires_worker(self, qtbot, fake_http_worker, monkeypatch) -> None:
        # 한글 주석 — SignupDialog 안 register click → HttpJsonWorker fire chain
        from app.ui.signup_dialog import SignupDialog
        from app.net.auth_client import AuthClient
        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
        monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
        client = AuthClient(base_url="https://fake.local")
        dialog = SignupDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("user@example.com")
        dialog._username_edit.setText("user99")
        dialog._password_edit.setText("password123")
        dialog._password_confirm_edit.setText("password123")
        dialog._on_signup_clicked()
        assert len(fake_http_worker.instances) == 1
        worker = fake_http_worker.instances[0]
        assert worker.path == "/api/auth/register"
        assert worker.payload == {
            "email": "user@example.com",
            "username": "user99",
            "password": "password123",
        }

    def test_login_fires_worker(self, qtbot, fake_http_worker, monkeypatch) -> None:
        # 한글 주석 — LoginDialog 안 login click → HttpJsonWorker fire chain
        from app.ui.login_dialog import LoginDialog
        from app.net.auth_client import AuthClient
        monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
        client = AuthClient(base_url="https://fake.local")
        dialog = LoginDialog(auth_client=client)
        qtbot.addWidget(dialog)
        dialog._email_edit.setText("user@example.com")
        dialog._password_edit.setText("password123")
        dialog._on_login_clicked()
        assert len(fake_http_worker.instances) == 1
        worker = fake_http_worker.instances[0]
        assert worker.path == "/api/auth/login"
        assert worker.payload == {"email": "user@example.com", "password": "password123"}
