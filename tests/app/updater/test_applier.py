# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.updater.applier`` 의 단위 테스트.

cycle 132 skeleton(macOS/Windows branch missing-binary) + cycle 169.851 coverage
2차 확장(zip 유효성 부재/non-zip/empty/BadZipFile + platform 미지원 + macOS swap
PASS·rollback + Windows swap PASS Popen mock).
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


class TestApplyValidation:
    """apply_update 의 zip 유효성 + platform 미지원 분기 검증."""

    def test_missing_zip_returns_false(self, tmp_path: Path) -> None:
        # 한글 주석: zip 파일 부재 → False
        assert apply_update(tmp_path / "absent.zip", tmp_path / "T.app") is False

    def test_non_zip_file_returns_false(self, tmp_path: Path) -> None:
        # 한글 주석: zip 형식 위반(평문 파일) → is_zipfile False → False
        bogus = tmp_path / "fake.zip"
        bogus.write_text("not a zip archive")
        assert apply_update(bogus, tmp_path / "T.app") is False

    def test_empty_zip_returns_false(self, tmp_path: Path) -> None:
        # 한글 주석: 유효 zip 이나 entry 부재 → False
        empty = tmp_path / "empty.zip"
        with zipfile.ZipFile(empty, "w"):
            pass
        assert apply_update(empty, tmp_path / "T.app") is False

    def test_bad_zipfile_open_returns_false(self, tmp_path: Path) -> None:
        # 한글 주석: is_zipfile 통과 후 ZipFile open 단계 BadZipFile → False
        zip_path = tmp_path / "update.zip"
        _make_valid_zip(zip_path)
        with patch(
            "app.updater.applier.zipfile.ZipFile",
            side_effect=zipfile.BadZipFile("손상"),
        ):
            assert apply_update(zip_path, tmp_path / "T.app") is False

    def test_unsupported_platform_returns_false(self, tmp_path: Path) -> None:
        # 한글 주석: macOS/Windows 외 platform → 미지원 False
        zip_path = tmp_path / "update.zip"
        _make_valid_zip(zip_path)
        with patch("app.updater.applier.sys.platform", "linux"):
            assert apply_update(zip_path, tmp_path / "T.app") is False


class TestApplySwapSuccess:
    """macOS/Windows skeleton 의 swap PASS 경로 검증 (실 binary 포함 zip)."""

    def test_macos_swap_success(self, tmp_path: Path) -> None:
        # 한글 주석: TooTalk.app/Contents/MacOS/TooTalk 실행 binary 포함 zip → swap PASS
        zip_path = tmp_path / "update.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("TooTalk.app/Contents/MacOS/TooTalk", "#!/bin/sh\necho hi\n")
        # 기존 .app 존재(백업 이동 대상) 구성
        install_dir = tmp_path / "TooTalk.app"
        (install_dir / "Contents" / "MacOS").mkdir(parents=True)
        (install_dir / "Contents" / "MacOS" / "TooTalk").write_text("old")

        with patch("app.updater.applier.sys.platform", "darwin"):
            result = apply_update(zip_path, install_dir)

        assert result is True
        assert (install_dir / "Contents" / "MacOS" / "TooTalk").is_file()

    def test_macos_swap_rollback_on_missing_executable(self, tmp_path: Path) -> None:
        # 한글 주석: extract 가 install_dir 이름(TooTalk.app)을 만들지 않는 zip → new_app
        # 부재 → swap 검증 실패 → install_dir 미존재 시점 rollback(백업 복원) → False
        zip_path = tmp_path / "update.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("readme.txt", "wrong payload — TooTalk.app 미포함")
        install_dir = tmp_path / "TooTalk.app"
        install_dir.mkdir()
        (install_dir / "marker.txt").write_text("original")

        with patch("app.updater.applier.sys.platform", "darwin"):
            result = apply_update(zip_path, install_dir)

        assert result is False
        # rollback 으로 원본 install_dir 복원(backup → install_dir)
        assert install_dir.exists()
        assert (install_dir / "marker.txt").read_text() == "original"

    def test_windows_swap_success(self, tmp_path: Path) -> None:
        # 한글 주석: TooTalk.exe 포함 zip + Popen mock → batch 생성 + detached Popen PASS
        zip_path = tmp_path / "update.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("TooTalk.exe", "MZ binary placeholder")
        install_dir = tmp_path / "TooTalk"

        with patch("app.updater.applier.sys.platform", "win32"), patch(
            "subprocess.Popen"
        ) as mock_popen:
            result = apply_update(zip_path, install_dir)

        assert result is True
        mock_popen.assert_called_once()  # detached batch process 기동
