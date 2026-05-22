# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 방송 도우미 봇 별개 API skeleton — 사이클 67.

memory `project_bot_framework.md` (B) 방송 도우미 봇 의 별개 API 의 의무
정합 — TooTalk Bot API 와 분리 + streaming platform callback (YouTube /
Twitch / CHZZK / Kick) + OBS WebSocket + Toonation API 직접 통합 (옵션 B).

나이트봇 (NightBot) / StreamElements 등가 패턴.

본 module 범위
-------------
- ``StreamingPlatform`` Enum — 5 종 (YouTube / Twitch / CHZZK / Kick / OBS local)
- ``StreamingBotConfig`` frozen dataclass — bot_user_id (≥ 2_000_000 prefix
  분리) + display_name + platform + access_token Optional + cooldown_default
- ``StreamingCommand`` frozen dataclass — trigger (!hello 등) + response
  template + cooldown_seconds + enabled
- ``StreamingHelperBot`` class — apply_command(viewer_message, viewer_id, now_s)
  → Optional[str] reply
- ``default_streaming_commands`` — 5 기본 명령
- platform-specific 별개 API hook = placeholder NotImplementedError

본 cycle 의 범위 외 (별개 cycle):
- YouTube Data API + Twitch IRC + CHZZK API + Kick API 의 실 binding
- OBS WebSocket (obs-websocket-py) 의 의 source 제어
- Toonation API 의 후원 알림 직접 통합 (옵션 B 핵심)
- 사용자 의 settings panel UI (TooTalk Qt dialog)
- 자동 응답 의 cooldown shared between viewers (chatter-wide vs per-viewer)
- 단어 필터 / 타이머 메시지 / 후원 알림 매크로
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable, Dict, Final, List, Optional, Tuple

from app.bot.obs_websocket_client import ObsWebSocketClient, build_default_client

log = logging.getLogger(__name__)

# bot_user_id prefix — 방송 도우미 봇 의 별개 영역 (고객센터 봇 1_xxx_xxx 와 분리)
_STREAMING_BOT_USER_ID_PREFIX: Final[int] = 2_000_000
# default cooldown — 명령 의 viewer 의 5초 의 spam 차단
_DEFAULT_COOLDOWN_SECONDS: Final[int] = 5
# command trigger 최대 길이 (예: "!command_name")
_MAX_TRIGGER_LENGTH: Final[int] = 32
# response template 최대 길이 (chat spam 차단)
_MAX_RESPONSE_LENGTH: Final[int] = 500


class StreamingPlatform(str, Enum):
    """방송 platform 식별."""

    YOUTUBE = "youtube"
    TWITCH = "twitch"
    CHZZK = "chzzk"  # 네이버 치지직
    KICK = "kick"
    OBS_LOCAL = "obs_local"  # OBS WebSocket local 의 의 별개


@dataclass(frozen=True, slots=True)
class StreamingCommand:
    """단일 명령 의 trigger + response 의 정의.

    Attributes
    ----------
    trigger : str
        viewer 의 chat 의 prefix match (예: "!hello").
    response : str
        bot 의 응답 template ({viewer} / {streamer} 의 의 placeholder 의 caller 치환).
    cooldown_seconds : int
        명령 간 의 cooldown (per command + per platform 의 의 shared).
    enabled : bool
        활성 여부 (true = trigger 시 응답 / false = 무시).
    """

    trigger: str
    response: str
    cooldown_seconds: int = _DEFAULT_COOLDOWN_SECONDS
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.trigger:
            raise ValueError("trigger 빈 문자열 불가")
        if not self.trigger.startswith("!"):
            raise ValueError(
                f"trigger 의 '!' 시작 의무 — {self.trigger}"
            )
        if len(self.trigger) > _MAX_TRIGGER_LENGTH:
            raise ValueError(
                f"trigger 길이 초과 — {_MAX_TRIGGER_LENGTH} 한도"
            )
        if not self.response:
            raise ValueError("response 빈 문자열 불가")
        if len(self.response) > _MAX_RESPONSE_LENGTH:
            raise ValueError(
                f"response 길이 초과 — {_MAX_RESPONSE_LENGTH} 한도"
            )
        if self.cooldown_seconds < 0:
            raise ValueError(
                f"cooldown_seconds 음수 불가 — {self.cooldown_seconds}"
            )


