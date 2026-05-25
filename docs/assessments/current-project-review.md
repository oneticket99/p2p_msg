---
title: "TooTalk 현재 프로젝트 전면평가"
owner: oneticket99
last_verified: 2026-05-25T16:05:00+09:00
status: active
---

# TooTalk 현재 프로젝트 전면평가

> 검토 기준: 2026-05-25 cycle 169.782 main branch.
> 목적: Claude가 다음 세션에서 바로 작업 순서를 잡을 수 있는 최신 평가 snapshot.
> 핵심 판정: 구현 진척은 좋고, 병목은 평가 문서 freshness + M6 enforcement + 원격 데스크탑 M4 검증이다.

## 1. 종합 판정

**현재 점수: 7.6 / 10**

TooTalk 는 문서만 있는 프로젝트가 아니라 PyQt6 클라이언트, aiohttp 시그널링, aiortc DataChannel, MariaDB/SQLite 저장, 봇, i18n, 원격 데스크탑, CI/문서 가드레일이 실제 파일과 테스트로 누적된 프로젝트다.

cycle 169.774~782 사이의 핵심 진척으로 이전 7.1/10 평가는 더 이상 유효하지 않다. `SignalingClient` 자동 재연결은 구현됐고, 원격 데스크탑은 `RemoteSessionRunner` 단위 검증을 넘어 실 aiortc DataChannel loopback까지 통과했다. M6 WBS backfill도 수행되어 프로세스 추적이 다시 살아났다.

다만 외부 사용자 배포 단계로 보기는 아직 이르다. 원격 데스크탑은 실 OS capture/input dispatch 수동 검증 전이고, macOS `.app` 배포 신뢰성·DB 문서 strict·WBS 자동 강제·평가 snapshot 동기화가 남아 있다. 현재 단계는 **내부 dogfooding 후보 + 원격 데스크탑 M4 진입 직전**이다.

## 2. 최신 검증 결과

이번 재평가에서 확인한 로컬 결과.

- `git status -sb`: clean, `main...origin/main`
- `.venv/bin/pytest -q tests/app/remote tests/app/ui/test_remote_session_wire.py tests/integration/test_remote_session_loopback.py tests/app/net/test_signaling_reconnect.py tests/app/ui/test_status_bar_states.py`: `162 passed, 1 deselected`
- `python3 tools/md_agents.py`: PASS
- `bash tools/doc-lint.sh`: PASS
- `data/wbs.sqlite` `wbs_tasks`: 274 row (cycle 169.783 current directive row 포함)

이전 전체 검증 기준.

- 기본 unit: `2463 passed, 38 skipped, 307 deselected`
- integration/server: `307 passed, 591 deselected`
- e2e: `10 passed`
- coverage 실행: `2770 passed, 38 skipped`, coverage `90.45%`

주의점.

- 전체 suite 재실행은 이번 문서 갱신에서 새로 수행하지 않았다. 위 162 PASS는 최신 변경 경로 집중 검증이다.
- coverage 90.45%는 `pyproject.toml` omit 범위가 넓은 상태의 측정값이다.
- SQLite `ResourceWarning: unclosed database` 반복 이슈는 이전 평가의 잔존 리스크다.

## 3. 최근 구현 진척

### 3.1 SignalingClient 자동 재연결

cycle 169.775에서 [app/net/signaling_client.py](../../app/net/signaling_client.py) 에 backoff 재연결 + reJOIN 복구가 구현됐다.

구현된 항목.

- `_should_reconnect` 로 비정상 drop과 명시적 `disconnect()` 구분
- `_recv_loop` 종료 시 `_schedule_reconnect()` 예약
- `_reconnect_loop` 지수 backoff + max attempts + `RECONNECTING` 상태 전이
- 마지막 `join()` 식별자 기반 reJOIN 복구
- `disconnect()` 중 재연결 task 취소
- [app/core/app_state.py](../../app/core/app_state.py) `RECONNECTING` valid state 추가
- cycle 169.780에서 [app/ui/status_bar.py](../../app/ui/status_bar.py) `_VALID_STATES` 동기화

검증.

- [tests/app/net/test_signaling_reconnect.py](../../tests/app/net/test_signaling_reconnect.py): 9 PASS
- [tests/app/ui/test_status_bar_states.py](../../tests/app/ui/test_status_bar_states.py): 3 PASS

