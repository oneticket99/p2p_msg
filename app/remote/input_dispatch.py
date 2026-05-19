# SPDX-License-Identifier: GPL-3.0-or-later
"""원격 제어 input event dispatch — 3 OS 분기 skeleton (cycle 150).

Phase 5 Item 5 원격 제어 의 input event dispatch (mouse + keyboard) actual binding
chain 의 skeleton. controller (sender) 의 RemoteInput → target OS native event 의
변환 + dispatch layer.

3 OS 분기 의무
--------------
- macOS — Quartz ``CGEventCreateMouseEvent`` + ``CGEventCreateKeyboardEvent`` + ``CGEventPost``
- Windows — user32 ``SendInput`` 의 ctypes binding (INPUT_MOUSE + INPUT_KEYBOARD)
- Linux — Xlib ``XTestFakeMotionEvent`` + ``XTestFakeButtonEvent`` + ``XTestFakeKeyEvent``

본 cycle 의 범위
---------------
- ``DispatchEvent`` frozen dataclass — event_type / x / y / button / keycode / pressed
- ``InputDispatchBackend`` base — dispatch / is_available 의 skeleton
- ``MacOSCGEventBackend`` — PyObjC + Quartz graceful import + CFRelease 의 try / finally
- ``WindowsSendInputBackend`` — ctypes user32 graceful import skeleton
- ``LinuxXTestBackend`` — Xlib + XTest graceful import skeleton
- ``build_input_dispatch_backend`` — ``platform.system()`` 의 OS 분기 factory

본 cycle 의 범위 외 (Phase 5 cycle 166~180 의 의무):
- 실 CGEvent + SendInput + XTest binding 의 actual dispatch
- macOS Accessibility permission grant flow (Privacy & Security pref pane)
- Windows UIPI / UAC elevation 의 SendInput 의 의 권한 chain
- modifier key stateful tracking (shift down → A 입력 → shift up 순서 의무)
- input event rate limit + flood 방어 (per-second cap)
- key repeat + auto-repeat 의 OS-specific timing 의 의 정합
- Wayland 의 libinput 의 권한 + 별개 protocol 의 별개 cycle

메모리 release 의무 (feedback_objc_memory_release_mandatory):
- ``CGEventCreateMouseEvent`` 반환 = CGEvent CFRetain count = 1.
  ``CGEventPost`` 직후 ``CFRelease`` 의무.
- ``CGEventCreateKeyboardEvent`` 동일 — 1 event = 1 CFRelease 의 의무.
- ``CGEventSourceCreate`` = process-wide 1회 만 + finalizer 의 CFRelease 의무.
- ``with objc.autorelease_pool():`` 패턴 권장 — high-frequency input dispatch loop
  의 autorelease pool drain 의 의무.
- macOS Accessibility permission 의 fail 시점 의 graceful raise + 누적
  event source 의 release 의무.
- try / finally 의 raise 경로 의 부분 alloc release 의 의무.
"""

from __future__ import annotations

import logging
import platform
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DispatchEvent:
    """input event 의 3 OS 의 공통 wire format.

    Attributes
    ----------
    event_type : str
        "mouse_move" / "mouse_button" / "key" 의 분류.
    x : int
        target 화면 의 절대 X 좌표 (mouse_* 의 의무).
    y : int
        target 화면 의 절대 Y 좌표 (mouse_* 의 의무).
    button : int
        mouse button (1 = left / 2 = middle / 3 = right). mouse_button 의 의무.
    keycode : int
        OS-specific keycode (macOS = AppKit / Win32 = VK_* / X11 = KeySym).
    pressed : bool
        True = press / down, False = release / up.
    """

    event_type: str  # "mouse_move" / "mouse_button" / "key"
    x: int = 0
    y: int = 0
    button: int = 0
    keycode: int = 0
    pressed: bool = False


class InputDispatchBackend:
    """3 OS 분기 base class — skeleton fallback.

    dispatch / is_available 의 False / None 반환 = skeleton graceful degrade.
    실 구현 의 OS-specific subclass 의 override 의무.
    """

    @classmethod
    def is_available(cls) -> bool:
        """현 platform 의 framework + permission 가용성 — skeleton = False."""
        return False

    def dispatch(self, event: DispatchEvent) -> Optional[bool]:
        """단일 event 의 OS native dispatch — skeleton = None 반환."""
        return None


