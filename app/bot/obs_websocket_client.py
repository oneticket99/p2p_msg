# SPDX-License-Identifier: GPL-3.0-or-later
"""OBS WebSocket client — OBS Studio v28+ obs-websocket v5 protocol (cycle 141 skeleton).

memory `project_bot_framework.md` (B) 방송 도우미 봇 의 별개 API 의무 정합 —
nightbot/StreamElements 등가 의 OBS Studio 의 WebSocket Server (port 4455
default) 연결 + 4 streaming platform (YouTube / Twitch / CHZZK / Kick) 의
chat overlay alert dispatch + scene switch + source visibility 제어.

본 module 범위
-------------
- ``ObsConnectionConfig`` dataclass — host + port + password + timeout
- ``ObsSceneInfo`` frozen dataclass — name + index + is_program
- ``ObsWebSocketClient`` class — connect/disconnect + get_scene_list +
  set_current_scene + trigger_alert (graceful False / [] skeleton)
- ``build_default_client`` — env OBS_HOST/OBS_PORT/OBS_PASSWORD 의 factory

본 cycle 의 범위 외 (별개 cycle):
- obs-websocket v5 의 HELLO + IDENTIFY + AUTHENTICATE 의 실 handshake
- request/response correlation id 기반 async future 패턴
- event subscription (CurrentProgramSceneChanged 등) 의 listener
- browser source 의 의 custom alert dispatch protocol
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

log = logging.getLogger(__name__)

# 한글 주석 — websockets 라이브러리 optional import (graceful False 의무)
try:
    import websockets  # type: ignore[import-not-found]

    _WS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _WS_AVAILABLE = False


# OBS WebSocket v5 의 default port (OBS Studio v28+ 의 표준)
_DEFAULT_OBS_PORT = 4455
# connect timeout default — handshake 응답 의 의 5초 한도
_DEFAULT_TIMEOUT_SECONDS = 5.0
# host 최대 길이 — 일반 hostname/IP 의 안전 한도
_MAX_HOST_LENGTH = 253


@dataclass(slots=True)
class ObsConnectionConfig:
    """OBS WebSocket 의 연결 설정.

    Attributes
    ----------
    host : str
        OBS Studio host (localhost default — 동일 PC 상 OBS 가정).
    port : int
        WebSocket Server port (4455 default — OBS v28+ 표준).
    password : str
        OBS WebSocket Server 의 비밀번호 (빈 문자열 = 무인증).
    timeout_seconds : float
        connect handshake timeout (5초 default).
    """

    host: str = "localhost"
    port: int = _DEFAULT_OBS_PORT
    password: str = ""
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        # 한글 주석 — host 빈 문자열 + 길이 검증
        if not self.host:
            raise ValueError("host 빈 문자열 불가")
        if len(self.host) > _MAX_HOST_LENGTH:
            raise ValueError(
                f"host 길이 초과 — {_MAX_HOST_LENGTH} 한도"
            )
        # port 범위 검증 — 1~65535
        if not (1 <= self.port <= 65535):
            raise ValueError(f"port 범위 외 — {self.port} (1~65535)")
        if self.timeout_seconds <= 0:
            raise ValueError(
                f"timeout_seconds 양수 의무 — {self.timeout_seconds}"
            )


@dataclass(frozen=True, slots=True)
class ObsSceneInfo:
    """OBS scene 의 메타데이터.

    Attributes
    ----------
    name : str
        scene 이름 (OBS 사용자 정의).
    index : int
        scene list 안 의 index (0-base).
    is_program : bool
        현재 program (송출 중) scene 여부.
    """

    name: str
    index: int
    is_program: bool


class ObsWebSocketClient:
    """OBS WebSocket v5 client + scene switch + source visibility + chat overlay alert.

    한글 주석 — Phase 5 cycle 의 실 handshake / event / request 의무.
    본 cycle 141 = skeleton graceful False / [] 만 의 정의.

    Parameters
    ----------
    config : ObsConnectionConfig | None
        연결 설정. None = default (localhost:4455 + 무인증).
    """

    # obs-websocket protocol version (v5)
    PROTOCOL_VERSION = 1

    def __init__(self, config: Optional[ObsConnectionConfig] = None) -> None:
        self._config = config or ObsConnectionConfig()
        self._ws = None
        self._connected = False

    @property
    def config(self) -> ObsConnectionConfig:
        return self._config

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """OBS WebSocket 의 connect + HELLO + IDENTIFY handshake.

        한글 주석 — Phase 5 cycle 의 actual handshake. 본 cycle = graceful False.

        Returns
        -------
        bool
            연결 성공 여부. websockets 부재 또는 skeleton = False.
        """

        if not _WS_AVAILABLE:
            log.warning("[obs] websockets 라이브러리 부재 — graceful False")
            return False
        # 한글 주석 — Phase 5 cycle 의 actual websockets.connect + handshake
        # url = f"ws://{self._config.host}:{self._config.port}"
        # await websockets.connect(url, ...) + HELLO + IDENTIFY chain 의무
        return False

    async def disconnect(self) -> None:
        """OBS WebSocket 의 disconnect — websocket close + state reset."""

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception as exc:  # pragma: no cover
                log.warning("[obs] disconnect 실패 — %s", exc)
        self._ws = None
        self._connected = False

    async def get_scene_list(self) -> list[ObsSceneInfo]:
        """OBS scene list 조회 — GetSceneList request.

        Returns
        -------
        list[ObsSceneInfo]
            scene 메타데이터 list. 미연결 = 빈 list.
        """

        if not self._connected:
            return []
        # 한글 주석 — Phase 5 cycle 의 GetSceneList request + response parsing
        return []

    async def set_current_scene(self, scene_name: str) -> bool:
        """현재 program scene 전환 — SetCurrentProgramScene request.

        Parameters
        ----------
        scene_name : str
            전환 대상 scene 이름.

        Returns
        -------
        bool
            전환 성공 여부. 미연결 또는 skeleton = False.
        """

        if not scene_name:
            raise ValueError("scene_name 빈 문자열 불가")
        if not self._connected:
            return False
        # 한글 주석 — Phase 5 cycle 의 SetCurrentProgramScene request
        return False

    async def trigger_alert(self, alert_id: str, payload: dict) -> bool:
        """OBS browser source 의 custom alert dispatch.

        한글 주석 — chat overlay alert / 후원 알림 / sub 알림 의 의 dispatch.
        browser source 의 의 custom event listener 의 의 매크로 trigger.

        Parameters
        ----------
        alert_id : str
            alert identifier (예: "donation" / "chat_highlight" / "sub").
        payload : dict
            alert 본문 (viewer / amount / message 등).

        Returns
        -------
        bool
            dispatch 성공 여부. 미연결 또는 skeleton = False.
        """

        if not alert_id:
            raise ValueError("alert_id 빈 문자열 불가")
        if payload is None:
            raise ValueError("payload None 불가")
        if not self._connected:
            return False
        # 한글 주석 — Phase 5 cycle 의 CallVendorRequest 또는 browser source 의 의 event
        return False


def build_default_client() -> ObsWebSocketClient:
    """env OBS_HOST + OBS_PORT + OBS_PASSWORD 의 default factory.

    환경변수 부재 시 default — localhost:4455 + 무인증.

    Returns
    -------
    ObsWebSocketClient
        env 기반 설정 의 client 인스턴스.
    """

    host = os.environ.get("OBS_HOST", "localhost").strip() or "localhost"
    port_raw = os.environ.get("OBS_PORT", "").strip()
    try:
        port = int(port_raw) if port_raw else _DEFAULT_OBS_PORT
    except ValueError:
        log.warning("[obs] OBS_PORT 파싱 실패 — default %d", _DEFAULT_OBS_PORT)
        port = _DEFAULT_OBS_PORT
    password = os.environ.get("OBS_PASSWORD", "").strip()
    cfg = ObsConnectionConfig(host=host, port=port, password=password)
    return ObsWebSocketClient(config=cfg)
