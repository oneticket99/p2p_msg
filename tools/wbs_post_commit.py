#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""post-commit WBS row 자동 등록 — M6 enforcement (cycle 169.787 신설).

Codex 전면평가 P0 — "post-commit WBS hook 미설치" 회수. git post-commit hook 에서
호출되어 직전 commit 의 메시지에서 `cycle169.N` 패턴을 추출, `data/wbs.sqlite`
`wbs_tasks` 에 1행 등록(M6 "directive 1건 = wbs_tasks 1행"). 중복 cycle 은 skip.

설치: `bash tools/install_wbs_hook.sh` (.git/hooks/post-commit 생성).
`data/` 는 gitignored 라 wbs.sqlite 는 local only — 본 hook 도 local 자동화 보조.
"""

from __future__ import annotations

import datetime
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DB = _REPO / "data" / "wbs.sqlite"
# 한글 주석 — commit subject 의 cycle169.N (N = 정수 또는 169.NNN 소수 형태)
_CYCLE_RE = re.compile(r"cycle169\.(\d+)")


def _head_commit() -> tuple[str, str]:
    """직전 commit 의 (short sha, subject) 반환."""

    out = subprocess.run(
        ["git", "-C", str(_REPO), "log", "-1", "--format=%h\t%s"],
        capture_output=True, text=True,
    ).stdout.strip()
    sha, _, subject = out.partition("\t")
    return sha, subject


def register() -> int:
    """직전 commit 의 cycle 을 wbs_tasks 에 등록 (멱등). 반환 = 등록 수(0/1)."""

    if not _DB.exists():
        return 0
    sha, subject = _head_commit()
    m = _CYCLE_RE.search(subject)
    if not m:
        return 0
    cycle = f"169.{m.group(1)}"
    con = sqlite3.connect(str(_DB))
    cur = con.cursor()
    try:
        exists = cur.execute(
            "SELECT 1 FROM wbs_tasks WHERE cycle = ?", (cycle,)
        ).fetchone()
        if exists:
            return 0
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # 한글 주석 — finished_at 채움 (status=completed 시맨틱 + wbs_view 표시 컬럼 정합)
        cur.execute(
            "INSERT INTO wbs_tasks (cycle, directive, status, commit_sha, "
            "started_at, finished_at, created_at, updated_at) "
            "VALUES (?, ?, 'completed', ?, ?, ?, ?, ?)",
            (cycle, subject[:200], sha, now, now, now, now),
        )
        con.commit()
        return 1
    finally:
        con.close()


if __name__ == "__main__":
    # 한글 주석 — hook 실패가 commit 을 막지 않도록 예외는 stderr 로만 보고
    try:
        n = register()
        if n:
            print("[wbs] post-commit row 등록 완료")
    except Exception as exc:  # noqa: BLE001 — hook 은 commit 차단 금지
        print(f"[wbs] post-commit 등록 skip — {exc!r}", file=sys.stderr)
