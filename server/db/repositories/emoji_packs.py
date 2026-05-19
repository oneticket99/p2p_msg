# SPDX-License-Identifier: GPL-3.0-or-later
"""emoji_packs 영속화 repository — Phase 5 Item 3 cycle 132 skeleton.

DDL 정합 = `server/db/migrations/0004_emoji_packs.sql`.
모든 함수 = pool DI + asyncmy execute + parameterized SQL (injection 차단).

설계 결정
---------
- ModerationStatus + ItemModerationStatus ENUM = DDL 정합 의 enum dataclass.
- EmojiPackRow + EmojiPackItemRow = frozen dataclass slots — 메모리 효율 + 불변.
- 6 SQL: insert_pack / get_pack_by_slug / list_public_approved / insert_item /
  list_items / update_moderation_status. Phase 5 본격 cycle 의 actual binding.
- skeleton 단계 — 실 SQL 정의 + repository 함수 만 제공. REST endpoint binding
  은 cycle 141~150 본격 진입 시점 placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional


# ─── ENUM ──────────────────────────────────────────────────────────────────

class ModerationStatus(str, Enum):
    """emoji_packs.moderation_status 4 ENUM 정합."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DMCA_TAKEDOWN = "dmca_takedown"


class ItemModerationStatus(str, Enum):
    """emoji_pack_items.moderation_status 3 ENUM 정합."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ─── dataclass ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class EmojiPackRow:
    """emoji_packs row 도메인 객체 — 불변."""

    id: int
    owner_user_id: int
    name: str
    slug: str
    description: Optional[str]
    is_public: bool
    moderation_status: ModerationStatus
    download_count: int


@dataclass(frozen=True, slots=True)
class EmojiPackItemRow:
    """emoji_pack_items row 도메인 객체 — 불변."""

    id: int
    pack_id: int
    shortcode: str
    file_path: str
    mime_type: str
    file_size: int
    width: int
    height: int
    moderation_status: ItemModerationStatus


# ─── SQL ───────────────────────────────────────────────────────────────────

_INSERT_PACK = """
INSERT INTO emoji_packs
    (owner_user_id, name, slug, description, is_public, moderation_status)
VALUES
    (%s, %s, %s, %s, %s, %s)
"""

_SELECT_PACK_BY_SLUG = """
SELECT id, owner_user_id, name, slug, description, is_public,
       moderation_status, download_count
    FROM emoji_packs WHERE slug = %s
"""

_SELECT_PUBLIC_APPROVED = """
SELECT id, owner_user_id, name, slug, description, is_public,
       moderation_status, download_count
    FROM emoji_packs
    WHERE is_public = 1 AND moderation_status = 'approved'
    ORDER BY download_count DESC, id DESC
    LIMIT %s OFFSET %s
"""

_INSERT_ITEM = """
INSERT INTO emoji_pack_items
    (pack_id, shortcode, file_path, mime_type, file_size, width, height)
VALUES
    (%s, %s, %s, %s, %s, %s, %s)
"""

_SELECT_ITEMS_BY_PACK = """
SELECT id, pack_id, shortcode, file_path, mime_type, file_size,
       width, height, moderation_status
    FROM emoji_pack_items
    WHERE pack_id = %s
    ORDER BY id ASC
"""

_UPDATE_MODERATION_STATUS = """
UPDATE emoji_packs
    SET moderation_status = %s
    WHERE id = %s
