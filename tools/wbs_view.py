#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""WBS sqlite viewer — directive row tabular print (cycle 169.560 신설).

usage:
  python tools/wbs_view.py                    # 최근 30 row tail
  python tools/wbs_view.py --limit 100        # 최근 100 row
  python tools/wbs_view.py --status pending   # status filter
  python tools/wbs_view.py --cycle 169.55     # cycle prefix filter
  python tools/wbs_view.py --summary          # count summary only

정합: data/wbs.sqlite + wbs_tasks table (cycle 169.72 신설 schema).
"""

from __future__ import annotations

import argparse
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "wbs.sqlite"


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise SystemExit(f"[wbs_view] {DB_PATH} 부재 — tools/wbs_init.py 선행 의무")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _format_row(row: sqlite3.Row, max_dir_len: int = 80) -> str:
    """1 row → tabular string."""
    cycle = row["cycle"]
    status = row["status"]
    sha = (row["commit_sha"] or "")[:7]
    directive = row["directive"]
    if len(directive) > max_dir_len:
        directive = directive[: max_dir_len - 1] + "…"
    finished = (row["finished_at"] or "")[:16]
    # 한글 주석 — status emoji
    icon = {"done": "✓", "pending": "·", "in_progress": "→"}.get(status, "?")
    return f"  {icon} {cycle:<10} {sha:<8} {finished:<17} {directive}"


def main() -> None:
    ap = argparse.ArgumentParser(description="WBS sqlite viewer")
    ap.add_argument("--limit", type=int, default=30, help="row count (default 30)")
    ap.add_argument("--status", choices=["pending", "in_progress", "done"], help="status filter")
    ap.add_argument("--cycle", help="cycle prefix filter (예: 169.55)")
    ap.add_argument("--summary", action="store_true", help="count summary only")
    args = ap.parse_args()

    conn = _connect()
    cur = conn.cursor()

    # 한글 주석 — total count + status breakdown
    cur.execute("SELECT status, COUNT(*) AS cnt FROM wbs_tasks GROUP BY status")
    status_count = {r["status"]: r["cnt"] for r in cur.fetchall()}
    total = sum(status_count.values())

    print(f"\n[wbs] {DB_PATH}")
    print(f"  total={total}  done={status_count.get('done', 0)}  pending={status_count.get('pending', 0)}  in_progress={status_count.get('in_progress', 0)}\n")

    if args.summary:
        # cycle prefix 별 count (cycle 의 의 의 dot split 의 의 의 의 의 의 major group)
        cur.execute("SELECT cycle FROM wbs_tasks")
        prefixes = Counter()
        for r in cur.fetchall():
            cyc = r["cycle"]
            prefix = ".".join(cyc.split(".")[:2]) if "." in cyc else cyc
            prefixes[prefix] += 1
        print("cycle prefix group:")
        for prefix, cnt in sorted(prefixes.items(), key=lambda x: -x[1])[:15]:
            print(f"  {prefix:<10} {cnt:>4}")
        return

    # filter chain
    where = []
    params: list = []
    if args.status:
        where.append("status = ?")
        params.append(args.status)
    if args.cycle:
        where.append("cycle LIKE ?")
        params.append(f"{args.cycle}%")
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
        SELECT cycle, directive, status, finished_at, commit_sha
        FROM wbs_tasks
        {where_sql}
        ORDER BY id DESC
        LIMIT ?
    """
    cur.execute(sql, params + [args.limit])
    rows = cur.fetchall()

    print(f"recent {len(rows)} row (DESC):")
    print(f"  {'icon':<2} {'cycle':<10} {'sha':<8} {'finished_at':<17} directive")
    print(f"  {'-' * 2} {'-' * 10} {'-' * 8} {'-' * 17} {'-' * 60}")
    for row in rows:
        print(_format_row(row))
    conn.close()


if __name__ == "__main__":
    main()
