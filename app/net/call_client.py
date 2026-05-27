# SPDX-License-Identifier: GPL-3.0-or-later
"""CallClient — WebRTC SDP + ICE + MediaStreamTrack scaffolding (cycle 169.57 신설).

역할 — 1:1 음성/영상 통화의 aiortc RTCPeerConnection 수명(offer/answer/ICE/hangup)
+ OS 미디어 캡처 + mute/video toggle 을 담당한다(SFU 그룹 통화는 sfu_call_client 별개).

계층 위치 — app/net 클라이언트 계층(정본 §E). CallMixin(UI)이 본 client 를 생성하고,
SDP/ICE 교환은 주입된 `signaling_client.send_offer/answer/ice` 에 위임한다.

의존성 — `aiortc`(RTCPeerConnection/MediaPlayer, 미설치 시 AIORTC_AVAILABLE=False
graceful) + 주입된 signaling_client + STUN/TURN env(TOOTALK_STUN_URL/TURN_*). UI/Qt
직접 의존 부재.

범위 한계 — peer connection + track 수명만. 실 미디어 device 선택은 OS-specific
(_build_media_player), 타일 렌더는 UI 책임. aiortc 부재 환경은 None 반환 graceful.

카탈로그(공개 async 5 + toggle 2 + helper 3):
- `create_offer`/`accept_offer`/`apply_answer`/`hangup` + `toggle_mute`/`toggle_video`.
- `_build_media_player`/`_build_ice_servers`/`_notify`(상태 콜백).
"""

from __future__ import annotations

import asyncio
import logging
import os
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
        signaling_client: Optional[Any] = None,
        peer_id: Optional[str] = None,
        turn_url: str = "",
        turn_username: str = "",
        turn_credential: str = "",
    ) -> None:
        # TURN credential 을 env override 로 주입(production binding, cycle 169.81 회수)
        # TOOTALK_TURN_URL / TOOTALK_TURN_USERNAME / TOOTALK_TURN_CREDENTIAL
        self._stun_url = os.environ.get("TOOTALK_STUN_URL", stun_url)
        self._turn_url = os.environ.get("TOOTALK_TURN_URL", turn_url)
        self._turn_username = os.environ.get("TOOTALK_TURN_USERNAME", turn_username)
        self._turn_credential = os.environ.get("TOOTALK_TURN_CREDENTIAL", turn_credential)
        self._on_state_change = on_state_change
        self._signaling = signaling_client
        self._peer_id = peer_id  # 상대 peer 의 signaling id
        self._pc: Optional[Any] = None
        self._remote_track: Optional[Any] = None
        self._video_enabled = False

    def _build_media_player(self, system: str, video: bool = False):  # type: ignore[no-untyped-def]
        """OS-specific MediaPlayer 신설 (cycle 169.60 video capture 회수).

        Darwin avfoundation video device 는 `default:default`(camera + mic).
        Linux v4l2 + pulse. Windows dshow audio-only (미지원 시 graceful).
        """
        if not AIORTC_AVAILABLE:
            return None
        try:
            if system == "Darwin":
                if video:
                    return MediaPlayer("default:default", format="avfoundation",
                                       options={"framerate": "30", "video_size": "640x480"})
                return MediaPlayer("none:default", format="avfoundation")
            if system == "Linux":
                if video:
                    return MediaPlayer("/dev/video0", format="v4l2",
                                       options={"framerate": "30", "video_size": "640x480"})
                return MediaPlayer("default", format="pulse")
            return None
        except Exception as exc:  # noqa: BLE001
            log.warning("[CallClient] MediaPlayer 신설 fail system=%s video=%s — %r", system, video, exc)
            return None

    def _build_ice_servers(self):  # type: ignore[no-untyped-def]
        """STUN + TURN iceServer list 생성 (cycle 169.60 회수)."""
        if not AIORTC_AVAILABLE:
            return []
        servers = [RTCIceServer(urls=[self._stun_url])]
        if self._turn_url:
            servers.append(
                RTCIceServer(
                    urls=[self._turn_url],
                    username=self._turn_username or None,
                    credential=self._turn_credential or None,
                )
            )
        return servers

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
        config = RTCConfiguration(self._build_ice_servers())
        self._pc = RTCPeerConnection(configuration=config)
        self._video_enabled = video

        @self._pc.on("connectionstatechange")
        async def _on_state():
            self._notify(self._pc.connectionState)

        @self._pc.on("track")
        def _on_track(track):
            log.info("[CallClient] remote track 수신 kind=%s", track.kind)
            self._remote_track = track

        # MediaPlayer 로 audio + video device capture (cycle 169.60 회수)
        try:
            import platform
            self._media_player = self._build_media_player(platform.system(), video=video)
            if self._media_player is not None:
                if self._media_player.audio is not None:
                    self._pc.addTrack(self._media_player.audio)
                    log.info("[CallClient] audio track 추가 PASS")
                if video and self._media_player.video is not None:
                    self._pc.addTrack(self._media_player.video)
                    log.info("[CallClient] video track 추가 PASS")
            else:
                log.info("[CallClient] media device 부재 — silence/black fallback")
        except Exception as exc:  # noqa: BLE001
            log.warning("[CallClient] MediaPlayer capture 실패 — %r", exc)
            self._media_player = None

        @self._pc.on("icecandidate")
        async def _on_ice(candidate):
            if self._signaling is not None and self._peer_id and candidate is not None:
                try:
                    await self._signaling.send_ice(self._peer_id, {
                        "candidate": candidate.candidate,
                        "sdpMid": candidate.sdpMid,
                        "sdpMLineIndex": candidate.sdpMLineIndex,
                    })
                except Exception as exc:  # noqa: BLE001
                    log.warning("[CallClient] ICE send fail — %r", exc)

        offer = await self._pc.createOffer()
        await self._pc.setLocalDescription(offer)

        # signaling 으로 SDP offer 전송 (peer_id + signaling_client 주입 시점만)
        if self._signaling is not None and self._peer_id:
            try:
                await self._signaling.send_offer(self._peer_id, self._pc.localDescription.sdp)
            except Exception as exc:  # noqa: BLE001
                log.warning("[CallClient] offer send fail — %r", exc)

        return {"sdp": self._pc.localDescription.sdp, "type": "offer"}

    async def accept_offer(self, remote_sdp: str, video: bool = False) -> Optional[dict]:
        """incoming call — remote SDP set + answer 생성."""
        if not AIORTC_AVAILABLE:
            return None
        config = RTCConfiguration(self._build_ice_servers())
        self._pc = RTCPeerConnection(configuration=config)
        self._video_enabled = video

        await self._pc.setRemoteDescription(RTCSessionDescription(sdp=remote_sdp, type="offer"))
        answer = await self._pc.createAnswer()
        await self._pc.setLocalDescription(answer)

        # signaling 으로 answer 전송
        if self._signaling is not None and self._peer_id:
            try:
                await self._signaling.send_answer(self._peer_id, self._pc.localDescription.sdp)
            except Exception as exc:  # noqa: BLE001
                log.warning("[CallClient] answer send fail — %r", exc)

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
