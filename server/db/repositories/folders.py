# SPDX-License-Identifier: GPL-3.0-or-later
"""folders + folder_chats + folder_invites repository (cycle 169.76 신설).

역할
----
채팅 폴더(최상위 그룹화)와 그 안의 chat 포함/제외 규칙·초대 링크를 영속한다.
도메인: folder(최상위) ⊃ folder_chats(포함/제외 규칙) + folder_invites(공유 초대).

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = folders 관리 handler. DDL 정합: ``0009_folders.sql``.

invariant / 설계 결정
--------------------
- folder_id = uuid 8자(애플리케이션 생성). (folder_id, owner_id) 로 소유권 검증 후 접근.
- **include/exclude 2-mode** — folder_chats.mode 가 include(포함) 또는 exclude(명시 제외). 표시 시
  included 만 보이거나 excluded 를 빼는 규칙(list_folder_chats 가 양쪽 분리 반환).
- **batch = 단일 transaction** — insert/update_folder_with_chats 는 folder + chats 를 한 트랜잭션으로
  묶어 부분 실패(folder 만 생성/chats 누락)를 차단(cycle 169.79 HIGH-2 회수).
- chat_count 는 included 수의 캐시(매 조회 COUNT 회피).
- 모든 함수 = pool DI + parameterized SQL. write 류 commit, read 류 부작용 없음.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class FolderRow:
    """folders 단일 row 의 read-only 투영 — 8 column.

    불변식: frozen + 필드 순서 = folders SELECT 컬럼 1:1. ``color_name``/``color_hex`` None =
    색상 미지정, ``chat_count`` = 포함 chat 수 캐시.
    """

    id: int
    folder_id: str
    owner_id: int
    name: str
    color_name: Optional[str]
    color_hex: Optional[str]
    chat_count: int
    created_at: datetime


async def insert_folder(
    pool: Any,
    *,
    folder_id: str,
    owner_id: int,
    name: str,
    color_name: Optional[str] = None,
    color_hex: Optional[str] = None,
) -> int:
    """folder 단건 INSERT — folder_id(uuid 8자) + owner + name + color. 신규 id 반환.

    의도: chat 없는 빈 폴더 생성. chat 동반 생성은 insert_folder_with_chats(단일 transaction).
    부작용: folders INSERT + commit.
    """
    sql = (
        "INSERT INTO folders (folder_id, owner_id, name, color_name, color_hex) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_id, owner_id, name, color_name, color_hex))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def list_folders(pool: Any, owner_id: int) -> List[FolderRow]:
    """owner 의 폴더 전수 list — 생성 순(id ASC). 부작용 없음(SELECT only).

    의도: 폴더 탭 표시. chat 포함 규칙은 list_folder_chats 로 별도 조회(목록은 메타만).
    """
    sql = (
        "SELECT id, folder_id, owner_id, name, color_name, color_hex, chat_count, created_at "
        "FROM folders WHERE owner_id = %s ORDER BY id ASC"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (owner_id,))
            rows = await cur.fetchall()
    return [FolderRow(*row) for row in rows]


async def list_folder_chats(pool: Any, folder_pk: int) -> dict:
    """folder_chats 조회 — include/exclude 모드별 분리 dict 반환 (cycle 169.387).

    의도: 폴더 편집/표시 화면이 "포함된 chat"과 "명시 제외된 chat"을 따로 그릴 수 있게 한다.
    회귀 회수 근거 — 이전엔 server response 에 included_chats/excluded_chats 필드가 없어
    (사용자 critique image #148) UI 가 규칙을 복원 못 하던 결함을 본 함수로 해소. 부작용 없음.

    Returns
    -------
    dict
        ``{"included_chats": [{"kind","target_id"}...], "excluded_chats": [...]}``.
    """
    sql = (
        "SELECT chat_kind, chat_target_id, mode FROM folder_chats "
        "WHERE folder_id = %s"
    )
    included: list = []
    excluded: list = []
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_pk,))
            rows = await cur.fetchall()
    for kind, tid, mode in rows or []:
        entry = {"kind": kind, "target_id": int(tid)}
        if mode == "exclude":
            excluded.append(entry)
        else:
            included.append(entry)
    return {"included_chats": included, "excluded_chats": excluded}


async def delete_folder(pool: Any, folder_id: str, owner_id: int) -> bool:
    """폴더 삭제 — (folder_id, owner_id) 정합 시만. 삭제 여부 bool. 부작용: DELETE + commit.

    의도: owner_id 를 WHERE 에 포함해 남의 폴더 삭제를 차단(소유권 검증). folder_chats 는
    DDL ON DELETE CASCADE 로 동반 정리(별도 DELETE 불요).
    """
    sql = "DELETE FROM folders WHERE folder_id = %s AND owner_id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_id, owner_id))
            affected = cur.rowcount
        await conn.commit()
    return int(affected or 0) > 0


async def add_folder_chat(
    pool: Any,
    *,
    folder_pk: int,
    chat_kind: str,
    chat_target_id: int,
    mode: str = "include",
) -> int:
    """folder 에 chat 포함/제외 규칙 1건 추가. INSERT IGNORE(중복 무시). 부작용: INSERT + commit.

    의도: 폴더에 대화를 단건 추가. INSERT IGNORE 로 (folder, kind, target) 중복 등록을 멱등 처리.
    """
    sql = (
        "INSERT IGNORE INTO folder_chats (folder_id, chat_kind, chat_target_id, mode) "
        "VALUES (%s, %s, %s, %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_pk, chat_kind, chat_target_id, mode))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id) if new_id else 0


async def fetch_by_folder_id_and_owner(
    pool: Any, folder_id: str, owner_id: int,
) -> Optional[FolderRow]:
    """단일 SELECT — owner check + folder_id 정합 (cycle 169.79 MED-1 회수)."""
    sql = (
        "SELECT id, folder_id, owner_id, name, color_name, color_hex, chat_count, created_at "
        "FROM folders WHERE folder_id = %s AND owner_id = %s LIMIT 1"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_id, owner_id))
            row = await cur.fetchone()
    return FolderRow(*row) if row is not None else None


async def insert_folder_with_chats(
    pool: Any,
    *,
    folder_id: str,
    owner_id: int,
    name: str,
    color_name: Optional[str] = None,
    color_hex: Optional[str] = None,
    included_chats: Optional[list] = None,
    excluded_chats: Optional[list] = None,
) -> int:
    """folder + chats batch — 단일 transaction (cycle 169.79 HIGH-2 회수)."""
    sql_folder = (
        "INSERT INTO folders (folder_id, owner_id, name, color_name, color_hex, chat_count) "
        "VALUES (%s, %s, %s, %s, %s, %s)"
    )
    sql_chat = (
        "INSERT IGNORE INTO folder_chats (folder_id, chat_kind, chat_target_id, mode) "
        "VALUES (%s, %s, %s, %s)"
    )
    included_chats = included_chats or []
    excluded_chats = excluded_chats or []
    chat_count_cache = len(included_chats)
    async with pool.acquire() as conn:
        try:
            await conn.begin()
        except AttributeError:
            await conn.autocommit(False)
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    sql_folder,
                    (folder_id, owner_id, name, color_name, color_hex, chat_count_cache),
                )
                new_id = cur.lastrowid
                for chat in included_chats:
                    await cur.execute(
                        sql_chat,
                        (new_id, str(chat.get("kind", "")), int(chat.get("target_id", 0)), "include"),
                    )
                for chat in excluded_chats:
                    await cur.execute(
                        sql_chat,
                        (new_id, str(chat.get("kind", "")), int(chat.get("target_id", 0)), "exclude"),
                    )
            await conn.commit()
            return int(new_id)
        except Exception:
            await conn.rollback()
            raise


async def update_folder_with_chats(
    pool: Any,
    *,
    folder_id: str,
    owner_id: int,
    name: str,
    color_name: Optional[str] = None,
    color_hex: Optional[str] = None,
    included_chats: Optional[list] = None,
    excluded_chats: Optional[list] = None,
) -> bool:
    """cycle 169.411 — folder edit mode 의 server UPDATE chain (Phase 1 잔존 회수).

    단일 transaction 안 sequence:
    1. folders UPDATE (name + color + chat_count + updated_at) — owner_id 정합 의무
    2. folder_chats DELETE (folder_pk 기준 전수 삭제)
    3. folder_chats INSERT batch (included + excluded reconciliation)

    Returns True = UPDATE PASS (1+ row affected). False = folder_id 부재 또는 권한 부재.
    """
    sql_update = (
        "UPDATE folders SET name = %s, color_name = %s, color_hex = %s, chat_count = %s "
        "WHERE folder_id = %s AND owner_id = %s"
    )
    sql_delete_chats = "DELETE FROM folder_chats WHERE folder_id = %s"
    sql_insert_chat = (
        "INSERT IGNORE INTO folder_chats (folder_id, chat_kind, chat_target_id, mode) "
        "VALUES (%s, %s, %s, %s)"
    )
    included_chats = included_chats or []
    excluded_chats = excluded_chats or []
    chat_count_cache = len(included_chats)
    async with pool.acquire() as conn:
        try:
            await conn.begin()
        except AttributeError:
            await conn.autocommit(False)
        try:
            async with conn.cursor() as cur:
                # 한글 주석 — folder lookup 으로 PK 확보(이후 chats DELETE/INSERT 의 FK)
                row = None
                await cur.execute(
                    "SELECT id FROM folders WHERE folder_id = %s AND owner_id = %s LIMIT 1",
                    (folder_id, owner_id),
                )
                row = await cur.fetchone()
                if row is None:
                    await conn.rollback()
                    return False
                folder_pk = int(row[0])
                # 한글 주석 — folders UPDATE
                await cur.execute(
                    sql_update,
                    (name, color_name, color_hex, chat_count_cache, folder_id, owner_id),
                )
                # 한글 주석 — folder_chats 전수 DELETE + reconciliation
                await cur.execute(sql_delete_chats, (folder_pk,))
                for chat in included_chats:
                    await cur.execute(
                        sql_insert_chat,
                        (folder_pk, str(chat.get("kind", "")), int(chat.get("target_id", 0)), "include"),
                    )
                for chat in excluded_chats:
                    await cur.execute(
                        sql_insert_chat,
                        (folder_pk, str(chat.get("kind", "")), int(chat.get("target_id", 0)), "exclude"),
                    )
            await conn.commit()
            return True
        except Exception:
            await conn.rollback()
            raise


async def create_invite(
    pool: Any,
    *,
    folder_pk: int,
    created_by: int,
    expires_days: int = 7,
) -> str:
    """초대 link token 생성 — folder_invites row insert + 7일 default expires (cycle 169.79 LOW-1)."""
    token = secrets.token_hex(16)
    sql = (
        "INSERT INTO folder_invites (folder_id, invite_token, created_by, expires_at) "
        "VALUES (%s, %s, %s, DATE_ADD(CURRENT_TIMESTAMP, INTERVAL %s DAY))"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_pk, token, created_by, expires_days))
        await conn.commit()
    return token
