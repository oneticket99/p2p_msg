---
title: "TooTalk 현재 프로젝트 전면평가"
owner: oneticket99
last_verified: 2026-05-26T08:15:00+09:00
status: active
---

# TooTalk 현재 프로젝트 전면평가

> 검토 기준: 2026-05-26 cycle 169.839 main branch (`b84ca51`) + 로컬 문서 산출 cycle 169.840 진행 상태 + 본 평가 갱신 commit cycle 169.841. 169.838 전 dialog in-app overlay 모달 변환, "방 입장" 제거, GroupChatView 중복 헤더 정리, 169.839 group-flow isolated test 재구성, 169.840 token usage 재산출 변경을 기준으로 재평가했다.
> 목적: 다음 작업 세션에서 곧바로 우선순위를 잡을 수 있는 협업용 평가 snapshot.
> 핵심 판정: 내부 dogfooding 후보권은 유지한다. 외부 사용자 배포 직전 단계는 아니다. 최신성 게이트, 배포 산출물 실행 증거, 핵심 UI/RTC 실효 커버리지가 남은 차이다.

## 1. 종합 판정

**현재 점수: 7.7 / 10**

TooTalk 는 PyQt6 클라이언트, aiohttp signaling, aiortc DataChannel/SFU, MariaDB schema, bot/i18n/remote-control 기반, CI/문서 가드레일이 실제 파일과 자동 테스트로 누적된 프로젝트다. 최근 cycle 169.834~839 에서 dogfooding 버그, 그룹 멤버 UX, in-app overlay modal, 방번호 직접 입력 폐지, group-flow test 재구성까지 이어져 사용자 흐름은 더 단순해졌다.

점수는 직전 7.8 에서 **7.7** 로 보수 조정한다. 구현량과 자동검증 규모는 강하지만, 평가 문서 stale 로 `assessment-consistency` 가 실패했던 사실, coverage omit 범위가 넓은 사실, macOS/Windows 산출물 실행 증거와 원격 데스크탑/SFU 실 기기 검증이 부족한 사실을 반영했다. 제품 단계 표현은 **내부 dogfooding 후보 + 배포/실기기 검증 대기**가 가장 정확하다.

## 2. 최신 검증 결과

2026-05-26 08:15 KST 기준 로컬 확인 결과.

- `git status -sb`: `main...origin/main`, 단 token usage 산출물 + README/History 작업 중 변경 존재.
- `git log --oneline -5`: HEAD `b84ca51 test(cycle169.839): group-flow isolated test 재구성`.
- `.venv/bin/python tools/md_agents.py`: PASS (`M3 history`, `M2 readme`, `root freeze`).
- `bash tools/doc-lint.sh`: PASS, 77개 markdown 위반 0건.
- `.venv/bin/python tools/check_migration_tables.py --strict`: PASS, SQL 25개 = 문서 25개.
- `.venv/bin/python -m pytest -q`: `2557 passed, 24 skipped, 327 deselected`.
- `.venv/bin/python -m pytest --cov -q`: `2557 passed, 24 skipped, 327 deselected`, coverage `87.99%`.
- `.venv/bin/python tools/check_assessment_consistency.py`: 재평가 전 FAIL, 원인 = `current-project-review.md` 최신 cycle 169.839 누락.

주의점.

- 샌드박스 제한 환경에서는 aiohttp test server 의 `127.0.0.1:0` bind 가 `PermissionError` 로 실패했다. 제한 없는 로컬 실행에서는 통과했다.
- coverage 87.99% 는 `pyproject.toml` omit 범위가 넓은 조건의 수치다. UI dialog, RTC peer/file, remote capture/input, 여러 REST handler 가 측정에서 빠져 있다.
- coverage 실행 후 `sqlite3.Connection` 미종료 `ResourceWarning` 이 1건 남는다.

## 3. 최근 구현 진척

### 3.1 Group flow canonical 정리

