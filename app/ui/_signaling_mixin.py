# SPDX-License-Identifier: GPL-3.0-or-later
"""SignalingMixin — WebRTC signaling 4 slot chain (cycle 169.520 신설).

계층 위치 — app/ui MainWindow mixin(정본 §E). signaling_client 의 pyqtSignal 을
받는 slot 4종을 MainWindow 에 합성한다 — call_client/CallDialog 결선 진입점.

codex 2.5 HIGH 진입 6차 — main_window.py 책임 분리.
cavecrew-investigator verdict — 59 line, LOW risk (self-contained WebRTC peer flow).

분리 대상 method (cycle 169.59 origin):
- `_on_signaling_offer(from_peer, sdp)` — incoming OFFER → CallDialog + CallClient.accept_offer
- `_on_signaling_answer(from_peer, sdp)` — incoming ANSWER → call_client.apply_answer
- `_on_signaling_ice(from_peer, candidate)` — incoming ICE → pc.addIceCandidate
- `_on_signaling_peer_joined(peer_id)` — peer joined → _active_peer_id set

본 mixin 안 의존 attribute:
- `_config` (stun_url, turn_url, turn_username, turn_credential)
- `_signaling_client`, `_active_call_client`, `_active_peer_id`
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSlot

log = logging.getLogger(__name__)


class SignalingMixin:
    """WebRTC signaling 4 slot chain mixin (cycle 169.520)."""

    @pyqtSlot(str, str)
    def _on_signaling_offer(self, from_peer: str, sdp: str) -> None:
        """incoming OFFER → CallDialog incoming=True + CallClient.accept_offer (cycle 169.59)."""
        log.info("[call] incoming OFFER from=%s sdp_len=%d", from_peer, len(sdp))
        from app.ui.call_dialog import CallDialog
        from app.net.call_client import CallClient
        stun_url = getattr(self._config, "stun_url", "stun:stun.l.google.com:19302")
        turn_url = getattr(self._config, "turn_url", "")
        turn_username = getattr(self._config, "turn_username", "")
        turn_credential = getattr(self._config, "turn_credential", "")
        signaling = getattr(self, "_signaling_client", None)
        call_client = CallClient(
            stun_url=stun_url, signaling_client=signaling, peer_id=from_peer,
            turn_url=turn_url, turn_username=turn_username, turn_credential=turn_credential,
        )
        self._active_call_client = call_client
        # accept_offer fire (background) + CallDialog incoming=True modal
        import asyncio
        asyncio.ensure_future(call_client.accept_offer(remote_sdp=sdp, video=False))
        dialog = CallDialog(peer_name=from_peer, video_enabled=False, incoming=True, parent=self)
        dialog.attach_client(call_client)
        # cycle 169.838 — 별도 OS 윈도우 .exec() → 메인 레이아웃 안 in-app overlay 모달.
        self._exec_dialog_centered(dialog)

    @pyqtSlot(str, str)
    def _on_signaling_answer(self, from_peer: str, sdp: str) -> None:
        """incoming ANSWER → call_client.apply_answer dispatch."""
        log.info("[call] incoming ANSWER from=%s", from_peer)
        client = getattr(self, "_active_call_client", None)
        if client is None:
            log.warning("[call] active client 부재 — answer drop")
            return
        import asyncio
        asyncio.ensure_future(client.apply_answer(remote_sdp=sdp))

    @pyqtSlot(str, dict)
    def _on_signaling_ice(self, from_peer: str, candidate: dict) -> None:
        """incoming ICE candidate → pc.addIceCandidate dispatch."""
        log.debug("[call] incoming ICE from=%s", from_peer)
        client = getattr(self, "_active_call_client", None)
        if client is None or client._pc is None:
            return
        import asyncio
        try:
            from aiortc import RTCIceCandidate
            cand = RTCIceCandidate(
                candidate=candidate.get("candidate", ""),
                sdpMid=candidate.get("sdpMid"),
                sdpMLineIndex=candidate.get("sdpMLineIndex"),
            )
            asyncio.ensure_future(client._pc.addIceCandidate(cand))
        except Exception as exc:
            log.warning("[call] ICE addCandidate fail — %r", exc)

    @pyqtSlot(str)
    def _on_signaling_peer_joined(self, peer_id: str) -> None:
        """peer joined → active peer 자동 set (단일 peer chain)."""
        log.info("[signaling] peer joined — peer_id=%s", peer_id)
        self._active_peer_id = peer_id
