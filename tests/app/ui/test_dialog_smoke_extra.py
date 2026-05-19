# SPDX-License-Identifier: GPL-3.0-or-later
"""추가 dialog smoke test — PasswordResetDialog + AddFriendDialog + InviteDialog + SettingsDialog + UpdateDialog (cycle 169.27 신설).

사용자 directive '다른 dialog 도 자동 test 추가해' verbatim 회수.
"""

from __future__ import annotations

import pytest

try:
    from PyQt6.QtCore import Qt
    _PYQT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYQT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _PYQT_AVAILABLE, reason="PyQt6 미설치")


class _MockAuthClient:
    async def login(self, email, password):
        return type("R", (), {"ok": False, "token": None, "user_id": None, "error_code": "M", "error_message": "m"})()

    async def register(self, email, username, password):
        return type("R", (), {"ok": False, "error_message": "m"})()

    async def reset_password(self, email):
        return type("R", (), {"ok": False, "error_message": "m"})()

    async def close(self):
        pass


class TestPasswordResetDialogSmoke:
    def test_instantiate_no_crash(self, qtbot) -> None:
        from app.ui.password_reset_dialog import PasswordResetDialog
        dialog = PasswordResetDialog(auth_client=_MockAuthClient())
        qtbot.addWidget(dialog)
        assert "TooTalk" in dialog.windowTitle() or dialog.windowTitle()
        dialog.close()


class TestAddFriendDialogSmoke:
    def test_instantiate_no_crash(self, qtbot) -> None:
        from app.ui.add_friend_dialog import AddFriendDialog
        dialog = AddFriendDialog()
        qtbot.addWidget(dialog)
        dialog.close()


class TestInviteDialogSmoke:
    def test_instantiate_no_crash(self, qtbot) -> None:
        from app.ui.invite_dialog import InviteDialog
        dialog = InviteDialog(room_id=1, friends=[], room_title="test room")
        qtbot.addWidget(dialog)
        dialog.close()


class TestSettingsDialogSmoke:
    def test_instantiate_no_crash(self, qtbot) -> None:
        from app.ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(sound_player=None)
        qtbot.addWidget(dialog)
        # cycle 153.5 — 10 section tabbed dialog
        assert dialog._tabs.count() == 10
        dialog.close()


class TestUpdateDialogSmoke:
    def test_instantiate_no_crash(self, qtbot) -> None:
        from app.ui.update_dialog import UpdateDialog
        latest = {
            "latest_version": "1.0.0",
            "download_url": "https://example.com/x.zip",
            "release_notes": "test",
        }
        dialog = UpdateDialog(current_version="0.9.0", latest_info=latest)
        qtbot.addWidget(dialog)
        dialog.close()
