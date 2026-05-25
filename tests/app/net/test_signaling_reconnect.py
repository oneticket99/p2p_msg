# SPDX-License-Identifier: GPL-3.0-or-later
"""SignalingClient 자동 재연결(backoff + reJOIN) 통합 test — cycle 169.775 신설.

Codex 전면평가 P0 회수 — `connect()` 단발 연결만 있고 backoff 재연결 + reJOIN
복구 흐름이 부재하던 결함을 구현한 뒤 본 test 로 FSM 동작을 검증한다.

검증 범위:
- 비정상 drop(수신 루프 종료) 시 재연결 예약 (disconnect 미호출)
- 지수 backoff 재시도 후 성공 + 마지막 JOIN 식별자로 reJOIN 복구
- max_attempts 초과 시 ERROR 전이
- 명시적 disconnect() 가 진행 중 재연결을 취소 + 의지 off
- connect() 성공이 자동 재연결 의지를 활성

실 네트워크 없이 `_connect_once` / `ws_connect` / `asyncio.sleep` 를 mock 으로
대체하여 FSM 만 격리 검증한다 (chaos 도구의 서버 접속 벤치와 별개).
"""

from __future__ import annotations

import asyncio

import pytest

from app.core.config import load_config
from app.net.signaling_client import SignalingClient


@pytest.fixture
def client() -> SignalingClient:
    """qapp 불요 — SignalingClient 는 QObject(위젯 아님)."""

    cfg = load_config()
    c = SignalingClient(config=cfg)
    # backoff 를 test 용으로 즉시화 (실제 sleep 은 monkeypatch 로 무력화)
    c._reconnect_base_delay = 0.0
    c._reconnect_max_delay = 0.0
    return c


class _FakeWS:
    """aiohttp WebSocket 대역 — async-iterable + send_str/close/exception."""

    def __init__(self, frames=None) -> None:
        # 한글 주석 — frames 소진 후 StopAsyncIteration → 수신 루프 정상 종료(=drop) 모사
        self._frames = list(frames or [])
        self.closed = False
        self.sent: list[str] = []

    def __aiter__(self):
        self._it = iter(self._frames)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration

    async def send_str(self, raw: str) -> None:
        self.sent.append(raw)

    async def close(self) -> None:
        self.closed = True

    def exception(self):  # noqa: D401 — aiohttp API 시그니처 모사
        return None


async def _noop_sleep(_delay: float) -> None:
    """asyncio.sleep 무력화 — backoff 대기 즉시 통과."""

    return None


class TestRecvLoopDropSchedulesReconnect:
    """비정상 drop 감지 → 재연결 예약."""

    async def test_drop_schedules_reconnect_when_should(self, client, monkeypatch) -> None:
        client._should_reconnect = True
        client._ws = _FakeWS(frames=[])  # 즉시 종료 = drop
        scheduled: list[bool] = []
        monkeypatch.setattr(client, "_schedule_reconnect", lambda: scheduled.append(True))
        await client._recv_loop()
        assert scheduled == [True]
        assert client._ws is None

    async def test_drop_no_reconnect_when_explicit(self, client, monkeypatch) -> None:
        # disconnect 경로(_should_reconnect False) 면 재연결 예약하지 않는다
        client._should_reconnect = False
        client._ws = _FakeWS(frames=[])
        scheduled: list[bool] = []
        monkeypatch.setattr(client, "_schedule_reconnect", lambda: scheduled.append(True))
        await client._recv_loop()
        assert scheduled == []
        assert client._state.connection_state == "DISCONNECTED"


