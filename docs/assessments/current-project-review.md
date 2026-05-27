---
title: "TooTalk 현재 프로젝트 전면평가"
owner: oneticket99
last_verified: 2026-05-27T22:35:00+09:00
status: active
---

# TooTalk 현재 프로젝트 전면평가

> HEAD 동기 (Claude, 2026-05-27 22:35 KST): main HEAD **cycle 169.855**. 본 Codex 전면평가(아래 본문, cycle 169.852 기준) 이후 진행 = avatar M1~M7 완결(G-final webcam ack 만 잔존) + 한글 주석 상세화 페이즈 M2 repo 21/21 + M3 server API handler 19/19 완료 + **M4 `app/net/*.py` 9/16 진행**(주석 전용 트랙 — 기능 diff 0, verify_comment_only AST 동일 전수 PASS + server 642/app pytest 무변경, 카탈로그 정정 다수 rooms 7·friends 8·auth 15·folder worker 5). M4 잔여 6 = avatars·call·rooms·friends·messages·signaling. 신규 VERIFIED capability 부재 → readiness 7.6 / 데모 8.4 유지. 다음 = M4 잔여 6 → M5 rtc. 본문 분석은 Codex 정본 그대로 보존.
>
> 검토 기준: 2026-05-26 19:50 KST main branch HEAD `ac54cf8` cycle 169.852 + avatar 이미지 picker M1/M2 서버 영속 완료 + 다음 session 인계 자료 작성 이후 Codex 전면평가 보정. room broadcast → 통합 ChatView 마이그레이션 M1~M5b 완결, Codex 평가 §8 직접 작업 큐 회수(§8-1 sqlite ResourceWarning 해소 + §8-3 SFU coverage sfu_call_client 14→89% + sfu_room 49→100% + M6 WBS 사용자 ack "재개+backfill" 수령·524 row backfill), avatar 서버 영속 foundation/endpoint 구현, 하드코딩 잔존 개선 큐, 그리고 사용자 직접 빌드 산출물 검증 기반의 **실사용 데모 readiness** 산정 기준을 함께 반영한다.
> 목적: 다음 작업 세션에서 곧바로 우선순위를 잡을 수 있는 협업용 평가 snapshot.
> 핵심 판정: 상용 제품화 readiness 는 7.6/10 으로 유지하지만, 본 프로젝트의 현재 목표가 "실사용 가능한 데모"임을 기준으로 보면 데모 readiness 는 8.4/10 이다. 사용자 직접 빌드 산출물 dogfooding 은 결함이 아니라 데모 QA의 핵심 검증 경로다.

## 1. 종합 판정

**상용 제품화 readiness: 7.6 / 10** (유지)
**실사용 데모 readiness: 8.4 / 10** (신규 기준)

TooTalk 는 PyQt6 클라이언트, aiohttp signaling, aiortc DataChannel/SFU, MariaDB schema, bot/i18n/remote-control 기반, CI/문서 가드레일이 실제 파일과 자동 테스트로 누적된 프로젝트다. 최근 cycle 169.842~848 에서 **room broadcast → 통합 ChatView 마이그레이션 M1~M5b 가 완결**돼, 통합 ChatView(StackedWidget idx 0)가 friend/bot/saved/room/group 단일 표시·진입·송신 경로로 수렴했고 legacy GroupChatView/`room_entered`/RoomListWidget/`_dispatch_message_chain`/`_group_message_client` 가 물리 회수됐다.

상용 제품화 점수는 **7.6** 으로 유지한다. 마이그레이션은 구조 부채 회수 + 경로 단일화(품질 개선)이나 신규 VERIFIED capability 가 아니며, avatar 서버 영속도 아직 클라이언트 picker/표시 전파/G-final visual ack 전이라 진행 중 상태다. coverage omit 범위가 넓은 사실, macOS/Windows 산출물의 광범위 사용자 환경 증거 부족, 원격 데스크탑/SFU 실 기기 검증 부족, 그리고 REST/STUN/update endpoint fallback 하드코딩 잔존은 외부 배포 readiness 를 낮추는 실질 리스크다.

