# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.remote.input_forward`` 단위 테스트.

InputForwardBackend Protocol + MockInputForwardBackend 의 누적 + factory 분기
+ apply_events batch + filter_events_by_type + raise 시점 의 fail-fast.
"""

from __future__ import annotations

import pytest

from app.remote.input_forward import (
    MacOSCGEventBackend,
    MockInputForwardBackend,
    apply_events,
    filter_events_by_type,
    select_input_backend,
)
from app.remote.protocol import InputEventType, RemoteInput


def _mouse_move(x: int = 100, y: int = 200, ts: int = 1_000) -> RemoteInput:
    """test fixture — mouse_move event."""

    return RemoteInput(
        event_type=InputEventType.MOUSE_MOVE,
        payload={"x": x, "y": y},
        timestamp_ms=ts,
    )


def _key_down(keycode: int = 65, ts: int = 1_000) -> RemoteInput:
    """test fixture — key_down event."""

    return RemoteInput(
        event_type=InputEventType.KEY_DOWN,
        payload={"keycode": keycode},
        timestamp_ms=ts,
    )


class TestMockInputForwardBackend:
    """``MockInputForwardBackend`` 의 누적 + reset + raise 검증."""

    def test_is_available_always_true(self) -> None:
        assert MockInputForwardBackend.is_available() is True

    def test_apply_accumulates(self) -> None:
        backend = MockInputForwardBackend()
        e1 = _mouse_move()
        e2 = _key_down()
        backend.apply(e1)
        backend.apply(e2)
        assert backend.applied == [e1, e2]

    def test_reset_clears(self) -> None:
        backend = MockInputForwardBackend()
        backend.apply(_mouse_move())
        backend.reset()
        assert backend.applied == []

    def test_raise_on_apply_raises(self) -> None:
        backend = MockInputForwardBackend(raise_on_apply=True)
        with pytest.raises(RuntimeError, match="intentional failure"):
            backend.apply(_mouse_move())
        # raise 시점 = 누적 0건 (의 의무)
        assert backend.applied == []


class TestMacOSCGEventBackend:
    """``MacOSCGEventBackend`` placeholder 의 graceful degrade 검증."""

    def test_apply_raises_not_implemented(self) -> None:
        backend = MacOSCGEventBackend()
        with pytest.raises(NotImplementedError, match="CGEvent binding"):
            backend.apply(_mouse_move())


class TestSelectInputBackend:
    """``select_input_backend`` factory 분기 검증."""

    def test_mock_explicit(self) -> None:
        cls = select_input_backend("mock")
        assert cls is MockInputForwardBackend

    def test_darwin_returns_cgevent(self) -> None:
        cls = select_input_backend("darwin")
        assert cls is MacOSCGEventBackend

    def test_win32_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="win32 input backend"):
            select_input_backend("win32")

    def test_linux_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="linux input backend"):
            select_input_backend("linux")

    def test_unknown_platform_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown platform_name"):
            select_input_backend("solaris")


class TestApplyEvents:
    """``apply_events`` batch dispatch + fail-fast 검증."""

    def test_empty_events(self) -> None:
        backend = MockInputForwardBackend()
        succeeded = apply_events(backend, [])
        assert succeeded == 0
        assert backend.applied == []

    def test_all_succeed(self) -> None:
        backend = MockInputForwardBackend()
        events = [_mouse_move(ts=1), _key_down(ts=2), _mouse_move(ts=3)]
        succeeded = apply_events(backend, events)
        assert succeeded == 3
        assert len(backend.applied) == 3

    def test_fail_fast_on_raise(self) -> None:
        backend = MockInputForwardBackend(raise_on_apply=True)
        events = [_mouse_move(ts=1), _key_down(ts=2)]
        succeeded = apply_events(backend, events)
        # 1번째 event 의 raise = 0 success + 후속 차단
        assert succeeded == 0
        assert backend.applied == []


class TestFilterEventsByType:
    """``filter_events_by_type`` 검증."""

    def test_filter_mouse_move(self) -> None:
        events = [
            _mouse_move(ts=1),
            _key_down(ts=2),
            _mouse_move(ts=3),
        ]
        filtered = filter_events_by_type(events, InputEventType.MOUSE_MOVE)
        assert len(filtered) == 2
        assert all(e.event_type == InputEventType.MOUSE_MOVE for e in filtered)

    def test_filter_key_down(self) -> None:
        events = [_mouse_move(), _key_down()]
        filtered = filter_events_by_type(events, InputEventType.KEY_DOWN)
        assert len(filtered) == 1

    def test_filter_no_match(self) -> None:
        events = [_mouse_move(), _mouse_move(ts=2)]
        filtered = filter_events_by_type(events, InputEventType.KEY_UP)
        assert filtered == []

    def test_order_preserved(self) -> None:
        events = [
            _mouse_move(x=1, ts=1),
            _mouse_move(x=2, ts=2),
            _mouse_move(x=3, ts=3),
        ]
        filtered = filter_events_by_type(events, InputEventType.MOUSE_MOVE)
        assert [e.payload["x"] for e in filtered] == [1, 2, 3]
