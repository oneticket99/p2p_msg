# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 Item 3 cycle 132 — emoji_packs 0004 migration schema 정합 검증.

본 test 의 범위 = file content parse + SQL DDL 정합 검증 (3 test):
- TestEmojiPackSchema: CREATE TABLE + UNIQUE / KEY / FK 정합
- TestEmojiPackItemSchema: shortcode UNIQUE per pack 검증
- TestModerationStatusEnum: ENUM 4값 (pending/approved/rejected/dmca_takedown)
"""

from __future__ import annotations

from pathlib import Path

import pytest


# migration SQL 파일 경로 — 저장소 root 기준
_MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "server" / "db" / "migrations" / "0004_emoji_packs.sql"
)


@pytest.fixture(scope="module")
def migration_sql() -> str:
    """0004 migration SQL 파일 전체 본문 load."""

    assert _MIGRATION_PATH.exists(), f"migration 파일 부재 — {_MIGRATION_PATH}"
    return _MIGRATION_PATH.read_text(encoding="utf-8")


class TestEmojiPackSchema:
    """emoji_packs 테이블 의 CREATE TABLE + UNIQUE / KEY / FK 정합."""

    def test_create_table_emoji_packs_exists(self, migration_sql: str) -> None:
        """CREATE TABLE emoji_packs 존재 + IF NOT EXISTS 정합."""

        assert "CREATE TABLE IF NOT EXISTS emoji_packs" in migration_sql

    def test_emoji_packs_unique_slug(self, migration_sql: str) -> None:
        """slug UNIQUE 제약 의무 — uq_emoji_packs_slug index."""

        assert "UNIQUE KEY uq_emoji_packs_slug (slug)" in migration_sql

    def test_emoji_packs_fk_owner_cascade(self, migration_sql: str) -> None:
        """owner_user_id → users(id) FK + ON DELETE CASCADE 정합."""

        assert "CONSTRAINT fk_emoji_packs_owner FOREIGN KEY (owner_user_id)" in migration_sql
        assert "REFERENCES users(id) ON DELETE CASCADE" in migration_sql

    def test_emoji_packs_idx_public_moderation(self, migration_sql: str) -> None:
        """공개 디렉토리 조회 index 정합 — (is_public, moderation_status)."""

        assert "idx_emoji_packs_public_moderation (is_public, moderation_status)" in migration_sql

    def test_emoji_packs_download_count_default(self, migration_sql: str) -> None:
        """download_count 기본값 0 + UNSIGNED 정합."""

        assert "download_count BIGINT UNSIGNED NOT NULL DEFAULT 0" in migration_sql


class TestEmojiPackItemSchema:
    """emoji_pack_items 테이블 의 shortcode UNIQUE per pack 정합."""

    def test_create_table_emoji_pack_items_exists(self, migration_sql: str) -> None:
        """CREATE TABLE emoji_pack_items 존재 정합."""

        assert "CREATE TABLE IF NOT EXISTS emoji_pack_items" in migration_sql

    def test_pack_shortcode_composite_unique(self, migration_sql: str) -> None:
        """(pack_id, shortcode) composite UNIQUE — 팩 안 shortcode 중복 차단."""

        assert (
            "UNIQUE KEY uq_emoji_pack_items_pack_shortcode (pack_id, shortcode)"
            in migration_sql
        )

    def test_pack_items_fk_cascade(self, migration_sql: str) -> None:
        """pack_id → emoji_packs(id) FK + CASCADE DELETE 정합."""

        assert "CONSTRAINT fk_emoji_pack_items_pack FOREIGN KEY (pack_id)" in migration_sql
        assert "REFERENCES emoji_packs(id) ON DELETE CASCADE" in migration_sql

    def test_pack_items_default_mime_png(self, migration_sql: str) -> None:
        """mime_type 기본값 image/png 정합."""

        assert "mime_type VARCHAR(64) NOT NULL DEFAULT 'image/png'" in migration_sql

    def test_pack_items_moderation_3enum(self, migration_sql: str) -> None:
        """item moderation_status 3 ENUM 정합."""

        assert "ENUM('pending', 'approved', 'rejected')" in migration_sql


class TestModerationStatusEnum:
    """moderation_status ENUM 4값 정합 — pack 단위."""

    def test_pack_moderation_enum_pending(self, migration_sql: str) -> None:
        """pending 포함 정합."""

        assert "'pending'" in migration_sql

    def test_pack_moderation_enum_approved(self, migration_sql: str) -> None:
        """approved 포함 정합."""

        assert "'approved'" in migration_sql

    def test_pack_moderation_enum_rejected(self, migration_sql: str) -> None:
        """rejected 포함 정합."""

        assert "'rejected'" in migration_sql

    def test_pack_moderation_enum_dmca_takedown(self, migration_sql: str) -> None:
        """dmca_takedown 포함 정합 — DMCA 신고 takedown 의 workflow."""

        assert "'dmca_takedown'" in migration_sql

    def test_pack_moderation_enum_4_values_combined(self, migration_sql: str) -> None:
        """pack ENUM 4값 합쳐진 검증 — 'pending', 'approved', 'rejected', 'dmca_takedown'."""

        expected = "ENUM('pending', 'approved', 'rejected', 'dmca_takedown')"
        assert expected in migration_sql

    def test_pack_moderation_default_pending(self, migration_sql: str) -> None:
        """pack moderation_status 기본값 pending 정합."""

        assert "DEFAULT 'pending'" in migration_sql