반면 현재 목표를 **실사용 가능한 데모**로 두면 점수는 **8.4** 로 산정한다. 이유는 핵심 메신저 경로(로그인/친구/채팅/그룹/파일/봇/기본 통화 골격)가 실제 코드와 테스트로 상당 부분 갖춰졌고, 사용자가 직접 빌드 산출물을 실행하며 발견 이슈를 즉시 회수하는 dogfooding loop 가 이미 작동 중이기 때문이다. 데모 단계에서는 "상용 배포용 보편 환경 보장"보다 "정해진 데모 환경에서 주요 플로우가 실사용 가능하고, 발견 버그를 빠르게 고치는가"가 더 중요하다.

### 1.1 데모 readiness 점수표

| 항목 | 점수 | 근거 |
|---|---:|---|
| 핵심 채팅 플로우 | 8.8 | 통합 ChatView 경로 정리, DM/group/room 표시·송신 경로 수렴, 기본 suite PASS. |
| 계정/친구/그룹 UX | 8.3 | 로그인/친구요청/그룹 생성·멤버 보기 dogfooding 이슈 다수 회수. 남은 visual ack 필요. |
| 파일/이미지/아바타 데모 | 8.0 | 파일/이미지 DataChannel 검증 + avatar 서버 M1/M2 완료. 클라 picker M3~M7 잔존. |
| 음성·영상/SFU 데모 | 7.6 | server/client 종단 코드와 단위 coverage 는 좋지만, 실 OS 미디어 캡처·다중 화면 확인 전. |
| 원격 데스크탑 데모 | 6.8 | protocol/coord/session foundation 은 있으나 권한·DataChannel·실 입력/화면 수명 검증이 얇음. |
| 빌드 산출물 dogfooding | 8.6 | 사용자가 직접 빌드 파일로 실행 검증 중. 이 검증은 데모 목표의 핵심 QA 루프. 결과 체크리스트 문서화 필요. |
| 운영/설정 안정성 | 7.5 | 데모 서버와 WBS/CI/문서 게이트는 강하지만 하드코딩 fallback 잔존과 설정 single source 부채 존재. |
| **종합** | **8.4** | **실사용 데모 기준으로는 충분히 후보권. 외부 상용 배포 기준은 별도 7.6 유지.** |

## 2. 최신 검증 결과

2026-05-26 19:50 KST 기준 로컬 확인 결과.

- `git log --oneline -1`: HEAD = `ac54cf8 docs(cycle169.852): handoff 사용자 directive 반영 — 다음 session 전체 구현 1번(M3)부터 순차`.
- `.venv/bin/python -m pytest -q`: `2614 passed, 24 skipped, 334 deselected in 7.51s` (기본 unit suite, integration/e2e deselected).
- `.venv/bin/python -m pytest tests/app/ui/test_main_window_rooms.py tests/app/ui/test_main_window_mixin_mro.py tests/app/ui/test_mixin_isolated_batch3.py -q`: `30 passed`.
- `.venv/bin/python -m pytest tests/server/test_protocol.py tests/server/test_signaling_rooms_e2e.py tests/app/rtc/test_mesh_manager.py tests/app/net/test_messages_client.py -q`: `49 passed`.
- `.venv/bin/python -m pytest tests/server/test_sfu_room.py -q`: `10 passed`.
- `sqlite3 data/wbs.sqlite 'select count(*) from wbs_tasks;'`: `679`.
- `.venv/bin/python -m pytest --cov=app --cov=server --cov-report=term-missing:skip-covered -q`: `2614 passed, 24 skipped, 334 deselected`, coverage `89.38%` (omit 적용 조건).
- `.venv/bin/python -m tools.md_agents`: PASS — M3 history, M2 README, root md 18개.
- `pytest tests/app tests/server -q`: `2493 passed, 24 skipped` (마이그레이션 단위 회귀 baseline).
- 마이그레이션 검증: reviewer-agent 게이트 M2 / M3+M4 / M5 / M6 전수 PASS (차단 0). D7 grep(`GroupChatView`/`_STACK_GROUP_CHAT`/`room_entered`/`_room_list`) 런타임 잔존 0 (주석/docstring 이력 참조만).
- `tools/check_migration_tables.py --strict`: PASS, SQL 25개 = 문서 25개 (직전 동일).
- `tools/check_assessment_consistency.py`: 본 19:45 보정 전 FAIL(HEAD cycle 169.852 marker 누락). 본 보정 뒤 PASS.
- `git status -sb`: `main...origin/main` clean 에서 본 평가 보정 변경 발생.
- 하드코딩 스캔: `rg "114.207.112.73|stun.l.google.com|8765|TOOTALK_API_BASE|api_base"` 기준 `app/core/config.py` 외 UI mixin fallback, settings dialog 표시값, update URL, OAuth redirect, call/STUN fallback 잔존 확인.
- 데모 검증 전제: 사용자가 빌드된 macOS/Windows 산출물을 직접 실행해 로그인·메뉴·그룹·소리·네트워크 이슈를 확인하고 있으며, 발견사항은 dogfooding 버그 큐로 회수 중이다.