class TestReconnectLoopBackoffRejoin:
    """backoff 재시도 후 성공 + reJOIN 복구."""

    async def test_backoff_then_success_rejoin(self, client, monkeypatch) -> None:
        monkeypatch.setattr("app.net.signaling_client.asyncio.sleep", _noop_sleep)
        client._should_reconnect = True
        client._last_room_id = "room-1"
        client._last_peer_id = "peer-A"

        attempts = {"n": 0}

        async def fake_connect_once() -> None:
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise ConnectionError("일시 실패")
            client._set_state("CONNECTED")

        joined: list[tuple[str, str]] = []

        async def fake_join(room_id: str, peer_id: str) -> None:
            joined.append((room_id, peer_id))

        monkeypatch.setattr(client, "_connect_once", fake_connect_once)
        monkeypatch.setattr(client, "join", fake_join)

        await client._reconnect_loop()

        assert attempts["n"] == 3  # 2회 실패 후 3회차 성공
        assert joined == [("room-1", "peer-A")]  # 마지막 식별자로 reJOIN
        assert client._state.connection_state == "CONNECTED"

    async def test_success_without_prior_join_skips_rejoin(self, client, monkeypatch) -> None:
        monkeypatch.setattr("app.net.signaling_client.asyncio.sleep", _noop_sleep)
        client._should_reconnect = True
        client._last_room_id = None
        client._last_peer_id = None

        async def fake_connect_once() -> None:
            client._set_state("CONNECTED")

        joined: list[tuple[str, str]] = []
        monkeypatch.setattr(client, "_connect_once", fake_connect_once)
        monkeypatch.setattr(client, "join", lambda r, p: joined.append((r, p)))

        await client._reconnect_loop()
        assert joined == []  # JOIN 이력 없으면 reJOIN 생략


class TestReconnectMaxAttempts:
    """max_attempts 초과 → ERROR."""

    async def test_max_attempts_transitions_error(self, client, monkeypatch) -> None:
        monkeypatch.setattr("app.net.signaling_client.asyncio.sleep", _noop_sleep)
        client._should_reconnect = True
        client._reconnect_max_attempts = 3

        async def always_fail() -> None:
            raise ConnectionError("영구 실패")

        monkeypatch.setattr(client, "_connect_once", always_fail)
        await client._reconnect_loop()
        assert client._state.connection_state == "ERROR"


class TestDisconnectCancelsReconnect:
    """명시적 disconnect 가 진행 중 재연결을 취소 + 의지 off."""

    async def test_disconnect_stops_reconnect(self, client) -> None:
        client._should_reconnect = True

        async def _long_reconnect() -> None:
            await asyncio.sleep(100)

        client._reconnect_task = asyncio.create_task(_long_reconnect())
        await asyncio.sleep(0)  # task 기동 보장

        await client.disconnect()

        assert client._should_reconnect is False
        assert client._reconnect_task is None
        assert client._state.connection_state == "DISCONNECTED"
        assert client._last_room_id is None
        assert client._last_peer_id is None


class TestConnectEnablesReconnect:
    """connect() 성공이 자동 재연결 의지를 활성화."""

    async def test_connect_sets_should_reconnect(self, client, monkeypatch) -> None:
        async def fake_connect_once() -> None:
            client._ws = _FakeWS(frames=[])
            client._set_state("CONNECTED")
            # 수신 루프는 본 test 에서 예약하지 않는다 (FSM 의지만 검증)

        monkeypatch.setattr(client, "_connect_once", fake_connect_once)
        await client.connect()
        assert client._should_reconnect is True
        assert client._state.connection_state == "CONNECTED"

    async def test_connect_failure_sets_error_and_raises(self, client, monkeypatch) -> None:
        async def fake_connect_once() -> None:
            raise ConnectionError("최초 연결 실패")

        monkeypatch.setattr(client, "_connect_once", fake_connect_once)
        with pytest.raises(ConnectionError):
            await client.connect()
        assert client._state.connection_state == "ERROR"


class TestScheduleReconnectIdempotent:
    """_schedule_reconnect 멱등 — 이미 진행 중이면 새 task 생성 안 함."""

    async def test_idempotent_schedule(self, client, monkeypatch) -> None:
        monkeypatch.setattr("app.net.signaling_client.asyncio.sleep", _noop_sleep)
        client._should_reconnect = True

        started = {"n": 0}

        async def slow_connect_once() -> None:
            started["n"] += 1
            await asyncio.sleep(0)
            client._set_state("CONNECTED")

        monkeypatch.setattr(client, "_connect_once", slow_connect_once)
        client._schedule_reconnect()
        first = client._reconnect_task
        client._schedule_reconnect()  # 두번째 호출 — 같은 task 유지
        assert client._reconnect_task is first
        await first  # 정리
