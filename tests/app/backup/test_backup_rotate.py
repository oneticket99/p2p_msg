# SPDX-License-Identifier: GPL-3.0-or-later
"""사이클 132 — encrypted backup master key rotation skeleton 단위 검증.

5 test 의무
-----------
1. ``TestNeedsRotation`` (3)
   - fresh ISO → False
   - 180 일 초과 ISO → True
   - invalid ISO → True (안전쪽 fallback)
2. ``TestGenerateNewMasterKey`` (1)
   - default 32 byte + secrets 의 entropy 회귀
3. ``TestRotationLogEntry`` (1)
   - KST ISO + old_key_id + new_key_id + reason + policy 5 키 의무
"""
from __future__ import annotations

import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.backup.rotate_key import (
    DEFAULT_ROTATION_DAYS,
    export_rotation_command,
    generate_new_master_key,
    needs_rotation,
    rotation_log_entry,
)

# 한글 주석 — KST timezone 단위 검증 정합
_KST = timezone(timedelta(hours=9))


class TestNeedsRotation(unittest.TestCase):
    """rotation 의무 검증 — fresh / expired / invalid 3 분기."""

    def test_fresh_returns_false(self) -> None:
        """한글 주석 — 어제 rotation = 의무 불필요 (180 일 정책 안)."""
        yesterday = (datetime.now(_KST) - timedelta(days=1)).isoformat()
        self.assertFalse(needs_rotation(yesterday))

    def test_expired_returns_true(self) -> None:
        """한글 주석 — 200 일 전 rotation = 즉시 rotation 의무."""
        expired = (datetime.now(_KST) - timedelta(days=200)).isoformat()
        self.assertTrue(needs_rotation(expired))

    def test_invalid_iso_returns_true(self) -> None:
        """한글 주석 — invalid ISO 시 안전쪽 (rotation 의무) 처리 의무."""
        self.assertTrue(needs_rotation("not-an-iso-timestamp"))
        # 한글 주석 — None / empty 도 safety fallback
        self.assertTrue(needs_rotation(""))


class TestGenerateNewMasterKey(unittest.TestCase):
    """secrets 의 AES-256 32 byte 생성 회귀."""

    def test_default_32_byte_and_entropy(self) -> None:
        """한글 주석 — default 32 byte + 2 회 호출 의 동일 결과 차단 (entropy 회귀)."""
        key_a = generate_new_master_key()
        key_b = generate_new_master_key()
        self.assertEqual(len(key_a), 32)
        self.assertEqual(len(key_b), 32)
        # 한글 주석 — secrets.token_bytes 의 256 bit entropy → 충돌 확률 무시 가능
        self.assertNotEqual(key_a, key_b)

    def test_min_byte_guard(self) -> None:
        """한글 주석 — 16 byte 미만 차단 (AES-128 minimum)."""
        with self.assertRaises(ValueError):
            generate_new_master_key(byte_length=8)


class TestRotationLogEntry(unittest.TestCase):
    """audit log entry 빌더 회귀."""

    def test_required_keys_and_kst_iso(self) -> None:
        """한글 주석 — 5 key 의무 + KST ISO 형식 + policy 정합."""
        entry = rotation_log_entry(
            old_key_id="abc12345",
            new_key_id="def67890",
            reason="scheduled",
        )
        self.assertEqual(
            set(entry.keys()),
            {"ts_kst", "old_key_id", "new_key_id", "reason", "policy"},
        )
        self.assertEqual(entry["old_key_id"], "abc12345")
        self.assertEqual(entry["new_key_id"], "def67890")
        self.assertEqual(entry["reason"], "scheduled")
        self.assertIn(str(DEFAULT_ROTATION_DAYS), entry["policy"])
        # 한글 주석 — ISO 8601 + KST offset +09:00 검증
        self.assertRegex(entry["ts_kst"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        self.assertTrue(
            entry["ts_kst"].endswith("+09:00")
            or "+09:00" in entry["ts_kst"]
        )


class TestExportRotationCommand(unittest.TestCase):
    """사용자 manual 명령 안내 string 회귀 (bonus 6 번째 test)."""

    def test_4_step_chain_text(self) -> None:
        """한글 주석 — 4 단계 chain 안내 + 경로 binding 검증."""
        backup_dir = Path("/var/backups/tootalk")
        new_key_path = Path("/etc/tootalk/keys/active.key.new")
        text = export_rotation_command(backup_dir, new_key_path)
        self.assertIn("1.", text)
        self.assertIn("2.", text)
        self.assertIn("3.", text)
        self.assertIn("4.", text)
        self.assertIn(str(backup_dir), text)
        self.assertIn(str(new_key_path), text)
        self.assertIn("user_activity_log", text)


if __name__ == "__main__":
    unittest.main()
