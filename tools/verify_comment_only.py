#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""기능 diff 0 검증 — 한글 주석 상세화 페이즈(B-1) 안전 gate.

주석 전용 cycle 의 최상위 게이트(Exec Plan §12.1 / D2): 변경된 `.py` 파일이
**주석 + docstring + 공백/포맷만** 바뀌고 동작 라인(statement/expression/제어흐름)은
1줄도 안 바뀌었음을 보장한다.

검증 원리 — AST 비교(grep 보다 견고):
- 주석(``#``)은 Python AST 에 포함되지 않는다 → 주석만 바뀌면 AST 가 동일하다.
- docstring 은 AST 노드(Expr→Constant[str])다 → 본 페이즈는 docstring 보강을 허용하므로
  module/class/function 의 **선두 docstring 을 재귀 제거** 한 뒤 `ast.dump` 를 비교한다.
- 따라서 "주석 + docstring 외 동작 라인 변경 0" 이면 두 dump 가 정확히 일치한다.
- 멀티라인 docstring·문자열 내 ``#``·줄바꿈 재배치 등 grep 방식의 noise 에 면역이다.

사용:
    python3 tools/verify_comment_only.py                 # working tree vs HEAD 변경 .py 전수
    python3 tools/verify_comment_only.py <ref>           # <ref> vs working tree
    python3 tools/verify_comment_only.py <ref> <path...> # 특정 경로만

exit 0 = PASS(주석/docstring 만), exit 1 = FAIL(동작 라인 변경 검출), exit 2 = 사용 오류.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from typing import Optional


def _git(*args: str) -> str:
    """git 명령 실행 → stdout 문자열(실패 시 빈 문자열)."""

    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False
        )
        return out.stdout
    except OSError:
        return ""


def _strip_docstrings(node: ast.AST) -> None:
    """module/class/function 의 선두 docstring 노드를 재귀 제거(in-place).

    docstring = body[0] 이 Expr 이고 그 값이 str Constant 인 경우. 본 페이즈가 보강하는
    대상이므로 비교 전 제거해 "동작 라인" 만 남긴다.
    """
    for child in ast.walk(node):
        body = getattr(child, "body", None)
        if not isinstance(body, list) or not body:
            continue
        if not isinstance(
            child, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            # 한글 주석 — 선두 docstring 제거(보강 허용 대상이라 비교에서 배제)
            body.pop(0)


def _normalized_dump(source: str) -> Optional[str]:
    """source → docstring 제거 + ast.dump 정규화 문자열(parse 실패 None)."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    _strip_docstrings(tree)
    # 한글 주석 — 위치 속성 제외(주석 추가로 line 번호가 밀려도 동작 동일)
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def _changed_py_files(ref: str) -> list[str]:
    """ref 대비 변경된 `.py` 파일 목록(working tree 포함)."""

    raw = _git("diff", "--name-only", ref, "--", "*.py")
    return [line for line in raw.splitlines() if line.strip().endswith(".py")]


def _before_after(ref: str, path: str) -> tuple[Optional[str], Optional[str]]:
    """(ref 시점 source, working tree source). 부재 시 None."""

    before = _git("show", f"{ref}:{path}") or None
    try:
        with open(path, encoding="utf-8") as fh:
            after = fh.read()
    except OSError:
        after = None
    return before, after


def main(argv: list[str]) -> int:
    ref = argv[1] if len(argv) > 1 else "HEAD"
    paths = argv[2:] if len(argv) > 2 else _changed_py_files(ref)

    if not paths:
        print(f"[verify_comment_only] {ref} 대비 변경 .py 부재 — PASS(검증 대상 0)")
        return 0

    failures: list[str] = []
    for path in paths:
        before, after = _before_after(ref, path)
        if before is None or after is None:
            # 한글 주석 — 신규/삭제 파일은 본 검증 대상 외(주석 보강 = 기존 파일 편집)
            print(f"  [skip] {path} — 신규/삭제(주석 보강 대상 아님)")
            continue
        nb, na = _normalized_dump(before), _normalized_dump(after)
        if nb is None or na is None:
            failures.append(f"{path} — AST parse 실패(syntax 손상 의심)")
            continue
        if nb != na:
            failures.append(f"{path} — 동작 라인 변경 검출(docstring 제거 후 AST 불일치)")
        else:
            print(f"  [ok] {path} — 주석/docstring 만 변경")

    if failures:
        print("\n🔴 기능 diff 0 FAIL — 주석 전용 게이트 위반:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\n[verify_comment_only] PASS — {len(paths)} 파일 주석/docstring 만 변경(동작 불변)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
