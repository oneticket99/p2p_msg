# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 input forward abstraction — 사이클 58.

원격 데스크탑 의 controller → target 의 input event 의 target 단 의 OS 적용
layer (target 의 키보드 / 마우스 의 controller 의 input event 의 의 제어 — 사용자
directive 2026-05-21 의 명시 정합). platform 별 framework 의존 (macOS CGEvent /
Win32 SendInput / X11 XTestFakeKey) 의 인터페이스 격리.

본 module = abstract backend + Mock + macOS CGEvent placeholder. 실 framework
binding (PyObjC + Quartz CGEventCreate*) = 별개 cycle.

본 module 범위
-------------
- ``InputForwardBackend`` Protocol — apply(event) + is_available classmethod
- ``MockInputForwardBackend`` — test fixture, event 의 in-memory list 누적
- ``MacOSCGEventBackend`` — placeholder (Quartz CGEventCreate* binding 의 별개 cycle)
- ``select_input_backend`` — platform-specific 의 factory
- ``apply_events`` — N event 의 batch dispatch helper

본 cycle 의 범위 외 (별개 cycle):
- PyObjC + Quartz 의 실 CGEventCreate* binding
- Win32 user32.dll 의 SendInput ctypes binding
- X11 XTestFakeKeyEvent + XTestFakeMotionEvent 의 Xlib binding
- Accessibility permission 의 OS 권한 grant flow (macOS Privacy)
- input event 의 rate limit + flood 방어
- modifier key 의 stateful tracking (shift down → A 입력 → shift up 순서 의무)

메모리 release 의무 (PyObjC + Quartz CGEvent — 별개 cycle 실 binding 단계):
- ``CGEventCreateMouseEvent`` 반환 = CFRetain count = 1. 호출 후 ``CFRelease``
  의무 (또는 PyObjC 의 auto-release pool 의무).
- ``CGEventCreateKeyboardEvent`` 동일 — 1 event = 1 CFRelease 의 의무.
- ``CGEventSourceCreate`` = process-wide 1회 만 + finalizer 의 CFRelease 의무.
- macOS Accessibility permission grant 의 fail 시점 의 ``apply`` 의 graceful
  raise + 누적 event source 의 release 의무.
- weak reference 또는 ``contextlib.AbstractContextManager`` 패턴 의 의무 검토.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import List, Optional, Protocol, Type

from app.remote.protocol import InputEventType, RemoteInput


class InputForwardBackend(Protocol):
    """input event forward backend 의 interface.

    platform-specific 구현 의무:
    - ``is_available`` classmethod — runtime framework 의 import + permission 의 가용성
    - ``apply`` instance method — 단일 RemoteInput 의 OS event 적용

    본 Protocol 의 의무 = duck typing 의 인터페이스 통일.
    """

    @classmethod
    def is_available(cls) -> bool:
        """현 platform 의 backend 의 framework + permission 가용성 검증."""
        ...

    def apply(self, event: RemoteInput) -> None:
        """단일 RemoteInput 의 OS event 적용."""
        ...


@dataclass(slots=True)
class MockInputForwardBackend:
    """test fixture — apply 호출 의 event 의 in-memory list 누적.

    실 platform framework 의 의존 없음. tests 의 dispatch + factory + batch
    의무 의 단일 backend.

    Attributes
    ----------
    applied : list[RemoteInput]
        apply() 호출 의 순서 의 event 누적.
    raise_on_apply : bool
        True = apply() 호출 시 RuntimeError raise (실패 시나리오 의 test fixture).
    """

    applied: List[RemoteInput] = field(default_factory=list)
    raise_on_apply: bool = False

    @classmethod
    def is_available(cls) -> bool:
        """mock backend = 항상 가용."""

        return True

    def apply(self, event: RemoteInput) -> None:
        """event 의 누적 list 의 append (raise_on_apply=True 시 RuntimeError)."""

        if self.raise_on_apply:
            raise RuntimeError("MockInputForwardBackend.apply intentional failure")
        self.applied.append(event)

    def reset(self) -> None:
        """누적 list 의 초기화."""

        self.applied.clear()


