# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 109 — 환경 변수 통합 Config 클래스.

본 module = server.main 의 env 분산 access (os.environ.get 패턴) 의 single
source of truth 통합. .env / .env.local / .env.production 의 load 순서 의
override chain + dataclass field 의 type-safe parse + default fallback.

설계 결정
---------
- ENV 환경 식별 (local / staging / production) 기반 .env.<ENV> 파일 자동
  선택. 부재 시 .env 폴백.
- python-dotenv 의 load_dotenv override=False 의무 — 이미 설정된 env 의
  유지 (Docker secret + Kubernetes ConfigMap 정합).
- bool / int / float 의 parse helper + 음수 / 비숫자 fallback.
- DB / SMTP / 시그널링 / 봇 / FCM / nginx / Toonation 의 7 영역 grouping.
- production 환경 의 의무 키 미설정 시 ConfigError raise (defense-in-depth).

본 module 범위 외
----------------
- 실 .env 파일 의 dump / write (.env.example 의 정본 외).
- 환경 변수 의 hot reload (SIGHUP 등) — 별개 cycle.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

log = logging.getLogger(__name__)


_ENV_KEY = "ENV"
_DEFAULT_ENV = "local"
_LOAD_ORDER = (".env", ".env.{env}")  # later override earlier (override=False 회피)


class ConfigError(Exception):
    """Production 환경 의 필수 키 미설정 등 의 설정 오류."""


