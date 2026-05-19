# SPDX-License-Identifier: GPL-3.0-or-later
"""원격 제어 좌표 보정 — sender ↔ target 화면 해상도 + DPI + Retina backing scale 비율 (cycle 148 skeleton).

방향 정의 (cycle 148 사용자 directive 2026-05-19):

- ``sender`` = controller (control 요청자) 의 view 단. 사용자 mouse 좌표 의 발생점.
- ``target`` = 원격 제어 대상. sender 의 view 좌표 → target OS 의 절대 좌표 변환 의무.

본 module 의 범위
----------------
- ``AspectRatioPolicy`` Enum — 3 종 (letterbox / stretch / crop) 의 aspect ratio mismatch 대응.
- ``RemoteScreenInfo`` frozen dataclass — sender / target 양쪽 의 화면 메타 (physical pixel
  + logical pixel + DPI + backing_scale + primary monitor index).
- ``transform_coordinates`` 함수 — sender 좌표 → target 좌표 비례 변환 + DPI / Retina 보정
  + 경계 cap.
- ``build_local_screen_info`` 함수 — PyQt6 의 QGuiApplication.screens[0] 자동 detect (
  framework 부재 시 graceful None).

본 cycle 의 범위 외 (Phase 5 cycle 166~180 의무):
- 실 NSScreen / win32 GetDpiForWindow 호출 (PyQt6 graceful 만).
- 실 mouse event dispatch (CGEventCreateMouseEvent / SendInput / XTestFakeMotionEvent).
- multi-monitor span + monitor 별 DPI 개별 처리.
- HiDPI fractional scaling (Windows 150% / Linux Wayland scale_factor) 의 sub-pixel 정합.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

log = logging.getLogger(__name__)


class AspectRatioPolicy(Enum):
    """aspect ratio mismatch 시 사용자 선택 정책 3 종."""

    # 한글 주석 — 검은 띠 + 가운데 정렬 (default). sender 화면 비율 보존.
    LETTERBOX = "letterbox"
    # 한글 주석 — 왜곡 허용 + target 전체 화면 사용.
    STRETCH = "stretch"
    # 한글 주석 — sender 화면 의 중앙 영역만 target 표시. 영역 외 좌표 = (-1, -1) dispatch skip.
    CROP = "crop"


@dataclass(frozen=True, slots=True)
class RemoteScreenInfo:
    """원격 화면 메타 정보 — sender / target 양쪽 의 WebRTC DataChannel 교환 의무.

    Attributes
    ----------
    width : int
        physical pixel 가로 (backing scale 반영). macOS Retina 시 logical_width * 2.
    height : int
        physical pixel 세로.
    logical_width : int
        CSS pixel (logical) 가로. macOS backing 1x 시 physical 등가.
    logical_height : int
        CSS pixel (logical) 세로.
    dpi : int
        Windows DPI awareness (96 = 100% / 120 = 125% / 144 = 150% / 168 = 175%). default 96.
    backing_scale : float
        macOS Retina backing scale (1.0 / 2.0 / 3.0). Windows 통상 1.0.
    primary_monitor_index : int
        multi-monitor 시 primary index. 본 cycle = 0 단일 monitor 가정.
    """

    width: int
    height: int
    logical_width: int
    logical_height: int
    dpi: int = 96
    backing_scale: float = 1.0
    primary_monitor_index: int = 0

    def __post_init__(self) -> None:
        # 한글 주석 — dataclass invariant 검증. 음수 / 0 width / height 차단.
        if self.width < 0:
            raise ValueError(f"width 음수 불가 — {self.width}")
        if self.height < 0:
            raise ValueError(f"height 음수 불가 — {self.height}")
        if self.logical_width < 0:
            raise ValueError(f"logical_width 음수 불가 — {self.logical_width}")
        if self.logical_height < 0:
            raise ValueError(f"logical_height 음수 불가 — {self.logical_height}")
        if self.dpi <= 0:
            raise ValueError(f"dpi 양수 의무 — {self.dpi}")
        if self.backing_scale <= 0:
            raise ValueError(f"backing_scale 양수 의무 — {self.backing_scale}")
        if self.primary_monitor_index < 0:
            raise ValueError(
                f"primary_monitor_index 음수 불가 — {self.primary_monitor_index}"
            )


def transform_coordinates(
    sender: RemoteScreenInfo,
    target: RemoteScreenInfo,
    sender_x: int,
    sender_y: int,
    policy: AspectRatioPolicy = AspectRatioPolicy.LETTERBOX,
) -> tuple[int, int]:
    """sender 좌표 → target 절대 좌표 변환.

    비례 scaling + aspect ratio 정책 분기 + DPI / Retina 보정 + 경계 cap 의 순서.

    Parameters
    ----------
    sender : RemoteScreenInfo
        controller 의 view 단 화면 정보.
    target : RemoteScreenInfo
        원격 제어 대상 OS 의 화면 정보.
    sender_x, sender_y : int
        sender view 안 mouse 좌표 (physical pixel).
    policy : AspectRatioPolicy
        aspect mismatch 대응 정책. default = LETTERBOX.

    Returns
    -------
    tuple[int, int]
        target 의 OS 절대 좌표. CROP 정책 의 영역 외 시 (-1, -1) 반환 → dispatch skip 신호.
    """

    # 한글 주석 — sender 화면 크기 0 = 변환 불가 → (0, 0) 안전 반환.
    if sender.width == 0 or sender.height == 0:
        return (0, 0)

    sender_aspect = sender.width / sender.height
    target_aspect = target.width / target.height

    if abs(sender_aspect - target_aspect) < 0.001 or policy == AspectRatioPolicy.STRETCH:
        # 한글 주석 — aspect 일치 또는 stretch 허용 → 직접 비례 scaling.
        target_x = int(sender_x * target.width / sender.width)
        target_y = int(sender_y * target.height / sender.height)
    elif policy == AspectRatioPolicy.LETTERBOX:
        # 한글 주석 — letterbox = 가운데 정렬 + 검은 띠. sender 화면 비율 보존.
        if sender_aspect > target_aspect:
            # sender 가 wider → target 안 상하 검은 띠.
            scale = target.width / sender.width
            scaled_height = int(sender.height * scale)
            offset_y = (target.height - scaled_height) // 2
            target_x = int(sender_x * scale)
            target_y = offset_y + int(sender_y * scale)
        else:
            # sender 가 taller → target 안 좌우 검은 띠.
            scale = target.height / sender.height
            scaled_width = int(sender.width * scale)
            offset_x = (target.width - scaled_width) // 2
            target_x = offset_x + int(sender_x * scale)
            target_y = int(sender_y * scale)
    else:  # AspectRatioPolicy.CROP
        # 한글 주석 — crop = sender 화면 의 중앙 영역만 target 표시.
        if sender_aspect > target_aspect:
            scale = target.height / sender.height
            crop_width = int(target.width / scale)
            offset_x = (sender.width - crop_width) // 2
            if sender_x < offset_x or sender_x >= offset_x + crop_width:
                return (-1, -1)  # 영역 외 → dispatch skip 신호.
            target_x = int((sender_x - offset_x) * scale)
            target_y = int(sender_y * scale)
        else:
            scale = target.width / sender.width
            crop_height = int(target.height / scale)
            offset_y = (sender.height - crop_height) // 2
            if sender_y < offset_y or sender_y >= offset_y + crop_height:
                return (-1, -1)
            target_x = int(sender_x * scale)
            target_y = int((sender_y - offset_y) * scale)

    # 한글 주석 — DPI 보정 (Windows scaling factor). macOS backing scale = width / logical_width 비율로
    # 이미 width 안 반영 가정 (build_local_screen_info 가 physical pixel 산정 의무).
    if target.dpi != 96:
        dpi_scale = target.dpi / 96
        target_x = int(target_x * dpi_scale)
        target_y = int(target_y * dpi_scale)

    # 한글 주석 — target 경계 cap. width-1 / height-1 의무 (좌표 0-based).
    if target.width > 0:
        target_x = max(0, min(target_x, target.width - 1))
    if target.height > 0:
        target_y = max(0, min(target_y, target.height - 1))

    return (target_x, target_y)


def build_local_screen_info() -> Optional[RemoteScreenInfo]:
    """현재 시스템 의 RemoteScreenInfo 자동 detect.

    PyQt6 의 QGuiApplication.screens[0] 의 primary screen 의 size + DPI + devicePixelRatio
    경유. macOS NSScreen / Windows GetDpiForWindow 의 직접 호출 = Phase 5 cycle 166~180 의무.

    Returns
    -------
    Optional[RemoteScreenInfo]
        PyQt6 부재 + QGuiApplication 미생성 시 None graceful.
    """

    try:
        from PyQt6.QtGui import QGuiApplication
    except ImportError:
        log.warning("[coord_transform] PyQt6 부재 — None 반환")
        return None

    app = QGuiApplication.instance()
    if app is None:
        log.warning("[coord_transform] QGuiApplication 미생성 — None 반환")
        return None
    screens = app.screens()
    if not screens:
        log.warning("[coord_transform] screens 빈 list — None 반환")
        return None

    primary = screens[0]
    size = primary.size()
    logical_dpi = primary.logicalDotsPerInch()
    device_pixel_ratio = primary.devicePixelRatio()

    return RemoteScreenInfo(
        width=int(size.width() * device_pixel_ratio),
        height=int(size.height() * device_pixel_ratio),
        logical_width=size.width(),
        logical_height=size.height(),
        dpi=int(logical_dpi),
        backing_scale=float(device_pixel_ratio),
        primary_monitor_index=0,
    )
