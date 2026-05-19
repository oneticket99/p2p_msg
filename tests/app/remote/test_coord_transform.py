# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.remote.coord_transform`` 단위 테스트 — cycle 148.

RemoteScreenInfo + transform_coordinates + AspectRatioPolicy 3 종 + DPI / Retina 보정
+ build_local_screen_info graceful 의 12 케이스.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.remote.coord_transform import (
    AspectRatioPolicy,
    RemoteScreenInfo,
    build_local_screen_info,
    transform_coordinates,
)


# 한글 주석 — 일반 FHD 화면 fixture (16:9 1920x1080 + 96 DPI + 1.0 backing scale).
def _fhd() -> RemoteScreenInfo:
    return RemoteScreenInfo(
        width=1920,
        height=1080,
        logical_width=1920,
        logical_height=1080,
        dpi=96,
        backing_scale=1.0,
    )


# 한글 주석 — QHD 화면 fixture (16:9 2560x1440).
def _qhd() -> RemoteScreenInfo:
    return RemoteScreenInfo(
        width=2560,
        height=1440,
        logical_width=2560,
        logical_height=1440,
        dpi=96,
        backing_scale=1.0,
    )


class TestSameResolution:
    """sender = target 동일 해상도 → 1:1 mapping."""

    def test_identity_mapping(self) -> None:
        sender = _fhd()
        target = _fhd()
        x, y = transform_coordinates(sender, target, 960, 540)
        assert x == 960
        assert y == 540

    def test_corner_origin(self) -> None:
        sender = _fhd()
        target = _fhd()
        x, y = transform_coordinates(sender, target, 0, 0)
        assert (x, y) == (0, 0)

    def test_corner_max(self) -> None:
        sender = _fhd()
        target = _fhd()
        x, y = transform_coordinates(sender, target, 1919, 1079)
        assert (x, y) == (1919, 1079)


class TestFHDtoQHD:
    """1920x1080 → 2560x1440 → 1.333x scaling (aspect 동일)."""

    def test_center_scaling(self) -> None:
        sender = _fhd()
        target = _qhd()
        x, y = transform_coordinates(sender, target, 960, 540)
        # 960 * 2560 / 1920 = 1280, 540 * 1440 / 1080 = 720
        assert x == 1280
        assert y == 720


class TestQHDtoFHD:
    """2560x1440 → 1920x1080 → 0.75x scaling."""

    def test_center_scaling(self) -> None:
        sender = _qhd()
        target = _fhd()
        x, y = transform_coordinates(sender, target, 1280, 720)
        # 1280 * 1920 / 2560 = 960, 720 * 1080 / 1440 = 540
        assert x == 960
        assert y == 540


class TestRetinaBackingScale:
    """macOS Retina backing_scale 2.0 → logical pixel 정합. width = logical_width * 2 가정."""

    def test_retina_physical_pixel(self) -> None:
        # 한글 주석 — Retina MBP 13" 2560x1600 logical 1280x800 (backing 2.0).
        sender = RemoteScreenInfo(
            width=2560,
            height=1600,
            logical_width=1280,
            logical_height=800,
            dpi=96,
            backing_scale=2.0,
        )
        target = _fhd()
        x, y = transform_coordinates(sender, target, 1280, 800)
        # 1280 * 1920 / 2560 = 960, 800 * 1080 / 1600 = 540
        assert x == 960
        assert y == 540


class TestWindowsDPI125:
    """Windows DPI 120 (125% scaling) → 1.25x 보정."""

    def test_dpi_scaling(self) -> None:
        sender = _fhd()
        # 한글 주석 — target = aspect 동일 FHD 의 DPI 120. dpi_scale 1.25 적용 후 width-1 cap.
        target = RemoteScreenInfo(
            width=1920,
            height=1080,
            logical_width=1536,
            logical_height=864,
            dpi=120,
            backing_scale=1.0,
        )
        x, y = transform_coordinates(sender, target, 960, 540)
        # base scaling = 1:1 → 960, 540. dpi scaling 1.25 → 1200, 675. width-1 cap 1919.
        assert x == 1200
        assert y == 675


class TestLetterboxWiderSender:
    """16:9 sender (1920x1080) → 4:3 target (1024x768) → 상하 검은 띠."""

    def test_letterbox_top_bottom_bars(self) -> None:
        sender = _fhd()
        target = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        x, y = transform_coordinates(
            sender, target, 960, 540, policy=AspectRatioPolicy.LETTERBOX
        )
        # scale = 1024 / 1920 ≈ 0.5333, scaled_height = 1080 * 0.5333 ≈ 576
        # offset_y = (768 - 576) // 2 = 96
        # target_x = int(960 * 1024 / 1920) = 512, target_y ≈ 96 + 287 = 383
        assert 510 <= x <= 514
        assert 380 <= y <= 388


