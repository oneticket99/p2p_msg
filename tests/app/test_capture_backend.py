# SPDX-License-Identifier: GPL-3.0-or-later
"""capture CapturedFrame + MockCaptureBackend unit test — cycle 169.691 신설."""

from __future__ import annotations

import pytest

from app.remote.capture import (
    CaptureFormat, CapturedFrame, MockCaptureBackend, captured_to_remote_frame,
)


class TestCapturedFrameValidation:
    def test_zero_width_raises(self) -> None:
        with pytest.raises(ValueError, match="width"):
            CapturedFrame(width=0, height=10, format=CaptureFormat.BGRA,
                          buffer=b"", capture_time_ms=0)

    def test_zero_height_raises(self) -> None:
        with pytest.raises(ValueError, match="height"):
            CapturedFrame(width=10, height=0, format=CaptureFormat.BGRA,
                          buffer=b"", capture_time_ms=0)

    def test_negative_time_raises(self) -> None:
        with pytest.raises(ValueError, match="capture_time_ms"):
            CapturedFrame(width=2, height=2, format=CaptureFormat.BGRA,
                          buffer=b"\x00" * 16, capture_time_ms=-1)

    def test_buffer_size_mismatch_raises(self) -> None:
        # 한글 주석 — 2x2 BGRA = 16 byte expected
        with pytest.raises(ValueError, match="buffer"):
            CapturedFrame(width=2, height=2, format=CaptureFormat.BGRA,
                          buffer=b"\x00" * 10, capture_time_ms=1)

    def test_bgra_4_bytes_per_pixel(self) -> None:
        f = CapturedFrame(width=2, height=2, format=CaptureFormat.BGRA,
                          buffer=b"\x00" * 16, capture_time_ms=1)
        assert len(f.buffer) == 16
        assert f.format == CaptureFormat.BGRA

    def test_rgb_3_bytes_per_pixel(self) -> None:
        # 한글 주석 — 2x2 RGB = 12 byte
        f = CapturedFrame(width=2, height=2, format=CaptureFormat.RGB,
                          buffer=b"\x00" * 12, capture_time_ms=1)
        assert len(f.buffer) == 12


class TestMockCaptureBackend:
    def test_returns_valid_frame(self) -> None:
        b = MockCaptureBackend(width=4, height=4)
        f = b.capture()
        assert f.width == 4
        assert f.height == 4
        # 4x4 BGRA = 64
        assert len(f.buffer) == 64
        assert f.capture_time_ms > 0

    def test_is_available_true(self) -> None:
        # 한글 주석 — mock backend = 항상 available
        assert MockCaptureBackend.is_available() is True


class TestCapturedToRemoteFrame:
    def test_envelope_conversion(self) -> None:
        # 한글 주석 — BGRA 4byte → RAW_RGB 3byte 변환 의무 (payload size 비교)
        b = MockCaptureBackend(width=2, height=2)
        captured = b.capture()
        remote = captured_to_remote_frame(captured, frame_id=42)
        assert remote.frame_id == 42
        assert remote.width == 2
        assert remote.height == 2
        # payload bytes 길이 = width × height × 3 (RAW_RGB)
        assert len(remote.payload) == 2 * 2 * 3

    def test_envelope_negative_frame_id_raises(self) -> None:
        b = MockCaptureBackend(width=2, height=2)
        captured = b.capture()
        with pytest.raises(ValueError):
            captured_to_remote_frame(captured, frame_id=-1)
