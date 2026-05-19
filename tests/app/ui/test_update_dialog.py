# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.ui.update_dialog`` + ``app.ui.update_checker`` 단위 테스트 (cycle 133).

PyQt6 부재 graceful skip + progress clamp + periodic_check 신/구 버전
분기 검증 4 PASS.

GUI 실 동작 (QDialog show / signal) = manual smoke 의무 — 본 테스트는
순수 함수 + state mock 만 커버.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ui.update_checker import periodic_check
from app.ui.update_dialog import UpdateDialog, clamp_progress_percent


class TestUpdateDialogPyQt6Absent:
    """PyQt6 ImportError 환경 의 graceful skip 검증."""

    def test_dialog_init_pyqt6_absent_no_raise(self) -> None:
        # 한글 주석: _PYQT_AVAILABLE False patch — __init__ 의 early return
        with patch("app.ui.update_dialog._PYQT_AVAILABLE", False):
            dialog = UpdateDialog(
                current_version="0.4.0",
                latest_info={"version": "0.5.0"},
            )
            assert dialog.current_version == "0.4.0"
            assert dialog.latest_info["version"] == "0.5.0"
            assert dialog.progress is None
            assert dialog.btn_update is None

    def test_update_progress_pyqt6_absent_noop(self) -> None:
        # 한글 주석: PyQt6 부재 환경 의 update_progress noop (raise 없음)
        with patch("app.ui.update_dialog._PYQT_AVAILABLE", False):
            dialog = UpdateDialog(
                current_version="0.4.0",
                latest_info={"version": "0.5.0"},
            )
            dialog.update_progress(0.5)
            assert dialog.progress is None


class TestUpdateProgressClamp:
    """clamp_progress_percent 의 0.0~1.0 → 0~100 + 범위 외 clamp 검증."""

    def test_zero_ratio(self) -> None:
        # 한글 주석: 0.0 = 0
        assert clamp_progress_percent(0.0) == 0

    def test_full_ratio(self) -> None:
        # 한글 주석: 1.0 = 100
        assert clamp_progress_percent(1.0) == 100

    def test_half_ratio(self) -> None:
        # 한글 주석: 0.5 = 50
        assert clamp_progress_percent(0.5) == 50

    def test_negative_clamp(self) -> None:
        # 한글 주석: 음수 ratio → 0 cap (UI freeze 방지)
        assert clamp_progress_percent(-0.3) == 0

    def test_above_one_clamp(self) -> None:
        # 한글 주석: 1.0 초과 ratio → 100 cap
        assert clamp_progress_percent(1.7) == 100

    def test_arbitrary_ratio(self) -> None:
        # 한글 주석: 0.234 → int(23.4) = 23
        assert clamp_progress_percent(0.234) == 23


class TestPeriodicCheckNewVersion:
    """periodic_check 의 신 버전 검출 분기 — callback 호출 검증."""

    @pytest.mark.asyncio
    async def test_new_version_triggers_callback(self) -> None:
        # 한글 주석: CURRENT_VERSION 보다 신 버전 mock — callback 1회 호출
        callback = MagicMock()
        latest_info = {
            "version": "99.0.0",
            "download_url": "https://example.com/tootalk.zip",
            "sha256": "a" * 64,
        }

        with patch(
            "app.ui.update_checker.check_latest_version",
            new=AsyncMock(return_value=latest_info),
        ):
            # 한글 주석: interval 짧게 + 1회 iteration 후 cancel
            task = asyncio.create_task(
                periodic_check(
                    "https://update.example.com",
                    callback,
                    interval_seconds=3600,
                )
            )
            # 한글 주석: 첫 iteration 완료 대기 — 짧은 sleep yield
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        callback.assert_called_once_with(latest_info)


class TestPeriodicCheckSameVersion:
    """periodic_check 의 동일/구 버전 분기 — callback 미호출 검증."""

    @pytest.mark.asyncio
    async def test_same_version_no_callback(self) -> None:
        # 한글 주석: CURRENT_VERSION 과 동일 → callback 미호출
        callback = MagicMock()
        from app.updater.version_check import CURRENT_VERSION

        # 한글 주석: prerelease tag 정합 — semver 동일 비교
        latest_info = {"version": CURRENT_VERSION}

        with patch(
            "app.ui.update_checker.check_latest_version",
            new=AsyncMock(return_value=latest_info),
        ):
            task = asyncio.create_task(
                periodic_check(
                    "https://update.example.com",
                    callback,
                    interval_seconds=3600,
                )
            )
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_latest_no_callback(self) -> None:
        # 한글 주석: check_latest_version None 반환 → callback 미호출
        callback = MagicMock()

        with patch(
            "app.ui.update_checker.check_latest_version",
            new=AsyncMock(return_value=None),
        ):
            task = asyncio.create_task(
                periodic_check(
                    "https://update.example.com",
                    callback,
                    interval_seconds=3600,
                )
            )
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        callback.assert_not_called()
