---
title: "session handoff — cycle 169.852 manifest (avatar 이미지 picker M3 재개)"
owner: oneticket99
last_verified: 2026-05-26T20:40:00+09:00
status: active
---

# Session Handoff — cycle 169.852 (2026-05-26)

> 본 doc = 다음 session 진입 첫 액션 manifest. **진행 중 핵심 작업 = avatar 이미지 picker (텔레그램 정합) — M1+M2 서버 영속 완결, M3~M7 클라 잔존.** 직전 handoff [2026-05-26-session-handoff-cycle169.850.md](2026-05-26-session-handoff-cycle169.850.md) 후속(잔존작업 batch + coverage 2차 + avatar feature 착수로 소비됨).

---

## 1. 30초 TL;DR

본 session = 다수 directive 처리 후 **avatar 이미지 picker 기능 착수**(사용자 directive — 그룹/채널/프로필 3곳 아바타 클릭 → 파일/카메라/클립보드 드롭다운, 이모지 제외, 서버 영속, 이미지 미설정 시 2글자 이니셜 fallback).

| cycle | 작업 | commit |
|---|---|---|
| 169.851 | 잔존작업 batch(i18n dangling §8-5 + token-usage 재산출 + active-plan archive) + 평가 sweep | b21f57f~f7c0bca |
| 169.851 | coverage omit 축소 2차 — `app/updater` 68→97% | 9130497 |
| 169.852 | **avatar Exec Plan 신설** (planning-agent, 14 섹션 M1~M7+G-final) | 5a3bc9f |
| 169.852 | **avatar M1** — migration 0018 `users.avatar_ref` + `avatars.py` repo(디스크/sha256/traversal) + `users.py` | 3a62963 |
| 169.852 | **avatar M2** — POST/GET/PATCH endpoint(multipart+Pillow 512 crop+EXIF strip) + rooms avatar_ref + route 등록 | 21bd680 |
| 169.852 | 평가 sweep(avatar M1/M2) | cd50dc3 |
| 169.852 | **avatar M3** — `AvatarPickerButton`(드롭다운 파일/카메라/클립보드, 이모지 제외 + 원형 preview + 이니셜/camera fallback) + `avatars_client` QThread worker 3종 + camera/image SVG. 17 PASS, reviewer PASS | 6a86ce6 |
| 169.852 | `RoomsClient.create_room` avatar_ref/description param(서버 M2 수용 결선) | 0bead04 |
| 169.852 | **avatar M4 서버 chain e2e** — room create avatar_ref + invite isolated e2e 보강(18 PASS, 사용자 directive) | cadfa2c |
| 169.852 | codex §4.6 **하드코딩 수렴** — demo IP routing literal 8 파일 → `config.DEMO_FALLBACK_API_BASE` 단일 + scan gate. reviewer PASS | dc3ccc3 |
| 169.852 | **한글 주석 보강 별도 페이즈 Exec Plan**(planning-agent, draft) | 86e3361 |
| 169.852 | Codex 문서 batch 취합(current-project-review + token-usage 5/24~26 필터 + ledger) — dirty 해소 | 4563f47 |

또한 본 session: productization.html 빈 화면 회귀 회수(cycle 849 sweep `-->` 드롭), 로컬 stale 빌드 재빌드(메뉴 토글 버그 = stale 빌드 확정, cycle 835 fix), M6 WBS resume(850/851/852 row).

핵심 milestone:

- **avatar M1~M3 완결 + M4 서버측 완결.** M1+M2 서버 영속(migration 0018 + avatars repo + POST/GET/PATCH endpoint), M3 클라 `AvatarPickerButton`+`avatars_client`(파일/클립보드 동작, 카메라는 `camera_requested` signal M5 연결 대기), M4 서버 room create(avatar_ref/name) + invite isolated e2e 완비. **잔존 = M4 클라 dialog 통합(T-11~T-13) + M5 카메라 + M6 표시 전파 + M7 문서 + G-final.**
- **codex §4.6 하드코딩 수렴**(demo IP routing literal 단일 config) + scan gate CI lock. 잔여 §4.6 = stun/OAuth redirect/bot sender id(후속 분리).
- **한글 주석 보강 별도 페이즈 Exec Plan**(`2026-05-26-korean-comment-enrichment-phase.md`, draft) — 사용자 directive, active 전환 GO 대기.

main HEAD = `4563f47` (cycle 169.852). 점수 productization 7.6/10 · vibe-coding 8.4/10 유지. tree clean.

> **사용자 directive 2026-05-26 (유효)**: avatar 이미지 picker **전체 구현 완주** + group/channel **서버 room 생성도 지금 결선**(사용자 확정 — client placeholder gid → 실 POST /api/rooms 승격). 스킵/조기중단 없이 G-final 까지.
> **진척 업데이트**: M1~M3 + M4 서버측(create avatar_ref/invite e2e) 완결. **다음 1번 = M4 클라 dialog 통합(T-11 group → T-12 channel → T-13 profile)**. M1~M3/M4서버 재작업 불요. §3 순서대로.

---

## 2. 첫 응답 템플릿 (다음 session 진입)

