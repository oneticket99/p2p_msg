# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 방송 도우미 봇 4 platform actual handshake skeleton — 사이클 146.

memory `project_bot_framework.md` (B) 방송 도우미 봇 별개 API 의무 정합.

cycle 141 의 ``StreamingHelperDispatcher`` 4 platform callback chain 위 의
실 platform chat client skeleton 4 종 — YouTube Live Chat API v3 + Twitch
IRC WebSocket + 네이버 CHZZK Chat WebSocket + Kick Pusher WebSocket.

본 cycle 146 의 범위
--------------------
- ``ChatMessage`` frozen dataclass — platform/channel_id/user/message/timestamp.
- 각 client 의 connect / receive_loop / disconnect 의 skeleton (graceful False).
- httpx / websockets 부재 의 graceful import.

본 cycle 의 범위 외 (별개 cycle)
-------------------------------
- 실 OAuth2 token 발급 chain (Google + Twitch + 네이버 + Kick).
- chat message 의 의 ``StreamingHelperDispatcher`` 의 의 실 bridge.
- Pusher protocol auth + Twitch IRC CAP REQ tags + CHZZK 의 chat session.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """4 platform 의 공통 chat message dataclass.

    Attributes
    ----------
    platform : str
        platform 식별자 (``"youtube"`` / ``"twitch"`` / ``"chzzk"`` / ``"kick"``).
    channel_id : str
        platform 별 채널 식별자 (YouTube liveChatId + Twitch channel name +
        CHZZK chatChannelId + Kick channel slug 등).
    user : str
        발송 viewer 의 display name.
    message : str
        chat 본문.
    timestamp : float
        epoch seconds — 수신 시점.
    """

    platform: str
    channel_id: str
    user: str
    message: str
    timestamp: float

    def __post_init__(self) -> None:
        # 한글 주석 — empty field 차단
        if not self.platform:
            raise ValueError("platform 빈 문자열 불가")
        if not self.channel_id:
            raise ValueError("channel_id 빈 문자열 불가")
        if self.timestamp < 0:
            raise ValueError(
                f"timestamp 음수 불가 — {self.timestamp}"
            )


from app.bot.streaming.chzzk_client import ChzzkChatClient  # noqa: E402
from app.bot.streaming.kick_client import KickChatClient  # noqa: E402
from app.bot.streaming.twitch_client import TwitchChatClient  # noqa: E402

# 한글 주석 — 기존 streaming.py SSE parser 의 호환 re-export (사이클 87 → 146 의 package 의 의 흡수)
from app.bot.streaming.sse import (  # noqa: E402, F401
    StreamChunk,
    StreamEvent,
    accumulate_chunks,
    extract_anthropic_delta,
    extract_openai_delta,
    is_terminal,
    parse_sse_line,
)

__all__ = [
    "ChatMessage",
    "ChzzkChatClient",
    "KickChatClient",
    "StreamChunk",
    "StreamEvent",
    "TwitchChatClient",
    "accumulate_chunks",
    "extract_anthropic_delta",
    "extract_openai_delta",
    "is_terminal",
    "parse_sse_line",
]