@dataclass(frozen=True, slots=True)
class StreamingBotConfig:
    """방송 도우미 봇 인스턴스 설정.

    Attributes
    ----------
    bot_user_id : int
        bot user_id (≥ 2_000_000 prefix 의무 — 고객센터 봇 1_xxx 와 분리).
    display_name : str
        UI 표시명 (예: "TooTalk 방송 도우미").
    platform : StreamingPlatform
        대상 platform.
    access_token : str | None
        platform API 의 access token (YouTube OAuth / Twitch IRC OAuth /
        CHZZK 의 token / Kick 의 token). 별개 cycle 의 실 binding 의 사용.
    """

    bot_user_id: int
    display_name: str
    platform: StreamingPlatform
    access_token: Optional[str] = None

    def __post_init__(self) -> None:
        if self.bot_user_id < _STREAMING_BOT_USER_ID_PREFIX:
            raise ValueError(
                f"bot_user_id 의 {_STREAMING_BOT_USER_ID_PREFIX} 이상 의무 "
                f"— {self.bot_user_id} (고객센터 봇 1_xxx 와 분리)"
            )
        if not self.display_name:
            raise ValueError("display_name 빈 문자열 불가")


def default_streaming_commands() -> List[StreamingCommand]:
    """기본 5 명령 — nightbot 등가 minimal set.

    - !hello — viewer 인사 응답
    - !uptime — 방송 시작 후 경과 시간 (별개 cycle 의 streaming session 통합)
    - !donate — 후원 안내 (Toonation 위젯 URL)
    - !command — bot 명령 list
    - !so — shoutout (다른 streamer 추천)
    """

    return [
        StreamingCommand(
            trigger="!hello",
            response="{viewer} 님 안녕하세요! 방송 즐겨주세요 :)",
        ),
        StreamingCommand(
            trigger="!uptime",
            response="방송 시작 후 {uptime} 경과 (별개 cycle 의 실 시간 binding 의무)",
        ),
        StreamingCommand(
            trigger="!donate",
            response="후원 = https://toonation.com/donate/{streamer} (Toonation 공식 위젯)",
        ),
        StreamingCommand(
            trigger="!command",
            response="명령 list — !hello / !uptime / !donate / !command / !so",
        ),
        StreamingCommand(
            trigger="!so",
            response="추천 streamer = {target} (방송 응원 부탁드립니다)",
        ),
    ]


