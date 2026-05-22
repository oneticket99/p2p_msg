# SPDX-License-Identifier: GPL-3.0-or-later
"""device_tokens repository — FCM push notification token 영속 (cycle 169.446 신설).

DDL 정합: `server/db/migrations/0013_device_tokens.sql`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class DeviceTokenRow:
    id: int
    user_id: int
    fcm_token: str
    platform: str
    device_label: Optional[str]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]


async def upsert_token(
    pool: Any, *, user_id: int, fcm_token: str, platform: str,
    device_label: Optional[str] = None,
) -> int:
    """token UPSERT — (user_id, fcm_token) UNIQUE 정합 시점 is_active=1 + last_used_at 갱신."""
    if user_id <= 0:
        raise ValueError(f"user_id 양수 의무 — {user_id}")
    if not fcm_token or len(fcm_token) > 512:
        raise ValueError(f"fcm_token 1~512자 의무 — len={len(fcm_token)}")
    if platform not in ("macos", "windows", "linux", "ios", "android", "web"):
        raise ValueError(f"platform ENUM 의무 — {platform}")
    sql = (
        "INSERT INTO device_tokens (user_id, fcm_token, platform, device_label) "
        "VALUES (%s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE is_active = 1, device_label = COALESCE(VALUES(device_label), device_label)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id, fcm_token, platform, device_label))
            row_id = int(cur.lastrowid)
        await conn.commit()
    return row_id


async def list_active_tokens(pool: Any, *, user_id: int) -> List[DeviceTokenRow]:
    """사용자 active token list (push send 시점 fan-out base)."""
    sql = (
        "SELECT id, user_id, fcm_token, platform, device_label, is_active, "
        "       created_at, last_used_at FROM device_tokens "
        "WHERE user_id = %s AND is_active = 1"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id,))
            rows = await cur.fetchall()
    return [
        DeviceTokenRow(
            id=int(r[0]), user_id=int(r[1]), fcm_token=str(r[2]),
            platform=str(r[3]), device_label=r[4], is_active=bool(r[5]),
            created_at=r[6], last_used_at=r[7],
        )
        for r in rows
    ]


async def deactivate_token(pool: Any, *, token_id: int) -> bool:
    """token revoke (is_active=0). FCM unregister 응답 또는 사용자 명시 unsub."""
    sql = "UPDATE device_tokens SET is_active = 0 WHERE id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (token_id,))
            rowcount = int(cur.rowcount or 0)
        await conn.commit()
    return rowcount > 0


async def touch_last_used(pool: Any, *, token_id: int) -> None:
    """push send 직후 last_used_at = NOW() 갱신 (idle revoke chain base)."""
    sql = "UPDATE device_tokens SET last_used_at = CURRENT_TIMESTAMP WHERE id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (token_id,))
        await conn.commit()
