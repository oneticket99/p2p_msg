# SPDX-License-Identifier: GPL-3.0-or-later
"""RoomGroupChatMixin — 그룹 채팅 chain (cycle 169.521 신설).

codex 2.5 HIGH 진입 7차 — main_window.py 책임 분리.
cavecrew-investigator verdict — 367 line, HIGH risk (tight coupling __init__ state).

분리 대상 method (cycle 139~169.334 origin):
- `_on_group_info()` — GroupInfoDialog open
- `_on_chat_clear()` — chat_view + dm_history reset
- `_on_chat_leave()` — chat_list entry remove
- `_on_open_members_panel()` — 멤버 보기 in-app 모달 (cycle 169.838)

cycle 169.845 M5 — legacy GroupChatView 경로(`_on_room_entered` + `_on_group_message_send`
+ `_dispatch_message_chain`) 회수. room broadcast → 통합 ChatView 마이그레이션 M4 후
사용자 도달 불가 확정 → 물리 제거. room/group 송신은 통합 `_on_send_clicked`
(mesh + REST) 단일 경로. 멤버 보기(`_on_open_members_panel`)는 in-app 모달로 유지.

본 mixin 안 의존 attribute (MainWindow init 안 retain 의무):
- `_active_chat_kind`, `_active_chat_target_id`, `_chat_view`, `_chat_list_panel`
- `_current_room_id`, `_config`, `_state`, `_exec_dialog_centered(dialog)` helper
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

    @pyqtSlot()
    def _on_open_members_panel(self) -> None:
        """멤버 보기 — 방 구성원 목록 in-app 모달 (cycle 169.838).

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

        # cycle 169.838 — 별도 OS 윈도우(QDialog.show) → 메인 레이아웃 안 in-app overlay 모달.
        # 사용자 directive: 얼럿창(별도 윈도우) 금지, 메인 레이아웃 안 모달. _exec_dialog_centered
        # (backdrop dim + child overlay + manual modal loop)로 다른 dialog 들과 동일 처리.
        dlg = QDialog(self)
        dlg.setWindowTitle("멤버")
        dlg.setFixedSize(360, 440)
        dlg.setStyleSheet("QDialog { background-color: #131C30; }")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        title = QLabel(f"멤버 {len(members)}명", dlg)
        title.setStyleSheet("color: #f3f4f6; font-size: 15px; font-weight: 700; background: transparent;")
        lst = MemberListWidget(parent=dlg)
        lst.set_members(members, viewer_role="member")
        lay.addWidget(title)
        lay.addWidget(lst, stretch=1)
        self._members_dialog = dlg  # 참조 보유 (test 검증 + GC 방지)
        self._exec_dialog_centered(dlg)
