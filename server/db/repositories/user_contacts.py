# SPDX-License-Identifier: GPL-3.0-or-later
"""user_contacts repository — 전화번호 기반 친구 추가 (telegram align, cycle 169.452 신설).

역할
----
사용자가 올린 주소록 연락처(전화번호 + 이름)를 영속하고, 가입자와 매칭해 친구 추천/자동 연결의
근거를 만든다(telegram 의 "연락처로 친구 찾기" 등가).

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = contacts 동기화 handler / signup 시 reverse-match use case.

매칭 모델 (invariant)
--------------------
- 전화번호는 ``normalize_phone`` 으로 E.164 정규화 후 저장/비교(입력 형식 차이 흡수).
- (owner_user_id, phone) UNIQUE — upsert 의 근거.
- **양방향 reverse match** — A 가 B 의 번호를 연락처 등록 + B 가 신규 가입 시:
  A 의 contact.matched_user_id 를 B.id 로 갱신(update_matched_user_id) → 양쪽 연락처가
  서로를 가리키면 자동 친구 연결(친구 INSERT 는 호출자 영역).
- 6 공개 함수 — normalize_phone(순수) + upsert_contact + find_user_by_phone +
  update_matched_user_id + list_owners_with_contact + list_contacts.

부작용
------
upsert/update_matched_user_id 는 write(commit). normalize_phone/find/list 류는 부작용 없음.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class UserContactRow:
    """user_contacts 단일 row 의 read-only 투영 — 7 column.

    불변식: frozen + 필드 순서 = ``list_contacts`` SELECT 컬럼 1:1. ``matched_user_id`` None =
    아직 미가입(또는 미매칭) 연락처, 값 존재 = 매칭된 가입자 PK.
    """

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
    """contact UPSERT — (owner, phone) UNIQUE. 기존이면 이름만 COALESCE 보강. row id 반환.

    의도: 주소록 동기화 — 같은 (owner, 번호) 재등록 시 중복 INSERT 대신 이름 보강(기존값 보존).
    phone 은 저장 전 normalize_phone 으로 E.164 정규화. 부작용: upsert + commit.

    Raises
    ------
    ValueError
        owner_user_id 비양수 / 정규화 결과 빈 phone.
    """
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
    """phone 정규화 후 users.phone 일치 user_id lookup. 부재 시 None. 부작용 없음.

    의도: 연락처 등록·가입 시 "이 번호가 이미 가입자인가" 판정(reverse match 의 한 축).
    뒤 10자리(국가코드 제외 가입자 식별 부분)로 LIKE 비교해 저장 형식 차이를 흡수한다.
    """
    norm = normalize_phone(phone)
    if not norm:
        return None
    # 한글 주석 — users.phone 컬럼이 정규화 저장을 보장하지 않아(별도 migration 필요) 본 cycle 은
    # SQL REPLACE 로 구분자 제거 후 digit 만 비교한다(임시 방편 — phone 정규화 migration 후 단순화 예정).
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
    """phone 일치 모든 contact 의 matched_user_id 일괄 UPDATE. 갱신 row 수 반환.

    의도: 신규 가입 시 reverse propagate — 그 번호를 연락처에 담아둔 모든 owner 의 contact 가
    신규 가입자를 가리키게 한다(가입 즉시 "내 연락처가 가입했어요" 추천 활성). 부작용: UPDATE + commit.
    """
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
    """해당 phone 을 연락처에 저장한 owner_user_id list. 부작용 없음(SELECT only).

    의도: reverse match 의 후보 산출 — 신규 가입자의 번호를 연락처에 담아둔 owner 들을 찾는다.
    흐름: A 가 B 의 번호를 연락처 등록 + B 신규 가입 → A 의 contact.matched_user_id = B.id 갱신
    → 양방향 확인(B 의 연락처에도 A 번호 존재)되면 호출자가 친구 자동 연결을 INSERT.

    Returns
    -------
    List[int]
        해당 번호를 등록한 owner user_id 목록(부재 시 빈 list).
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
    """owner 의 연락처 전수 list — 이름(성/이름) 정렬. 부작용 없음(SELECT only).

    의도: 연락처 목록 화면(telegram align). 호출자가 matched_user_id 로 가입/미가입을 구분 표시.
    """
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
