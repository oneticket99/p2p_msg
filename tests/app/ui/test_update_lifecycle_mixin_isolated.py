# SPDX-License-Identifier: GPL-3.0-or-later
"""UpdateLifecycleMixin isolated test — cycle 169.645 mock isolation refactor.

cycle 169.574 + 169.637 안 MainWindow instantiation hang 회수 path. 본 file =
mixin method 직접 호출 + MagicMock self instance + asyncio loop / UpdateDialog mock.
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")


class TestStartUpdateCheckTask:
    """_start_update_check_task — running loop 부재 graceful skip."""

    def test_no_running_loop_sets_task_none(self) -> None:
        from app.ui._update_lifecycle_mixin import UpdateLifecycleMixin

        self_mock = MagicMock()
        # 한글 주석: get_running_loop 안 RuntimeError raise — graceful skip path
        with patch(
            "app.ui._update_lifecycle_mixin.asyncio.get_running_loop",
            side_effect=RuntimeError("no running loop"),
        ):
            UpdateLifecycleMixin._start_update_check_task(self_mock)

        assert self_mock._update_task is None

    def test_running_loop_registers_task(self) -> None:
        from app.ui._update_lifecycle_mixin import UpdateLifecycleMixin

        self_mock = MagicMock()
        fake_loop = MagicMock(spec=asyncio.AbstractEventLoop)
        fake_task = MagicMock(spec=asyncio.Task)

        with patch(
            "app.ui._update_lifecycle_mixin.asyncio.get_running_loop",
            return_value=fake_loop,
        ), patch(
            "app.ui._update_lifecycle_mixin.asyncio.ensure_future",
            return_value=fake_task,
        ) as fake_ensure, patch(
            "app.ui._update_lifecycle_mixin.periodic_check"
        ) as fake_periodic:
            UpdateLifecycleMixin._start_update_check_task(self_mock)

            assert self_mock._update_task is fake_task
            fake_ensure.assert_called_once()


class TestOnNewVersion:
    """_on_new_version — UpdateDialog instantiation + exec chain."""

    def test_new_version_creates_dialog(self) -> None:
        from app.ui._update_lifecycle_mixin import UpdateLifecycleMixin

        self_mock = MagicMock()
        fake_dialog = MagicMock()

        with patch(
            "app.ui._update_lifecycle_mixin.UpdateDialog",
            return_value=fake_dialog,
        ) as fake_cls:
            UpdateLifecycleMixin._on_new_version(
                self_mock, {"version": "99.0.0", "download_url": "https://x"}
            )

            fake_cls.assert_called_once()
            assert self_mock._current_update_dialog is fake_dialog
            # cycle 169.838 — .exec()(별도 윈도우) → _exec_dialog_centered(in-app overlay) 전환
            self_mock._exec_dialog_centered.assert_called_once()

    def test_dialog_instantiation_graceful_on_error(self) -> None:
        from app.ui._update_lifecycle_mixin import UpdateLifecycleMixin

        self_mock = MagicMock()

        with patch(
            "app.ui._update_lifecycle_mixin.UpdateDialog",
            side_effect=RuntimeError("dialog fail"),
        ):
            # 한글 주석: graceful catch — raise 부재
            UpdateLifecycleMixin._on_new_version(
                self_mock, {"version": "99.0.0"}
            )


class TestCancelUpdateTask:
    """_cancel_update_task — closeEvent cleanup."""

    def test_no_task_noop(self) -> None:
        from app.ui._update_lifecycle_mixin import UpdateLifecycleMixin

        self_mock = MagicMock()
        self_mock._update_task = None

        UpdateLifecycleMixin._cancel_update_task(self_mock)
        # 한글 주석: graceful — exception 부재

    def test_done_task_clears(self) -> None:
        from app.ui._update_lifecycle_mixin import UpdateLifecycleMixin

        self_mock = MagicMock()
        fake_task = MagicMock()
        fake_task.done.return_value = True
        self_mock._update_task = fake_task

        UpdateLifecycleMixin._cancel_update_task(self_mock)
        assert self_mock._update_task is None
        fake_task.cancel.assert_not_called()

    def test_active_task_cancels(self) -> None:
        from app.ui._update_lifecycle_mixin import UpdateLifecycleMixin

        self_mock = MagicMock()
        fake_task = MagicMock()
        fake_task.done.return_value = False
        self_mock._update_task = fake_task

        UpdateLifecycleMixin._cancel_update_task(self_mock)
        fake_task.cancel.assert_called_once()
        assert self_mock._update_task is None
