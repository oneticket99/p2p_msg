# SPDX-License-Identifier: GPL-3.0-or-later
"""Twitch IRC WebSocket chat client — 사이클 146 skeleton.

memory `project_bot_framework.md` (B) 방송 도우미 봇 별개 API 정합 —
Twitch IRC over WebSocket (``wss://irc.chat.twitch.tv:443``) 의 chat ingest.

Protocol 의 핵심
----------------
- ``wss://irc.chat.twitch.tv:443`` 연결 + ``PASS oauth:<token>`` + ``NICK
  <bot_login>`` + ``JOIN #<channel>`` 의 ordered handshake.
- ``CAP REQ :twitch.tv/tags twitch.tv/commands`` 의 의 extended message tags
  (badges + bits + emotes) 의무.
- ``PRIVMSG #<channel> :<msg>`` line 의 parse — IRCv3 message-tags prefix
  + sender prefix (``<user>!<user>@<user>.tmi.twitch.tv``) + command +
  trailing 추출.
- ``PING :tmi.twitch.tv`` → ``PONG :tmi.twitch.tv`` 의 의 keepalive 의무.
- 본 cycle = websockets 부재 graceful False + skeleton receive_loop.

본 cycle 의 범위 외 (별개 cycle)
-------------------------------
- 실 OAuth2 device code flow.
- bits / sub / raid event 의 의 별개 dispatch.
- USERSTATE / ROOMSTATE / GLOBALUSERSTATE 의 의 parse.
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


# Twitch IRC WebSocket endpoint (TLS 443)
_IRC_WSS_URL = "wss://irc.chat.twitch.tv:443"
# channel name 최대 길이 — Twitch login 25자 한도
_MAX_CHANNEL_LENGTH = 25
# bot_login 최대 길이 — Twitch login 25자 한도
_MAX_LOGIN_LENGTH = 25
# oauth token 최대 길이 — Twitch token 안전 상한
_MAX_TOKEN_LENGTH = 1024


@dataclass(slots=True)
class TwitchChatConfig:
    """Twitch IRC chat client 의 연결 설정.

    Attributes
    ----------
    oauth_token : str
        Twitch OAuth2 token (``chat:read`` scope 의무, ``oauth:`` prefix 제외).
    bot_login : str
        bot 의 Twitch login name (lowercase).
    channel : str
        대상 channel name (lowercase, ``#`` prefix 제외).
    """

    oauth_token: str
    bot_login: str
    channel: str

    def __post_init__(self) -> None:
        # 한글 주석 — token / login / channel 의 empty + 상한 검증
        if not self.oauth_token:
            raise ValueError("oauth_token 빈 문자열 불가")
        if len(self.oauth_token) > _MAX_TOKEN_LENGTH:
            raise ValueError(
                f"oauth_token 길이 초과 — {_MAX_TOKEN_LENGTH} 한도"
            )
        if not self.bot_login:
            raise ValueError("bot_login 빈 문자열 불가")
        if len(self.bot_login) > _MAX_LOGIN_LENGTH:
            raise ValueError(
                f"bot_login 길이 초과 — {_MAX_LOGIN_LENGTH} 한도"
            )
        if not self.channel:
            raise ValueError("channel 빈 문자열 불가")
        if self.channel.startswith("#"):
            raise ValueError("channel '#' prefix 제외 의무")
        if len(self.channel) > _MAX_CHANNEL_LENGTH:
            raise ValueError(
                f"channel 길이 초과 — {_MAX_CHANNEL_LENGTH} 한도"
            )


class TwitchChatClient:
    """Twitch IRC WebSocket chat client skeleton.

    한글 주석 — 본 cycle 146 = websockets graceful False + skeleton receive_loop.
    실 IRC handshake + tags parse + PING/PONG keepalive = 별개 cycle.

    Parameters
    ----------
    config : TwitchChatConfig
        client 설정.
    on_message : Callable[[ChatMessage], Awaitable[None]] | None
        chat message 수신 callback (None = 무동작).
    """

    PLATFORM = "twitch"

    def __init__(
        self,
        config: TwitchChatConfig,
        on_message: Optional[Callable[[object], Awaitable[None]]] = None,
    ) -> None:
        self._config = config
        self._on_message = on_message
        self._ws: Optional[object] = None
        self._connected = False

    @property
    def config(self) -> TwitchChatConfig:
        return self._config

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """cycle 169.422 — Twitch IRC WebSocket actual handshake chain.

        Returns
        -------
        bool
            연결 + handshake 성공 여부. websockets 부재 시 False.
        """
        if not _WS_AVAILABLE:
            log.warning("[twitch] websockets 라이브러리 부재 — graceful False")
            return False
        try:
            self._ws = await websockets.connect(_IRC_WSS_URL)
            await self._ws.send("CAP REQ :twitch.tv/tags twitch.tv/commands")
            await self._ws.send(f"PASS oauth:{self._config.oauth_token}")
            await self._ws.send(f"NICK {self._config.bot_login}")
            await self._ws.send(f"JOIN #{self._config.channel}")
            self._connected = True
            log.info("[twitch] connect PASS — channel=#%s", self._config.channel)
            return True
        except Exception as exc:
            log.warning("[twitch] connect fail — %r", exc)
            self._ws = None
            return False

    async def disconnect(self) -> None:
        """WebSocket close + state reset."""

        if self._ws is not None:
            try:
                close = getattr(self._ws, "close", None)
                if close is not None:
                    await close()
            except Exception as exc:  # pragma: no cover
                log.warning("[twitch] disconnect 실패 — %s", exc)
        self._ws = None
        self._connected = False

    async def receive_loop(self, max_iterations: Optional[int] = None) -> List[object]:
        """cycle 169.422 — IRC PRIVMSG actual parse + PING/PONG keepalive.

        Returns
        -------
        list[object]
            수신 message dict list (parsed PRIVMSG).
        """
        if not self._connected or self._ws is None:
            return []
        messages: List[object] = []
        iters = 0
        try:
            async for raw in self._ws:
                line = raw.strip() if isinstance(raw, str) else raw.decode("utf-8", "replace").strip()
                if line.startswith("PING"):
                    await self._ws.send(line.replace("PING", "PONG", 1))
                    continue
                # 한글 주석 — IRC PRIVMSG parse: `:user!user@user.tmi.twitch.tv PRIVMSG #channel :message`
                if " PRIVMSG " in line:
                    try:
                        prefix, _, rest = line.partition(" PRIVMSG ")
                        user = prefix.lstrip(":").split("!", 1)[0]
                        chan, _, text = rest.partition(" :")
                        msg = {
                            "platform": self.PLATFORM,
                            "text": text,
                            "author": user,
                            "channel": chan.lstrip("#"),
                            "raw": line,
                        }
                        messages.append(msg)
                        if self._on_message is not None:
                            try:
                                await self._on_message(msg)
                            except Exception as exc:  # pragma: no cover
                                log.warning("[twitch] on_message exc — %r", exc)
                    except Exception as exc:  # pragma: no cover
                        log.debug("[twitch] parse fail — %r", exc)
                iters += 1
                if max_iterations is not None and iters >= max_iterations:
                    break
        except Exception as exc:  # pragma: no cover
            log.warning("[twitch] recv loop exc — %r", exc)
        return messages