주의 — coverage omit 범위, macOS/Windows 산출물 실행 증거, RTC/remote 실 기기 검증은 직전 평가 대비 변동 없음(마이그레이션은 표시·송신 경로 단일화 한정).

주의점.

- 샌드박스 제한 환경에서는 aiohttp test server 의 `127.0.0.1:0` bind 가 `PermissionError` 로 실패했다. 제한 없는 로컬 실행에서는 통과했다.
- coverage 87.96% 는 `pyproject.toml` omit 범위가 넓은 조건의 수치다. UI dialog, RTC peer/file, remote capture/input, 여러 REST handler 가 측정에서 빠져 있다.
- ✅ (cycle 169.849 해소) `sqlite3.Connection` 미종료 `ResourceWarning` — `app/db/local_db.py` 싱글톤에 `atexit.register(close_connection)` 추가로 인터프리터 종료 시 결정적 close. full suite trailer 경고 제거 (codex §8-1).
- ✅ (cycle 169.849~850 완결) SFU coverage — `app/net/sfu_call_client.py` 18 PASS 로 14.39→89.21%(849) + `server/sfu_room.py` 10 PASS 로 49.48→100%(850, `tests/server/test_sfu_room.py`). codex §8-3 종결.
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

판정: **IMPLEMENTED, VERIFIED 아님.** 단위 coverage 는 sfu_call_client 89.21% + sfu_room 100% 로 회수됐으나(cycle 849~850), 실 OS 미디어 캡처/다중 화면 visual ack 전에는 제품 검증 완료로 올리면 안 된다(coverage ≠ 실 미디어 종단 검증).

### 3.4 원격 데스크탑

remote protocol, permission, coord transform, session runner, handshake, loopback test 는 갖춰졌다. 다만 실제 friend peer path 에서 `_remote_data_channel` 생성, host permission grant 주입, Screen Recording/Accessibility 권한, frame/input/control close/revoke 수명 관리는 아직 얇다.

판정: **PARTIAL.** 자동 테스트만으로는 부족하며 M4 실 OS 수동 검증이 필요하다.

### 3.5 DB/MIGRATION 정합

`MIGRATION_MARIADB.md` 와 `server/db/migrations` 는 strict 기준 SQL 25개 = 문서 25개로 맞다. cycle 169.821 의 `0017_group_roles_meta.sql` 은 owner/admin/member role + rooms group meta foundation 을 제공한다.

판정: **IMPLEMENTED.** 신규 migration 추가 때 `tools/check_migration_tables.py --strict` 를 계속 머지 게이트로 유지해야 한다.

### 3.6 Avatar 서버 영속 foundation

cycle 169.852 에서 avatar 이미지 picker Exec Plan M1/M2 가 완료됐다. 서버 영역은 `users.avatar_ref` migration, content-addressed avatar repository, multipart upload/GET/PATCH endpoint, rooms create payload `avatar_ref` 수용까지 구현됐고, repository 18 PASS + integration 17 PASS + 전체 기본 suite 회귀 0 으로 확인됐다.

