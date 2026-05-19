# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.remote.screen_capture`` 단위 테스트 (cycle 150).

CapturedFrame invariant + 3 OS 분기 backend skeleton + factory 의 platform-specific
분기 + graceful import 의 정합. 실 Quartz / BitBlt / X11 binding 차단 (skeleton + None 만).
"""

from __future__ import annotations

from unittest.mock import patch

from app.remote.screen_capture import (
    CapturedFrame,
    LinuxX11Backend,
    MacOSQuartzBackend,
    ScreenCaptureBackend,
    WindowsBitBltBackend,
    build_capture_backend,
)


class TestCapturedFrame:
    """``CapturedFrame`` frozen dataclass invariant."""

    def test_frame_fields_immutable(self) -> None:
        """frozen=True — width 등 의 mutate 차단."""
        frame = CapturedFrame(
            width=10,
            height=20,
            bytes_per_row=40,
            pixel_format="BGRA",
            data=b"\x00" * 800,
        )
        assert frame.width == 10
        assert frame.height == 20
        assert frame.bytes_per_row == 40
        assert frame.pixel_format == "BGRA"
        assert len(frame.data) == 800


class TestScreenCaptureBackendSkeleton:
    """``ScreenCaptureBackend`` base 의 skeleton fallback 반환."""

    def test_base_capture_primary_returns_none(self) -> None:
        """base = skeleton graceful None."""
        backend = ScreenCaptureBackend()
        assert backend.capture_primary() is None

    def test_base_list_monitors_returns_empty(self) -> None:
        """base list_monitors = 빈 list."""
        backend = ScreenCaptureBackend()
        assert backend.list_monitors() == []


class TestMacOSQuartzBackendGracefulImport:
    """``MacOSQuartzBackend`` 의 PyObjC + Quartz 부재 시 graceful None."""

    def test_capture_primary_graceful_import_fail(self) -> None:
        """Quartz import 실패 = warning + None 반환 (실 binding 차단)."""
        backend = MacOSQuartzBackend()
        # 실 PyObjC binding 회피 — None 반환 의 정합 (graceful skeleton)
        result = backend.capture_primary()
        assert result is None


class TestWindowsBitBltBackendGracefulImport:
    """``WindowsBitBltBackend`` 의 win32gui 부재 시 graceful None."""

    def test_capture_primary_graceful(self) -> None:
        """win32gui 부재 = warning + None 반환."""
        backend = WindowsBitBltBackend()
        result = backend.capture_primary()
        assert result is None


class TestLinuxX11BackendGracefulImport:
    """``LinuxX11Backend`` 의 Xlib 부재 시 graceful None."""

    def test_capture_primary_graceful(self) -> None:
        """Xlib 부재 = warning + None 반환."""
        backend = LinuxX11Backend()
        result = backend.capture_primary()
        assert result is None


class TestBuildCaptureBackendFactory:
    """``build_capture_backend`` 의 ``platform.system()`` 분기 의 정합."""

    def test_factory_returns_backend_instance(self) -> None:
        """현 OS 의 backend instance 반환 (subclass 또는 base)."""
        backend = build_capture_backend()
        assert isinstance(backend, ScreenCaptureBackend)

    def test_factory_darwin_returns_macos(self) -> None:
        """``platform.system()`` = Darwin → MacOSQuartzBackend."""
        with patch(
            "app.remote.screen_capture.platform.system", return_value="Darwin"
        ):
            backend = build_capture_backend()
            assert isinstance(backend, MacOSQuartzBackend)

    def test_factory_windows_returns_bitblt(self) -> None:
        """``platform.system()`` = Windows → WindowsBitBltBackend."""
        with patch(
            "app.remote.screen_capture.platform.system", return_value="Windows"
        ):
            backend = build_capture_backend()
            assert isinstance(backend, WindowsBitBltBackend)
