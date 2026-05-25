---
title: "TooTalk 현재 프로젝트 전면평가"
owner: oneticket99
last_verified: 2026-05-25T20:30:00+09:00
status: active
---

# TooTalk 현재 프로젝트 전면평가

> 검토 기준: 2026-05-25 cycle 169.810 main branch. cycle 169.797 Codex snapshot 에 cycle 169.793~810 진척(음성·영상 SFU 그룹 통화 종단 코드 완결 PR #12/#13 merge + Structure §11 ERD drift 회수)을 환류 반영.
> 목적: Claude가 다음 세션에서 바로 작업 순서를 잡을 수 있는 협업용 평가 snapshot.
> 핵심 판정: 구현·검증 자동화는 내부 dogfooding 후보권에 들어왔고, 반복 작업 방지는 `tools/check_assessment_consistency.py` + doc-gardener 연결로 차단한다.

## 1. 종합 판정

**현재 점수: 7.8 / 10**

TooTalk 는 PyQt6 클라이언트, aiohttp 시그널링, aiortc DataChannel, MariaDB/SQLite 저장, 봇, i18n, 원격 데스크탑, CI/문서 가드레일이 실제 파일과 테스트로 누적된 프로젝트다. cycle 169.787~793 사이에 M6 post-commit hook, NFR-04 chaos 재연결 검증, 원격 M4 수동 절차, MIGRATION strict 정합이 추가되어 직전 7.6/10보다 소폭 올린다. cycle 169.794~810 에서 **음성·영상 SFU 그룹 통화(9 peer+)** 가 server(aiortc MediaRelay) + client net(SfuCallClient) + UI(GroupCallDialog) + MainWindow entry 까지 종단 코드 완결되어(PR #12/#13 merge, reviewer-gate 11 feat 전수 PASS, headless aiortc forward + offscreen Qt 검증) 그룹 통화가 TODO 에서 IMPLEMENTED 로 승급했다 — 단 실 OS 미디어 캡처/다중 화면 visual ack 전까지 VERIFIED 아님.

다만 외부 사용자 배포 단계로 보기는 아직 이르다. 원격 데스크탑은 실 OS capture/input dispatch와 친구 peer 경로 결선 전이고, macOS/Windows 배포 산출물의 실제 실행 증거가 부족하다. 현재 단계는 **내부 dogfooding 후보 + 원격 데스크탑 M4 사용자 게이트 대기**다.

## 2. 최신 검증 결과

이번 재평가에서 확인한 로컬 결과.

- `git status -sb`: clean, `main...origin/main` (cycle 169.793 기준)
- `python3 tools/md_agents.py`: PASS
- `bash tools/doc-lint.sh`: PASS
- `python3 tools/check_migration_tables.py --strict`: PASS, SQL 25개 = 문서 25개
- `.venv/bin/pytest -q tests/app/net/test_signaling_reconnect.py tests/integration/test_signaling_chaos_reconnect.py tests/app/ui/test_status_bar_states.py`: `12 passed, 1 deselected`
- `.venv/bin/pytest -q tests/app/remote tests/app/ui/test_remote_session_wire.py tests/integration/test_remote_session_loopback.py`: `150 passed, 1 deselected`
- `data/wbs.sqlite` `wbs_tasks`: 최신 12개 row 모두 `completed`, cycle 169.793 row가 commit `b523349`와 연결됨

이전 전체 검증 기준.

- 기본 unit: `2463 passed, 38 skipped, 307 deselected`
- integration/server: `307 passed, 591 deselected`
- e2e: `10 passed`
- coverage 실행: `2770 passed, 38 skipped`, coverage `90.45%`

주의점.

- 전체 suite 재실행은 이번 문서 갱신에서 새로 수행하지 않았다.
- coverage 90.45%는 `pyproject.toml` omit 범위가 넓은 상태의 측정값이다.
- SQLite `ResourceWarning: unclosed database` 반복 이슈는 이전 평가의 잔존 리스크다.

## 3. 최근 구현 진척

### 3.1 SignalingClient 자동 재연결

cycle 169.775에서 [app/net/signaling_client.py](../../app/net/signaling_client.py)에 backoff 재연결 + reJOIN 복구가 구현됐다. cycle 169.780에서 [app/ui/status_bar.py](../../app/ui/status_bar.py) `RECONNECTING` whitelist 회귀도 회수됐다. cycle 169.788에서 [tests/integration/test_signaling_chaos_reconnect.py](../../tests/integration/test_signaling_chaos_reconnect.py)가 추가되어 실제 aiohttp WebSocket close 기반 reJOIN 증거가 생겼다.

판정: **IMPLEMENTED.** NFR-04의 “30초 안 99%” 같은 운영 SLO는 장기 chaos 반복과 데모 서버 관측치가 쌓여야 `VERIFIED` 로 올린다.

### 3.2 원격 데스크탑 실 binding

cycle 169.777~782에서 원격 데스크탑 wire layer가 크게 진척됐다.

- [app/remote/session_runner.py](../../app/remote/session_runner.py): host/controller orchestration
- [app/remote/remote_handshake.py](../../app/remote/remote_handshake.py): REQUEST/GRANT/DENY/REVOKE control protocol
- [app/remote/coord_transform.py](../../app/remote/coord_transform.py): controller 좌표를 host 화면 좌표로 보정
- [app/ui/_chat_header_mixin.py](../../app/ui/_chat_header_mixin.py): RemoteCallDialog accept 후 runner 생성 결선
- [tests/integration/test_remote_session_loopback.py](../../tests/integration/test_remote_session_loopback.py): 실 aiortc DataChannel loopback

판정: **IMPLEMENTED에 가까운 PARTIAL.** 실 DataChannel loopback은 통과했지만, 실제 친구 peer connection binding, OS capture/dispatch, 권한 팝업, 사용자 visual ack 전까지 `VERIFIED` 로 올리면 안 된다.

### 3.3 M6 WBS enforcement

cycle 169.787에서 [tools/wbs_post_commit.py](../../tools/wbs_post_commit.py)와 [tools/install_wbs_hook.sh](../../tools/install_wbs_hook.sh)이 추가됐다. `data/wbs.sqlite` 기준 최신 row는 cycle 169.793까지 `completed` 상태로 commit SHA와 연결되어 있다.

판정: **ACTIVE.** `data/` 는 gitignore 대상이므로 CI 환경에서는 sqlite 부재 시 consistency 검사가 WBS 항목을 skip한다. 로컬 작업 세션에서는 post-commit hook 설치 상태와 최신 row를 함께 확인한다.

### 3.4 MIGRATION strict 정합

cycle 169.793에서 [MIGRATION_MARIADB.md](../../MIGRATION_MARIADB.md) §3.5에 확장 테이블 18개가 등재되어 SQL 25개와 문서 25개가 맞춰졌다. [tools/check_migration_tables.py](../../tools/check_migration_tables.py)의 strict 실행도 PASS다.

판정: **IMPLEMENTED.** 이후 신규 migration 추가 시 같은 strict 검사가 drift를 차단한다.

### 3.5 반복 방지 가드레일

cycle 169.797에서 [tools/check_assessment_consistency.py](../../tools/check_assessment_consistency.py)를 추가한다.

- HEAD commit cycle marker가 본 평가 문서에 없으면 실패한다.
- WBS 최신 row가 HEAD commit `completed` 인데 M6를 잔존 큐로 남기면 실패한다.
- DB strict PASS 이후 같은 항목을 큐에 다시 두면 실패한다.
- [doc-gardener.yml](../../.github/workflows/doc-gardener.yml)과 [tools/meta_enforce.py](../../tools/meta_enforce.py)에 연결한다.

판정: **반복 방지 ACTIVE.**

### 3.6 음성·영상 SFU 그룹 통화 (cycle 169.794~810)

9 peer 이상 그룹 음성·영상은 기존 표기("mesh ≤ 8 ✅ 기본 구현")가 부정확했다 — `CallClient`=1:1만, `MeshManager`=text fan-out 전용으로 group 미디어는 미결선이었다. cycle 169.794~810 에서 SFU 경로를 greenfield 로 종단 구현했다.

- server: [server/sfu_room.py](../../server/sfu_room.py)(aiortc MediaRelay publisher→N forward) + [server/sfu_registry.py](../../server/sfu_registry.py)(room lifecycle) + [server/protocol.py](../../server/protocol.py) SFU 메시지 4종 + [server/signaling.py](../../server/signaling.py) 라우팅 + [server/main.py](../../server/main.py) startup 등록 (PR #12 merge)
- client: [app/net/sfu_call_client.py](../../app/net/sfu_call_client.py)(publish/subscribe/on_remote_track) + [app/net/signaling_client.py](../../app/net/signaling_client.py) SFU dispatch/send + [app/ui/group_call_dialog.py](../../app/ui/group_call_dialog.py)(타일 그리드) + [app/ui/_sfu_call_mixin.py](../../app/ui/_sfu_call_mixin.py) 배선 + MainWindow 합성 + "그룹 통화 시작"(Ctrl+Shift+G) 메뉴 entry (PR #13 merge)
- test: [tests/integration/test_sfu_room_loopback.py](../../tests/integration/test_sfu_room_loopback.py)(1→2 forward + 실 frame) + [tests/integration/test_sfu_call_client_e2e.py](../../tests/integration/test_sfu_call_client_e2e.py)(종단) + signaling/dialog/mixin isolated

판정: **IMPLEMENTED.** reviewer-gate 11 feat 전수 PASS + headless aiortc 실 forward + offscreen Qt + MRO smoke. 실 OS 미디어 캡처/다중 화면 visual ack 전까지 `VERIFIED` 아님 (G4 사용자 게이트, visual ack 후반 일괄 큐).

## 4. 문서와 구현 불일치

### 4.1 해결된 불일치

- `SignalingClient` 자동 재연결 부재 판정은 폐기한다.
- M6 WBS 자동화 미설치 판정은 폐기한다.
- MIGRATION strict 미완료 판정은 폐기한다.
- NFR-04 실 서버 chaos 테스트 부재 판정은 폐기한다.
- Structure.md 가 DB 스키마 4 테이블만 등재하던 drift 는 cycle 169.794 에서 §11.3 전체 25 테이블 도메인 인벤토리로 회수했다(폐기).
- "mesh ≤ 8 그룹 음성·영상 기본 구현" 부정확 표기는 cycle 169.794~810 SFU greenfield 종단 구현으로 정정됐다.

### 4.2 아직 남은 불일치

다음 문서는 다음 작업에서 먼저 손봐야 한다.

- [Specification.md](../../Specification.md), [Structure.md](../../Structure.md), [CheckList.md](../../CheckList.md), [MIGRATION_MARIADB.md](../../MIGRATION_MARIADB.md)에 남은 과거 `예정`/`작성 예정`/`스켈레톤` 표현 정리.
- [docs/assessments/productization.md](productization.md) 장문 본문에는 과거 cycle 표현이 아직 많다. 최신 요약은 맞아도 본문 전수 rewrite가 필요하다.
- [docs/html/productization.html](../html/productization.html), [docs/html/vibe-coding.html](../html/vibe-coding.html) mirror는 평가 md 변경과 같은 cycle에서 확인해야 한다.

## 5. 구조 리스크

가장 큰 구조 리스크는 UI 결합이다. MainWindow 전면 DI refactor가 정답이라는 결론은 폐기됐다.

현재 유효한 방향.

1. mixin full-instantiation hang 테스트를 무리하게 되살리지 않는다.
2. MagicMock self 기반 isolated test로 로직을 검증한다.
3. 실제 QWidget wiring은 subprocess/offscreen smoke 또는 수동 visual ack로 분리한다.
4. 원격 데스크탑은 runner/core와 UI binding을 계속 분리한다.

원격 데스크탑의 다음 구조 리스크.

- `_remote_data_channel` 실 생성 지점이 제품 경로에 완전 결선되어야 한다.
- HOST 역할 runner는 grant 미주입 시 input 전량 거부하는 안전 기본값이다. 실제 승인 grant 주입 경로가 M4에서 필요하다.
- frame/input/control 3채널의 수명 관리, close/revoke, 재협상 정책이 아직 얇다.

## 6. Claude 즉시 작업 큐

### P0 — 반복 방지 검증 안착

1. `python3 tools/check_assessment_consistency.py` PASS를 유지한다.
2. doc-gardener 수동 실행 또는 CI run에서 새 step이 동작하는지 확인한다.
3. 평가 문서 갱신 시 최신 `git log -1 --pretty=%s` cycle marker를 본문 상단에 반영한다.

### P0 — 과거 표현 sweep

1. 아래 grep 결과를 기준으로 `Specification.md`, `Structure.md`, `CheckList.md`, `MIGRATION_MARIADB.md`를 최신 구현 링크로 교체한다.

   ```bash
   rg -n "예정|작성 예정|스켈레톤|자동 연결 수행하지|Task #|placeholder" README.md Specification.md Structure.md MIGRATION_MARIADB.md CheckList.md docs/assessments
   ```

2. 과거 상태를 의도적으로 남길 때는 “historical” 또는 “완료된 과거 표기”처럼 현재 작업 큐가 아님을 명시한다.

### P1 — 원격 데스크탑 M4

1. 실 OS capture backend 실행 확인: macOS Screen Recording 권한 포함.
2. 실 input dispatch 확인: Accessibility 권한 포함.
3. friend peer connection 경로에서 `_remote_data_channel` 생성과 runner send callable을 실제 채널에 결선.
4. permission GRANT를 HOST runner에 주입하는 UI/채널 경로 구현.
5. M4 수동 visual ack를 [MANUAL_TESTS.md](../exec-plans/active/MANUAL_TESTS.md)에 남긴다.

### P1 — 배포 산출물 검증

1. macOS `.app` 실행성을 실제 빌드 산출물 기준으로 검증한다.
2. Windows zip 실행 smoke를 runner 또는 별도 장비에서 확인한다.
3. codesign/notarization은 사용자 배포 직전 결정 사항이므로 현 cycle 작업 큐에서 제외한다.

## 7. 불일치 방지 규칙

문서 상태 라벨은 다음 의미로만 사용한다.

| 라벨 | 허용 조건 |
|---|---|
| `TODO` | 요구만 있고 코드·테스트 없음 |
| `PARTIAL` | 코드 또는 테스트 중 하나만 있거나 앱 wiring·배포·수동 QA 중 하나가 비어 있음 |
| `IMPLEMENTED` | 코드 + 자동 테스트 PASS + 문서 링크가 모두 있음 |
| `VERIFIED` | `IMPLEMENTED` + 수동 QA 또는 배포 산출물 실행 증거 있음 |
| `DEFERRED` | 명시적으로 뒤로 미룬 항목. 이유와 재개 조건 필요 |

`DONE`, `완료`, `PASS` 는 `VERIFIED` 와 같은 강도로 취급한다. 자동 테스트만 통과한 상태는 `IMPLEMENTED` 까지만 허용한다.

FR/NFR 추적표 필수 열.

- `id`
- `status`
- `code_refs`
- `test_refs`
- `doc_refs`
- `last_verified`
- `evidence`

`status=VERIFIED` 인데 `test_refs` 또는 `evidence` 가 비어 있으면 reviewer가 차단한다.

## 8. 다음 Claude 세션 시작 절차

1. `git status -sb`
2. `git log --oneline -8`
3. `python3 tools/check_assessment_consistency.py`
4. `sqlite3 data/wbs.sqlite "select id, cycle, status, commit_sha from wbs_tasks order by id desc limit 12;"`
5. `python3 tools/check_migration_tables.py --strict`
6. P0 과거 표현 sweep → P1 원격 M4 → P1 배포 산출물 검증 순서로 진행.

## 9. 결론

Claude가 바로 들어가야 할 작업은 새 기능 추가보다 **반복 방지 검증 안착과 stale 문구 sweep**이다. 구현은 cycle 169.793 기준으로 좋아졌고, 이제 같은 항목을 반복 큐에 올리지 않도록 assessment consistency gate를 운영해야 한다.
