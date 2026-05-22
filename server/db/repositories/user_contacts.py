# SPDX-License-Identifier: GPL-3.0-or-later
"""user_contacts repository — telegram align phone 기반 친구 추가 (cycle 169.452 신설)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class UserContactRow:
    id: int
    owner_user_id: int
    phone: str
    last_name: Optional[str]
    first_name: Optional[str]
    matched_user_id: Optional[int]
    created_at: datetime


def normalize_phone(phone: str) -> str:
    """E.164 정규화 — 숫자만 retain + 11 digit 한국 휴대폰 한정 '+' prefix.

    Notes
    -----
    - '01012345678' → '+821012345678'
    - '+82 10 1234 5678' → '+821012345678'
    - '821012345678' → '+821012345678'
    """
    if not phone:
        return ""
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return ""
    if digits.startswith("0") and len(digits) == 11:
        return f"+82{digits[1:]}"
    if digits.startswith("82") and len(digits) == 12:
        return f"+{digits}"
    return f"+{digits}"


async def upsert_contact(
    pool: Any, *, owner_user_id: int, phone: str,
    last_name: Optional[str] = None, first_name: Optional[str] = None,
) -> int:
    """contact UPSERT — (owner, phone) UNIQUE 정합 시점 last_name/first_name 갱신."""
    if owner_user_id <= 0:
        raise ValueError("owner_user_id 양수 의무")
    norm = normalize_phone(phone)
    if not norm:
        raise ValueError("phone 빈 차단")
    sql = (
        "INSERT INTO user_contacts (owner_user_id, phone, last_name, first_name) "
        "VALUES (%s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE "
        "  last_name = COALESCE(VALUES(last_name), last_name), "
        "  first_name = COALESCE(VALUES(first_name), first_name)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (owner_user_id, norm, last_name, first_name))
            row_id = int(cur.lastrowid)
        await conn.commit()
    return row_id


async def find_user_by_phone(pool: Any, phone: str) -> Optional[int]:
    """phone normalize 후 users.phone 일치 user_id lookup (reverse match base)."""
    norm = normalize_phone(phone)
    if not norm:
        return None
    # 한글 주석 — users.phone 의 의 normalized retain 의무 (별 cycle migration 의 필요). 본 cycle = digit only 비교
    digits = norm.lstrip("+")
    sql = "SELECT id FROM users WHERE REPLACE(REPLACE(REPLACE(phone, '-', ''), ' ', ''), '+', '') LIKE %s LIMIT 1"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (f"%{digits[-10:]}",))
            row = await cur.fetchone()
    return int(row[0]) if row else None


async def update_matched_user_id(
    pool: Any, *, phone: str, matched_user_id: int,
) -> int:
    """phone 일치 모든 contact row 의 matched_user_id UPDATE (signup 시점 reverse propagate)."""
    norm = normalize_phone(phone)
    if not norm:
        return 0
    sql = "UPDATE user_contacts SET matched_user_id = %s WHERE phone = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (matched_user_id, norm))
            rowcount = int(cur.rowcount or 0)
        await conn.commit()
    return rowcount


async def list_owners_with_contact(
    pool: Any, *, phone: str,
) -> List[int]:
    """본 phone 을 contact 안 저장한 owner_user_id list (reverse match base).

    user A 가 user B 의 phone 을 contact 등록 시점 + user B 신규 가입 시점:
    → A 의 contact matched_user_id = B.id 갱신
    → 양방향 검증: B 의 contact 안 A.phone 존재 시점 자동 friends INSERT
    """
    norm = normalize_phone(phone)
    if not norm:
        return []
    sql = "SELECT owner_user_id FROM user_contacts WHERE phone = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (norm,))
            rows = await cur.fetchall()
    return [int(r[0]) for r in rows]


async def list_contacts(pool: Any, *, owner_user_id: int) -> List[UserContactRow]:
    """owner contact 전수 list (telegram align list view base)."""
    sql = (
        "SELECT id, owner_user_id, phone, last_name, first_name, matched_user_id, created_at "
        "FROM user_contacts WHERE owner_user_id = %s ORDER BY last_name, first_name"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (owner_user_id,))
            rows = await cur.fetchall()
    return [
        UserContactRow(
            id=int(r[0]), owner_user_id=int(r[1]), phone=str(r[2]),
            last_name=r[3], first_name=r[4],
            matched_user_id=int(r[5]) if r[5] is not None else None,
            created_at=r[6],
        )
        for r in rows
    ]
