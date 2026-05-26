---
title: "TooTalk 현재 프로젝트 전면평가"
owner: oneticket99
last_verified: 2026-05-26T11:51:00+09:00
status: active
---

# TooTalk 현재 프로젝트 전면평가

> 검토 기준: 2026-05-26 cycle 169.848 main branch + room broadcast → 통합 ChatView 마이그레이션 M1~M5b 완결 반영 + Codex 재평가 후 Claude 진입 큐 정리. 직전 169.841 평가(P0 = legacy room path 전체 마이그레이션)에서 지목한 P0 항목이 cycle 169.842~848 에 단계별(M2 송신 echo → M3 적재 cache → M4 진입 통일 → M5 위젯 회수 → M6 송신 coverage → M5b idx 재번호+파일 삭제) reviewer 게이트 전수 PASS 로 완결됐다.
> 목적: 다음 작업 세션에서 곧바로 우선순위를 잡을 수 있는 협업용 평가 snapshot.
> 핵심 판정: 내부 dogfooding 후보권은 유지한다. 외부 사용자 배포 직전 단계는 아니다. legacy room path P0 는 해소됐고, 남은 차이는 최신성 게이트, 배포 산출물 실행 증거, 핵심 UI/RTC 실효 커버리지, 실 기기 검증이다.

## 1. 종합 판정

**현재 점수: 7.7 / 10** (유지)

TooTalk 는 PyQt6 클라이언트, aiohttp signaling, aiortc DataChannel/SFU, MariaDB schema, bot/i18n/remote-control 기반, CI/문서 가드레일이 실제 파일과 자동 테스트로 누적된 프로젝트다. 최근 cycle 169.842~848 에서 **room broadcast → 통합 ChatView 마이그레이션 M1~M5b 가 완결**돼, 통합 ChatView(StackedWidget idx 0)가 friend/bot/saved/room/group 단일 표시·진입·송신 경로로 수렴했고 legacy GroupChatView/`room_entered`/RoomListWidget/`_dispatch_message_chain`/`_group_message_client` 가 물리 회수됐다.

점수는 **7.7 로 유지**한다. 마이그레이션은 구조 부채 회수 + 경로 단일화(품질 측면 개선)이나 신규 VERIFIED capability 가 아니며, coverage omit 범위가 넓은 사실, macOS/Windows 산출물 실행 증거와 원격 데스크탑/SFU 실 기기 검증이 부족한 사실은 그대로다. 직전 평가의 P0(legacy room path 전체 마이그레이션)는 해소됐으나, 그 자체가 외부 readiness 지표를 올리지는 않는다. 제품 단계 표현은 **내부 dogfooding 후보 + 배포/실기기 검증 대기**가 가장 정확하다.

## 2. 최신 검증 결과

2026-05-26 11:15 KST 기준 로컬 확인 결과.

- `git log --oneline`: HEAD = cycle 169.848 (M5b idx 재번호 + 위젯 파일 삭제). 직전 169.842~847 마이그레이션 commit 누계.
- `QT_QPA_PLATFORM=offscreen python3 -m pytest -q`: `2546 passed, 24 skipped, 317 deselected` (직전 2557 → obsolete 위젯 standalone test 2 파일 삭제분 반영, 회귀 0).
- `QT_QPA_PLATFORM=offscreen python3 -m pytest --cov -q`: `2546 passed, 24 skipped, 317 deselected`, coverage `87.96%`.
- `bash tools/doc-lint.sh`: PASS, 79개 markdown 위반 0건.
- `pytest tests/app tests/server -q`: `2493 passed, 24 skipped` (마이그레이션 단위 회귀 baseline).
- 마이그레이션 검증: reviewer-agent 게이트 M2 / M3+M4 / M5 / M6 전수 PASS (차단 0). D7 grep(`GroupChatView`/`_STACK_GROUP_CHAT`/`room_entered`/`_room_list`) 런타임 잔존 0 (주석/docstring 이력 참조만).
- `tools/check_migration_tables.py --strict`: PASS, SQL 25개 = 문서 25개 (직전 동일).
- `tools/check_assessment_consistency.py`: 본 cycle 169.848 marker 갱신으로 PASS 복구 의무.