class StreamingHelperBot:
    """방송 도우미 봇.

    Parameters
    ----------
    config : StreamingBotConfig
        bot 설정.
    commands : list[StreamingCommand] | None
        명령 list. None = default_streaming_commands 의 5종.
    """

    def __init__(
        self,
        config: StreamingBotConfig,
        commands: Optional[List[StreamingCommand]] = None,
    ) -> None:
        self._config = config
        self._commands = list(commands or default_streaming_commands())
        # cooldown 추적 — trigger → 마지막 호출 시점 (epoch seconds)
        self._cooldown_until: Dict[str, float] = {}

    @property
    def config(self) -> StreamingBotConfig:
        return self._config

    @property
    def commands(self) -> Tuple[StreamingCommand, ...]:
        """명령 list 의 immutable view."""

        return tuple(self._commands)

    def find_command(self, message: str) -> Optional[StreamingCommand]:
        """message 의 first token = trigger match 의 명령 검색.

        Notes
        -----
        매치 = whitespace split 의 first token 의 정확 trigger 일치. enabled
        명령 만 의 match (disabled = None 반환).
        """

        if not message:
            return None
        token = message.split(maxsplit=1)[0]
        for cmd in self._commands:
            if cmd.trigger == token and cmd.enabled:
                return cmd
        return None

    def apply_command(
        self,
        viewer_message: str,
        *,
        viewer_name: str = "viewer",
        streamer_name: str = "streamer",
        target_name: str = "",
        uptime_text: str = "?",
        now_seconds: Optional[float] = None,
    ) -> Optional[str]:
        """viewer chat → bot reply (또는 None).

        Parameters
        ----------
        viewer_message : str
            viewer 의 chat 본문.
        viewer_name : str
            응답 의 {viewer} placeholder.
        streamer_name : str
            응답 의 {streamer} placeholder.
        target_name : str
            !so 의 {target} placeholder.
        uptime_text : str
            !uptime 의 {uptime} placeholder (별개 cycle 의 session uptime 의 caller 산출).
        now_seconds : float | None
            현재 시점 (test injection). None = time.time().

        Returns
        -------
        str | None
            응답 str. command match 부재 또는 cooldown 시 None.
        """

        cmd = self.find_command(viewer_message)
        if cmd is None:
            return None
        now = now_seconds if now_seconds is not None else time.time()
        cooldown_until = self._cooldown_until.get(cmd.trigger, 0.0)
        if now < cooldown_until:
            return None
        # template 치환
        reply = (
            cmd.response.replace("{viewer}", viewer_name)
            .replace("{streamer}", streamer_name)
            .replace("{target}", target_name)
            .replace("{uptime}", uptime_text)
        )
        self._cooldown_until[cmd.trigger] = now + cmd.cooldown_seconds
        return reply

    def add_command(self, command: StreamingCommand) -> None:
        """신규 명령 추가. 동일 trigger 존재 시 ValueError."""

        for existing in self._commands:
            if existing.trigger == command.trigger:
                raise ValueError(
                    f"trigger 중복 — {command.trigger} 이미 등록"
                )
        self._commands.append(command)

    def remove_command(self, trigger: str) -> bool:
        """trigger 의 명령 제거. 부재 = False 반환."""

        before = len(self._commands)
        self._commands = [c for c in self._commands if c.trigger != trigger]
        return len(self._commands) < before


# 한글 주석 — chat event payload 의 type alias (platform → handler dispatch)
ChatEventPayload = Dict[str, object]
# 한글 주석 — platform chat handler callback signature
ChatEventHandler = Callable[[ChatEventPayload], Awaitable[bool]]


