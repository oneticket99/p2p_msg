# SPDX-License-Identifier: GPL-3.0-or-later
"""ChatNavigationMixin — chat_list panel populate + sidebar tab + chat select 3 method (cycle 169.526 신설).

codex 2.5 LOW 진입 11차 — main_window.py 책임 분리 batch.

분리 대상 method (cycle 169.106/136/62 origin):
- `_refresh_chat_list_panel()` — friend/room/bot 통합 ChatListEntry 변환 + populate
- `_on_sidebar_tab_clicked(tab_key)` — SidebarRail tab → stacked widget index
- `_on_chat_selected(kind, target_id)` — chat 진입 chain (header/view/cache replay)

본 mixin 안 의존:
- `self._friend_list`, `self._room_list`, `self._chat_list_panel`
- `self._chat_view`, `self._chat_header`, `self._input_container`, `self._stacked`
- `self._STACK_DIRECT_CHAT`, `self._STACK_FRIENDS`, `self._sidebar_rail`
- `self._active_chat_kind`, `self._active_chat_target_id`, `self._current_user_id`
- `self._user_folders`, `self._active_folder_dialog`, `self._dm_history`
- `self._on_room_entered()`, `self._fetch_user_status()`, `self._fetch_dm_history()`
- `self._fetch_bot_history()`, `self._kind_room_local()`, `self._load_local_history()`
- `self._on_folder_create_requested()`, `self._on_folder_delete_requested()`
- `self._on_folder_edit_requested()`, `self._exec_dialog_centered()`
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSlot

log = logging.getLogger(__name__)


class ChatNavigationMixin:
    """chat_list populate + sidebar tab + chat select chain mixin (cycle 169.526)."""

    def _refresh_chat_list_panel(self) -> None:
        """친구 + 방 + 봇 data 의 ChatListEntry 변환 + chat_list_panel populate (cycle 169.106).

        사용자 directive — "chatlist 는 추가된 친구 + 단톡방 + 봇톡 출력".
        default seed (투네이션 고객센터 봇) retain + friend/room 실 data 추가.
        """
        from datetime import datetime
        from app.ui.chat_list_panel import ChatListEntry

        entries: list[ChatListEntry] = []

        # 한글 주석 — 투네이션 고객센터 봇 default (pinned + online)
        entries.append(
            ChatListEntry(
                kind="bot",
                target_id=1,
                name="투네이션 고객센터",
                last_message="안녕하세요. 무엇을 도와드릴까요? 24시간 LLM 상담 chain.",
                last_ts=datetime.now(),
                unread_count=0,
                is_pinned=True,
                is_online=True,
            )
        )

        # 한글 주석 — friend_list 안 friends → ChatListEntry kind=friend 변환
        friends = getattr(self._friend_list, "_friends", [])
        for fr in friends:
            uid = getattr(fr, "user_id", None) or getattr(fr, "id", None) or 0
            name = getattr(fr, "username", None) or getattr(fr, "display_name", None) or f"friend_{uid}"
            online = bool(getattr(fr, "is_online", False) or getattr(fr, "online", False))
            entries.append(
                ChatListEntry(
                    kind="friend",
                    target_id=int(uid),
                    name=str(name),
                    last_message="",
                    last_ts=None,
                    unread_count=0,
                    is_pinned=False,
                    is_online=online,
                )
            )

        # 한글 주석 — room_list 안 rooms → ChatListEntry kind=room 변환
        rooms = getattr(self._room_list, "_rooms", []) if hasattr(self, "_room_list") else []
        for rm in rooms:
            rid = getattr(rm, "room_id", None) or getattr(rm, "id", None) or 0
            rname = getattr(rm, "name", None) or getattr(rm, "title", None) or f"room_{rid}"
            entries.append(
                ChatListEntry(
                    kind="room",
                    target_id=int(rid),
                    name=str(rname),
                    last_message="",
                    last_ts=None,
                    unread_count=0,
                    is_pinned=False,
                    is_online=False,
                )
            )

        self._chat_list_panel.set_entries(entries)
        log.info(
            "[main_window] chat_list_panel refresh — bot=1 friend=%d room=%d",
            len(friends), len(rooms),
        )
        # cycle 169.202 — re-populate 후 active chat retain 또는 default 진입 (사용자 critique image #28)
        if self._active_chat_kind and self._active_chat_target_id is not None:
            try:
                self._chat_list_panel.set_current_chat(
                    self._active_chat_kind, self._active_chat_target_id,
                )
            except Exception:
                pass
        else:
            # 빈 chat default 회피 — 투네이션 고객센터 bot 진입
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._on_chat_selected("bot", 1))

    @pyqtSlot(str)
    def _on_sidebar_tab_clicked(self, tab_key: str) -> None:
        """SidebarRail tab 변경 — stacked widget index 매핑.

        tab_key ∈ {"friends", "rooms", "bots", "settings"} (telegram align label = 채팅/연락처/통화/설정)
        cycle 169.136 — bot_panel 폐기 + chat_list 통합 (사용자 ack)
        - friends("채팅") = chat_list 통합 view (이미 friend + room + bot entry populate chain — cycle 169.106)
        - rooms("연락처") = friends widget (연락처 list)
        - bots("통화") = call placeholder (Phase 5 actual binding)
        - settings = SettingsDialog modal
        """
        if tab_key == "friends":
            # cycle 169.185 — "모든 대화방" 통합 view (default — chat_list 친구+방+봇 통합)
            # cycle 169.283 — 사용자 critique image #55/56/57 회수 — chat_header clear 폐기 (active chat retain)
            self._stacked.setCurrentIndex(self._STACK_DIRECT_CHAT)
        elif tab_key == "settings":
            # cycle 169.193 — 편집 tab = FolderManageDialog modal (telegram 폴더 편집 — 사용자 directive 회수)
            # cycle 169.230 — dialog main 안 centered + height clamp
            try:
                from app.ui.folder_manage_dialog import FolderManageDialog
                user_folders = getattr(self, "_user_folders", [])
                dialog = FolderManageDialog(user_folders=user_folders, parent=self)
                # cycle 169.369 — folder_create_requested connect chain (사용자 critique image #123/124 '+ 새 폴더 만들기' 무반응 회수)
                dialog.folder_create_requested.connect(self._on_folder_create_requested)  # type: ignore[arg-type]
                dialog.folder_delete_requested.connect(self._on_folder_delete_requested)  # type: ignore[arg-type]
                # cycle 169.381 — folder_edit_requested chain (사용자 critique image #139/140 수정 button)
                dialog.folder_edit_requested.connect(self._on_folder_edit_requested)  # type: ignore[arg-type]
                # cycle 169.373 — active dialog reference retain (만들기 완료 시점 close chain)
                self._active_folder_dialog = dialog
                self._exec_dialog_centered(dialog)
                self._active_folder_dialog = None
            except Exception as exc:  # pragma: no cover - graceful
                log.debug("FolderManageDialog open 실패 graceful — %r", exc)
            self._sidebar_rail.set_active_tab("friends")
            self._on_sidebar_tab_clicked("friends")
            # cycle 169.305 — 사용자 critique image #74/75 — dialog close 後 chat_list_panel 의 visibility 강제 retain
            if hasattr(self, "_chat_list_panel"):
                self._chat_list_panel.show()
                self._chat_list_panel.update()

    def _on_chat_selected(self, kind: str, target_id: int) -> None:
        """ChatListPanel.chat_selected → group room 진입 또는 friend/bot chat 진입 (cycle 169.62)."""
        log.info("[main_window] chat_selected kind=%s target_id=%d", kind, target_id)
        if kind == "room":
            self._on_room_entered(target_id)
            return
        # 한글 주석 — cycle 169.107 회수 — entry 안 name + status lookup chain
        # cycle 169.159 — telegram align fallback "최근에 접속함" (actual last_seen REST = 별 cycle)
        chat_panel = getattr(self, "_chat_list_panel", None)
        name = f"{kind}:{target_id}"
        status = "최근에 접속함"
        if chat_panel is not None:
            for entry in getattr(chat_panel, "_entries", []):
                if entry.kind == kind and entry.target_id == target_id:
                    name = entry.name
                    status = "온라인" if entry.is_online else "최근에 접속함"
                    break
        self._chat_header.set_chat(name, status=status)
        # cycle 169.221 — friend kind 시점 last_seen REST fetch (cycle 169.216 endpoint 연동)
        # cycle 169.225 — DM history fetch (cycle 169.222 DM room resolve + list_messages)
        # 한글 주석 — cycle 169.572: asyncio.ensure_future graceful guard (python 3.13 안 running loop 부재 시 DeprecationWarning + fail)
        # test setup (qasync 부재 환경) 안 fail 회수. running loop 시점 만 schedule.
        import asyncio
        try:
            _loop = asyncio.get_running_loop()
        except RuntimeError:
            _loop = None
        if _loop is not None:
            if kind == "friend" and target_id > 0:
                asyncio.ensure_future(self._fetch_user_status(target_id))
                asyncio.ensure_future(self._fetch_dm_history(target_id))
            # cycle 169.411 — saved messages history fetch chain
            if kind == "saved":
                self_id = getattr(self, "_current_user_id", None)
                if isinstance(self_id, int) and self_id > 0:
                    asyncio.ensure_future(self._fetch_dm_history(self_id))
            # cycle 169.454 — bot kind history fetch chain
            if kind == "bot":
                asyncio.ensure_future(self._fetch_bot_history())
        # cycle 169.156~157 — chat 전환 + DM cache replay (image #12 telegram 동작성)
        try:
            # cycle 169.176 — prev active chat 의 scroll offset save (전환 직전)
            self._chat_view.save_scroll_offset()
            self._chat_view.clear_messages()
            self._active_chat_kind = kind
            self._active_chat_target_id = target_id
            # cycle 169.157 — cache replay (server REST fetch = 별 cycle 169.158+)
            # cycle 169.163 — 1:1 chat (friend/bot) sender label suppress propagate
            # cycle 169.441 — local SQLite 우선 replay (in-memory cache 부재 시점 fallback)
            hide_sender = kind in ("friend", "bot", "saved")
            cached = self._dm_history.get((kind, target_id), [])
            if cached:
                for sender, text, ts, is_self in cached:
                    # cycle 169.462 — history replay 시점 sound 차단 (사용자 critique)
                    self._chat_view.add_message(
                        sender, text, ts, is_self=is_self, hide_sender=hide_sender,
                        play_sound=False,
                    )
            else:
                # 한글 주석 — in-memory cache miss → local SQLite history replay (사용자 directive 영속)
                self._load_local_history(kind, target_id)
            # cycle 169.444 — chat_view active room_id 갱신 (lazy load cursor base)
            self._chat_view.set_active_room(self._kind_room_local(kind, target_id))
            # cycle 169.457 — chat focus 시점 모든 peer bubble 자동 읽음 처리 (사용자 directive 정합)
            try:
                self._chat_view.mark_all_bubbles_read()
            except Exception as exc:
                log.debug("[chat_focus] mark_read 실패 — %r", exc)
            # cycle 169.176 — prev offset restore 시도 + 부재 시 bottom fallback
            restored = self._chat_view.restore_scroll_offset(kind, target_id)
            if not restored:
                self._chat_view.scroll_to_bottom()
            # cycle 169.167 — chat_list selected row sync (programmatic 진입 path 정합)
            try:
                self._chat_list_panel.set_current_chat(kind, target_id)
            except Exception:  # pragma: no cover - graceful
                pass
            log.info("[main_window] chat switched — kind=%s target=%d replay=%d restored=%s",
                     kind, target_id, len(cached), restored)
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("chat_view switch 실패 — %r", exc)
        self._stacked.setCurrentIndex(self._STACK_DIRECT_CHAT)
        self._input_container.setVisible(True)
