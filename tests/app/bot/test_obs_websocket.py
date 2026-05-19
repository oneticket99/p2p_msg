# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.obs_websocket_client`` + StreamingHelperDispatcher 단위 테스트.

ObsConnectionConfig validation + ObsSceneInfo + ObsWebSocketClient graceful
False / [] + build_default_client env factory + StreamingHelperDispatcher
4 platform callback chain + trigger_alert dispatch.
"""

from __future__ import annotations

import asyncio
import os
from typing import List, Tuple
from unittest.mock import patch

import pytest

from app.bot.obs_websocket_client import (
    ObsConnectionConfig,
    ObsSceneInfo,
    ObsWebSocketClient,
    build_default_client,
)
from app.bot.streaming_helper import (
    StreamingHelperDispatcher,
    StreamingPlatform,
)


class TestObsConnectionConfig:
    """``ObsConnectionConfig`` dataclass 검증."""

    def test_default(self) -> None:
        cfg = ObsConnectionConfig()
        assert cfg.host == "localhost"
        assert cfg.port == 4455
        assert cfg.password == ""
        assert cfg.timeout_seconds == 5.0

    def test_empty_host_rejected(self) -> None:
        with pytest.raises(ValueError, match="host 빈 문자열 불가"):
            ObsConnectionConfig(host="")

    def test_oversized_host_rejected(self) -> None:
        with pytest.raises(ValueError, match="host 길이 초과"):
            ObsConnectionConfig(host="x" * 300)

    def test_invalid_port_low(self) -> None:
        with pytest.raises(ValueError, match="port 범위 외"):
            ObsConnectionConfig(port=0)

    def test_invalid_port_high(self) -> None:
        with pytest.raises(ValueError, match="port 범위 외"):
            ObsConnectionConfig(port=70000)

    def test_invalid_timeout(self) -> None:
        with pytest.raises(ValueError, match="timeout_seconds 양수 의무"):
            ObsConnectionConfig(timeout_seconds=0)


class TestObsSceneInfo:
    """``ObsSceneInfo`` frozen dataclass 검증."""

    def test_basic_construction(self) -> None:
        info = ObsSceneInfo(name="Main", index=0, is_program=True)
        assert info.name == "Main"
        assert info.index == 0
        assert info.is_program is True

    def test_frozen(self) -> None:
        info = ObsSceneInfo(name="A", index=1, is_program=False)
        with pytest.raises((AttributeError, Exception)):
            info.name = "B"  # type: ignore[misc]


class TestObsClientConnectGraceful:
    """``ObsWebSocketClient`` skeleton graceful False / [] 검증."""

    def test_default_state(self) -> None:
        client = ObsWebSocketClient()
        assert client.is_connected is False
        assert client.config.host == "localhost"

    def test_connect_returns_false_skeleton(self) -> None:
        client = ObsWebSocketClient()
        result = asyncio.run(client.connect())
        assert result is False

    def test_get_scene_list_empty_when_disconnected(self) -> None:
        client = ObsWebSocketClient()
        scenes = asyncio.run(client.get_scene_list())
        assert scenes == []

    def test_set_current_scene_false_when_disconnected(self) -> None:
        client = ObsWebSocketClient()
        result = asyncio.run(client.set_current_scene("Main"))
        assert result is False

    def test_set_current_scene_empty_name_rejected(self) -> None:
        client = ObsWebSocketClient()
        with pytest.raises(ValueError, match="scene_name 빈 문자열 불가"):
            asyncio.run(client.set_current_scene(""))

    def test_trigger_alert_false_when_disconnected(self) -> None:
        client = ObsWebSocketClient()
        result = asyncio.run(client.trigger_alert("test", {"k": 1}))
        assert result is False

    def test_trigger_alert_empty_id_rejected(self) -> None:
        client = ObsWebSocketClient()
        with pytest.raises(ValueError, match="alert_id 빈 문자열 불가"):
            asyncio.run(client.trigger_alert("", {}))

    def test_disconnect_safe_when_never_connected(self) -> None:
        client = ObsWebSocketClient()
        # disconnect 의 multiple call 안전성
        asyncio.run(client.disconnect())
        assert client.is_connected is False


class TestEnvFactory:
    """``build_default_client`` env 기반 factory 검증."""

    def test_default_no_env(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            for key in ("OBS_HOST", "OBS_PORT", "OBS_PASSWORD"):
                os.environ.pop(key, None)
            client = build_default_client()
            assert client.config.host == "localhost"
            assert client.config.port == 4455
            assert client.config.password == ""

    def test_env_overrides(self) -> None:
        env = {
            "OBS_HOST": "192.168.1.100",
            "OBS_PORT": "5555",
            "OBS_PASSWORD": "secret123",
        }
        with patch.dict(os.environ, env, clear=False):
            client = build_default_client()
            assert client.config.host == "192.168.1.100"
            assert client.config.port == 5555
            assert client.config.password == "secret123"

    def test_invalid_port_fallback_to_default(self) -> None:
        env = {"OBS_PORT": "not_a_number"}
        with patch.dict(os.environ, env, clear=False):
            client = build_default_client()
            assert client.config.port == 4455


class TestStreamingHelperDispatch:
    """``StreamingHelperDispatcher`` 4 platform callback → trigger_alert."""

    class _MockObsClient(ObsWebSocketClient):
        """trigger_alert 호출 기록 mock."""

        def __init__(self) -> None:
            super().__init__()
            self.calls: List[Tuple[str, dict]] = []

        async def trigger_alert(  # type: ignore[override]
            self,
            alert_id: str,
            payload: dict,
        ) -> bool:
            self.calls.append((alert_id, dict(payload)))
            return True

    def test_youtube_dispatch(self) -> None:
        mock = self._MockObsClient()
        d = StreamingHelperDispatcher(obs_client=mock)
        result = asyncio.run(
            d.dispatch(StreamingPlatform.YOUTUBE, {"viewer": "a", "msg": "hi"})
        )
        assert result is True
        assert mock.calls[0][0] == "youtube_chat"
        assert mock.calls[0][1]["viewer"] == "a"

    def test_twitch_dispatch(self) -> None:
        mock = self._MockObsClient()
        d = StreamingHelperDispatcher(obs_client=mock)
        result = asyncio.run(
            d.dispatch(StreamingPlatform.TWITCH, {"viewer": "b", "bits": 100})
        )
        assert result is True
        assert mock.calls[0][0] == "twitch_chat"

    def test_chzzk_dispatch(self) -> None:
        mock = self._MockObsClient()
        d = StreamingHelperDispatcher(obs_client=mock)
        result = asyncio.run(
            d.dispatch(StreamingPlatform.CHZZK, {"viewer": "c"})
        )
        assert result is True
        assert mock.calls[0][0] == "chzzk_chat"

    def test_kick_dispatch(self) -> None:
        mock = self._MockObsClient()
        d = StreamingHelperDispatcher(obs_client=mock)
        result = asyncio.run(
            d.dispatch(StreamingPlatform.KICK, {"viewer": "d"})
        )
        assert result is True
        assert mock.calls[0][0] == "kick_chat"

    def test_obs_local_dispatch(self) -> None:
        mock = self._MockObsClient()
        d = StreamingHelperDispatcher(obs_client=mock)
        result = asyncio.run(
            d.dispatch(StreamingPlatform.OBS_LOCAL, {"event": "local"})
        )
        assert result is True
        assert mock.calls[0][0] == "obs_local"

    def test_register_custom_handler_override(self) -> None:
        mock = self._MockObsClient()
        d = StreamingHelperDispatcher(obs_client=mock)
        invoked: List[dict] = []

        async def custom(payload: dict) -> bool:
            invoked.append(payload)
            return True

        d.register_handler(StreamingPlatform.YOUTUBE, custom)
        result = asyncio.run(
            d.dispatch(StreamingPlatform.YOUTUBE, {"viewer": "x"})
        )
        assert result is True
        assert len(invoked) == 1
        # default handler 미호출
        assert mock.calls == []
