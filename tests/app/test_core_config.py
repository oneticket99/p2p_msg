# SPDX-License-Identifier: GPL-3.0-or-later
"""core/config + helper unit — cycle 169.740 신설."""

from __future__ import annotations

import pytest


class TestConfigProperties:
    def test_signaling_url(self) -> None:
        from app.core.config import Config

        c = Config(
            signal_host="1.2.3.4", signal_port=8765, signal_scheme="ws",
            stun_url="stun:x", turn_url="", turn_username="", turn_credential="",
            user_nickname="user", log_level="INFO",
            db_host="h", db_port=3306, db_user="u", db_pass="p", db_name="n",
            media_cache_dir="/tmp", sound_enabled=True, sound_volume=0.7,
            sound_signature_path="s.wav",
        )
        assert c.signaling_url == "ws://1.2.3.4:8765/ws"

    def test_db_dsn(self) -> None:
        from app.core.config import Config

        c = Config(
            signal_host="h", signal_port=1, signal_scheme="ws",
            stun_url="s", turn_url="", turn_username="", turn_credential="",
            user_nickname="u", log_level="INFO",
            db_host="dbhost", db_port=3306, db_user="root", db_pass="pw",
            db_name="tootalk", media_cache_dir="/tmp",
            sound_enabled=True, sound_volume=0.5, sound_signature_path="x.wav",
        )
        assert c.db_dsn == "mysql://root:pw@dbhost:3306/tootalk"


class TestEnvHelpers:
    def test_env_str_default(self, monkeypatch) -> None:
        from app.core.config import _env_str

        monkeypatch.delenv("TEST_K", raising=False)
        assert _env_str("TEST_K", "fallback") == "fallback"

    def test_env_str_empty_falls_back(self, monkeypatch) -> None:
        # 한글 주석 — 빈 문자열 → default
        from app.core.config import _env_str

        monkeypatch.setenv("TEST_K", "")
        assert _env_str("TEST_K", "fallback") == "fallback"

    def test_env_str_value(self, monkeypatch) -> None:
        from app.core.config import _env_str

        monkeypatch.setenv("TEST_K", "actual")
        assert _env_str("TEST_K", "fallback") == "actual"

    def test_env_int_default(self, monkeypatch) -> None:
        from app.core.config import _env_int

        monkeypatch.delenv("TEST_N", raising=False)
        assert _env_int("TEST_N", 42) == 42

    def test_env_int_invalid_falls_back(self, monkeypatch) -> None:
        from app.core.config import _env_int

        monkeypatch.setenv("TEST_N", "notanumber")
        assert _env_int("TEST_N", 99) == 99

    def test_env_bool_true_variants(self, monkeypatch) -> None:
        from app.core.config import _env_bool

        for v in ("1", "true", "True", "yes"):
            monkeypatch.setenv("TEST_B", v)
            assert _env_bool("TEST_B", False) is True

    def test_env_bool_false(self, monkeypatch) -> None:
        from app.core.config import _env_bool

        monkeypatch.setenv("TEST_B", "0")
        assert _env_bool("TEST_B", True) is False

    def test_env_float_clamp_high(self, monkeypatch) -> None:
        from app.core.config import _env_float_clamp

        monkeypatch.setenv("TEST_F", "2.5")
        assert _env_float_clamp("TEST_F", 0.5, 0.0, 1.0) == 1.0

    def test_env_float_clamp_low(self, monkeypatch) -> None:
        from app.core.config import _env_float_clamp

        monkeypatch.setenv("TEST_F", "-1.0")
        assert _env_float_clamp("TEST_F", 0.5, 0.0, 1.0) == 0.0


class TestNormalizeScheme:
    def test_ws_retain(self) -> None:
        from app.core.config import _normalize_scheme

        assert _normalize_scheme("ws") == "ws"

    def test_wss_retain(self) -> None:
        from app.core.config import _normalize_scheme

        assert _normalize_scheme("wss") == "wss"

    def test_invalid_falls_back_ws(self) -> None:
        # 한글 주석 — 부재 scheme → ws fallback
        from app.core.config import _normalize_scheme

        assert _normalize_scheme("http") == "ws"


class TestNormalizeLogLevel:
    def test_valid_upper(self) -> None:
        from app.core.config import _normalize_log_level

        assert _normalize_log_level("debug") == "DEBUG"

    def test_invalid_falls_back_info(self) -> None:
        from app.core.config import _normalize_log_level

        assert _normalize_log_level("bogus") == "INFO"


class TestLoadConfig:
    def test_returns_config(self, monkeypatch) -> None:
        from app.core.config import Config, load_config

        c = load_config()
        assert isinstance(c, Config)
        assert c.signal_scheme in ("ws", "wss")
        assert c.log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
