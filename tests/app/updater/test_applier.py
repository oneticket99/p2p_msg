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

    def test_apply_macos_skeleton_returns_true(self, tmp_path: Path) -> None:
        # 한글 주석: macOS branch — skeleton chain PASS
        zip_path = tmp_path / "update.zip"
        _make_valid_zip(zip_path)
        install_dir = tmp_path / "Applications" / "TooTalk.app"

        with patch("app.updater.applier.sys.platform", "darwin"):
            result = apply_update(zip_path, install_dir)

        assert result is True

    def test_apply_windows_skeleton_returns_true(
        self, tmp_path: Path
    ) -> None:
        # 한글 주석: Windows branch — skeleton chain PASS
        zip_path = tmp_path / "update.zip"
        _make_valid_zip(zip_path)
        install_dir = tmp_path / "Program Files" / "TooTalk"

        with patch("app.updater.applier.sys.platform", "win32"):
            result = apply_update(zip_path, install_dir)

        assert result is True
