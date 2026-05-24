#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""meta_enforce.py — enforcement layer 자기검증 (L5).

정본 문서가 말하는 도구와 CI gate 가 실제로 존재하고, soft-fail 로 약화되지
않았는지 검사한다. 본 스크립트는 기존 lint 를 대체하지 않고, lint 자체의
실재성과 차단력을 감시한다.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
CI = ROOT / ".github" / "workflows" / "ci.yml"
DOC_GARDENER = ROOT / ".github" / "workflows" / "doc-gardener.yml"
HISTORY = ROOT / "History.md"
README = ROOT / "README.md"

REQUIRED_FILES = [
    "tools/doc-lint.sh",
    "tools/md_agents.py",
    "tools/hook_check_bpe_token_input.sh",
    "tools/hook_telegram_report_stop.sh",
    ".github/workflows/ci.yml",
    ".github/workflows/docs-lint.yml",
    ".github/workflows/doc-gardener.yml",
]


def _read(path: Path) -> str:
    """UTF-8 text read helper."""
    return path.read_text(encoding="utf-8")


def _run_git_ls_files() -> List[str]:
    """추적 파일 목록 조회 — .git 상태 의존 검사용."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git ls-files 실패: {result.stderr.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _run_git_text(args: List[str]) -> str:
    """git command stdout helper."""
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패: {result.stderr.strip()}")
    return result.stdout.strip()


def check_required_files() -> Tuple[bool, str]:
    """정본과 CI가 참조하는 enforcement 파일 실재성 검증."""
    missing = [rel for rel in REQUIRED_FILES if not (ROOT / rel).is_file()]
    if missing:
        return False, "필수 enforcement 파일 부재: " + ", ".join(missing)
    return True, f"필수 enforcement 파일 {len(REQUIRED_FILES)}개 확인"


def check_root_markdown_freeze() -> Tuple[bool, str]:
    """루트 마크다운 18개 동결 상태 검증."""
    root_md = sorted(p.name for p in ROOT.glob("*.md") if p.is_file())
    if len(root_md) != 18:
        return False, f"루트 .md {len(root_md)}개 — 기대 18개: {root_md}"
    return True, "루트 .md 18개 동결 확인"


def check_ci_soft_fail() -> Tuple[bool, str]:
    """ci.yml 안 soft-fail 설정 차단."""
    text = _read(CI)
    forbidden = "continue-on-error: true"
    # 한글 주석 — 설명 주석 안 문자열은 허용하고 실제 YAML key 만 차단한다.
    active_lines = [
        line
        for line in text.splitlines()
        if not line.lstrip().startswith("#")
    ]
    if any(forbidden in line for line in active_lines):
        return False, f"ci.yml 안 soft-fail 설정 발견: {forbidden}"
    return True, "ci.yml soft-fail 설정 없음"


def check_ci_meta_job() -> Tuple[bool, str]:
    """ci.yml 안 meta-enforcement job 자기등록 확인."""
    text = _read(CI)
    required_tokens = [
        "meta-enforcement",
        "python3 tools/meta_enforce.py",
    ]
    missing = [token for token in required_tokens if token not in text]
    if missing:
        return False, "ci.yml meta-enforcement 등록 누락: " + ", ".join(missing)
    return True, "ci.yml meta-enforcement job 확인"


def check_ci_m3_uses_md_agents() -> Tuple[bool, str]:
    """CI M3 job 이 로컬 하네스와 같은 검증기를 쓰는지 확인."""
    text = _read(CI)
    required = "python3 tools/md_agents.py --history-only"
    if required not in text:
        return False, f"ci.yml M3 job 이 md_agents history 검증기를 호출하지 않음: {required}"
    stale_python = "python tools/md_agents.py --history-only"
    if stale_python in text:
        return False, "ci.yml M3 job 안 python 명령 의존 잔존"
    forbidden = "grep -E '^## Phase'"
    if forbidden in text:
        return False, "ci.yml M3 job 안 stale Phase 헤더 grep 검증 잔존"
    return True, "ci.yml M3 job md_agents history 검증기 사용"


def check_latest_cycle_documented() -> Tuple[bool, str]:
    """최신 commit subject 의 cycle marker 가 README/History 에 반영됐는지 검증."""
    subject = _run_git_text(["log", "-1", "--pretty=%s"])
    matches = re.findall(r"cycle\s*(\d+)\.(\d+)(?:[-~](\d+))?", subject)
    if not matches:
        return True, "최신 commit subject 안 cycle marker 없음 — freshness 검사 skip"
    major, start, end = matches[-1]
    labels = [f"{major}.{start}"]
    if end:
        labels.extend([f"{major}.{end}", f"{major}.{start}~{end}", f"{major}.{start}-{end}"])
    history_text = _read(HISTORY)
    readme_text = _read(README)
    missing = []
    if not any(label in history_text for label in labels):
        missing.append("History.md")
    if not any(label in readme_text for label in labels):
        missing.append("README.md")
    if missing:
        return False, f"최신 cycle marker 문서 반영 누락: {', '.join(missing)} / labels={labels}"
    return True, f"최신 cycle marker 문서 반영 확인: {labels[-1]}"


def check_doc_gardener_auto_push() -> Tuple[bool, str]:
    """doc-gardener workflow 의 자동 commit/push/PR 경로 복구 상태 검증."""
    text = _read(DOC_GARDENER)
    required_tokens = [
        "contents: write",
        "pull-requests: write",
        "git commit -m",
        "git push origin \"$BRANCH\"",
        "gh pr create",
        "auto/doc-gardener-",
    ]
    missing = [token for token in required_tokens if token not in text]
    if missing:
        return False, "doc-gardener 자동 commit/push/PR 경로 누락: " + ", ".join(missing)
    forbidden = "git push origin main"
    if forbidden in text:
        return False, "doc-gardener main 직접 push 발견"
    return True, "doc-gardener 자동 보정 branch push + PR 경로 확인"


def check_tracked_noise_files() -> Tuple[bool, str]:
    """macOS/IDE 잡음 파일이 git 추적 대상인지 검증."""
    tracked = _run_git_ls_files()
    noise = [
        path
        for path in tracked
        if path.endswith(".DS_Store") or path.endswith("settings.local.json")
    ]
    if noise:
        return False, "추적 금지 잡음 파일 발견: " + ", ".join(noise)
    return True, "추적 금지 잡음 파일 없음"


def main() -> int:
    """L5 검사 누계 실행."""
    checks: List[Tuple[str, Callable[[], Tuple[bool, str]]]] = [
        ("required-files", check_required_files),
        ("root-markdown-freeze", check_root_markdown_freeze),
        ("ci-soft-fail", check_ci_soft_fail),
        ("ci-meta-job", check_ci_meta_job),
        ("ci-m3-md-agents", check_ci_m3_uses_md_agents),
        ("latest-cycle-documented", check_latest_cycle_documented),
        ("doc-gardener-auto-push", check_doc_gardener_auto_push),
        ("tracked-noise-files", check_tracked_noise_files),
    ]
    failures: List[str] = []
    for name, fn in checks:
        try:
            ok, message = fn()
        except Exception as exc:  # noqa: BLE001
            ok, message = False, f"검사 예외: {exc}"
        label = "PASS" if ok else "FAIL"
        print(f"[{label}] {name}: {message}")
        if not ok:
            failures.append(name)
    if failures:
        print("meta-enforcement 실패: " + ", ".join(failures), file=sys.stderr)
        return 1
    print("meta-enforcement 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
