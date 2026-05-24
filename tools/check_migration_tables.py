#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""MIGRATION_MARIADB.md ↔ migrations SQL 테이블 정합 검사 (cycle 169.747 신설).

doc-gardener.yml Phase 3 항목 구현. 정본 §L "MIGRATION tables ↔ 모델 정합" 회수.

검사 불변식
----------
MIGRATION_MARIADB.md 안 `CREATE TABLE <name>` 으로 문서화한 테이블은
server/db/migrations/*.sql 안 실제 `CREATE TABLE` 정의에 반드시 존재해야 한다.
(doc 는 의도적 부분 reference 문서 — SQL 전체 테이블 문서화 의무 부재. forward 만 default error.)

drift 판정
---------
- forward(default) : doc 가 참조하나 SQL 부재 테이블 = drift (rename/삭제 후 doc 미갱신 detect).
- reverse(--strict): SQL 정의 단 doc 미문서화 테이블 도 drift 승격 (DB 문서 완전 차단 기준).
1건 이상 drift → exit 1 + 보고. clean → exit 0.

사용
----
    python3 tools/check_migration_tables.py            # forward only (default)
    python3 tools/check_migration_tables.py --strict   # reverse(SQL→doc 미문서화) 도 error
    python3 tools/check_migration_tables.py --json      # CI Issue 본문용 JSON (--strict 병용 가능)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# 한글 주석 — 저장소 루트 기준 경로 (본 스크립트 = tools/ 하위)
REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_DOC = REPO_ROOT / "MIGRATION_MARIADB.md"
MIGRATIONS_DIR = REPO_ROOT / "server" / "db" / "migrations"

# 한글 주석 — CREATE TABLE [IF NOT EXISTS] `name` 또는 name 형태 모두 매칭
_CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"']?([a-zA-Z_][a-zA-Z0-9_]*)[`\"']?",
    re.IGNORECASE,
)


def _extract_tables(text: str) -> set[str]:
    """본문에서 CREATE TABLE 테이블 이름 집합 추출."""
    return {m.group(1).lower() for m in _CREATE_RE.finditer(text)}


def collect_sql_tables() -> set[str]:
    """migrations/*.sql 전체에서 실제 정의 테이블 집합."""
    tables: set[str] = set()
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        tables |= _extract_tables(sql_file.read_text(encoding="utf-8"))
    return tables


def collect_doc_tables() -> set[str]:
    """MIGRATION_MARIADB.md 안 문서화 테이블 집합."""
    if not MIGRATION_DOC.exists():
        return set()
    return _extract_tables(MIGRATION_DOC.read_text(encoding="utf-8"))


def run_check() -> dict:
    """검사 실행 — drift 결과 dict 반환."""
    sql_tables = collect_sql_tables()
    doc_tables = collect_doc_tables()
    # 한글 주석 — doc 참조 단 SQL 부재 = drift (핵심 불변식 위반)
    missing_in_sql = sorted(doc_tables - sql_tables)
    # 한글 주석 — 참고용 (drift 아님) SQL 정의 단 doc 미문서화 — 부분 문서 정합상 정상
    undocumented = sorted(sql_tables - doc_tables)
    return {
        "sql_table_count": len(sql_tables),
        "doc_table_count": len(doc_tables),
        "drift": missing_in_sql,
        "undocumented": undocumented,
        "ok": len(missing_in_sql) == 0,
    }


def main() -> int:
    # 한글 주석 — --strict = reverse(SQL → doc 미문서화) 도 drift error 승격 (cycle 169.761 codex 회수)
    # default = forward(doc → SQL 부재) 만 error. MIGRATION_MARIADB.md 가 의도적 부분 reference 문서이므로.
    strict = "--strict" in sys.argv
    result = run_check()
    # 한글 주석 — strict 시 undocumented 도 ok 판정에 포함
    ok = result["ok"] and (not strict or not result["undocumented"])

    if "--json" in sys.argv:
        out = dict(result)
        out["strict"] = strict
        out["ok"] = ok
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    print(f"[check_migration_tables] SQL 정의 테이블 {result['sql_table_count']}개 "
          f"/ doc 문서화 {result['doc_table_count']}개 (strict={strict})")
    if result["undocumented"]:
        label = "ERR (strict)" if strict else "참고 (drift 아님)"
        print(f"  [{label}] doc 미문서화 SQL 테이블 {len(result['undocumented'])}개: "
              f"{', '.join(result['undocumented'])}")
    if result["drift"]:
        print("[ERR] MIGRATION drift — doc 참조 단 SQL 부재 테이블:")
        for t in result["drift"]:
            print(f"        - {t}")
        print("      MIGRATION_MARIADB.md 갱신 또는 migrations SQL 추가 의무")
    if ok:
        print("[OK] MIGRATION 테이블 정합 — doc 참조 테이블 전부 SQL 실재"
              + (" + SQL 전수 문서화 (strict)" if strict else ""))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
