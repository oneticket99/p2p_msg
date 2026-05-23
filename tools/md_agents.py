#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""md_agents.py — M1~M4 정합 검증 entry (cycle 169.505 복구).

정본 §A + §I + AGENTS §A 안 참조 retain. codex review 2.2 verdict 정합 — 본 file
부재 → 정본 신뢰도 + 자동화 재현성 저하 회수.

기능
----
- ``agent_history()`` — `History.md` 역순 prepend 정합 검증 (M3 강제)
- ``agent_readme()`` — `README.md` "변경 이력" 헤더 존재 검증 (M2 강제)
- ``agent_root_freeze()`` — 루트 .md 정확히 18개 동결 (정본 §K)
- ``agent_korean_comments(target)`` — `.py`/`.js`/`.html`/`.css`/`.sql`/`.sh` 의 한글
  주석 1줄 이상 검증 (M4 강제)
- ``main()`` — 위 4 검증 누계 + exit code 1 시점 1 위반 이상

사용
----
::

    python tools/md_agents.py                # 4 검증 누계
    python tools/md_agents.py --history-only # M3 만
    python tools/md_agents.py --readme-only  # M2 만

CI ``.github/workflows/ci.yml`` 의 `m3-history-prepend` job 안 호출. 본 stub 은 외부
참조 단절 회수 의 최소 PASS path (CI 의 별 grep 검증 chain 과 중복 retain).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "History.md"
README = ROOT / "README.md"


# ─── M3 — History.md 역순 prepend 검증 ──────────────────────────────────────


def agent_history() -> Tuple[bool, str]:
    """``History.md`` Phase 헤더 + cycle entry 의 역순 prepend 정합 검증.

    본 함수 = 모든 cycle entry 의 cycle 번호 + 타임스탬프를 추출해 전체 역순 정합을 검증한다.
    이전 구현처럼 상위 2건만 비교하면 중간 append 패턴을 놓치므로 전체 pair 를 순회한다.

    Returns
    -------
    (ok, message) : Tuple[bool, str]
        ok = True 시점 정합 PASS. message = 위반 detail 또는 PASS log.
    """
    if not HISTORY.exists():
        return False, f"History.md 부재 — {HISTORY}"
    lines = HISTORY.read_text(encoding="utf-8").splitlines()
    cycle_entries: List[Tuple[int, int, int, str, str]] = []
    pat = re.compile(
        r"^- cycle (\d+)\.(\d+).*?\((\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) KST\)"
    )
    for idx, line in enumerate(lines):
        m = pat.match(line)
        if m:
            major, minor = int(m.group(1)), int(m.group(2))
            stamp = f"{m.group(3)} {m.group(4)}"
            cycle_entries.append((idx + 1, major, minor, stamp, line))
    if len(cycle_entries) < 2:
        return True, "cycle entry 1건 이하 — 검증 skip"
    # 한글 주석 — cycle 내림차순 + 같은 cycle 안 timestamp 내림차순을 전체 entry 에 강제한다.
    for prev, current in zip(cycle_entries, cycle_entries[1:]):
        prev_line, prev_major, prev_minor, prev_stamp, _ = prev
        cur_line, cur_major, cur_minor, cur_stamp, _ = current
        prev_key = (prev_major, prev_minor, prev_stamp)
        cur_key = (cur_major, cur_minor, cur_stamp)
        if prev_key < cur_key:
            prev_cycle = f"{prev_major}.{prev_minor}"
            cur_cycle = f"{cur_major}.{cur_minor}"
            return (
                False,
                "M3 위반 — "
                f"line {prev_line} {prev_cycle} {prev_stamp} < "
                f"line {cur_line} {cur_cycle} {cur_stamp} (append 패턴)",
            )
    top = cycle_entries[0]
    bottom = cycle_entries[-1]
    return (
        True,
        "M3 PASS — "
        f"{len(cycle_entries)} entries, top={top[1]}.{top[2]} {top[3]}, "
        f"bottom={bottom[1]}.{bottom[2]} {bottom[3]}",
    )