class StreamingHelperDispatcher:
    """4 streaming platform (YouTube / Twitch / CHZZK / Kick) chat → OBS alert dispatch.

    한글 주석 — cycle 141 skeleton — platform callback chain + trigger_alert
    bridge. 실 platform API binding = 별개 cycle.

    Parameters
    ----------
    obs_client : ObsWebSocketClient | None
        OBS WebSocket client. None = build_default_client factory.
    """

    def __init__(self, obs_client: Optional[ObsWebSocketClient] = None) -> None:
        self._obs = obs_client or build_default_client()
        # platform → handler 의 registry
        self._handlers: Dict[StreamingPlatform, ChatEventHandler] = {}

    @property
    def obs(self) -> ObsWebSocketClient:
        return self._obs

    def register_handler(
        self,
        platform: StreamingPlatform,
        handler: ChatEventHandler,
    ) -> None:
        """platform 의 chat handler 등록.

        Parameters
        ----------
        platform : StreamingPlatform
            대상 platform.
        handler : ChatEventHandler
            chat event payload → bool awaitable. True = OBS dispatch 성공.
        """

        self._handlers[platform] = handler

    async def youtube_chat_handler(self, payload: ChatEventPayload) -> bool:
        """YouTube chat / Super Chat → OBS alert dispatch."""

        return await self._obs.trigger_alert("youtube_chat", payload)

    async def twitch_chat_handler(self, payload: ChatEventPayload) -> bool:
        """Twitch chat / bits / sub → OBS alert dispatch."""

        return await self._obs.trigger_alert("twitch_chat", payload)

    async def chzzk_chat_handler(self, payload: ChatEventPayload) -> bool:
        """CHZZK (네이버 치지직) chat / 후원 → OBS alert dispatch."""

        return await self._obs.trigger_alert("chzzk_chat", payload)

    async def kick_chat_handler(self, payload: ChatEventPayload) -> bool:
        """Kick chat / sub → OBS alert dispatch."""

        return await self._obs.trigger_alert("kick_chat", payload)

    async def dispatch(
        self,
        platform: StreamingPlatform,
        payload: ChatEventPayload,
    ) -> bool:
        """platform 별 default handler dispatch.

        Parameters
        ----------
        platform : StreamingPlatform
            대상 platform.
        payload : ChatEventPayload
            chat event 본문.

        Returns
        -------
        bool
            OBS alert dispatch 성공 여부.
        """

        # 한글 주석 — registered handler 우선 + default handler fallback
        registered = self._handlers.get(platform)
        if registered is not None:
            return await registered(payload)
        if platform == StreamingPlatform.YOUTUBE:
            return await self.youtube_chat_handler(payload)
        if platform == StreamingPlatform.TWITCH:
            return await self.twitch_chat_handler(payload)
        if platform == StreamingPlatform.CHZZK:
            return await self.chzzk_chat_handler(payload)
        if platform == StreamingPlatform.KICK:
            return await self.kick_chat_handler(payload)
        # OBS_LOCAL — 직접 alert
        if platform == StreamingPlatform.OBS_LOCAL:
            return await self._obs.trigger_alert("obs_local", payload)
        raise ValueError(f"unknown platform — {platform}")


def fetch_platform_callback(platform: StreamingPlatform) -> str:
    """cycle 169.418 — platform-specific callback endpoint URL 반환 (NotImplementedError 폐기).

    각 platform 의 chat stream / event subscribe 의 base endpoint URL return.
    env var override 패턴 — 사용자 별 baseUrl 직접 설정 가능 (Toonation 통합 옵션 B).

    Notes
    -----
    OAuth flow + token refresh + actual subscribe chain = 별개 cycle 의무 retain.
    본 함수 = 단순 base endpoint URL return — caller responsibility = OAuth + subscribe.

    Returns
    -------
    str
        platform 의 base endpoint URL (env override 우선).
    """
    import os
    if platform == StreamingPlatform.YOUTUBE:
        # YouTube Data API v3 — liveChatMessages.list endpoint base
        return os.environ.get(
            "YOUTUBE_LIVECHAT_URL",
            "https://www.googleapis.com/youtube/v3/liveChat/messages",
        )
    if platform == StreamingPlatform.TWITCH:
        # Twitch IRC WebSocket endpoint (TMI)
        return os.environ.get("TWITCH_IRC_WS_URL", "wss://irc-ws.chat.twitch.tv")
    if platform == StreamingPlatform.CHZZK:
        # CHZZK (네이버 치지직) live-status polling endpoint base
        return os.environ.get(
            "CHZZK_API_URL", "https://api.chzzk.naver.com/polling/v2/channels"
        )
    if platform == StreamingPlatform.KICK:
        # Kick Pusher WebSocket endpoint (chatroom events)
        return os.environ.get(
            "KICK_PUSHER_URL",
            "wss://ws-us2.pusher.com/app/eb1d5f283081a78b932c?protocol=7",
        )
    if platform == StreamingPlatform.OBS_LOCAL:
        # OBS WebSocket v5 default endpoint (localhost)
        return os.environ.get("OBS_WS_URL", "ws://localhost:4455")
    raise ValueError(f"unknown platform — {platform}")
