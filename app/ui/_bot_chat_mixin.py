# SPDX-License-Identifier: GPL-3.0-or-later
"""BotChatMixin — 투네이션 고객센터 bot chat 송신 + history fetch chain (cycle 169.513 신설).

codex 2.5 HIGH 진입 3차 — main_window.py 책임 분리.
TrayMixin (cycle 169.509) + FriendSearchMixin (cycle 169.511) 등가 패턴.

분리 대상 method (cycle 169.203~497 origin):
- `_send_bot_message(text)` — POST /api/bot/chat + typing indicator + reply parse +
  user_msg_id/bot_msg_id local cache insert (cycle 169.441)
- `_fetch_bot_history()` — GET /api/auth/dm/bot/room + GET /api/rooms/{id}/messages
  + cached/server merge dedup (cycle 169.497)

본 mixin 안 의존 attribute (MainWindow init 안 retain 의무):
- `_session_token`, `_current_user_id`, `_config` (api_base)
- `_active_chat_kind`, `_dm_history`, `_active_room_id_server`
- `_chat_view` (clear_messages + add_message + scroll_to_bottom)
- `_kind_room_local(kind, target_id)` (cycle 169.444 helper)
- `_append_dm_message(kind, target_id, sender, text, ts, is_self)` (cycle 169.160 helper)
"""

from __future__ import annotations
from app.core.config import DEMO_FALLBACK_API_BASE

import logging
from datetime import datetime

log = logging.getLogger(__name__)


