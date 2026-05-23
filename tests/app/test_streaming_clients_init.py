# SPDX-License-Identifier: GPL-3.0-or-later
"""ChzzkChatClient + KickChatClient + TwitchChatClient init/state unit test — cycle 169.701 신설."""

from __future__ import annotations

import pytest


class TestChzzkChatClientInit:
    def test_config_stored(self) -> None:
        from app.bot.streaming.chzzk_client import ChzzkChatClient, ChzzkChatConfig

        cfg = ChzzkChatConfig(channel_id="ch", chat_channel_id="cc",
                              access_token="tok")
        c = ChzzkChatClient(cfg)
        assert c.config is cfg
        assert c.is_connected is False

    def test_callback_stored(self) -> None:
        from app.bot.streaming.chzzk_client import ChzzkChatClient, ChzzkChatConfig

        async def cb(msg):
            pass

        cfg = ChzzkChatConfig(channel_id="ch", chat_channel_id="cc",
                              access_token="tok")
        c = ChzzkChatClient(cfg, on_message=cb)
        assert c._on_message is cb

    @pytest.mark.asyncio
    async def test_connect_returns_false_no_ws_lib(self, monkeypatch) -> None:
        # 한글 주석 — websockets 의 library 부재 graceful → False
        from app.bot.streaming import chzzk_client
        from app.bot.streaming.chzzk_client import ChzzkChatClient, ChzzkChatConfig

        monkeypatch.setattr(chzzk_client, "_WS_AVAILABLE", False)
        cfg = ChzzkChatConfig(channel_id="ch", chat_channel_id="cc",
                              access_token="tok")
        c = ChzzkChatClient(cfg)
        result = await c.connect()
        assert result is False
        assert c.is_connected is False

    @pytest.mark.asyncio
    async def test_receive_loop_empty_when_disconnected(self) -> None:
        from app.bot.streaming.chzzk_client import ChzzkChatClient, ChzzkChatConfig

        cfg = ChzzkChatConfig(channel_id="ch", chat_channel_id="cc",
                              access_token="tok")
        c = ChzzkChatClient(cfg)
        # 한글 주석 — disconnected 상태 → empty list
        result = await c.receive_loop()
        assert result == []

    @pytest.mark.asyncio
    async def test_disconnect_noop_when_no_ws(self) -> None:
        from app.bot.streaming.chzzk_client import ChzzkChatClient, ChzzkChatConfig

        cfg = ChzzkChatConfig(channel_id="ch", chat_channel_id="cc",
                              access_token="tok")
        c = ChzzkChatClient(cfg)
        await c.disconnect()
        assert c.is_connected is False
        assert c._sid is None


class TestKickChatClientInit:
    def test_config_stored(self) -> None:
        from app.bot.streaming.kick_client import KickChatClient, KickChatConfig

        cfg = KickChatConfig(channel_slug="adin", chatroom_id="42",
                             pusher_app_key="key")
        c = KickChatClient(cfg)
        assert c.config is cfg
        assert c.is_connected is False


class TestTwitchChatClientInit:
    def test_config_stored(self) -> None:
        from app.bot.streaming.twitch_client import TwitchChatClient, TwitchChatConfig

        cfg = TwitchChatConfig(oauth_token="tok", bot_login="bot",
                               channel="alice")
        c = TwitchChatClient(cfg)
        assert c.config is cfg
        assert c.is_connected is False
