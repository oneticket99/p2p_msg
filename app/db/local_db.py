# SPDX-License-Identifier: GPL-3.0-or-later
"""SQLite singleton + schema bootstrap (cycle 169.440 신설).

DB 위치 = `~/.tootalk/local.sqlite` (사용자 home 안 hidden dir).
PyInstaller bundle 내부 부재 — 사용자 별 자체 path 의무.

schema:
- messages_cache (server msg_id PK + room_id + sender_id + body + ts_ms + kind + synced_at)
- rooms_cache (room_id PK + room_code + kind + display_name + last_synced_at)
- sync_state (room_id PK + min_msg_id + max_msg_id + last_sync_ts)

migration_version table = future schema upgrade chain.
"""

from __future__ import annotations

import atexit
import logging
import sqlite3
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# DB path = 사용자 home + .tootalk dir
_DB_DIR = Path.home() / ".tootalk"
_DB_PATH = _DB_DIR / "local.sqlite"

# schema bootstrap version — 추후 migration chain 의 의무
_SCHEMA_VERSION = 1

_SCHEMA_DDL = [
    """
    CREATE TABLE IF NOT EXISTS messages_cache (
        msg_id       INTEGER PRIMARY KEY,            -- server messages.id (mariadb msg PK)
        room_id      INTEGER NOT NULL,               -- room 식별 (rooms.id)
        sender_id    INTEGER NOT NULL,               -- users.id
        kind         TEXT NOT NULL DEFAULT 'text',   -- text/file/system
        body         TEXT,                            -- 텍스트 본문 (file kind = NULL)
        file_id      TEXT,                            -- 파일 식별 (text kind = NULL)
        ts_ms        INTEGER NOT NULL,               -- UNIX epoch ms (UTC)
        client_uuid  TEXT,                            -- 클라이언트 uuid (cycle 156)
        is_self      INTEGER NOT NULL DEFAULT 0,     -- 1 = self echo
        synced_at_ms INTEGER NOT NULL                -- local cache 저장 ts
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_messages_cache_room_ts ON messages_cache(room_id, ts_ms DESC)",
    "CREATE INDEX IF NOT EXISTS idx_messages_cache_client_uuid ON messages_cache(client_uuid)",
    """
    CREATE TABLE IF NOT EXISTS rooms_cache (
        room_id           INTEGER PRIMARY KEY,        -- mariadb rooms.id
        room_code         TEXT,
        kind              TEXT NOT NULL DEFAULT 'direct',
        display_name      TEXT,
        last_synced_at_ms INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sync_state (
        room_id          INTEGER PRIMARY KEY,         -- rooms.id (FK 부재 — cache 의존성 차단)
        min_msg_id       INTEGER,                     -- local cache 안 최소 msg_id
        max_msg_id       INTEGER,                     -- local cache 안 최대 msg_id
        last_sync_at_ms  INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS migration_version (
        version          INTEGER PRIMARY KEY,
        applied_at_ms    INTEGER NOT NULL
    )
    """,
]


def _ensure_dir() -> None:
    """`.tootalk` 디렉토리 생성 (사용자 home + 0700 권한)."""
    try:
        _DB_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    except Exception as exc:  # noqa: BLE001
        log.warning("[local_db] dir mkdir 실패 — %r", exc)


def _bootstrap_schema(conn: sqlite3.Connection) -> None:
    """schema DDL 실행 + version row insert (idempotent)."""
    cur = conn.cursor()
    for ddl in _SCHEMA_DDL:
        cur.execute(ddl)
    # version row idempotent insert
    import time as _time
    cur.execute(
        "INSERT OR IGNORE INTO migration_version (version, applied_at_ms) VALUES (?, ?)",
        (_SCHEMA_VERSION, int(_time.time() * 1000)),
    )
    conn.commit()


_conn: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """SQLite singleton connection + schema bootstrap.

    Returns
    -------
    sqlite3.Connection
        WAL mode + foreign_keys=ON + row_factory=Row.
    """
    global _conn
    if _conn is not None:
        return _conn
    _ensure_dir()
    log.info("[local_db] connect path=%s", _DB_PATH)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL mode = concurrent read + write 의 안전 (단일 process 라도 권장)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    _bootstrap_schema(conn)
    _conn = conn
    return conn


def close_connection() -> None:
    """singleton close (app shutdown 시점 호출 의무)."""
    global _conn
    if _conn is not None:
        try:
            _conn.close()
        except Exception:  # noqa: BLE001
            pass
        _conn = None


# 한글 주석 — cycle 169.849: 인터프리터 종료 시 싱글톤 결정적 close 보장.
# app shutdown 에서 close_connection 명시 호출이 누락된 경로(특히 pytest process
# 종료)에서 sqlite3.Connection 이 GC 의 __del__ 로 닫히며 발생하던
# `ResourceWarning: unclosed database` (codex 평가 §8-1)를 회수. _conn 미오픈 시
# None 가드로 no-op — 부작용 없음.
atexit.register(close_connection)


def get_db_path() -> Path:
    """DB 경로 반환 (테스트 또는 backup chain)."""
    return _DB_PATH