판정: **IMPLEMENTED 진행 중.** 서버 write path 는 갖춰졌지만 클라이언트 `AvatarPickerButton`, 3 dialog 통합, CameraCaptureDialog, `_avatar_helper` 표시 전파, 사용자 visual ack 가 남아 있어 VERIFIED 로 올리면 안 된다.

## 4. 주요 리스크

### 4.1 평가 snapshot stale 재발

`check_assessment_consistency.py` 는 HEAD cycle marker 가 `current-project-review.md` 에 없으면 실패한다. 이번 재평가 직전 상태가 바로 이 실패였다. 평가 문서는 기능 완료 뒤 따라붙는 보조 문서가 아니라 CI 차단 자원이다.

대응: 기능/테스트 commit 뒤 current-project-review 의 검토 기준과 최신 검증 결과를 같은 cycle 에 갱신한다.

### 4.2 Coverage 신뢰도 착시

총 coverage 87.99% 는 나쁘지 않지만 `pyproject.toml` omit 이 넓다. 특히 UI core, RTC peer/file path, remote OS backend, 여러 REST handler 가 실제 측정에서 빠졌다. 수치 자체보다 제외 목록 축소 추세가 더 중요하다.

대응: omit 제거를 한 번에 밀지 말고 `sfu_call_client`, `sfu_room`, updater, SMTP, friends/rooms handler 순으로 작은 단위 검증을 추가한다.

### 4.3 빌드 산출물 dogfooding 진행 중

Windows native build 와 macOS build workflow 는 존재하고, 사용자는 실제 빌드 산출물을 직접 실행해 하나씩 테스트하며 디버깅 중이다. 이 프로젝트의 현재 목표가 "실사용 가능한 데모"이므로 수동 실행 검증은 부족분이 아니라 **데모 QA의 핵심 경로**다. 다만 macOS PyInstaller/서명 관련 Team ID mismatch 리스크가 build.yml 주석에 남아 있고, 수동 테스트 결과가 체크리스트 형태로 구조화돼 있지는 않다.

대응: "실행 증거 부족"으로 표현하지 않고 `MANUAL_TESTS.md` 또는 본 평가문서 P1 큐에 **사용자 직접 검증 항목**으로 누적한다. macOS `.app`, Windows zip, 로그인, 친구/그룹, 메시지, 파일, 아바타, 통화, 원격제어를 데모 플로우별 PASS/FAIL/발견 버그 링크로 기록한다.

### 4.4 Legacy room path 마이그레이션 — ✅ 해소 (cycle 169.842~848)

직전 평가의 우려(단순 삭제 시 test 6종 + 구 feature path 파괴, 보류 시 room/group 개념 혼동)는 Exec Plan(`2026-05-26-room-broadcast-unified-chatview-migration.md`) 기반 단계 마이그레이션으로 해소됐다. test 재설계(M6)와 코드 제거(M5/M5b)를 commit 분리 + 단계별 reviewer 게이트로 묶었고, 되돌리기 비용 큰 idx 재번호는 M5b 로 위험 등급 분리 후 사용자 GO 수령해 진행했다.

잔존 리스크: room/group 실 동작(다중 peer mesh broadcast + REST 영속화)의 사용자 visual ack 는 아직 자동 검증 범위 밖(후반 일괄 큐). 코드 경로 단일화는 완결.

### 4.5 Structure.md UI tree drift — ✅ 해소 (2026-05-26 11:51 KST)

Codex 재평가에서 `Structure.md` 의 `app/ui/` 트리가 M5b 파일 회수 이후 상태를 따라오지 못한 점을 발견했다. 삭제된 `group_chat_view.py` 항목을 제거했고, `room_list.py` 는 `RoomListWidget` 이 아니라 `RoomItem` dataclass 만 보존하는 파일로 설명을 바꿨다.

### 4.6 하드코딩 fallback 잔존

정본 §E 는 설정값을 `.env` 또는 DB 상수 테이블로 주입하라고 요구하지만, 현재 코드에는 운영 endpoint fallback 이 아직 여러 곳에 남아 있다. 주요 예시는 다음과 같다.

