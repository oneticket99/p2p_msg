# SPDX-License-Identifier: GPL-3.0-or-later
"""ChatHeaderMixin — ChatHeader 8 slot chain (cycle 169.525 신설).

codex 2.5 HIGH 진입 10차 — main_window.py 책임 분리.
잔존 큰 group (378 line) — header + remote dropdown chain isolated.

분리 대상 method (cycle 169.57~426 origin):
- `_on_header_sidebar_toggle()` — room_list visibility toggle
- `_on_header_search()` — ChatListPanel filter focus
- `_on_header_call()` — CallDialog + CallClient binding (음성 통화)
- `_on_header_remote()` — 원격 제어 dropdown menu (원격 요청 + 원격 연결)
- `_on_remote_request()` — RemoteCallDialog outgoing (도움 요청)
- `_spawn_incoming_remote_modal(peer_name, kind)` — incoming modal helper
- `_on_remote_connect()` — RemoteCallDialog outgoing (제어 요청)
- `_on_header_menu()` — kind 분기 dropdown (group/channel/friend)

본 mixin 안 의존 attribute:
- `_room_list`, `_chat_list_panel`, `_active_chat_kind`, `_active_chat_target_id`
- `_config` (stun/turn), `_signaling_client`, `_active_peer_id`, `_active_call_client`
- `_exec_dialog_centered` (main_window helper)
- `_on_group_info`, `_on_chat_clear`, `_on_chat_leave` (RoomGroupChatMixin retain)
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSlot

log = logging.getLogger(__name__)


class ChatHeaderMixin:
    """ChatHeader + remote dropdown chain mixin (cycle 169.525)."""

    @pyqtSlot()
    def _on_header_sidebar_toggle(self) -> None:
        """chat header sidebar toggle button — room_list visibility toggle (cycle 169.61)."""
        visible = self._room_list.isVisible()
        self._room_list.setVisible(not visible)
        log.info("[main_window] sidebar toggle — visible=%s", not visible)

    @pyqtSlot()
    def _on_header_search(self) -> None:
        """ChatHeader 검색 button — ChatListPanel filter focus (cycle 169.63)."""
        log.info("ChatHeader 검색 click — chat list filter focus")
        if hasattr(self, "_chat_list_panel"):
            self._chat_list_panel._search_edit.setFocus()
            self._chat_list_panel._search_edit.selectAll()

    @pyqtSlot()
    def _on_header_call(self) -> None:
        """ChatHeader 통화 button — CallDialog + CallClient binding (cycle 169.57).

        음성 통화 default. 영상 toggle 가능. WebRTC SDP/ICE actual exchange =
        signaling chain 안 fire (별도 cycle).
        """
        log.info("ChatHeader 통화 click — CallDialog 진입")
        from app.ui.call_dialog import CallDialog
        from app.net.call_client import CallClient
        # cycle 169.331 — active chat peer name lookup
        peer = "상대 사용자"
        active_kind = getattr(self, "_active_chat_kind", None)
        active_target = getattr(self, "_active_chat_target_id", None)
        clp = getattr(self, "_chat_list_panel", None)
        if clp is not None and active_kind is not None:
            for entry in getattr(clp, "_entries", []):
                if entry.kind == active_kind and entry.target_id == active_target:
                    peer = entry.name or peer
                    break
        dialog = CallDialog(peer_name=peer, video_enabled=False, incoming=False, parent=self)
        stun_url = getattr(self._config, "stun_url", "stun:stun.l.google.com:19302")
        turn_url = getattr(self._config, "turn_url", "")
        turn_username = getattr(self._config, "turn_username", "")
        turn_credential = getattr(self._config, "turn_credential", "")
        # cycle 169.60 — signaling_client + peer_id + TURN inject
        signaling = getattr(self, "_signaling_client", None)
        peer_id = getattr(self, "_active_peer_id", None)
        call_client = CallClient(
            stun_url=stun_url, signaling_client=signaling, peer_id=peer_id,
            turn_url=turn_url, turn_username=turn_username, turn_credential=turn_credential,
        )
        dialog.attach_client(call_client)
        self._active_call_client = call_client
        # 통화 시점 즉시 outgoing offer fire
        import asyncio
        try:
            asyncio.ensure_future(call_client.create_offer(video=False))
        except Exception as exc:
            log.warning("[call] create_offer schedule fail — %r", exc)
        self._exec_dialog_centered(dialog)

    @pyqtSlot()
    def _on_header_remote(self) -> None:
        """원격 제어 icon → dropdown menu (원격 요청 + 원격 연결) — cycle 169.330."""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QCursor
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #131C30; color: #e5e7eb; border: 1px solid #1f2937; padding: 4px; }"
            "QMenu::item { padding: 8px 16px; border-radius: 4px; }"
            "QMenu::item:selected { background-color: #1F2937; }"
        )
        act_request = menu.addAction("원격 요청")
        act_connect = menu.addAction("원격 연결")
        act_request.triggered.connect(self._on_remote_request)  # type: ignore[arg-type]
        act_connect.triggered.connect(self._on_remote_connect)  # type: ignore[arg-type]
        menu.exec(QCursor.pos())

    @pyqtSlot()
    def _on_remote_request(self) -> None:
        """원격 요청 → RemoteCallDialog outgoing (cycle 169.426).

        원격요청 = me → 상대 PC 제어 도움 요청 (도움 제공 의도, 상대 PC 제어 의도).
        """
        try:
            from app.ui.remote_call_dialog import RemoteCallDialog
            peer = "상대 사용자"
            clp = getattr(self, "_chat_list_panel", None)
            kind = getattr(self, "_active_chat_kind", None)
            tid = getattr(self, "_active_chat_target_id", None)
            if clp is not None and kind is not None:
                for e in getattr(clp, "_entries", []):
                    if e.kind == kind and e.target_id == tid:
                        peer = e.name or peer
                        break
            dialog = RemoteCallDialog(
                peer_name=peer, mode="request", parent=self,
                outgoing_label="원격 도움 요청 발신 중… (상대 PC 제어 의도)",
            )
            # cycle 169.782 (M3c) — accept 시 controller(상대 PC 제어) 세션 기동 결선
            dialog.accepted_signal.connect(  # type: ignore[attr-defined]
                lambda p=peer: self._start_remote_session("controller", p)
            )
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("RemoteCallDialog request 실패 — %r", exc)

    def _spawn_incoming_remote_modal(
        self, peer_name: str, kind: str = "remote_request",
    ) -> None:
        """상대 peer 요청 incoming 시점 강제 modal spawn helper (cycle 169.425~426)."""
        try:
            from app.ui.remote_call_dialog import RemoteCallDialog
            label_map = {
                "voice_call": "음성 통화 수신…",
                "remote_request": "원격 도움 요청 수신… (상대 PC 제어)",
                "remote_connect": "원격 제어 요청 수신… (내 PC 제어)",
            }
            label = label_map.get(kind, "수신…")
            dialog = RemoteCallDialog(
                peer_name=peer_name, mode="incoming", parent=self,
                incoming_label=label,
            )
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("[incoming_remote] spawn 실패 kind=%s — %r", kind, exc)

    @pyqtSlot()
    def _on_remote_connect(self) -> None:
        """원격 연결 → RemoteCallDialog outgoing (cycle 169.424 회수).

        원격연결 = me → 상대 PC 제어 의도 (내 PC 제어 위임 의도).
        """
        try:
            from app.ui.remote_call_dialog import RemoteCallDialog
            peer = "상대 사용자"
            clp = getattr(self, "_chat_list_panel", None)
            kind = getattr(self, "_active_chat_kind", None)
            tid = getattr(self, "_active_chat_target_id", None)
            if clp is not None and kind is not None:
                for e in getattr(clp, "_entries", []):
                    if e.kind == kind and e.target_id == tid:
                        peer = e.name or peer
                        break
            dialog = RemoteCallDialog(
                peer_name=peer, mode="request", parent=self,
                outgoing_label="원격 제어 요청 발신 중… (내 PC 제어 위임)",
            )
            # cycle 169.782 (M3c) — accept 시 host(내 PC 제어 위임) 세션 기동 결선
            dialog.accepted_signal.connect(  # type: ignore[attr-defined]
                lambda p=peer: self._start_remote_session("host", p)
            )
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("RemoteCallDialog connect 실패 — %r", exc)

    def _start_remote_session(self, role_name: str, peer_name: str) -> None:
        """RemoteCallDialog accept → RemoteSessionRunner 기동 (cycle 169.782 M3c).

        role_name = "controller"(상대 PC 제어) / "host"(내 PC 제어 위임).
        send callable 은 friend peer connection 의 원격 DataChannel(`_remote_data_channel`)
        확립 시 결선, 미확립 시 graceful no-op (실 OS backend + 채널 binding = M4 단계).
        본 결선 = accept signal → runner 생성 + 역할/grant 보관 chain.
        """

        try:
            from app.remote.session_runner import RemoteSessionRunner, SessionRole

            role = SessionRole.HOST if role_name == "host" else SessionRole.CONTROLLER
            chan = getattr(self, "_remote_data_channel", None)
            # 한글 주석 — 채널 확립 시 send 결선, 미확립 시 graceful no-op (M4 binding 지점)
            send = (lambda b: chan.send(b)) if chan is not None else (lambda b: None)
            runner = RemoteSessionRunner(role, send_frame=send, send_input=send)
            self._remote_runner = runner
            log.info("원격 세션 runner 생성 — role=%s peer=%s", role_name, peer_name)
        except Exception as exc:
            log.warning("원격 세션 기동 실패 role=%s — %r", role_name, exc)

    @pyqtSlot()
    def _on_header_menu(self) -> None:
        """ChatHeader 메뉴 button — kind 분기 dropdown (group/channel/friend) cycle 169.334."""
        log.info("ChatHeader 메뉴 click")
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QCursor
        kind = getattr(self, "_active_chat_kind", None) or "friend"
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #131C30; color: #e5e7eb; border: 1px solid #1f2937; padding: 4px; }"
            "QMenu::item { padding: 8px 16px; border-radius: 4px; }"
            "QMenu::item:selected { background-color: #1F2937; }"
            "QMenu::separator { height: 1px; background: #1f2937; margin: 4px 0; }"
        )
        # cycle 169.837 — "..." 메뉴 = 실 구현 완료 항목만 노출 (사용자 directive: 미구현
        # 메뉴 노출 금지). 그룹 정보 보기·그룹 관리·설문 만들기·알림 끄기는 실 데이터/기능
        # 미완(Exec Plan cycle820 M3~M5)이라 메뉴서 제거 — 완성 시 재노출.
        # cycle 169.844 M4 — "room" 추가. room broadcast → 통합 ChatView 마이그레이션 후
        # 서버 room 은 _on_chat_selected("room") 통합 진입으로 _active_chat_kind="room" 이
        # 된다(이전 _on_room_entered 의 "group" 강제 폐기). group/channel 과 동일하게 멤버
        # 보기 노출 의무 — room 이 친구 메뉴(else)로 빠져 멤버 보기를 잃는 회귀 차단.
        if kind in ("group", "channel", "room"):
            # 멤버 보기 = 원형 아바타 모달(cycle 169.836~837 통합), 대화 비우기/나가기 = 실 동작
            act_members = menu.addAction("멤버 보기")
            act_clear = menu.addAction("대화 내용 비우기")
            menu.addSeparator()
            act_leave = menu.addAction("삭제하고 나가기")
            act_members.triggered.connect(self._on_open_members_panel)  # type: ignore[arg-type]
            act_clear.triggered.connect(self._on_chat_clear)  # type: ignore[arg-type]
            act_leave.triggered.connect(self._on_chat_leave)  # type: ignore[arg-type]
        else:
            act_clear_f = menu.addAction("대화 내용 비우기")
            menu.addSeparator()
            act_leave_f = menu.addAction("채팅 나가기")
            act_clear_f.triggered.connect(self._on_chat_clear)  # type: ignore[arg-type]
            act_leave_f.triggered.connect(self._on_chat_leave)  # type: ignore[arg-type]
        menu.exec(QCursor.pos())
