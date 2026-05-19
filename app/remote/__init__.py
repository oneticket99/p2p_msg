# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 원격 데스크탑 차별화 패키지 — 사이클 55 entry skeleton.

cycle 148 추가 — ``coord_transform`` 모듈 (sender ↔ target 화면 해상도 + DPI + Retina
backing scale 좌표 보정). Phase 5 cycle 166~180 원격 제어 본격 prerequisite.
"""

from app.remote.coord_transform import (
    AspectRatioPolicy,
    RemoteScreenInfo,
    build_local_screen_info,
    transform_coordinates,
)

__all__ = [
    "AspectRatioPolicy",
    "RemoteScreenInfo",
    "build_local_screen_info",
    "transform_coordinates",
]
