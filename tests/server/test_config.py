# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.config`` 의 단위 테스트.

env load chain + 7 영역 from_env + production validate + ConfigError.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.config import (
    BotConfig,
    Config,
    ConfigError,
    DBConfig,
    FCMConfig,
    SMTPConfig,
    SignalingConfig,
    TLSConfig,
    load_env_files,
)


def _clean_env(monkeypatch: pytest.MonkeyPatch, keys: list[str]) -> None:
    for k in keys:
        monkeypatch.delenv(k, raising=False)


class TestParseHelpers:
    """_str_env / _int_env / _bool_env 의 helper 검증 (Config.from_env 경로)."""

    def test_default_env_local(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ENV", raising=False)
        # 한글 주석: 빈 cwd 가정 — .env 의 부재 시 default = local
        cfg = Config(env="local")
        assert cfg.env == "local"

    def test_int_env_invalid_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DB_PORT", "not-a-number")
        cfg = DBConfig.from_env()
        # 한글 주석: 의 invalid int → default 3306 fallback
        assert cfg.port == 3306

    def test_bool_env_truthy_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for v in ("1", "true", "TRUE", "yes", "on"):
            monkeypatch.setenv("BOT_ENABLED", v)
            assert BotConfig.from_env().enabled is True

    def test_bool_env_falsy_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for v in ("0", "false", "no", "off", ""):
            monkeypatch.setenv("BOT_ENABLED", v)
            assert BotConfig.from_env().enabled is False


class TestDBConfig:
    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clean_env(monkeypatch, ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD",
                                  "DB_NAME", "DB_POOL_SIZE",
                                  "DB_POOL_RECYCLE_SECONDS"])
        cfg = DBConfig.from_env()
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 3306
        assert cfg.user == "tootalk"
        assert cfg.password == ""
        assert cfg.pool_size == 10
        assert cfg.pool_recycle_seconds == 3600

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DB_HOST", "db.prod.internal")
        monkeypatch.setenv("DB_PORT", "13306")
        monkeypatch.setenv("DB_PASSWORD", "secret123")
        cfg = DBConfig.from_env()
        assert cfg.host == "db.prod.internal"
        assert cfg.port == 13306
        assert cfg.password == "secret123"


class TestSMTPConfig:
    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clean_env(monkeypatch, ["SMTP_HOST", "SMTP_PORT", "SMTP_USER",
                                  "SMTP_PASSWORD", "SMTP_FROM_ADDRESS",
                                  "SMTP_DOMAIN", "DKIM_SELECTOR"])
        cfg = SMTPConfig.from_env()
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 1587
        assert cfg.from_address == "noreply@tootalk.demo"

    def test_dkim_selector_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DKIM_SELECTOR", "ts2026")
        cfg = SMTPConfig.from_env()
        assert cfg.dkim_selector == "ts2026"


class TestSignalingConfig:
    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clean_env(monkeypatch, ["SIGNAL_SERVER_HOST", "SIGNAL_SERVER_WS_PORT",
                                  "SIGNAL_SERVER_WS_SCHEME",
                                  "SIGNAL_SERVER_MODE"])
        cfg = SignalingConfig.from_env()
        assert cfg.host == "0.0.0.0"
        assert cfg.ws_port == 8765
        assert cfg.mode == "ws"


class TestBotConfig:
    def test_defaults_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clean_env(monkeypatch, ["BOT_ENABLED", "BOT_RATE_PER_MINUTE",
                                  "ANTHROPIC_API_KEY", "OPENAI_API_KEY"])
        cfg = BotConfig.from_env()
        assert cfg.enabled is False
        assert cfg.rate_per_minute == 20

    def test_enabled_with_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BOT_ENABLED", "1")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("BOT_RATE_PER_MINUTE", "50")
        cfg = BotConfig.from_env()
        assert cfg.enabled is True
        assert cfg.rate_per_minute == 50
        assert cfg.anthropic_api_key == "sk-ant-test"


class TestFCMConfig:
    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _clean_env(monkeypatch, ["FCM_PROJECT_ID", "FCM_CREDENTIAL_PATH"])
        cfg = FCMConfig.from_env()
        assert cfg.project_id == ""
        assert cfg.credential_path == ""


class TestTLSConfig:
    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ACME_EMAIL", "admin@example.com")
        monkeypatch.setenv("TLS_PRIMARY_DOMAIN", "example.com")
        cfg = TLSConfig.from_env()
        assert cfg.acme_email == "admin@example.com"
        assert cfg.primary_domain == "example.com"


class TestConfigFromEnv:
    """통합 Config.from_env + load chain 검증."""

    def test_local_defaults(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.delenv("ENV", raising=False)
        # 한글 주석: tmp_path 의 .env 부재 → ENV = "local" default
        cfg = Config.from_env(project_root=tmp_path)
        assert cfg.env == "local"
        assert cfg.log_level == "INFO"
        assert cfg.timezone == "Asia/Seoul"
        assert isinstance(cfg.db, DBConfig)
        assert isinstance(cfg.smtp, SMTPConfig)

    def test_load_env_files_picks_specific_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # 한글 주석: .env 의 ENV=production + .env.production 의 DB_HOST chain
        # load_dotenv 는 monkeypatch 우회 의 직접 os.environ 변경 — test 후
        # 명시적 cleanup 의무 (production validate 의 cross-test 오염 차단).
        import os

        saved = {k: os.environ.get(k) for k in ("ENV", "DB_HOST")}
        try:
            (tmp_path / ".env").write_text("ENV=production\nDB_HOST=base-host\n")
            (tmp_path / ".env.production").write_text("DB_HOST=prod-host\n")
            monkeypatch.delenv("ENV", raising=False)
            monkeypatch.delenv("DB_HOST", raising=False)
            env_name = load_env_files(tmp_path)
            assert env_name == "production"
            # override=False 의무 — base 의 DB_HOST=base-host 유지
            assert os.environ.get("DB_HOST") == "base-host"
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class TestConfigValidate:
    """production 환경 의 의무 키 누락 ConfigError 검증."""

    def test_local_passes_with_empty(self) -> None:
        # 한글 주석: local 환경 = validate 즉시 return (production 외)
        cfg = Config(env="local", db=DBConfig(password=""))
        cfg.validate()  # no raise

    def test_production_missing_db_password_raises(self) -> None:
        cfg = Config(
            env="production",
            db=DBConfig(password=""),
            tls=TLSConfig(acme_email="a@b.com", primary_domain="b.com"),
        )
        with pytest.raises(ConfigError, match="DB_PASSWORD"):
            cfg.validate()

    def test_production_missing_tls_raises(self) -> None:
        cfg = Config(
            env="production",
            db=DBConfig(password="set"),
            tls=TLSConfig(),
        )
        with pytest.raises(ConfigError, match="ACME_EMAIL"):
            cfg.validate()

    def test_production_bot_enabled_without_keys_raises(self) -> None:
        cfg = Config(
            env="production",
            db=DBConfig(password="set"),
            bot=BotConfig(enabled=True),
            tls=TLSConfig(acme_email="a@b.com", primary_domain="b.com"),
        )
        with pytest.raises(ConfigError, match="API_KEY"):
            cfg.validate()

    def test_production_all_set_passes(self) -> None:
        cfg = Config(
            env="production",
            db=DBConfig(password="dbpw"),
            bot=BotConfig(enabled=True, anthropic_api_key="sk-ant"),
            tls=TLSConfig(acme_email="a@b.com", primary_domain="b.com"),
        )
        cfg.validate()  # no raise
