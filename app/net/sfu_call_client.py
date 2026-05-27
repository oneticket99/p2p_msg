# SPDX-License-Identifier: GPL-3.0-or-later
"""SFU 그룹 통화 클라이언트 — cycle 169.804 SFU 확장 M4a.

server-side SFU(``server/sfu_room.py``)의 클라이언트 대응부. 자신의 로컬
미디어를 1개 upstream 으로 SFU 에 publish 하고, room 안 다른 producer 들을
downstream 으로 subscribe 해 forward track 을 수신한다.

server-side 와 동일하게 publish·subscribe 모두 **client-offer / server-answer**
대칭이다 (`server/protocol.py` SFU_PUBLISH/SFU_SUBSCRIBE → SFU_ANSWER).

본 모듈은 UI 와 분리된 net 계층이다 — 와이어 송신은 주입된 ``send`` 콜러블에
위임하고, 수신 track 은 ``on_remote_track`` 콜백으로 통지한다 (UI 비의존,
headless 테스트 가능). signaling 수신 dispatch (SFU_ANSWER/SFU_PRODUCERS) 는
``handle_sfu_answer`` / ``handle_producers`` 진입점으로 받는다.

계층 위치 — app/net 클라이언트 계층(정본 §E). server `sfu_room.py` 대응부.
SfuCallMixin(UI 배선)이 본 client 를 생성·signal 결선한다.

의존성 — `aiortc`(RTCPeerConnection/MediaPlayer, 미설치 graceful None bind) +
주입된 send 콜러블(signaling 송신) + `on_remote_track` 콜백. UI/Qt 직접 의존 부재.

범위 한계 — publish/subscribe PeerConnection 수명 + track forward 수신만. 실
미디어 캡처 장치 선택·타일 렌더는 UI 책임. STUN/TURN 은 env 주입.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Awaitable, Callable, Optional

try:
    from aiortc import (
        RTCConfiguration,
        RTCIceServer,
        RTCPeerConnection,
        RTCSessionDescription,
    )
    from aiortc.contrib.media import MediaPlayer
except Exception:  # noqa: BLE001 — aiortc 미설치 환경 guard
    # 미설치 시 사용 심볼 전체를 None 으로 bind (부분 bind 시 NameError 회피)
    RTCConfiguration = None  # type: ignore
    RTCIceServer = None  # type: ignore
    RTCPeerConnection = None  # type: ignore
    RTCSessionDescription = None  # type: ignore
    MediaPlayer = None  # type: ignore

log = logging.getLogger(__name__)

# 와이어 송신 콜러블 — payload dict 1건을 async 송신
SendCallable = Callable[[dict[str, Any]], Awaitable[None]]
# 수신 track 콜백 — (producer_id, track)
RemoteTrackCallable = Callable[[str, Any], None]


class SfuCallClient:
    """room 단위 SFU 그룹 통화 클라이언트 (publish 1 + subscribe N)."""

    def __init__(
        self,
        room_id: str,
        peer_id: str,
        send: SendCallable,
        on_remote_track: Optional[RemoteTrackCallable] = None,
        on_producers: Optional[Callable[[list[str]], None]] = None,
        stun_url: str = "stun:stun.l.google.com:19302",
    ) -> None:
        # room/self 식별자 + 와이어 송신 + 수신 콜백
        self._room_id = room_id
        self._peer_id = peer_id
        self._send = send
        self._on_remote_track = on_remote_track
        self._on_producers = on_producers
        self._stun_url = os.environ.get("TOOTALK_STUN_URL", stun_url)
        # upstream publish 연결 1개 + producer_id 별 downstream 연결
        self._publish_pc: Optional[Any] = None
        self._subscribe_pcs: dict[str, Any] = {}

    def _config(self) -> Any:
        """ICE 설정 — STUN 1개 (데모 단순 구성)."""
        return RTCConfiguration([RTCIceServer(urls=[self._stun_url])])

    def _build_media_player(self, video: bool) -> Optional[Any]:
        """OS별 로컬 미디어 캡처 MediaPlayer 신설 (실패 시 None)."""
        import platform

        system = platform.system().lower()
        try:
            if system == "darwin":
                spec = "default:default" if video else "none:default"
                return MediaPlayer(spec, format="avfoundation")
            if system == "linux":
                if video:
                    return MediaPlayer("/dev/video0", format="v4l2")
                return MediaPlayer("default", format="pulse")
        except Exception as exc:  # noqa: BLE001
            log.warning("[SfuCallClient] MediaPlayer 신설 실패 video=%s — %r", video, exc)
        return None

    async def publish(
        self,
        video: bool = False,
        audio: bool = True,
        player: Optional[Any] = None,
    ) -> None:
        """로컬 미디어를 SFU 에 upstream publish (offer 송신).

        ``audio``/``video`` 플래그로 publish 할 track 종류를 명시 제어한다.
        ``player`` 주입 시 그 track 을, 없으면 OS 캡처를 사용한다 (테스트는
        aiortc 합성 track 주입). SFU_ANSWER 수신은 ``handle_sfu_answer`` 가 처리.
        """
        if RTCPeerConnection is None:
            raise RuntimeError("aiortc 미설치 — SFU 통화 불가")
        pc = RTCPeerConnection(self._config())
        self._publish_pc = pc

        media = player if player is not None else self._build_media_player(video)
        if media is not None:
            # audio/video 플래그가 켜진 track 만 선택 publish
            if audio and getattr(media, "audio", None) is not None:
                pc.addTrack(media.audio)
            if video and getattr(media, "video", None) is not None:
                pc.addTrack(media.video)

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await self._send(
            {
                "type": "SFU_PUBLISH",
                "room": self._room_id,
                "peer_id": self._peer_id,
                "sdp": pc.localDescription.sdp,
            }
        )

    async def subscribe(self, producer_id: str) -> None:
        """특정 producer 의 미디어를 downstream subscribe (recvonly offer 송신)."""
        if producer_id == self._peer_id or producer_id in self._subscribe_pcs:
            # 자기 producer 또는 이미 구독 중이면 skip
            return
        if RTCPeerConnection is None:
            raise RuntimeError("aiortc 미설치 — SFU 통화 불가")
        pc = RTCPeerConnection(self._config())
        # recvonly transceiver 로 forward track 수신 준비
        pc.addTransceiver("video", direction="recvonly")
        pc.addTransceiver("audio", direction="recvonly")

        @pc.on("track")
        def _on_track(track: Any, _pid: str = producer_id) -> None:
            # forward 된 track 을 UI 계층으로 통지
            if self._on_remote_track is not None:
                self._on_remote_track(_pid, track)

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        self._subscribe_pcs[producer_id] = pc
        try:
            await self._send(
                {
                    "type": "SFU_SUBSCRIBE",
                    "room": self._room_id,
                    "peer_id": self._peer_id,
                    "producer_id": producer_id,
                    "sdp": pc.localDescription.sdp,
                }
            )
        except Exception:
            # 송신 실패 시 등록 rollback + pc 정리 (좀비 연결 방지)
            self._subscribe_pcs.pop(producer_id, None)
            await pc.close()
            raise

    async def handle_sfu_answer(
        self, kind: str, sdp: str, producer_id: str
    ) -> None:
        """SFU_ANSWER 수신 — publish/subscribe 연결의 remote description 적용."""
        answer = RTCSessionDescription(sdp=sdp, type="answer")
        if kind == "publish":
            if self._publish_pc is not None:
                await self._publish_pc.setRemoteDescription(answer)
        elif kind == "subscribe":
            pc = self._subscribe_pcs.get(producer_id)
            if pc is not None:
                await pc.setRemoteDescription(answer)

    async def handle_producers(self, producers: list[str]) -> None:
        """SFU_PRODUCERS 수신 — 자신 제외 신규 producer 자동 subscribe + 콜백."""
        if self._on_producers is not None:
            self._on_producers(producers)
        for producer_id in producers:
            if producer_id != self._peer_id and producer_id not in self._subscribe_pcs:
                await self.subscribe(producer_id)

    def producer_ids(self) -> list[str]:
        """현재 구독 중인 producer 목록 (관측·테스트용)."""
        return list(self._subscribe_pcs.keys())

    async def close(self) -> None:
        """publish + 모든 subscribe 연결 정리."""
        if self._publish_pc is not None:
            await self._publish_pc.close()
            self._publish_pc = None
        for pc in self._subscribe_pcs.values():
            await pc.close()
        self._subscribe_pcs.clear()