주의 — coverage omit 범위, macOS/Windows 산출물 실행 증거, RTC/remote 실 기기 검증은 직전 평가 대비 변동 없음(마이그레이션은 표시·송신 경로 단일화 한정).

주의점.

- 샌드박스 제한 환경에서는 aiohttp test server 의 `127.0.0.1:0` bind 가 `PermissionError` 로 실패했다. 제한 없는 로컬 실행에서는 통과했다.
- coverage 87.96% 는 `pyproject.toml` omit 범위가 넓은 조건의 수치다. UI dialog, RTC peer/file, remote capture/input, 여러 REST handler 가 측정에서 빠져 있다.
- coverage 실행 후 `sqlite3.Connection` 미종료 `ResourceWarning` 이 1건 남는다.
- Codex 재평가 중 `Structure.md` 에 삭제된 `app/ui/group_chat_view.py` 항목이 남은 drift 를 발견했고, 본 문서 갱신 cycle 에서 트리 항목을 회수했다. `room_list.py` 는 파일은 유지하되 `RoomItem` dataclass 전용으로 의미를 정정했다.

## 3. 최근 구현 진척

### 3.1 Group flow canonical 정리 + legacy room path 전체 마이그레이션 완결

cycle 169.838 에서 "방 입장" 메뉴와 Room ID 직접 입력 흐름을 제거했고, 그룹방은 그룹 만들기 + 초대 구조로 정리했다. 이어 cycle 169.842~848 에서 직전 평가가 P0 로 지목한 **legacy room broadcast path → 통합 ChatView/group flow 전체 마이그레이션**을 단계별로 완결했다: M2 송신 echo 통합 재배선 → M3 room 적재 source-of-truth `_rooms_cache` 이전 → M4 kind=room 진입 통합 ChatView 통일(`_on_room_entered` early return 제거 + `_current_room_id` 결선) → M5 legacy 위젯(GroupChatView/`room_entered`/RoomListWidget/`_on_room_entered`/`_on_group_message_send`/`_dispatch_message_chain`) 물리 회수 → M6 통합 room-send mesh+REST 신규 coverage → M5b StackedWidget idx 완전 재번호 + `group_chat_view.py`/`room_list.py` RoomListWidget 파일 삭제 + dead attr `_group_message_client` 회수.

판정: **IMPLEMENTED (마이그레이션 완결).** 통합 ChatView(idx 0)가 friend/bot/saved/room/group 단일 표시·진입·송신 경로로 수렴했고, 단계별 reviewer 게이트 전수 PASS + D7 grep 런타임 잔존 0 + 전체 2546 PASS(회귀 0). 직전 평가의 "단순 dead code 가 아닌 legacy feature path" 우려는 단계 분리(코드 마이그레이션 + test 재설계 분리) + 위험 등급별 commit(안전 M5 / idx 재번호 M5b)로 해소됐다. room/group 실 동작의 사용자 visual ack 는 후반 일괄 큐.

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

### 4.4 Legacy room path 마이그레이션 — ✅ 해소 (cycle 169.842~848)

직전 평가의 우려(단순 삭제 시 test 6종 + 구 feature path 파괴, 보류 시 room/group 개념 혼동)는 Exec Plan(`2026-05-26-room-broadcast-unified-chatview-migration.md`) 기반 단계 마이그레이션으로 해소됐다. test 재설계(M6)와 코드 제거(M5/M5b)를 commit 분리 + 단계별 reviewer 게이트로 묶었고, 되돌리기 비용 큰 idx 재번호는 M5b 로 위험 등급 분리 후 사용자 GO 수령해 진행했다.

잔존 리스크: room/group 실 동작(다중 peer mesh broadcast + REST 영속화)의 사용자 visual ack 는 아직 자동 검증 범위 밖(후반 일괄 큐). 코드 경로 단일화는 완결.

### 4.5 Structure.md UI tree drift — ✅ 해소 (2026-05-26 11:51 KST)

