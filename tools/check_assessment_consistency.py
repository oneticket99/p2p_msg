#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""current-project-review.md 최신성/정합성 검사.

평가 문서가 다음 세션 작업 큐의 진입점이므로, 최신 commit/WBS/MIGRATION
상태와 반대로 말하는 문장을 CI 단계에서 차단한다.
"""

from __future__ import annotations

import re
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "docs" / "assessments" / "current-project-review.md"
WBS_DB = ROOT / "data" / "wbs.sqlite"


@dataclass(frozen=True)
class GitHead:
    """최신 commit 식별 정보."""

    sha: str
    subject: str
    cycle: str | None


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    """저장소 루트 기준 subprocess 실행."""

    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _head() -> GitHead:
    """HEAD commit 의 short sha, subject, cycle marker 추출."""

    result = _run(["git", "log", "-1", "--format=%h\t%s"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    sha, _, subject = result.stdout.strip().partition("\t")
    cycle = _extract_cycle(subject)
    return GitHead(sha=sha, subject=subject, cycle=cycle)


def _extract_cycle(text: str) -> str | None:
    """`cycle169.793` 또는 `cycle 169.793` 형식 추출."""

    match = re.search(r"cycle\s*169\.(\d+)", text)
    if not match:
        return None
    return f"169.{match.group(1)}"


def _wbs_head_completed(head_sha: str) -> bool:
    """WBS sqlite 가 존재할 때 HEAD row completed 여부 확인."""

    if not WBS_DB.exists():
        return False
    con = sqlite3.connect(str(WBS_DB))
    try:
        row = con.execute(
            "SELECT status, commit_sha FROM wbs_tasks ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        con.close()
    if not row:
        return False
    status, commit_sha = row
    return status == "completed" and str(commit_sha or "").startswith(head_sha)


def _migration_strict_ok() -> bool:
    """MIGRATION strict 검사가 통과하는지 확인."""

    result = _run(["python3", "tools/check_migration_tables.py", "--strict"])
    return result.returncode == 0


def _contains_any(text: str, patterns: list[str]) -> list[str]:
    """정규식 패턴 매칭 목록 반환."""

    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            hits.append(pattern)
    return hits


def check() -> list[str]:
    """평가 문서 모순 목록 반환."""

    text = REVIEW.read_text(encoding="utf-8")
    head = _head()
    failures: list[str] = []

    if head.cycle and head.cycle not in text:
        failures.append(
            f"current-project-review.md 최신 cycle 누락: HEAD={head.cycle} "
            f"({head.sha})"
        )

    if _wbs_head_completed(head.sha):
        # 한글 주석 — WBS가 HEAD completed 인데 평가 문서가 과거 P0 queue 를 유지하면 다음 세션이 잘못 출발한다.
        patterns = [
            r"M6[^\n]{0,120}PARTIAL",
            r"M6[^\n]{0,120}enforcement[^\n]{0,120}마감",
            r"post-commit WBS hook[^\n]{0,120}(설치|필요|결정)",
            r"status[^\n]{0,80}(done|completed)[^\n]{0,80}통일",
        ]
        hits = _contains_any(text, patterns)
        if hits:
            failures.append("WBS completed 상태와 충돌하는 평가 문장: " + ", ".join(hits))

    if _migration_strict_ok():
        # 한글 주석 — strict PASS 이후에도 DB strict 를 잔존 작업으로 남기면 반복 처리된다.
        patterns = [
            r"MIGRATION[^\n]{0,120}strict[^\n]{0,120}(잔존|필요|남아|올리는 시점)",
            r"DB/배포 정합[^\n]{0,240}MIGRATION",
            r"tools/check_migration_tables\.py --strict[^\n]{0,120}(warning|CI gate)",
        ]
        hits = _contains_any(text, patterns)
        if hits:
            failures.append("MIGRATION strict PASS 상태와 충돌하는 평가 문장: " + ", ".join(hits))

    return failures


def main() -> int:
    """CLI entry."""

    failures = check()
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}", file=sys.stderr)
        return 1
    print("[PASS] current-project-review.md assessment consistency")
    return 0


if __name__ == "__main__":
    sys.exit(main())
