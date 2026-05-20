# SPDX-License-Identifier: GPL-3.0-or-later
"""FolderClient worker test (cycle 169.80 신설 — MED-3 회수)."""

from __future__ import annotations

import pytest

try:
    from PyQt6.QtCore import Qt
    _PYQT_AVAILABLE = True
except ImportError:
    _PYQT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _PYQT_AVAILABLE, reason="PyQt6 미설치")


class TestFolderClientWorkers:
    """FolderCreateWorker / FolderListWorker / FolderDeleteWorker / FolderInviteWorker init verify."""

    def test_folder_create_worker_path_post(self) -> None:
        from app.net.folder_client import FolderCreateWorker
        worker = FolderCreateWorker(
            base_url="https://fake.local",
            token="tok",
            folder_data={"folder_id": "abc12345", "name": "X"},
        )
        assert worker._url == "https://fake.local/api/folders"
        assert worker._method == "POST"
        # cycle 169.79 LOW-3 — Create timeout 30s
        assert worker._timeout == 30
        assert worker._payload == {"folder_id": "abc12345", "name": "X"}

    def test_folder_list_worker_get(self) -> None:
        from app.net.folder_client import FolderListWorker
        worker = FolderListWorker(base_url="https://fake.local", token="tok")
        assert worker._method == "GET"
        assert worker._timeout == 10
        assert worker._payload is None

    def test_folder_delete_worker_path(self) -> None:
        from app.net.folder_client import FolderDeleteWorker
        worker = FolderDeleteWorker(base_url="https://fake.local", token="tok", folder_id="abc12345")
        assert worker._url == "https://fake.local/api/folders/abc12345"
        assert worker._method == "DELETE"

    def test_folder_invite_worker_path(self) -> None:
        from app.net.folder_client import FolderInviteWorker
        worker = FolderInviteWorker(base_url="https://fake.local", token="tok", folder_id="abc12345")
        assert worker._url == "https://fake.local/api/folders/abc12345/invite"
        assert worker._method == "POST"


class TestSslContextEnv:
    """cycle 169.79 HIGH-1 회수 — TOOTALK_TLS_VERIFY env override."""

    def test_default_verify_enabled(self, monkeypatch) -> None:
        monkeypatch.delenv("TOOTALK_TLS_VERIFY", raising=False)
        from app.net._ssl_util import build_ssl_context
        import ssl
        ctx = build_ssl_context()
        # default = production safe (CERT_REQUIRED)
        assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_env_zero_disables_verify(self, monkeypatch) -> None:
        monkeypatch.setenv("TOOTALK_TLS_VERIFY", "0")
        from app.net._ssl_util import build_ssl_context
        import ssl
        ctx = build_ssl_context()
        assert ctx.verify_mode == ssl.CERT_NONE
        assert ctx.check_hostname is False
