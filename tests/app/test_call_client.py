# SPDX-License-Identifier: GPL-3.0-or-later
"""CallClient unit test — cycle 169.678 omit 제거 path.

aiortc dependency 부재 graceful + env override + init field 정합.
"""

from __future__ import annotations

import pytest


class TestCallClientInit:
    def test_default_stun_url(self, monkeypatch) -> None:
        monkeypatch.delenv("TOOTALK_STUN_URL", raising=False)
        monkeypatch.delenv("TOOTALK_TURN_URL", raising=False)
        from app.net.call_client import CallClient

        c = CallClient()
        assert c._stun_url == "stun:stun.l.google.com:19302"
        assert c._turn_url == ""
        assert c._pc is None
        assert c._remote_track is None
        assert c._video_enabled is False

    def test_env_override_stun(self, monkeypatch) -> None:
        # 한글 주석 — env override STUN URL
        monkeypatch.setenv("TOOTALK_STUN_URL", "stun:custom:3478")
        from app.net.call_client import CallClient

        c = CallClient()
        assert c._stun_url == "stun:custom:3478"

    def test_env_override_turn(self, monkeypatch) -> None:
        monkeypatch.setenv("TOOTALK_TURN_URL", "turn:demo.local:3478")
        monkeypatch.setenv("TOOTALK_TURN_USERNAME", "user")
        monkeypatch.setenv("TOOTALK_TURN_CREDENTIAL", "pw")
        from app.net.call_client import CallClient

        c = CallClient()
        assert c._turn_url == "turn:demo.local:3478"
        assert c._turn_username == "user"
        assert c._turn_credential == "pw"

    def test_explicit_peer_id_stored(self) -> None:
        from app.net.call_client import CallClient

        c = CallClient(peer_id="bob")
        assert c._peer_id == "bob"

    def test_on_state_change_callback_stored(self) -> None:
        from app.net.call_client import CallClient

        # 한글 주석 — bound method 동일성 변동 회피 — 별 함수 객체 사용
        def cb(state: str) -> None:
            pass

        c = CallClient(on_state_change=cb)
        assert c._on_state_change is cb


class TestBuildIceServers:
    def test_no_turn_only_stun(self, monkeypatch) -> None:
        monkeypatch.delenv("TOOTALK_TURN_URL", raising=False)
        from app.net.call_client import AIORTC_AVAILABLE, CallClient

        c = CallClient()
        servers = c._build_ice_servers()
        if not AIORTC_AVAILABLE:
            assert servers == []
        else:
            assert len(servers) == 1

    def test_with_turn_two_servers(self, monkeypatch) -> None:
        monkeypatch.setenv("TOOTALK_TURN_URL", "turn:demo:3478")
        monkeypatch.setenv("TOOTALK_TURN_USERNAME", "u")
        monkeypatch.setenv("TOOTALK_TURN_CREDENTIAL", "p")
        from app.net.call_client import AIORTC_AVAILABLE, CallClient

        c = CallClient()
        servers = c._build_ice_servers()
        if not AIORTC_AVAILABLE:
            assert servers == []
        else:
            assert len(servers) == 2


class TestMediaPlayerGuards:
    def test_unknown_system_returns_none(self) -> None:
        from app.net.call_client import CallClient

        c = CallClient()
        # 한글 주석 — Windows fallback path = None (audio dshow 부재 graceful)
        result = c._build_media_player("Windows", video=False)
        assert result is None