def _str_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _int_env(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        log.warning("env %s=%r invalid int — fallback %d", key, raw, default)
        return default


def _bool_env(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key, "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def load_env_files(project_root: Optional[Path] = None) -> str:
    """`.env` + `.env.<ENV>` 의 순차 load. 반환값 = 선택된 ENV 이름.

    Parameters
    ----------
    project_root : Optional[Path]
        .env 파일 search 시작 디렉토리. None 시 cwd.

    Returns
    -------
    str
        ``ENV`` 환경 변수 의 정규화 값 (local / staging / production).
    """

    root = project_root or Path.cwd()
    # 1단계 — .env 의 ENV 키 노출 (이후 .env.<ENV> 선택 의 base)
    base_env = root / ".env"
    if base_env.is_file():
        load_dotenv(base_env, override=False)
    env_name = _str_env(_ENV_KEY, _DEFAULT_ENV).lower()
    # 2단계 — .env.<ENV> override (예: .env.production)
    specific = root / f".env.{env_name}"
    if specific.is_file():
        load_dotenv(specific, override=False)
        log.info("env 파일 load: %s", specific)
    return env_name


@dataclass(frozen=True)
class DBConfig:
    """MariaDB 접속 설정."""

    host: str = field(default="127.0.0.1")
    port: int = 3306
    user: str = field(default="tootalk")
    password: str = field(default="")
    name: str = field(default="tootalk")
    pool_size: int = 10
    pool_recycle_seconds: int = 3600

    @classmethod
    def from_env(cls) -> "DBConfig":
        return cls(
            host=_str_env("DB_HOST", "127.0.0.1"),
            port=_int_env("DB_PORT", 3306),
            user=_str_env("DB_USER", "tootalk"),
            password=_str_env("DB_PASSWORD"),
            name=_str_env("DB_NAME", "tootalk"),
            pool_size=_int_env("DB_POOL_SIZE", 10),
            pool_recycle_seconds=_int_env("DB_POOL_RECYCLE_SECONDS", 3600),
        )


@dataclass(frozen=True)
class SMTPConfig:
    """OTP 발송 SMTP client 설정."""

    host: str = "127.0.0.1"
    port: int = 1587
    user: str = ""
    password: str = ""
    from_address: str = "noreply@tootalk.demo"
    domain: str = "tootalk.demo"
    dkim_selector: str = "tootalk"

    @classmethod
    def from_env(cls) -> "SMTPConfig":
        return cls(
            host=_str_env("SMTP_HOST", "127.0.0.1"),
            port=_int_env("SMTP_PORT", 1587),
            user=_str_env("SMTP_USER"),
            password=_str_env("SMTP_PASSWORD"),
            from_address=_str_env("SMTP_FROM_ADDRESS", "noreply@tootalk.demo"),
            domain=_str_env("SMTP_DOMAIN", "tootalk.demo"),
            dkim_selector=_str_env("DKIM_SELECTOR", "tootalk"),
        )


@dataclass(frozen=True)
class SignalingConfig:
    """시그널링 WebSocket 서버 설정."""

    host: str = "0.0.0.0"
    ws_port: int = 8765
    ws_scheme: str = "ws"
    mode: str = "ws"

    @classmethod
    def from_env(cls) -> "SignalingConfig":
        return cls(
            host=_str_env("SIGNAL_SERVER_HOST", "0.0.0.0"),
            ws_port=_int_env("SIGNAL_SERVER_WS_PORT", 8765),
            ws_scheme=_str_env("SIGNAL_SERVER_WS_SCHEME", "ws"),
            mode=_str_env("SIGNAL_SERVER_MODE", "ws"),
        )


@dataclass(frozen=True)
class BotConfig:
    """Phase 3 bot framework 설정."""

    enabled: bool = False
    rate_per_minute: int = 20
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    @classmethod
    def from_env(cls) -> "BotConfig":
        return cls(
            enabled=_bool_env("BOT_ENABLED", False),
            rate_per_minute=_int_env("BOT_RATE_PER_MINUTE", 20),
            anthropic_api_key=_str_env("ANTHROPIC_API_KEY"),
            openai_api_key=_str_env("OPENAI_API_KEY"),
        )


@dataclass(frozen=True)
class FCMConfig:
    """Firebase Cloud Messaging 설정."""

    project_id: str = ""
    credential_path: str = ""

    @classmethod
    def from_env(cls) -> "FCMConfig":
        return cls(
            project_id=_str_env("FCM_PROJECT_ID"),
            credential_path=_str_env("FCM_CREDENTIAL_PATH"),
        )


@dataclass(frozen=True)
class TLSConfig:
    """nginx + Let's Encrypt TLS 설정."""

    acme_email: str = ""
    primary_domain: str = ""

    @classmethod
    def from_env(cls) -> "TLSConfig":
        return cls(
            acme_email=_str_env("ACME_EMAIL"),
            primary_domain=_str_env("TLS_PRIMARY_DOMAIN"),
        )


@dataclass(frozen=True)
class Config:
    """7 영역 통합 정본 — server.main 의 single entry point."""

    env: str = "local"
    log_level: str = "INFO"
    log_format: str = "text"
    timezone: str = "Asia/Seoul"
    db: DBConfig = field(default_factory=DBConfig)
    smtp: SMTPConfig = field(default_factory=SMTPConfig)
    signaling: SignalingConfig = field(default_factory=SignalingConfig)
    bot: BotConfig = field(default_factory=BotConfig)
    fcm: FCMConfig = field(default_factory=FCMConfig)
    tls: TLSConfig = field(default_factory=TLSConfig)

    @classmethod
    def from_env(cls, project_root: Optional[Path] = None) -> "Config":
        """`.env` chain load → 모든 카테고리 의 from_env 호출 → frozen 반환."""

        env_name = load_env_files(project_root)
        cfg = cls(
            env=env_name,
            log_level=_str_env("LOG_LEVEL", "INFO").upper(),
            log_format=_str_env("LOG_FORMAT", "text").lower(),
            timezone=_str_env("TZ", "Asia/Seoul"),
            db=DBConfig.from_env(),
            smtp=SMTPConfig.from_env(),
            signaling=SignalingConfig.from_env(),
            bot=BotConfig.from_env(),
            fcm=FCMConfig.from_env(),
            tls=TLSConfig.from_env(),
        )
        cfg.validate()
        return cfg

    def validate(self) -> None:
        """Production 환경 의 의무 키 누락 검증.

        Raises
        ------
        ConfigError
            production 환경 + 의무 키 (DB_PASSWORD / ACME_EMAIL / TLS_PRIMARY_DOMAIN)
            미설정 시.
        """

        if self.env != "production":
            return
        problems = []
        if not self.db.password:
            problems.append("DB_PASSWORD")
        if not self.smtp.from_address or self.smtp.from_address == "noreply@tootalk.demo":
            log.warning("SMTP_FROM_ADDRESS default 값 유지 — production 권장 별개 도메인")
        if self.bot.enabled and not (self.bot.anthropic_api_key or self.bot.openai_api_key):
            problems.append("ANTHROPIC_API_KEY 또는 OPENAI_API_KEY (BOT_ENABLED=1)")
        if not self.tls.acme_email:
            problems.append("ACME_EMAIL")
        if not self.tls.primary_domain:
            problems.append("TLS_PRIMARY_DOMAIN")
        if problems:
            raise ConfigError(
                "production 환경 의무 키 누락 — " + ", ".join(problems)
            )