판정: **IMPLEMENTED.** 실 서버 강제 close 기반 e2e chaos는 아직 필요하므로 NFR-04는 **VERIFIED 아님**.

### 3.2 UI skip/DI 방향 정리

cycle 169.774에서 superseded skip 파일 3개가 삭제되어 UI skip 38건이 24건으로 줄었다. MainWindow 전면 DI refactor는 hang 원인과 직접 관련이 없다는 진단이 확정됐다.

판정: **DI refactor 재개 금지.** 남은 24 skip은 asyncSlot 직접 호출 부적합, PyQt6 부재 skip, isolated 대체 미완료 항목으로 분류해서 다룬다.

### 3.3 원격 데스크탑 실 binding

cycle 169.777~782에서 원격 데스크탑 wire layer가 크게 진척됐다.

구현된 항목.

- [app/remote/session_runner.py](../../app/remote/session_runner.py): host/controller orchestration
- frame/input 별도 wire 직렬화
- capture/input backend DI
- host grant gate 기반 무단 input 차단
- [app/remote/remote_handshake.py](../../app/remote/remote_handshake.py): REQUEST/GRANT/DENY/REVOKE control protocol
- revoke token 상수시간 검증
- controller 화면 좌표를 host 화면 좌표로 보정
- [app/ui/_chat_header_mixin.py](../../app/ui/_chat_header_mixin.py): RemoteCallDialog accept 후 runner 생성 결선

검증.

- [tests/app/remote/test_session_runner.py](../../tests/app/remote/test_session_runner.py)
- [tests/app/remote/test_remote_handshake.py](../../tests/app/remote/test_remote_handshake.py)
- [tests/app/ui/test_remote_session_wire.py](../../tests/app/ui/test_remote_session_wire.py)
- [tests/integration/test_remote_session_loopback.py](../../tests/integration/test_remote_session_loopback.py)

판정: **IMPLEMENTED에 가까운 PARTIAL.** 실 DataChannel loopback은 통과했지만, 실제 친구 peer connection binding, OS capture/dispatch, 권한 팝업, 사용자 visual ack 전까지 `VERIFIED` 로 올리면 안 된다.

### 3.4 M6 WBS 활성

cycle 169.781에서 `data/wbs.sqlite` `wbs_tasks` backfill이 수행됐다.

현재 상태.

- 총 row: 274
- cycle 169.745~781 누락분 상당수 backfill
- M6 활성 전환 결정 기록됨

잔존 문제.

- cycle 169.782 row가 아직 없다.
- id 274 `cycle 169.781` self row의 `commit_sha`가 비어 있다.
- status 값이 `done`과 `completed`로 갈라져 있다.
- `.git/hooks`에는 실제 post-commit WBS hook이 설치되어 있지 않다.

판정: **M6는 활성화됐지만 enforcement는 PARTIAL.**

## 4. 문서와 구현 불일치

### 4.1 해결된 불일치

이전 평가의 “`SignalingClient` 자동 재연결 부재” 판정은 현재 폐기한다. cycle 169.775~780 구현과 테스트로 앱 클라이언트 재연결은 실제 존재한다.

[CheckList.md](../../CheckList.md) FR-10 `[x]` 표기는 현재 구현과 정합한다. 단, NFR-04의 30초 안 99% 성공률은 실 서버 chaos evidence가 별도 필요하므로 `[~]` 유지가 맞다.

### 4.2 아직 남은 불일치

다음 문서는 Claude가 먼저 손봐야 한다.

- [Specification.md](../../Specification.md) FR-10 trace row에 `app/net/signaling_client.py (예정)` 같은 과거 표현이 남아 있다.
- [docs/assessments/productization.md](productization.md) 상단 snapshot은 cycle 169.783에서 보정됐지만, 장문 본문에는 cycle 169.765~778 표현이 아직 남아 있다.
- [MIGRATION_MARIADB.md](../../MIGRATION_MARIADB.md) 와 [Structure.md](../../Structure.md) 는 실제 SQL 테이블 전수와 클라이언트 SQLite cache를 충분히 반영하지 못한다.
- [README.md](../../README.md) 일부 본문은 과거 스켈레톤 표현이 남아 있을 가능성이 있다. 변경 이력은 최신이지만 본문 전수 sweep이 필요하다.

## 5. 구조 리스크

가장 큰 구조 리스크는 여전히 UI 결합이다. 다만 MainWindow 전면 DI refactor가 정답이라는 결론은 폐기됐다.

현재 유효한 방향.

