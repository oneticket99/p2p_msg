# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 screen capture abstraction — 사이클 57.

원격 데스크탑 의 target 단 screen capture layer (사용자 directive 2026-05-21
의 controller / target 용어 정합 — target = control 대상 의 화면 capture +
controller 의 input event 의 OS 의 적용 단). platform 별 framework 의존
(macOS Quartz / Win32 BitBlt / X11 XGetImage) 의 인터페이스 격리 의무.

본 module = abstract backend + Mock + macOS Quartz placeholder. 실 framework
binding (PyObjC + Quartz Core / ctypes Win32 / Xlib) = 별개 cycle 의 의무.

본 module 범위
-------------
- ``CaptureFormat`` Enum — 2 종 (BGRA + RGB)
- ``CapturedFrame`` frozen dataclass — width + height + format + buffer + capture_time_ms
- ``CaptureBackend`` Protocol — capture() async + is_available() classmethod 의무
- ``MockCaptureBackend`` — test fixture 의 deterministic 1x1 BGRA frame
- ``MacOSQuartzBackend`` — placeholder (PyObjC framework 부재 시 NotImplementedError raise)
- ``select_capture_backend`` — platform-specific 의 factory
- ``captured_to_remote_frame`` — CapturedFrame → app.remote.protocol.RemoteFrame 변환

본 cycle 의 범위 외 (별개 cycle):
- PyObjC + Quartz Core 의 실 framework binding (CGDisplayCreateImage)
- Win32 BitBlt + GetDIBits 의 ctypes binding
- X11 XGetImage + Xlib python binding
- multi-monitor 의 display select
- ABR encoding (raw → png / jpeg / h264) — 별개 cycle
- cursor pointer overlay (Pattern A 의 도움 시각화)
- frame rate throttling + dynamic resolution

메모리 release 의무 (PyObjC + Quartz Core — 별개 cycle 실 binding 단계):
- ``CGDisplayCreateImage`` 반환 = CGImageRef CFRetain count = 1. ``CGImageGetDataProvider``
  + ``CGDataProviderCopyData`` 의 결과 = CFData = 추가 release 의무.
  단일 capture cycle 의 끝 시점 = 양쪽 CFRelease 의무.
- ``CGDisplayCreateImageForRect`` 동일.
- ``with objc.autorelease_pool():`` 패턴 권장 — frame 의 sequential capture
  의 loop 안 의 autorelease pool drain 의 의무 (60 fps × 1080p RGB frame
  의 GB-scale memory 누수 차단).
