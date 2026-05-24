# SPDX-License-Identifier: GPL-3.0-or-later
"""UI dialog batch 6 isolated — cycle 169.729 신설.

OTPDialog + LoginDialog + PendingRequestsDialog + AddFriendByUsernameDialog.
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


class TestOTPDialog:
    def test_construct(self, qapp) -> None:
        from app.net.auth_client import AuthClient
        from app.ui.otp_dialog import OTPDialog

        client = AuthClient("https://api.local")
        d = OTPDialog(auth_client=client, email="x@x.com")
        assert d._email == "x@x.com"
        assert d._token is None
        assert d._verify_in_flight is False
        d._countdown_timer.stop()
        d.close()

    def test_get_otp_concat(self, qapp) -> None:
        from app.net.auth_client import AuthClient
        from app.ui.otp_dialog import OTPDialog

        client = AuthClient("https://api.local")
        d = OTPDialog(auth_client=client, email="x@x.com")
        # 한글 주석 — 6 box 안 digit 입력 → concat
        for i, box in enumerate(d._boxes):
            box.setText(str(i))
        assert d._get_otp() == "012345"
        d._countdown_timer.stop()
        d.close()

    def test_six_boxes(self, qapp) -> None:
        from app.net.auth_client import AuthClient
        from app.ui.otp_dialog import OTPDialog

        client = AuthClient("https://api.local")
        d = OTPDialog(auth_client=client, email="x@x.com")
        assert len(d._boxes) == 6
        d._countdown_timer.stop()
        d.close()


class TestLoginDialog:
    def test_construct(self, qapp) -> None:
        from app.net.auth_client import AuthClient
        from app.ui.login_dialog import LoginDialog

        client = AuthClient("https://api.local")
        d = LoginDialog(auth_client=client)
        assert d is not None
        d.close()


class TestPendingRequestsDialog:
    def test_construct_no_client(self, qapp) -> None:
        from app.ui.pending_requests_dialog import PendingRequestsDialog

        d = PendingRequestsDialog(friends_client=None)
        assert d._fc is None
        assert d.minimumWidth() >= 420
        d.close()

    def test_construct_with_client(self, qapp) -> None:
        from app.ui.pending_requests_dialog import PendingRequestsDialog

        fc = MagicMock()
        d = PendingRequestsDialog(friends_client=fc)
        assert d._fc is fc
        d.close()


class TestAddFriendByUsernameDialog:
    def test_construct(self, qapp) -> None:
        from app.ui.add_friend_by_username_dialog import AddFriendByUsernameDialog

        d = AddFriendByUsernameDialog()
        assert d.windowTitle() == "사용자명 검색"
        assert d.width() == 420
        assert d.height() == 280
        d.close()
