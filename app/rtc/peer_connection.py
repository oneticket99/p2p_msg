# SPDX-License-Identifier: GPL-3.0-or-later
"""aiortc RTCPeerConnection + DataChannel actual binding skeleton (cycle 167 신설).

mesh_manager (cycle 138 skeleton + cycle 158 broadcast_payload) 의 placeholder
peer 본격 actual chain.

설계:
- WebRTC offer/answer SDP signaling = signaling WS 경유
- DataChannel = reliable ordered (TCP-like) message channel
- ICE = STUN/TURN 기반 NAT traversal
- onmessage callback → mesh_manager.dispatch_incoming chain

aiortc 부재 환경 (test collection / headless) graceful import 폴백.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger(__name__)

# 한글 주석 — aiortc graceful import (headless / test 환경)
try:
    from aiortc import RTCConfiguration, RTCDataChannel, RTCIceServer, RTCPeerConnection
    from aiortc.contrib.signaling import object_from_string, object_to_string
    _AIORTC_AVAILABLE = True
except ImportError:  # pragma: no cover — aiortc 미설치
    RTCConfiguration = None  # type: ignore[assignment]
    RTCDataChannel = None  # type: ignore[assignment]
    RTCIceServer = None  # type: ignore[assignment]
    RTCPeerConnection = None  # type: ignore[assignment]
    object_from_string = None  # type: ignore[assignment]
    object_to_string = None  # type: ignore[assignment]
    _AIORTC_AVAILABLE = False


@dataclass(slots=True)
class PeerConnectionConfig:
    """ICE server + DataChannel 옵션."""
    stun_urls: tuple[str, ...] = ("stun:stun.l.google.com:19302",)
    turn_url: Optional[str] = None
    turn_username: Optional[str] = None
    turn_credential: Optional[str] = None
    data_channel_label: str = "tootalk"
    ordered: bool = True


class PeerConnectionWrapper:
    """RTCPeerConnection + DataChannel 통합 wrapper — cycle 167 actual binding.

    Lifecycle:
        1. __init__ — RTCPeerConnection 생성 + DataChannel 등록
        2. create_offer / set_remote / create_answer — SDP exchange
        3. on_message handler → DataChannel.add_listener
        4. send(text) — DataChannel.send (str/bytes)
        5. close — RTCPeerConnection.close + cleanup
    """

    def __init__(
        self,
        peer_id: str,
        config: Optional[PeerConnectionConfig] = None,
        on_message: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        if not _AIORTC_AVAILABLE:
            raise RuntimeError("aiortc 미설치 — PeerConnectionWrapper 생성 불가")
        self.peer_id = peer_id
        self.config = config or PeerConnectionConfig()
        self._on_message = on_message
        self._pc: Optional["RTCPeerConnection"] = None
        self._channel: Optional["RTCDataChannel"] = None
        self.connected = False
        self._init_pc()

    def _init_pc(self) -> None:
        """RTCPeerConnection 인스턴스 + ICE config + connectionstatechange 등록."""
        ice_servers = [RTCIceServer(urls=list(self.config.stun_urls))]
        if self.config.turn_url:
            ice_servers.append(
                RTCIceServer(
                    urls=[self.config.turn_url],
                    username=self.config.turn_username,
                    credential=self.config.turn_credential,
                )
            )
        rtc_config = RTCConfiguration(iceServers=ice_servers)
        self._pc = RTCPeerConnection(configuration=rtc_config)

        @self._pc.on("connectionstatechange")
        def _on_state_change() -> None:
            state = self._pc.connectionState if self._pc else "closed"  # type: ignore[attr-defined]
            log.info("[rtc] peer=%s state=%s", self.peer_id, state)
            self.connected = state == "connected"

        @self._pc.on("datachannel")
        def _on_remote_channel(channel: "RTCDataChannel") -> None:
            log.info("[rtc] peer=%s remote channel — label=%s", self.peer_id, channel.label)
            self._channel = channel
            self._bind_channel_listeners()

    def _bind_channel_listeners(self) -> None:
        """DataChannel.on('message') → on_message callback dispatch."""
        if self._channel is None:
            return

        @self._channel.on("message")
        def _on_msg(raw: str) -> None:
            if self._on_message is not None:
                try:
                    self._on_message(self.peer_id, raw)
                except Exception as exc:  # noqa: BLE001
                    log.warning("[rtc] on_message handler 실패 — %r", exc)

    async def create_offer(self) -> str:
        """offer SDP 생성 + DataChannel 등록 + serialize 반환."""
        if self._pc is None:
            raise RuntimeError("PC 부재 — __init__ 호출 의무")
        self._channel = self._pc.createDataChannel(
            self.config.data_channel_label, ordered=self.config.ordered
        )
        self._bind_channel_listeners()
        offer = await self._pc.createOffer()
        await self._pc.setLocalDescription(offer)
        return object_to_string(self._pc.localDescription)  # type: ignore[arg-type]

    async def set_remote_answer(self, sdp_str: str) -> None:
        """remote answer SDP 적용."""
        if self._pc is None:
            raise RuntimeError("PC 부재")
        remote = object_from_string(sdp_str)  # type: ignore[arg-type]
        await self._pc.setRemoteDescription(remote)

    async def accept_offer(self, sdp_str: str) -> str:
        """remote offer 수신 + answer 생성 + serialize 반환."""
        if self._pc is None:
            raise RuntimeError("PC 부재")
        remote = object_from_string(sdp_str)  # type: ignore[arg-type]
        await self._pc.setRemoteDescription(remote)
        answer = await self._pc.createAnswer()
        await self._pc.setLocalDescription(answer)
        return object_to_string(self._pc.localDescription)  # type: ignore[arg-type]

    def send(self, message: str) -> bool:
        """DataChannel raw send — connected + channel open 시점 만."""
        if self._channel is None or not self.connected:
            return False
        try:
            self._channel.send(message)
            return True
        except Exception as exc:  # noqa: BLE001
            log.warning("[rtc] send 실패 peer=%s — %r", self.peer_id, exc)
            return False

    async def close(self) -> None:
        """RTCPeerConnection close + DataChannel cleanup."""
        if self._channel is not None:
            try:
                self._channel.close()
            except Exception:  # noqa: BLE001
                pass
            self._channel = None
        if self._pc is not None:
            try:
                await self._pc.close()
            except Exception:  # noqa: BLE001
                pass
            self._pc = None
        self.connected = False


def is_aiortc_available() -> bool:
    """aiortc import 가능 여부."""
    return _AIORTC_AVAILABLE
