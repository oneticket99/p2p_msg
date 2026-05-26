# SPDX-License-Identifier: GPL-3.0-or-later
"""SfuCallClient 단위 test — cycle 169.849 codex 평가 §8-3 coverage omit 축소.

aiortc ``RTCPeerConnection``/``RTCSessionDescription`` 을 mock 으로 대체해 SFU
그룹 통화 클라이언트의 핵심 dispatch 경로(publish/subscribe offer 송신 + dedup +
rollback + SFU_ANSWER 적용 + SFU_PRODUCERS 자동 subscribe + close 정리)를
headless 검증한다 (실 미디어 캡처 + ICE 부재). pyproject ``asyncio_mode=auto``
정합 — async def test 직접 구동.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.net import sfu_call_client as sccmod
from app.net.sfu_call_client import SfuCallClient


def _make_fake_pc() -> MagicMock:
    """aiortc RTCPeerConnection mock — async 메서드 + localDescription stub."""

    pc = MagicMock(name="RTCPeerConnection")
    pc.createOffer = AsyncMock(return_value=MagicMock(sdp="OFFER_SDP"))
    pc.setLocalDescription = AsyncMock()
    pc.setRemoteDescription = AsyncMock()
    pc.close = AsyncMock()
    pc.localDescription = MagicMock(sdp="LOCAL_SDP")
    pc.addTransceiver = MagicMock()
    pc.addTrack = MagicMock()
    # 한글 주석 — @pc.on("track") 데코레이터가 등록한 핸들러를 event 별 capture.
    # 통과 반환(fn) 으로 데코레이터 의미 보존 + 테스트가 핸들러 직접 발화 가능.
    pc._handlers = {}

    def _register(event):
        def _wrap(fn):
            pc._handlers[event] = fn
            return fn

        return _wrap

    pc.on = MagicMock(side_effect=_register)
    return pc


@pytest.fixture
def patched_aiortc(monkeypatch):
    """모듈 레벨 aiortc 심볼 mock 주입 + 생성된 fake pc 목록 반환."""

    fake_pcs: list[MagicMock] = []

    def _factory(*_a, **_k) -> MagicMock:
        pc = _make_fake_pc()
        fake_pcs.append(pc)
        return pc

    monkeypatch.setattr(sccmod, "RTCPeerConnection", MagicMock(side_effect=_factory))
    monkeypatch.setattr(sccmod, "RTCConfiguration", MagicMock())
    monkeypatch.setattr(sccmod, "RTCIceServer", MagicMock())
    monkeypatch.setattr(
        sccmod,
        "RTCSessionDescription",
        MagicMock(side_effect=lambda sdp, type: MagicMock(sdp=sdp, type=type)),
    )
    return fake_pcs


def _make_client(send=None, **kwargs) -> SfuCallClient:
    """room=r1 / peer=me 기본 SfuCallClient — send 는 AsyncMock 기본."""

    return SfuCallClient(
        room_id="r1",
        peer_id="me",
        send=send if send is not None else AsyncMock(),
        **kwargs,
    )


# ----------------------------------------------------------------------
# __init__ + _config
# ----------------------------------------------------------------------


def test_init_stun_env_override(monkeypatch) -> None:
    """TOOTALK_STUN_URL 환경변수가 기본 stun_url 을 덮어쓴다."""

    monkeypatch.setenv("TOOTALK_STUN_URL", "stun:custom.example:3478")
    client = _make_client()
    assert client._stun_url == "stun:custom.example:3478"
    assert client.producer_ids() == []


def test_config_builds_rtc_configuration(patched_aiortc) -> None:
    """_config() 가 stun_url 로 RTCConfiguration 을 만든다 (aiortc mock)."""

    client = _make_client()
    cfg = client._config()
    assert cfg is not None
    sccmod.RTCIceServer.assert_called_once()


# ----------------------------------------------------------------------
# publish
# ----------------------------------------------------------------------


async def test_publish_sends_offer_and_adds_audio_track(patched_aiortc) -> None:
    """publish(audio=True) → 주입 player 의 audio track addTrack + SFU_PUBLISH 송신."""

    send = AsyncMock()
    client = _make_client(send=send)
    player = MagicMock()
    player.audio = MagicMock(name="audio_track")
    player.video = None

    await client.publish(video=False, audio=True, player=player)

    pc = patched_aiortc[0]
    pc.addTrack.assert_called_once_with(player.audio)
    pc.createOffer.assert_awaited_once()
    pc.setLocalDescription.assert_awaited_once()
    sent = send.await_args.args[0]
    assert sent["type"] == "SFU_PUBLISH"
    assert sent["room"] == "r1"
    assert sent["peer_id"] == "me"
    assert sent["sdp"] == "LOCAL_SDP"


async def test_publish_raises_without_aiortc(monkeypatch) -> None:
    """aiortc 미설치(RTCPeerConnection None) 시 publish 가 RuntimeError."""

    monkeypatch.setattr(sccmod, "RTCPeerConnection", None)
    client = _make_client()
    with pytest.raises(RuntimeError):
        await client.publish()


# ----------------------------------------------------------------------
# subscribe — dedup + rollback
# ----------------------------------------------------------------------


async def test_subscribe_sends_offer_and_registers(patched_aiortc) -> None:
    """subscribe(producer) → recvonly transceiver + SFU_SUBSCRIBE 송신 + 등록."""

    send = AsyncMock()
    client = _make_client(send=send)

    await client.subscribe("peer2")

    assert client.producer_ids() == ["peer2"]
    pc = patched_aiortc[0]
    # video + audio recvonly transceiver 2건
    assert pc.addTransceiver.call_count == 2
    sent = send.await_args.args[0]
    assert sent["type"] == "SFU_SUBSCRIBE"
    assert sent["producer_id"] == "peer2"


async def test_subscribe_skips_self(patched_aiortc) -> None:
    """자기 peer_id subscribe 는 no-op (송신·등록 부재)."""

    send = AsyncMock()
    client = _make_client(send=send)

    await client.subscribe("me")

    assert client.producer_ids() == []
    send.assert_not_awaited()
    assert patched_aiortc == []  # pc 생성조차 안 함


async def test_subscribe_skips_duplicate(patched_aiortc) -> None:
    """이미 구독 중인 producer 재subscribe 는 no-op (중복 pc 부재)."""

    send = AsyncMock()
    client = _make_client(send=send)

    await client.subscribe("peer2")
    await client.subscribe("peer2")

    assert client.producer_ids() == ["peer2"]
    assert send.await_count == 1
    assert len(patched_aiortc) == 1


async def test_subscribe_rollback_on_send_failure(patched_aiortc) -> None:
    """send 실패 시 producer 등록 rollback + pc close + 예외 re-raise (좀비 차단)."""

    send = AsyncMock(side_effect=RuntimeError("wire down"))
    client = _make_client(send=send)

    with pytest.raises(RuntimeError, match="wire down"):
        await client.subscribe("peer2")

    # rollback — 등록 제거 + pc.close 호출
    assert client.producer_ids() == []
    patched_aiortc[0].close.assert_awaited_once()


# ----------------------------------------------------------------------
# handle_sfu_answer — publish / subscribe 분기
# ----------------------------------------------------------------------


async def test_handle_answer_publish_sets_remote(patched_aiortc) -> None:
    """kind=publish answer → publish_pc.setRemoteDescription 적용."""

    client = _make_client()
    await client.publish(player=MagicMock(audio=None, video=None))
    publish_pc = patched_aiortc[0]

    await client.handle_sfu_answer("publish", "ANS_SDP", producer_id="")

    publish_pc.setRemoteDescription.assert_awaited_once()


async def test_handle_answer_subscribe_sets_remote(patched_aiortc) -> None:
    """kind=subscribe answer → 해당 producer 의 subscribe pc 에 remote 적용."""

    client = _make_client()
    await client.subscribe("peer2")
    sub_pc = patched_aiortc[0]

    await client.handle_sfu_answer("subscribe", "ANS_SDP", producer_id="peer2")

    sub_pc.setRemoteDescription.assert_awaited_once()


async def test_handle_answer_subscribe_unknown_producer_noop(patched_aiortc) -> None:
    """미등록 producer 의 subscribe answer 는 None 가드로 no-op (예외 부재)."""

    client = _make_client()
    # 등록된 pc 부재 — 예외 없이 통과해야 한다
    await client.handle_sfu_answer("subscribe", "ANS_SDP", producer_id="ghost")


# ----------------------------------------------------------------------
# handle_producers — self 필터 + 자동 subscribe + 콜백
# ----------------------------------------------------------------------


async def test_handle_producers_auto_subscribe_and_callback(patched_aiortc) -> None:
    """SFU_PRODUCERS → self 제외 신규 producer 자동 subscribe + on_producers 콜백."""

    send = AsyncMock()
    seen: list[list[str]] = []
    client = _make_client(send=send, on_producers=lambda ps: seen.append(list(ps)))

    await client.handle_producers(["me", "peer2", "peer3"])

    # 콜백은 원본 목록(self 포함) 전달, subscribe 는 self 제외
    assert seen == [["me", "peer2", "peer3"]]
    assert sorted(client.producer_ids()) == ["peer2", "peer3"]
    assert send.await_count == 2


async def test_remote_track_callback_invoked(patched_aiortc) -> None:
    """subscribe pc 의 on('track') 등록 핸들러 발화 → on_remote_track(producer, track) 통지."""

    received: list[tuple[str, object]] = []
    client = _make_client(on_remote_track=lambda pid, tr: received.append((pid, tr)))

    await client.subscribe("peer2")

    # subscribe 내부에서 @pc.on("track") 로 등록한 _on_track 핸들러를 직접 발화
    pc = patched_aiortc[0]
    track_handler = pc._handlers["track"]
    fake_track = MagicMock(name="forward_track")
    track_handler(fake_track)

    # _on_track 은 producer_id(peer2) default 인자 클로저 → (peer2, track) 통지
    assert received == [("peer2", fake_track)]


async def test_publish_adds_video_track(patched_aiortc) -> None:
    """publish(video=True) → 주입 player 의 video track addTrack 선택."""

    client = _make_client()
    player = MagicMock()
    player.audio = None
    player.video = MagicMock(name="video_track")

    await client.publish(video=True, audio=False, player=player)

    patched_aiortc[0].addTrack.assert_called_once_with(player.video)


# ----------------------------------------------------------------------
# close
# ----------------------------------------------------------------------


async def test_close_cleans_publish_and_subscribes(patched_aiortc) -> None:
    """close() → publish pc + 모든 subscribe pc close + 등록 clear."""

    client = _make_client()
    await client.publish(player=MagicMock(audio=None, video=None))
    await client.subscribe("peer2")
    await client.subscribe("peer3")
    publish_pc, sub2, sub3 = patched_aiortc[0], patched_aiortc[1], patched_aiortc[2]

    await client.close()

    publish_pc.close.assert_awaited_once()
    sub2.close.assert_awaited_once()
    sub3.close.assert_awaited_once()
    assert client.producer_ids() == []
    assert client._publish_pc is None


# ----------------------------------------------------------------------
# _build_media_player — OS별 캡처 spec 선택 + graceful
# ----------------------------------------------------------------------


def test_build_media_player_darwin_video_spec(monkeypatch) -> None:
    """darwin + video → avfoundation 'default:default' spec 선택."""

    fake_mp = MagicMock(name="MediaPlayer")
    monkeypatch.setattr(sccmod, "MediaPlayer", fake_mp)
    monkeypatch.setattr("platform.system", lambda: "Darwin")

    client = _make_client()
    client._build_media_player(video=True)

    fake_mp.assert_called_once_with("default:default", format="avfoundation")


def test_build_media_player_linux_audio_spec(monkeypatch) -> None:
    """linux + audio-only → pulse 'default' spec 선택."""

    fake_mp = MagicMock(name="MediaPlayer")
    monkeypatch.setattr(sccmod, "MediaPlayer", fake_mp)
    monkeypatch.setattr("platform.system", lambda: "Linux")

    client = _make_client()
    client._build_media_player(video=False)

    fake_mp.assert_called_once_with("default", format="pulse")


def test_build_media_player_exception_returns_none(monkeypatch) -> None:
    """MediaPlayer 신설 예외 시 None graceful 반환."""

    monkeypatch.setattr(
        sccmod, "MediaPlayer", MagicMock(side_effect=OSError("no capture device"))
    )
    monkeypatch.setattr("platform.system", lambda: "Linux")

    client = _make_client()
    assert client._build_media_player(video=True) is None