```text
이전 session handoff (cycle 169.852) 정독 완료. avatar 이미지 picker M1~M3 + M4
서버측(room create avatar_ref + invite e2e) 완결. main HEAD 4563f47. 사용자 "전체
구현 + group/channel 서버 room 생성도 지금 결선" 승인 유효.

본 session 진입 우선순위 (avatar Exec Plan 순차, M4 클라부터):
1. M4 클라 dialog 통합 (서버 room 생성 결선 포함):
   - new_group_dialog/new_channel_dialog: camera_btn → AvatarPickerButton +
     _drawer_mixin._on_group_created/_on_channel_created 를 음수 gid placeholder →
     실 RoomsClient.create_room(name,kind,avatar_ref) + invite_user(멤버) 결선(qasync
     ensure_future 패턴, _invite_mixin:81 참조). avatar 선택 시 AvatarUploadWorker →
     avatar_ref → create_room. channel dialog icon 오용(notification) 시정.
   - my_profile_dialog: AvatarPickerButton + AvatarUploadWorker → AvatarPatchMeWorker
     (PATCH /api/me/avatar). 독립(서버 PATCH 경로 완비) — 병렬 가능.
2. M5 — _camera_capture_dialog.py(QtMultimedia in-app 모달) + AvatarPickerButton
   camera_requested signal 연결 + 권한 거부 graceful + resource release.
3. M6 — _avatar_helper.make_avatar_pixmap(name, avatar_ref) + 6곳 표시 전파(이니셜 fallback 무손상).
4. M7 — 문서 동기 + 회귀 → G-final 사용자 visual ack.

각 마일스톤 reviewer 게이트 + 즉시 commit/push. Exec Plan T-11~T-18 정본.
부수 잔존: 한글 주석 보강 페이즈(draft, active GO 대기) / codex §4.6 잔여(stun/OAuth/bot sender).
```

---

## 3. 잔존 task — avatar M3~M7 (Exec Plan T-8~T-18 정본)

> 정본 = [2026-05-26-avatar-image-picker-upload.md](2026-05-26-avatar-image-picker-upload.md) §5 마일스톤 + §6 Task + §8 결정 로그.

### 3-1. ✅ M3 — AvatarPickerButton 공유 컴포넌트 (T-8~T-10, 완결 6a86ce6)

- `app/ui/_avatar_picker_button.py`(드롭다운 파일/카메라/클립보드, 이모지 제외 + 정사각 crop 원형 preview + 이니셜/camera fallback + `avatar_selected(QImage)`/`camera_requested()` signal + `to_bytes()`) + `app/net/avatars_client.py`(QThread worker — **httpx 아님, account_client 컨벤션** AvatarUploadWorker multipart / AvatarFetchWorker / AvatarPatchMeWorker + `qimage_to_bytes`) + camera/image SVG. 17 PASS, reviewer 차단 0.

### 3-2. M4 — 3 dialog 통합 + 서버 room 생성 결선 (T-11~T-13)

- **서버측 ✅** (cadfa2c): `RoomsClient.create_room` avatar_ref/description param(0bead04) + room create avatar_ref + invite endpoint isolated e2e 18 PASS.
- **클라 잔여** (다음 1번):
  - `new_group_dialog.py:93`·`new_channel_dialog.py:91` camera_btn → `AvatarPickerButton` + `_drawer_mixin._on_group_created`/`_on_channel_created` 의 음수 gid placeholder(`gid=-abs(hash...)`) → **실 `RoomsClient.create_room(name,kind,avatar_ref)` + `invite_user(멤버)` 결선**(사용자 "서버 room 생성도 지금" 확정). qasync `asyncio.ensure_future` 패턴(`_invite_mixin.py:81` 참조). avatar 선택 시 `AvatarUploadWorker` → avatar_ref → create_room. channel dialog icon 오용(notification) 시정.
  - `my_profile_dialog.py` AvatarPickerButton + `AvatarUploadWorker` → `AvatarPatchMeWorker`(PATCH /api/me/avatar). 서버 PATCH 경로 완비 → 독립, **group/channel 과 병렬 가능**.

### 3-3. M5 — CameraCaptureDialog (T-14~T-15, 고위험)

- `app/ui/_camera_capture_dialog.py` 신설 — QtMultimedia(QCamera/QImageCapture/QMediaCaptureSession) in-app 모달(FRONTEND.md §16 `_exec_dialog_centered` 정합). live preview(QVideoWidget) + 촬영 button → QImage. 권한 거부 graceful(toast + 다른 2항목 정상) + **camera resource release 의무**(feedback_objc_memory_release_mandatory — setActive(False)/deleteLater + tracemalloc 회귀). Info.plist NSCameraUsageDescription 이미 declared.
- 검증: offscreen + QImageCapture.imageCaptured 가짜 frame mock + 권한 거부 분기.

### 3-4. M6 — 표시 전파 6곳 (T-16~T-17)

