# SPDX-License-Identifier: GPL-3.0-or-later
"""user_activity ENUM unit test — cycle 169.698 신설.

ActivityAction + SessionEndReason ENUM 의 정합 verify.
"""

from __future__ import annotations


class TestSessionEndReason:
    def test_5_enums_exist(self) -> None:
        from server.db.repositories.user_activity import SessionEndReason

        # 한글 주석 — DDL 0007 정합 5 ENUM
        assert SessionEndReason.LOGOUT.value == "logout"
        assert SessionEndReason.IDLE_TIMEOUT.value == "idle_timeout"
        assert SessionEndReason.TOKEN_REVOKE.value == "token_revoke"
        assert SessionEndReason.FORCE_DISCONNECT.value == "force_disconnect"
        assert SessionEndReason.SERVER_RESTART.value == "server_restart"

    def test_str_enum_protocol(self) -> None:
        from server.db.repositories.user_activity import SessionEndReason

        # 한글 주석 — str Enum → "logout" string 직접 equality
        assert SessionEndReason.LOGOUT == "logout"

    def test_enum_count_5(self) -> None:
        from server.db.repositories.user_activity import SessionEndReason

        assert len(list(SessionEndReason)) == 5


class TestActivityActionBasic:
    def test_login_logout_signup_exist(self) -> None:
        from server.db.repositories.user_activity import ActivityAction

        assert ActivityAction.LOGIN.value == "login"
        assert ActivityAction.LOGOUT.value == "logout"
        assert ActivityAction.SIGNUP.value == "signup"

    def test_friend_5_actions(self) -> None:
        from server.db.repositories.user_activity import ActivityAction

        # 한글 주석 — friend chain 5 ENUM
        assert ActivityAction.FRIEND_REQUEST.value == "friend_request"
        assert ActivityAction.FRIEND_ACCEPT.value == "friend_accept"
        assert ActivityAction.FRIEND_REJECT.value == "friend_reject"
        assert ActivityAction.FRIEND_BLOCK.value == "friend_block"
        assert ActivityAction.FRIEND_REMOVE.value == "friend_remove"
