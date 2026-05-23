# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.updater.applier`` 의 단위 테스트 — cycle 132 skeleton.

macOS branch + Windows branch (mock sys.platform) = 2 PASS.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app.updater.applier import apply_update


def _make_valid_zip(path: Path) -> None:
    """skeleton 테스트용 정상 zip 생성 (entry 1개)."""

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("tootalk-binary.txt", "cycle 132 skeleton placeholder")


class TestApply:
    """apply_update 의 platform 분기 검증 — 실 swap 부재 (skeleton)."""

    def test_apply_macos_skeleton_returns_false_on_missing_binary(self, tmp_path: Path) -> None:
        # 한글 주석 — cycle 169.579: cycle 169.413~427 actual binary swap chain 안 verify gate (Contents/MacOS/TooTalk 부재 → False + rollback).
        # zip skeleton 안 actual binary 부재 시점 swap 검증 fail + rollback chain return False (정상 production behavior).
        zip_path = tmp_path / "update.zip"
        _make_valid_zip(zip_path)
        install_dir = tmp_path / "Applications" / "TooTalk.app"

        with patch("app.updater.applier.sys.platform", "darwin"):
            result = apply_update(zip_path, install_dir)

        # skeleton zip = actual binary 부재 → False return (정상 fail + rollback)
        assert result is False

    def test_apply_windows_skeleton_returns_false_on_missing_binary(
        self, tmp_path: Path
    ) -> None:
        # 한글 주석 — cycle 169.579: Windows branch 동일 verify gate (TooTalk.exe 부재 → False + rollback)
        zip_path = tmp_path / "update.zip"
        _make_valid_zip(zip_path)
        install_dir = tmp_path / "Program Files" / "TooTalk"

        with patch("app.updater.applier.sys.platform", "win32"):
            result = apply_update(zip_path, install_dir)

        # skeleton zip = actual binary 부재 → False return (정상 fail + rollback)
        assert result is False