- `app/ui/_avatar_helper.make_avatar_pixmap(name, avatar_ref=None, size)` 단일 진입 신설 — avatar_ref 있으면 GET /api/avatars 이미지 load + 원형 crop, 없으면 기존 `make_initial_pixmap` 이니셜 fallback(무손상). directive 명시 6곳 전파: chat sender / drawer header / profile / group / channel / member_list. (나머지 5곳 fallback 유지 = TD-3.)

### 3-5. M7 + G-final (T-18)

- 문서 동기: Structure / FRONTEND §16(picker 항목 + 모달) / ARCHITECTURE §6(avatar 파이프라인) / CheckList + 평가 2 + HTML 2. 회귀 전량 GREEN.
- **G-final 사용자 visual ack** — 실 webcam 촬영 + 3 dialog 원형 아바타 + 서버 영속 round-trip(headless 대체 불가).

### 3-6. (비차단) 후속 — Exec Plan OBS/TD

- OBS-1/2: create_room 응답 description + `_room_row_to_wire` avatar_ref surface(M6 표시 전파 시).
- TD-1 S3 전환(repository layer), TD-5 디스크 orphan GC(주 1회 sweep).
- B-4: 그룹 avatar **수정** 경로 = 2026-05-25-telegram-group-management PATCH /api/rooms/{id} 의존 — 미완 시 생성 시 avatar_ref 만 우선.

---

## 4. 활성 가드레일/directive (본 session 정합)

- **사용자 "GO 전체 구현" 승인 유효** — avatar Exec Plan M1~M7 전체 진행 승인됨(카메라 포함, 서버 업로드 포함). 각 마일스톤 reviewer 게이트 + 즉시 push.
- **큰 작업 = M1 문서 선행 의무** — planning-agent Exec Plan 후 ② 개발. avatar feature 가 본 패턴 사례(planning → M1 → M2 …).
- **서버 write 선행 원칙** — 클라가 회신받을 계약(avatar_ref REST) 선존 후 클라 결선.
- **단계별 reviewer 게이트** — feat commit 마다 reviewer→(qa→observability). avatar M1/M2 PASS.
- **평가 staleness 5 commit 임계** — productization/vibe-coding + HTML mirror 동시 sweep + cycle marker. 본 session 169.851/852 2회 sweep.
- **HTML 주석 무결성** — marker `<!-- -->` 중첩 불가, 닫는 `-->` 드롭 시 빈 화면. `grep -oc '<!--' / '-->'` 개수 일치 점검(cycle 849 회귀 교훈).
- **공유 working dir + 병렬 Codex** — git fetch + status 선행. commit Codex / push Claude 분담 가능.
- **dereliction-detector 자동 spawn** — 작업 완료 보고 직후.
- **로컬 빌드 = stale 주의** — 사용자 dogfooding 빌드는 재빌드 필수(`scripts/build.sh macos`). 메뉴/UI 버그 진단 시 현 코드 vs 빌드 시점 먼저 대조.

---

## 5. 직접 진입 명령

```bash
cd /Users/oneticket_toonation/Documents/vscode_work/p2p_msg && git fetch origin main && git log --oneline -6 && git status -sb

# avatar Exec Plan 정독 (정본)
sed -n '150,215p' docs/exec-plans/active/2026-05-26-avatar-image-picker-upload.md

# M3 착수점 — 현 camera_btn (3 dialog) + 재사용 이니셜 helper
sed -n '90,101p' app/ui/new_group_dialog.py
grep -n 'make_initial_pixmap\|make_avatar_pixmap' app/ui/_avatar_helper.py

# 서버 계약 확인 (M2 완결 — 클라가 호출)
sed -n '1,30p' server/api/avatars_handlers.py

# 회귀 baseline + avatar 서버 test
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/app tests/server -q
QT_QPA_PLATFORM=offscreen python3 -m pytest tests/integration/test_avatars_handlers_e2e.py -m integration -o addopts="" -q
```

---

## 6. 참조

- avatar Exec Plan(정본): [2026-05-26-avatar-image-picker-upload.md](2026-05-26-avatar-image-picker-upload.md) — §4 REST 계약 · §5 M3~M7 · §6 T-8~T-18 · §8 결정 D-1~D-8
- 서버 구현(M1+M2): `server/db/migrations/0018_user_avatar_field.sql` · `server/db/repositories/avatars.py` · `server/api/avatars_handlers.py` · `tests/server/test_avatars_repo.py` · `tests/integration/test_avatars_handlers_e2e.py`
- 재사용 자산: `app/ui/_avatar_helper.py`(이니셜 fallback) · FRONTEND.md §16(in-app 모달)
- 직전 handoff: [2026-05-26-session-handoff-cycle169.850.md](2026-05-26-session-handoff-cycle169.850.md)
- 평가 snapshot: [productization](../../assessments/productization.md) 7.6/10 · [vibe-coding](../../assessments/vibe-coding.md) 8.4/10 (cycle 169.852 동기)
- 가드레일 인덱스: `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/MEMORY.md`

---

마지막 갱신: 2026-05-26 (cycle 169.852 — avatar M1~M3 + M4 서버측 완결 + 하드코딩 수렴 + 주석 plan + Codex 취합 반영, 다음 = M4 클라 dialog 통합 manifest)
