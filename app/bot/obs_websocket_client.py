# SPDX-License-Identifier: GPL-3.0-or-later
"""OBS WebSocket client — OBS Studio v28+ obs-websocket v5 protocol (cycle 148 actual).

memory `project_bot_framework.md` (B) 방송 도우미 봇 의 별개 API 의무 정합 —
nightbot/StreamElements 등가 의 OBS Studio 의 WebSocket Server (port 4455
default) 연결 + 4 streaming platform (YouTube / Twitch / CHZZK / Kick) 의
chat overlay alert dispatch + scene switch + source visibility 제어.

cycle 148 갱신 범위
------------------
- ``connect()`` — ``websockets.connect`` ws://host:port + Hello (op=0) +
  Identify (op=1) + Identified (op=2) handshake. SHA256 password hash +
  RPC version 1 negotiation.
- ``get_scene_list()`` — op=6 ``GetSceneList`` request + UUID requestId +
  op=7 RequestResponse parse + ``ObsSceneInfo`` list 반환.
- ``set_current_scene(scene_name)`` — op=6 ``SetCurrentProgramScene``
  request + boolean 반환.
- ``trigger_alert(alert_id, payload)`` — op=6 ``CallVendorRequest``
  vendorName=``obs-browser`` vendorRequest=``emit_event`` browser source
  custom event dispatch.

본 module 범위
-------------
- ``ObsConnectionConfig`` dataclass — host + port + password + timeout
- ``ObsSceneInfo`` frozen dataclass — name + index + is_program
- ``ObsWebSocketClient`` class — connect/disconnect + get_scene_list +
  set_current_scene + trigger_alert (actual v5 protocol)
- ``build_default_client`` — env OBS_HOST/OBS_PORT/OBS_PASSWORD factory
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)

# 한글 주석 — websockets 라이브러리 optional import (graceful False 의무)
try:
    import websockets  # type: ignore[import-not-found]

    _WS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _WS_AVAILABLE = False


# OBS WebSocket v5 의 default port (OBS Studio v28+ 의 표준)
_DEFAULT_OBS_PORT = 4455
# connect timeout default — handshake 응답 5초 한도
_DEFAULT_TIMEOUT_SECONDS = 5.0
# host 최대 길이 — 일반 hostname/IP 안전 한도
_MAX_HOST_LENGTH = 253

# 한글 주석 — obs-websocket v5 opcode (공식 spec)
_OP_HELLO = 0
_OP_IDENTIFY = 1
_OP_IDENTIFIED = 2
_OP_REQUEST = 6
_OP_REQUEST_RESPONSE = 7

# 한글 주석 — RPC version (v5 의 표준 = 1)
_RPC_VERSION = 1


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


def _compute_auth_string(password: str, salt: str, challenge: str) -> str:
    """OBS WebSocket v5 의 authentication string 계산.

    한글 주석 — 공식 spec —
    1) base64(sha256(password + salt))
    2) base64(sha256(step1 + challenge))

    Parameters
    ----------
    password : str
        OBS Server 비밀번호.
    salt : str
        Hello 메시지 안 의 authentication.salt 필드.
    challenge : str
        Hello 메시지 안 의 authentication.challenge 필드.

    Returns
    -------
    str
        Identify 의 ``authentication`` 필드 의 의 base64 string.
    """

    # 한글 주석 — 1단계 — password+salt 의 SHA256 → base64
    secret = base64.b64encode(
        hashlib.sha256((password + salt).encode("utf-8")).digest()
    ).decode("ascii")
    # 한글 주석 — 2단계 — step1+challenge 의 SHA256 → base64
    auth = base64.b64encode(
        hashlib.sha256((secret + challenge).encode("utf-8")).digest()
    ).decode("ascii")
    return auth


class ObsWebSocketClient:
    """OBS WebSocket v5 client + scene switch + source visibility + chat overlay alert.

    한글 주석 — cycle 148 = actual handshake + 4 request 의 binding.
    실 OBS 호출 시 ``websockets`` 라이브러리 필요. 부재 시 graceful False.

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
        """OBS WebSocket 의 connect + Hello + Identify + Identified handshake.

        한글 주석 — v5 handshake chain —
        1) ``websockets.connect(ws://host:port)``
        2) Hello (op=0) receive — obsWebSocketVersion + rpcVersion + auth challenge
        3) Identify (op=1) send — rpcVersion=1 + authentication string (필요 시)
        4) Identified (op=2) receive — negotiatedRpcVersion 검증

        Returns
        -------
        bool
            연결 성공 여부. websockets 부재 또는 handshake 실패 = False.
        """

        if not _WS_AVAILABLE:
            log.warning("[obs] websockets 라이브러리 부재 — graceful False")
            return False

        url = f"ws://{self._config.host}:{self._config.port}"
        try:
            # 한글 주석 — websockets.connect 의 timeout wrapper
            self._ws = await asyncio.wait_for(
                websockets.connect(url),
                timeout=self._config.timeout_seconds,
            )
        except Exception as exc:
            log.warning("[obs] connect 실패 — %s", exc)
            self._ws = None
            return False

        try:
            # 한글 주석 — Hello (op=0) 수신
            hello_raw = await asyncio.wait_for(
                self._ws.recv(),
                timeout=self._config.timeout_seconds,
            )
            hello_msg = json.loads(hello_raw)
            if hello_msg.get("op") != _OP_HELLO:
                log.warning(
                    "[obs] Hello op 불일치 — %s", hello_msg.get("op")
                )
                await self._safe_close()
                return False

            hello_data = hello_msg.get("d", {})
            auth_challenge = hello_data.get("authentication")

            # 한글 주석 — Identify (op=1) 송신
            identify_data: dict = {"rpcVersion": _RPC_VERSION}
            if auth_challenge:
                # 한글 주석 — auth 요구 시 password 의무
                if not self._config.password:
                    log.warning(
                        "[obs] auth 요구 but password 부재 — connect 실패"
                    )
                    await self._safe_close()
                    return False
                salt = auth_challenge.get("salt", "")
                challenge = auth_challenge.get("challenge", "")
                identify_data["authentication"] = _compute_auth_string(
                    self._config.password, salt, challenge
                )

            identify_msg = {"op": _OP_IDENTIFY, "d": identify_data}
            await self._ws.send(json.dumps(identify_msg))

            # 한글 주석 — Identified (op=2) 수신 + rpcVersion 검증
            identified_raw = await asyncio.wait_for(
                self._ws.recv(),
                timeout=self._config.timeout_seconds,
            )
            identified_msg = json.loads(identified_raw)
            if identified_msg.get("op") != _OP_IDENTIFIED:
                log.warning(
                    "[obs] Identified op 불일치 — %s (auth 실패 가능)",
                    identified_msg.get("op"),
                )
                await self._safe_close()
                return False

            negotiated = identified_msg.get("d", {}).get(
                "negotiatedRpcVersion"
            )
            if negotiated != _RPC_VERSION:
                log.warning(
                    "[obs] rpcVersion 불일치 — negotiated=%s expected=%s",
                    negotiated,
                    _RPC_VERSION,
                )
                await self._safe_close()
                return False

            self._connected = True
            return True
        except Exception as exc:
            log.warning("[obs] handshake 실패 — %s", exc)
            await self._safe_close()
            return False

    async def _safe_close(self) -> None:
        """내부 cleanup — ws close + state reset (handshake 실패 경로)."""

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # pragma: no cover
                pass
        self._ws = None
        self._connected = False

    async def disconnect(self) -> None:
        """OBS WebSocket 의 disconnect — websocket close + state reset."""

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception as exc:  # pragma: no cover
                log.warning("[obs] disconnect 실패 — %s", exc)
        self._ws = None
        self._connected = False

    async def _send_request(
        self,
        request_type: str,
        request_data: Optional[dict] = None,
    ) -> Optional[dict]:
        """op=6 Request 송신 + op=7 RequestResponse 수신 의 단일 round-trip.

        한글 주석 — UUID requestId correlate + requestStatus.result 검증.

        Parameters
        ----------
        request_type : str
            obs-websocket v5 의 requestType (예: ``GetSceneList``).
        request_data : dict | None
            requestData 본문 (없으면 빈 dict).

        Returns
        -------
        dict | None
            ``responseData`` dict. 실패 시 None.
        """

        if not self._connected or self._ws is None:
            return None

        request_id = str(uuid.uuid4())
        msg = {
            "op": _OP_REQUEST,
            "d": {
                "requestType": request_type,
                "requestId": request_id,
                "requestData": request_data or {},
            },
        }
        try:
            await self._ws.send(json.dumps(msg))
            raw = await asyncio.wait_for(
                self._ws.recv(),
                timeout=self._config.timeout_seconds,
            )
            resp = json.loads(raw)
            if resp.get("op") != _OP_REQUEST_RESPONSE:
                log.warning(
                    "[obs] RequestResponse op 불일치 — %s", resp.get("op")
                )
                return None
            data = resp.get("d", {})
            if data.get("requestId") != request_id:
                log.warning(
                    "[obs] requestId 불일치 — got=%s expected=%s",
                    data.get("requestId"),
                    request_id,
                )
                return None
            status = data.get("requestStatus", {})
            if not status.get("result"):
                log.warning(
                    "[obs] request 실패 — %s code=%s",
                    request_type,
                    status.get("code"),
                )
                return None
            return data.get("responseData") or {}
        except Exception as exc:
            log.warning("[obs] request 송수신 실패 — %s", exc)
            return None

    async def get_scene_list(self) -> list[ObsSceneInfo]:
        """OBS scene list 조회 — ``GetSceneList`` request.

        Returns
        -------
        list[ObsSceneInfo]
            scene 메타데이터 list. 미연결 또는 실패 = 빈 list.
        """

        if not self._connected:
            return []
        data = await self._send_request("GetSceneList")
        if data is None:
            return []
        # 한글 주석 — currentProgramSceneName + scenes (sceneIndex + sceneName)
        current_program = data.get("currentProgramSceneName", "")
        raw_scenes = data.get("scenes", []) or []
        result: list[ObsSceneInfo] = []
        for entry in raw_scenes:
            name = entry.get("sceneName", "")
            index = int(entry.get("sceneIndex", 0))
            result.append(
                ObsSceneInfo(
                    name=name,
                    index=index,
                    is_program=(name == current_program),
                )
            )
        return result

    async def set_current_scene(self, scene_name: str) -> bool:
        """현재 program scene 전환 — ``SetCurrentProgramScene`` request.

        Parameters
        ----------
        scene_name : str
            전환 대상 scene 이름.

        Returns
        -------
        bool
            전환 성공 여부. 미연결 또는 실패 = False.
        """

        if not scene_name:
            raise ValueError("scene_name 빈 문자열 불가")
        if not self._connected:
            return False
        data = await self._send_request(
            "SetCurrentProgramScene",
            {"sceneName": scene_name},
        )
        # 한글 주석 — _send_request 의 None = 실패. dict (빈 dict 포함) = 성공
        return data is not None

    async def trigger_alert(self, alert_id: str, payload: dict) -> bool:
        """OBS browser source 의 custom alert dispatch.

        한글 주석 — ``CallVendorRequest`` (vendorName=``obs-browser``
        vendorRequest=``emit_event``) browser source 안 의 의 custom event
        dispatch. nightbot / StreamElements 등가 의 chat overlay alert.

        Parameters
        ----------
        alert_id : str
            alert identifier (예: ``donation`` / ``chat_highlight`` / ``sub``).
        payload : dict
            alert 본문 (viewer / amount / message 등).

        Returns
        -------
        bool
            dispatch 성공 여부. 미연결 또는 실패 = False.
        """

        if not alert_id:
            raise ValueError("alert_id 빈 문자열 불가")
        if payload is None:
            raise ValueError("payload None 불가")
        if not self._connected:
            return False
        data = await self._send_request(
            "CallVendorRequest",
            {
                "vendorName": "obs-browser",
                "requestType": "emit_event",
                "requestData": {
                    "event_name": alert_id,
                    "event_data": payload,
                },
            },
        )
        return data is not None


def build_default_client() -> ObsWebSocketClient:
    """env OBS_HOST + OBS_PORT + OBS_PASSWORD default factory.

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
