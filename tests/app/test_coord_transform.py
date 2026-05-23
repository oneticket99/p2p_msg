# SPDX-License-Identifier: GPL-3.0-or-later
"""remote coord_transform unit test — cycle 169.690 신설."""

from __future__ import annotations

import pytest


class TestRemoteScreenInfoValidation:
    def test_negative_width_raises(self) -> None:
        from app.remote.coord_transform import RemoteScreenInfo

        with pytest.raises(ValueError, match="width"):
            RemoteScreenInfo(
                width=-1, height=100,
                logical_width=100, logical_height=100,
            )

    def test_zero_dpi_raises(self) -> None:
        from app.remote.coord_transform import RemoteScreenInfo

        with pytest.raises(ValueError, match="dpi"):
            RemoteScreenInfo(
                width=100, height=100,
                logical_width=100, logical_height=100,
                dpi=0,
            )

    def test_zero_backing_scale_raises(self) -> None:
        from app.remote.coord_transform import RemoteScreenInfo

        with pytest.raises(ValueError, match="backing_scale"):
            RemoteScreenInfo(
                width=100, height=100,
                logical_width=100, logical_height=100,
                backing_scale=0.0,
            )

    def test_negative_monitor_index_raises(self) -> None:
        from app.remote.coord_transform import RemoteScreenInfo

        with pytest.raises(ValueError, match="primary_monitor_index"):
            RemoteScreenInfo(
                width=100, height=100,
                logical_width=100, logical_height=100,
                primary_monitor_index=-1,
            )

    def test_valid_construct(self) -> None:
        from app.remote.coord_transform import RemoteScreenInfo

        s = RemoteScreenInfo(
            width=1920, height=1080,
            logical_width=960, logical_height=540,
            dpi=144, backing_scale=2.0,
        )
        assert s.width == 1920
        assert s.dpi == 144


class TestTransformCoordinates:
    def test_sender_zero_returns_origin(self) -> None:
        # 한글 주석 — sender 화면 0 → (0, 0) 안전 폴백
        from app.remote.coord_transform import (
            AspectRatioPolicy, RemoteScreenInfo, transform_coordinates,
        )

        sender = RemoteScreenInfo(
            width=0, height=100,
            logical_width=0, logical_height=100,
        )
        target = RemoteScreenInfo(
            width=100, height=100,
            logical_width=100, logical_height=100,
        )
        x, y = transform_coordinates(
            sender, target, sender_x=50, sender_y=50,
            policy=AspectRatioPolicy.LETTERBOX,
        )
        assert (x, y) == (0, 0)

    def test_same_aspect_proportional(self) -> None:
        # 한글 주석 — 동일 비율 sender (100x100) → target (200x200) → 2배 scaling
        from app.remote.coord_transform import (
            AspectRatioPolicy, RemoteScreenInfo, transform_coordinates,
        )

        sender = RemoteScreenInfo(
            width=100, height=100,
            logical_width=100, logical_height=100,
        )
        target = RemoteScreenInfo(
            width=200, height=200,
            logical_width=200, logical_height=200,
        )
        x, y = transform_coordinates(
            sender, target, sender_x=50, sender_y=50,
            policy=AspectRatioPolicy.LETTERBOX,
        )
        # 한글 주석 — 중앙 좌표 50 → 200 의 중앙 100
        assert x == 100
        assert y == 100

    def test_aspect_ratio_policy_enum(self) -> None:
        from app.remote.coord_transform import AspectRatioPolicy

        assert AspectRatioPolicy.LETTERBOX.value == "letterbox"
        assert AspectRatioPolicy.STRETCH.value == "stretch"
        assert AspectRatioPolicy.CROP.value == "crop"
