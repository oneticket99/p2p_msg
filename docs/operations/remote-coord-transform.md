---
title: "Remote Coord Transform — sender ↔ target 화면 해상도 + DPI 좌표 보정 (cycle 148)"
owner: oneticket99
last_verified: 2026-05-19T20:00:00+09:00
status: skeleton
cycle: 148
---


> TooTalk Phase 5 원격 제어 (cycle 166~180) prerequisite 문서.
> 정합: `app/remote/coord_transform.py` · `tests/app/remote/test_coord_transform.py` · memory `project_phase2_remote_control_differentiator.md` · 사용자 directive 2026-05-19 "원격에서 시에 나의 화면 해상도와 상대방의 화면 해상도 비율을 계산해서 마우스좌표의 보정이 필요할꺼야".

본 문서는 controller (sender) 의 view 안 mouse 좌표 → target OS 의 절대 좌표 변환 chain 의 skeleton 사양이다. 실 NSScreen / win32 GetDpiForWindow / mouse event dispatch = Phase 5 cycle 166~180 의 별개 cycle 의무.

---

## 1. 개요 — 왜 좌표 보정이 필요한가

원격 제어 시나리오에서 controller 의 mouse 가 target 의 OS 의 마우스 좌표로 적용되려면 양쪽 화면 의 다음 4 종 의 mismatch 를 보정해야 한다.

- 해상도 (1920x1080 ↔ 2560x1440 ↔ 3840x2160 ↔ ...)
- aspect ratio (16:9 ↔ 4:3 ↔ 16:10 ↔ 21:9 ultrawide)
- Windows DPI awareness (96 / 120 / 144 / 168 = 100% / 125% / 150% / 175% scaling)
- macOS Retina backing_scale (1.0 / 2.0 / 3.0 의 logical pixel ↔ physical pixel 비율)

보정 부재 시 controller 의 mouse 좌표 (예: (960, 540) 정중앙) 가 target 의 (960, 540) 으로 적용 → target 화면 의 비례 위치 와 불일치. 사용자 의도 의 click / drag 의 의 실패.

## 2. RemoteScreenInfo schema

`app/remote/coord_transform.py` 의 frozen dataclass.

| 필드 | 형 | 의미 | 출처 |
| --- | --- | --- | --- |
| `width` | int | physical pixel 가로 (backing scale 반영) | macOS: NSScreen.frame.size.width \* backingScaleFactor / Windows: GetSystemMetrics(SM_CXSCREEN) |
| `height` | int | physical pixel 세로 | (위 등가) |
| `logical_width` | int | CSS pixel 가로. macOS backing 1x 시 physical 등가. | NSScreen.frame.size.width / Windows: 통상 physical 등가 |
| `logical_height` | int | CSS pixel 세로 | (위 등가) |
| `dpi` | int | Windows DPI awareness (96=100% / 120=125% / 144=150% / 168=175%) | GetDpiForWindow / QScreen.logicalDotsPerInch |
| `backing_scale` | float | macOS Retina backing scale (1.0 / 2.0 / 3.0) | NSScreen.backingScaleFactor / QScreen.devicePixelRatio |
| `primary_monitor_index` | int | multi-monitor 시 primary index. 본 cycle = 0 단일 monitor 가정. | NSScreen.screens[0] / EnumDisplayMonitors[0] |

invariant — 음수 차단 + dpi / backing_scale 양수 의무 (`__post_init__` 검증).

## 3. 비례 scaling 공식

aspect ratio 일치 시 (또는 STRETCH 정책) — 직접 비례 scaling.

```
target_x = sender_x * target.width / sender.width
target_y = sender_y * target.height / sender.height
```

예시 — 1920x1080 → 2560x1440 (양쪽 16:9):

- sender_x = 960 → target_x = 960 × 2560 / 1920 = 1280
- sender_y = 540 → target_y = 540 × 1440 / 1080 = 720

aspect 차이 < 0.001 시 동일 의 처리. 이상 시 §4 의 정책 분기.

## 4. Aspect ratio 정책 3 종

### 4-1. LETTERBOX (default) — 검은 띠 + 가운데 정렬

sender 화면 비율 보존. target 안 sender 비례 의 max scale + 상하 또는 좌우 검은 띠.

- sender wider (16:9 → 4:3 target) → 상하 검은 띠. scale = target.width / sender.width.
- sender taller (4:3 → 16:9 target) → 좌우 검은 띠. scale = target.height / sender.height.

예시 — 1920x1080 sender → 1024x768 target (sender wider):

