# SPDX-License-Identifier: GPL-3.0-or-later
"""ChatHelperMixin — chat history + cache + lazy load + unread fetch chain (cycle 169.519 신설).

계층 위치 — app/ui MainWindow mixin(정본 §E). main_window 책임 분리 단위 — MRO 합성.
local SQLite replay + scroll-up lazy load + unread batch + friend DM history 의 server 결선.

codex 2.5 HIGH 진입 5차 — main_window.py 책임 분리.
TrayMixin (509) + FriendSearchMixin (511) + BotChatMixin (513) + DrawerMixin (514) 등가 패턴.

분리 대상 method (cycle 169.441~466 origin):
- `_kind_room_local(kind, target_id)` — local SQLite room_id namespace 변환
- `_load_local_history(kind, target_id, scroll_bottom)` — chat enter local cache replay
- `_on_lazy_load_requested(room_id_local)` — scroll-up incremental prepend
- `_fetch_unread_counts()` — startup + 주기 unread batch
- `_fetch_dm_history(friend_id)` — friend DM room resolve + history fetch

본 mixin 안 의존 attribute (MainWindow init 안 retain 의무):
- `_session_token`, `_current_user_id`, `_config` (api_base)
- `_active_chat_kind`, `_active_chat_target_id`, `_active_room_id_server`
- `_chat_view` (add_message + prepend_message + clear_messages + _lazy_load_active)
- `_chat_list_panel` (_entries + _render)
- `_state` (user_id)
- `_fetch_bot_history()` — BotChatMixin 안 retain
- `_mark_room_read(room_id, msg_id)` — main_window 안 retain
"""

from __future__ import annotations
from app.core.config import DEMO_FALLBACK_API_BASE

import asyncio
import logging
from datetime import datetime

from PyQt6.QtCore import pyqtSlot

log = logging.getLogger(__name__)


