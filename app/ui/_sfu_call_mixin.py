# SPDX-License-Identifier: GPL-3.0-or-later
"""SfuCallMixin — SFU 그룹 통화 배선 (cycle 169.807 M4b-2b).

server-side SFU + SfuCallClient(net) + GroupCallDialog(UI) 를 MainWindow 에서
한 곳으로 묶는 mixin. SignalingClient 의 SFU 수신 신호(sfu_answer_received /
sfu_producers_received)를 SfuCallClient 의 async 핸들러로 라우팅하고,
SfuCallClient 가 받은 forward track 을 GroupCallDialog 타일로 표시한다.

본 mixin 은 ``self._signaling_client`` (SignalingClient) 가 주입돼 있다고 가정한다.
Qt 신호 → async 핸들러 연결은 ``asyncio.ensure_future`` 로 스케줄한다 (qasync
event loop 정합).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

log = logging.getLogger(__name__)


class SfuCallMixin:
    """MainWindow 에 합성되는 SFU 그룹 통화 제어 mixin."""

    # 합성 대상이 보유한다고 가정하는 속성 (타입 힌트용)
    _signaling_client: Any

    def _init_sfu_call(self) -> None:
        """SFU 통화 상태 초기화 — MainWindow __init__ 에서 1회 호출."""
        self._sfu_call_client: Optional[Any] = None
        self._group_call_dialog: Optional[Any] = None
        self._sfu_signals_connected = False

    def start_group_call(
        self, room_id: str, peer_id: str, video: bool = False
    ) -> None:
        """그룹 통화 시작 — SfuCallClient + GroupCallDialog 생성 + publish.

        SfuCallClient 의 forward track 을 GroupCallDialog 타일로 잇고,
        SignalingClient SFU 신호를 async 핸들러로 연결한 뒤 로컬 미디어를
        publish 한다.
        """
        from app.net.sfu_call_client import SfuCallClient
        from app.ui.group_call_dialog import GroupCallDialog

        # 한글 주석 — 재진입 시 기존 통화를 먼저 정리 (dialog/client leak 방지)
        if self._sfu_call_client is not None or self._group_call_dialog is not None:
            self.end_group_call()

        parent = self if hasattr(self, "show") else None
        self._group_call_dialog = GroupCallDialog(room_id, parent=parent)

        async def _send(payload: dict[str, Any]) -> None:
            # 한글 주석 — SfuCallClient 가 만든 완성 payload 를 signaling 으로 송신
            await self._signaling_client._send(payload)

        def _on_track(producer_id: str, track: Any) -> None:
            # 한글 주석 — forward track 도달 시 GroupCallDialog 타일 추가
            if self._group_call_dialog is not None:
                self._group_call_dialog.add_remote_track(producer_id, track)

        self._sfu_call_client = SfuCallClient(
            room_id, peer_id, _send, on_remote_track=_on_track
        )
        self._connect_sfu_signals()
        # cycle 169.838 — 별도 OS 윈도우(.show()) → 메인 레이아웃 안 in-app overlay.
        # publish 가 이어서 async 스케줄돼야 하므로 비차단 embed 헬퍼 사용(loop.exec() 생략).
        if hasattr(self, "_embed_dialog_centered"):
            self._embed_dialog_centered(self._group_call_dialog)
        else:
            self._group_call_dialog.show()
        asyncio.ensure_future(self._sfu_call_client.publish(video=video))

    def _connect_sfu_signals(self) -> None:
        """SignalingClient SFU 수신 신호 → mixin 슬롯 연결 (중복 연결 차단)."""
        if self._sfu_signals_connected or self._signaling_client is None:
            return
        self._signaling_client.sfu_answer_received.connect(self._on_sfu_answer)
        self._signaling_client.sfu_producers_received.connect(self._on_sfu_producers)
        self._sfu_signals_connected = True

    def _disconnect_sfu_signals(self) -> None:
        """SFU 신호 연결 해제 (통화 종료 시)."""
        if not self._sfu_signals_connected or self._signaling_client is None:
            return
        try:
            self._signaling_client.sfu_answer_received.disconnect(self._on_sfu_answer)
            self._signaling_client.sfu_producers_received.disconnect(self._on_sfu_producers)
        except (TypeError, RuntimeError) as exc:
            log.warning("[SfuCallMixin] SFU 신호 해제 실패 — %r", exc)
        self._sfu_signals_connected = False

    def _on_sfu_answer(self, kind: str, sdp: str, producer_id: str) -> None:
        """sfu_answer_received 슬롯 — async handle_sfu_answer 스케줄."""
        if self._sfu_call_client is not None:
            asyncio.ensure_future(
                self._sfu_call_client.handle_sfu_answer(kind, sdp, producer_id)
            )

    def _on_sfu_producers(self, room: str, producers: list) -> None:
        """sfu_producers_received 슬롯 — async handle_producers 스케줄."""
        if self._sfu_call_client is not None:
            asyncio.ensure_future(
                self._sfu_call_client.handle_producers(list(producers))
            )

    def end_group_call(self) -> None:
        """그룹 통화 종료 — SfuCallClient close + GroupCallDialog 정리 + 신호 해제."""
        self._disconnect_sfu_signals()
        if self._sfu_call_client is not None:
            asyncio.ensure_future(self._sfu_call_client.close())
            self._sfu_call_client = None
        if self._group_call_dialog is not None:
            self._group_call_dialog.close_all()
            # cycle 169.838 — in-app overlay backdrop 정리 (embed 시 부착한 dim layer)
            backdrop = getattr(self._group_call_dialog, "_embed_backdrop", None)
            if backdrop is not None:
                try:
                    backdrop.hide()
                    backdrop.deleteLater()
                except Exception:
                    pass
            self._group_call_dialog.close()
            self._group_call_dialog = None

    def _on_start_group_call(self) -> None:
        """메뉴 entry — 현재 합류한 방의 room/peer 로 그룹 통화 시작.

        AppState(self._state) 의 room_id/peer_id 가 모두 있어야 시작한다 (방
        미입장 시 no-op + 로그). 영상 기본 on 으로 publish 한다.
        """
        state = getattr(self, "_state", None)
        room_id = getattr(state, "room_id", None) if state is not None else None
        peer_id = getattr(state, "peer_id", None) if state is not None else None
        if not room_id or not peer_id:
            log.warning("[SfuCallMixin] 그룹 통화 시작 불가 — 방 미입장 (room/peer 부재)")
            return
        self.start_group_call(room_id, peer_id, video=True)