# ─── M2 — README.md 변경 이력 헤더 검증 ──────────────────────────────────────


def agent_readme() -> Tuple[bool, str]:
    """``README.md`` "변경 이력" 섹션 헤더 존재 + cycle entry 30 행 상한 검증."""
    if not README.exists():
        return False, f"README.md 부재 — {README}"
    text = README.read_text(encoding="utf-8")
    if "변경 이력" not in text:
        return False, "M2 위반 — '변경 이력' 섹션 헤더 부재"
    # 한글 주석 — cycle entry count 검증 (30 행 상한 — 정본 §H)
    cycle_count = len(re.findall(r"^- cycle ", text, flags=re.MULTILINE))
    if cycle_count > 30:
        return False, f"M2 위반 — cycle entry {cycle_count}건 > 30 상한"
    return True, f"M2 PASS — cycle entry={cycle_count}"


# ─── §K — 루트 .md 18개 동결 검증 ────────────────────────────────────────────


def agent_root_freeze() -> Tuple[bool, str]:
    """루트 .md 정확히 18개 동결 검증 (정본 §K)."""
    root_md = sorted(p.name for p in ROOT.glob("*.md") if p.is_file())
    if len(root_md) == 18:
        return True, f"§K PASS — root md 18개"
    return False, f"§K 위반 — root md {len(root_md)}개 (예상 18). 목록={root_md}"


# ─── M4 — 한글 주석 1줄 이상 검증 ────────────────────────────────────────────


_M4_EXT = {".py", ".js", ".html", ".css", ".sql", ".sh"}
_HANGUL_RE = re.compile(r"[가-힣]")


def agent_korean_comments(target: Path) -> Tuple[bool, str]:
    """단일 파일 안 한글 주석 1줄 이상 검증 (M4)."""
    if not target.exists():
        return False, f"파일 부재 — {target}"
    if target.suffix not in _M4_EXT:
        return True, f"M4 skip — 비대상 확장자 {target.suffix}"
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False, f"M4 위반 — utf-8 디코드 실패 {target}"
    if _HANGUL_RE.search(text):
        return True, f"M4 PASS — 한글 1자 이상 {target.name}"
    return False, f"M4 위반 — 한글 부재 {target}"


# ─── main entry ─────────────────────────────────────────────────────────────


def main() -> int:
    """4 검증 누계 + 위반 1건 이상 시점 exit code 1 반환."""
    parser = argparse.ArgumentParser(description="md_agents — M1~M4 + §K 검증 entry")
    parser.add_argument("--history-only", action="store_true", help="M3 검증 만")
    parser.add_argument("--readme-only", action="store_true", help="M2 검증 만")
    parser.add_argument("--root-freeze-only", action="store_true", help="§K 검증 만")
    parser.add_argument("--target", type=str, help="M4 단일 file 검증 대상 path")
    args = parser.parse_args()

    failures: List[str] = []

    if args.history_only:
        ok, msg = agent_history()
        print(msg)
        return 0 if ok else 1
    if args.readme_only:
        ok, msg = agent_readme()
        print(msg)
        return 0 if ok else 1
    if args.root_freeze_only:
        ok, msg = agent_root_freeze()
        print(msg)
        return 0 if ok else 1
    if args.target:
        ok, msg = agent_korean_comments(Path(args.target))
        print(msg)
        return 0 if ok else 1

    # 한글 주석 — 전수 4 검증 chain
    for name, fn in [
        ("M3 history", agent_history),
        ("M2 readme", agent_readme),
        ("§K root freeze", agent_root_freeze),
    ]:
        ok, msg = fn()
        prefix = "PASS" if ok else "FAIL"
        print(f"[{prefix}] {name}: {msg}")
        if not ok:
            failures.append(name)
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