Codex 재평가에서 `Structure.md` 의 `app/ui/` 트리가 M5b 파일 회수 이후 상태를 따라오지 못한 점을 발견했다. 삭제된 `group_chat_view.py` 항목을 제거했고, `room_list.py` 는 `RoomListWidget` 이 아니라 `RoomItem` dataclass 만 보존하는 파일로 설명을 바꿨다.

## 5. 즉시 작업 큐

### P0

1. ✅ (해소) legacy room path 전체 마이그레이션 — cycle 169.842~848 M1~M5b 완결, reviewer 게이트 전수 PASS.
2. ✅ (해소) `current-project-review.md` 최신 cycle marker 유지로 `check_assessment_consistency.py` PASS 복구 — 본 cycle 169.848 marker 갱신.
3. ✅ (해소) `Structure.md` UI tree drift — 삭제된 `group_chat_view.py` 제거 + `room_list.py` 역할을 `RoomItem` dataclass 전용으로 정정.
4. M6 WBS `data/wbs.sqlite` row 등록 정책 — cycle 169.231 이후 600+ cycle 중단(dereliction-detector MEDIUM detect). 사용자 ack 필요(재개/backfill vs 영구 비활성).
5. `sqlite3.Connection` 미종료 `ResourceWarning` 원인 추적 (coverage/test teardown).

### P1

1. coverage omit 축소 1차: `app/net/sfu_call_client.py`, `server/sfu_room.py`.
2. macOS/Windows 산출물 실행 smoke 증거 문서화.
3. 원격 데스크탑 M4 실 OS 검증: Screen Recording/Accessibility 권한 + friend peer DataChannel + GRANT/revoke visual ack.
4. room/group 통합 경로 사용자 visual ack (다중 peer mesh broadcast + REST 영속화) — 후반 일괄 큐.

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
6. P0 잔존(M6 WBS 활성 ack + sqlite ResourceWarning) 확인 → P1(coverage omit 축소 / 배포 산출물 smoke / 원격 M4 실 OS) 우선순위 진입.

## 8. Claude 진입용 직접 작업 큐

다음 Claude 세션은 신규 기능보다 정합성 마감부터 잡는다.

1. `sqlite3.Connection` 미종료 `ResourceWarning` 재현 지점 추적: `pytest -q` 와 `pytest --cov -q` 양쪽에서 동일 connection object 경고가 난다. teardown 누락 가능성이 높은 영역은 `app/db/local_db.py`, `app/db/messages_cache.py`, UI fixture, server repository fixture 순으로 본다.
2. M6 WBS 정책 결정: `data/wbs.sqlite` 가 gitignored local artifact 이므로, 재개/backfill 또는 영구 비활성 중 하나를 사용자에게 확인한 뒤 문서와 hook 정책을 맞춘다.
3. coverage omit 축소 1차: `app/net/sfu_call_client.py` 와 `server/sfu_room.py` 부터 작은 단위 테스트를 추가한다. 목표는 총 coverage 숫자 상승보다 핵심 SFU 경로의 실효 커버리지 확보다.
4. 배포 smoke 증거 확보: macOS `.app` 실행, Windows zip 실행, 업데이트 URL dead-path guard 를 release checklist 에 증거 형식으로 남긴다.

## 9. 결론

직전 평가의 **전체 마이그레이션** 큐는 cycle 169.842~848 에 완결됐다. GroupChatView/room_entered/RoomListWidget/server room broadcast 잔존 경로는 단계별 마이그레이션(코드 제거 + test 재설계 분리 + reviewer 게이트 전수 PASS)으로 통합 ChatView/group flow 단일 경로로 확정됐고, legacy 위젯은 물리 회수됐다.

TooTalk 는 내부 dogfooding 후보로 충분히 진입했다. legacy path 제거가 끝난 지금, 외부 사용자 배포 전까지 남은 일은 새 기능 확장보다 stale 평가 방지(자동화 강화), 배포 산출물 실행 증거, 실 기기 검증(원격 데스크탑 M4 / SFU / room·group mesh), 그리고 coverage omit 축소다.
