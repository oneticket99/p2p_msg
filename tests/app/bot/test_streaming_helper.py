# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.streaming_helper`` 단위 테스트.

StreamingCommand validation + StreamingBotConfig + default_streaming_commands +
StreamingHelperBot apply_command + cooldown + find_command + add/remove +
platform callback placeholder NotImplementedError.
"""

from __future__ import annotations

import pytest

from app.bot.streaming_helper import (
    StreamingBotConfig,
    StreamingCommand,
    StreamingHelperBot,
    StreamingPlatform,
    default_streaming_commands,
    fetch_platform_callback,
)


def _config(
    *,
    platform: StreamingPlatform = StreamingPlatform.TWITCH,
) -> StreamingBotConfig:
    return StreamingBotConfig(
        bot_user_id=2_000_001,
        display_name="TooTalk 방송 도우미",
        platform=platform,
    )


class TestStreamingCommandValidation:
    """``StreamingCommand`` dataclass 검증."""

    def test_valid_construction(self) -> None:
        cmd = StreamingCommand(trigger="!hello", response="hi")
        assert cmd.cooldown_seconds == 5
        assert cmd.enabled is True

    def test_empty_trigger_rejected(self) -> None:
        with pytest.raises(ValueError, match="trigger 빈 문자열 불가"):
            StreamingCommand(trigger="", response="r")

    def test_trigger_without_bang_rejected(self) -> None:
        with pytest.raises(ValueError, match="trigger 의 '!' 시작 의무"):
            StreamingCommand(trigger="hello", response="r")

    def test_oversized_trigger_rejected(self) -> None:
        big = "!" + "x" * 32
        with pytest.raises(ValueError, match="trigger 길이 초과"):
            StreamingCommand(trigger=big, response="r")

    def test_empty_response_rejected(self) -> None:
        with pytest.raises(ValueError, match="response 빈 문자열 불가"):
            StreamingCommand(trigger="!hi", response="")

    def test_oversized_response_rejected(self) -> None:
        big = "x" * 501
        with pytest.raises(ValueError, match="response 길이 초과"):
            StreamingCommand(trigger="!hi", response=big)

    def test_negative_cooldown_rejected(self) -> None:
        with pytest.raises(ValueError, match="cooldown_seconds 음수 불가"):
            StreamingCommand(trigger="!hi", response="r", cooldown_seconds=-1)


class TestStreamingBotConfigValidation:
    """``StreamingBotConfig`` dataclass 검증."""

    def test_valid_default(self) -> None:
        config = _config()
        assert config.bot_user_id >= 2_000_000
        assert config.platform == StreamingPlatform.TWITCH

    def test_low_bot_user_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="bot_user_id"):
            StreamingBotConfig(
                bot_user_id=1_999_999,
                display_name="X",
                platform=StreamingPlatform.TWITCH,
            )

    def test_empty_display_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="display_name 빈 문자열 불가"):
            StreamingBotConfig(
                bot_user_id=2_000_001,
                display_name="",
                platform=StreamingPlatform.TWITCH,
            )


class TestDefaultStreamingCommands:
    """``default_streaming_commands`` 5 명령 검증."""

    def test_returns_5_commands(self) -> None:
        cmds = default_streaming_commands()
        assert len(cmds) == 5

    def test_trigger_list(self) -> None:
        cmds = default_streaming_commands()
        triggers = [c.trigger for c in cmds]
        assert "!hello" in triggers
        assert "!uptime" in triggers
        assert "!donate" in triggers
        assert "!command" in triggers
        assert "!so" in triggers

    def test_all_enabled(self) -> None:
        cmds = default_streaming_commands()
        assert all(c.enabled for c in cmds)


class TestFindCommand:
    """``StreamingHelperBot.find_command`` 검증."""

    def test_empty_message(self) -> None:
        bot = StreamingHelperBot(_config())
        assert bot.find_command("") is None

    def test_no_match(self) -> None:
        bot = StreamingHelperBot(_config())
        assert bot.find_command("그냥 채팅 메시지") is None

    def test_match_hello(self) -> None:
        bot = StreamingHelperBot(_config())
        cmd = bot.find_command("!hello")
        assert cmd is not None
        assert cmd.trigger == "!hello"

    def test_match_with_args(self) -> None:
        bot = StreamingHelperBot(_config())
        cmd = bot.find_command("!so otherstreamer")
        assert cmd is not None
        assert cmd.trigger == "!so"

    def test_disabled_not_matched(self) -> None:
        custom = [
            StreamingCommand(trigger="!secret", response="r", enabled=False),
        ]
        bot = StreamingHelperBot(_config(), commands=custom)
        assert bot.find_command("!secret") is None


class TestApplyCommand:
    """``apply_command`` reply + cooldown + placeholder 치환."""

    def test_basic_reply(self) -> None:
        bot = StreamingHelperBot(_config())
        reply = bot.apply_command(
            "!hello",
            viewer_name="alice",
            now_seconds=100.0,
        )
        assert reply is not None
        assert "alice" in reply

    def test_no_match_returns_none(self) -> None:
        bot = StreamingHelperBot(_config())
        reply = bot.apply_command("일반 chat", now_seconds=100.0)
        assert reply is None

    def test_cooldown_blocks_second_call(self) -> None:
        bot = StreamingHelperBot(_config())
        r1 = bot.apply_command("!hello", viewer_name="a", now_seconds=100.0)
        assert r1 is not None
        # 5초 cooldown 안 의 즉시 재호출 = None
        r2 = bot.apply_command("!hello", viewer_name="b", now_seconds=101.0)
        assert r2 is None

    def test_cooldown_releases_after_period(self) -> None:
        bot = StreamingHelperBot(_config())
        bot.apply_command("!hello", viewer_name="a", now_seconds=100.0)
        # 5초 + 1 의 경과 = 재호출 허용
        r2 = bot.apply_command("!hello", viewer_name="b", now_seconds=106.0)
        assert r2 is not None
        assert "b" in r2

    def test_placeholder_substitution(self) -> None:
        bot = StreamingHelperBot(_config())
        reply = bot.apply_command(
            "!donate",
            streamer_name="streamerX",
            now_seconds=100.0,
        )
        assert reply is not None
        assert "streamerX" in reply
        # toonation.com URL 정합
        assert "toonation.com" in reply

    def test_so_target_placeholder(self) -> None:
        bot = StreamingHelperBot(_config())
        reply = bot.apply_command(
            "!so",
            target_name="friend123",
            now_seconds=100.0,
        )
        assert reply is not None
        assert "friend123" in reply


class TestAddRemoveCommand:
    """``add_command`` + ``remove_command`` 검증."""

    def test_add_new_command(self) -> None:
        bot = StreamingHelperBot(_config())
        before = len(bot.commands)
        bot.add_command(StreamingCommand(trigger="!new", response="new!"))
        assert len(bot.commands) == before + 1

    def test_add_duplicate_rejected(self) -> None:
        bot = StreamingHelperBot(_config())
        with pytest.raises(ValueError, match="trigger 중복"):
            bot.add_command(StreamingCommand(trigger="!hello", response="dup"))

    def test_remove_existing(self) -> None:
        bot = StreamingHelperBot(_config())
        before = len(bot.commands)
        assert bot.remove_command("!hello") is True
        assert len(bot.commands) == before - 1

    def test_remove_missing(self) -> None:
        bot = StreamingHelperBot(_config())
        assert bot.remove_command("!notexist") is False


class TestFetchPlatformCallback:
    """``fetch_platform_callback`` URL return 검증 (cycle 169.418 NotImplementedError 폐기 + URL return swap, cycle 169.535 test 갱신)."""

    def test_youtube_returns_livechat_url(self) -> None:
        # 한글 주석 — YouTube Data API v3 liveChatMessages.list endpoint
        url = fetch_platform_callback(StreamingPlatform.YOUTUBE)
        assert "googleapis.com" in url
        assert "youtube/v3/liveChat" in url

    def test_twitch_returns_irc_ws_url(self) -> None:
        # 한글 주석 — Twitch IRC WebSocket endpoint (TMI)
        url = fetch_platform_callback(StreamingPlatform.TWITCH)
        assert url.startswith("wss://")
        assert "twitch.tv" in url

    def test_chzzk_returns_polling_url(self) -> None:
        # 한글 주석 — CHZZK 폴링 endpoint base
        url = fetch_platform_callback(StreamingPlatform.CHZZK)
        assert "chzzk.naver.com" in url

    def test_kick_returns_pusher_ws_url(self) -> None:
        # 한글 주석 — Kick Pusher WebSocket endpoint
        url = fetch_platform_callback(StreamingPlatform.KICK)
        assert url.startswith("wss://")
        assert "pusher.com" in url

    def test_obs_local_returns_ws_url(self) -> None:
        # 한글 주석 — OBS WebSocket v5 default localhost
        url = fetch_platform_callback(StreamingPlatform.OBS_LOCAL)
        assert url.startswith("ws://localhost:4455")
