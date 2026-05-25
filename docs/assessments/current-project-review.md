---
title: "TooTalk 현재 프로젝트 전면평가"
owner: oneticket99
last_verified: 2026-05-25T13:55:00+09:00
status: active
---

# TooTalk 현재 프로젝트 전면평가

> 검토 기준: 2026-05-25 13:40 KST 로컬 작업 트리.
> 범위: 실 구현, 문서 정합성, 테스트·CI 게이트, 배포 가능성, 구조 리스크.
> 목적: 다음 Claude 세션이 즉시 읽고 우선순위를 잡을 수 있는 평가 기록.

## 1. 종합 판정

**현재 점수: 7.1 / 10**

TooTalk 는 문서만 있는 스켈레톤이 아니라 실제 구현·테스트·운영 자산이 상당히 누적된 프로젝트다. 서버 API, PyQt6 클라이언트, WebRTC/DataChannel, 파일·이미지 전송, 봇, 원격 제어, i18n, 배포 인프라가 실제 파일과 테스트로 존재한다.

다만 문서 표현 중 일부는 구현보다 앞서 있거나 과거 상태를 아직 말한다. 특히 자동 재연결, DB 정본, README 빠른 시작, coverage 해석, macOS 앱 실행성은 “완료”보다 “부분 구현 또는 검증 보류”로 분류해야 한다.

현재 단계는 **외부 사용자 배포 직전**이 아니라 **내부 dogfooding 안정화 단계**다.

## 2. 이번 검증 결과

로컬 검증 결과.

- `python3 tools/md_agents.py`: PASS
- `bash tools/doc-lint.sh`: PASS
- `python3 tools/check_migration_tables.py`: PASS
- 기본 unit: `2463 passed, 38 skipped, 307 deselected`
- integration/server: `307 passed, 591 deselected`
- e2e: `10 passed`
- CI 유사 coverage: `2770 passed, 38 skipped`, coverage `90.45%`

주의점.

- 기본·통합·coverage 실행 후 SQLite `ResourceWarning: unclosed database` 가 반복 발생했다.
- skip 38건 중 UI hang, asyncSlot 직접 호출 부적합, fake worker fixture 누적 hang 계열이 남아 있다.
- coverage 90.45%는 넓은 omit 범위 위에서 산출된 값이다.

## 3. 실 구현된 항목

실 구현으로 분류 가능한 영역.

- 서버: auth, devices, messages, reactions, rooms, friends, bot, remote, health 라우트와 repository 계층이 존재한다.
- 클라이언트: PyQt6 앱, 로그인·회원가입, 채팅 UI, 파일·이미지 전송 모듈, i18n, 사운드, updater, bot, remote 관련 모듈이 존재한다.
- WebRTC/DataChannel: `app/rtc/*`, browser e2e, 파일·이미지 e2e가 통과했다.
- 테스트: unit/integration/e2e가 광범위하게 존재하며 로컬 기준 모두 통과했다.
- 운영: Docker, nginx, postfix, build workflow, release workflow, doc-gardener workflow가 존재한다.

## 4. 문서와 구현 불일치

### 4.1 자동 재연결

[CheckList.md](../../CheckList.md) 는 NFR-04를 chaos PASS 근거로 부분 충족 상태로 둔다. 하지만 [app/net/signaling_client.py](../../app/net/signaling_client.py) 의 `connect()` 는 단발 연결 + 수신 루프 예약만 수행하고, 수신 루프 종료 시 `DISCONNECTED` 로 전이한다. 앱 내부 backoff 재연결 루프와 reJOIN 복구 흐름은 없다.

[tools/chaos_signaling.py](../../tools/chaos_signaling.py) 는 새 aiohttp 클라이언트를 만들어 JOIN 재성공 시간을 측정한다. 이는 서버 접속 가능성 벤치이며 앱 클라이언트 자동 재연결 구현 증거로는 부족하다.

판정: **문서가 구현보다 앞섬.**

### 4.2 DB 정본

[MIGRATION_MARIADB.md](../../MIGRATION_MARIADB.md) 는 MariaDB 7개 핵심 테이블 중심 문서다. 실제 migrations SQL은 25개 테이블이며 `tools/check_migration_tables.py` 역시 “문서 테이블이 SQL에 존재하는가”만 기본 검사한다.

[Structure.md](../../Structure.md) 는 아직 `app/db/` 미생성, `MIGRATION_MARIADB.md` 작성 예정 같은 과거 표현을 포함한다. 실제로는 `app/db/local_db.py`, `app/db/messages_cache.py`가 존재하고 클라 SQLite cache도 사용된다.

판정: **DB 문서가 실제 구현을 전수 반영하지 못함.**

### 4.3 README 빠른 시작

