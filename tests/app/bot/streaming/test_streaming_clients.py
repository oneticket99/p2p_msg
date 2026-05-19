# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.streaming`` 4 platform chat client 단위 테스트 — 사이클 146.

3 × 4 platform = 12 test
-----------------------
- init (config + client 인스턴스화 검증)
- graceful (connect skeleton False + receive_loop disconnected []) 검증
- dataclass (ChatMessage frozen + field validation) 검증

실 platform API call 차단 — graceful path 만 검증.
"""

from __future__ import annotations

import asyncio

import pytest

from app.bot.streaming import (
    ChatMessage,
    ChzzkChatClient,
    KickChatClient,
    TwitchChatClient,
    YouTubeChatClient,
)
from app.bot.streaming.chzzk_client import ChzzkChatConfig
from app.bot.streaming.kick_client import KickChatConfig
from app.bot.streaming.twitch_client import TwitchChatConfig
from app.bot.streaming.youtube_client import YouTubeChatConfig


# ─── YouTube ──────────────────────────────────────────────────────────────


class TestYouTubeChatClient:
    """YouTube Live Chat API v3 client skeleton 검증."""

    def _config(self) -> YouTubeChatConfig:
        return YouTubeChatConfig(
            access_token="ya29.fake_token",
            live_chat_id="Cg0KC2xpdmVfY2hhdF9pZA",
        )

    def test_init_default(self) -> None:
        client = YouTubeChatClient(self._config())
        assert client.is_connected is False
        assert client.PLATFORM == "youtube"
        assert client.config.live_chat_id.startswith("Cg")

    def test_graceful_skeleton(self) -> None:
        client = YouTubeChatClient(self._config())
        # connect = graceful False (skeleton)
        assert asyncio.run(client.connect()) is False
        # receive_loop = 미연결 시 [] 반환
        msgs = asyncio.run(client.receive_loop(max_iterations=1))
        assert msgs == []
        # disconnect 안전 (never connected)
        asyncio.run(client.disconnect())
        assert client.is_connected is False

    def test_dataclass_validation(self) -> None:
        # empty token 차단
        with pytest.raises(ValueError, match="access_token 빈 문자열 불가"):
            YouTubeChatConfig(access_token="", live_chat_id="x")
        # empty chat_id 차단
        with pytest.raises(ValueError, match="live_chat_id 빈 문자열 불가"):
            YouTubeChatConfig(access_token="t", live_chat_id="")
        # poll_interval 0 차단
        with pytest.raises(ValueError, match="poll_interval_seconds"):
            YouTubeChatConfig(
                access_token="t",
                live_chat_id="x",
                poll_interval_seconds=0,
            )


# ─── Twitch ───────────────────────────────────────────────────────────────


class TestTwitchChatClient:
    """Twitch IRC WebSocket client skeleton 검증."""

    def _config(self) -> TwitchChatConfig:
        return TwitchChatConfig(
            oauth_token="fake_oauth_token",
            bot_login="tootalkbot",
            channel="streamer",
        )

    def test_init_default(self) -> None:
        client = TwitchChatClient(self._config())
        assert client.is_connected is False
        assert client.PLATFORM == "twitch"
        assert client.config.channel == "streamer"

    def test_graceful_skeleton(self) -> None:
        client = TwitchChatClient(self._config())
        # connect = graceful False
        assert asyncio.run(client.connect()) is False
        # receive_loop = 미연결 시 [] 반환
        msgs = asyncio.run(client.receive_loop(max_iterations=1))
        assert msgs == []
        asyncio.run(client.disconnect())
        assert client.is_connected is False

    def test_dataclass_validation(self) -> None:
        # empty token 차단
        with pytest.raises(ValueError, match="oauth_token 빈 문자열 불가"):
            TwitchChatConfig(oauth_token="", bot_login="b", channel="c")
        # channel '#' prefix 차단
        with pytest.raises(ValueError, match="channel '#' prefix 제외"):
            TwitchChatConfig(oauth_token="t", bot_login="b", channel="#wrong")
        # bot_login empty 차단
        with pytest.raises(ValueError, match="bot_login 빈 문자열 불가"):
            TwitchChatConfig(oauth_token="t", bot_login="", channel="c")


# ─── CHZZK ────────────────────────────────────────────────────────────────


class TestChzzkChatClient:
    """네이버 CHZZK Chat WebSocket client skeleton 검증."""

    def _config(self) -> ChzzkChatConfig:
        return ChzzkChatConfig(
            channel_id="abc123def456",
            chat_channel_id="N1_CHAT_XYZ",
            access_token="fake_chzzk_token",
        )

    def test_init_default(self) -> None:
        client = ChzzkChatClient(self._config())
        assert client.is_connected is False
        assert client.PLATFORM == "chzzk"
        # CMD constant 검증
        assert client.CMD_CONNECT == 100
        assert client.CMD_CHAT == 93101

    def test_graceful_skeleton(self) -> None:
        client = ChzzkChatClient(self._config())
        assert asyncio.run(client.connect()) is False
        msgs = asyncio.run(client.receive_loop(max_iterations=1))
        assert msgs == []
        asyncio.run(client.disconnect())
        assert client.is_connected is False

    def test_dataclass_validation(self) -> None:
        with pytest.raises(ValueError, match="channel_id 빈 문자열 불가"):
            ChzzkChatConfig(channel_id="", chat_channel_id="x", access_token="t")
        with pytest.raises(ValueError, match="chat_channel_id 빈 문자열 불가"):
            ChzzkChatConfig(channel_id="x", chat_channel_id="", access_token="t")
        with pytest.raises(ValueError, match="access_token 빈 문자열 불가"):
            ChzzkChatConfig(channel_id="x", chat_channel_id="y", access_token="")


# ─── Kick ─────────────────────────────────────────────────────────────────


class TestKickChatClient:
    """Kick Pusher WebSocket client skeleton 검증."""

    def _config(self) -> KickChatConfig:
        return KickChatConfig(
            channel_slug="streamerx",
            chatroom_id="123456",
            pusher_app_key="kick_app_key_demo",
        )

    def test_init_default(self) -> None:
        client = KickChatClient(self._config())
        assert client.is_connected is False
        assert client.PLATFORM == "kick"
        # Pusher event id 검증
        assert client.EVENT_SUBSCRIBE == "pusher:subscribe"
        assert "ChatMessageEvent" in client.EVENT_CHAT

    def test_graceful_skeleton(self) -> None:
        client = KickChatClient(self._config())
        assert asyncio.run(client.connect()) is False
        msgs = asyncio.run(client.receive_loop(max_iterations=1))
        assert msgs == []
        asyncio.run(client.disconnect())
        assert client.is_connected is False

    def test_dataclass_validation(self) -> None:
        with pytest.raises(ValueError, match="channel_slug 빈 문자열 불가"):
            KickChatConfig(
                channel_slug="",
                chatroom_id="1",
                pusher_app_key="k",
            )
        with pytest.raises(ValueError, match="chatroom_id 빈 문자열 불가"):
            KickChatConfig(
                channel_slug="s",
                chatroom_id="",
                pusher_app_key="k",
            )
        with pytest.raises(ValueError, match="pusher_app_key 빈 문자열 불가"):
            KickChatConfig(
                channel_slug="s",
                chatroom_id="1",
                pusher_app_key="",
            )


# ─── ChatMessage 공통 dataclass ───────────────────────────────────────────


class TestChatMessageDataclass:
    """``ChatMessage`` 공통 dataclass 검증 (보조 — 12 test 외)."""

    def test_basic_construction(self) -> None:
        msg = ChatMessage(
            platform="twitch",
            channel_id="streamer",
            user="viewer123",
            message="안녕하세요",
            timestamp=1700000000.0,
        )
        assert msg.platform == "twitch"
        assert msg.user == "viewer123"

    def test_frozen(self) -> None:
        msg = ChatMessage(
            platform="kick",
            channel_id="c",
            user="u",
            message="m",
            timestamp=1.0,
        )
        with pytest.raises((AttributeError, Exception)):
            msg.user = "other"  # type: ignore[misc]

    def test_empty_platform_rejected(self) -> None:
        with pytest.raises(ValueError, match="platform 빈 문자열 불가"):
            ChatMessage(
                platform="",
                channel_id="c",
                user="u",
                message="m",
                timestamp=1.0,
            )

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timestamp 음수 불가"):
            ChatMessage(
                platform="p",
                channel_id="c",
                user="u",
                message="m",
                timestamp=-1.0,
            )
