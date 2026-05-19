# SPDX-License-Identifier: GPL-3.0-or-later
"""CallClient — WebRTC SDP + ICE + MediaStreamTrack scaffolding (cycle 169.57 신설).

aiortc RTCPeerConnection + audio/video track 추가 + offer/answer chain.
signaling server 안 candidate exchange = `signaling_client.send_call_*` chain 의무.
actual MediaStream device capture = OS-specific (별도 cycle).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
    from aiortc.contrib.media import MediaPlayer, MediaBlackhole
    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False
    RTCPeerConnection = None  # type: ignore
    RTCSessionDescription = None  # type: ignore


class CallClient:
    """음성/영상 통화 — aiortc peer connection wrapper."""

    def __init__(
        self,
        stun_url: str = "stun:stun.l.google.com:19302",
        on_state_change: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._stun_url = stun_url
        self._on_state_change = on_state_change
        self._pc: Optional[Any] = None
        self._remote_track: Optional[Any] = None
        self._video_enabled = False

    def _notify(self, state: str) -> None:
        if self._on_state_change is not None:
            try:
                self._on_state_change(state)
            except Exception as exc:  # noqa: BLE001
                log.warning("[CallClient] state callback fail — %r", exc)

    async def create_offer(self, video: bool = False) -> Optional[dict]:
        """outgoing call — RTCPeerConnection + audio (+ video) track + offer 생성.

        Returns
        -------
        dict | None
            `{"sdp": str, "type": "offer"}` 또는 aiortc 부재 시 None.
        """
        if not AIORTC_AVAILABLE:
            log.warning("[CallClient] aiortc 부재 — offer scaffolding skip")
            return None
        config = RTCConfiguration([RTCIceServer(urls=[self._stun_url])])
        self._pc = RTCPeerConnection(configuration=config)
        self._video_enabled = video

        @self._pc.on("connectionstatechange")
        async def _on_state():
            self._notify(self._pc.connectionState)

        @self._pc.on("track")
        def _on_track(track):
            log.info("[CallClient] remote track 수신 kind=%s", track.kind)
            self._remote_track = track

        # 한글 주석 — actual MediaPlayer device capture = OS-specific 별도 cycle.
        # placeholder = silence track (audio) + black frame (video).
        # 본 cycle scaffolding 한정. actual device binding 별도 cycle.

        offer = await self._pc.createOffer()
        await self._pc.setLocalDescription(offer)
        return {"sdp": self._pc.localDescription.sdp, "type": "offer"}

    async def accept_offer(self, remote_sdp: str, video: bool = False) -> Optional[dict]:
        """incoming call — remote SDP set + answer 생성."""
        if not AIORTC_AVAILABLE:
            return None
        config = RTCConfiguration([RTCIceServer(urls=[self._stun_url])])
        self._pc = RTCPeerConnection(configuration=config)
        self._video_enabled = video

        await self._pc.setRemoteDescription(RTCSessionDescription(sdp=remote_sdp, type="offer"))
        answer = await self._pc.createAnswer()
        await self._pc.setLocalDescription(answer)
        return {"sdp": self._pc.localDescription.sdp, "type": "answer"}

    async def apply_answer(self, remote_sdp: str) -> None:
        """outgoing call 후 remote answer set."""
        if self._pc is None:
            return
        await self._pc.setRemoteDescription(RTCSessionDescription(sdp=remote_sdp, type="answer"))

    async def hangup(self) -> None:
        """통화 종료 — peer connection close."""
        if self._pc is not None:
            try:
                await self._pc.close()
            except Exception as exc:  # noqa: BLE001
                log.warning("[CallClient] hangup fail — %r", exc)
            self._pc = None
        self._notify("ended")

    def toggle_mute(self, muted: bool) -> None:
        """audio sender 의 track.enabled toggle."""
        if self._pc is None:
            return
        for sender in self._pc.getSenders():
            if sender.track is not None and sender.track.kind == "audio":
                sender.track.enabled = not muted

    def toggle_video(self, enabled: bool) -> None:
        """video sender 의 track.enabled toggle."""
        if self._pc is None:
            return
        self._video_enabled = enabled
        for sender in self._pc.getSenders():
            if sender.track is not None and sender.track.kind == "video":
                sender.track.enabled = enabled
