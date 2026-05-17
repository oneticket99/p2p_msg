"""SignalingClient — aiohttp WebSocket 기반 시그널링 클라이언트.

시그널링 프로토콜은 ``server/protocol.py`` 와 ``server/README.md §3`` 의
명세를 그대로 따른다.

- 클라이언트 → 서버: ``JOIN`` / ``LEAVE`` / ``OFFER`` / ``ANSWER`` / ``ICE``
- 서버 → 클라이언트: ``PEERS`` / ``PEER_JOINED`` / ``PEER_LEFT`` / ``ERROR``

본 클라이언트는 위 envelope 의 ``from_`` 내부 키를 와이어 포맷 ``from`` 으로
변환하여 송신한다 — ``server.protocol.internal_to_wire`` 와 동일한 정책.

Qt 통합 메모:

- 본 클래스는 ``QObject`` 를 상속하여 ``pyqtSignal`` 5종을 노출한다.
- Qt 신호는 Qt 의 모든 스레드(여기서는 qasync 단일 스레드)에서 자동으로
  슬롯에 전달된다 — 외부 위젯이 별도 동기화 없이 슬롯을 연결할 수 있다.
- 본 Phase 1 스켈레톤은 WebSocket 수신 루프 골격까지만 제공하며, 실제
  WebRTC PeerConnection 연동은 Task #16 에서 본 시그널의 슬롯으로 결합된다.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

import aiohttp
from PyQt6.QtCore import QObject, pyqtSignal

from app.core.app_state import AppState
from app.core.config import Config

log = logging.getLogger(__name__)


# 와이어 포맷 ``from`` ↔ 내부 ``from_`` 변환은 본 모듈 안에 동봉
# (server.protocol 을 클라이언트가 import 하지 않도록 격리)
def _internal_to_wire(payload: dict[str, Any]) -> dict[str, Any]:
    """내부 dict 의 ``from_`` 키를 와이어 ``from`` 으로 치환."""

    if "from_" in payload:
        converted = dict(payload)
        converted["from"] = converted.pop("from_")
        return converted
    return payload


def _wire_to_internal(payload: dict[str, Any]) -> dict[str, Any]:
    """와이어 dict 의 ``from`` 키를 내부 ``from_`` 으로 치환."""

    if "from" in payload and "from_" not in payload:
        converted = dict(payload)
        converted["from_"] = converted.pop("from")
        return converted
    return payload


class SignalingClient(QObject):
    """시그널링 서버 WebSocket 클라이언트.

    상태 머신:

    ```
    [INIT] --connect()--> [CONNECTING] --ws_connect ok--> [CONNECTED]
                                  └ 실패 ──> [ERROR]
    [CONNECTED] --disconnect()/close--> [DISCONNECTED]
    ```

    Qt 신호:

    - ``connection_state_changed(str)`` : DISCONNECTED/CONNECTING/CONNECTED/ERROR
    - ``peers_received(list)``          : ``PEERS`` 응답
    - ``peer_joined(str)``              : ``PEER_JOINED`` 알림
    - ``peer_left(str)``                : ``PEER_LEFT`` 알림
    - ``offer_received(str, str)``      : (from, sdp)
    - ``answer_received(str, str)``     : (from, sdp)
    - ``ice_received(str, dict)``       : (from, candidate)
    - ``error_received(str, str)``      : (code, message)
    """

    # ---- Qt 신호 정의 (스켈레톤 단계에서 정의만, 슬롯 결합은 Task #16) ----
    connection_state_changed = pyqtSignal(str)
    peers_received = pyqtSignal(list)
    peer_joined = pyqtSignal(str)
    peer_left = pyqtSignal(str)
    offer_received = pyqtSignal(str, str)
    answer_received = pyqtSignal(str, str)
    ice_received = pyqtSignal(str, dict)
    error_received = pyqtSignal(str, str)

    def __init__(self, config: Config, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self._config: Config = config
        self._state: AppState = AppState.instance()

        # aiohttp 세션·웹소켓 — connect() 호출 시 생성
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None

        # 수신 루프 태스크 핸들 (취소·종료 제어용)
        self._recv_task: Optional[asyncio.Task[None]] = None

    # ------------------------------------------------------------------
    # public API — 호출자는 모두 코루틴이므로 ``await`` 필요
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """시그널링 서버에 WebSocket 연결.

        성공 시 ``connection_state_changed("CONNECTED")`` 신호 발행 후
        백그라운드 수신 루프(``_recv_loop``) 를 ``create_task`` 로 예약한다.
        실패 시 ``ERROR`` 상태로 전이하고 예외를 호출자에게 propagate.
        """

        self._set_state("CONNECTING")
        url = self._config.signaling_url
        log.info("시그널링 WebSocket 연결 시도 — url=%s", url)

        try:
            self._session = aiohttp.ClientSession()
            self._ws = await self._session.ws_connect(url, heartbeat=30.0)
        except Exception:
            log.exception("시그널링 연결 실패 — url=%s", url)
            await self._cleanup()
            self._set_state("ERROR")
            raise

        self._set_state("CONNECTED")
        # 백그라운드 수신 루프 예약 — Qt 슬롯에서 await 하지 않아도 동작
        self._recv_task = asyncio.create_task(
            self._recv_loop(), name="signaling-recv-loop"
        )

    async def disconnect(self) -> None:
        """연결 종료 — LEAVE 송신 후 WebSocket/세션 정리.

        이미 끊어진 상태라면 멱등하게 통과한다.
        """

        if self._state.room_id and self._state.peer_id and self._ws is not None:
            try:
                await self.leave(self._state.room_id, self._state.peer_id)
            except Exception:
                log.exception("LEAVE 전송 중 오류 — 무시하고 정리 진행")

        await self._cleanup()
        self._set_state("DISCONNECTED")

    async def join(self, room_id: str, peer_id: str) -> None:
        """``JOIN`` 메시지 송신 + AppState 식별자 등록."""

        await self._send({"type": "JOIN", "room": room_id, "peer_id": peer_id})
        self._state.set_identity(room_id=room_id, peer_id=peer_id)

    async def leave(self, room_id: str, peer_id: str) -> None:
        """``LEAVE`` 메시지 송신 (식별자 초기화는 disconnect 가 담당)."""

        await self._send({"type": "LEAVE", "room": room_id, "peer_id": peer_id})

    async def send_offer(self, to: str, sdp: str) -> None:
        """``OFFER`` 송신 — 본인 peer_id 가 미등록이면 거부."""

        from_ = self._require_self_peer_id()
        await self._send(
            {"type": "OFFER", "from_": from_, "to": to, "sdp": sdp}
        )

    async def send_answer(self, to: str, sdp: str) -> None:
        """``ANSWER`` 송신."""

        from_ = self._require_self_peer_id()
        await self._send(
            {"type": "ANSWER", "from_": from_, "to": to, "sdp": sdp}
        )

    async def send_ice(self, to: str, candidate: dict[str, Any]) -> None:
        """``ICE`` candidate 송신."""

        from_ = self._require_self_peer_id()
        await self._send(
            {
                "type": "ICE",
                "from_": from_,
                "to": to,
                "candidate": candidate,
            }
        )

    # ------------------------------------------------------------------
    # 내부 — 송신/수신/상태 전이
    # ------------------------------------------------------------------

    async def _send(self, payload: dict[str, Any]) -> None:
        """내부 표현 dict 를 와이어 포맷으로 변환 후 텍스트 프레임 송신."""

        if self._ws is None or self._ws.closed:
            raise RuntimeError("시그널링 WebSocket 이 연결돼 있지 않습니다.")
        wire = _internal_to_wire(payload)
        await self._ws.send_str(json.dumps(wire, ensure_ascii=False))
        log.debug("→ %s", wire)

    async def _recv_loop(self) -> None:
        """WebSocket 수신 루프 — 종료 시 ``DISCONNECTED`` 또는 ``ERROR`` 로 전이.

        텍스트 프레임만 처리하고, 그 외(바이너리/PING/PONG) 는 무시한다.
        JSON 파싱 실패 또는 알 수 없는 ``type`` 은 로그만 남기고 루프 유지.
        """

        assert self._ws is not None, "_recv_loop 진입 전 _ws 가 None"
        try:
            async for frame in self._ws:
                if frame.type == aiohttp.WSMsgType.TEXT:
                    self._handle_text_frame(frame.data)
                elif frame.type == aiohttp.WSMsgType.ERROR:
                    log.error(
                        "WebSocket 프레임 오류 — exception=%s",
                        self._ws.exception(),
                    )
                    break
                elif frame.type in (
                    aiohttp.WSMsgType.CLOSE,
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSING,
                ):
                    log.info("WebSocket close 프레임 수신 — 루프 종료")
                    break
        except asyncio.CancelledError:
            log.debug("수신 루프 cancelled")
            raise
        except Exception:
            log.exception("수신 루프에서 예외 발생")
            self._set_state("ERROR")
            return
        finally:
            # 정상 종료 시 DISCONNECTED 로 전이
            if self._state.connection_state != "ERROR":
                self._set_state("DISCONNECTED")

    def _handle_text_frame(self, raw: str) -> None:
        """수신 텍스트 프레임 → JSON 파싱 → 신호 발행."""

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("JSON 파싱 실패 — raw=%r", raw[:200])
            return

        if not isinstance(payload, dict):
            log.warning("dict 가 아닌 payload 수신 — raw=%r", raw[:200])
            return

        payload = _wire_to_internal(payload)
        msg_type = payload.get("type")
        log.debug("← %s", payload)

        if msg_type == "PEERS":
            peers = list(payload.get("peers") or [])
            self._state.replace_peers(peers)
            self.peers_received.emit(peers)
        elif msg_type == "PEER_JOINED":
            peer = str(payload.get("peer_id") or "")
            if peer:
                self._state.add_peer(peer)
                self.peer_joined.emit(peer)
        elif msg_type == "PEER_LEFT":
            peer = str(payload.get("peer_id") or "")
            if peer:
                self._state.remove_peer(peer)
                self.peer_left.emit(peer)
        elif msg_type == "OFFER":
            self.offer_received.emit(
                str(payload.get("from_") or ""),
                str(payload.get("sdp") or ""),
            )
        elif msg_type == "ANSWER":
            self.answer_received.emit(
                str(payload.get("from_") or ""),
                str(payload.get("sdp") or ""),
            )
        elif msg_type == "ICE":
            candidate = payload.get("candidate") or {}
            if not isinstance(candidate, dict):
                candidate = {}
            self.ice_received.emit(
                str(payload.get("from_") or ""),
                candidate,
            )
        elif msg_type == "ERROR":
            self.error_received.emit(
                str(payload.get("code") or "UNKNOWN"),
                str(payload.get("message") or ""),
            )
        else:
            log.warning("알 수 없는 메시지 type=%r — 무시", msg_type)

    def _require_self_peer_id(self) -> str:
        """본인 peer_id 가 ``AppState`` 에 등록돼 있지 않으면 예외."""

        peer_id = self._state.peer_id
        if not peer_id:
            raise RuntimeError(
                "본인 peer_id 가 등록돼 있지 않습니다 — join() 을 먼저 호출하세요."
            )
        return peer_id

    def _set_state(self, state: str) -> None:
        """상태 전이 헬퍼 — AppState 갱신 + Qt 신호 발행."""

        self._state.set_connection_state(state)
        self.connection_state_changed.emit(state)

    async def _cleanup(self) -> None:
        """WebSocket + ClientSession + 수신 태스크 일괄 정리 (멱등)."""

        if self._recv_task is not None and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except (asyncio.CancelledError, Exception):
                # 정리 단계 예외는 호출자에게 propagate 하지 않는다
                pass
        self._recv_task = None

        if self._ws is not None and not self._ws.closed:
            try:
                await self._ws.close()
            except Exception:
                log.exception("WebSocket close 중 예외 — 무시")
        self._ws = None

        if self._session is not None and not self._session.closed:
            try:
                await self._session.close()
            except Exception:
                log.exception("aiohttp ClientSession close 중 예외 — 무시")
        self._session = None
