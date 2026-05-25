# SPDX-License-Identifier: GPL-3.0-or-later
"""LifecycleEventsMixin — Qt 윈도우 lifecycle event hook 2 method (cycle 169.529 신설).

codex 2.5 14차 — main_window.py 책임 분리 batch.

분리 대상 method (cycle 139/169.498~501 origin):
- `resizeEvent(event)` — drawer geometry 동기 (resize 시점 stale 차단)
- `closeEvent(event)` — tray retain hide + update_task cancel + tray hint balloon

본 mixin 안 의존:
- `self._active_drawer`, `self._sidebar_rail`
- `self._tray_quit_requested`, `self._tray_icon`, `self._tray_hint_shown`
- `self._cancel_update_task()` (UpdateLifecycleMixin)
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class LifecycleEventsMixin:
    """Qt resizeEvent + closeEvent hook mixin (cycle 169.529)."""

    def resizeEvent(self, event) -> None:  # noqa: N802 — Qt 규약
        """윈도우 resize 시점 훅 — drawer geometry 동기 (사용자 directive image #26).

        cycle 169.500 — main window resize → active drawer height 동시 갱신 의무.
        drawer setGeometry 가 init 1 회만 — resize 시점 stale.
        """
        super().resizeEvent(event)
        try:
            drawer = getattr(self, "_active_drawer", None)
            if drawer is not None and hasattr(drawer, "isVisible") and drawer.isVisible():
                sidebar_w = self._sidebar_rail.width() if hasattr(self, "_sidebar_rail") else 96
                # 한글 주석 — cycle 169.501 — self.height() (full client area) 사용 — central.height() cut 회수
                drawer.setGeometry(sidebar_w, 0, drawer.width(), self.height())
        except Exception as exc:  # noqa: BLE001
            log.debug("[resize] drawer 동기 실패 — %r", exc)

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt 규약
        """윈도우 종료 시점 훅.

        cycle 139 — auto-update background task 의 cancel + cleanup.
        cycle 169.498 — close button = hide + tray retain (사용자 directive).
        tray menu "TooTalk 종료" 만 본격 quit chain.
        """
        # 한글 주석 — tray 가용 + quit 명시 부재 시점 hide + ignore (tray retain)
        if (
            not self._tray_quit_requested
            and self._tray_icon is not None
            and self._tray_icon.isVisible()
        ):
            event.ignore()
            self.hide()
            try:
                # 한글 주석 — 첫 hide 시점 사용자 안내 balloon (1회만)
                if not getattr(self, "_tray_hint_shown", False):
                    from PyQt6.QtWidgets import QSystemTrayIcon
                    self._tray_icon.showMessage(
                        "TooTalk",
                        "창을 닫아도 TooTalk는 트레이에서 계속 실행됩니다. "
                        "트레이 아이콘을 마우스 오른쪽 버튼으로 클릭하면 로그아웃하거나 종료할 수 있어요.",
                        QSystemTrayIcon.MessageIcon.Information,
                        5000,
                    )
                    self._tray_hint_shown = True
            except Exception:
                pass
            return
        log.info("MainWindow 종료 — Qt 이벤트 루프 정리 단계 진입")
        # 한글 주석: auto-update background task 정상 cancel (cycle 139)
        self._cancel_update_task()
        super().closeEvent(event)
