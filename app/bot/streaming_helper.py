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

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Final, List, Optional, Tuple

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


def fetch_platform_callback(platform: StreamingPlatform) -> str:
    """platform-specific callback endpoint 의 placeholder.

    실 binding (별개 cycle) — YouTube Data API + Twitch IRC + CHZZK API +
    Kick API 의 OAuth + webhook 등록 + chat stream subscribe 의무.
    """

    if platform == StreamingPlatform.YOUTUBE:
        raise NotImplementedError(
            "YouTube Data API + OAuth + chat stream 별개 cycle 의무"
        )
    if platform == StreamingPlatform.TWITCH:
        raise NotImplementedError(
            "Twitch IRC + OAuth + helix API 별개 cycle 의무"
        )
    if platform == StreamingPlatform.CHZZK:
        raise NotImplementedError(
            "CHZZK API + 네이버 OAuth + chat polling 별개 cycle 의무"
        )
    if platform == StreamingPlatform.KICK:
        raise NotImplementedError(
            "Kick API + OAuth + chat WebSocket 별개 cycle 의무"
        )
    if platform == StreamingPlatform.OBS_LOCAL:
        raise NotImplementedError(
            "OBS WebSocket (obs-websocket-py) + source 제어 별개 cycle 의무"
        )
    raise ValueError(f"unknown platform — {platform}")
