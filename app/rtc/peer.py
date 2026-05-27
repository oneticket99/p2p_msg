# SPDX-License-Identifier: GPL-3.0-or-later
"""``RTCPeerConnection`` 래퍼 — aiortc + Qt signal 통합.

본 모듈은 aiortc 의 ``RTCPeerConnection`` 를 한 단계 감싸 ``app.net.
signaling_client.SignalingClient`` 와 결선하기 쉬운 형태로 제공한다. 본
래퍼는 시그널링 자체를 직접 알지 못한다 — Offer/Answer/ICE 의 송신은
호출자(예: ``MainWindow`` 또는 별도 컨트롤러) 가 본 래퍼의 ``local_*``
signal 을 받아서 ``SignalingClient.send_*`` 코루틴을 예약한다.

설계 의도:

- 본 래퍼는 **상태 머신 + 시그널 발행** 만 담당. IO 는 aiortc 가 처리.
- 단일 1:1 연결만 지원 (Phase 1 MVP 범위). 그룹 채팅(Phase 2) 은 별 래퍼.
- DataChannel 은 본 래퍼가 생성/수신하고, 메시지 핸들러는 ``set_message_
  handler`` 로 외부 모듈(file_sender/file_receiver) 이 주입.

Qt 통합 (``QObject`` 상속) 으로 다음 신호를 노출한다.

- ``local_description_ready(str, str)``  : (sdp_type, sdp) — Offer/Answer 생성 완료
- ``local_ice_candidate(dict)``          : 신규 로컬 ICE 후보
- ``connection_state_changed(str)``      : aiortc 의 connectionState 전이
- ``data_channel_opened(str)``           : DataChannel open 이벤트 (label)
- ``data_channel_closed(str)``           : DataChannel close 이벤트 (label)
- ``text_message_received(str)``         : DataChannel JSON 텍스트 수신
- ``binary_message_received(bytes)``     : DataChannel 바이너리 수신
- ``error(str)``                         : 내부 오류 보고

계층 위치 — app/rtc 계층(정본 §E)의 1:1 PeerConnection backbone. signaling_client
(app/net)와 local_* signal 로 결합하고, file_sender/file_receiver 가 message handler
를 주입한다. mesh_manager 의 그룹 경로와 별개(1:1 전용).

의존성 — `aiortc`(RTCPeerConnection, graceful) + PyQt6 `QObject`/`pyqtSignal` +
asyncio/json. UI 직접 의존 부재(signal 경유).

범위 한계 — 1:1 연결 상태 머신 + signal 발행 + DataChannel 송수신만. SDP/ICE 실
송신은 호출자(signaling 예약), 미디어 track 은 call_client 책임. close 가 연결
자원 release.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal

try:  # aiortc 는 선택적 의존성 — import 실패 시에도 모듈 자체는 로드 가능
    from aiortc import (  # type: ignore[import-not-found]
        RTCConfiguration,
        RTCDataChannel,
        RTCIceServer,
        RTCPeerConnection,
        RTCSessionDescription,
    )
    from aiortc.contrib.signaling import (  # type: ignore[import-not-found]
        object_from_string,
        object_to_string,
    )

    _AIORTC_AVAILABLE = True
except ImportError:  # pragma: no cover - 의존성 미설치 환경 폴백
    RTCConfiguration = None  # type: ignore[assignment]
    RTCDataChannel = None  # type: ignore[assignment]
    RTCIceServer = None  # type: ignore[assignment]
    RTCPeerConnection = None  # type: ignore[assignment]
    RTCSessionDescription = None  # type: ignore[assignment]
    object_from_string = None  # type: ignore[assignment]
    object_to_string = None  # type: ignore[assignment]
    _AIORTC_AVAILABLE = False

from app.core.config import Config

log = logging.getLogger(__name__)


# 외부에서 주입하는 메시지 핸들러 타입
# - text payload(str) → 코루틴
# - binary payload(bytes) → 코루틴
TextHandler = Callable[[str], Awaitable[None]]
BinaryHandler = Callable[[bytes], Awaitable[None]]


class Peer(QObject):
    """단일 1:1 ``RTCPeerConnection`` 래퍼.

    수명 주기:

    1. ``__init__`` — aiortc PeerConnection 인스턴스 + 이벤트 핸들러 결선
    2. ``create_offer`` — Offer SDP 생성 + 시그널 발행 (Caller 흐름)
    3. ``apply_remote_offer`` + ``create_answer`` — Callee 흐름
    4. ``apply_remote_answer`` — Caller 가 Answer 받았을 때
    5. ``add_remote_ice_candidate`` — 양쪽 ICE 후보 누적
    6. ``close`` — 정상 종료

    Notes
    -----
    aiortc 의 PeerConnection 은 자체적으로 asyncio 기반이므로 모든 메서드는
    코루틴이다 (정본 §E — 비동기 전용).
    """

    # ---- Qt 신호 ----
    local_description_ready = pyqtSignal(str, str)  # (sdp_type, sdp)
    local_ice_candidate = pyqtSignal(dict)
    connection_state_changed = pyqtSignal(str)
    data_channel_opened = pyqtSignal(str)
    data_channel_closed = pyqtSignal(str)
    text_message_received = pyqtSignal(str)
    binary_message_received = pyqtSignal(bytes)
    error = pyqtSignal(str)

    # DataChannel 기본 라벨 — 양쪽이 동일해야 매칭됨
    DEFAULT_CHANNEL_LABEL = "tootalk-data"

    def __init__(
        self,
        config: Config,
        *,
        channel_label: Optional[str] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        """aiortc PeerConnection 생성 + 이벤트 핸들러 결선.

        Parameters
        ----------
        config : Config
            ``.env`` 로딩 결과. ``stun_url`` / TURN 자격증명을 사용.
        channel_label : str | None
            DataChannel 라벨. 양쪽이 동일해야 매칭됨. None 이면 기본값.
        parent : QObject | None
            Qt 상위 객체.
        """

        super().__init__(parent)

        if not _AIORTC_AVAILABLE:
            raise ImportError(
                "aiortc 가 설치돼 있지 않습니다 — "
                "app/requirements.txt 의 aiortc>=1.9 를 설치하세요."
            )

        self._config: Config = config
        self._channel_label: str = channel_label or self.DEFAULT_CHANNEL_LABEL

        # 외부에서 주입하는 메시지 핸들러 — 미설정 시 Qt signal 만 발행
        self._text_handler: Optional[TextHandler] = None
        self._binary_handler: Optional[BinaryHandler] = None

        # aiortc RTCPeerConnection — ICE 서버 구성 적용
        ice_servers: list[RTCIceServer] = [RTCIceServer(urls=[config.stun_url])]
        if config.turn_url:
            ice_servers.append(
                RTCIceServer(
                    urls=[config.turn_url],
                    username=config.turn_username or None,
                    credential=config.turn_credential or None,
                )
            )
        self._pc: RTCPeerConnection = RTCPeerConnection(
            configuration=RTCConfiguration(iceServers=ice_servers)
        )

        # DataChannel — Caller 가 ``create_offer`` 직전 생성, Callee 는 수신
        self._channel: Optional[RTCDataChannel] = None

        # aiortc 이벤트 핸들러 결선
        self._wire_pc_events()

        log.info(
            "[Peer] 생성 완료 — channel_label=%s stun=%s turn=%s",
            self._channel_label,
            config.stun_url,
            bool(config.turn_url),
        )

    # ------------------------------------------------------------------
    # 외부 주입 — 메시지 핸들러
    # ------------------------------------------------------------------

    def set_message_handler(
        self,
        *,
        text: Optional[TextHandler] = None,
        binary: Optional[BinaryHandler] = None,
    ) -> None:
        """외부 모듈(file_sender/file_receiver) 의 핸들러 주입.

        주입된 핸들러는 Qt signal 발행과 별개로 호출된다 — 한쪽이 ``None``
        이면 해당 타입은 signal 만 발행되고 핸들러는 건너뛴다.
        """

        self._text_handler = text
        self._binary_handler = binary

    @property
    def channel(self) -> Optional[RTCDataChannel]:
        """현재 DataChannel — 미생성 또는 closed 면 None.

        ``file_sender.send()`` 가 본 객체를 직접 받아 ``send`` 호출.
        """

        return self._channel

    # ------------------------------------------------------------------
    # SDP / ICE 흐름 — Caller / Callee 공통 코루틴 API
    # ------------------------------------------------------------------

    async def create_offer(self) -> None:
        """Caller 흐름 — DataChannel 생성 + Offer SDP 발행.

        성공 시 ``local_description_ready('offer', sdp)`` 신호 발행.
        호출자가 그 sdp 를 ``SignalingClient.send_offer`` 로 전달한다.
        """

        self._channel = self._pc.createDataChannel(self._channel_label)
        self._wire_channel_events(self._channel)

        offer = await self._pc.createOffer()
        await self._pc.setLocalDescription(offer)
        local = self._pc.localDescription
        log.info("[Peer] Offer 생성 — type=%s len=%d", local.type, len(local.sdp))
        self.local_description_ready.emit(local.type, local.sdp)

    async def apply_remote_offer(self, sdp: str) -> None:
        """Callee 흐름 — 원격 Offer 적용. 다음 단계는 ``create_answer``."""

        desc = RTCSessionDescription(sdp=sdp, type="offer")
        await self._pc.setRemoteDescription(desc)
        log.info("[Peer] 원격 Offer 적용 — sdp_len=%d", len(sdp))

    async def create_answer(self) -> None:
        """Callee 흐름 — Answer SDP 생성 + 신호 발행.

        반드시 ``apply_remote_offer`` 이후에 호출돼야 한다.
        """

        answer = await self._pc.createAnswer()
        await self._pc.setLocalDescription(answer)
        local = self._pc.localDescription
        log.info("[Peer] Answer 생성 — type=%s len=%d", local.type, len(local.sdp))
        self.local_description_ready.emit(local.type, local.sdp)

    async def apply_remote_answer(self, sdp: str) -> None:
        """Caller 흐름 — 원격 Answer 적용. 이후 ICE 후보 교환 진행."""

        desc = RTCSessionDescription(sdp=sdp, type="answer")
        await self._pc.setRemoteDescription(desc)
        log.info("[Peer] 원격 Answer 적용 — sdp_len=%d", len(sdp))

    async def add_remote_ice_candidate(self, candidate: dict[str, Any]) -> None:
        """수신한 원격 ICE 후보를 aiortc 에 주입.

        aiortc 의 ``addIceCandidate`` 는 ``RTCIceCandidate`` 객체 또는
        candidate 문자열을 받는다. 본 래퍼는 두 형식 모두 수용한다.
        """

        if not candidate:
            # 빈 dict / null — ICE gathering 완료 신호로 해석, 무시
            log.debug("[Peer] 빈 ICE 후보 — gathering 완료로 간주, 무시")
            return

        # aiortc 1.9 이상은 ``aiortc.contrib.signaling.object_from_string``
        # 으로 candidate dict → 객체 변환을 제공한다. 사용 불가 시 폴백.
        try:
            if object_from_string is not None:
                # 본 헬퍼는 일반적으로 SDP/JSON 문자열을 받지만, 본 래퍼는
                # 후보 dict 자체를 객체로 만들기 위해 jsonify 한 뒤 전달.
                wrapped = json.dumps({**candidate, "type": "candidate"})
                obj = object_from_string(wrapped)
                await self._pc.addIceCandidate(obj)
            else:
                await self._pc.addIceCandidate(candidate)  # type: ignore[arg-type]
            log.debug("[Peer] 원격 ICE 후보 적용 — keys=%s", sorted(candidate))
        except Exception as exc:
            log.exception("[Peer] 원격 ICE 후보 적용 실패")
            self.error.emit(f"ICE 후보 적용 실패 — {exc!s}")

    # ------------------------------------------------------------------
    # 종료
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """PeerConnection + DataChannel 정상 종료 (멱등).

        aiortc 의 ``RTCPeerConnection.close()`` 는 연관 transceiver/ICE/
        DataChannel 을 모두 정리한다. 본 래퍼는 그 위에 로깅만 추가.
        """

        if self._channel is not None and self._channel.readyState != "closed":
            try:
                self._channel.close()
            except Exception:
                log.exception("[Peer] DataChannel close 중 예외 — 무시")

        try:
            await self._pc.close()
        except Exception:
            log.exception("[Peer] PeerConnection close 중 예외 — 무시")
        log.info("[Peer] 종료 완료")

    # ------------------------------------------------------------------
    # 내부 — aiortc 이벤트 결선
    # ------------------------------------------------------------------

    def _wire_pc_events(self) -> None:
        """aiortc PeerConnection 의 이벤트를 Qt signal 로 중계.

        aiortc 의 이벤트는 ``@pc.on(event_name)`` 데코레이터 또는
        ``pc.on(event_name, handler)`` 호출로 등록한다. 본 래퍼는 후자를
        사용해 이름 충돌 없이 메서드 형태로 결선한다.
        """

        @self._pc.on("connectionstatechange")
        async def _on_state_change() -> None:
            state = self._pc.connectionState
            log.info("[Peer] connectionState=%s", state)
            self.connection_state_changed.emit(state)

        @self._pc.on("icecandidate")
        async def _on_local_ice(event: Any) -> None:
            # event.candidate 는 RTCIceCandidate 객체 또는 None (gathering 완료)
            candidate = getattr(event, "candidate", None)
            if candidate is None:
                log.debug("[Peer] 로컬 ICE gathering 완료 — null 후보 발행")
                self.local_ice_candidate.emit({})
                return
            wire = self._serialize_ice_candidate(candidate)
            log.debug("[Peer] 로컬 ICE 후보 발행 — keys=%s", sorted(wire))
            self.local_ice_candidate.emit(wire)

        @self._pc.on("datachannel")
        def _on_remote_channel(channel: "RTCDataChannel") -> None:
            log.info(
                "[Peer] 원격 DataChannel 수신 — label=%s id=%s",
                channel.label,
                channel.id,
            )
            self._channel = channel
            self._wire_channel_events(channel)

    def _wire_channel_events(self, channel: "RTCDataChannel") -> None:
        """DataChannel 의 message/open/close 이벤트를 Qt signal 로 중계.

        텍스트 / 바이너리 분기는 aiortc 가 자동으로 payload 타입을 ``str``
        또는 ``bytes`` 로 전달한다. 본 래퍼는 그 타입 분기에 따라 적절한
        signal + 핸들러를 호출한다.
        """

        @channel.on("open")
        def _on_open() -> None:
            log.info(
                "[Peer] DataChannel open — label=%s id=%s",
                channel.label,
                channel.id,
            )
            self.data_channel_opened.emit(channel.label)

        @channel.on("close")
        def _on_close() -> None:
            log.info("[Peer] DataChannel close — label=%s", channel.label)
            self.data_channel_closed.emit(channel.label)

        @channel.on("message")
        def _on_message(message: Any) -> None:
            # 동기 핸들러 — 비동기 작업은 ``create_task`` 로 예약
            if isinstance(message, str):
                self.text_message_received.emit(message)
                if self._text_handler is not None:
                    asyncio.ensure_future(self._safe_text_call(message))
            elif isinstance(message, (bytes, bytearray, memoryview)):
                raw = bytes(message)
                self.binary_message_received.emit(raw)
                if self._binary_handler is not None:
                    asyncio.ensure_future(self._safe_binary_call(raw))
            else:
                log.warning(
                    "[Peer] 알 수 없는 DataChannel 메시지 타입 — %r",
                    type(message),
                )

    async def _safe_text_call(self, payload: str) -> None:
        """텍스트 핸들러 호출 — 예외는 로그만 남기고 swallow."""

        try:
            assert self._text_handler is not None
            await self._text_handler(payload)
        except Exception as exc:
            log.exception("[Peer] 텍스트 핸들러 예외 — payload_len=%d", len(payload))
            self.error.emit(f"텍스트 메시지 처리 실패 — {exc!s}")

    async def _safe_binary_call(self, payload: bytes) -> None:
        """바이너리 핸들러 호출 — 예외는 로그만 남기고 swallow."""

        try:
            assert self._binary_handler is not None
            await self._binary_handler(payload)
        except Exception as exc:
            log.exception(
                "[Peer] 바이너리 핸들러 예외 — payload_len=%d", len(payload)
            )
            self.error.emit(f"바이너리 메시지 처리 실패 — {exc!s}")

    # ------------------------------------------------------------------
    # 헬퍼 — ICE candidate 직렬화
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_ice_candidate(candidate: Any) -> dict[str, Any]:
        """aiortc ``RTCIceCandidate`` 객체를 wire dict 로 변환.

        wire 포맷은 시그널링 서버 README §3 의 ``ICE.candidate`` 와 동일:

        ```json
        {"candidate": "...", "sdpMid": "...", "sdpMLineIndex": 0}
        ```

        aiortc 의 RTCIceCandidate 는 SDP 라인을 직접 보관하지 않으므로
        ``aiortc.contrib.signaling.object_to_string`` 헬퍼가 가능한 경우
        이를 활용해 정확한 candidate 문자열을 얻는다.
        """

        # 안전한 기본 dict — getattr 로 누락 필드 폴백
        wire: dict[str, Any] = {
            "candidate": "",
            "sdpMid": getattr(candidate, "sdpMid", None),
            "sdpMLineIndex": getattr(candidate, "sdpMLineIndex", None),
        }

        # ``object_to_string`` 은 JSON 문자열로 후보를 반환 — 파싱 후 candidate
        # 필드만 추출. 사용 불가 시 to_sdp() 같은 메서드 폴백.
        try:
            if object_to_string is not None:
                serialized = object_to_string(candidate)
                obj = json.loads(serialized)
                if isinstance(obj, dict):
                    wire["candidate"] = str(obj.get("candidate") or "")
                    if obj.get("sdpMid") is not None:
                        wire["sdpMid"] = obj["sdpMid"]
                    if obj.get("sdpMLineIndex") is not None:
                        wire["sdpMLineIndex"] = obj["sdpMLineIndex"]
        except Exception:
            log.exception(
                "[Peer] ICE candidate 직렬화 실패 — 빈 candidate 전달"
            )
        return wire