class BotChatMixin:
    """투네이션 고객센터 bot LLM chat chain mixin (cycle 169.513).

    MainWindow MRO 안 본 mixin 가 retain — `class MainWindow(..., BotChatMixin, QMainWindow)`.
    """

    async def _send_bot_message(self, text: str) -> None:
        """투네이션 고객센터 bot LLM 응답 chain (cycle 169.203 origin).

        POST /api/bot/chat → reply.content → DM cache append.
        graceful exception (server fail 시 system message render).
        """
        import time
        import aiohttp
        from app.ui.typing_indicator import TypingIndicator

        # cycle 169.288 — typing indicator 표시 (사용자 directive image #58/62)
        # cycle 169.432 — active chat 의 bot kind 검증 의무 (cross-leak 차단)
        typing = TypingIndicator(parent=self._chat_view._content)
        if self._active_chat_kind == "bot":
            try:
                # 한글 주석 — stretch slot 직전 insertWidget (chat_view layout 정합)
                insert_at = max(0, self._chat_view._messages_layout.count() - 1)
                self._chat_view._messages_layout.insertWidget(insert_at, typing)
                self._chat_view._scroll_to_bottom_once()
            except Exception:  # pragma: no cover - graceful
                pass
        try:
            api_base = getattr(self._config, "api_base", None) or DEMO_FALLBACK_API_BASE
            token = getattr(self, "_session_token", None) or ""
            # cycle 169.263 — bot 401 retain root cause trace log
            log.warning(
                "[bot_chat] token_present=%s token_len=%d api_base=%s",
                bool(token), len(token), api_base,
            )
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            payload = {
                "messages": [
                    {"role": "user", "content": text, "timestamp_ms": int(time.time() * 1000)},
                ],
            }
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    f"{api_base}/api/bot/chat", json=payload, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    # cycle 169.209 — ContentTypeError 회수 — content_type=None force parse
                    text_body = await resp.text()
                    status = resp.status
                    if status != 200:
                        log.warning("[bot_chat] HTTP %d body=%s", status, text_body[:200])
                        reply = f"⚠️ 서버 응답 부재 (HTTP {status}). 잠시 후 다시 시도해주세요."
                    else:
                        try:
                            import json as _json
                            data = _json.loads(text_body)
                            reply = data.get("reply", {}).get("content", "응답 부재")
                            # cycle 169.441 — server msg_id capture + local cache write-through
                            _user_msg_id = data.get("user_msg_id")
                            _bot_msg_id = data.get("bot_msg_id")
                            try:
                                from app.db import messages_cache as _mc
                                import time as _t
                                self_id = getattr(self, "_current_user_id", None) or 1
                                bot_room = self_id * 10 + 2  # bot kind local namespace
                                now_ms = int(_t.time() * 1000)
                                if isinstance(_user_msg_id, int) and _user_msg_id > 0:
                                    _mc.insert_message(
                                        msg_id=_user_msg_id, room_id=bot_room,
                                        sender_id=self_id, body=text,
                                        ts_ms=now_ms - 1000, is_self=True,
                                    )
                                if isinstance(_bot_msg_id, int) and _bot_msg_id > 0:
                                    _mc.insert_message(
                                        msg_id=_bot_msg_id, room_id=bot_room,
                                        sender_id=1, body=reply,
                                        ts_ms=now_ms, is_self=False,
                                    )
                            except Exception as exc:
                                log.debug("[bot_chat] local cache 실패 — %r", exc)
                        except _json.JSONDecodeError:
                            log.warning("[bot_chat] JSON parse 실패 — body=%s", text_body[:200])
                            reply = "⚠️ 응답 형식 오류. 잠시 후 다시 시도해주세요."
        except Exception as exc:  # pragma: no cover - graceful
            log.warning("[bot_chat] LLM 호출 실패 — %r", exc)
            reply = f"⚠️ 서버 연결 실패 — {exc.__class__.__name__}. 데모 서버 점검 중일 수 있습니다."
        finally:
            # cycle 169.288~432 — typing indicator 제거 (응답 도착 또는 graceful 분기)
            try:
                typing.stop()
                typing.setParent(None)
                typing.deleteLater()
            except Exception:  # pragma: no cover - graceful
                pass
        # cycle 169.432 — bot 응답 cache append (active 무관)
        self._append_dm_message(
            "bot", 1, "투네이션 고객센터", reply, datetime.now(), is_self=False,
        )

    async def _fetch_bot_history(self) -> None:
        """bot chat history server fetch chain (cycle 169.445~454 origin + 169.497 merge).

        GET /api/auth/dm/bot/room → bot-{uid} room_id resolve.
        + GET /api/rooms/{rid}/messages bulk + cached/server merge dedup + SQLite write-back.
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
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.get(
                    f"{api_base}/api/auth/dm/bot/room",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return
                    dm = await resp.json()
                    room_id = dm.get("room_id")
                if not room_id:
                    return
                async with session.get(
                    f"{api_base}/api/rooms/{room_id}/messages?limit=50&offset=0",
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return
                    page = await resp.json()
                    raw_messages = page.get("messages", [])
            if self._active_chat_kind == "bot":
                # 한글 주석 — cycle 169.497 — cached + server merge (bot reply 사라짐 회수)
                from app.db import messages_cache as _mc
                room_id_local = self._kind_room_local("bot", 1)
                # cycle 169.461 — server DESC fetch → ASC iteration (사용자 critique image #24)
                raw_messages = list(reversed(raw_messages))
                key = ("bot", 1)
                existing = set()
                for sender_e, text_e, ts_e, is_self_e in self._dm_history.get(key, []):
                    existing.add((bool(is_self_e), str(text_e), int(ts_e.timestamp() * 1000) if ts_e else 0))
                new_entries: list = []
                for m in raw_messages:
                    sender_id = int(m.get("sender_id") or 0)
                    is_self = sender_id == self_id
                    sender = "투네이션 고객센터" if not is_self else "나"
                    text = m.get("body") or m.get("text") or ""
                    ts_ms = m.get("ts_ms") or 0
                    ts = datetime.fromtimestamp(ts_ms / 1000.0) if ts_ms else datetime.now()
                    triplet = (is_self, text, int(ts_ms))
                    if triplet in existing:
                        continue
                    new_entries.append((sender, text, ts, is_self, sender_id))
                    msg_id = m.get("message_id") or m.get("id") or 0
                    if isinstance(msg_id, int) and msg_id > 0:
                        try:
                            _mc.insert_message(
                                msg_id=msg_id, room_id=room_id_local,
                                sender_id=sender_id or 1, body=text,
                                ts_ms=int(ts_ms) if ts_ms else int(ts.timestamp() * 1000),
                                is_self=is_self,
                            )
                        except Exception:
                            pass
                # 한글 주석 — cycle 169.497 — server full row truth + cached fallback
                if new_entries or not self._dm_history.get(key):
                    self._chat_view.clear_messages()
                    merged: list = []
                    for m in raw_messages:
                        sender_id = int(m.get("sender_id") or 0)
                        is_self = sender_id == self_id
                        sender = "투네이션 고객센터" if not is_self else "나"
                        text = m.get("body") or m.get("text") or ""
                        ts_ms = m.get("ts_ms") or 0
                        ts = datetime.fromtimestamp(ts_ms / 1000.0) if ts_ms else datetime.now()
                        merged.append((sender, text, ts, is_self))
                    server_set = set()
                    for s, t, ts_v, slf in merged:
                        server_set.add((slf, t, int(ts_v.timestamp() * 1000) if ts_v else 0))
                    for sender_e, text_e, ts_e, is_self_e in self._dm_history.get(key, []):
                        triplet = (bool(is_self_e), str(text_e), int(ts_e.timestamp() * 1000) if ts_e else 0)
                        if triplet not in server_set:
                            merged.append((sender_e, text_e, ts_e, bool(is_self_e)))
                    merged.sort(key=lambda x: int(x[2].timestamp() * 1000) if x[2] else 0)
                    for sender, text, ts, is_self in merged:
                        self._chat_view.add_message(
                            sender, text, ts, is_self=is_self, hide_sender=True,
                            play_sound=False,
                        )
                    self._dm_history[key] = list(merged)
                self._chat_view.scroll_to_bottom()
                self._active_room_id_server = int(room_id)
                log.info("[bot_history] room=%d msgs=%d new=%d replay PASS",
                         room_id, len(raw_messages), len(new_entries))
        except Exception as exc:
            log.debug("[bot_history] 실패 — %r", exc)
