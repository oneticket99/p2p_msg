# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.remote.input_dispatch`` 단위 테스트 (cycle 150).

DispatchEvent invariant + 3 OS 분기 backend skeleton + factory 의 platform-specific
분기 + graceful import 의 정합. 실 CGEvent / SendInput / XTest binding 차단.
"""

from __future__ import annotations

from unittest.mock import patch

from app.remote.input_dispatch import (
    DispatchEvent,
    InputDispatchBackend,
    LinuxXTestBackend,
    MacOSCGEventBackend,
    WindowsSendInputBackend,
    build_input_dispatch_backend,
)


class TestDispatchEvent:
    """``DispatchEvent`` frozen dataclass invariant."""

    def test_mouse_move_event(self) -> None:
        """mouse_move = x / y 의무."""
        event = DispatchEvent(event_type="mouse_move", x=100, y=200)
        assert event.event_type == "mouse_move"
        assert event.x == 100
        assert event.y == 200
        assert event.button == 0
        assert event.pressed is False

    def test_key_event(self) -> None:
        """key event = keycode + pressed."""
        event = DispatchEvent(event_type="key", keycode=65, pressed=True)
        assert event.event_type == "key"
        assert event.keycode == 65
        assert event.pressed is True


class TestInputDispatchBackendSkeleton:
    """``InputDispatchBackend`` base 의 skeleton fallback 반환."""

    def test_base_is_available_false(self) -> None:
        """base = skeleton False 반환."""
        assert InputDispatchBackend.is_available() is False

    def test_base_dispatch_returns_none(self) -> None:
        """base dispatch = skeleton None 반환."""
        backend = InputDispatchBackend()
        event = DispatchEvent(event_type="mouse_move", x=10, y=20)
        assert backend.dispatch(event) is None


class TestMacOSCGEventBackendGracefulImport:
    """``MacOSCGEventBackend`` 의 PyObjC + Quartz 부재 시 graceful None."""

    def test_is_available_non_darwin_false(self) -> None:
        """darwin 외 OS = False."""
        with patch(
            "app.remote.input_dispatch.platform.system", return_value="Linux"
        ):
            assert MacOSCGEventBackend.is_available() is False

    def test_dispatch_graceful(self) -> None:
        """dispatch = graceful skeleton None."""
        backend = MacOSCGEventBackend()
        event = DispatchEvent(event_type="mouse_move", x=10, y=20)
        result = backend.dispatch(event)
        assert result is None


class TestWindowsSendInputBackendGracefulImport:
    """``WindowsSendInputBackend`` 의 ctypes + user32 부재 시 graceful None."""

    def test_is_available_non_windows_false(self) -> None:
        """Windows 외 OS = False."""
        with patch(
            "app.remote.input_dispatch.platform.system", return_value="Darwin"
        ):
            assert WindowsSendInputBackend.is_available() is False

    def test_dispatch_graceful(self) -> None:
        """dispatch = graceful skeleton None."""
        backend = WindowsSendInputBackend()
        event = DispatchEvent(event_type="key", keycode=65, pressed=True)
        result = backend.dispatch(event)
        assert result is None


class TestLinuxXTestBackendGracefulImport:
    """``LinuxXTestBackend`` 의 Xlib 부재 시 graceful None."""

    def test_dispatch_graceful(self) -> None:
        """dispatch = graceful skeleton None."""
        backend = LinuxXTestBackend()
        event = DispatchEvent(
            event_type="mouse_button", x=50, y=60, button=1, pressed=True
        )
        result = backend.dispatch(event)
        assert result is None


class TestBuildInputDispatchBackendFactory:
    """``build_input_dispatch_backend`` 의 ``platform.system()`` 분기."""

    def test_factory_returns_backend_instance(self) -> None:
        """현 OS 의 backend instance 반환."""
        backend = build_input_dispatch_backend()
        assert isinstance(backend, InputDispatchBackend)

    def test_factory_darwin_returns_cgevent(self) -> None:
        """Darwin → MacOSCGEventBackend."""
        with patch(
            "app.remote.input_dispatch.platform.system", return_value="Darwin"
        ):
            backend = build_input_dispatch_backend()
            assert isinstance(backend, MacOSCGEventBackend)

    def test_factory_linux_returns_xtest(self) -> None:
        """Linux → LinuxXTestBackend."""
        with patch(
            "app.remote.input_dispatch.platform.system", return_value="Linux"
        ):
            backend = build_input_dispatch_backend()
            assert isinstance(backend, LinuxXTestBackend)
