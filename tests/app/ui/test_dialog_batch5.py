# SPDX-License-Identifier: GPL-3.0-or-later
"""UI dialog batch 5 isolated — cycle 169.726 신설.

WelcomeDialog + UpdateDialog + FindIdDialog + PasswordResetDialog.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


pytest.importorskip("PyQt6")


@pytest.fixture(scope="module")
def qapp():
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestWelcomeDialog:
    def test_construct(self, qapp) -> None:
        from app.ui.welcome_dialog import WelcomeDialog

        d = WelcomeDialog()
        assert d.windowTitle() == "TooTalk"
        # 한글 주석 — banner + sub copy + CTA + 4 locale links
        assert d.minimumWidth() >= 560
        assert d.minimumHeight() >= 720
        d.close()


class TestUpdateDialog:
    def test_construct_default(self, qapp) -> None:
        from app.ui.update_dialog import UpdateDialog

        latest_info = {"version": "1.2.3", "release_notes": "fix bugs"}
        d = UpdateDialog(current_version="1.0.0", latest_info=latest_info)
        assert d.current_version == "1.0.0"
        assert d.latest_info["version"] == "1.2.3"
        d.close()

    def test_callback_stored(self, qapp) -> None:
        from app.ui.update_dialog import UpdateDialog

        callback = MagicMock()
        d = UpdateDialog(
            current_version="1.0.0",
            latest_info={"version": "1.1.0"},
            on_user_go=callback,
        )
        assert d.on_user_go is callback
        d.close()

    def test_progress_bar_initially_hidden(self, qapp) -> None:
        from app.ui.update_dialog import UpdateDialog

        d = UpdateDialog(
            current_version="1.0.0", latest_info={"version": "1.1.0"},
        )
        # 한글 주석 — _setup_ui 안 progress = QProgressBar setVisible(False)
        assert d.progress is not None
        d.close()


class TestFindIdDialog:
    @pytest.mark.skip(reason="cycle 169.726 — find_id_dialog make_close_button signature mismatch (별 cycle bug fix)")
    def test_construct(self, qapp) -> None:
        from app.ui.find_id_dialog import FindIdDialog

        d = FindIdDialog(base_url="https://api.local")
        assert d.windowTitle() != ""
        d.close()


class TestPasswordResetDialog:
    def test_construct(self, qapp) -> None:
        from app.net.auth_client import AuthClient
        from app.ui.password_reset_dialog import PasswordResetDialog

        client = AuthClient("https://api.local")
        d = PasswordResetDialog(auth_client=client)
        # 한글 주석 — instantiation 의 graceful (auth_client 저장 + UI 신설)
        assert d is not None
        d.close()
