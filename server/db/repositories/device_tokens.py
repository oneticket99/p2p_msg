# SPDX-License-Identifier: GPL-3.0-or-later
"""device_tokens repository — FCM push notification token 영속 (cycle 169.446 신설).

역할
----
사용자의 기기별 FCM push token(multi-device)을 영속하고, push 발송 시 활성 token 으로 fan-out 한다.

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = push 발송 use case / devices 관련 handler.
DDL 정합: ``server/db/migrations/0013_device_tokens.sql``.

invariant / 설계 결정
--------------------
- (user_id, fcm_token) UNIQUE — upsert(ON DUPLICATE KEY) 의 근거. 같은 기기 재등록 시 row 중복 방지.
- **soft revoke** — token 무효화는 삭제가 아니라 ``is_active = 0``(재활성/audit 여지). 활성 = is_active=1.
- 입력 검증 — user_id 양수 + fcm_token 1~512자 + platform 6 ENUM. DB 도달 전 ValueError fail-fast.
- 4 공개 함수 — upsert_token + list_active_tokens + deactivate_token + touch_last_used.

부작용
------
upsert/deactivate/touch 는 write(commit). list_active_tokens 는 부작용 없음(SELECT only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class DeviceTokenRow:
    """device_tokens 단일 row 의 read-only 투영 — 8 column.

    불변식: frozen. ``is_active`` False = revoke 됨(push 대상 제외). ``last_used_at`` = 마지막
    push 발송 시각(idle token 정리 chain 의 근거).
    """

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
    """token UPSERT — (user_id, fcm_token) UNIQUE. 기존이면 is_active=1 재활성 + label 보강.

    의도: 앱 시작/로그인 시 FCM token 등록. 같은 token 재등록이면 INSERT 대신 ON DUPLICATE KEY
    로 재활성(이전 revoke 해제) + device_label COALESCE 보강(기존 label 보존). 부작용: upsert + commit.

    Raises
    ------
    ValueError
        user_id 비양수 / fcm_token 길이 1~512 위반 / platform 이 6 ENUM 외.

    Returns
    -------
    int
        row id (신규 INSERT 시 lastrowid).
    """
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
    """사용자의 활성 token list — is_active=1 만 (push 발송 fan-out 대상). 부작용 없음.

    의도: push 발송 시 한 사용자의 모든 기기에 fan-out 할 대상 산출. revoke 된 token 제외.
    """
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
    """token revoke (is_active=0, soft). 갱신 성공 여부 bool 반환. 부작용: UPDATE + commit.

    의도: FCM 이 token 무효(unregistered) 응답 시 또는 사용자 명시 unsubscribe 시 호출 —
    삭제 대신 비활성화해 audit/재활성 여지를 남긴다(soft revoke invariant).
    """
    sql = "UPDATE device_tokens SET is_active = 0 WHERE id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (token_id,))
            rowcount = int(cur.rowcount or 0)
        await conn.commit()
    return rowcount > 0


async def touch_last_used(pool: Any, *, token_id: int) -> None:
    """push 발송 직후 last_used_at = CURRENT_TIMESTAMP 갱신. 부작용: UPDATE + commit.

    의도: token 최근 사용 시각 추적 — 장기 미사용(idle) token 의 주기적 정리/revoke chain 의 근거.
    """
    sql = "UPDATE device_tokens SET last_used_at = CURRENT_TIMESTAMP WHERE id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (token_id,))
        await conn.commit()