- `app/ui/_bot_chat_mixin.py`, `_chat_helper_mixin.py`, `_rest_post_mixin.py`, `_friend_status_mixin.py`, `contacts_dialog.py` 의 `http://114.207.112.73:8765` fallback.
- `app/ui/main_window.py`, `_menu_bar_mixin.py`, `_update_lifecycle_mixin.py` 의 update server default URL 중복.
- `app/ui/settings_dialog.py` 의 server endpoint/STUN 표시값 literal.
- `app/net/call_client.py`, `app/net/sfu_call_client.py`, `app/ui/_signaling_mixin.py`, `_chat_header_mixin.py` 의 `stun:stun.l.google.com:19302` fallback.
- `server/api/streaming_oauth_handlers.py` 의 redirect URL `https://114.207.112.73:8443/...`.
- `server/api/bot_handlers.py` 의 bot sender id `1` fallback.

영향: 데모 환경에서는 동작하지만 staging/production 전환, private host 전환, TLS/wss 도입, multi-tenant 운영에서 silent wrong-endpoint 장애가 재발할 수 있다. cycle 169.823 의 443/8080 dead-path 회수처럼 endpoint literal 은 실제 사용자 502 로 이어진 전례가 있다.

대응: `Config.api_base`, `Config.stun_url`, update server URL, OAuth redirect, bot sender id 를 단일 설정 소스로 수렴한다. UI 파일은 `getattr(self._config, ...) or literal` 대신 config 주입 실패 시 명시 error/log 로 전환하고, `tests/app/test_no_443_hardcode.py` 를 확장해 운영 IP/STUN/update/OAuth literal scan 을 CI gate 로 묶는다.

## 5. 즉시 작업 큐

### P0

1. ✅ (해소) legacy room path 전체 마이그레이션 — cycle 169.842~848 M1~M5b 완결, reviewer 게이트 전수 PASS.
2. ✅ (해소) `current-project-review.md` 최신 cycle marker 유지로 `check_assessment_consistency.py` PASS 복구 — 본 cycle 169.848 marker 갱신.
3. ✅ (해소) `Structure.md` UI tree drift — 삭제된 `group_chat_view.py` 제거 + `room_list.py` 역할을 `RoomItem` dataclass 전용으로 정정.
4. ✅ M6 WBS `data/wbs.sqlite` row 등록 정책 — 사용자 ack "재개+backfill" 수령 후 backfill 완료로 기록됨. 16:24 로컬 확인 기준 `wbs_tasks` 675 rows. 후속은 hook 재중단 방지와 row 증분 검증.
5. ✅ (cycle 169.849 해소) `sqlite3.Connection` 미종료 `ResourceWarning` — `local_db` atexit 결정적 close.

### P1

1. coverage omit 축소 1차 완결: ✅ `app/net/sfu_call_client.py` (14→89%, cycle 169.849) / ✅ `server/sfu_room.py` (49→100%, cycle 169.850).
2. 사용자 직접 빌드 산출물 dogfooding 결과를 데모 체크리스트로 문서화: macOS `.app` / Windows zip / 로그인 / 친구 / 그룹 / 채팅 / 파일 / 아바타 / 통화 / 원격제어.
3. 원격 데스크탑 M4 실 OS 검증: Screen Recording/Accessibility 권한 + friend peer DataChannel + GRANT/revoke visual ack.
4. room/group 통합 경로 사용자 visual ack (다중 peer mesh broadcast + REST 영속화) — 후반 일괄 큐.
5. `app/i18n/labels.py:68/69/72` 출처 주석 dangling — 삭제된 `group_chat_view.py` 가리킴. `i18n_extract.py` 재추출 cycle (orphan key drop + qm 재컴파일 동반, 수동 편집 시 labels_extract.json desync) — OBS-2 추적.
6. 하드코딩 fallback 제거 1차: REST API base/update URL/STUN/OAuth redirect/bot sender id 를 `Config` 또는 DB 상수 테이블로 수렴하고, 운영 IP literal scan 을 CI gate 로 승격한다.

### P2

