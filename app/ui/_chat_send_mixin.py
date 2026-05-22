# SPDX-License-Identifier: GPL-3.0-or-later
"""ChatSendMixin — 1:1 채팅 송신 + DM cache 5 method (cycle 169.527 신설).

codex 2.5 MED 진입 12차 — main_window.py 책임 분리 batch.

분리 대상 method (cycle 153.7/154.2/154.3/169.160/169.411 origin):
- `_on_input_message_sent(text)` — InputBar.message_sent → _on_send_clicked
- `_on_input_file_attached(paths)` — InputBar.file_attached → DataChannel/file_sender
- `_on_chat_reply_requested(sender, text)` — ChatView reply_to_message → InputBar
- `_on_send_clicked()` — 1:1 송신 + mesh broadcast + REST POST + bot LLM chain
- `_append_dm_message(kind, target_id, sender, text, ts, is_self, reply_to)` — DM cache + local SQLite + chat_list bump + chat_view render single source

본 mixin 안 의존:
- `self._stacked`, `self._STACK_DIRECT_CHAT`, `self._input_edit`, `self._input_bar`
- `self._chat_view`, `self._chat_list_panel`, `self._config`
- `self._active_chat_kind`, `self._active_chat_target_id`, `self._dm_history`
- `self._current_user_id`, `self._mesh_manager`, `self._messages_client`
- `self._current_room_id`, `self._file_sender`
- `self._append_dm_message()` (self-ref)
- `self._send_bot_message()` (BotChatMixin)
- `self._send_saved_message_rest()`, `self._post_and_resolve()` (RestPostMixin)
- `self._kind_room_local()` (ChatHelperMixin)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import pyqtSlot

log = logging.getLogger(__name__)


class ChatSendMixin:
    """1:1 채팅 송신 + DM cache + InputBar slot chain mixin (cycle 169.527)."""

    @pyqtSlot(str)
    def _on_input_message_sent(self, text: str) -> None:
        """InputBar message_sent → 기존 _on_send_clicked chain dispatch."""
        # 한글 주석 — InputBar 의 QTextEdit 안 text 이미 clear 됨. 기존 logic 호환 의무
        if hasattr(self, "_input_edit"):
            self._input_edit.setPlainText(text)
        self._on_send_clicked()
        if hasattr(self, "_input_edit"):
            self._input_edit.clear()

    @pyqtSlot(list)
    def _on_input_file_attached(self, paths: list) -> None:
        """InputBar file_attached → DataChannel chunk transfer chain (cycle 154.2 actual)."""
        log.info("input file attached — %d file", len(paths))
        # 한글 주석 — cycle 154.2 file_sender 의존 graceful binding
        try:
            file_sender = getattr(self, "_file_sender", None)
            if file_sender is None:
                # 한글 주석 — placeholder ChatView 안 system message render
                for path in paths:
                    self._chat_view.add_message(
                        sender="system",
                        text=f"📎 첨부 (송신 대기): {path}",
                        ts=datetime.now(),
                        is_self=True,
                    )
                return
            # 한글 주석 — file_sender.send(path) async coroutine chain (cycle 119+ FileSender 정합)
            import asyncio
            for path in paths:
                asyncio.ensure_future(file_sender.send(path))
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("file attached chain 실패 — %r", exc)

    @pyqtSlot(str, str)
    def _on_chat_reply_requested(self, sender: str, text: str) -> None:
        """ChatView reply_to_message signal → InputBar reply mode set."""
        if hasattr(self, "_input_bar"):
            self._input_bar.set_reply_to(sender, text)

    def _on_send_clicked(self) -> None:
        """보내기 버튼 / Enter 키 슬롯 — 1:1 ChatView 의 의무.

        그룹 채팅 모드 (StackedWidget idx == GROUP) 일 때는 GroupChatView 의
        내부 입력창 의 책임 — 본 슬롯 은 echo 차단.
        """

        # cycle 139 — 그룹 모드 active 시 1:1 입력 차단
        if self._stacked.currentIndex() != self._STACK_DIRECT_CHAT:
            return

        # 한글 주석 — cycle 153.7 InputBar 마이그레이션 — QTextEdit `toPlainText()` 우선
        # legacy QLineEdit `text()` fallback graceful
        try:
            text = self._input_edit.toPlainText().strip()
        except AttributeError:
            text = self._input_edit.text().strip()
        if not text:
            return

        # cycle 154.3 — reply context snapshot + InputBar clear
        reply_ctx = None
        if hasattr(self, "_input_bar"):
            ctx = self._input_bar.reply_context()
            if ctx is not None:
                # 한글 주석 — ReplyContext dataclass (message_bubble) 의 instance 생성
                from app.ui.message_bubble import ReplyContext
                reply_ctx = ReplyContext(original_sender=ctx[0], original_text=ctx[1])
            self._input_bar.clear_reply_to()

        ts_now = datetime.now()
        # cycle 169.160 — single source helper _append_dm_message 호출 (active 시점 chat_view 동시 render)
        if self._active_chat_kind and self._active_chat_target_id is not None:
            self._append_dm_message(
                self._active_chat_kind,
                self._active_chat_target_id,
                self._config.user_nickname,
                text,
                ts_now,
                True,
                reply_to=reply_ctx,
            )
            # cycle 169.203 — bot kind 의 LLM 응답 chain (사용자 critique image #29)
            if self._active_chat_kind == "bot":
                import asyncio
                asyncio.ensure_future(self._send_bot_message(text))
        else:
            # active chat 부재 fallback — 기존 chat_view direct render
            self._chat_view.add_message(
                sender=self._config.user_nickname,
                text=text,
                ts=ts_now,
                is_self=True,
                reply_to=reply_ctx,
            )
        self._input_edit.clear()

        # cycle 161~163 — mesh_manager broadcast + server REST POST chain
        # MessagePayload v1.0 + ReplyToField + uuid → bubble mapping + server message_id resolve
        try:
            from app.net.message_protocol import ReplyToField, build_text_payload
            proto_reply = None
            if reply_ctx is not None:
                proto_reply = ReplyToField(
                    message_id="",
                    sender=reply_ctx.original_sender,
                    preview=reply_ctx.original_text[:60],
                )
            payload = build_text_payload(
                sender=self._config.user_nickname,
                text=text,
                reply_to=proto_reply,
            )

            # cycle 163 — client uuid → bubble mapping 등록
            try:
                self._chat_view.register_pending_bubble(payload.id)
            except Exception:  # pragma: no cover - graceful
                pass

            import asyncio
            # cycle 169.411 — saved kind 의 의 mesh skip + self DM REST POST chain
            if self._active_chat_kind == "saved":
                asyncio.ensure_future(self._send_saved_message_rest(text, payload.id))
            else:
                # 한글 주석 — mesh broadcast (DataChannel fan-out, ≤ 8 peer)
                mesh = getattr(self, "_mesh_manager", None)
                if mesh is not None:
                    asyncio.ensure_future(mesh.broadcast_payload(payload))

                # cycle 163 — server REST POST + message_id resolve chain
                msg_client = getattr(self, "_messages_client", None)
                current_room = getattr(self, "_current_room_id", None)
                if msg_client is not None and current_room:
                    asyncio.ensure_future(
                        self._post_and_resolve(msg_client, current_room, text, payload.id)
                    )
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("send chain 실패 graceful — %r", exc)

    def _append_dm_message(
        self,
        kind: str,
        target_id: int,
        sender: str,
        text: str,
        ts: "datetime",
        is_self: bool,
        reply_to: Optional[object] = None,
    ) -> None:
        """cycle 169.160 — DM cache append + active chat 시점 chat_view render single source.

        send chain + receive callback (future cycle) 동일 helper 호출 → cache 정합.
        cycle 169.163 — 1:1 chat (kind="friend" or "bot") sender label suppress (telegram align).
        """
        key = (kind, target_id)
        self._dm_history.setdefault(key, []).append((sender, text, ts, is_self))
        # cycle 169.440 — local SQLite cache write-through (사용자 directive MariaDB 부하 분담)
        # room_id mapping = bot/saved/friend kind 별 별 chain (server REST POST 의 응답 안 msg_id retain 별 cycle)
        # 본 cycle = client-only insert (msg_id 부재 시점 0 — uuid-only retain)
        try:
            from app.db import messages_cache as _mc
            # 한글 주석 — room_id derive: bot=1*10+kind_offset, friend=target_id*100, saved=self_id*100
            self_id = getattr(self, "_current_user_id", None) or 0
            sender_id = self_id if is_self else target_id
            # 한글 주석 — cycle 169.497 — _kind_room_local helper 사용 (공식 통일).
            # 이전 cycle 169.440 의 bot 공식 = target_id * 10 + 2 → cycle 169.444 안 self_id * 10 + 2 swap.
            # _load_local_history 와 read 공식 불일치 회수.
            room_id_local = self._kind_room_local(kind, target_id)
            ts_ms = int(ts.timestamp() * 1000) if ts else 0
            _mc.insert_message(
                msg_id=0,  # server msg_id 부재 — uuid-only path retain
                room_id=room_id_local,
                sender_id=int(sender_id) if sender_id else 1,
                kind="text",
                body=text,
                ts_ms=ts_ms,
                is_self=is_self,
            )
        except Exception as exc:
            log.debug("[append_dm_message] local cache 실패 — %r", exc)
        # cycle 169.174~436 — chat_list entry preview + ts bump (sort + render + unread)
        try:
            active_match = (
                self._active_chat_kind == kind and self._active_chat_target_id == target_id
            )
            log.warning(
                "[append_dm_message] bump fire — kind=%s tid=%s active_kind=%s active_tid=%s match=%s is_self=%s text=%r",
                kind, target_id, self._active_chat_kind, self._active_chat_target_id,
                active_match, is_self, text[:40],
            )
            self._chat_list_panel.bump_entry(
                kind=kind, target_id=target_id,
                last_message=text, last_ts=ts,
                last_sender=sender if not is_self else "나",
                is_self=is_self,
                active_chat_match=active_match,
            )
        except Exception as exc:
            log.warning("[append_dm_message] bump_entry 실패 — %r", exc)
        # cycle 169.437 — peer 수신 시점 sound 실시간 (사용자 directive — 포커싱 무관 의무)
        # active chat 부재 시점도 sound trigger — 메신저 기본 의무
        if not is_self and kind != "saved":
            try:
                sp = getattr(self._chat_view, "_sound_player", None)
                if sp is not None:
                    sp.play_signature()
            except Exception as exc:
                log.debug("[append_dm_message] sound trigger 실패 — %r", exc)
        # active chat 이면 chat_view render
        if self._active_chat_kind == kind and self._active_chat_target_id == target_id:
            try:
                # 1:1 chat = friend/bot/saved kind → sender label suppress (room = retain)
                hide_sender = kind in ("friend", "bot", "saved")
                # cycle 169.430 — saved kind = self DM 의 모든 msg 의 is_self=True 강제 (사용자 critique 회수)
                effective_is_self = True if kind == "saved" else is_self
                self._chat_view.add_message(
                    sender=sender, text=text, ts=ts, is_self=effective_is_self,
                    reply_to=reply_to, hide_sender=hide_sender,
                )
                # cycle 169.165 — send/receive 직후 scroll bottom 자동 (telegram align)
                self._chat_view.scroll_to_bottom()
            except Exception as exc:  # pragma: no cover - graceful
                log.debug("chat_view add_message 실패 — %r", exc)