cycle 169.838 에서 "방 입장" 메뉴와 Room ID 직접 입력 흐름을 제거했고, 그룹방은 그룹 만들기 + 초대 구조로 정리했다. cycle 169.839 에서 `tests/app/ui/test_main_window_rooms.py` 를 구 `room_entered.emit(N)` 직접 호출 방식에서 그룹 만들기 wizard chain 으로 재구성했다.

판정: **IMPLEMENTED.** 통합 ChatView 를 canonical widget 으로 삼는 방향이 맞다. 다만 `GroupChatView`, `room_entered`, `RoomListWidget`, server room broadcast 잔존 경로는 단순 dead code 가 아니라 legacy feature path 이므로, 제거보다 **전체 마이그레이션** scope 로 다루는 편이 안전하다.

### 3.2 In-app overlay modal 전환

cycle 169.838 에서 거의 모든 dialog 를 별도 OS window 에서 메인 레이아웃 내부 modal 흐름으로 바꿨다. 원격제어 상대 화면 창만 별도 window 예외로 남긴다. `_exec_dialog_centered` 와 `_modal_helper.exec_modal` 이 nested dialog 위임과 headless test guard 를 담당한다.

판정: **IMPLEMENTED.** UX 방향은 선명해졌지만 overlay 체계는 UI 결합도가 높으므로 full-instantiation test 보다 isolated logic + offscreen smoke + 수동 visual ack 조합이 현실적이다.

### 3.3 음성/영상 SFU 그룹 통화

cycle 169.794~810 에서 server `SfuRoom`/`SfuRegistry`, protocol/signaling SFU message, client `SfuCallClient`, `GroupCallDialog`, `SfuCallMixin`, MainWindow entry 까지 종단 코드가 완결됐다. cycle 169.826~828 에서 aiortc optional import 와 requirements 반영으로 데모 서버 crash loop 위험도 회수했다.

판정: **IMPLEMENTED, VERIFIED 아님.** `app/net/sfu_call_client.py` coverage 가 14.39%, `server/sfu_room.py` coverage 가 49.48% 라서 실 OS 미디어 캡처/다중 화면 visual ack 전에는 제품 검증 완료로 올리면 안 된다.

### 3.4 원격 데스크탑

remote protocol, permission, coord transform, session runner, handshake, loopback test 는 갖춰졌다. 다만 실제 friend peer path 에서 `_remote_data_channel` 생성, host permission grant 주입, Screen Recording/Accessibility 권한, frame/input/control close/revoke 수명 관리는 아직 얇다.

판정: **PARTIAL.** 자동 테스트만으로는 부족하며 M4 실 OS 수동 검증이 필요하다.

### 3.5 DB/MIGRATION 정합

`MIGRATION_MARIADB.md` 와 `server/db/migrations` 는 strict 기준 SQL 25개 = 문서 25개로 맞다. cycle 169.821 의 `0017_group_roles_meta.sql` 은 owner/admin/member role + rooms group meta foundation 을 제공한다.

판정: **IMPLEMENTED.** 신규 migration 추가 때 `tools/check_migration_tables.py --strict` 를 계속 머지 게이트로 유지해야 한다.

## 4. 주요 리스크

### 4.1 평가 snapshot stale 재발

`check_assessment_consistency.py` 는 HEAD cycle marker 가 `current-project-review.md` 에 없으면 실패한다. 이번 재평가 직전 상태가 바로 이 실패였다. 평가 문서는 기능 완료 뒤 따라붙는 보조 문서가 아니라 CI 차단 자원이다.

대응: 기능/테스트 commit 뒤 current-project-review 의 검토 기준과 최신 검증 결과를 같은 cycle 에 갱신한다.

### 4.2 Coverage 신뢰도 착시

총 coverage 87.99% 는 나쁘지 않지만 `pyproject.toml` omit 이 넓다. 특히 UI core, RTC peer/file path, remote OS backend, 여러 REST handler 가 실제 측정에서 빠졌다. 수치 자체보다 제외 목록 축소 추세가 더 중요하다.

대응: omit 제거를 한 번에 밀지 말고 `sfu_call_client`, `sfu_room`, updater, SMTP, friends/rooms handler 순으로 작은 단위 검증을 추가한다.

