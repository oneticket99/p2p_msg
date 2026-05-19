# SPDX-License-Identifier: GPL-3.0-or-later
"""원격 제어 screen capture — 3 OS 분기 skeleton (cycle 150).

Phase 5 Item 5 원격 제어 의 screen capture actual binding chain 의 skeleton.
cycle 132 REMOTE 3 ENUM wiring + cycle 148 remote coord transform chain 의
연장선 의 OS-specific framework binding layer.

3 OS 분기 의무
--------------
- macOS — Quartz ``CGMainDisplayID`` + ``CGDisplayCreateImage`` + CFRelease
- Windows — ``GetDC`` + ``CreateCompatibleDC`` + ``BitBlt`` + ``GetDIBits``
- Linux — Xlib ``XGetImage`` + Wayland 의 별개 cycle 의 의무

본 cycle 의 범위
---------------
- ``CapturedFrame`` frozen dataclass — width / height / bytes_per_row / pixel_format / data
- ``ScreenCaptureBackend`` base — capture_primary + capture_monitor + list_monitors
- ``MacOSQuartzBackend`` — PyObjC + Quartz graceful import + CFRelease 의 try / finally
- ``WindowsBitBltBackend`` — win32gui graceful import skeleton
- ``LinuxX11Backend`` — Xlib graceful import skeleton
- ``build_capture_backend`` — ``platform.system()`` 의 OS 분기 factory

본 cycle 의 범위 외 (Phase 5 cycle 166~180 의 의무):
- 실 CFData extract + pixel buffer marshal (raw bytes 반환)
- Win32 BitBlt + GetDIBits ctypes binding 의 actual pixel copy
- Xlib XGetImage 의 actual buffer extract
- Wayland 의 screencopy-unstable-v1 protocol 의 별개 cycle
- multi-monitor 의 monitor_index dispatch 의 OS API binding
- frame rate throttle + ABR encoding (raw → png / jpeg / h264)
- cursor overlay (Pattern A 의 도움 시각화)
- HiDPI / Retina backing scale 의 coord_transform 연계 검토

메모리 release 의무 (PyObjC + Quartz Core — feedback_objc_memory_release_mandatory):
- ``CGDisplayCreateImage`` 반환 = CGImageRef CFRetain count = 1.
  ``CGImageGetDataProvider`` + ``CGDataProviderCopyData`` 의 결과 = CFData =
  추가 release 의무. 단일 capture cycle 의 끝 시점 = 양쪽 CFRelease 의무.
- ``with objc.autorelease_pool():`` 패턴 권장 — frame 의 sequential capture
  의 loop 안 의 autorelease pool drain 의 의무 (60 fps × 1080p RGB frame
  의 GB-scale memory 누수 차단).
- try / finally 패턴 의 raise 시점 의 부분 alloc 의 release 의무.
- Win32 ``GetDC`` 의 ``ReleaseDC`` 의무 + ``DeleteObject`` (HBITMAP) + ``DeleteDC``
  (compat DC) 의 finally chain 의무.
- X11 ``Display`` handle 의 process-wide single + finalizer 의 release.
- tracemalloc + objgraph 의 회귀 검증 (별개 cycle 의 의무).
"""

from __future__ import annotations

import logging
import platform
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CapturedFrame:
    """captured 1 frame raw pixel 결과.

    Attributes
    ----------
    width : int
        frame 가로 pixel.
    height : int
        frame 세로 pixel.
    bytes_per_row : int
        1 row 의 byte 수. ``width × bytes_per_pixel`` + alignment padding 가능.
    pixel_format : str
        "BGRA" / "RGBA" / "RGB" 의 layout 식별자.
    data : bytes
        raw pixel buffer (immutable).
    """

    width: int
    height: int
    bytes_per_row: int
    pixel_format: str  # "BGRA" / "RGBA" / "RGB"
    data: bytes  # raw pixel bytes


class ScreenCaptureBackend:
    """3 OS 분기 base class — skeleton fallback.

    capture_primary / capture_monitor / list_monitors 의 None / [] 반환 =
    skeleton 단계 의 graceful degrade. 실 구현 의 OS-specific subclass 의 override 의무.
    """

    def capture_primary(self) -> Optional[CapturedFrame]:
        """primary monitor 1 frame capture — skeleton = None 반환."""
        return None

    def capture_monitor(self, monitor_index: int) -> Optional[CapturedFrame]:
        """monitor_index 의 1 frame capture — skeleton = None 반환."""
        return None

    def list_monitors(self) -> list[dict]:
        """monitor 목록 반환 — skeleton = 빈 list."""
        return []