[README.md](../../README.md) 는 “본 Phase 스켈레톤은 시그널링 자동 연결을 수행하지 않는다”, `rtc/` 예정, 운영 문서 작성 예정 같은 과거 문구를 포함한다. 실제 트리와 구현 수준을 반영하도록 갱신이 필요하다.

판정: **사용자 안내 문서 드리프트.**

### 4.4 Coverage 해석

[pyproject.toml](../../pyproject.toml) 의 coverage omit 범위가 매우 넓다. `app/ui/_*_mixin.py`, `app/ui/main_window.py`, RTC binding, 여러 net client, server auth/api 일부가 제외되어 있다.

판정: **coverage 90.45%는 “전체 제품 품질 90%”가 아니라 “측정 대상 기준 90%”로 해석해야 함.**

### 4.5 macOS 앱 배포

[README.md](../../README.md) 와 [History.md](../../History.md) 에 PyInstaller `.app` Team ID mismatch, codesign 실패, Nuitka 또는 Developer ID 필요성이 남아 있다.

판정: **소스 실행과 Windows 빌드 경로는 강하지만 macOS `.app` 실사용 배포는 보류.**

## 5. 구조 리스크

가장 큰 구조 리스크는 `MainWindow` 중심 UI 결합이다.

현재 `app/ui/main_window.py` 는 20개 안팎의 mixin을 상속하고, 로그인 이후 세션 상태, 채팅, 친구, 폴더, 봇, 원격, 업데이트, 트레이, dialog routing을 한 객체에 모은다. 이미 별도 Exec Plan [2026-05-25-mainwindow-di-refactor.md](../exec-plans/active/2026-05-25-mainwindow-di-refactor.md) 가 존재하며, 전면 DI보다 skip 분류 후 단계적 격리가 타당하다는 결론이 기록되어 있다.

권장 방향.

1. dead/중복 skip 제거
2. asyncSlot 직접 호출 부적합 테스트 정리
3. 실제 QWidget wiring 계열은 subprocess 격리 또는 presenter 추출
4. 1 mixin = 1 file = 1 commit 단위로 회귀 확인

## 6. 우선순위

### P0

1. `SignalingClient` 실제 backoff reconnect + reJOIN + 상태 복구 구현.
2. 자동 재연결 통합 테스트를 `SignalingClient` 기반으로 작성.
3. `README.md`, `Structure.md`, `MIGRATION_MARIADB.md` 의 과거 표현 정리.

### P1

1. coverage omit 목록 축소: `app/net/signaling_client.py`, RTC binding, server signaling부터 복구.
2. skip 38건 중 hang 계열 UI 테스트 격리.
3. SQLite unclosed database ResourceWarning 원인 추적.

### P2

1. macOS `.app` 실행성 회수: Developer ID, Nuitka, rpath refactor 중 하나 결정.
2. DB 문서 strict 모드 정책 결정: 핵심 7개 문서 유지 또는 25개 전수 문서화.
3. 제품화 평가 snapshot의 낙관 표현을 로컬 검증 근거 중심으로 재작성.

## 7. 불일치 방지 방법

앞으로 개발 항목과 문서가 다시 어긋나지 않게 하려면 “문서를 더 많이 쓰기”보다 **상태 전이를 기계가 검증 가능한 형태로 제한**해야 한다.

### 7.1 상태 라벨을 증거 기반으로 고정

문서 안 상태 라벨은 다음 정의로만 쓴다.

| 라벨 | 허용 조건 |
|---|---|
| `TODO` | 요구만 있고 코드·테스트 없음 |
| `PARTIAL` | 코드 또는 테스트 중 하나만 있거나, 앱 wiring / 배포 / 수동 QA 중 하나가 비어 있음 |
| `IMPLEMENTED` | 코드 + 자동 테스트 PASS + 문서 링크가 모두 있음 |
| `VERIFIED` | `IMPLEMENTED` + 수동 QA 또는 배포 산출물 실행 증거 있음 |
| `DEFERRED` | 명시적으로 뒤로 미룬 항목. 이유와 재개 조건 필요 |

`DONE`, `완료`, `PASS` 는 `VERIFIED` 와 같은 강도로 취급한다. 자동 테스트만 통과한 상태는 `IMPLEMENTED` 까지만 허용한다.

### 7.2 FR/NFR 추적표를 단일 소스로 운영

[Specification.md](../../Specification.md), [CheckList.md](../../CheckList.md), [Structure.md](../../Structure.md) 에 흩어진 FR/NFR 매핑을 하나의 표준 행 구조로 맞춘다.

필수 열.

- `id`: FR-xx 또는 NFR-xx
- `status`: TODO / PARTIAL / IMPLEMENTED / VERIFIED / DEFERRED
- `code_refs`: 실제 파일 링크 1개 이상
- `test_refs`: 테스트 파일 또는 수동 QA 문서 링크
- `doc_refs`: 관련 정책·요구사항 문서 링크
- `last_verified`: YYYY-MM-DD
- `evidence`: 명령 결과 또는 workflow run id