class MacOSCGEventBackend:
    """macOS CGEvent placeholder — 사이클 58 skeleton.

    실 구현 = PyObjC + Quartz 의 CGEventCreateMouseEvent + CGEventCreateKeyboardEvent.
    본 cycle = framework 부재 + permission 검증 의 graceful degrade.
    별개 cycle 의 실 binding + Accessibility 권한 grant flow 의무.

    메모리 release 의무 (실 binding 단계 의 필수 검토 — 사용자 directive 2026-05-21):

    - ``CGEventCreate*`` 반환 = CFRetain count = 1. 호출 직후 ``CFRelease`` 의무
      또는 ``with objc.autorelease_pool():`` 패턴.
    - ``CGEventSourceCreate`` = process-wide 단일 인스턴스 의무 + ``__del__``
      또는 explicit ``close()`` 의 release.
    - ``apply`` 의 raise 시점 = 부분 생성 의 event 의 release leak 차단 의무
      (try / finally 패턴).
    - tracemalloc + objgraph 의 회귀 검증 (별개 cycle 의 의무).
    """

    @classmethod
    def is_available(cls) -> bool:
        """macOS + PyObjC + Quartz 의 import 가능 여부.

        실 의무 = Accessibility permission grant 의 추가 검증 (macOS Privacy
        의 System Settings 의 Accessibility 의 항목 grant). 본 placeholder =
        import 검증 만.
        """

        if sys.platform != "darwin":
            return False
        try:
            import Quartz  # type: ignore[import]  # noqa: F401
        except ImportError:
            return False
        return True

    def apply(self, event: RemoteInput) -> None:
        """실 apply 미구현 — 별개 cycle 의 PyObjC CGEvent binding 의무."""

        raise NotImplementedError(
            "MacOSCGEventBackend.apply — PyObjC + Quartz CGEvent binding "
            "+ Accessibility permission grant 의 별개 cycle 의무"
        )


def select_input_backend(
    platform_name: Optional[str] = None,
) -> Type[InputForwardBackend]:
    """platform-specific 의 input forward backend class 의 factory.

    Parameters
    ----------
    platform_name : str | None
        "darwin" / "win32" / "linux" / "mock". None = ``sys.platform`` 자동 detect.

    Returns
    -------
    Type[InputForwardBackend]
        backend class. caller 의 instantiate 의무.

    Raises
    ------
    NotImplementedError
        platform 의 실 구현 미존재.
    ValueError
        unknown platform_name.
    """

    name = (platform_name or sys.platform).lower()
    if name == "mock":
        return MockInputForwardBackend  # type: ignore[return-value]
    if name == "darwin":
        return MacOSCGEventBackend  # type: ignore[return-value]
    if name in ("win32", "cygwin"):
        raise NotImplementedError(
            f"{name} input backend 별개 cycle 의무 — Win32 SendInput + ctypes"
        )
    if name == "linux":
        raise NotImplementedError(
            "linux input backend 별개 cycle 의무 — X11 XTestFakeKeyEvent + Xlib"
        )
    raise ValueError(f"unknown platform_name — {name}")


def apply_events(
    backend: InputForwardBackend,
    events: List[RemoteInput],
) -> int:
    """N event 의 backend 의 batch dispatch.

    Parameters
    ----------
    backend : InputForwardBackend
        target backend instance.
    events : list[RemoteInput]
        순서 보장 의 event list (timestamp 정렬 의무 = caller responsibility).

    Returns
    -------
    int
        성공 적용 의 event 갯수. 1 event 실패 시 즉시 중단 + 누적 카운트 반환.

    Notes
    -----
    fail-fast 패턴 — 1 event 실패 = 후속 event 차단. caller 의 partial-success
    의 결정 의무 (예: 부분 적용 후 retry 또는 grant revoke).
    """

    succeeded = 0
    for event in events:
        try:
            backend.apply(event)
        except Exception:  # noqa: BLE001 — caller 의 결정 의무 + fail-fast
            return succeeded
        succeeded += 1
    return succeeded


def filter_events_by_type(
    events: List[RemoteInput],
    event_type: InputEventType,
) -> List[RemoteInput]:
    """특정 event_type 의 event 만 추출 — caller 의 select dispatch 의무.

    Parameters
    ----------
    events : list[RemoteInput]
        input list.
    event_type : InputEventType
        filter target type.

    Returns
    -------
    list[RemoteInput]
        filter 결과. 입력 순서 유지.
    """

    return [e for e in events if e.event_type == event_type]
