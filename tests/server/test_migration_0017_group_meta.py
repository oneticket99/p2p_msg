# SPDX-License-Identifier: GPL-3.0-or-later
"""마이그레이션 0017 group_roles_meta isolated 단위 테스트 — cycle 169.820 모델 단계.

DB 접속 없이 SQL DDL 파일 + MIGRATION_MARIADB.md 문서 정합을 정적 파싱으로
검증한다 (텔레그램 그룹 관리 모델→REST→UI 의 모델 단계).

검증 항목:
- peers.role ENUM owner/admin/member 3-tier 확장 (admin 추가).
- rooms 에 name/description/avatar_ref 3 컬럼 추가.
- 각 변경 컬럼 COMMENT 존재 (필드 주석 5요소 가드레일 정합).
- MIGRATION_MARIADB.md 가 0017 ALTER 변경을 문서화.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# 한글 주석 — 저장소 루트 (본 파일 = tests/server/ 하위)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = _REPO_ROOT / "server" / "db" / "migrations" / "0017_group_roles_meta.sql"
_DOC = _REPO_ROOT / "MIGRATION_MARIADB.md"


@pytest.fixture(scope="module")
def sql_text() -> str:
    """마이그레이션 0017 SQL 원문."""
    assert _MIGRATION.exists(), f"마이그레이션 부재: {_MIGRATION}"
    return _MIGRATION.read_text(encoding="utf-8")


class TestPeersRoleEnum:
    """peers.role ENUM 3-tier 확장 검증."""

    def test_role_enum_has_admin(self, sql_text: str) -> None:
        # 한글 주석 — owner/admin/member 3값 ENUM 정의 존재 (quote 제거 후 비교)
        normalized = sql_text.replace("'", "").lower()
        assert "enum(owner, admin, member)" in normalized

    def test_role_modify_targets_peers(self, sql_text: str) -> None:
        assert "ALTER TABLE peers" in sql_text
        assert "MODIFY COLUMN role" in sql_text

    def test_role_default_member_retained(self, sql_text: str) -> None:
        # 한글 주석 — 기존 row 무손상 위해 DEFAULT 'member' 불변
        assert "DEFAULT 'member'" in sql_text

    def test_role_has_comment(self, sql_text: str) -> None:
        # 한글 주석 — role 변경 COMMENT 5요소 (용도/제약/출처/참조/민감도)
        for token in ("용도=", "제약=", "출처=", "참조=", "민감도="):
            assert token in sql_text


class TestRoomsMetaColumns:
    """rooms 그룹 메타 3 컬럼 추가 검증."""

    @pytest.mark.parametrize("col", ["name", "description", "avatar_ref"])
    def test_column_added(self, sql_text: str, col: str) -> None:
        assert f"ADD COLUMN {col} " in sql_text

    def test_alter_targets_rooms(self, sql_text: str) -> None:
        assert "ALTER TABLE rooms" in sql_text

    def test_columns_not_null_default_empty(self, sql_text: str) -> None:
        # 한글 주석 — 기존 row 안전 위해 NOT NULL DEFAULT '' (빈 문자열) 채움
        assert sql_text.count("NOT NULL DEFAULT ''") >= 3

    @pytest.mark.parametrize(
        "col,limit",
        [("name", "VARCHAR(128)"), ("description", "VARCHAR(255)"), ("avatar_ref", "VARCHAR(255)")],
    )
    def test_column_type(self, sql_text: str, col: str, limit: str) -> None:
        assert f"ADD COLUMN {col} {limit}" in sql_text


class TestMigrationDocSync:
    """MIGRATION_MARIADB.md ↔ 0017 정합 검증."""

    @pytest.fixture(scope="class")
    def doc_text(self) -> str:
        assert _DOC.exists()
        return _DOC.read_text(encoding="utf-8")

    def test_doc_range_includes_0017(self, doc_text: str) -> None:
        # 한글 주석 — §3.5 헤더 range 가 0017 포함
        assert "0002~0017" in doc_text

    def test_doc_notes_0017_alter(self, doc_text: str) -> None:
        assert "0017_group_roles_meta.sql" in doc_text

    def test_doc_describes_3tier(self, doc_text: str) -> None:
        # 한글 주석 — admin 3-tier 확장 명시
        assert "admin" in doc_text and "3-tier" in doc_text
