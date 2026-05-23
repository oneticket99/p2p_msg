# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.remote.capture`` 단위 테스트.

CapturedFrame 의 invariant + MockCaptureBackend 의 deterministic 출력 +
factory 의 platform-specific 분기 + BGRA → RGB 변환 + RemoteFrame 정합.
"""

from __future__ import annotations

import pytest

from app.remote.capture import (
    CaptureFormat,
    CapturedFrame,
    LinuxX11Backend,
    MacOSQuartzBackend,
    MockCaptureBackend,
    WindowsGDIBackend,
    captured_to_remote_frame,
    detect_default_backend,
    select_capture_backend,
)
from app.remote.protocol import FrameFormat, RemoteFrame


class TestCapturedFrameValidation:
    """``CapturedFrame`` dataclass invariant 검증."""

    def test_valid_bgra(self) -> None:
        frame = CapturedFrame(
            width=2,
            height=2,
            format=CaptureFormat.BGRA,
            buffer=b"\x00" * (2 * 2 * 4),
            capture_time_ms=100,
        )
        assert frame.width == 2

    def test_valid_rgb(self) -> None:
        frame = CapturedFrame(
            width=3,
            height=1,
            format=CaptureFormat.RGB,
            buffer=b"\xff\x00\x00" * 3,
            capture_time_ms=100,
        )
        assert len(frame.buffer) == 9

    def test_zero_width_rejected(self) -> None:
        with pytest.raises(ValueError, match="width 양수 의무"):
            CapturedFrame(
                width=0,
                height=2,
                format=CaptureFormat.BGRA,
                buffer=b"",
                capture_time_ms=0,
            )

    def test_zero_height_rejected(self) -> None:
        with pytest.raises(ValueError, match="height 양수 의무"):
            CapturedFrame(
                width=2,
                height=0,
                format=CaptureFormat.BGRA,
                buffer=b"",
                capture_time_ms=0,
            )

    def test_negative_capture_time_rejected(self) -> None:
        with pytest.raises(ValueError, match="capture_time_ms 음수 불가"):
            CapturedFrame(
                width=1,
                height=1,
                format=CaptureFormat.BGRA,
                buffer=b"\x00" * 4,
                capture_time_ms=-1,
            )

    def test_buffer_size_mismatch_bgra(self) -> None:
        # 2x2 BGRA = 16 byte 의무 — 12 byte 제공 시 차단
        with pytest.raises(ValueError, match="buffer 크기 불일치"):
            CapturedFrame(
                width=2,
                height=2,
                format=CaptureFormat.BGRA,
                buffer=b"\x00" * 12,
                capture_time_ms=0,
            )

    def test_buffer_size_mismatch_rgb(self) -> None:
        # 2x2 RGB = 12 byte 의무 — 9 byte 제공 시 차단
        with pytest.raises(ValueError, match="buffer 크기 불일치"):
            CapturedFrame(
                width=2,
                height=2,
                format=CaptureFormat.RGB,
                buffer=b"\x00" * 9,
                capture_time_ms=0,
            )


class TestMockCaptureBackend:
    """``MockCaptureBackend`` deterministic 출력 검증."""

    def test_is_available_always_true(self) -> None:
        assert MockCaptureBackend.is_available() is True

    def test_default_1x1_capture(self) -> None:
        backend = MockCaptureBackend()
        frame = backend.capture()
        assert frame.width == 1
        assert frame.height == 1
        assert frame.format == CaptureFormat.BGRA
        assert frame.buffer == b"\x80\x80\x80\xff"

    def test_custom_dimensions(self) -> None:
        backend = MockCaptureBackend(width=4, height=2)
        frame = backend.capture()
        assert frame.width == 4
        assert frame.height == 2
        # 4×2×4 = 32 byte
        assert len(frame.buffer) == 32

    def test_zero_dimension_rejected(self) -> None:
        with pytest.raises(ValueError, match="width / height 양수 의무"):
            MockCaptureBackend(width=0, height=1)


class TestMacOSQuartzBackend:
    """``MacOSQuartzBackend`` placeholder 의 graceful degrade 검증."""

    def test_capture_raises_not_implemented(self) -> None:
        backend = MacOSQuartzBackend()
        with pytest.raises(NotImplementedError, match="PyObjC \\+ Quartz binding"):
            backend.capture()


class TestSelectBackend:
    """``select_capture_backend`` factory 분기 검증."""

    def test_mock_explicit(self) -> None:
        cls = select_capture_backend("mock")
        assert cls is MockCaptureBackend

    def test_darwin_returns_quartz(self) -> None:
        cls = select_capture_backend("darwin")
        assert cls is MacOSQuartzBackend

    def test_win32_returns_gdi_backend(self) -> None:
        # cycle 169.421 actual binding swap — WindowsGDIBackend class return
        cls = select_capture_backend("win32")
        assert cls is WindowsGDIBackend

    def test_linux_returns_x11_backend(self) -> None:
        # cycle 169.421 actual binding swap — LinuxX11Backend class return
        cls = select_capture_backend("linux")
        assert cls is LinuxX11Backend

    def test_unknown_platform_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown platform_name"):
            select_capture_backend("solaris")


class TestDetectDefaultBackend:
    """``detect_default_backend`` skeleton 폴백 검증."""

    def test_returns_class(self) -> None:
        cls = detect_default_backend()
        assert cls in (MacOSQuartzBackend, MockCaptureBackend)


class TestCapturedToRemoteFrame:
    """``captured_to_remote_frame`` 변환 검증."""

    def test_rgb_pass_through(self) -> None:
        captured = CapturedFrame(
            width=2,
            height=1,
            format=CaptureFormat.RGB,
            buffer=b"\xff\x00\x00\x00\xff\x00",
            capture_time_ms=100,
        )
        frame = captured_to_remote_frame(captured, frame_id=0)
        assert isinstance(frame, RemoteFrame)
        assert frame.format == FrameFormat.RAW_RGB
        assert frame.payload == b"\xff\x00\x00\x00\xff\x00"
        assert frame.frame_id == 0
        assert frame.timestamp_ms == 100

    def test_bgra_to_rgb_swap(self) -> None:
        # BGRA = B=10, G=20, R=30, A=255 → RGB = 30, 20, 10
        captured = CapturedFrame(
            width=1,
            height=1,
            format=CaptureFormat.BGRA,
            buffer=b"\x0a\x14\x1e\xff",
            capture_time_ms=200,
        )
        frame = captured_to_remote_frame(captured, frame_id=5)
        assert frame.payload == b"\x1e\x14\x0a"
        assert frame.frame_id == 5

    def test_bgra_multi_pixel(self) -> None:
        # 2 pixel BGRA = 8 byte → RGB 6 byte (alpha drop + swap)
        captured = CapturedFrame(
            width=2,
            height=1,
            format=CaptureFormat.BGRA,
            buffer=b"\x01\x02\x03\xff\x04\x05\x06\xff",
            capture_time_ms=300,
        )
        frame = captured_to_remote_frame(captured, frame_id=1)
        assert frame.payload == b"\x03\x02\x01\x06\x05\x04"
        assert frame.width == 2
        assert frame.height == 1

    def test_frame_id_propagates(self) -> None:
        captured = CapturedFrame(
            width=1,
            height=1,
            format=CaptureFormat.RGB,
            buffer=b"\xff\xff\xff",
            capture_time_ms=400,
        )
        frame = captured_to_remote_frame(captured, frame_id=42)
        assert frame.frame_id == 42
