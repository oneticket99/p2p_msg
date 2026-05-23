# SPDX-License-Identifier: GPL-3.0-or-later
"""bot obs_websocket_client unit — cycle 169.723 신설."""

from __future__ import annotations

import pytest


class TestObsConnectionConfig:
    def test_defaults(self) -> None:
        from app.bot.obs_websocket_client import ObsConnectionConfig

        c = ObsConnectionConfig()
        assert c.host == "localhost"
        assert c.port == 4455
        assert c.password == ""
        assert c.timeout_seconds == 5.0

    def test_empty_host_raises(self) -> None:
        from app.bot.obs_websocket_client import ObsConnectionConfig

        with pytest.raises(ValueError, match="host"):
            ObsConnectionConfig(host="")

    def test_port_out_of_range_raises(self) -> None:
        from app.bot.obs_websocket_client import ObsConnectionConfig

        with pytest.raises(ValueError, match="port"):
            ObsConnectionConfig(port=0)
        with pytest.raises(ValueError, match="port"):
            ObsConnectionConfig(port=70000)

    def test_zero_timeout_raises(self) -> None:
        from app.bot.obs_websocket_client import ObsConnectionConfig

        with pytest.raises(ValueError, match="timeout_seconds"):
            ObsConnectionConfig(timeout_seconds=0)


class TestObsSceneInfo:
    def test_construct(self) -> None:
        from app.bot.obs_websocket_client import ObsSceneInfo

        s = ObsSceneInfo(name="Scene 1", index=0, is_program=True)
        assert s.name == "Scene 1"
        assert s.index == 0
        assert s.is_program is True


class TestComputeAuthString:
    def test_deterministic(self) -> None:
        from app.bot.obs_websocket_client import _compute_auth_string

        a1 = _compute_auth_string("password", "salt123", "challenge456")
        a2 = _compute_auth_string("password", "salt123", "challenge456")
        assert a1 == a2

    def test_different_password_different_auth(self) -> None:
        from app.bot.obs_websocket_client import _compute_auth_string

        a1 = _compute_auth_string("password1", "salt", "challenge")
        a2 = _compute_auth_string("password2", "salt", "challenge")
        assert a1 != a2

    def test_base64_encoded(self) -> None:
        # 한글 주석 — base64 alphabet 만 (A-Z, a-z, 0-9, +, /, =)
        from app.bot.obs_websocket_client import _compute_auth_string

        result = _compute_auth_string("pw", "salt", "ch")
        b64_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
        assert all(c in b64_chars for c in result)


class TestObsWebSocketClient:
    def test_init_default_config(self) -> None:
        from app.bot.obs_websocket_client import (
            ObsConnectionConfig, ObsWebSocketClient,
        )

        c = ObsWebSocketClient(ObsConnectionConfig())
        # 한글 주석 — default state — disconnected
        assert c.is_connected is False


class TestBuildDefaultClient:
    def test_returns_client(self) -> None:
        from app.bot.obs_websocket_client import (
            ObsWebSocketClient, build_default_client,
        )

        c = build_default_client()
        assert isinstance(c, ObsWebSocketClient)
