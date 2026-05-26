# SPDX-License-Identifier: GPL-3.0-or-later
"""SfuRoom 단위 test — cycle 169.850 codex 평가 §8-3 잔여 회수.

server-side SFU room 의 forward registry(add_publisher/subscribe/remove_peer
/close)를 aiortc ``RTCPeerConnection``·``MediaRelay`` mock 으로 headless 검증한다.
실 aiortc 종단 loopback 은 ``tests/integration/test_sfu_room_loopback.py`` 가
담당(중복 회피) — 본 모듈은 분기·registry 상태·정리 경로 coverage 에 집중한다.
pyproject ``asyncio_mode=auto`` 정합 — async def test 직접 구동.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import server.sfu_room as srmod
from server.sfu_room import SfuRoom


def _make_fake_pc(emit_tracks=None) -> MagicMock:
    """server-side RTCPeerConnection mock — async 메서드 + track 이벤트 발화."""

    emit_tracks = emit_tracks or []
    pc = MagicMock(name="RTCPeerConnection")
    pc.createAnswer = AsyncMock(return_value=MagicMock(sdp="ANSWER_SDP"))
    pc.setLocalDescription = AsyncMock()
    pc.close = AsyncMock()
    pc.addTrack = MagicMock()
    pc.localDescription = MagicMock(sdp="LOCAL_SDP")
    # 한글 주석 — @pc.on("track") 데코레이터가 등록한 핸들러를 capture.
    pc._handlers = {}

    def _register(event):
        def _wrap(fn):
            pc._handlers[event] = fn
            return fn

        return _wrap

    pc.on = MagicMock(side_effect=_register)

    async def _set_remote(_desc):
        # 한글 주석 — aiortc 는 setRemoteDescription(offer) 코루틴 안에서 transceiver
        # 별 track 이벤트를 동기 발화한다. 등록된 핸들러를 emit_tracks 로 재현해
        # add_publisher 반환 시점의 producer.tracks 전수 등재 보장을 검증 가능케 한다.
        handler = pc._handlers.get("track")
        if handler is not None:
            for track in emit_tracks:
                handler(track)

    pc.setRemoteDescription = AsyncMock(side_effect=_set_remote)
    return pc


@pytest.fixture
def aiortc(monkeypatch):
    """모듈 레벨 aiortc 심볼 mock 주입 + pc 생성 큐 제어 핸들 반환."""

    created: list[MagicMock] = []
    # 한글 주석 — 다음 생성 pc 가 발화할 track 목록을 순서대로 공급(FIFO).
    track_queue: list[list] = []

    def _pc_factory(*_a, **_k) -> MagicMock:
        emit = track_queue.pop(0) if track_queue else []
        pc = _make_fake_pc(emit)
        created.append(pc)
        return pc

    relay = MagicMock(name="MediaRelay")
    # 한글 주석 — relay.subscribe(track) → forward sentinel 반환(원본과 구별).
    relay.subscribe = MagicMock(side_effect=lambda track: ("forward", track))

    monkeypatch.setattr(srmod, "AIORTC_AVAILABLE", True)
    monkeypatch.setattr(
        srmod, "RTCPeerConnection", MagicMock(side_effect=_pc_factory)
    )
    monkeypatch.setattr(srmod, "MediaRelay", MagicMock(return_value=relay))
    monkeypatch.setattr(
        srmod,
        "RTCSessionDescription",
        MagicMock(side_effect=lambda sdp, type: MagicMock(sdp=sdp, type=type)),
    )
    return SimpleNamespace(created=created, queue=track_queue, relay=relay)


# ----------------------------------------------------------------------
# __init__ + 기본 registry 상태
# ----------------------------------------------------------------------


def test_init_requires_aiortc(monkeypatch) -> None:
    """aiortc 미설치 환경에서 SfuRoom 생성은 명확한 RuntimeError 로 즉시 실패한다."""

    monkeypatch.setattr(srmod, "AIORTC_AVAILABLE", False)
    with pytest.raises(RuntimeError, match="aiortc 미설치"):
        SfuRoom("r1")


def test_room_id_and_empty_registry(aiortc) -> None:
    """초기 room 은 room_id 노출 + producer/subscriber 공집합(is_empty True)."""

    room = SfuRoom("r1")
    assert room.room_id == "r1"
    assert room.is_empty() is True
    assert room.producer_ids() == []
    assert room.has_producer("p1") is False


# ----------------------------------------------------------------------
# add_publisher
# ----------------------------------------------------------------------


async def test_add_publisher_registers_tracks(aiortc) -> None:
    """upstream offer 수신 → answer SDP 회신 + 발화 track 전수 producer 등재."""

    room = SfuRoom("r1")
    t_audio, t_video = MagicMock(kind="audio"), MagicMock(kind="video")
    aiortc.queue.append([t_audio, t_video])

    sdp = await room.add_publisher("p1", "OFFER_SDP")

    assert sdp == "LOCAL_SDP"
    assert room.has_producer("p1")
    assert room.producer_ids() == ["p1"]
    assert room._producers["p1"].tracks == [t_audio, t_video]
    assert room.is_empty() is False


async def test_add_publisher_replaces_existing(aiortc) -> None:
    """동일 peer 재 publish 시 기존 producer pc 를 close(드롭) 후 교체한다."""

    room = SfuRoom("r1")
    aiortc.queue.append([MagicMock(kind="audio")])
    await room.add_publisher("p1", "OFFER1")
    old_pc = aiortc.created[0]

    aiortc.queue.append([MagicMock(kind="audio")])
    await room.add_publisher("p1", "OFFER2")

    old_pc.close.assert_awaited_once()
    assert room.producer_ids() == ["p1"]


# ----------------------------------------------------------------------
# subscribe
# ----------------------------------------------------------------------


async def test_subscribe_forwards_via_relay(aiortc) -> None:
    """producer 의 각 track 을 relay.subscribe 경유로만 forward addTrack 한다(D-A)."""

    room = SfuRoom("r1")
    t1, t2 = MagicMock(kind="audio"), MagicMock(kind="video")
    aiortc.queue.append([t1, t2])
    await room.add_publisher("pub", "PUB_OFFER")

    aiortc.queue.append([])  # subscriber recvonly — track 발화 없음
    sdp = await room.subscribe("sub", "pub", "SUB_OFFER")

    assert sdp == "LOCAL_SDP"
    sub_pc = aiortc.created[-1]
    # 원본 직접 addTrack 금지 — track 수만큼 relay.subscribe + addTrack 호출
    assert aiortc.relay.subscribe.call_count == 2
    assert sub_pc.addTrack.call_count == 2
    assert ("sub", "pub") in room._subscribers


async def test_subscribe_unknown_producer_raises(aiortc) -> None:
    """대상 producer 부재 시 KeyError(Router 가 ERR_SFU_NO_PRODUCER 로 변환)."""

    room = SfuRoom("r1")
    with pytest.raises(KeyError):
        await room.subscribe("sub", "ghost", "OFFER")


async def test_subscribe_resubscribe_closes_old(aiortc) -> None:
    """동일 (subscriber, producer) 재구독 시 이전 downstream 연결을 close 후 교체."""

    room = SfuRoom("r1")
    aiortc.queue.append([MagicMock(kind="audio")])
    await room.add_publisher("pub", "PUB")

    aiortc.queue.append([])
    await room.subscribe("sub", "pub", "OFFER1")
    old_sub_pc = aiortc.created[-1]

    aiortc.queue.append([])
    await room.subscribe("sub", "pub", "OFFER2")

    old_sub_pc.close.assert_awaited_once()
    assert len(room._subscribers) == 1


# ----------------------------------------------------------------------
# remove_peer / close
# ----------------------------------------------------------------------


async def test_remove_peer_producer_cleans_downstream(aiortc) -> None:
    """producer 이탈 시 그 producer pc + 구독하던 downstream 을 모두 정리한다."""

    room = SfuRoom("r1")
    aiortc.queue.append([MagicMock(kind="audio")])
    await room.add_publisher("pub", "PUB")
    pub_pc = aiortc.created[0]

    aiortc.queue.append([])
    await room.subscribe("sub", "pub", "OFFER")
    sub_pc = aiortc.created[-1]

    await room.remove_peer("pub")

    pub_pc.close.assert_awaited_once()
    sub_pc.close.assert_awaited_once()
    assert room.is_empty()


async def test_remove_peer_subscriber_side(aiortc) -> None:
    """subscriber 이탈 시 그 subscriber 가 연 downstream 만 종료하고 producer 는 유지한다."""

    room = SfuRoom("r1")
    aiortc.queue.append([MagicMock(kind="audio")])
    await room.add_publisher("pub", "PUB")

    aiortc.queue.append([])
    await room.subscribe("sub", "pub", "OFFER")
    sub_pc = aiortc.created[-1]

    await room.remove_peer("sub")

    sub_pc.close.assert_awaited_once()
    assert room.has_producer("pub")
    assert ("sub", "pub") not in room._subscribers


async def test_close_cleans_all_connections(aiortc) -> None:
    """room close 는 모든 producer + subscriber pc 를 close 후 registry 비운다."""

    room = SfuRoom("r1")
    aiortc.queue.append([MagicMock(kind="audio")])
    await room.add_publisher("pub", "PUB")
    pub_pc = aiortc.created[0]

    aiortc.queue.append([])
    await room.subscribe("sub", "pub", "OFFER")
    sub_pc = aiortc.created[-1]

    await room.close()

    pub_pc.close.assert_awaited_once()
    sub_pc.close.assert_awaited_once()
    assert room.is_empty()
    assert room.producer_ids() == []
