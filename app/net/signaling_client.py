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
- 본 클라이언트는 WebSocket 수신 루프 + 자동 재연결(backoff + reJOIN, cycle 169.775)
  까지 제공한다. WebRTC PeerConnection 연동은 본 시그널의 슬롯으로 결합된다.
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
                                  └ 최초 실패 ──> [ERROR]
    [CONNECTED] --비정상 drop--> [RECONNECTING] --backoff connect ok--> [CONNECTED] (+reJOIN)
                                       └ max_attempts 초과 ──> [ERROR]
    [CONNECTED]/[RECONNECTING] --disconnect()--> [DISCONNECTED]
    ```

    자동 재연결: ``connect()`` 성공 후 수신 루프가 비정상 종료하면 ``disconnect()``
    호출 전까지 지수 backoff 로 재연결하고, 마지막 ``join()`` 식별자로 reJOIN 복구한다.

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

        # cycle 169.775 — 자동 재연결(backoff + reJOIN) 상태
        # connect() 성공 후 True, disconnect() 시 False — 비정상 drop 과
        # 명시적 종료를 구분하는 단일 플래그
        self._should_reconnect: bool = False
        self._reconnect_task: Optional[asyncio.Task[None]] = None
        # 마지막 JOIN 식별자 — 재연결 후 reJOIN 복구에 사용
        self._last_room_id: Optional[str] = None
        self._last_peer_id: Optional[str] = None
        # backoff 파라미터 — config override 가능(getattr fallback), test 는 직접 주입
        self._reconnect_base_delay: float = float(
            getattr(config, "signaling_reconnect_base_delay", 0.5)
        )
        self._reconnect_max_delay: float = float(
            getattr(config, "signaling_reconnect_max_delay", 30.0)
        )
        self._reconnect_multiplier: float = float(
            getattr(config, "signaling_reconnect_multiplier", 2.0)
        )
        # 0 = 무한 재시도 (사용자가 disconnect 할 때까지)
        self._reconnect_max_attempts: int = int(
            getattr(config, "signaling_reconnect_max_attempts", 0)
        )

    # ------------------------------------------------------------------
    # public API — 호출자는 모두 코루틴이므로 ``await`` 필요
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """시그널링 서버에 WebSocket 연결 (자동 재연결 활성).

        성공 시 ``connection_state_changed("CONNECTED")`` 신호 발행 후
        백그라운드 수신 루프(``_recv_loop``) 를 ``create_task`` 로 예약한다.
        이후 수신 루프가 비정상 종료하면 ``disconnect()`` 호출 전까지
        backoff 재연결 + reJOIN 을 자동 수행한다.
        최초 연결 실패 시에는 ``ERROR`` 상태로 전이하고 예외를 propagate 한다.
        """

        # 명시적 connect → 자동 재연결 의지 on
        self._should_reconnect = True
        try:
            await self._connect_once()
        except Exception:
            log.exception("시그널링 최초 연결 실패 — url=%s", self._config.signaling_url)
            self._set_state("ERROR")
            raise

    async def _connect_once(self) -> None:
        """단발 WebSocket 연결 + 수신 루프 시작 (재연결 루프가 재사용).

        성공 시 ``CONNECTED`` 전이 + 수신 루프 예약. 실패 시 소켓만 정리하고
        예외를 호출자(connect 또는 _reconnect_loop)에게 propagate 한다.
        상태 전이(ERROR/RECONNECTING) 판단은 호출자가 담당한다.
        """

        self._set_state("CONNECTING")
        url = self._config.signaling_url
        log.info("시그널링 WebSocket 연결 시도 — url=%s", url)

        try:
            self._session = aiohttp.ClientSession()
            self._ws = await self._session.ws_connect(url, heartbeat=30.0)
        except Exception:
            # 소켓만 정리 (재연결 task 는 건드리지 않는다)
            await self._close_sockets()
            raise

        self._set_state("CONNECTED")
        # 백그라운드 수신 루프 예약 — Qt 슬롯에서 await 하지 않아도 동작
        self._recv_task = asyncio.create_task(
            self._recv_loop(), name="signaling-recv-loop"
        )

    async def disconnect(self) -> None:
        """연결 종료 — 자동 재연결 중단 + LEAVE 송신 후 WebSocket/세션 정리.

        이미 끊어진 상태라면 멱등하게 통과한다. 본 호출은 "의도적 종료"이므로
        진행 중인 재연결 루프를 먼저 취소해 비정상 drop 과 구분한다.
        """

        # 명시적 종료 → 자동 재연결 의지 off (recv loop finally 가 reconnect 예약 안 하도록)
        self._should_reconnect = False
        await self._cancel_reconnect()

        if self._state.room_id and self._state.peer_id and self._ws is not None:
            try:
                await self.leave(self._state.room_id, self._state.peer_id)
            except Exception:
                log.exception("LEAVE 전송 중 오류 — 무시하고 정리 진행")

        await self._cleanup()
        self._set_state("DISCONNECTED")
        # reJOIN 식별자 초기화 (다음 connect 는 새 join 의무)
        self._last_room_id = None
        self._last_peer_id = None

    async def join(self, room_id: str, peer_id: str) -> None:
        """``JOIN`` 메시지 송신 + AppState 식별자 등록 + reJOIN 식별자 기록."""

        await self._send({"type": "JOIN", "room": room_id, "peer_id": peer_id})
        self._state.set_identity(room_id=room_id, peer_id=peer_id)
        # 재연결 후 reJOIN 복구용 — 마지막 JOIN 식별자 보관
        self._last_room_id = room_id
        self._last_peer_id = peer_id

    async def leave(self, room_id: str, peer_id: str) -> None:
        """``LEAVE`` 메시지 송신 (식별자 초기화는 disconnect 가 담당)."""

        await self._send({"type": "LEAVE", "room": room_id, "peer_id": peer_id})

    async def send_offer(self, to: str, sdp: str) -> None:
        """``OFFER`` 송신 — self peer_id 가 미등록이면 거부."""

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
            # 예외도 비정상 drop 으로 취급 — finally 가 재연결 판단
            log.exception("수신 루프에서 예외 발생")
        finally:
            # 현 소켓은 이미 종료됨 — 핸들 초기화 (재연결이 새 소켓 생성)
            self._ws = None
            if self._should_reconnect:
                # 비정상 drop (disconnect() 미호출) → backoff 재연결 + reJOIN 예약
                log.warning("시그널링 비정상 종료 감지 — 자동 재연결 예약")
                self._schedule_reconnect()
            elif self._state.connection_state != "ERROR":
                # 명시적 종료 경로 — DISCONNECTED 전이
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
        """self peer_id 가 ``AppState`` 에 등록돼 있지 않으면 예외."""

        peer_id = self._state.peer_id
        if not peer_id:
            raise RuntimeError(
                "self peer_id 가 등록돼 있지 않습니다 — join() 을 먼저 호출하세요."
            )
        return peer_id

    def _set_state(self, state: str) -> None:
        """상태 전이 헬퍼 — AppState 갱신 + Qt 신호 발행."""

        self._state.set_connection_state(state)
        self.connection_state_changed.emit(state)

    # ------------------------------------------------------------------
    # 자동 재연결 (backoff + reJOIN) — cycle 169.775
    # ------------------------------------------------------------------

    def _schedule_reconnect(self) -> None:
        """재연결 루프 task 예약 (이미 진행 중이면 멱등 통과)."""

        if self._reconnect_task is not None and not self._reconnect_task.done():
            return
        self._reconnect_task = asyncio.create_task(
            self._reconnect_loop(), name="signaling-reconnect"
        )

    async def _reconnect_loop(self) -> None:
        """backoff 재연결 + reJOIN 복구 루프.

        ``_should_reconnect`` 가 True 인 동안 지수 backoff 로 재연결을 시도한다.
        성공 시 마지막 JOIN 식별자로 reJOIN 복구 후 종료(새 수신 루프가 동작).
        ``_reconnect_max_attempts`` 도달 시 ``ERROR`` 전이 후 포기.
        """

        attempt = 0
        delay = self._reconnect_base_delay
        while self._should_reconnect:
            self._set_state("RECONNECTING")
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                # disconnect() 가 취소 → 조용히 종료
                raise
            if not self._should_reconnect:
                return

            try:
                await self._connect_once()
            except Exception:
                attempt += 1
                log.warning(
                    "시그널링 재연결 시도 %d 실패 — %.1fs 후 재시도", attempt, delay
                )
                if (
                    self._reconnect_max_attempts
                    and attempt >= self._reconnect_max_attempts
                ):
                    log.error("재연결 최대 시도(%d) 초과 — 포기", self._reconnect_max_attempts)
                    self._set_state("ERROR")
                    return
                # 지수 backoff (상한 cap)
                delay = min(delay * self._reconnect_multiplier, self._reconnect_max_delay)
                continue

            # 연결 성공 → reJOIN 복구 (마지막 JOIN 식별자 보유 시)
            if self._last_room_id and self._last_peer_id:
                try:
                    await self.join(self._last_room_id, self._last_peer_id)
                    log.info(
                        "reJOIN 복구 성공 — room=%s peer=%s",
                        self._last_room_id,
                        self._last_peer_id,
                    )
                except Exception:
                    log.exception("reJOIN 송신 실패 — 다음 drop 시 재시도")
            return

    async def _cancel_reconnect(self) -> None:
        """진행 중인 재연결 루프 task 취소 (멱등)."""

        if self._reconnect_task is not None and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except (asyncio.CancelledError, Exception):
                pass
        self._reconnect_task = None

    async def _close_sockets(self) -> None:
        """WebSocket + ClientSession 만 정리 (recv/reconnect task 는 보존, 멱등)."""

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

    async def _cleanup(self) -> None:
        """수신 태스크 + WebSocket + ClientSession 일괄 정리 (멱등).

        재연결 task 는 본 함수가 건드리지 않는다(``disconnect`` 가 먼저 취소).
        """

        if self._recv_task is not None and not self._recv_task.done():
            self._recv_task.cancel()
            try:
                await self._recv_task
            except (asyncio.CancelledError, Exception):
                # 정리 단계 예외는 호출자에게 propagate 하지 않는다
                pass
        self._recv_task = None

        await self._close_sockets()
