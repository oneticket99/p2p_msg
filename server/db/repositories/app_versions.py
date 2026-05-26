# SPDX-License-Identifier: GPL-3.0-or-later
"""app_versions 영속화 repository — 자동 업데이트 버전 카탈로그 (Phase 5 cycle 132).

역할
----
플랫폼별 앱 릴리즈(버전/다운로드 URL/체크섬/최신 플래그)를 영속해 클라이언트 자동 업데이트
version check 의 source 를 제공한다.

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = 업데이트 version check handler + 관리자 console.
DDL 정합: ``server/db/migrations/0006_app_versions.sql``. pool DI + parameterized SQL.

invariant / 설계 결정
--------------------
- Platform = ENUM 4종(macos-arm64 / macos-x64 / windows-x64 / linux-x64) — str Enum, DDL enum 정합.
- **플랫폼당 is_latest=1 단 1건** — mark_latest 가 동일 platform 의 기존 latest 를 reset 한 뒤 본 row 만
  1 로 세팅하는 것을 단일 트랜잭션(UPDATE 2회 atomic)으로 보장(latest 중복/공백 방지).
- insert_version 은 admin only(caller 권한 검증 의무).
- 4 공개 함수 — insert_version + get_latest_by_platform + list_history + mark_latest.

부작용
------
insert_version/mark_latest 는 write(commit). get_latest/list_history 는 부작용 없음(SELECT only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional


class Platform(str, Enum):
    """플랫폼 ENUM — DDL 의 enum 정합."""

    MACOS_ARM64 = "macos-arm64"
    MACOS_X64 = "macos-x64"
    WINDOWS_X64 = "windows-x64"
    LINUX_X64 = "linux-x64"


@dataclass(frozen=True, slots=True)
class AppVersionRow:
    """app_versions row 도메인 객체."""

    id: int
    version: str
    platform: Platform
    zip_url: str
    sha256: str
    file_size: int
    min_compatible_version: Optional[str]
    released_at: datetime
    release_notes: Optional[str]
    is_latest: bool


# ─── SQL ────────────────────────────────────────────────────────────────────

_SELECT_COLUMNS = (
    "id, version, platform, zip_url, sha256, file_size, "
    "min_compatible_version, released_at, release_notes, is_latest"
)

_INSERT = (
    "INSERT INTO app_versions ("
    "version, platform, zip_url, sha256, file_size, "
    "min_compatible_version, release_notes, is_latest"
    ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
)

_SELECT_LATEST = (
    f"SELECT {_SELECT_COLUMNS} FROM app_versions "
    "WHERE platform = %s AND is_latest = 1 LIMIT 1"
)

_SELECT_HISTORY = (
    f"SELECT {_SELECT_COLUMNS} FROM app_versions "
    "WHERE platform = %s ORDER BY released_at DESC LIMIT %s"
)

_RESET_LATEST = (
    "UPDATE app_versions SET is_latest = 0 WHERE platform = %s AND is_latest = 1"
)

_MARK_LATEST = (
    "UPDATE app_versions SET is_latest = 1 WHERE id = %s"
)


def _row_to_dataclass(row: tuple) -> AppVersionRow:
    """SELECT 결과 tuple → AppVersionRow 의 도메인 변환."""

    return AppVersionRow(
        id=int(row[0]),
        version=str(row[1]),
        platform=Platform(row[2]),
        zip_url=str(row[3]),
        sha256=str(row[4]),
        file_size=int(row[5]),
        min_compatible_version=str(row[6]) if row[6] is not None else None,
        released_at=row[7],
        release_notes=str(row[8]) if row[8] is not None else None,
        is_latest=bool(row[9]),
    )


# ─── repository 함수 ────────────────────────────────────────────────────────


async def insert_version(
    pool: Any,
    *,
    version: str,
    platform: Platform,
    zip_url: str,
    sha256: str,
    file_size: int = 0,
    min_compatible_version: Optional[str] = None,
    release_notes: Optional[str] = None,
    is_latest: bool = False,
) -> int:
    """신규 버전 INSERT — 반환값 = lastrowid (app_versions.id PK).

    Parameters
    ----------
    pool : asyncmy pool — None 차단.
    version : semver 문자열 — 32자 cap.
    platform : Platform ENUM — DDL enum 의 정합.
    zip_url : GitHub Release zip URL — 512자 cap + HTTPS 의무 (caller 검증).
    sha256 : zip 의 SHA-256 hex 64자 (소문자).
    file_size : zip 바이트 (0 = 미산정 fallback).
    min_compatible_version : 하위 호환 minimum 버전 — NULL 허용.
    release_notes : 한국어 변경 사항 — NULL 허용.
    is_latest : 출시 직후 latest 의 flag 의무 여부.

    Raises
    ------
    ValueError
        pool 부재 / version 빈 / zip_url 빈 / sha256 비-hex 의 64자 의 위반.
    """

    if pool is None:
        raise ValueError("pool 의무")
    if not version:
        raise ValueError("version 빈 차단")
    if len(version) > 32:
        raise ValueError(f"version 32자 cap — 실 {len(version)}")
    if not zip_url:
        raise ValueError("zip_url 빈 차단")
    if len(zip_url) > 512:
        raise ValueError(f"zip_url 512자 cap — 실 {len(zip_url)}")
    if len(sha256) != 64:
        raise ValueError(f"sha256 hex 64자 의무 — 실 {len(sha256)}")
    try:
        int(sha256, 16)
    except ValueError as exc:
        raise ValueError(f"sha256 hex 의무 — 실 {sha256!r}") from exc
    if file_size < 0:
        raise ValueError(f"file_size 음수 차단 — {file_size}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _INSERT,
                (
                    version,
                    platform.value,
                    zip_url,
                    sha256.lower(),
                    file_size,
                    min_compatible_version,
                    release_notes,
                    1 if is_latest else 0,
                ),
            )
            await conn.commit()
            return int(cur.lastrowid)


async def get_latest_by_platform(
    pool: Any, platform: Platform
) -> Optional[AppVersionRow]:
    """플랫폼 별 최신 버전 SELECT — 없으면 None.

    GET /api/version/latest endpoint 의 base 의무.
    """

    if pool is None:
        raise ValueError("pool 의무")
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SELECT_LATEST, (platform.value,))
            row = await cur.fetchone()
            return _row_to_dataclass(row) if row else None


async def list_history(
    pool: Any, *, platform: Platform, limit: int = 50
) -> List[AppVersionRow]:
    """플랫폼 별 출시 history DESC — 관리자 console base."""

    if pool is None:
        raise ValueError("pool 의무")
    if limit <= 0:
        raise ValueError(f"limit 양수 의무 — {limit}")
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SELECT_HISTORY, (platform.value, limit))
            rows = await cur.fetchall()
            return [_row_to_dataclass(r) for r in rows]


async def mark_latest(pool: Any, *, version_id: int, platform: Platform) -> int:
    """동일 platform 의 기존 latest reset + 본 row is_latest=1.

    UPDATE 2회 의 atomic transaction. 반환값 = mark 의 rowcount (0 또는 1).
    """

    if pool is None:
        raise ValueError("pool 의무")
    if version_id <= 0:
        raise ValueError(f"version_id 양수 의무 — {version_id}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 한글 주석: 동일 platform 의 기존 latest 의 reset 의 선행
            await cur.execute(_RESET_LATEST, (platform.value,))
            # 한글 주석: 본 row 의 is_latest=1 의 mark
            await cur.execute(_MARK_LATEST, (version_id,))
            await conn.commit()
            return int(cur.rowcount or 0)
