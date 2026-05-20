#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""WBS sqlite initial schema — M6 인프라 (cycle 169.72 신설).

data/wbs.sqlite + wbs_tasks table — directive 1건 = 1 row 등록 + status 갱신.
정합: CLAUDE_HARNESS_IMPORTANT.md §A M6 + check_m6 verifier.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "wbs.sqlite"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS wbs_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle TEXT NOT NULL,
    directive TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TEXT,
    finished_at TEXT,
    commit_sha TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wbs_tasks_cycle ON wbs_tasks(cycle);
CREATE INDEX IF NOT EXISTS idx_wbs_tasks_status ON wbs_tasks(status);
"""


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        cur = conn.execute("SELECT COUNT(*) FROM wbs_tasks")
        n = cur.fetchone()[0]
        print(f"[wbs] {DB_PATH} 신설 PASS — wbs_tasks count={n}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
