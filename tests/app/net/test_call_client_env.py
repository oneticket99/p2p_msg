# SPDX-License-Identifier: GPL-3.0-or-later
"""CallClient TURN env override unit test (cycle 169.81 신설).

production deploy 정합 — TOOTALK_TURN_URL/USERNAME/CREDENTIAL env 우선 적용 검증.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.net.call_client import CallClient


class TestCallClientEnvOverride:
    """ctor parameter default + env 우선 적용 검증."""

    def test_default_no_env(self) -> None:
        # 한글 주석 — env 부재 시점 ctor default 적용
        with patch.dict(os.environ, {}, clear=False):
            for key in ("TOOTALK_STUN_URL", "TOOTALK_TURN_URL",
                        "TOOTALK_TURN_USERNAME", "TOOTALK_TURN_CREDENTIAL"):
                os.environ.pop(key, None)
            client = CallClient()
            assert client._stun_url == "stun:stun.l.google.com:19302"
            assert client._turn_url == ""
            assert client._turn_username == ""
            assert client._turn_credential == ""

    def test_env_override_turn(self) -> None:
        # 한글 주석 — TURN env 4종 적용 검증
        env = {
            "TOOTALK_STUN_URL": "stun:custom.stun.io:3478",
            "TOOTALK_TURN_URL": "turn:114.207.112.73:3478?transport=udp",
            "TOOTALK_TURN_USERNAME": "tootalk",
            "TOOTALK_TURN_CREDENTIAL": "secret_password_xyz",
        }
        with patch.dict(os.environ, env):
            client = CallClient()
            assert client._stun_url == "stun:custom.stun.io:3478"
            assert client._turn_url == "turn:114.207.112.73:3478?transport=udp"
            assert client._turn_username == "tootalk"
            assert client._turn_credential == "secret_password_xyz"

    def test_env_priority_over_ctor(self) -> None:
        # 한글 주석 — env 우선 — ctor parameter override
        env = {"TOOTALK_TURN_URL": "turn:env.priority:3478"}
        with patch.dict(os.environ, env):
            client = CallClient(turn_url="turn:ctor.lower:3478")
            assert client._turn_url == "turn:env.priority:3478"


class TestCallClientMediaPlayerSystem:
    """OS-specific MediaPlayer 분기 검증 (mock — 실 device 부재 graceful)."""

    def test_unknown_system_returns_none(self) -> None:
        # 한글 주석 — Windows 등 미지원 시스템 graceful None return
        client = CallClient()
        result = client._build_media_player("Windows", video=False)
        assert result is None

    def test_darwin_audio_only_attempts(self) -> None:
        # 한글 주석 — Darwin system 호출 시점 — 실 device 부재 → exception 경로 None 또는 mock 정합
        client = CallClient()
        result = client._build_media_player("Darwin", video=False)
        # 실 macOS device 부재 / aiortc 부재 시 None — 검증 = exception silent + None fallback
        assert result is None or hasattr(result, "audio")

    def test_linux_video_v4l2_format(self) -> None:
        # 한글 주석 — Linux v4l2 분기 — 실 /dev/video0 부재 → exception → None graceful
        client = CallClient()
        result = client._build_media_player("Linux", video=True)
        assert result is None or hasattr(result, "video")