### 4.3 배포 산출물 검증 부족

Windows native build 와 macOS build workflow 는 존재하지만, macOS PyInstaller/서명 관련 Team ID mismatch 리스크가 build.yml 주석에 남아 있다. README 는 Gatekeeper/SmartScreen 우회 안내를 제공하지만 실제 산출물 실행 smoke 증거가 더 필요하다.

대응: macOS `.app` 실제 실행, Windows zip 실행 smoke, 업데이트 서버 URL/443 dead-path guard 를 release checklist 에 고정한다.

### 4.4 Legacy room path 마이그레이션

GroupChatView/room_entered/RoomListWidget/server room broadcast 를 단순 삭제로 처리하면 작동 중 test 6종과 구 feature path 를 파괴할 수 있다. 반대로 보류하면 room/group 개념 혼동이 계속된다.

대응: **legacy room broadcast path → unified ChatView/group flow migration** 으로 Exec Plan 을 만들고, test 재설계와 코드 제거를 단계 분리한다.

## 5. 즉시 작업 큐

### P0

1. `current-project-review.md` 최신 cycle marker 유지로 `check_assessment_consistency.py` PASS 복구.
2. legacy room path 전체 마이그레이션 Exec Plan 작성: server broadcast, GroupChatView, room_entered, RoomListWidget, 6 test 재설계 포함.
3. `sqlite3.Connection` 미종료 `ResourceWarning` 원인 추적.

### P1

1. coverage omit 축소 1차: `app/net/sfu_call_client.py`, `server/sfu_room.py`.
2. macOS/Windows 산출물 실행 smoke 증거 문서화.
3. 원격 데스크탑 M4 실 OS 검증: Screen Recording/Accessibility 권한 + friend peer DataChannel + GRANT/revoke visual ack.

### P2

1. active Exec Plan 정리: 완료된 draft/active 문서 archive 이동 또는 status 정정.
2. `Specification.md`, `Structure.md`, `CheckList.md`, `MIGRATION_MARIADB.md` 안 과거 표현 sweep.
3. productization/vibe-coding snapshot 과 HTML mirror 최신성 동기.

## 6. 상태 라벨 기준

| 라벨 | 허용 조건 |
|---|---|
| `TODO` | 요구만 있고 코드·테스트 없음 |
| `PARTIAL` | 코드 또는 테스트 중 하나만 있거나 앱 wiring·배포·수동 QA 중 하나가 비어 있음 |
| `IMPLEMENTED` | 코드 + 자동 테스트 PASS + 문서 링크가 모두 있음 |
| `VERIFIED` | `IMPLEMENTED` + 수동 QA 또는 배포 산출물 실행 증거 있음 |
| `DEFERRED` | 명시적으로 뒤로 미룬 항목. 이유와 재개 조건 필요 |

`DONE`, `완료`, `PASS` 는 `VERIFIED` 와 같은 강도로 취급한다. 자동 테스트만 통과한 상태는 `IMPLEMENTED` 까지만 허용한다.

## 7. 다음 세션 시작 절차

1. `git status -sb`
2. `git log --oneline -8`
3. `.venv/bin/python tools/check_assessment_consistency.py`
4. `.venv/bin/python tools/check_migration_tables.py --strict`
5. `.venv/bin/python -m pytest -q`
6. P0 legacy room path 전체 마이그레이션 Exec Plan 작성 → M1 문서 선행 → 코드 마이그레이션 순서로 진행.

## 8. 결론

다음 큰 방향은 **전체 마이그레이션**이다. GroupChatView/room_entered/RoomListWidget/server room broadcast 잔존 경로는 죽은 코드라기보다 이전 구조가 아직 살아 있는 상태다. 통합 ChatView/group flow 로 경로를 확정하려면 test 재설계와 코드 제거를 함께 묶어야 한다.

TooTalk 는 내부 dogfooding 후보로 충분히 진입했다. 외부 사용자 배포 전까지 필요한 일은 새 기능 확장보다 stale 평가 방지, legacy path 제거, 배포 산출물 실행 증거, 실 기기 검증이다.
