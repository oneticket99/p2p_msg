# SPDX-License-Identifier: GPL-3.0-or-later
"""rotate_key + avatar_palette pure unit — cycle 169.764 신설.

backup master key rotation 정책 + telegram gradient palette hash. 미커버 branch
(naive tz / non-empty name hash) 회수. PyQt6 비의존 pure logic.
"""

from __future__ import annotations

import pytest


class TestNeedsRotation:
    def test_naive_timestamp_kst_assumed(self) -> None:
        # 한글 주석 — tz 부재 ISO → KST 가정 분기 (line 65)
        from app.backup.rotate_key import needs_rotation

        # 한글 주석 — naive (tz 부재) + 충분히 과거 → rotation 의무 True
        assert needs_rotation("2020-01-01T00:00:00", rotation_days=180) is True
        # 한글 주석 — naive + 현재 근접 → rotation 불필요 False
        from datetime import datetime, timedelta, timezone
        recent = (datetime.now(timezone(timedelta(hours=9)))
                  .replace(tzinfo=None)).isoformat()
        assert needs_rotation(recent, rotation_days=180) is False

    def test_aware_expired_true(self) -> None:
        from app.backup.rotate_key import needs_rotation

        assert needs_rotation("2020-01-01T00:00:00+09:00", rotation_days=180) is True

    def test_invalid_timestamp_true(self) -> None:
        from app.backup.rotate_key import needs_rotation

        assert needs_rotation("not-a-date") is True
        assert needs_rotation("") is True


class TestGenerateMasterKey:
    def test_default_32_bytes(self) -> None:
        from app.backup.rotate_key import generate_new_master_key

        assert len(generate_new_master_key()) == 32

    def test_custom_length(self) -> None:
        from app.backup.rotate_key import generate_new_master_key

        assert len(generate_new_master_key(16)) == 16

    def test_too_small_raises(self) -> None:
        from app.backup.rotate_key import generate_new_master_key

        with pytest.raises(ValueError, match="byte_length"):
            generate_new_master_key(8)


class TestRotationLogEntry:
    def test_5_keys(self) -> None:
        from app.backup.rotate_key import rotation_log_entry

        entry = rotation_log_entry(old_key_id="aaaa1111", new_key_id="bbbb2222", reason="manual")
        assert set(entry) == {"ts_kst", "old_key_id", "new_key_id", "reason", "policy"}
        assert entry["reason"] == "manual"
        assert entry["new_key_id"] == "bbbb2222"


class TestExportRotationCommand:
    def test_4_step_chain(self) -> None:
        from pathlib import Path

        from app.backup.rotate_key import export_rotation_command

        out = export_rotation_command(Path("/backups"), Path("/etc/tootalk/keys/new.key"))
        assert "# 1." in out and "# 2." in out and "# 3." in out and "# 4." in out
        assert "/backups" in out and "new.key" in out


class TestAvatarPalette:
    def test_palette_pair_non_empty(self) -> None:
        from app.ui.avatar_palette import palette_pair

        # 한글 주석 — non-empty name → hash index 분기 (line 28)
        pair = palette_pair("alice")
        assert isinstance(pair, tuple) and len(pair) == 2
        assert pair[0].startswith("#") and pair[1].startswith("#")

    def test_palette_pair_empty_default(self) -> None:
        from app.ui.avatar_palette import palette_pair

        assert palette_pair("") == ("#E17076", "#A0464B")

    def test_palette_pair_deterministic(self) -> None:
        from app.ui.avatar_palette import palette_pair

        assert palette_pair("bob") == palette_pair("bob")

    def test_palette_solid_start_color(self) -> None:
        from app.ui.avatar_palette import palette_pair, palette_solid

        assert palette_solid("alice") == palette_pair("alice")[0]