- HWND / X11 Display handle 의 process-wide single 의무 + finalizer 의 release.
- tracemalloc + objgraph 의 회귀 검증 (별개 cycle 의 의무).
"""

from __future__ import annotations

import platform
import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Final, Optional, Protocol, Type

from app.remote.protocol import FrameFormat, RemoteFrame

# CapturedFrame 의 최소 dimension — 1x1 의 의무 (위 / 아래 0 차단)
_MIN_DIMENSION: Final[int] = 1


class CaptureFormat(str, Enum):
    """captured frame 의 pixel format."""

    BGRA = "bgra"  # macOS Quartz 의 native + Win32 BitBlt 의 native
    RGB = "rgb"  # X11 XGetImage 의 native + 변환 후 의 normalized format


@dataclass(frozen=True, slots=True)
class CapturedFrame:
    """단일 screen capture 결과.

    Attributes
    ----------
    width : int
        frame 가로 pixel.
    height : int
        frame 세로 pixel.
    format : CaptureFormat
        pixel layout.
    buffer : bytes
        raw pixel buffer. BGRA = 4 byte / pixel, RGB = 3 byte / pixel.
    capture_time_ms : int
        capture 시점 (UNIX epoch ms).
    """

    width: int
    height: int
    format: CaptureFormat
    buffer: bytes
    capture_time_ms: int

    def __post_init__(self) -> None:
        if self.width < _MIN_DIMENSION:
            raise ValueError(f"width 양수 의무 — {self.width}")
        if self.height < _MIN_DIMENSION:
            raise ValueError(f"height 양수 의무 — {self.height}")
        if self.capture_time_ms < 0:
            raise ValueError(
                f"capture_time_ms 음수 불가 — {self.capture_time_ms}"
            )
        expected_size = self._expected_buffer_size()
        if len(self.buffer) != expected_size:
            raise ValueError(
                f"buffer 크기 불일치 — len={len(self.buffer)} "
                f"(기대 {expected_size} = {self.width}×{self.height}×"
                f"{self._bytes_per_pixel()})"
            )

    def _bytes_per_pixel(self) -> int:
        """format 별 pixel 당 byte 수."""

        return 4 if self.format == CaptureFormat.BGRA else 3

    def _expected_buffer_size(self) -> int:
        """width × height × bytes_per_pixel 의 정합 검증값."""

        return self.width * self.height * self._bytes_per_pixel()


class CaptureBackend(Protocol):
    """screen capture backend 의 interface.

    platform-specific 구현 의무:
    - ``is_available`` classmethod — runtime framework 의 import 가능 여부
    - ``capture`` instance method — 1 frame capture 반환

    본 Protocol 의 의무 = 인터페이스 통일 + duck typing 의 의 정합.
    """

    @classmethod
    def is_available(cls) -> bool:
        """현 platform 의 backend 의 framework 가용성 검증."""
        ...

    def capture(self) -> CapturedFrame:
        """단일 frame capture 반환."""
        ...


class MockCaptureBackend:
    """test fixture — deterministic 의 1x1 BGRA frame 반환.

    실 platform framework 의 의존 없음. tests 의 round-trip + factory 검증
    의무 의 단일 backend.
    """

    @classmethod
    def is_available(cls) -> bool:
        """mock backend = 항상 가용."""

        return True

    def __init__(self, width: int = 1, height: int = 1) -> None:
        if width < _MIN_DIMENSION or height < _MIN_DIMENSION:
            raise ValueError(
                f"width / height 양수 의무 — width={width} height={height}"
            )
        self._width = width
        self._height = height

    def capture(self) -> CapturedFrame:
        """deterministic gray frame (RGBA = 128, 128, 128, 255)."""

        pixel = b"\x80\x80\x80\xff"
        buffer = pixel * (self._width * self._height)
        return CapturedFrame(
            width=self._width,
            height=self._height,
            format=CaptureFormat.BGRA,
            buffer=buffer,
            capture_time_ms=int(time.time() * 1000),
        )


class MacOSQuartzBackend:
    """macOS Quartz placeholder — 사이클 57 skeleton.

    실 구현 = PyObjC + Quartz Core 의 CGDisplayCreateImage 의 binding.
    본 cycle = framework 부재 시 NotImplementedError raise 의 graceful degrade.
    별개 cycle 의 실 binding 의무.

    메모리 release 의무 (실 binding 단계 의 필수 검토 — 사용자 directive 2026-05-21):

    - ``CGDisplayCreateImage`` + ``CGImageGetDataProvider`` + ``CGDataProviderCopyData``
      = 각 단계 의 CFRelease 의무. 1 frame leak = 60 fps × 1080p RGB = ~370 KB / frame
      = 분당 1.3 GB 누수.
    - ``CGImageRef`` 의 capture 직후 ``CFRelease`` 의무 (또는 ``with objc.autorelease_pool()``).
    - ``__del__`` 의 finalizer + ``close()`` 의 explicit shutdown 의 의무.
    - try / finally 패턴 의 raise 시 부분 alloc 의 release 의무.
    """

    @classmethod
    def is_available(cls) -> bool:
        """macOS + PyObjC + Quartz 의 import 가능 여부."""

        if sys.platform != "darwin":
            return False
        try:
            import Quartz  # type: ignore[import]  # noqa: F401
        except ImportError:
            return False
        return True

    def __init__(self, display_id: Optional[int] = None) -> None:
        """display_id None 시점 main display (CGMainDisplayID) retain (cycle 169.416)."""
        self._display_id = display_id

    def capture(self) -> CapturedFrame:
        """cycle 169.416 — PyObjC + Quartz CGDisplayCreateImage actual binding.

        chain:
        1. CGMainDisplayID() (display_id None 시점)
        2. CGDisplayCreateImage(did) → CGImageRef
        3. CGImageGetWidth/Height + GetDataProvider + CopyData → BGRA bytes
        4. CFRelease 의 CGImageRef + CFData (memory leak 차단, 사용자 directive 2026-05-21)

        Returns
        -------
        CapturedFrame
            BGRA bytes (width × height × 4).

        Raises
        ------
        RuntimeError
            CGDisplayCreateImage 실패 (display 부재 또는 권한 부재).
        """
        # 한글 주석 — cycle 169.575: PyObjC + Quartz framework 부재 graceful guard.
        # framework 의 의 의 의 부재 시점 NotImplementedError raise (test expect 정합).
        try:
            import Quartz  # type: ignore[import]
            import CoreFoundation  # type: ignore[import]
        except ModuleNotFoundError as _exc:
            raise NotImplementedError(
                "PyObjC + Quartz binding 부재 — pip install pyobjc-framework-Quartz 의무"
            ) from _exc

        did = self._display_id if self._display_id is not None else Quartz.CGMainDisplayID()
        image_ref = Quartz.CGDisplayCreateImage(did)
        if image_ref is None:
            raise RuntimeError(
                "CGDisplayCreateImage 실패 — 권한 부재 또는 display 부재"
            )
        try:
            width = int(Quartz.CGImageGetWidth(image_ref))
            height = int(Quartz.CGImageGetHeight(image_ref))
            provider = Quartz.CGImageGetDataProvider(image_ref)
            cfdata = Quartz.CGDataProviderCopyData(provider)
            if cfdata is None:
                raise RuntimeError("CGDataProviderCopyData 실패")
            try:
                length = int(CoreFoundation.CFDataGetLength(cfdata))
                ptr = CoreFoundation.CFDataGetBytePtr(cfdata)
                buffer = bytes(ptr[:length])
            finally:
                # 한글 주석 — CFData CFRelease 의무 (PyObjC autorelease pool 외부)
                del cfdata  # PyObjC GC 자동 release retain (autoreleased object)
        finally:
            # 한글 주석 — CGImageRef autoreleased 의 의 PyObjC GC retain
            del image_ref
        return CapturedFrame(
            width=width,
            height=height,
            format=CaptureFormat.BGRA,
            buffer=buffer,
            capture_time_ms=int(time.time() * 1000),
        )


class WindowsGDIBackend:
    """cycle 169.421 — Windows BitBlt capture actual binding via ctypes user32+gdi32.

    chain (entire desktop):
    1. GetDC(NULL) → screen HDC
    2. CreateCompatibleDC + CreateCompatibleBitmap + SelectObject
    3. BitBlt(SRCCOPY) → memory DC
    4. GetDIBits(BI_RGB) → BGRA bytes (32-bit DIB)
    5. DeleteObject + DeleteDC + ReleaseDC (memory leak 차단 의무)

    Notes
    -----
    GetDIBits BITMAPINFOHEADER biHeight = 음수 (top-down DIB) 활용 — 자동 row reverse.
    """

    @classmethod
    def is_available(cls) -> bool:
        if sys.platform not in ("win32", "cygwin"):
            return False
        try:
            import ctypes  # noqa: F401
            from ctypes import wintypes  # noqa: F401
            return True
        except ImportError:
            return False

    def capture(self) -> CapturedFrame:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        SRCCOPY = 0x00CC0020
        BI_RGB = 0
        DIB_RGB_COLORS = 0
        SM_CXSCREEN = 0
        SM_CYSCREEN = 1

        width = user32.GetSystemMetrics(SM_CXSCREEN)
        height = user32.GetSystemMetrics(SM_CYSCREEN)
        screen_dc = user32.GetDC(None)
        if not screen_dc:
            raise RuntimeError("GetDC 실패 — Windows desktop DC 부재")
        mem_dc = gdi32.CreateCompatibleDC(screen_dc)
        if not mem_dc:
            user32.ReleaseDC(None, screen_dc)
            raise RuntimeError("CreateCompatibleDC 실패")
        bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
        if not bitmap:
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(None, screen_dc)
            raise RuntimeError("CreateCompatibleBitmap 실패")
        try:
            gdi32.SelectObject(mem_dc, bitmap)
            gdi32.BitBlt(mem_dc, 0, 0, width, height, screen_dc, 0, 0, SRCCOPY)

            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", wintypes.DWORD),
                    ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD),
                ]

            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height  # 한글 주석 — 음수 = top-down DIB (auto row reverse)
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = BI_RGB

            buf_size = width * height * 4
            buffer = (ctypes.c_ubyte * buf_size)()
            res = gdi32.GetDIBits(
                mem_dc, bitmap, 0, height, buffer,
                ctypes.byref(bmi), DIB_RGB_COLORS,
            )
            if res == 0:
                raise RuntimeError("GetDIBits 실패")
            return CapturedFrame(
                width=width, height=height, format=CaptureFormat.BGRA,
                buffer=bytes(buffer), capture_time_ms=int(time.time() * 1000),
            )
        finally:
            # 한글 주석 — GDI 객체 release 의무 (memory leak 차단 — 사용자 directive 2026-05-21)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(None, screen_dc)


class LinuxX11Backend:
    """cycle 169.421 — Linux X11 XGetImage capture actual binding via python-xlib.

    chain:
    1. Xlib.display.Display() → connect default display
    2. root.get_image(0,0,w,h, ZPixmap, 0xffffffff) → image bytes
    3. Display.close() (resource release 의무)

    Notes
    -----
    Xlib data = BGRX (32bit) — BGRA로 reformat (alpha=0xff fill).
    """

    @classmethod
    def is_available(cls) -> bool:
        if sys.platform != "linux":
            return False
        try:
            import Xlib.display  # type: ignore[import]  # noqa: F401
            from Xlib import X  # type: ignore[import]  # noqa: F401
            return True
        except ImportError:
            return False

    def capture(self) -> CapturedFrame:
        from Xlib import X  # type: ignore[import]
        import Xlib.display  # type: ignore[import]

        display = Xlib.display.Display()
        try:
            root = display.screen().root
            geom = root.get_geometry()
            width = int(geom.width)
            height = int(geom.height)
            raw = root.get_image(0, 0, width, height, X.ZPixmap, 0xFFFFFFFF)
            data = bytes(raw.data)  # BGRX 32-bit
            if len(data) != width * height * 4:
                raise RuntimeError(
                    f"X11 buffer 크기 불일치 — len={len(data)} 기대 {width*height*4}"
                )
            # 한글 주석 — BGRX → BGRA reformat (alpha=0xff fill)
            ba = bytearray(data)
            for i in range(3, len(ba), 4):
                ba[i] = 0xFF
            return CapturedFrame(
                width=width, height=height, format=CaptureFormat.BGRA,
                buffer=bytes(ba), capture_time_ms=int(time.time() * 1000),
            )
        finally:
            # 한글 주석 — display close 의무 (Xlib socket release)
            try:
                display.close()
            except Exception:
                pass


def select_capture_backend(
    platform_name: Optional[str] = None,
) -> Type[CaptureBackend]:
    """platform-specific 의 capture backend class 의 factory.

    Parameters
    ----------
    platform_name : str | None
        "darwin" / "win32" / "linux" / "mock". None = ``sys.platform`` 의 자동 detect.

    Returns
    -------
    Type[CaptureBackend]
        backend class. caller 의 instantiate 의무.

    Raises
    ------
    NotImplementedError
        platform 의 backend 의 실 구현 미존재 (Win32 + X11 의 별개 cycle 의무).
    ValueError
        unknown platform_name.

    Notes
    -----
    "mock" = MockCaptureBackend (test 의 deterministic fixture).
    "darwin" = MacOSQuartzBackend (placeholder — 실 capture 별개 cycle).
    """

    name = (platform_name or sys.platform).lower()
    if name == "mock":
        return MockCaptureBackend  # type: ignore[return-value]
    if name == "darwin":
        return MacOSQuartzBackend  # type: ignore[return-value]
    if name in ("win32", "cygwin"):
        # cycle 169.421 — Windows GDI actual binding
        return WindowsGDIBackend  # type: ignore[return-value]
    if name == "linux":
        # cycle 169.421 — Linux X11 actual binding
        return LinuxX11Backend  # type: ignore[return-value]
    raise ValueError(f"unknown platform_name — {name}")


def detect_default_backend() -> Type[CaptureBackend]:
    """현 platform 의 default backend class (skeleton + 자동 detect).

    `select_capture_backend(None)` 의 wrapper + macOS = Quartz / 그 외 = Mock 폴백.
    실 구현 부재 platform = Mock 폴백 (skeleton 단계 의 의무).
    """

    name = sys.platform.lower()
    if name == "darwin":
        return MacOSQuartzBackend  # type: ignore[return-value]
    # Win32 + linux 의 실 구현 부재 = Mock 폴백 (skeleton 단계)
    return MockCaptureBackend  # type: ignore[return-value]


def captured_to_remote_frame(
    captured: CapturedFrame,
    frame_id: int,
) -> RemoteFrame:
    """``CapturedFrame`` → ``RemoteFrame`` 변환.

    captured.format BGRA → RemoteFrame.format RAW_RGB 의 변환 의무. raw_rgb
    의 RemoteFrame 의 의무 = pixel 당 3 byte (alpha 의 제외).

    Parameters
    ----------
    captured : CapturedFrame
        capture 결과 (BGRA 4-byte 또는 RGB 3-byte).
    frame_id : int
        RemoteFrame 의 sequential 식별자 (caller 의 monotonic 의무).

    Returns
    -------
    RemoteFrame
        protocol-level wire format. format = RAW_RGB.

    Notes
    -----
    BGRA → RGB 변환 = pixel 당 swap (B↔R + alpha drop). RGB 직접 = 변환 부재.
    PNG / JPEG encoding = 별개 cycle 의무 (Pillow + bandwidth 최적화).
    """

    if captured.format == CaptureFormat.RGB:
        rgb_buffer = captured.buffer
    else:
        # BGRA → RGB 변환 (alpha drop + B↔R swap)
        out = bytearray(captured.width * captured.height * 3)
        src = captured.buffer
        n_pixels = captured.width * captured.height
        for i in range(n_pixels):
            b = src[i * 4]
            g = src[i * 4 + 1]
            r = src[i * 4 + 2]
            # alpha (src[i*4+3]) 제외
            out[i * 3] = r
            out[i * 3 + 1] = g
            out[i * 3 + 2] = b
        rgb_buffer = bytes(out)
    return RemoteFrame(
        frame_id=frame_id,
        width=captured.width,
        height=captured.height,
        format=FrameFormat.RAW_RGB,
        payload=rgb_buffer,
        timestamp_ms=captured.capture_time_ms,
    )
