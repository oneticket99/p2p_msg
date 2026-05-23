# SPDX-License-Identifier: GPL-3.0-or-later
"""FolderWorker URL composition unit test — cycle 169.679 omit 제거.

PyQt6 QThread init 만 verify — run() thread start 부재.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def qapp():
    # 한글 주석 — QThread instantiation 의무 QApplication
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestFolderCreateWorker:
    def test_url_method_payload(self, qapp) -> None:
        from app.net.folder_client import FolderCreateWorker

        w = FolderCreateWorker(
            "https://api.local/", token="t", folder_data={"name": "x"}
        )
        assert w._url == "https://api.local/api/folders"
        assert w._method == "POST"
        assert w._payload == {"name": "x"}
        assert w._timeout == 30


class TestFolderUpdateWorker:
    def test_patch_url(self, qapp) -> None:
        from app.net.folder_client import FolderUpdateWorker

        w = FolderUpdateWorker(
            "https://api.local", token="t", folder_id="abc",
            folder_data={"name": "y"},
        )
        assert w._url == "https://api.local/api/folders/abc"
        assert w._method == "PATCH"
        assert w._timeout == 30


class TestFolderListWorker:
    def test_get_url(self, qapp) -> None:
        from app.net.folder_client import FolderListWorker

        w = FolderListWorker("https://api.local/", token="t")
        assert w._url == "https://api.local/api/folders"
        assert w._method == "GET"
        assert w._payload is None
        assert w._timeout == 10


class TestFolderDeleteWorker:
    def test_delete_url(self, qapp) -> None:
        from app.net.folder_client import FolderDeleteWorker

        w = FolderDeleteWorker("https://api.local", token="t", folder_id="42")
        assert w._url == "https://api.local/api/folders/42"
        assert w._method == "DELETE"
        assert w._payload is None


class TestFolderInviteWorker:
    def test_invite_url(self, qapp) -> None:
        from app.net.folder_client import FolderInviteWorker

        w = FolderInviteWorker("https://api.local", token="t", folder_id="42")
        assert w._url == "https://api.local/api/folders/42/invite"
        assert w._method == "POST"
        # 한글 주석 — invite payload = empty dict (signature)
        assert w._payload == {}


class TestBaseFolderWorker:
    def test_token_stored(self, qapp) -> None:
        from app.net.folder_client import FolderListWorker

        w = FolderListWorker("https://api.local", token="my-bearer-token")
        assert w._token == "my-bearer-token"

    def test_trailing_slash_normalized(self, qapp) -> None:
        from app.net.folder_client import FolderCreateWorker

        # 한글 주석 — base_url 끝 slash 다중 → 단일 rstrip
        w = FolderCreateWorker("https://api.local//", token="t", folder_data={})
        assert w._url == "https://api.local/api/folders"
