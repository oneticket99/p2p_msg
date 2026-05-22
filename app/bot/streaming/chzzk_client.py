# SPDX-License-Identifier: GPL-3.0-or-later
"""네이버 CHZZK Chat WebSocket chat client — 사이클 146 skeleton.

memory `project_bot_framework.md` (B) 방송 도우미 봇 별개 API 정합 —
네이버 CHZZK 의 chat session ingest (``wss://chat-ws.chzzk.naver.com``).

Protocol 의 핵심
----------------
- ``GET https://api.chzzk.naver.com/polling/v3/channels/<channel_id>/
  live-status`` → ``chatChannelId`` resolve.
- ``GET https://comm-api.game.naver.com/nng_main/v1/chats/access-token
  ?channelId=<chatChannelId>&chatType=STREAMING`` → ``accessToken`` 발급.
- ``wss://chat-ws.chzzk.naver.com/chat`` 연결 + CMD 100 connect packet
  (``accTkn`` + ``auth`` + ``uid``) → server 의 CMD 10000 ACK 수신.
- CMD 93101 CHAT packet 의 의 ``profile.nickname`` + ``msg`` + ``msgTime``
  추출 (JSON envelope).
- 본 cycle = websockets 부재 graceful False + skeleton receive_loop.

본 cycle 의 범위 외 (별개 cycle)
-------------------------------
- live-status polling rotation (방송 종료 detect).
- 후원 (``DONATION``) + 구독 (``SUBSCRIPTION``) event 의 의 별개 dispatch.
- CMD 0 (PING) → CMD 10000 (PONG) keepalive.
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


# CHZZK chat WebSocket endpoint (TLS)
_CHAT_WSS_URL = "wss://chat-ws.chzzk.naver.com/chat"
# live-status REST endpoint base
_LIVE_STATUS_BASE = "https://api.chzzk.naver.com/polling/v3/channels"
# access-token REST endpoint
_ACCESS_TOKEN_BASE = (
    "https://comm-api.game.naver.com/nng_main/v1/chats/access-token"
)
# channel_id 최대 길이 — CHZZK channelId hex 32자 한도
_MAX_CHANNEL_ID_LENGTH = 64
# accessToken 최대 길이 — 안전 상한
_MAX_TOKEN_LENGTH = 4096


@dataclass(slots=True)
class ChzzkChatConfig:
    """CHZZK chat client 의 연결 설정.

    Attributes
    ----------
    channel_id : str
        CHZZK 방송 channel UUID hex 32자.
    chat_channel_id : str
        live-status 의 ``chatChannelId`` (별개 polling 의 resolve).
    access_token : str
        ``chats/access-token`` 의 발급 token.
    user_id_hash : str
        viewer 의 의 hashed user_id (CHZZK 의 익명 viewer = ``""`` 가능).
    """

    channel_id: str
    chat_channel_id: str
    access_token: str
    user_id_hash: str = ""

    def __post_init__(self) -> None:
        # 한글 주석 — channel / chat_channel / token empty + 상한 검증
        if not self.channel_id:
            raise ValueError("channel_id 빈 문자열 불가")
        if len(self.channel_id) > _MAX_CHANNEL_ID_LENGTH:
            raise ValueError(
                f"channel_id 길이 초과 — {_MAX_CHANNEL_ID_LENGTH} 한도"
            )
        if not self.chat_channel_id:
            raise ValueError("chat_channel_id 빈 문자열 불가")
        if len(self.chat_channel_id) > _MAX_CHANNEL_ID_LENGTH:
            raise ValueError(
                f"chat_channel_id 길이 초과 — {_MAX_CHANNEL_ID_LENGTH} 한도"
            )
        if not self.access_token:
            raise ValueError("access_token 빈 문자열 불가")
        if len(self.access_token) > _MAX_TOKEN_LENGTH:
            raise ValueError(
                f"access_token 길이 초과 — {_MAX_TOKEN_LENGTH} 한도"
            )


class ChzzkChatClient:
    """네이버 CHZZK Chat WebSocket client skeleton.

    한글 주석 — 본 cycle 146 = websockets graceful False + skeleton receive_loop.
    실 CMD 100 connect packet + JSON envelope parse = 별개 cycle.

    Parameters
    ----------
    config : ChzzkChatConfig
        client 설정.
    on_message : Callable[[ChatMessage], Awaitable[None]] | None
        chat message 수신 callback (None = 무동작).
    """

    PLATFORM = "chzzk"
    # CHZZK chat command id
    CMD_CONNECT = 100
    CMD_CONNECT_ACK = 10000
    CMD_CHAT = 93101

    def __init__(
        self,
        config: ChzzkChatConfig,
        on_message: Optional[Callable[[object], Awaitable[None]]] = None,
    ) -> None:
        self._config = config
        self._on_message = on_message
        self._ws: Optional[object] = None
        self._connected = False
        self._sid: Optional[str] = None

    @property
    def config(self) -> ChzzkChatConfig:
        return self._config

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """cycle 169.422 — CHZZK chat WebSocket actual handshake chain.

        Returns
        -------
        bool
            연결 + CMD 10000 ACK + sid 저장 성공 여부.
        """
        if not _WS_AVAILABLE:
            log.warning("[chzzk] websockets 라이브러리 부재 — graceful False")
            return False
        import json as _json
        try:
            self._ws = await websockets.connect(_CHAT_WSS_URL)
            connect_pkt = {
                "ver": "2", "cmd": self.CMD_CONNECT, "tid": 1,
                "cid": self._config.chat_channel_id, "svcid": "game",
                "bdy": {
                    "uid": self._config.user_id_hash or None,
                    "devType": 2001,
                    "accTkn": self._config.access_token,
                    "auth": "READ",
                },
            }
            await self._ws.send(_json.dumps(connect_pkt))
            raw = await self._ws.recv()
            ack = _json.loads(raw)
            if ack.get("cmd") == self.CMD_CONNECT_ACK:
                self._sid = ack.get("bdy", {}).get("sid")
                self._connected = True
                log.info("[chzzk] connect PASS — cid=%s sid=%s", self._config.chat_channel_id, self._sid)
                return True
            log.warning("[chzzk] ACK 부재 — cmd=%s", ack.get("cmd"))
            return False
        except Exception as exc:
            log.warning("[chzzk] connect fail — %r", exc)
            self._ws = None
            return False

    async def disconnect(self) -> None:
        """WebSocket close + sid reset."""

        if self._ws is not None:
            try:
                close = getattr(self._ws, "close", None)
                if close is not None:
                    await close()
            except Exception as exc:  # pragma: no cover
                log.warning("[chzzk] disconnect 실패 — %s", exc)
        self._ws = None
        self._connected = False
        self._sid = None

    async def receive_loop(self, max_iterations: Optional[int] = None) -> List[object]:
        """cycle 169.422 — CMD 93101 CHAT packet actual parse + dispatch."""
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
                if envelope.get("cmd") == self.CMD_CHAT:
                    for entry in envelope.get("bdy", []):
                        profile_raw = entry.get("profile", "{}")
                        try:
                            profile = _json.loads(profile_raw) if isinstance(profile_raw, str) else profile_raw
                        except Exception:
                            profile = {}
                        msg = {
                            "platform": self.PLATFORM,
                            "text": entry.get("msg", ""),
                            "author": profile.get("nickname", "") if isinstance(profile, dict) else "",
                            "msg_time": entry.get("msgTime"),
                            "raw": entry,
                        }
                        messages.append(msg)
                        if self._on_message is not None:
                            try:
                                await self._on_message(msg)
                            except Exception as exc:  # pragma: no cover
                                log.warning("[chzzk] on_message exc — %r", exc)
                iters += 1
                if max_iterations is not None and iters >= max_iterations:
                    break
        except Exception as exc:  # pragma: no cover
            log.warning("[chzzk] recv loop exc — %r", exc)
        return messages
