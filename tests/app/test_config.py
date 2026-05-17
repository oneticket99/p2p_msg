"""``app.core.config`` 측 단위 테스트.

DESIGN.md §10.1 정합 — 단위 테스트는 Qt 비의존 + 외부 IO 격리.
사용자 directive 2026-05-17 (MariaDB 회수) 측 5 DB 필드 정합 검증.
"""

from __future__ import annotations

import pytest


def test_load_config_defaults_when_env_empty() -> None:
    """환경변수 모두 미설정 시 ``_DEFAULT_*`` 상수 값으로 폴백."""

    from app.core.config import load_config

    cfg = load_config()

    # 시그널링 기본값 (.env.example 정합)
    assert cfg.signal_host == "114.207.112.73"
    assert cfg.signal_port == 8765
    assert cfg.signal_scheme == "ws"

    # MariaDB 기본값 (사용자 directive 2026-05-17)
    assert cfg.db_host == "127.0.0.1"
    assert cfg.db_port == 3306
    assert cfg.db_user == "tootalk"
    assert cfg.db_pass == ""
    assert cfg.db_name == "tootalk"


def test_load_config_reads_signal_host_from_env(
    fake_env_signal_host: str,
) -> None:
    """``SIGNAL_SERVER_HOST`` env var 우선 적용 검증."""

    from app.core.config import load_config

    cfg = load_config()
    assert cfg.signal_host == fake_env_signal_host


def test_db_dsn_property_format() -> None:
    """``db_dsn`` 프로퍼티 측 mysql:// 형식 검증 (asyncmy 호환)."""

    from app.core.config import load_config

    cfg = load_config()
    expected = (
        f"mysql://{cfg.db_user}:{cfg.db_pass}"
        f"@{cfg.db_host}:{cfg.db_port}/{cfg.db_name}"
    )
    assert cfg.db_dsn == expected


def test_signaling_url_property_format() -> None:
    """``signaling_url`` 프로퍼티 측 ws:// 형식 검증."""

    from app.core.config import load_config

    cfg = load_config()
    expected = (
        f"{cfg.signal_scheme}://{cfg.signal_host}:{cfg.signal_port}/ws"
    )
    assert cfg.signaling_url == expected


def test_invalid_signal_port_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``SIGNAL_SERVER_WS_PORT`` 정수 변환 실패 시 기본값 8765 폴백."""

    from app.core.config import load_config

    monkeypatch.setenv("SIGNAL_SERVER_WS_PORT", "not_an_int")
    cfg = load_config()
    assert cfg.signal_port == 8765


def test_invalid_signal_scheme_falls_back_to_ws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``ws`` / ``wss`` 외 값은 ``ws`` 로 폴백."""

    from app.core.config import load_config

    monkeypatch.setenv("SIGNAL_SERVER_WS_SCHEME", "http")
    cfg = load_config()
    assert cfg.signal_scheme == "ws"