1. mixin full-instantiation hang 테스트를 무리하게 되살리지 않는다.
2. MagicMock self 기반 isolated test로 로직을 검증한다.
3. 실제 QWidget wiring은 subprocess/offscreen smoke 또는 수동 visual ack로 분리한다.
4. 원격 데스크탑은 runner/core와 UI binding을 계속 분리한다.

원격 데스크탑의 다음 구조 리스크.

- `_remote_data_channel` 실 생성 지점이 아직 명확히 제품 경로에 결선되지 않았다.
- HOST 역할 runner는 현재 grant 미주입 시 input 전량 거부하는 안전 기본값이다. 실제 승인 grant 주입 경로가 M4에서 필요하다.
- frame/input/control 3채널의 수명 관리, close/revoke, 재협상 정책이 아직 얇다.

## 6. Claude 즉시 작업 큐

### P0 — 문서 freshness 회수

1. [Specification.md](../../Specification.md) FR-10 trace row 수정: code ref를 `app/net/signaling_client.py`, test ref를 `tests/app/net/test_signaling_reconnect.py` / `tests/app/ui/test_status_bar_states.py`로 교체.
2. [docs/assessments/productization.md](productization.md) 장문 본문을 cycle 169.782 기준으로 전수 rewrite.
3. HTML mirror가 정책상 필요하면 `docs/html/productization.html`도 동기화.
4. README 본문에서 `(예정)`, `스켈레톤`, `자동 연결 수행하지 않는다`, `작성 예정` 류 표현 전수 grep.

권장 grep.

```bash
rg -n "예정|작성 예정|스켈레톤|자동 연결 수행하지|Task #|placeholder|Phase [0-9]+ .*활성" README.md Specification.md Structure.md MIGRATION_MARIADB.md CheckList.md docs/assessments
```

### P0 — M6 enforcement 마감

1. `wbs_tasks` cycle 169.782 row 추가.
2. id 274 `commit_sha` 보정 또는 self row 정책 문서화.
3. `status` 값을 `done` 또는 `completed` 하나로 통일할지 결정.
4. post-commit WBS hook 설치 여부 결정. hook 설치 전까지는 reviewer gate에서 WBS row 존재를 직접 검사한다.

검증 SQL.

```bash
sqlite3 -header -column data/wbs.sqlite \
  "select id, cycle, status, commit_sha, directive from wbs_tasks order by id desc limit 12;"
```

### P1 — 원격 데스크탑 M4

1. 실 OS capture backend 실행 확인: macOS Screen Recording 권한 포함.
2. 실 input dispatch 확인: Accessibility 권한 포함.
3. friend peer connection 경로에서 `_remote_data_channel` 생성과 runner send callable을 실제 채널에 결선.
4. permission GRANT를 HOST runner에 주입하는 UI/채널 경로 구현.
5. M4 수동 visual ack를 `MANUAL_TESTS.md` 또는 Exec Plan evidence에 남긴다.

### P1 — NFR-04 실 서버 chaos

1. 실제 `SignalingClient` 인스턴스 기반으로 aiohttp WS server close를 강제하는 integration test 추가.
2. close 후 `RECONNECTING -> CONNECTED -> reJOIN` event 순서를 검증.
3. StatusBar 표시가 `ERROR`로 잘못 떨어지지 않는지 smoke 추가.

### P2 — DB/배포 정합

1. `MIGRATION_MARIADB.md` tables 배열과 SQL migration table 목록을 strict 기준으로 맞춘다.
2. `tools/check_migration_tables.py --strict` 를 warning에서 CI gate로 올리는 시점을 정한다.
3. macOS `.app` 실행성: Developer ID, Nuitka, rpath refactor 중 하나를 결정한다.

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
3. `sqlite3 data/wbs.sqlite "select id, cycle, status, commit_sha from wbs_tasks order by id desc limit 12;"`
4. `rg -n "예정|스켈레톤|자동 연결 수행하지" README.md Specification.md Structure.md MIGRATION_MARIADB.md docs/assessments`
5. P0 문서 freshness → M6 enforcement → 원격 M4 순서로 진행.

## 9. 결론

Claude가 바로 들어가야 할 작업은 새 기능 추가가 아니라 **정합성 마감**이다. 구현은 169.782 기준으로 꽤 좋아졌다. 지금 병목은 “구현된 사실을 문서·WBS·검증 evidence가 같은 말로 고정하는 것”이다.
