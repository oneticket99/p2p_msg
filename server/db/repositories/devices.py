# SPDX-License-Identifier: GPL-3.0-or-later
"""devices 테이블 repository — multi-device sync 영속화 (Phase 2 사이클 43).

사이클 42 의 `app/crypto/device_registry.py` skeleton 의 server-side
counterpart. asyncmy pool 경유 INSERT / SELECT / UPDATE / soft-delete
(status='revoked') 5 함수 제공.

설계 결정
---------
- DELETE 의무 = soft-delete (status='revoked'). 외부 fan-out 송신 차단 +
  audit trail 보존. hard-delete = 별도 cycle (30일 보관 후 cron).
- 동일 device_id 재등록 = 차단 (UNIQUE 제약). 재설치 = 새 UUID 의무.
- get_devices_by_user 의 status filter = 기본 active 만 (revoked 제외).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class DeviceRow:
    """devices row dataclass — DB 의 1 row 등가 객체."""

    id: int
    device_id: str
    user_id: int
    label: str
    identity_public: bytes
    signed_prekey_public: bytes
    one_time_prekey_public: Optional[bytes]
    created_at: datetime
    updated_at: datetime
    last_seen_at: Optional[datetime]
    status: str


def _row_to_device(row: tuple) -> DeviceRow:
    """SELECT 결과 tuple → DeviceRow."""

    return DeviceRow(
        id=int(row[0]),
        device_id=str(row[1]),
        user_id=int(row[2]),
        label=str(row[3]) if row[3] is not None else "",
        identity_public=bytes(row[4]),
        signed_prekey_public=bytes(row[5]),
        one_time_prekey_public=bytes(row[6]) if row[6] is not None else None,
        created_at=row[7],
        updated_at=row[8],
        last_seen_at=row[9],
        status=str(row[10]),
    )


_SELECT_COLUMNS = (
    "id, device_id, user_id, label, identity_public, signed_prekey_public, "
    "one_time_prekey_public, created_at, updated_at, last_seen_at, status"
)


async def insert_device(
    pool: Any,
    *,
    device_id: str,
    user_id: int,
    label: str,
    identity_public: bytes,
    signed_prekey_public: bytes,
    one_time_prekey_public: Optional[bytes] = None,
) -> int:
    """device 등록. 중복 device_id = MariaDB UNIQUE 위반 (caller 단 1062 처리 의무).

    Returns
    -------
    int
        INSERT 의 lastrowid (devices.id PK).
    """

    sql = (
        "INSERT INTO devices ("
        "device_id, user_id, label, identity_public, "
        "signed_prekey_public, one_time_prekey_public"
        ") VALUES (%s, %s, %s, %s, %s, %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                sql,
                (
                    device_id,
                    user_id,
                    label,
                    identity_public,
                    signed_prekey_public,
                    one_time_prekey_public,
                ),
            )
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def get_devices_by_user(
    pool: Any,
    user_id: int,
    *,
    include_revoked: bool = False,
) -> List[DeviceRow]:
    """user_id 의 모든 device fetch.

    Parameters
    ----------
    pool : asyncmy pool
        DB connection pool.
    user_id : int
        조회 대상 사용자.
    include_revoked : bool
        True = revoked 포함, False = active 만 (기본).

    Returns
    -------
    List[DeviceRow]
        device 목록. 없으면 빈 list.
    """

    if include_revoked:
        sql = f"SELECT {_SELECT_COLUMNS} FROM devices WHERE user_id = %s ORDER BY id ASC"
        params: tuple = (user_id,)
    else:
        sql = (
            f"SELECT {_SELECT_COLUMNS} FROM devices "
            "WHERE user_id = %s AND status = 'active' ORDER BY id ASC"
        )
        params = (user_id,)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
    return [_row_to_device(row) for row in rows]


async def get_device_by_device_id(
    pool: Any,
    device_id: str,
) -> Optional[DeviceRow]:
    """device_id (UUID) 의 단일 row lookup. 미존재 = None."""

    sql = f"SELECT {_SELECT_COLUMNS} FROM devices WHERE device_id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (device_id,))
            row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_device(row)


async def revoke_device(
    pool: Any,
    device_id: str,
    user_id: int,
) -> bool:
    """device 의 status='revoked' 갱신 (soft-delete).

    user_id 검증 의무 — 다른 user 의 device revoke 차단. 본 함수는
    user_id 일치 + status='active' device 만 갱신.

    Returns
    -------
    bool
        True = 1 row 갱신 성공, False = 미존재 또는 다른 user 또는 이미 revoked.
    """

    sql = (
        "UPDATE devices SET status = 'revoked' "
        "WHERE device_id = %s AND user_id = %s AND status = 'active'"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            affected = await cur.execute(sql, (device_id, user_id))
        await conn.commit()
    return int(affected) > 0


async def update_last_seen(
    pool: Any,
    device_id: str,
) -> bool:
    """device 의 last_seen_at = NOW() 갱신. 30일 inactive 감지 정합.

    Returns
    -------
    bool
        True = 1 row 갱신, False = 미존재.
    """

    sql = (
        "UPDATE devices SET last_seen_at = CURRENT_TIMESTAMP "
        "WHERE device_id = %s"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            affected = await cur.execute(sql, (device_id,))
        await conn.commit()
    return int(affected) > 0