"""


# ─── 변환 ─────────────────────────────────────────────────────────────────

def _row_to_pack(row: tuple) -> EmojiPackRow:
    """SELECT row → EmojiPackRow."""

    return EmojiPackRow(
        id=int(row[0]),
        owner_user_id=int(row[1]),
        name=str(row[2]),
        slug=str(row[3]),
        description=str(row[4]) if row[4] is not None else None,
        is_public=bool(row[5]),
        moderation_status=ModerationStatus(row[6]),
        download_count=int(row[7]),
    )


def _row_to_item(row: tuple) -> EmojiPackItemRow:
    """SELECT row → EmojiPackItemRow."""

    return EmojiPackItemRow(
        id=int(row[0]),
        pack_id=int(row[1]),
        shortcode=str(row[2]),
        file_path=str(row[3]),
        mime_type=str(row[4]),
        file_size=int(row[5]),
        width=int(row[6]),
        height=int(row[7]),
        moderation_status=ItemModerationStatus(row[8]),
    )


# ─── repository 함수 ────────────────────────────────────────────────────────

async def insert_pack(
    pool: Any,
    *,
    owner_user_id: int,
    name: str,
    slug: str,
    description: Optional[str] = None,
    is_public: bool = False,
    moderation_status: ModerationStatus = ModerationStatus.PENDING,
) -> int:
    """신규 팩 INSERT — 반환값 = lastrowid (pack id).

    Phase 5 본격 cycle 의 실 binding 의무.
    """

    if pool is None:
        raise ValueError("pool 의무")
    if owner_user_id <= 0:
        raise ValueError(f"owner_user_id 양수 의무 — {owner_user_id}")
    if not name or len(name) > 64:
        raise ValueError(f"name 1~64자 의무 — len={len(name)}")
    if not slug or len(slug) > 64:
        raise ValueError(f"slug 1~64자 의무 — len={len(slug)}")
    if description is not None and len(description) > 255:
        raise ValueError(f"description 255자 cap — len={len(description)}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _INSERT_PACK,
                (
                    owner_user_id,
                    name,
                    slug,
                    description,
                    1 if is_public else 0,
                    moderation_status.value,
                ),
            )
            await conn.commit()
            return int(cur.lastrowid)


async def get_pack_by_slug(pool: Any, slug: str) -> Optional[EmojiPackRow]:
    """slug 기준 단일 SELECT — 없으면 None."""

    if pool is None:
        raise ValueError("pool 의무")
    if not slug:
        raise ValueError("slug 빈 차단")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SELECT_PACK_BY_SLUG, (slug,))
            row = await cur.fetchone()
            return _row_to_pack(row) if row else None


async def list_public_approved(
    pool: Any, *, limit: int = 50, offset: int = 0
) -> List[EmojiPackRow]:
    """공개 + approved 팩 list — download_count DESC 우선 sort."""

    if pool is None:
        raise ValueError("pool 의무")
    if limit <= 0 or limit > 200:
        raise ValueError(f"limit 1~200 의무 — {limit}")
    if offset < 0:
        raise ValueError(f"offset 음수 차단 — {offset}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SELECT_PUBLIC_APPROVED, (limit, offset))
            rows = await cur.fetchall()
            return [_row_to_pack(r) for r in rows]


async def insert_item(
    pool: Any,
    *,
    pack_id: int,
    shortcode: str,
    file_path: str,
    mime_type: str = "image/png",
    file_size: int = 0,
    width: int = 0,
    height: int = 0,
) -> int:
    """신규 아이템 INSERT — 반환값 = lastrowid (item id)."""

    if pool is None:
        raise ValueError("pool 의무")
    if pack_id <= 0:
        raise ValueError(f"pack_id 양수 의무 — {pack_id}")
    if not shortcode or len(shortcode) > 32:
        raise ValueError(f"shortcode 1~32자 의무 — len={len(shortcode)}")
    if not file_path or len(file_path) > 255:
        raise ValueError(f"file_path 1~255자 의무 — len={len(file_path)}")
    if mime_type not in ("image/png", "image/webp", "image/gif"):
        raise ValueError(f"mime_type 3종 만 허용 — {mime_type}")
    if file_size < 0 or width < 0 or height < 0:
        raise ValueError("file_size + width + height 음수 차단")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _INSERT_ITEM,
                (pack_id, shortcode, file_path, mime_type, file_size, width, height),
            )
            await conn.commit()
            return int(cur.lastrowid)


async def list_items(pool: Any, *, pack_id: int) -> List[EmojiPackItemRow]:
    """pack_id 기준 의 아이템 list — id ASC."""

    if pool is None:
        raise ValueError("pool 의무")
    if pack_id <= 0:
        raise ValueError(f"pack_id 양수 의무 — {pack_id}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SELECT_ITEMS_BY_PACK, (pack_id,))
            rows = await cur.fetchall()
            return [_row_to_item(r) for r in rows]


async def update_moderation_status(
    pool: Any, *, pack_id: int, moderation_status: ModerationStatus
) -> int:
    """pack moderation_status UPDATE. 반환값 = rowcount."""

    if pool is None:
        raise ValueError("pool 의무")
    if pack_id <= 0:
        raise ValueError(f"pack_id 양수 의무 — {pack_id}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _UPDATE_MODERATION_STATUS, (moderation_status.value, pack_id)
            )
            await conn.commit()
            return int(cur.rowcount or 0)
