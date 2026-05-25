# SPDX-License-Identifier: GPL-3.0-or-later
"""UpdateLifecycleMixin — auto-update 3 method chain (cycle 169.526 신설).

codex 2.5 LOW 진입 11차 — main_window.py 책임 분리 batch.

분리 대상 method (cycle 132/Phase 5 origin):
- `_start_update_check_task()` — qasync running loop 에 periodic_check 등록
- `_on_new_version(latest_info)` — UpdateDialog instantiation + modal 호출
- `_cancel_update_task()` — closeEvent chain 의 task cancel + cleanup

본 mixin 안 의존 attribute:
- `self._update_task` (Optional[asyncio.Task])
- `self._current_update_dialog` (UpdateDialog 참조)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from app.ui.update_checker import periodic_check
from app.ui.update_dialog import UpdateDialog
from app.updater.version_check import CURRENT_VERSION

log = logging.getLogger(__name__)

# 한글 주석 — main_window 와 동일 default fallback URL (114.207.112.73:8765).
_DEFAULT_UPDATE_SERVER_URL = "http://114.207.112.73:8765"


class UpdateLifecycleMixin:
    """auto-update periodic_check task + UpdateDialog modal chain mixin (cycle 169.526)."""

    def _start_update_check_task(self) -> None:
        """``periodic_check`` 코루틴 의 asyncio task 등록.

        qasync 통합 환경 의 정상 경로 — 시작 시 1회 + 매 24시간 polling.
        running loop 부재 환경 (pytest QApplication only / 순수 unittest) 의
        graceful skip + log.debug. 정상 환경 에서는 task 가 background 살아 있다.
        """

        # 한글 주석: 환경변수 override — Phase 5 productization 시 .env 정합
        server_url = (
            os.environ.get("UPDATE_SERVER_URL", "").strip()
            or _DEFAULT_UPDATE_SERVER_URL
        )

        # 한글 주석: running loop 우선 — qasync 통합 환경 의 정상 경로.
        # 부재 시 graceful skip (running loop 부재 = pytest unittest 환경).
        loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            log.debug(
                "[main_window] asyncio running loop 부재 — auto-update task skip"
            )
            self._update_task = None
            return

        try:
            self._update_task = asyncio.ensure_future(
                periodic_check(server_url, self._on_new_version),
                loop=loop,
            )
            log.info(
                "[main_window] auto-update periodic_check task 등록 — server=%s",
                server_url,
            )
        except RuntimeError as exc:
            # 한글 주석: loop closed 등 의 graceful catch
            log.warning(
                "[main_window] auto-update task 등록 실패 — skip (%r)", exc
            )
            self._update_task = None

    def _on_new_version(self, latest_info: dict) -> None:
        """신 버전 검출 시 ``UpdateDialog`` instantiation + 사용자 GO 대기.

        ``periodic_check`` callback 진입점. UpdateDialog 의 modal 호출 +
        사용자 GO 시 download chain trigger (실 download = Phase 5 본격
        cycle 위탁 — 본 cycle 의 skeleton dialog 표시 까지).
        """

        latest_version = latest_info.get("version", "(unknown)")
        log.info(
            "[main_window] 신 버전 검출 — current=%s latest=%s",
            CURRENT_VERSION,
            latest_version,
        )
        try:
            dialog = UpdateDialog(
                current_version=CURRENT_VERSION,
                latest_info=latest_info,
                parent=self,
                on_user_go=None,  # 한글 주석: 실 download chain = Phase 5 본격 cycle
            )
            # 한글 주석: dialog 참조 보관 — gc 회피 + 테스트 가시성
            self._current_update_dialog = dialog
            dialog.exec()
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[main_window] UpdateDialog instantiation 실패 — graceful skip (%r)",
                exc,
            )

    def _cancel_update_task(self) -> None:
        """shutdown chain 의 update task cancel + cleanup.

        ``closeEvent`` 진입 시 호출. task 부재 / 이미 종료 시 noop.
        CancelledError 는 정상 종료 신호이므로 swallow.
        """

        if self._update_task is None:
            return
        if self._update_task.done():
            self._update_task = None
            return
        try:
            self._update_task.cancel()
            log.info("[main_window] auto-update task cancel 송신")
        except Exception as exc:  # noqa: BLE001
            log.warning("[main_window] auto-update task cancel 실패 — %r", exc)
        self._update_task = None
