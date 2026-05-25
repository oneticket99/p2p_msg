---
title: "TooTalk 현재 프로젝트 전면평가"
owner: oneticket99
last_verified: 2026-05-25T13:40:25+09:00
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

## 7. 다음 Claude 진입 메모

다음 세션은 새 기능 추가보다 정합성 회수를 우선한다.

추천 시작 순서.

1. `git status -sb` 로 기존 변경 확인.
2. `docs/assessments/current-project-review.md` 본 문서 확인.
3. `app/net/signaling_client.py` 재연결 구현 여부 확인.
4. `README.md`, `Structure.md`, `MIGRATION_MARIADB.md` 드리프트 수정 계획 수립.
5. 수정 전후 `python3 tools/md_agents.py`, `bash tools/doc-lint.sh`, `.venv/bin/pytest -q -x --ignore=tests/e2e -m "not integration and not e2e"` 실행.

## 8. 결론

TooTalk 는 기능 자산과 테스트 자산이 충분히 있는 프로젝트다. 현재 병목은 “무엇을 더 만들 것인가”보다 “문서·테스트·배포 판정이 실제 구현과 같은 말을 하게 만들 것인가”다. 자동 재연결, DB 정본, README, coverage omit, UI skip을 회수하면 제품화 신뢰도가 크게 올라간다.
