# SPDX-License-Identifier: GPL-3.0-or-later
"""asyncmy 기반 MariaDB 연결 pool wrapper.

본 모듈 = 시그널링 서버 의 모든 DB 접근 entry point.
환경변수 의 의 의 의 의 설정 (정본 §E 12-factor) — 하드코딩 금지.

사용 패턴::

    pool = await create_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            row = await cur.fetchone()

환경변수:
- DB_HOST (default 127.0.0.1)
- DB_PORT (default 3306)
- DB_USER (default tootalk)
- DB_PASS (default 비움 — 운영 의무)
- DB_NAME (default tootalk)
- DB_POOL_MIN (default 1)
- DB_POOL_MAX (default 10)
- DB_CHARSET (default utf8mb4)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

log = logging.getLogger(__name__)

# asyncmy import — 의 의 wheel install 시점 의 의 의 ImportError 대응
try:
    import asyncmy
except ImportError:  # pragma: no cover - 의존성 미설치 환경
    asyncmy = None  # type: ignore[assignment]


def _env_str(key: str, default: str) -> str:
    """환경변수 문자열 — 빈값 폴백."""

    raw = os.environ.get(key, "").strip()
    return raw if raw else default


def _env_int(key: str, default: int, *, min_value: int = 1) -> int:
    """환경변수 정수 + min_value 검증 + 폴백 (app/rtc/file_*._env_int 정합)."""

    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        parsed = int(raw)
        if parsed < min_value:
            raise ValueError
        return parsed
    except ValueError:
        log.warning("%s 환경변수 정수 변환 실패 — raw=%r 기본값 %d 사용", key, raw, default)
        return default


async def create_pool() -> Any:
    """asyncmy 연결 pool 생성.

    Returns
    -------
    asyncmy.Pool
        connection pool — `async with pool.acquire() as conn` 패턴 사용.

    Raises
    ------
    RuntimeError
        asyncmy 미설치 시.
    """

    if asyncmy is None:
        raise RuntimeError(
            "asyncmy 미설치 — `pip install -r server/requirements.txt` 후 재시도"
        )

    host = _env_str("DB_HOST", "127.0.0.1")
    port = _env_int("DB_PORT", 3306, min_value=1)
    user = _env_str("DB_USER", "tootalk")
    password = os.environ.get("DB_PASS", "")  # 빈 비번 허용 (로컬 dev)
    db_name = _env_str("DB_NAME", "tootalk")
    pool_min = _env_int("DB_POOL_MIN", 1, min_value=1)
    pool_max = _env_int("DB_POOL_MAX", 10, min_value=1)
    charset = _env_str("DB_CHARSET", "utf8mb4")

    log.info(
        "[DB] asyncmy pool 생성 host=%s port=%d db=%s user=%s pool=%d~%d",
        host,
        port,
        db_name,
        user,
        pool_min,
        pool_max,
    )

    return await asyncmy.create_pool(
        host=host,
        port=port,
        user=user,
        password=password,
        db=db_name,
        minsize=pool_min,
        maxsize=pool_max,
        charset=charset,
        autocommit=False,  # 명시 commit — repositories layer 의무
    )


async def close_pool(pool: Any) -> None:
    """asyncmy pool 종료 — graceful shutdown 정합."""

    if pool is None:
        return
    pool.close()
    await pool.wait_closed()
    log.info("[DB] asyncmy pool 종료 완료")