class MacOSCGEventBackend(InputDispatchBackend):
    """macOS Quartz CGEventCreate* + CFRelease 의무 (feedback-objc-memory-release-mandatory).

    실 구현 = PyObjC + Quartz 의 CGEventCreateMouseEvent / CGEventCreateKeyboardEvent
    + CGEventPost 의 binding. 본 cycle = graceful import + try / finally CFRelease chain
    skeleton.

    메모리 release 의무 (사용자 directive 2026-05-21):
    - ``CGEventCreateMouseEvent`` 반환 = CGEvent. ``CGEventPost`` 직후 ``CFRelease`` 의무.
    - ``CGEventCreateKeyboardEvent`` 동일.
    - ``CGEventSourceCreate`` = process-wide 1회 만 + ``__del__`` finalizer 의 release.
    - try / finally 의 raise 경로 의 부분 alloc release 의 의무.
    """

    @classmethod
    def is_available(cls) -> bool:
        """PyObjC + Quartz import 가능 + macOS Accessibility permission 의 가용성."""
        if platform.system().lower() != "darwin":
            return False
        try:
            import Quartz  # type: ignore  # noqa: F401
        except ImportError:
            return False
        # Accessibility permission 의 check = 별개 cycle (AXIsProcessTrusted)
        return True

    def dispatch(self, event: DispatchEvent) -> Optional[bool]:
        """단일 event 의 CGEvent 변환 + CGEventPost + CFRelease chain skeleton."""
        try:
            from Quartz import (  # type: ignore  # noqa: F401
                CGEventCreateMouseEvent,
                CGEventPost,
            )
            from CoreFoundation import CFRelease  # type: ignore  # noqa: F401
        except ImportError:
            log.warning("[input-macos] PyObjC + Quartz 부재 — graceful None")
            return None
        cg_event = None
        try:
            # Phase 5 본격 cycle 의 actual CGEvent 변환 — 현재 skeleton None 반환
            return None
        except Exception as exc:  # noqa: BLE001 — graceful degrade 의무
            log.warning("[input-macos] dispatch 실패 — %r", exc)
            return None
        finally:
            # CFRelease 의무 — 1 event leak = 60 fps × N hour = GB-scale 누수
            if cg_event is not None:
                try:
                    CFRelease(cg_event)
                except Exception:  # noqa: BLE001 — release 의 silent best-effort
                    pass


class WindowsSendInputBackend(InputDispatchBackend):
    """Windows user32 SendInput skeleton.

    실 구현 = ctypes + user32.SendInput 의 INPUT_MOUSE + INPUT_KEYBOARD struct binding.
    본 cycle = graceful import skeleton.

    UIPI / UAC elevation 의무: SendInput 의 target process 의 integrity level 이
    sender process 의 integrity level 이상 시 silent fail. Phase 5 본격 cycle 의
    elevation flow 의 별개 cycle 의무.
    """

    @classmethod
    def is_available(cls) -> bool:
        """ctypes user32 import 가능 + Windows OS 의 가용성."""
        if platform.system().lower() != "windows":
            return False
        try:
            import ctypes  # noqa: F401
        except ImportError:
            return False
        return True

    def dispatch(self, event: DispatchEvent) -> Optional[bool]:
        """단일 event 의 SendInput skeleton — graceful import."""
        try:
            import ctypes  # noqa: F401
        except ImportError:
            log.warning("[input-windows] ctypes 부재 — graceful None")
            return None
        # Phase 5 본격 cycle 의 actual SendInput chain — 현재 skeleton None 반환
        return None


class LinuxXTestBackend(InputDispatchBackend):
    """Linux X11 XTest skeleton — Wayland 의 별개 cycle 의 의무.

    실 구현 = Xlib + XTest extension 의 ``XTestFakeMotionEvent`` +
    ``XTestFakeButtonEvent`` + ``XTestFakeKeyEvent`` 의 binding.
    Wayland 의 별개 protocol (libinput + Wayland virtual input) 의 별개 cycle 의무.
    본 cycle = graceful import skeleton.
    """

    @classmethod
    def is_available(cls) -> bool:
        """Xlib + XTest import 가능 + X11 session 의 가용성."""
        if platform.system().lower() != "linux":
            return False
        try:
            from Xlib import display  # type: ignore  # noqa: F401
        except ImportError:
            return False
        return True

    def dispatch(self, event: DispatchEvent) -> Optional[bool]:
        """단일 event 의 XTest skeleton — graceful import."""
        try:
            from Xlib import display  # type: ignore  # noqa: F401
        except ImportError:
            log.warning("[input-linux] Xlib 부재 — graceful None")
            return None
        # Phase 5 본격 cycle 의 actual XTest chain — 현재 skeleton None 반환
        return None


def build_input_dispatch_backend() -> InputDispatchBackend:
    """현 OS 의 ``platform.system()`` 분기 의 backend instantiate.

    Returns
    -------
    InputDispatchBackend
        Darwin → ``MacOSCGEventBackend`` / Windows → ``WindowsSendInputBackend`` /
        Linux → ``LinuxXTestBackend`` / 그 외 → base ``InputDispatchBackend``.
    """
    sys_name = platform.system().lower()
    if sys_name == "darwin":
        return MacOSCGEventBackend()
    if sys_name == "windows":
        return WindowsSendInputBackend()
    if sys_name == "linux":
        return LinuxXTestBackend()
    log.warning("[input-dispatch] OS 미지원 — %s", sys_name)
    return InputDispatchBackend()
