# SPDX-License-Identifier: GPL-3.0-or-later
"""Kick Pusher WebSocket chat client — 사이클 146 skeleton.

memory `project_bot_framework.md` (B) 방송 도우미 봇 별개 API 정합 —
Kick 의 Pusher (소프트웨어 회사 Pusher.com) WebSocket 위 의 chat ingest.

Protocol 의 핵심
----------------
- ``GET https://kick.com/api/v2/channels/<slug>`` → ``chatroom.id`` resolve.
- ``wss://ws-us2.pusher.com/app/<key>?protocol=7&client=js&version=8.4.0``
  연결 + ``pusher:subscribe`` event 의 ``channel.<chatroom_id>`` 구독.
- private channel 의 의 ``pusher:auth`` HMAC-SHA256 signature 의무 (public
  chat = 무인증 가능).
- ``App\\Events\\ChatMessageEvent`` event 의 ``data`` JSON payload 의
  ``sender.username`` + ``content`` + ``created_at`` 추출.
- ``pusher:ping`` → ``pusher:pong`` keepalive (60초 timeout 기본).
- 본 cycle = websockets 부재 graceful False + skeleton receive_loop.

본 cycle 의 범위 외 (별개 cycle)
-------------------------------
- private channel HMAC signing chain.
- gift sub / host / raid event 의 의 별개 dispatch.
- pusher cluster latency-aware fallback (ws-us2 / ws-eu / ws-ap1).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional

log = logging.getLogger(__name__)

# 한글 주석 — websockets optional import (graceful False 의무)
try:
    import websockets  # type: ignore[import-not-found]

    _WS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _WS_AVAILABLE = False


# Kick Pusher WebSocket endpoint base (us2 cluster default)
_PUSHER_WSS_BASE = "wss://ws-us2.pusher.com/app"
# Pusher protocol version
_PUSHER_PROTOCOL = "7"
# channel slug 최대 길이 — Kick username 25자 한도
_MAX_SLUG_LENGTH = 25
# chatroom id 최대 길이 — int 표현 안전 상한
_MAX_CHATROOM_ID_LENGTH = 32
# app_key 최대 길이 — Pusher key 안전 상한
_MAX_APP_KEY_LENGTH = 64


@dataclass(slots=True)
class KickChatConfig:
    """Kick Pusher chat client 의 연결 설정.

    Attributes
    ----------
    channel_slug : str
        Kick channel slug (lowercase, 예: ``"adin"``).
    chatroom_id : str
        ``api/v2/channels/<slug>`` 의 ``chatroom.id`` (int → str).
    pusher_app_key : str
        Kick 의 Pusher app key (public — 클라이언트 의 hard-coded 정합).
    auth_token : str
        Kick OAuth2 token (private event 의무, public chat = ``""``).
    """

    channel_slug: str
    chatroom_id: str
    pusher_app_key: str
    auth_token: str = ""

    def __post_init__(self) -> None:
        # 한글 주석 — slug / chatroom / key empty + 상한 검증
        if not self.channel_slug:
            raise ValueError("channel_slug 빈 문자열 불가")
        if len(self.channel_slug) > _MAX_SLUG_LENGTH:
            raise ValueError(
                f"channel_slug 길이 초과 — {_MAX_SLUG_LENGTH} 한도"
            )
        if not self.chatroom_id:
            raise ValueError("chatroom_id 빈 문자열 불가")
        if len(self.chatroom_id) > _MAX_CHATROOM_ID_LENGTH:
            raise ValueError(
                f"chatroom_id 길이 초과 — {_MAX_CHATROOM_ID_LENGTH} 한도"
            )
        if not self.pusher_app_key:
            raise ValueError("pusher_app_key 빈 문자열 불가")
        if len(self.pusher_app_key) > _MAX_APP_KEY_LENGTH:
            raise ValueError(
                f"pusher_app_key 길이 초과 — {_MAX_APP_KEY_LENGTH} 한도"
            )


class KickChatClient:
    """Kick Pusher WebSocket chat client skeleton.

    한글 주석 — 본 cycle 146 = websockets graceful False + skeleton receive_loop.
    실 pusher:subscribe + ChatMessageEvent JSON parse = 별개 cycle.

    Parameters
    ----------
    config : KickChatConfig
        client 설정.
    on_message : Callable[[ChatMessage], Awaitable[None]] | None
        chat message 수신 callback (None = 무동작).
    """

    PLATFORM = "kick"
    # Pusher protocol event id
    EVENT_SUBSCRIBE = "pusher:subscribe"
    EVENT_PING = "pusher:ping"
    EVENT_PONG = "pusher:pong"
    EVENT_CHAT = "App\\Events\\ChatMessageEvent"

    def __init__(
        self,
        config: KickChatConfig,
        on_message: Optional[Callable[[object], Awaitable[None]]] = None,
    ) -> None:
        self._config = config
        self._on_message = on_message
        self._ws: Optional[object] = None
        self._connected = False
        self._socket_id: Optional[str] = None

    @property
    def config(self) -> KickChatConfig:
        return self._config

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """cycle 169.422 — Kick Pusher WebSocket actual handshake chain."""
        if not _WS_AVAILABLE:
            log.warning("[kick] websockets 라이브러리 부재 — graceful False")
            return False
        import json as _json
        try:
            url = (
                f"{_PUSHER_WSS_BASE}/{self._config.pusher_app_key}"
                f"?protocol={_PUSHER_PROTOCOL}&client=tootalk&version=1.0"
            )
            self._ws = await websockets.connect(url)
            hello_raw = await self._ws.recv()
            hello = _json.loads(hello_raw)
            data = hello.get("data")
            if isinstance(data, str):
                data = _json.loads(data)
            self._socket_id = data.get("socket_id") if isinstance(data, dict) else None
            await self._ws.send(_json.dumps({
                "event": self.EVENT_SUBSCRIBE,
                "data": {"channel": f"chatrooms.{self._config.chatroom_id}.v2"},
            }))
            self._connected = True
            log.info("[kick] connect PASS — chatroom=%s socket=%s",
                     self._config.chatroom_id, self._socket_id)
            return True
        except Exception as exc:
            log.warning("[kick] connect fail — %r", exc)
            self._ws = None
            return False

    async def disconnect(self) -> None:
        """WebSocket close + socket_id reset."""

        if self._ws is not None:
            try:
                close = getattr(self._ws, "close", None)
                if close is not None:
                    await close()
            except Exception as exc:  # pragma: no cover
                log.warning("[kick] disconnect 실패 — %s", exc)
        self._ws = None
        self._connected = False
        self._socket_id = None

    async def receive_loop(self, max_iterations: Optional[int] = None) -> List[object]:
        """cycle 169.422 — Kick Pusher ChatMessageEvent actual parse + dispatch."""
        if not self._connected or self._ws is None:
            return []
        import json as _json
        messages: List[object] = []
        iters = 0
        try:
            async for raw in self._ws:
                try:
                    envelope = _json.loads(raw)
                except Exception:
                    continue
                event = envelope.get("event")
                if event == self.EVENT_PING:
                    await self._ws.send(_json.dumps({"event": self.EVENT_PONG, "data": {}}))
                    continue
                if event == self.EVENT_CHAT:
                    data = envelope.get("data")
                    if isinstance(data, str):
                        try:
                            data = _json.loads(data)
                        except Exception:
                            data = {}
                    sender = data.get("sender", {}) if isinstance(data, dict) else {}
                    msg = {
                        "platform": self.PLATFORM,
                        "text": data.get("content", "") if isinstance(data, dict) else "",
                        "author": sender.get("username", "") if isinstance(sender, dict) else "",
                        "sender_id": sender.get("id") if isinstance(sender, dict) else None,
                        "raw": envelope,
                    }
                    messages.append(msg)
                    if self._on_message is not None:
                        try:
                            await self._on_message(msg)
                        except Exception as exc:  # pragma: no cover
                            log.warning("[kick] on_message exc — %r", exc)
                iters += 1
                if max_iterations is not None and iters >= max_iterations:
                    break
        except Exception as exc:  # pragma: no cover
            log.warning("[kick] recv loop exc — %r", exc)
        return messages