1. active Exec Plan 정리: 완료된 draft/active 문서 archive 이동 또는 status 정정. 단, room broadcast plan 은 상단 0.0 메모 기준 구현 완료 문서이므로 archive/finalize 전 README/History M2/M3 동시 갱신 의무.
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
3. 본 평가 문서가 HEAD cycle 169.852 를 포함하는지 확인
4. `.venv/bin/python tools/check_assessment_consistency.py`
5. `.venv/bin/python tools/check_migration_tables.py --strict`
6. `.venv/bin/python -m tools.md_agents`
7. `.venv/bin/python -m pytest -q`
8. P1(avatar M3 재개 / 하드코딩 fallback 제거 / 데모 dogfooding 체크리스트 / 원격 M4 실 OS) 우선순위 진입.

## 8. Claude 진입용 직접 작업 큐

다음 Claude 세션은 신규 기능보다 정합성 마감부터 잡는다. 아래 순서가 그대로 작업 진입 순서다.

1. **Assessment consistency 복구 확인** — `current-project-review.md` 가 HEAD `ac54cf8` / cycle 169.852 를 포함하는지 확인하고 `.venv/bin/python tools/check_assessment_consistency.py` PASS 를 먼저 확보한다.
2. ✅ **M6 WBS 정책 결정/ backfill 완료 확인** — `data/wbs.sqlite` 는 19:45 기준 `wbs_tasks` 679 rows. 다음 Claude 작업은 hook 재중단 방지와 신규 directive row 증분 검증만 수행한다.
3. ✅ **server SFU coverage 후속 완료 확인** — `tests/server/test_sfu_room.py` 10 PASS. `app/net/sfu_call_client.py` 는 18 PASS + 89%로 1차 완료. 다음 coverage 축소는 다른 omit 영역으로 넘어간다.
4. **avatar M3 재개** — `docs/exec-plans/active/2026-05-26-avatar-image-picker-upload.md` T-8~T-10 부터 진행한다. 서버 M1/M2 는 완료 상태다.
5. **하드코딩 fallback 제거 1차** — `app/ui/*_mixin.py`, `contacts_dialog.py`, update lifecycle, call/STUN client, streaming OAuth redirect 의 운영 IP/STUN literal 을 inventory 로 고정한 뒤 `Config` single source 로 이동한다. negative guard test 를 확장해 재발을 차단한다.
6. **데모 dogfooding 체크리스트 작성** — 사용자가 직접 빌드 산출물을 실행해 검증하는 항목을 `MANUAL` 로 분리하고, PASS/FAIL/발견 버그 링크를 남긴다. 이 검증은 데모 목표의 핵심 QA 로 취급한다.
7. **active plan 정리** — 완료된 handoff/마이그레이션 plan 은 archive/finalize 정책 확인 후 이동 또는 status 정정. 파일 이동 시 README/History 동시 갱신.
8. ✅ (cycle 169.849 해소) `sqlite3.Connection` 미종료 `ResourceWarning` — `app/db/local_db.py` 싱글톤이 `get_connection` 단일 소유 + `close_connection` 명시 호출 누락(pytest process 종료) 경로에서 GC `__del__` close 였다. `atexit.register(close_connection)` 추가로 결정적 close 보장(`_conn` 미오픈 None 가드 no-op). messages_cache 는 동일 싱글톤 재사용 → 단일 fix 로 충분.

## 9. 결론

직전 평가의 **전체 마이그레이션** 큐는 cycle 169.842~848 에 완결됐다. GroupChatView/room_entered/RoomListWidget/server room broadcast 잔존 경로는 단계별 마이그레이션(코드 제거 + test 재설계 분리 + reviewer 게이트 전수 PASS)으로 통합 ChatView/group flow 단일 경로로 확정됐고, legacy 위젯은 물리 회수됐다.

TooTalk 는 **실사용 가능한 데모 후보**로 충분히 진입했다. legacy path 제거가 끝난 지금, 외부 상용 배포 전까지 남은 일은 새 기능 확장보다 stale 평가 방지(자동화 강화), 사용자 직접 빌드 산출물 dogfooding 결과 문서화, 실 기기 검증(원격 데스크탑 M4 / SFU / room·group mesh), 하드코딩 fallback 제거, 그리고 coverage omit 축소다. 데모 기준 점수는 8.4/10, 상용 제품화 기준 점수는 7.6/10 으로 분리해 추적한다.
