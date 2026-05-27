# SPDX-License-Identifier: GPL-3.0-or-later
"""RestPostMixin — REST POST chain 5 method (cycle 169.522 신설).

계층 위치 — app/ui MainWindow mixin(정본 §E). main_window 책임 분리 단위 — MRO 합성.
message POST/읽음표시/초대 의 server REST 호출을 MainWindow 안으로 묶는 배선 단위.

codex 2.5 HIGH 진입 8차 — main_window.py 책임 분리.
cavecrew-investigator verdict — 9 REST method 中 5 retain (3 이미 별 mixin 분리:
_dispatch_message_chain → RoomGroupChatMixin / _on_send_clicked = chat send core retain).

분리 대상 method (cycle 163~169.447 origin):
- `_post_and_resolve(msg_client, room_id, text, client_uuid)` — server POST + message_id resolve
- `_send_saved_message_rest(text, client_uuid)` — saved messages self DM REST chain
- `_mark_room_read(room_id_server, last_msg_id)` — sync dispatch helper
- `_post_mark_read(room_id_server, last_msg_id)` — async POST /api/rooms/{id}/read
- `_on_invite_requested(room_id, friend_user_id)` — InviteDialog signal handler
- `_dispatch_invite_chain(*, room_id, friend_user_id)` — invite_user + MemberList 갱신 async

본 mixin 안 의존 attribute (MainWindow init 안 retain 의무):
- `_current_user_id`, `_session_token`, `_config` (api_base)
- `_chat_view` (resolve_pending_message_id)
- `_rooms_client`, `_member_list`, `_status_bar`
"""

from __future__ import annotations
from app.core.config import DEMO_FALLBACK_API_BASE

import asyncio
import logging
from typing import Optional

from PyQt6.QtCore import pyqtSlot

log = logging.getLogger(__name__)


class RestPostMixin:
    """REST POST chain mixin (cycle 169.522)."""

    async def _post_and_resolve(
        self, msg_client, room_id: int, text: str, client_uuid: str,
    ) -> None:
        """server POST → message_id resolve → bubble.set_message_id chain (cycle 163)."""
        try:
            resp = await msg_client.post_message(room_id, text)
            server_message_id = resp.get("message_id") if isinstance(resp, dict) else None
            if server_message_id is not None:
                self._chat_view.resolve_pending_message_id(client_uuid, int(server_message_id))
                log.debug(
                    "post_message resolve — uuid=%s message_id=%s",
                    client_uuid, server_message_id,
                )
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("post_message 실패 graceful — %r", exc)

    async def _send_saved_message_rest(self, text: str, client_uuid: str) -> None:
        """saved messages self DM room REST POST chain (cycle 169.411 origin).

        1. GET /api/auth/dm/{self_id}/room → saved-{uid} room return
        2. POST /api/rooms/{room_id}/messages → server 영속화
        mesh broadcast 부재 (self echo loop 회피).
        """
        import aiohttp
        try:
            self_id = getattr(self, "_current_user_id", None)
            token = getattr(self, "_session_token", None) or ""
            api_base = getattr(self._config, "api_base", None) or DEMO_FALLBACK_API_BASE
            if not isinstance(self_id, int) or self_id <= 0 or not token:
                return
            headers = {"Authorization": f"Bearer {token}"}
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.get(
                    f"{api_base}/api/auth/dm/{self_id}/room",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return
                    dm = await resp.json()
                    room_id = dm.get("room_id")
                if not room_id:
                    return
                async with session.post(
                    f"{api_base}/api/rooms/{room_id}/messages",
                    json={"body": text, "client_uuid": client_uuid},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status not in (200, 201):
                        log.warning("[saved_post] status=%d", resp.status)
                        return
                    data = await resp.json()
                    log.info(
                        "[saved_post] PASS room=%d msg_id=%s",
                        room_id, data.get("message_id"),
                    )
        except Exception as exc:
            log.debug("[saved_post] 실패 graceful — %r", exc)

    def _mark_room_read(self, room_id_server: int, last_msg_id: int) -> None:
        """chat 포커스 시점 server last_read_msg_id 갱신 chain (cycle 169.447 origin).

        graceful — server fail = silent skip. caller = _on_chat_selected + dm_history fetch 후.
        """
        try:
            asyncio.ensure_future(self._post_mark_read(room_id_server, last_msg_id))
        except Exception as exc:
            log.debug("[mark_read] dispatch 실패 — %r", exc)

    async def _post_mark_read(self, room_id_server: int, last_msg_id: int) -> None:
        """POST /api/rooms/{room_id}/read fire (async chain)."""
        import aiohttp
        try:
            token = getattr(self, "_session_token", None) or ""
            if not token or room_id_server <= 0:
                return
            api_base = getattr(self._config, "api_base", None) or DEMO_FALLBACK_API_BASE
            headers = {"Authorization": f"Bearer {token}"}
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.post(
                    f"{api_base}/api/rooms/{room_id_server}/read",
                    json={"last_read_msg_id": int(last_msg_id)},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        log.warning("[mark_read] HTTP %d", resp.status)
        except Exception as exc:
            log.debug("[mark_read] async fail — %r", exc)

    def _on_invite_requested(self, room_id: int, friend_user_id: int) -> None:
        """InviteDialog invite_requested signal handler (cycle 147)."""
        log.info(
            "[main_window] invite_requested room=%s friend_user_id=%s",
            room_id, friend_user_id,
        )

        if self._rooms_client is None:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(self, "TooTalk", "rooms_client 미주입 — 초대 차단")
            return

        loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is None:
            log.debug("[main_window] asyncio running loop 부재 — invite REST skip")
            return

        asyncio.ensure_future(
            self._dispatch_invite_chain(
                room_id=room_id, friend_user_id=friend_user_id,
            ),
            loop=loop,
        )

    async def _dispatch_invite_chain(
        self, *, room_id: int, friend_user_id: int,
    ) -> None:
        """invite_user REST + MemberList 갱신 async chain (cycle 147 origin)."""
        try:
            peer_id = await self._rooms_client.invite_user(room_id, friend_user_id)
            log.info(
                "[main_window] invite_user PASS room=%s friend=%s peer_id=%s",
                room_id, friend_user_id, peer_id,
            )
            self._status_bar.showMessage(
                f"초대 완료 — friend_id={friend_user_id} peer_id={peer_id}", 3000,
            )
        except Exception as exc:  # noqa: BLE001
            msg = f"초대 실패 — {exc}"
            log.warning(
                "[main_window] invite_user FAIL room=%s friend=%s: %r",
                room_id, friend_user_id, exc,
            )
            self._status_bar.showMessage(msg, 4000)
            return

        # MemberList 갱신 — get_room 재호출 + set_members
        try:
            _room, members = await self._rooms_client.get_room(room_id)
            from app.ui.member_list import MemberItem

            member_items = [
                MemberItem(
                    user_id=int(m.user_id),
                    username=f"user_{m.user_id}",
                    role=str(getattr(m, "role", "member")),
                    is_online=False,
                )
                for m in members
            ]
            viewer_role = "member"
            if self._current_user_id is not None:
                for m in members:
                    if int(m.user_id) == int(self._current_user_id):
                        viewer_role = str(getattr(m, "role", "member"))
                        break
            self._member_list.set_members(member_items, viewer_role=viewer_role)
            log.debug(
                "[main_window] MemberList refresh room=%s count=%d viewer_role=%s",
                room_id, len(member_items), viewer_role,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[main_window] get_room 재호출 FAIL room=%s — MemberList skip (%r)",
                room_id, exc,
            )
