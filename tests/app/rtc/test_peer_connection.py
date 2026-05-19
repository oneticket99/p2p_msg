# SPDX-License-Identifier: GPL-3.0-or-later
"""PeerConnectionWrapper + PeerConnectionConfig 검증 — cycle 167 신설.

5 case:
- aiortc 부재 시 RuntimeError raise
- config default 값 검증
- is_aiortc_available helper
- config custom STUN/TURN
- send 실패 (connected False) 시 False 반환
"""

from __future__ import annotations

import pytest

from app.rtc.peer_connection import (
    PeerConnectionConfig,
    PeerConnectionWrapper,
    is_aiortc_available,
)


class TestPeerConnectionConfig:
    """config default + custom 검증 — 2 case."""

    def test_default_config(self) -> None:
        cfg = PeerConnectionConfig()
        assert cfg.stun_urls == ("stun:stun.l.google.com:19302",)
        assert cfg.turn_url is None
        assert cfg.data_channel_label == "tootalk"
        assert cfg.ordered is True

    def test_custom_config(self) -> None:
        cfg = PeerConnectionConfig(
            stun_urls=("stun:example.com:3478",),
            turn_url="turn:turn.example.com:5349",
            turn_username="user",
            turn_credential="pass",
            data_channel_label="custom",
            ordered=False,
        )
        assert cfg.turn_url == "turn:turn.example.com:5349"
        assert cfg.data_channel_label == "custom"
        assert cfg.ordered is False


class TestAiortcAvailability:
    """is_aiortc_available helper — 1 case."""

    def test_helper_returns_bool(self) -> None:
        assert isinstance(is_aiortc_available(), bool)


class TestPeerConnectionWrapper:
    """wrapper instantiation graceful — 2 case."""

    def test_aiortc_absent_raises(self) -> None:
        """aiortc 부재 시 RuntimeError + UI 차단 부재 chain."""
        from app.rtc import peer_connection as pc_mod
        if pc_mod._AIORTC_AVAILABLE:
            pytest.skip("aiortc 설치됨 — skip")
        with pytest.raises(RuntimeError, match="aiortc 미설치"):
            PeerConnectionWrapper(peer_id="test")

    def test_send_disconnected_returns_false(self) -> None:
        """connected False 시 send → False."""
        from app.rtc import peer_connection as pc_mod
        if not pc_mod._AIORTC_AVAILABLE:
            pytest.skip("aiortc 미설치 — skip")
        wrapper = PeerConnectionWrapper(peer_id="test")
        # connected attribute default = False (handshake 부재)
        assert wrapper.connected is False
        assert wrapper.send("hi") is False