class ChatHelperMixin:
    """chat history + cache + lazy load + unread fetch chain mixin (cycle 169.519)."""

    def _kind_room_local(self, kind: str, target_id: int) -> int:
        """kind + target_id → local SQLite room_id namespace 변환 (cycle 169.444 origin)."""
        self_id = getattr(self, "_current_user_id", None) or 1
        if kind == "saved":
            return self_id * 100 + 1
        if kind == "bot":
            return self_id * 10 + 2
        if kind == "friend":
            return target_id * 100 + 3
        return target_id * 100 + 9

    @pyqtSlot(int)
    def _on_lazy_load_requested(self, room_id_local: int) -> None:
        """chat_view scroll-up 시점 incremental prepend chain (cycle 169.466 origin).

        chain:
        1. before_msg_id = local SQLite 안 현 min_msg_id
        2. fetch 30 older rows
        3. 부재 시점 = server REST fetch + SQLite write-back chain (별 trigger)
        4. retain 시점 = chat_view.prepend_message 호출 → scroll position 자연 retain
        """
        try:
            from app.db import messages_cache as _mc
            from datetime import datetime as _dt
            # cycle 169.830 — cursor = 실제 표시된 최소 msg_id 우선 (sync_state stale 회수).
            # 표시 기준으로 strictly older fetch → 동일 window 재fetch(중복 증식) 차단.
            disp_min = self._chat_view.min_displayed_msg_id()
            min_id = disp_min if disp_min > 0 else _mc.get_min_msg_id(room_id_local)
            if min_id is None or min_id <= 1:
                log.info("[lazy_load] room=%d local cache exhausted — server fetch fire", room_id_local)
                kind = self._active_chat_kind or "saved"
                tid = self._active_chat_target_id or 0
                if kind == "friend" and tid > 0:
                    asyncio.ensure_future(self._fetch_dm_history(tid))
                elif kind == "saved":
                    self_id = getattr(self, "_current_user_id", None)
                    if isinstance(self_id, int) and self_id > 0:
                        asyncio.ensure_future(self._fetch_dm_history(self_id))
                elif kind == "bot":
                    asyncio.ensure_future(self._fetch_bot_history())
                self._chat_view._lazy_load_active = False
                return
            rows = _mc.list_messages_by_room(
                room_id=room_id_local, limit=30, before_msg_id=min_id,
            )
            if not rows:
                self._chat_view._lazy_load_active = False
                return
            # cycle 169.466 — incremental prepend (clear+replay 폐기)
            kind = self._active_chat_kind or "saved"
            hide_sender = kind in ("friend", "bot", "saved")
            # DESC fetch 결과 그대로 iterate — prepend insertWidget(0) 가 reverse 효과 부여
            for r in rows:
                is_self_flag = bool(r["is_self"])
                if kind == "saved":
                    is_self_flag = True
                sender = "나" if is_self_flag else (
                    "투네이션 고객센터" if kind == "bot" else f"user#{r['sender_id']}"
                )
                ts = _dt.fromtimestamp(r["ts_ms"] / 1000.0) if r["ts_ms"] else _dt.now()
                self._chat_view.prepend_message(
                    sender=sender, text=r["body"] or "", ts=ts,
                    is_self=is_self_flag,
                    hide_sender=hide_sender,
                    msg_id=int(r["msg_id"]) if r["msg_id"] else 0,
                )
            log.info("[lazy_load] prepend PASS — room=%d fetched=%d", room_id_local, len(rows))
        except Exception as exc:
            log.debug("[lazy_load] 실패 — %r", exc)
            self._chat_view._lazy_load_active = False

    def _load_local_history(self, kind: str, target_id: int, scroll_bottom: bool = True) -> None:
        """chat enter 시점 local SQLite history replay (cycle 169.441 origin).

        사용자 directive — 모든 채팅방 이전 대화 영속 + 채팅방 진입 시점 즉시 표시.
        local cache 부재 시점 server fetch chain (`_fetch_dm_history`) 만 polling.
        """
        try:
            from app.db import messages_cache as _mc
            from datetime import datetime as _dt
            self_id = getattr(self, "_current_user_id", None) or 1
            if kind == "saved":
                room_id_local = self_id * 100 + 1
            elif kind == "bot":
                room_id_local = self_id * 10 + 2
            elif kind == "friend":
                room_id_local = target_id * 100 + 3
            else:
                return
            rows = _mc.list_messages_by_room(room_id=room_id_local, limit=100)
            if not rows:
                return
            # cycle 169.458 — ts ASC + id ASC sort (SQL DESC fetch → reversed = ASC)
            rows = list(reversed(rows))
            for r in rows:
                sender_name = "나" if r["is_self"] else (
                    "투네이션 고객센터" if kind == "bot" else f"user#{r['sender_id']}"
                )
                ts = _dt.fromtimestamp(r["ts_ms"] / 1000.0) if r["ts_ms"] else _dt.now()
                effective_self = True if kind == "saved" else bool(r["is_self"])
                self._chat_view.add_message(
                    sender_name, r["body"] or "", ts,
                    is_self=effective_self,
                    hide_sender=kind in ("friend", "bot", "saved"),
                    play_sound=False,  # cycle 169.462 — history replay sound 차단
                )
            # cycle 169.463 — lazy load 시점 scroll bottom 차단
            if scroll_bottom:
                self._chat_view.scroll_to_bottom()
            log.info("[load_local] kind=%s room=%d msgs=%d replay PASS",
                     kind, room_id_local, len(rows))
        except Exception as exc:
            log.debug("[load_local] 실패 — %r", exc)

    async def _fetch_unread_counts(self) -> None:
        """startup + 주기 unread count batch fetch (cycle 169.448~469 origin).

        chain:
        1. chat_list_panel entries 의 friend/saved/bot kind → server room_id resolve
        2. POST /api/auth/dm/{target}/room → room_id
        3. GET /api/rooms/unread?room_ids=N,M,K → {counts: {room_id: count}}
        4. chat_list_panel entry.unread_count 갱신 + _render fire
        """
        import aiohttp
        try:
            token = getattr(self, "_session_token", None) or ""
            self_id = getattr(self, "_current_user_id", None) or 0
            if not token or self_id <= 0:
                return
            api_base = getattr(self._config, "api_base", None) or DEMO_FALLBACK_API_BASE
            headers = {"Authorization": f"Bearer {token}"}
            connector = aiohttp.TCPConnector(ssl=False)

            entries = getattr(self._chat_list_panel, "_entries", [])
            room_id_to_entry: dict = {}
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                for e in entries:
                    if e.kind == "friend" and e.target_id > 0:
                        path = f"/api/auth/dm/{e.target_id}/room"
                    elif e.kind == "saved":
                        path = f"/api/auth/dm/{self_id}/room"
                    elif e.kind == "bot":
                        path = "/api/auth/dm/bot/room"
                    else:
                        continue
                    try:
                        async with session.get(
                            f"{api_base}{path}",
                            timeout=aiohttp.ClientTimeout(total=5),
                        ) as resp:
                            if resp.status != 200:
                                continue
                            data = await resp.json()
                            rid = data.get("room_id")
                            if isinstance(rid, int) and rid > 0:
                                room_id_to_entry[rid] = e
                    except Exception:
                        continue

                if not room_id_to_entry:
                    return
                ids_str = ",".join(str(k) for k in room_id_to_entry.keys())
                try:
                    async with session.get(
                        f"{api_base}/api/rooms/unread?room_ids={ids_str}",
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status != 200:
                            return
                        data = await resp.json()
                        counts = data.get("counts", {})
                except Exception as exc:
                    log.debug("[fetch_unread] batch fail — %r", exc)
                    return

            for rid_str, count in counts.items():
                try:
                    rid = int(rid_str)
                    entry = room_id_to_entry.get(rid)
                    if entry is not None:
                        entry.unread_count = int(count)
                except Exception:
                    continue
            try:
                self._chat_list_panel._render()
            except Exception:
                pass
            log.info("[fetch_unread] PASS — rooms=%d", len(counts))
        except Exception as exc:
            log.debug("[fetch_unread] 실패 — %r", exc)

    async def _fetch_dm_history(self, friend_id: int) -> None:
        """friend DM room resolve + message history fetch chain (cycle 169.225 origin).

        1. GET /api/auth/dm/{friend_id}/room → room_id resolve
        2. list_messages(room_id, limit=50) → MessagePayload list
        3. active chat retain 시점 chat_view re-populate
        """
        import aiohttp
        try:
            api_base = getattr(self._config, "api_base", None) or DEMO_FALLBACK_API_BASE
            token = getattr(self, "_session_token", None) or ""
            if not token:
                return
            headers = {"Authorization": f"Bearer {token}"}
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                # step 1 — DM room resolve
                async with session.get(
                    f"{api_base}/api/auth/dm/{friend_id}/room",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return
                    dm = await resp.json()
                    room_id = dm.get("room_id")
                if not room_id:
                    return
                # step 2 — messages list
                async with session.get(
                    f"{api_base}/api/rooms/{room_id}/messages?limit=50&offset=0",
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return
                    page = await resp.json()
                    raw_messages = page.get("messages", [])
            # step 3 — active chat retain 시점 chat_view re-populate
            active_match = (
                (self._active_chat_kind == "friend" and self._active_chat_target_id == friend_id)
                or (self._active_chat_kind == "saved")
            )
            if active_match:
                self._chat_view.clear_messages()
                # cycle 169.430 — saved kind is_self detection chain
                viewer_uid = (
                    getattr(self._state, "user_id", None)
                    or getattr(self, "_current_user_id", None)
                    or friend_id
                )
                from app.db import messages_cache as _mc
                kind_active = self._active_chat_kind or "saved"
                room_id_local = self._kind_room_local(kind_active, friend_id)
                self._active_room_id_server = int(room_id)
                _max_msg_id = 0
                # cycle 169.461 — server DESC fetch → ASC iteration
                raw_messages = list(reversed(raw_messages))
                for m in raw_messages:
                    sender = m.get("sender_name") or f"user#{m.get('sender_id', 0)}"
                    text = m.get("text", "")
                    if not text:
                        text = m.get("body", "")
                    ts_ms = m.get("ts_ms") or 0
                    ts = datetime.fromtimestamp(ts_ms / 1000.0) if ts_ms else datetime.now()
                    is_self = m.get("sender_id") == viewer_uid
                    if self._active_chat_kind == "saved":
                        is_self = True
                    self._chat_view.add_message(
                        sender, text, ts, is_self=is_self, hide_sender=True,
                        play_sound=False,
                    )
                    msg_id = m.get("message_id") or m.get("id") or 0
                    try:
                        if isinstance(msg_id, int) and msg_id > 0:
                            _mc.insert_message(
                                msg_id=msg_id, room_id=room_id_local,
                                sender_id=int(m.get("sender_id") or 0) or 1,
                                kind=str(m.get("kind") or "text"),
                                body=text,
                                ts_ms=int(ts_ms) if ts_ms else int(ts.timestamp() * 1000),
                                is_self=is_self,
                            )
                            if msg_id > _max_msg_id:
                                _max_msg_id = msg_id
                    except Exception as exc:
                        log.debug("[dm_history] SQLite write-back 실패 — %r", exc)
                if _max_msg_id > 0:
                    self._mark_room_read(int(room_id), _max_msg_id)
                self._chat_view.scroll_to_bottom()
                log.info("[dm_history] friend=%d room=%d msgs=%d viewer=%s replay PASS",
                         friend_id, room_id, len(raw_messages), viewer_uid)
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("[dm_history] fetch 실패 — %r", exc)