이 표에서 `status=VERIFIED` 인데 `test_refs` 나 `evidence` 가 비어 있으면 CI가 실패해야 한다.

### 7.3 “예정” 문구 자동 차단

이미 존재하는 파일이나 구현된 기능을 가리키면서 `(예정)`, `작성 예정`, `스켈레톤`, `Task #`, `placeholder`, `Phase 후반 활성` 같은 표현이 남으면 drift 후보로 본다.

권장 검사.

```bash
rg -n "예정|작성 예정|스켈레톤|Task #|placeholder|Phase [0-9]+ .*활성" README.md Specification.md Structure.md MIGRATION_MARIADB.md CheckList.md docs/assessments
```

검사 결과는 전부 제거하는 방식이 아니라, 각 항목을 다음 셋 중 하나로 분류한다.

1. 실제 미구현이면 `DEFERRED` 로 바꾸고 재개 조건 기록
2. 구현 완료면 실제 코드·테스트 링크로 교체
3. 의도적 placeholder면 owner와 만료일 기록

### 7.4 DB 문서 strict 모드 단계적 도입

현재 `tools/check_migration_tables.py` 는 기본값으로 “문서 테이블이 SQL에 존재하는가”만 본다. DB drift를 강하게 막으려면 두 단계로 올린다.

1. Phase A: `--strict` 결과를 doc-gardener summary에 warning으로 게시
2. Phase B: SQL 테이블 25개 전수 문서화 후 `--strict` 를 CI 차단 게이트로 승격

전수 문서화 전 strict를 바로 차단하면 기존 의도적 부분 문서가 전부 실패하므로, 먼저 `MIGRATION_MARIADB.md` 와 `Structure.md` ERD를 실제 25개 테이블 기준으로 맞춘다.

### 7.5 PR 템플릿에 정합 증거 추가

PR 본문에 다음 체크를 강제한다.

```text
## Docs Sync
- [ ] Specification / CheckList / Structure 중 영향 문서 갱신
- [ ] README 변경 이력 1행 추가
- [ ] History.md 1행 prepend
- [ ] FR/NFR status 변경 시 code_refs/test_refs/evidence 갱신
- [ ] "(예정)" 문구가 실제 구현 파일을 가리키지 않음
- [ ] DB 변경 시 MIGRATION_MARIADB.md + Structure.md ERD 동시 갱신
```

코드 변경 PR에서 위 항목이 비어 있으면 reviewer가 차단한다.

### 7.6 doc-gardener 검사를 “링크”에서 “의미”로 확장

현재 doc-gardener는 링크·frontmatter·스테일·BPE 위주다. 다음 검사를 추가하면 드리프트를 훨씬 빨리 잡는다.

- README/Structure 안 “예정” 파일이 실제 존재하면 warning
- CheckList `done` 항목의 `code_refs` 파일이 없으면 fail
- CheckList `done` 항목의 `test_refs` 가 없으면 fail
- `MIGRATION_MARIADB.md` tables 배열과 SQL migration table 목록 비교
- coverage omit 파일이 `VERIFIED` 기능의 핵심 코드면 warning
- e2e/수동 QA 필요한 NFR이 자동 테스트만으로 `VERIFIED` 되면 fail

### 7.7 릴리즈 직전 “정합 스냅샷”을 별도 산출

릴리즈 후보마다 `docs/assessments/release-readiness-YYYY-MM-DD.md` 를 생성한다. 이 문서는 다음 5개만 본다.

1. FR/NFR 상태표
2. 자동 테스트 결과
3. 수동 QA 결과
4. 배포 산출물 실행 증거
5. 문서 drift 검사 결과

이 snapshot이 통과하기 전에는 `productization.md` 에 강한 완료 표현을 쓰지 않는다.

## 8. 다음 Claude 진입 메모

다음 세션은 새 기능 추가보다 정합성 회수를 우선한다.

추천 시작 순서.

1. `git status -sb` 로 기존 변경 확인.
2. `docs/assessments/current-project-review.md` 본 문서 확인.
3. `app/net/signaling_client.py` 재연결 구현 여부 확인.
4. `README.md`, `Structure.md`, `MIGRATION_MARIADB.md` 드리프트 수정 계획 수립.
5. 수정 전후 `python3 tools/md_agents.py`, `bash tools/doc-lint.sh`, `.venv/bin/pytest -q -x --ignore=tests/e2e -m "not integration and not e2e"` 실행.

## 9. 결론

TooTalk 는 기능 자산과 테스트 자산이 충분히 있는 프로젝트다. 현재 병목은 “무엇을 더 만들 것인가”보다 “문서·테스트·배포 판정이 실제 구현과 같은 말을 하게 만들 것인가”다. 자동 재연결, DB 정본, README, coverage omit, UI skip을 회수하면 제품화 신뢰도가 크게 올라간다.