class MacOSQuartzBackend(ScreenCaptureBackend):
    """macOS Quartz CGDisplayCreateImage + CFRelease 의무 (feedback-objc-memory-release-mandatory).

    실 구현 = PyObjC + Quartz 의 CGDisplayCreateImage 의 binding. 본 cycle =
    graceful import + try / finally CFRelease chain skeleton.

    메모리 release 의무 (사용자 directive 2026-05-21):
    - ``CGDisplayCreateImage`` 반환 = CGImageRef. capture 직후 ``CFRelease`` 의무.
    - ``CGImageGetDataProvider`` + ``CGDataProviderCopyData`` 의 결과 CFData = 추가 release 의무.
    - ``with objc.autorelease_pool():`` 패턴 의 sequential capture loop 의 의무.
    - try / finally 의 raise 경로 의 부분 alloc release 의 의무.
    """

    def capture_primary(self) -> Optional[CapturedFrame]:
        """primary display 1 frame capture skeleton — graceful import + CFRelease."""
        try:
            from Quartz import CGDisplayCreateImage, CGMainDisplayID  # type: ignore
            from CoreFoundation import CFRelease  # type: ignore
        except ImportError:
            log.warning("[capture-macos] PyObjC + Quartz 부재 — graceful None")
            return None
        cg_image = None
        try:
            display_id = CGMainDisplayID()
            cg_image = CGDisplayCreateImage(display_id)
            if cg_image is None:
                return None
            # Phase 5 본격 cycle 의 actual CFData extract — 현재 skeleton None 반환
            return None
        except Exception as exc:  # noqa: BLE001 — graceful degrade 의무
            log.warning("[capture-macos] capture 실패 — %r", exc)
            return None
        finally:
            # CFRelease 의무 — 1 frame leak = 60 fps × 1080p = 분당 1.3 GB 누수
            if cg_image is not None:
                try:
                    CFRelease(cg_image)
                except Exception:  # noqa: BLE001 — release 의 silent best-effort
                    pass


class WindowsBitBltBackend(ScreenCaptureBackend):
    """Windows BitBlt + GetDC + ReleaseDC chain skeleton.

    실 구현 = win32gui + win32ui + win32con 의 BitBlt + GetDIBits chain.
    본 cycle = graceful import skeleton.

    메모리 release 의무 (Win32 GDI handle):
    - ``GetDC(0)`` = HDC. ``ReleaseDC(0, hdc)`` 의무.
    - ``CreateCompatibleDC`` = HDC. ``DeleteDC`` 의무.
    - ``CreateCompatibleBitmap`` = HBITMAP. ``DeleteObject`` 의무.
    - try / finally chain 의 GDI leak 차단.
    """

    def capture_primary(self) -> Optional[CapturedFrame]:
        """primary monitor BitBlt skeleton — graceful import + GDI release chain."""
        try:
            import win32gui  # type: ignore  # noqa: F401
        except ImportError:
            log.warning("[capture-windows] win32gui 부재 — graceful None")
            return None
        # Phase 5 본격 cycle 의 actual BitBlt chain — 현재 skeleton None 반환
        return None


class LinuxX11Backend(ScreenCaptureBackend):
    """Linux X11 XGetImage skeleton — Wayland 의 별개 cycle 의 의무.

    실 구현 = Xlib ``Display.screen().root.get_image()`` + Wayland 의
    ``screencopy-unstable-v1`` protocol 의 별개 cycle 의무.
    본 cycle = graceful import skeleton.
    """

    def capture_primary(self) -> Optional[CapturedFrame]:
        """primary monitor X11 XGetImage skeleton — graceful import."""
        try:
            from Xlib import display  # type: ignore  # noqa: F401
        except ImportError:
            log.warning("[capture-linux] Xlib 부재 — graceful None")
            return None
        # Phase 5 본격 cycle 의 actual XGetImage + buffer marshal — 현재 skeleton None
        return None


def build_capture_backend() -> ScreenCaptureBackend:
    """현 OS 의 ``platform.system()`` 분기 의 backend instantiate.

    Returns
    -------
    ScreenCaptureBackend
        Darwin → ``MacOSQuartzBackend`` / Windows → ``WindowsBitBltBackend`` /
        Linux → ``LinuxX11Backend`` / 그 외 → base ``ScreenCaptureBackend``.
    """
    sys_name = platform.system().lower()
    if sys_name == "darwin":
        return MacOSQuartzBackend()
    if sys_name == "windows":
        return WindowsBitBltBackend()
    if sys_name == "linux":
        return LinuxX11Backend()
    log.warning("[capture] OS 미지원 — %s", sys_name)
    return ScreenCaptureBackend()
