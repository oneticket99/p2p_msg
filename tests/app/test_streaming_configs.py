# SPDX-License-Identifier: GPL-3.0-or-later
"""streaming client config validation unit test — cycle 169.692 신설."""

from __future__ import annotations

import pytest


class TestTwitchChatConfig:
    def test_empty_oauth_raises(self) -> None:
        from app.bot.streaming.twitch_client import TwitchChatConfig

        with pytest.raises(ValueError, match="oauth_token"):
            TwitchChatConfig(oauth_token="", bot_login="b", channel="c")

    def test_empty_login_raises(self) -> None:
        from app.bot.streaming.twitch_client import TwitchChatConfig

        with pytest.raises(ValueError, match="bot_login"):
            TwitchChatConfig(oauth_token="t", bot_login="", channel="c")

    def test_channel_hash_prefix_raises(self) -> None:
        # 한글 주석 — '#' prefix 제외 의무
        from app.bot.streaming.twitch_client import TwitchChatConfig

        with pytest.raises(ValueError, match="prefix"):
            TwitchChatConfig(oauth_token="t", bot_login="b", channel="#alice")

    def test_valid_construct(self) -> None:
        from app.bot.streaming.twitch_client import TwitchChatConfig

        c = TwitchChatConfig(oauth_token="t", bot_login="bot", channel="alice")
        assert c.channel == "alice"


class TestKickChatConfig:
    def test_empty_slug_raises(self) -> None:
        from app.bot.streaming.kick_client import KickChatConfig

        with pytest.raises(ValueError, match="channel_slug"):
            KickChatConfig(channel_slug="", chatroom_id="42",
                           pusher_app_key="key")

    def test_empty_chatroom_raises(self) -> None:
        from app.bot.streaming.kick_client import KickChatConfig

        with pytest.raises(ValueError, match="chatroom_id"):
            KickChatConfig(channel_slug="adin", chatroom_id="",
                           pusher_app_key="key")

    def test_empty_pusher_key_raises(self) -> None:
        from app.bot.streaming.kick_client import KickChatConfig

        with pytest.raises(ValueError, match="pusher_app_key"):
            KickChatConfig(channel_slug="adin", chatroom_id="42",
                           pusher_app_key="")

    def test_valid_construct_no_auth(self) -> None:
        # 한글 주석 — public chat = auth_token 부재 graceful
        from app.bot.streaming.kick_client import KickChatConfig

        c = KickChatConfig(channel_slug="adin", chatroom_id="42",
                           pusher_app_key="key")
        assert c.auth_token == ""


class TestChzzkChatConfig:
    def test_empty_channel_raises(self) -> None:
        from app.bot.streaming.chzzk_client import ChzzkChatConfig

        with pytest.raises(ValueError, match="channel_id"):
            ChzzkChatConfig(channel_id="", chat_channel_id="cc",
                            access_token="tok")

    def test_empty_chat_channel_raises(self) -> None:
        from app.bot.streaming.chzzk_client import ChzzkChatConfig

        with pytest.raises(ValueError, match="chat_channel_id"):
            ChzzkChatConfig(channel_id="ch", chat_channel_id="",
                            access_token="tok")

    def test_empty_token_raises(self) -> None:
        from app.bot.streaming.chzzk_client import ChzzkChatConfig

        with pytest.raises(ValueError, match="access_token"):
            ChzzkChatConfig(channel_id="ch", chat_channel_id="cc",
                            access_token="")

    def test_valid_anonymous_viewer(self) -> None:
        from app.bot.streaming.chzzk_client import ChzzkChatConfig

        c = ChzzkChatConfig(channel_id="ch", chat_channel_id="cc",
                            access_token="tok")
        assert c.user_id_hash == ""
