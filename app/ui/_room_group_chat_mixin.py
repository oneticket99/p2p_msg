# SPDX-License-Identifier: GPL-3.0-or-later
"""RoomGroupChatMixin — 그룹 채팅 chain (cycle 169.521 신설).

codex 2.5 HIGH 진입 7차 — main_window.py 책임 분리.
cavecrew-investigator verdict — 367 line, HIGH risk (tight coupling __init__ state).

분리 대상 method (cycle 139~169.334 origin):
- `_on_group_info()` — GroupInfoDialog open
- `_on_chat_clear()` — chat_view + dm_history reset
- `_on_chat_leave()` — chat_list entry remove
- `_on_room_entered(room_id)` — RoomList 더블 클릭 → GroupChatView swap
- `_on_group_message_send(room_id, body)` — group message dual chain (REST + mesh)
- `_dispatch_message_chain(*, room_id, body)` — REST POST + mesh broadcast async
- `_on_open_members_panel()` — MemberList toggle

본 mixin 안 의존 attribute (MainWindow init 안 retain 의무):
- `_active_chat_kind`, `_active_chat_target_id`, `_dm_history`
- `_chat_view`, `_chat_list_panel`, `_input_container`, `_stacked`
- `_STACK_DIRECT_CHAT`, `_STACK_GROUP_CHAT`, `_STACK_MEMBERS` (class const)
- `_group_chat_view`, `_group_placeholder`, `_current_room_id`, `_active_peer_id`
- `_config`, `_state`, `_member_list`, `_messages_client`, `_group_message_client`, `_last_message_id`
- `_exec_dialog_centered(dialog)` helper
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import pyqtSlot

log = logging.getLogger(__name__)


class RoomGroupChatMixin:
    """그룹 채팅 chain mixin (cycle 169.521)."""

    # 한글 주석: 메시지 body 의 client-side 상한 — server _MAX_BODY_LEN (65535) 와 정합
    _MAX_MESSAGE_BODY_LEN: int = 65535

    def _on_group_info(self) -> None:
        """그룹 정보 보기 — GroupInfoDialog open (cycle 169.334 image #103)."""
        try:
            from app.ui.group_info_dialog import GroupInfoDialog
            kind = getattr(self, "_active_chat_kind", "group")
            target_id = getattr(self, "_active_chat_target_id", 0)
            clp = getattr(self, "_chat_list_panel", None)
            name = "?"
            if clp is not None:
                for e in getattr(clp, "_entries", []):
                    if e.kind == kind and e.target_id == target_id:
                        name = e.name
                        break
            dialog = GroupInfoDialog(group_name=name, members=[], parent=self)
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("GroupInfoDialog open 실패 — %r", exc)

    @pyqtSlot()
    def _on_chat_clear(self) -> None:
        """대화 내용 비우기 — chat_view + dm_history reset."""
        log.info("[chat_clear] active=%s/%s",
                 getattr(self, "_active_chat_kind", "?"),
                 getattr(self, "_active_chat_target_id", "?"))
        try:
            self._chat_view.clear_messages()
            key = (getattr(self, "_active_chat_kind", None),
                   getattr(self, "_active_chat_target_id", None))
            if hasattr(self, "_dm_history") and key in self._dm_history:
                self._dm_history[key] = []
        except Exception as exc:
            log.debug("chat_clear 실패 — %r", exc)

    @pyqtSlot()
    def _on_chat_leave(self) -> None:
        """삭제하고 나가기 — chat_list_panel entry remove + chat clear."""
        kind = getattr(self, "_active_chat_kind", None)
        target_id = getattr(self, "_active_chat_target_id", None)
        log.info("[chat_leave] kind=%s target=%s", kind, target_id)
        clp = getattr(self, "_chat_list_panel", None)
        if clp is None or kind is None:
            return
        entries = [e for e in getattr(clp, "_entries", [])
                   if not (e.kind == kind and e.target_id == target_id)]
        clp.set_entries(entries)
        self._chat_view.clear_messages()

    @pyqtSlot(int)
    def _on_room_entered(self, room_id: int) -> None:
        """RoomList sidebar 더블 클릭 → 그룹 채팅 진입 (cycle 139 origin)."""
        from app.ui.group_chat_view import GroupChatView

        log.info("[main_window] room_entered room_id=%s", room_id)

        # 1) 기존 GroupChatView cleanup
        if self._group_chat_view is not None:
            self._stacked.removeWidget(self._group_chat_view)
            self._group_chat_view.deleteLater()
            self._group_chat_view = None

        # 2) 신규 GroupChatView
        self_username = self._config.user_nickname
        # cycle 169.833 — 헤더 멤버 수 하드코딩 0 회수. self(방장) + 동일 방 known_peers
        # (signaling 접속 구성원) 기준 = "멤버 보기" 패널 표시 수와 정합 (방 진입 시점 count).
        # 동적 join/leave 갱신은 후속 — 본 cycle 은 "멤버 0" stub 회수 한정.
        member_count = 1 + len(getattr(self._state, "known_peers", ()) or ())
        new_view = GroupChatView(
            room_id=room_id,
            room_title=f"Room #{room_id}",
            member_count=member_count,
            self_username=self_username,
            parent=self._stacked,
        )
        new_view.message_send_requested.connect(
            lambda body, rid=room_id: self._on_group_message_send(rid, body)
        )
        new_view.members_panel_requested.connect(self._on_open_members_panel)

        # 3) StackedWidget swap
        self._stacked.insertWidget(self._STACK_GROUP_CHAT, new_view)
        if self._group_placeholder is not None:
            self._stacked.removeWidget(self._group_placeholder)
            self._group_placeholder.deleteLater()
            self._group_placeholder = None

        self._group_chat_view = new_view
        self._current_room_id = room_id
        # cycle 169.836 — room = group kind 명시. 미설정 시 직전 chat 의 kind(friend/bot)가
        # 잔존해 헤더 "..." 메뉴가 단순(채팅정보/알림/나가기) 분기로 잘못 표시됐다(사용자 발견).
        # group kind 설정 → "..." 가 group 분기(그룹 정보 보기 + 멤버 보기 + 그룹 관리 등) 노출.
        self._active_chat_kind = "group"
        self._active_chat_target_id = room_id
        # cycle 169.59 — room entry 시 active_peer_id = room_id str 형식 set
        self._active_peer_id = f"room:{room_id}"

        # 4) StackedWidget swap + 1:1 입력 영역 비활성
        self._stacked.setCurrentIndex(self._STACK_GROUP_CHAT)
        self._input_container.setVisible(False)

        # 5) AppState 갱신
        self._state.set_identity(room_id=str(room_id), peer_id=self_username)

    def _on_group_message_send(self, room_id: int, body: str) -> None:
        """GroupChatView 의 message_send_requested 핸들러 (cycle 142 actual chain).

        cycle 142 의 dual chain — REST POST + WebRTC mesh broadcast:
        1. body 검증
        2. UI append (local echo)
        3. REST POST `/api/rooms/{id}/messages`
        4. WebRTC mesh broadcast
        """
        # 1) body 검증
        if not body or not body.strip():
            log.debug("[main_window] group_message_send 빈 body — skip")
            return
        if len(body) > self._MAX_MESSAGE_BODY_LEN:
            log.warning(
                "[main_window] group_message_send body 길이 %d > %d — truncate",
                len(body), self._MAX_MESSAGE_BODY_LEN,
            )
            body = body[: self._MAX_MESSAGE_BODY_LEN]
        if room_id <= 0:
            log.warning("[main_window] group_message_send room_id 무효 — %s", room_id)
            return

        log.debug("[main_window] group_message_send room=%s body_len=%d",
                  room_id, len(body))

        # 2) UI append — local echo
        if self._group_chat_view is not None:
            self._group_chat_view.append_message(
                sender=self._config.user_nickname,
                text=body, ts=datetime.now(), is_self=True,
            )

        # 3) REST POST + 4) mesh broadcast — async
        loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            log.debug("[main_window] asyncio running loop 부재 — REST/mesh chain skip")
            return

        asyncio.ensure_future(
            self._dispatch_message_chain(room_id=room_id, body=body), loop=loop,
        )

    async def _dispatch_message_chain(self, *, room_id: int, body: str) -> None:
        """REST POST + mesh broadcast 의 async chain (cycle 142 origin)."""
        rest_ok = False
        if self._messages_client is not None:
            try:
                resp = await self._messages_client.post_message(room_id, body)
                if isinstance(resp, dict):
                    msg_id = resp.get("message_id")
                    if isinstance(msg_id, int):
                        self._last_message_id = msg_id
                        log.info(
                            "[main_window] REST POST PASS room=%s message_id=%s",
                            room_id, msg_id,
                        )
                rest_ok = True
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "[main_window] REST POST FAIL room=%s — mesh-only 모드 진입 (%r)",
                    room_id, exc,
                )
        else:
            log.debug("[main_window] messages_client 미주입 — REST skip + mesh-only")

        if self._group_message_client is not None:
            try:
                sender_id = self._current_user_id or 0
                await self._group_message_client.send_message(body, sender_id)
                log.debug(
                    "[main_window] mesh broadcast PASS room=%s rest_ok=%s",
                    room_id, rest_ok,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "[main_window] mesh broadcast FAIL room=%s rest_ok=%s — %r",
                    room_id, rest_ok, exc,
                )
        else:
            log.debug("[main_window] group_message_client 미주입 — mesh broadcast skip")

    @pyqtSlot()
    def _on_open_members_panel(self) -> None:
        """GroupChatView 의 members_panel_requested 핸들러 — 방 구성원 목록 표시.

        cycle 169.819 — 빈 stub([]) 회수. AppState 의 self peer + 동일 방 known_peers
        를 MemberItem 으로 구성한다 (signaling 기준 현재 접속 구성원). self = 방장
        표기. 서버 REST 영속 멤버(rooms_client.get_room)는 후속 결선 여지.
        """
        if self._current_room_id is None:
            return
        log.debug("[main_window] open_members_panel room=%s", self._current_room_id)

        from app.ui.member_list import MemberItem, MemberListWidget
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel

        self_peer = self._state.peer_id or self._config.user_nickname or "나"
        members = [MemberItem(user_id=0, username=self_peer, role="owner", is_online=True)]
        # 한글 주석 — 동일 방 다른 peer (signaling known_peers) 를 멤버로 추가
        for idx, peer_id in enumerate(sorted(self._state.known_peers), start=1):
            members.append(
                MemberItem(user_id=idx, username=peer_id, role="member", is_online=True)
            )

        # cycle 169.837 — StackedWidget 패널 swap → 모달 dialog (텔레그램 그룹 메뉴 = 전부 모달).
        # MemberListWidget 의 원형 아바타 행(cycle 169.837 통합)으로 표시.
        dlg = QDialog(self)
        dlg.setWindowTitle("멤버")
        dlg.setMinimumSize(340, 420)
        dlg.setStyleSheet("QDialog { background-color: #131C30; }")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(12, 12, 12, 12)
        title = QLabel(f"멤버 {len(members)}명", dlg)
        title.setStyleSheet("color: #f3f4f6; font-size: 15px; font-weight: 700; background: transparent;")
        lst = MemberListWidget(parent=dlg)
        lst.set_members(members, viewer_role="member")
        lay.addWidget(title)
        lay.addWidget(lst, stretch=1)
        # cycle 169.837 — exec()(blocking) 대신 modal+show()(non-blocking) — test event loop
        # 블록/hang 회피 + 인스턴스 참조 보유로 GC 방지(local 변수면 즉시 소멸).
        dlg.setModal(True)
        self._members_dialog = dlg
        dlg.show()
