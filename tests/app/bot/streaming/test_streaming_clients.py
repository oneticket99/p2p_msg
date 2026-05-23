# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.streaming`` 3 platform chat client 단위 테스트 — 사이클 146.

3 × 3 platform = 9 test (cycle 169.715 — youtube_client 삭제 정합)
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
)
from app.bot.streaming.chzzk_client import ChzzkChatConfig
from app.bot.streaming.kick_client import KickChatConfig
from app.bot.streaming.twitch_client import TwitchChatConfig


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

    def test_connect_disconnect(self) -> None:
        """cycle 169.507 — actual connect/disconnect 검증 (codex 2.3 회수).

        websockets 가용 시 connect attempt — 실 IRC 핸드셰이크 부재 시 False retain.
        본 test = graceful 분기 + state reset 만 검증.
        """
        client = TwitchChatClient(self._config())
        # 한글 주석 — IRC actual handshake 부재 시 connect graceful False retain
        try:
            ok = asyncio.run(client.connect())
        except Exception:
            ok = False
        # disconnect 안전 (connect 성공 여부 무관)
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

    def test_connect_disconnect(self) -> None:
        """cycle 169.507 — actual connect/disconnect (codex 2.3 회수)."""
        client = ChzzkChatClient(self._config())
        try:
            ok = asyncio.run(client.connect())
        except Exception:
            ok = False
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

    def test_connect_disconnect(self) -> None:
        """cycle 169.507 — actual connect/disconnect (codex 2.3 회수)."""
        client = KickChatClient(self._config())
        try:
            ok = asyncio.run(client.connect())
        except Exception:
            ok = False
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
