# SPDX-License-Identifier: GPL-3.0-or-later
"""server-side SFU(Selective Forwarding Unit) room 코어 — cycle 169.799 SFU 확장 M3.

9 peer 이상의 그룹 음성·영상은 full-mesh(O(n²) 연결 폭증)를 회피하기 위해
SFU 경로로 승격한다. 각 publisher 는 자신의 미디어를 1개 upstream 으로 SFU 에
publish 하고, SFU 는 aiortc ``MediaRelay`` 로 그 track 을 다른 peer 들에게
selective forward 한다. 클라이언트 upstream 부하는 peer 수와 무관하게 O(1),
서버 fan-out 만 O(n) 이 된다 (Exec Plan §6.1 NFR 정량 목표).

본 모듈은 server-side ``RTCPeerConnection`` 만 다룬다 — 와이어 메시지 라우팅은
``signaling.py`` (Router) 가 담당하고, 본 모듈은 SDP 본문 입출력 + track
forward registry 에 집중한다 (계층 분리, 정본 §E).

SDP 협상 방향 (publish·subscribe 모두 client-offer / server-answer 대칭):
- publish: 클라가 upstream offer → ``add_publisher`` 가 answer 회신 + track 등록.
- subscribe: 클라가 recvonly offer → ``subscribe`` 가 forward track 을 실은 answer 회신.

설계 결정 (Exec Plan §7 결정 로그 정합):
- D-A: ``MediaRelay.subscribe()`` 가 원본 track 을 영구 소비하므로 forward 는
  반드시 relay 경유로 통일한다 (원본 직접 addTrack 금지).
- 단일 layer 평문 forward 만 — simulcast/SVC/MCU/E2E 미디어 암호화는 범위 외.

track 등록 타이밍 보장: aiortc 는 ``setRemoteDescription(offer)`` 코루틴 안에서
transceiver 별 ``track`` 이벤트를 동기 발화한다. 따라서 ``add_publisher`` 가
반환된 시점에는 해당 publisher 의 모든 track 이 ``_Producer.tracks`` 에 등재
완료돼 있다 — Router 가 add_publisher await 종료 후에만 producer 를 노출하면
부분 track forward 경합은 발생하지 않는다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

# aiortc 는 native(av/pylibsrtp) 의존이라 graceful optional import — 미설치 시
# SFU(9+ peer 그룹 통화)만 비활성화하고 코어 시그널링·인증·메시지는 정상 부팅한다.
# requirements.txt 의 httpx·firebase·websockets·Pillow 등 다른 optional 의존성과
# 동일한 폴백 정책 (모듈 로드 단계 hard import 로 전체 서버가 죽는 회귀 차단).
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription
    from aiortc.contrib.media import MediaRelay

    AIORTC_AVAILABLE = True
except ImportError:  # pragma: no cover - aiortc 부재 환경 폴백
    # 한글 주석 — 부재 시 심볼을 None 으로 두고 가용 플래그만 내린다.
    # __future__ annotations 덕에 타입 주석은 문자열로 지연 평가되어 영향 없음.
    RTCPeerConnection = None  # type: ignore[assignment,misc]
    RTCSessionDescription = None  # type: ignore[assignment,misc]
    MediaRelay = None  # type: ignore[assignment,misc]
    AIORTC_AVAILABLE = False

if TYPE_CHECKING:
    from aiortc.mediastreams import MediaStreamTrack

logger = logging.getLogger(__name__)


@dataclass
class _Producer:
    """room 안 publisher 1명의 upstream 상태.

    ``pc`` 는 publisher → SFU 단방향 수신 연결, ``tracks`` 는 그 연결에서
    수신한 원본 미디어 track 목록 (relay subscribe 의 source).
    """

    pc: RTCPeerConnection
    tracks: list["MediaStreamTrack"] = field(default_factory=list)


class SfuRoom:
    """room 단위 SFU forward registry.

    publisher track 을 ``MediaRelay`` 로 받아 subscriber 들에게 forward 한다.
    동일 room 의 모든 peer 가 본 인스턴스 1개를 공유한다.
    """

    def __init__(self, room_id: str) -> None:
        # 한글 주석 — aiortc 부재 시 SFU room 생성 불가. Router 가 사전 차단하는 게
        # 정상 경로지만, 직접 생성 오용을 막기 위한 방어 가드(명확한 메시지로 즉시 실패).
        if not AIORTC_AVAILABLE:
            raise RuntimeError(
                "aiortc 미설치 — SFU 그룹 통화 비활성. "
                "server/requirements.txt 에 aiortc 추가 후 재배포 필요."
            )
        # 한글 주석 — room 식별자 + relay + producer/subscriber registry
        self._room_id = room_id
        self._relay = MediaRelay()
        # producer peer_id → upstream 상태
        self._producers: dict[str, _Producer] = {}
        # (subscriber_id, producer_id) → downstream 연결
        self._subscribers: dict[tuple[str, str], RTCPeerConnection] = {}

    @property
    def room_id(self) -> str:
        return self._room_id

    def producer_ids(self) -> list[str]:
        """현재 publish 중인 producer peer_id 목록 (SFU_PRODUCERS broadcast source)."""
        return list(self._producers.keys())

    def has_producer(self, producer_id: str) -> bool:
        """대상 producer 가 publish 중인지 — Router 의 사전 검증용."""
        return producer_id in self._producers

    async def add_publisher(self, peer_id: str, offer_sdp: str) -> str:
        """publisher 의 upstream offer 를 받아 answer SDP 를 회신한다.

        server-side ``RTCPeerConnection`` 을 생성해 offer 를 setRemoteDescription
        하면 aiortc 가 transceiver 별 ``track`` 이벤트를 동기 발화한다 — 그 시점에
        수신 track 을 producer registry 에 등록하고 answer 를 생성·반환한다.
        반환 직후 ``_Producer.tracks`` 는 전수 등재 완료 상태다.
        """
        pc = RTCPeerConnection()
        producer = _Producer(pc=pc)

        @pc.on("track")
        def _on_track(track: "MediaStreamTrack") -> None:
            # 한글 주석 — 수신한 원본 track 을 producer 목록에 등록 (forward source)
            producer.tracks.append(track)
            logger.info(
                "SFU producer track 등록 room=%s peer=%s kind=%s",
                self._room_id,
                peer_id,
                track.kind,
            )

        await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # 이전 동일 peer 의 producer 가 있으면 그 producer 를 구독하던 downstream 까지
        # 함께 정리한 뒤 교체한다 (좀비 forward 연결 + 리소스 누수 방지).
        if peer_id in self._producers:
            await self._drop_producer(peer_id)
        self._producers[peer_id] = producer
        return pc.localDescription.sdp

    async def subscribe(
        self, subscriber_id: str, producer_id: str, offer_sdp: str
    ) -> str:
        """subscriber 의 recvonly offer 를 받아 forward track 을 실은 answer 를 회신한다.

        producer 의 각 track 을 ``relay.subscribe`` 로 감싸 addTrack 한 뒤 answer 를
        생성한다 (client-offer / server-answer — publish 와 대칭).

        대상 producer 가 없으면 ``KeyError`` 를 던진다 (Router 가
        ``ERR_SFU_NO_PRODUCER`` 로 변환).
        """
        producer = self._producers[producer_id]
        pc = RTCPeerConnection()
        await pc.setRemoteDescription(RTCSessionDescription(sdp=offer_sdp, type="offer"))
        for track in producer.tracks:
            # 한글 주석 — D-A 정합: 원본 직접 addTrack 금지, 반드시 relay 경유 forward
            pc.addTrack(self._relay.subscribe(track))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        # 동일 (subscriber, producer) 재구독 시 이전 연결 정리 후 교체
        key = (subscriber_id, producer_id)
        old = self._subscribers.get(key)
        if old is not None:
            await old.close()
        self._subscribers[key] = pc
        return pc.localDescription.sdp

    async def _drop_producer(self, peer_id: str) -> None:
        """producer 와 그 producer 를 구독하던 downstream 연결을 모두 정리한다."""
        producer = self._producers.pop(peer_id, None)
        if producer is not None:
            await producer.pc.close()
        # 해당 producer 를 구독하던 subscriber 연결 종료 (producer_id == peer_id)
        stale = [key for key in self._subscribers if key[1] == peer_id]
        for key in stale:
            pc = self._subscribers.pop(key)
            await pc.close()

    async def remove_peer(self, peer_id: str) -> None:
        """peer 이탈 시 producer + 관련 subscriber 연결을 모두 정리한다.

        peer 가 producer 였다면 그 producer 의 downstream 까지 정리하고, peer 가
        subscriber 였다면 본인이 연 downstream 연결도 종료한다.
        """
        await self._drop_producer(peer_id)
        # 본인이 subscriber 였던 연결 종료 (subscriber_id == peer_id)
        stale = [key for key in self._subscribers if key[0] == peer_id]
        for key in stale:
            pc = self._subscribers.pop(key)
            await pc.close()

    async def close(self) -> None:
        """room 종료 — 모든 producer + subscriber 연결 정리."""
        for producer in self._producers.values():
            await producer.pc.close()
        for pc in self._subscribers.values():
            await pc.close()
        self._producers.clear()
        self._subscribers.clear()

    def is_empty(self) -> bool:
        """producer + subscriber 가 모두 없으면 True (room GC 판단용)."""
        return not self._producers and not self._subscribers
