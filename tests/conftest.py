"""TooTalk(p2p_msg) pytest 공유 픽스처.

DESIGN.md §10.4 정합 — 픽스처는 본 파일 측 ``@pytest.fixture`` 로 정의한다.
사용자 directive 2026-05-17 — "qa 단계에서는 pytest 당연히 필요해".
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# 저장소 루트 경로 — 모든 테스트 측 공유 (.env 로딩 / 픽스처 경로 등)
REPO_ROOT: Path = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """저장소 루트 절대경로 픽스처 (세션 단위 단일 인스턴스)."""

    return REPO_ROOT


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """테스트 간 환경변수 격리 — 외부 ``.env`` 영향 차단.

    각 테스트 시작 시 TooTalk 관련 env vars 모두 제거.
    개별 테스트 측 ``monkeypatch.setenv`` 로 명시 주입한 값만 유효.
    """

    keys_to_clear = [
        "SIGNAL_SERVER_HOST",
        "SIGNAL_SERVER_WS_PORT",
        "SIGNAL_SERVER_WS_SCHEME",
        "STUN_URL",
        "TURN_URL",
        "TURN_USERNAME",
        "TURN_CREDENTIAL",
        "USER_NICKNAME",
        "LOG_LEVEL",
        "DB_HOST",
        "DB_PORT",
        "DB_USER",
        "DB_PASS",
        "DB_NAME",
        "MEDIA_CACHE_DIR",
    ]
    for key in keys_to_clear:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def fake_env_signal_host(monkeypatch: pytest.MonkeyPatch) -> str:
    """``SIGNAL_SERVER_HOST`` 측 테스트 전용 fake 값."""

    fake_host = "10.0.0.42"
    monkeypatch.setenv("SIGNAL_SERVER_HOST", fake_host)
    return fake_host