class TestLetterboxTallerSender:
    """4:3 sender (1024x768) → 16:9 target (1920x1080) → 좌우 검은 띠."""

    def test_letterbox_left_right_bars(self) -> None:
        sender = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        target = _fhd()
        x, y = transform_coordinates(
            sender, target, 512, 384, policy=AspectRatioPolicy.LETTERBOX
        )
        # scale = 1080 / 768 ≈ 1.40625, scaled_width = 1024 * 1.40625 = 1440
        # offset_x = (1920 - 1440) // 2 = 240
        # target_x = 240 + 512 * 1.40625 = 240 + 720 = 960, target_y = 384 * 1.40625 = 540
        assert x == 960
        assert y == 540


class TestStretchPolicy:
    """aspect mismatch + stretch → 직접 비례 (왜곡 허용)."""

    def test_stretch_distortion(self) -> None:
        sender = _fhd()
        target = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        x, y = transform_coordinates(
            sender, target, 960, 540, policy=AspectRatioPolicy.STRETCH
        )
        # 960 * 1024 / 1920 = 512, 540 * 768 / 1080 = 384
        assert x == 512
        assert y == 384


class TestCropPolicyInsideArea:
    """crop 안 정상 변환 — sender wider 시 좌우 crop."""

    def test_crop_inside_center(self) -> None:
        sender = _fhd()
        target = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        # 한글 주석 — sender 16:9 > target 4:3 → 좌우 crop. scale = 768 / 1080 ≈ 0.711.
        # crop_width = 1024 / 0.711 ≈ 1440, offset_x = (1920 - 1440) // 2 = 240.
        # sender_x = 960 (중앙) → (960 - 240) * 0.711 = 720 * 0.711 ≈ 512.
        x, y = transform_coordinates(
            sender, target, 960, 540, policy=AspectRatioPolicy.CROP
        )
        assert 510 <= x <= 514
        assert 382 <= y <= 386


class TestCropPolicyOutsideArea:
    """crop 영역 외 좌표 → (-1, -1) dispatch skip 신호."""

    def test_crop_outside_left(self) -> None:
        sender = _fhd()
        target = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        # 한글 주석 — sender_x = 10 → crop 영역 (240~1680) 외 → (-1, -1).
        x, y = transform_coordinates(
            sender, target, 10, 540, policy=AspectRatioPolicy.CROP
        )
        assert (x, y) == (-1, -1)

    def test_crop_outside_right(self) -> None:
        sender = _fhd()
        target = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        x, y = transform_coordinates(
            sender, target, 1900, 540, policy=AspectRatioPolicy.CROP
        )
        assert (x, y) == (-1, -1)

    def test_crop_outside_taller_top(self) -> None:
        # 한글 주석 — 4:3 sender → 16:9 target 의 crop = 상하 crop.
        sender = RemoteScreenInfo(
            width=1024,
            height=768,
            logical_width=1024,
            logical_height=768,
            dpi=96,
            backing_scale=1.0,
        )
        target = _fhd()
        x, y = transform_coordinates(
            sender, target, 512, 5, policy=AspectRatioPolicy.CROP
        )
        # scale = 1920 / 1024 = 1.875, crop_height = 1080 / 1.875 = 576.
        # offset_y = (768 - 576) // 2 = 96. sender_y = 5 < 96 → (-1, -1).
        assert (x, y) == (-1, -1)


class TestZeroSenderSize:
    """sender width / height 0 → (0, 0) 안전 반환."""

    def test_zero_width(self) -> None:
        sender = RemoteScreenInfo(
            width=0,
            height=1080,
            logical_width=0,
            logical_height=1080,
        )
        target = _fhd()
        x, y = transform_coordinates(sender, target, 100, 100)
        assert (x, y) == (0, 0)

    def test_zero_height(self) -> None:
        sender = RemoteScreenInfo(
            width=1920,
            height=0,
            logical_width=1920,
            logical_height=0,
        )
        target = _fhd()
        x, y = transform_coordinates(sender, target, 100, 100)
        assert (x, y) == (0, 0)


class TestBuildLocalScreenInfo:
    """PyQt6 import / QGuiApplication 부재 시 graceful None."""

    def test_no_qguiapplication_instance(self) -> None:
        # 한글 주석 — QGuiApplication.instance() = None 시 None 반환.
        with patch("PyQt6.QtGui.QGuiApplication.instance", return_value=None):
            result = build_local_screen_info()
            assert result is None


class TestRemoteScreenInfoInvariant:
    """RemoteScreenInfo dataclass invariant 검증 (음수 / 0 차단)."""

    def test_negative_width_raises(self) -> None:
        with pytest.raises(ValueError, match="width"):
            RemoteScreenInfo(
                width=-1,
                height=1080,
                logical_width=0,
                logical_height=1080,
            )

    def test_zero_dpi_raises(self) -> None:
        with pytest.raises(ValueError, match="dpi"):
            RemoteScreenInfo(
                width=1920,
                height=1080,
                logical_width=1920,
                logical_height=1080,
                dpi=0,
            )

    def test_negative_backing_scale_raises(self) -> None:
        with pytest.raises(ValueError, match="backing_scale"):
            RemoteScreenInfo(
                width=1920,
                height=1080,
                logical_width=1920,
                logical_height=1080,
                backing_scale=-1.0,
            )
