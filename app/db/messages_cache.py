# SPDX-License-Identifier: GPL-3.0-or-later
"""messages_cache repository — local SQLite 안 메시지 영속 (cycle 169.440 신설).

write-through path:
- send chain (REST POST PASS 후) + receive chain (server fetch 후) → insert_message
- local cache + MariaDB 동시 정합

read path:
- 1차 = local cache (paginated DESC ts)
- 2차 = MariaDB fetch (lazy-load 시점 scroll-up trigger) — 별 cycle 의무
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.db.local_db import get_connection

log = logging.getLogger(__name__)


def insert_message(
    *,
    msg_id: int,
    room_id: int,
    sender_id: int,
    kind: str = "text",
    body: Optional[str] = None,
    file_id: Optional[str] = None,
    ts_ms: Optional[int] = None,
    client_uuid: Optional[str] = None,
    is_self: bool = False,
) -> None:
    """단일 message INSERT (write-through). 중복 msg_id = IGNORE.

    Parameters
    ----------
    msg_id : int
        server messages.id (mariadb PK). 0 미만 = client_uuid 만 retain (전송 직후 cycle).
    room_id : int
        rooms.id.
    sender_id : int
        users.id.
    kind : str
        text/file/system.
    body : str | None
        text/system 본문.
    file_id : str | None
        file kind 시점 file 식별.
    ts_ms : int | None
        UNIX epoch ms. None = 현재 시각.
    client_uuid : str | None
        클라이언트 uuid (message_protocol payload.id 정합).
    is_self : bool
        self echo flag.
    """
    if msg_id < 0:
        raise ValueError(f"msg_id 음수 차단 — {msg_id}")
    if room_id <= 0:
        raise ValueError(f"room_id 양수 의무 — {room_id}")
    if sender_id <= 0:
        raise ValueError(f"sender_id 양수 의무 — {sender_id}")
    if kind not in ("text", "file", "system"):
        raise ValueError(f"kind ENUM 의무 — {kind}")
    if ts_ms is None:
        ts_ms = int(time.time() * 1000)

    sql = (
        "INSERT OR IGNORE INTO messages_cache "
        "(msg_id, room_id, sender_id, kind, body, file_id, ts_ms, client_uuid, is_self, synced_at_ms) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    conn = get_connection()
    try:
        conn.execute(
            sql,
            (
                msg_id, room_id, sender_id, kind, body, file_id, ts_ms,
                client_uuid, 1 if is_self else 0, int(time.time() * 1000),
            ),
        )
        conn.commit()
        # sync_state 갱신 (min/max msg_id 추적)
        _update_sync_state(conn, room_id, msg_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("[messages_cache] insert 실패 — %r", exc)


def list_messages_by_room(
    *,
    room_id: int,
    limit: int = 50,
    before_msg_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """room 안 메시지 list (ts DESC). lazy-load chain 의 1차 read.

    Parameters
    ----------
    room_id : int
        rooms.id.
    limit : int
        max rows (cap 200).
    before_msg_id : int | None
        cursor — 본 msg_id 미만 fetch (scroll-up lazy load chain). None = latest.

    Returns
    -------
    list[dict]
        sqlite Row → dict list. ts_ms DESC 정렬.
    """
    if room_id <= 0:
        raise ValueError(f"room_id 양수 의무 — {room_id}")
    if limit <= 0 or limit > 200:
        raise ValueError(f"limit 1~200 의무 — {limit}")

    conn = get_connection()
    if before_msg_id is not None:
        sql = (
            "SELECT * FROM messages_cache WHERE room_id = ? AND msg_id < ? "
            "ORDER BY ts_ms DESC LIMIT ?"
        )
        params = (room_id, before_msg_id, limit)
    else:
        sql = (
            "SELECT * FROM messages_cache WHERE room_id = ? "
            "ORDER BY ts_ms DESC LIMIT ?"
        )
        params = (room_id, limit)
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:  # noqa: BLE001
        log.warning("[messages_cache] list 실패 — %r", exc)
        return []


def get_min_msg_id(room_id: int) -> Optional[int]:
    """room 안 local cache 최소 msg_id (lazy-load cursor base).

    None = cache 부재.
    """
    if room_id <= 0:
        raise ValueError(f"room_id 양수 의무 — {room_id}")
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT min_msg_id FROM sync_state WHERE room_id = ?",
            (room_id,),
        ).fetchone()
        return int(row["min_msg_id"]) if row and row["min_msg_id"] is not None else None
    except Exception as exc:  # noqa: BLE001
        log.warning("[messages_cache] min_msg_id 실패 — %r", exc)
        return None


def get_max_msg_id(room_id: int) -> Optional[int]:
    """room 안 local cache 최대 msg_id (incremental sync chain base)."""
    if room_id <= 0:
        raise ValueError(f"room_id 양수 의무 — {room_id}")
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT max_msg_id FROM sync_state WHERE room_id = ?",
            (room_id,),
        ).fetchone()
        return int(row["max_msg_id"]) if row and row["max_msg_id"] is not None else None
    except Exception as exc:  # noqa: BLE001
        log.warning("[messages_cache] max_msg_id 실패 — %r", exc)
        return None


def _update_sync_state(conn: Any, room_id: int, msg_id: int) -> None:
    """sync_state upsert — min/max msg_id 갱신 (insert_message 호출 직후 chain)."""
    if msg_id <= 0:
        return  # uuid-only retain 시점 skip
    now_ms = int(time.time() * 1000)
    # 한글 주석 — UPSERT 패턴 (SQLite 3.24+ ON CONFLICT)
    sql = (
        "INSERT INTO sync_state (room_id, min_msg_id, max_msg_id, last_sync_at_ms) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(room_id) DO UPDATE SET "
        "  min_msg_id = CASE WHEN min_msg_id IS NULL OR ? < min_msg_id THEN ? ELSE min_msg_id END, "
        "  max_msg_id = CASE WHEN max_msg_id IS NULL OR ? > max_msg_id THEN ? ELSE max_msg_id END, "
        "  last_sync_at_ms = ?"
    )
    try:
        conn.execute(sql, (room_id, msg_id, msg_id, now_ms, msg_id, msg_id, msg_id, msg_id, now_ms))
    except Exception as exc:  # noqa: BLE001
        log.debug("[messages_cache] sync_state upsert 실패 — %r", exc)


def delete_room_messages(room_id: int) -> int:
    """room 안 모든 메시지 삭제 (대화 내용 비우기 chain). 반환값 = 삭제 rowcount."""
    if room_id <= 0:
        raise ValueError(f"room_id 양수 의무 — {room_id}")
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM messages_cache WHERE room_id = ?", (room_id,))
        conn.execute("DELETE FROM sync_state WHERE room_id = ?", (room_id,))
        conn.commit()
        return int(cur.rowcount or 0)
    except Exception as exc:  # noqa: BLE001
        log.warning("[messages_cache] delete_room_messages 실패 — %r", exc)
        return 0


def count_messages(room_id: int) -> int:
    """room 안 cache 메시지 수 (debug + sync verify base)."""
    if room_id <= 0:
        raise ValueError(f"room_id 양수 의무 — {room_id}")
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM messages_cache WHERE room_id = ?",
            (room_id,),
        ).fetchone()
        return int(row["c"]) if row else 0
    except Exception as exc:  # noqa: BLE001
        log.warning("[messages_cache] count 실패 — %r", exc)
        return 0
