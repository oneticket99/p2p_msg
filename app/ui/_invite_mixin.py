# SPDX-License-Identifier: GPL-3.0-or-later
"""InviteMixin — InviteDialog host + invite_failed slot (cycle 169.529 신설).

codex 2.5 14차 — main_window.py 책임 분리 batch.

분리 대상 method (cycle 147 origin):
- `open_invite_dialog(room_id=None)` — InviteDialog instantiation + friends_client populate
- `_on_invite_failed(message)` — InviteDialog.invite_failed → status_bar feedback

본 mixin 안 의존:
- `self._current_room_id`, `self._friends_client`, `self._status_bar`
- `self._on_invite_requested()` (RestPostMixin)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from PyQt6.QtCore import pyqtSlot

log = logging.getLogger(__name__)


class InviteMixin:
    """InviteDialog host + invite_failed slot mixin (cycle 169.529)."""

    def open_invite_dialog(self, room_id: Optional[int] = None) -> Optional[object]:
        """InviteDialog 의 instantiation + friends_client populate chain.

        Parameters
        ----------
        room_id : int | None
            초대 대상 room. None = ``self._current_room_id`` 폴백. 부재 시 noop.

        Returns
        -------
        InviteDialog | None
            인스턴스 (caller 의 exec 의무 — test 가시성 확보).
            ``self._current_room_id`` 부재 시 None.

        Notes
        -----
        - friends_client 주입 부재 시 = dialog instantiation 만 (빈 dropdown).
        - rooms_client 부재 시 = invite_requested 시그널 발생 후 graceful skip.
        - 실 exec() 은 caller 책임 — test 의 modal 차단 회피.
        """

        from app.ui.invite_dialog import InviteDialog  # 한글 주석: lazy import (graceful)

        target_room_id = room_id if room_id is not None else self._current_room_id
        if target_room_id is None or target_room_id <= 0:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(self, "TooTalk", "초대 = 그룹 방 진입 의무")
            return None

        dialog = InviteDialog(
            room_id=target_room_id,
            friends_client=self._friends_client,
            room_title=f"Room #{target_room_id}",
            parent=self,
        )
        # 한글 주석: invite_requested → rooms_client.invite_user REST chain
        dialog.invite_requested.connect(self._on_invite_requested)
        dialog.invite_failed.connect(self._on_invite_failed)

        # 한글 주석: friends_client 가용 시 async populate task 등록 (graceful skip)
        if self._friends_client is not None:
            loop: Optional[asyncio.AbstractEventLoop] = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None:
                asyncio.ensure_future(
                    dialog.populate_friends_async(), loop=loop
                )
            else:
                log.debug(
                    "[main_window] asyncio running loop 부재 — populate skip"
                )

        log.info(
            "[main_window] invite_dialog 인스턴스화 room_id=%s friends_client=%s",
            target_room_id,
            bool(self._friends_client),
        )
        return dialog

    @pyqtSlot(str)
    def _on_invite_failed(self, message: str) -> None:
        """InviteDialog 의 invite_failed 시그널 핸들러 — status bar feedback.

        populate 단계 (friends_client.list_friends FAIL) 의 message 전달.
        """

        log.warning("[main_window] invite_failed — %s", message)
        self._status_bar.showMessage(message, 4000)
