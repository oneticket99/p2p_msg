# SPDX-License-Identifier: GPL-3.0-or-later
"""SfuCallMixin isolated 단위 테스트 — cycle 169.807 SFU 확장 M4b-2b.

SFU 그룹 통화 배선(SignalingClient SFU 신호 ↔ SfuCallClient ↔ GroupCallDialog)을
SfuCallClient/GroupCallDialog 를 mock 으로 치환해 실 aiortc/Qt 없이 검증한다.
"""

from __future__ import annotations

import asyncio

import pytest

from app.ui._sfu_call_mixin import SfuCallMixin


class _FakeSignal:
    """pyqtSignal 대역 — connect/disconnect/emit 직접 구현."""

    def __init__(self) -> None:
        self._slots: list = []

    def connect(self, slot) -> None:  # noqa: ANN001
        self._slots.append(slot)

    def disconnect(self, slot) -> None:  # noqa: ANN001
        self._slots.remove(slot)

    def emit(self, *args) -> None:
        for slot in list(self._slots):
            slot(*args)


class _FakeSignaling:
    def __init__(self) -> None:
        self.sfu_answer_received = _FakeSignal()
        self.sfu_producers_received = _FakeSignal()
        self.sent: list = []

    async def _send(self, payload: dict) -> None:
        self.sent.append(payload)


class _FakeSfuClient:
    def __init__(self, room_id, peer_id, send, on_remote_track=None) -> None:  # noqa: ANN001
        self.calls: list = []
        self.on_remote_track = on_remote_track

    async def publish(self, video: bool = False) -> None:
        self.calls.append(("publish", video))

    async def handle_sfu_answer(self, kind, sdp, producer_id) -> None:  # noqa: ANN001
        self.calls.append(("answer", kind, sdp, producer_id))

    async def handle_producers(self, producers) -> None:  # noqa: ANN001
        self.calls.append(("producers", producers))

    async def close(self) -> None:
        self.calls.append(("close",))


class _FakeDialog:
    def __init__(self, room_id, parent=None) -> None:  # noqa: ANN001
        self.room_id = room_id
        self.tracks: list = []
        self.shown = False

    def show(self) -> None:
        self.shown = True

    def add_remote_track(self, producer_id, track) -> None:  # noqa: ANN001
        self.tracks.append((producer_id, track))

    def close_all(self) -> None:
        pass

    def close(self) -> None:
        pass


class _FakeState:
    """AppState 대역 — room_id/peer_id 노출."""

    def __init__(self, room_id=None, peer_id=None) -> None:  # noqa: ANN001
        self.room_id = room_id
        self.peer_id = peer_id


class _Host(SfuCallMixin):
    def __init__(self, signaling, state=None) -> None:  # noqa: ANN001
        self._signaling_client = signaling
        self._state = state
        self._init_sfu_call()


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    import app.net.sfu_call_client as scc
    import app.ui.group_call_dialog as gcd

    monkeypatch.setattr(scc, "SfuCallClient", _FakeSfuClient)
    monkeypatch.setattr(gcd, "GroupCallDialog", _FakeDialog)


class TestSfuCallMixin:
    """그룹 통화 배선 검증."""

    @pytest.mark.asyncio
    async def test_start_group_call_wires_and_publishes(self) -> None:
        sig = _FakeSignaling()
        host = _Host(sig)
        host.start_group_call("r1", "alice", video=True)
        await asyncio.sleep(0)  # ensure_future(publish) 진행

        assert host._sfu_call_client is not None
        assert host._group_call_dialog.shown
        assert host._sfu_signals_connected
        assert ("publish", True) in host._sfu_call_client.calls

    @pytest.mark.asyncio
    async def test_on_remote_track_adds_tile(self) -> None:
        sig = _FakeSignaling()
        host = _Host(sig)
        host.start_group_call("r1", "alice")
        host._sfu_call_client.on_remote_track("bob", object())
        assert len(host._group_call_dialog.tracks) == 1
        assert host._group_call_dialog.tracks[0][0] == "bob"

    @pytest.mark.asyncio
    async def test_sfu_signals_route_to_client(self) -> None:
        sig = _FakeSignaling()
        host = _Host(sig)
        host.start_group_call("r1", "alice")
        sig.sfu_answer_received.emit("publish", "v=0", "alice")
        sig.sfu_producers_received.emit("r1", ["alice", "bob"])
        await asyncio.sleep(0)
        calls = host._sfu_call_client.calls
        assert ("answer", "publish", "v=0", "alice") in calls
        assert ("producers", ["alice", "bob"]) in calls

    @pytest.mark.asyncio
    async def test_end_group_call_cleans_up(self) -> None:
        sig = _FakeSignaling()
        host = _Host(sig)
        host.start_group_call("r1", "alice")
        assert host._sfu_signals_connected
        host.end_group_call()
        await asyncio.sleep(0)
        assert host._sfu_call_client is None
        assert host._group_call_dialog is None
        assert not host._sfu_signals_connected

    def test_on_sfu_answer_noop_without_client(self) -> None:
        # 한글 주석 — client 미생성 시 신호 슬롯은 무해(no-op)
        sig = _FakeSignaling()
        host = _Host(sig)
        host._on_sfu_answer("publish", "v=0", "alice")  # 예외 없이 통과
        host._on_sfu_producers("r1", ["alice"])

    @pytest.mark.asyncio
    async def test_on_start_group_call_uses_appstate(self) -> None:
        # 한글 주석 — 방 입장 상태(room/peer 존재)면 start_group_call 호출
        sig = _FakeSignaling()
        host = _Host(sig, state=_FakeState(room_id="r1", peer_id="alice"))
        host._on_start_group_call()
        await asyncio.sleep(0)
        assert host._sfu_call_client is not None
        assert host._group_call_dialog.room_id == "r1"
        host.end_group_call()

    def test_on_start_group_call_noop_without_room(self) -> None:
        # 한글 주석 — 방 미입장(room/peer 부재)이면 no-op
        sig = _FakeSignaling()
        host = _Host(sig, state=_FakeState(room_id=None, peer_id=None))
        host._on_start_group_call()
        assert host._sfu_call_client is None
        assert host._group_call_dialog is None
