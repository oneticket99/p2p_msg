---
title: "Remote Control prerequisite — Phase 5 cycle 166~180 screen capture + input dispatch skeleton (cycle 150)"
owner: oneticket99
last_verified: 2026-05-19T21:00:00+09:00
status: skeleton
cycle: 150
---


> TooTalk Phase 5 Item 5 원격 제어 (cycle 166~180) prerequisite 문서.
> 정합: `app/remote/screen_capture.py` · `app/remote/input_dispatch.py` ·
> `tests/app/remote/test_screen_capture.py` · `tests/app/remote/test_input_dispatch.py` ·
> memory `project_phase2_remote_control_differentiator.md` ·
> memory `feedback_objc_memory_release_mandatory.md` ·
> 사용자 directive 2026-05-21 "objc 관련해서 메모리 사용 완료시 release 했는지 체크해".

본 문서는 Phase 5 cycle 166~180 의 원격 제어 본격 binding 진입 전 의 screen capture +
input dispatch 의 3 OS 분기 skeleton 의 사양 + 메모리 release 의무 + 권한 chain 요약이다.
실 PyObjC / win32 / Xlib binding = Phase 5 본격 cycle 의 별개 cycle 의무.

---

## 1. 개요 — 왜 별도 skeleton 인가

cycle 132 의 REMOTE 3 ENUM wiring + cycle 148 의 coord transform chain 이 controller →
target 의 좌표 변환 layer 를 완성했다. 본 cycle 150 = OS-specific framework binding
의 layer 의 사전 격리 + graceful import + CFRelease chain 패턴 의 명문화.

- cycle 57 의 `app/remote/capture.py` = 단일 OS (macOS) placeholder + Mock + factory.
- cycle 58 의 `app/remote/input_forward.py` = 단일 OS (macOS) placeholder + Mock + factory.
- cycle 150 의 `app/remote/screen_capture.py` + `input_dispatch.py` = **3 OS 분기 동시
  skeleton** + graceful import + CFRelease chain 의 try / finally 패턴 의 명문화.

본 cycle 150 + cycle 57 / 58 의 차이 = 본격 binding 진입 전 의 3 OS 동시 발판.
중복 차단 = Phase 5 cycle 166 진입 시점 의 양쪽 module 의 통합 의 별개 cycle 의무.

---

## 2. 3 OS 분기 framework

| OS | screen capture | input dispatch | 권한 / permission |
| --- | --- | --- | --- |
| macOS | Quartz `CGDisplayCreateImage` + CFRelease | Quartz `CGEventCreateMouseEvent` + `CGEventPost` + CFRelease | Screen Recording + Accessibility (System Preferences > Privacy & Security) |
| Windows | `GetDC` + `BitBlt` + `GetDIBits` + `ReleaseDC` | user32 `SendInput` (INPUT_MOUSE + INPUT_KEYBOARD) | UIPI / UAC integrity level (target ≤ sender 의무) |
| Linux X11 | Xlib `XGetImage` | Xlib + XTest `XTestFakeMotionEvent` + `XTestFakeButtonEvent` + `XTestFakeKeyEvent` | X11 session 의 DISPLAY + XAuthority |
| Linux Wayland | `screencopy-unstable-v1` (별개 cycle) | libinput + Wayland virtual input (별개 cycle) | compositor-specific (sway / GNOME / KDE 별개) |

## 3. 메모리 release 의무 (PyObjC + Quartz Core)

memory `feedback_objc_memory_release_mandatory.md` 영구화 (사용자 directive 2026-05-21).

### 3.1 screen capture

- `CGDisplayCreateImage` 반환 = CGImageRef CFRetain count = 1.
- `CGImageGetDataProvider` + `CGDataProviderCopyData` 의 결과 = CFData = 추가 release 의무.
- 1 frame leak = 60 fps × 1080p RGB ≈ 분당 1.3 GB 누수.
- `with objc.autorelease_pool():` 패턴 의 sequential capture loop 의 의무.

### 3.2 input dispatch

- `CGEventCreateMouseEvent` / `CGEventCreateKeyboardEvent` 반환 = CGEvent CFRetain count = 1.
- `CGEventPost` 직후 `CFRelease` 의무.
- `CGEventSourceCreate` = process-wide 1회 만 + `__del__` finalizer 의 release.

### 3.3 Win32 GDI handle

- `GetDC(0)` = HDC. `ReleaseDC(0, hdc)` 의무.
- `CreateCompatibleDC` = HDC. `DeleteDC` 의무.
- `CreateCompatibleBitmap` = HBITMAP. `DeleteObject` 의무.
- try / finally chain 의 GDI handle leak 차단 의무.

### 3.4 X11 Display handle

- `Xlib.display.Display()` = process-wide single + finalizer 의 close 의무.
- XImage 의 frame buffer = `free()` 의무 (Xlib python binding 의 자동 처리 검증 필요).

---

## 4. Phase 5 cycle 166~180 의 진입 의무 checklist

- [ ] `app/remote/screen_capture.py` 의 macOS CFRelease chain 의 actual CFData extract 완성
- [ ] `app/remote/screen_capture.py` 의 Windows BitBlt + GetDIBits ctypes binding 완성
- [ ] `app/remote/screen_capture.py` 의 Linux Xlib XGetImage + buffer marshal 완성
- [ ] `app/remote/input_dispatch.py` 의 macOS CGEventCreate* + CFRelease chain 완성
- [ ] `app/remote/input_dispatch.py` 의 Windows SendInput ctypes binding 완성
- [ ] `app/remote/input_dispatch.py` 의 Linux XTest binding 완성
- [ ] cycle 57 / 58 의 `capture.py` / `input_forward.py` 의 통합 또는 deprecation 결정
- [ ] tracemalloc + objgraph 의 회귀 검증 의 별개 cycle (60 fps × 1 hour 의 RSS plateau)
- [ ] macOS Accessibility + Screen Recording permission grant flow UI
- [ ] Windows UIPI / UAC elevation 의 SendInput 권한 chain

## 5. 본 cycle 150 의 범위 외

- 실 PyObjC / win32 / Xlib binding 의 actual pixel + event dispatch
- multi-monitor 의 monitor_index dispatch 의 OS API binding
- frame rate throttle + ABR encoding (raw → png / jpeg / h264)
- modifier key stateful tracking (shift down → A 입력 → shift up 의 순서 의무)
- cursor overlay (Pattern A 의 도움 시각화)
- HiDPI / Retina backing scale 의 coord_transform 연계
- Wayland 의 screencopy + libinput 의 별개 protocol 의 별개 cycle

## 6. 참조

- `app/remote/screen_capture.py` (cycle 150)
- `app/remote/input_dispatch.py` (cycle 150)
- `app/remote/capture.py` (cycle 57)
- `app/remote/input_forward.py` (cycle 58)
- `app/remote/coord_transform.py` (cycle 148)
- `docs/operations/remote-coord-transform.md` (cycle 148)
- memory `feedback_objc_memory_release_mandatory.md`
- memory `project_phase2_remote_control_differentiator.md`
- memory `project_phase5_mobile_last.md`
