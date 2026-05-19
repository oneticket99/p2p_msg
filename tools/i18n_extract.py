#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk Phase 5 cycle 133 — i18n 한글 hardcoded string 추출 도구.

대상 — app/ui/**/*.py
방법 — ast.parse + ast.Constant value 한글 정규식 match + .ts 갱신 candidate report.
실행 — python tools/i18n_extract.py [--root app/ui] [--ts-out app/i18n/translations/tootalk_ko.ts]
출력 — stdout candidate list (file:line:string) — `.ts` direct write 차단 (skeleton 의무).
"""
from __future__ import annotations
import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Iterator

# 한글 주석 — 한글 음절 정규식 (가~힣 + 자모)
HANGUL_RE = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")


def find_hangul_constants(py_path: Path) -> Iterator[tuple[int, str]]:
    """단일 .py 의 ast.Constant value 한글 detect + (lineno, string) yield."""
    try:
        source = py_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        print(f"[i18n-extract] read 실패 — {py_path} ({err})", file=sys.stderr)
        return
    try:
        tree = ast.parse(source, filename=str(py_path))
    except SyntaxError as err:
        print(f"[i18n-extract] parse 실패 — {py_path} ({err})", file=sys.stderr)
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if HANGUL_RE.search(node.value):
                yield node.lineno, node.value


def scan_directory(root: Path) -> dict[Path, list[tuple[int, str]]]:
    """대상 디렉토리 의 .py 전체 walk + 한글 string detect."""
    result: dict[Path, list[tuple[int, str]]] = {}
    for py_path in sorted(root.rglob("*.py")):
        if "__pycache__" in py_path.parts:
            continue
        hits = list(find_hangul_constants(py_path))
        if hits:
            result[py_path] = hits
    return result


def report_candidates(scan: dict[Path, list[tuple[int, str]]]) -> int:
    """추출 결과 stdout report + 총 candidate count return."""
    total = 0
    for py_path, hits in scan.items():
        for lineno, text in hits:
            preview = text.replace("\n", "\\n")[:80]
            print(f"{py_path}:{lineno}: {preview}")
            total += 1
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TooTalk i18n 한글 hardcoded 추출")
    parser.add_argument("--root", default="app/ui", help="스캔 대상 디렉토리 — default app/ui")
    parser.add_argument(
        "--ts-out",
        default="app/i18n/translations/tootalk_ko.ts",
        help="ts 파일 출력 경로 안내용 (현재 cycle 의 direct write 차단)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"[i18n-extract] root 디렉토리 부재 — {root}", file=sys.stderr)
        return 2

    scan = scan_directory(root)
    total = report_candidates(scan)
    files = len(scan)
    print(
        f"\n[i18n-extract] 한글 string {total} 건 / {files} 파일 detect — "
        f"수동 반영 대상 ts={args.ts_out} (lrelease 실행은 tools/i18n_compile.sh 안내)",
        file=sys.stderr,
    )
    return 0 if total >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