- scale = 1024 / 1920 ≈ 0.5333
- scaled_height = 1080 × 0.5333 ≈ 576
- offset_y = (768 − 576) / 2 = 96
- sender_x = 960, sender_y = 540 → target_x = 512, target_y = 96 + 287 = 383

### 4-2. STRETCH — 왜곡 허용 + 전체 화면 사용

aspect 차이 무시 + 직접 비례. target 화면 전체 활용 의 대가로 화면 왜곡.

게임 / 영상 시청 외 일반 데스크탑 제어 = LETTERBOX 권장.

### 4-3. CROP — sender 중앙 영역만 target 표시

target aspect 와 일치하는 sender 의 중앙 영역만 표시. 영역 외 sender 좌표 → `(-1, -1)` 반환 → dispatch skip 신호.

예시 — 1920x1080 sender → 1024x768 target (sender wider, crop):

- scale = 768 / 1080 ≈ 0.7111
- crop_width = 1024 / 0.7111 ≈ 1440
- offset_x = (1920 − 1440) / 2 = 240
- sender_x = 100 (영역 240~1680 외) → `(-1, -1)`

## 5. DPI / Retina 정합

### 5-1. Windows DPI 보정

target.dpi != 96 시 `dpi_scale = target.dpi / 96` 의 추가 multiplier 적용 후 경계 cap.

- DPI 96 = 100% scaling (base)
- DPI 120 = 125% scaling
- DPI 144 = 150% scaling
- DPI 168 = 175% scaling

본 cycle skeleton = uniform DPI scaling. fractional scaling (Windows 150% / Linux Wayland sub-pixel) = 별개 cycle.

### 5-2. macOS Retina 정합

macOS Retina backing_scale 2.0 시 NSScreen.frame.size 의 logical pixel × 2 = physical pixel.

- MBP 13" Retina = logical 1280x800 / physical 2560x1600 / backing 2.0
- iMac 5K = logical 2560x1440 / physical 5120x2880 / backing 2.0
- Studio Display = logical 2560x1440 / physical 5120x2880 / backing 2.0

`build_local_screen_info` 함수 = `QScreen.size() * QScreen.devicePixelRatio()` 의 physical pixel 자동 산정.

## 6. WebRTC DataChannel payload schema

원격 세션 설립 시 양쪽 의 `RemoteScreenInfo` 교환 의무. payload schema (JSON serialize 기준):

```json
{
  "type": "screen_info",
  "screen": {
    "width": 1920,
    "height": 1080,
    "logical_width": 1920,
    "logical_height": 1080,
    "dpi": 96,
    "backing_scale": 1.0,
    "primary_monitor_index": 0
  }
}
```

dispatch 순서:

1. Permission grant 직후 양쪽 의 `build_local_screen_info()` 결과 직렬화 + DataChannel 교환.
2. controller 가 target.RemoteScreenInfo 보관.
3. controller 의 mouse move event → `transform_coordinates(controller_info, target_info, x, y, policy)` 변환.
4. 변환 결과 = (-1, -1) 시 dispatch skip (CROP 영역 외). 외 시 `RemoteInput` envelope 으로 target 송신.
5. target 의 `input_forward.apply()` = OS 의 mouse event dispatch (Phase 5 cycle 166~180).

monitor 변경 / DPI 변경 / resolution 변경 시 양쪽 의 `RemoteScreenInfo` 재교환 의무. polling 부재 = QScreen.geometryChanged signal 의 추적 별개 cycle.

---

## 본 cycle 의 범위 외 (Phase 5 cycle 166~180 의무)

- 실 NSScreen / win32 GetDpiForWindow / X11 XRandR 직접 호출 (PyQt6 graceful only).
- 실 mouse event dispatch (CGEventCreateMouseEvent / SendInput / XTestFakeMotionEvent).
- multi-monitor span + monitor 별 DPI 개별 처리.
- fractional scaling sub-pixel 정합 (Windows 150% / Wayland scale_factor).
- monitor 변경 / DPI 변경 dynamic 추적 (QScreen.geometryChanged signal).
- DataChannel screen_info 교환 의 wire protocol envelope + ack.

## 참조

- `app/remote/coord_transform.py` — 본 cycle skeleton 정본
- `tests/app/remote/test_coord_transform.py` — 20 case 회귀
- `app/remote/protocol.py` — `RemoteFrame` + `RemoteInput` + `RemoteSession` 의 wire format
- `app/remote/input_forward.py` — Phase 3 input forward graceful (cycle 55)
- memory `project_phase2_remote_control_differentiator.md` — Phase 3 막바지 원격 제어 차별화 directive
