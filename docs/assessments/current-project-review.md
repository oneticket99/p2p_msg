---
title: "TooTalk 현재 프로젝트 전수 검토 요약"
owner: oneticket99
last_verified: 2026-05-23T00:17:49+09:00
status: active
---

# TooTalk 현재 프로젝트 전수 검토 요약

> 검토 기준: 2026-05-23 00:17 KST 로컬 작업 트리.
> 범위: 문서, CI, 테스트 정합, 핵심 UI 구조, 운영 자동화, 제품화 가능성.
> 방식: 읽기 전용 검토 결과 정리. 본 문서는 코드 수정 결과가 아니라 평가 기록이다.

## 1. 종합 평가

**현재 점수: 6.3 / 10**

TooTalk 는 PyQt6 데스크탑 메신저, WebRTC, MariaDB, 친구 관리, 봇, 원격 제어, i18n, 자동 업데이트, 배포 인프라까지 넓은 기능 자산을 이미 보유한다. 다만 출시 가능한 안정 제품으로 보기에는 정합성, 테스트 신뢰도, 구조 피로도 문제가 남아 있다.

핵심 판단은 다음과 같다.

- 기능 부족보다 기능 누적 속도가 더 큰 리스크다.
- 문서화는 강하지만, 일부 문서와 실제 파일 상태 사이 드리프트가 보인다.
- 테스트 파일은 많지만, 기대값과 구현이 어긋난 지점이 존재한다.
- `MainWindow` 중심 UI 구조가 커져 회귀 가능성이 높다.
- CI 게이트 일부는 문서상 강도보다 실제 차단력이 낮다.

## 2. 주요 리스크

### 2.1 CI 루트 문서 동결 위반 가능성

루트 마크다운 파일은 현재 19개다. CI는 정확히 18개를 요구한다. `PORTABLE_HARNESS.md`가 추가된 상태라면 root-freeze 게이트에서 실패할 가능성이 높다.

관련 근거:

- `.github/workflows/ci.yml` 의 `root-18-freeze` job
- 루트 마크다운 목록 19개

### 2.2 정본 문서와 도구 상태 불일치

정본 문서는 `tools/md_agents.py`를 M1~M4 검증 도구로 안내하지만, 현재 파일 시스템에는 해당 파일이 없다. 이 상태는 문서 신뢰도와 자동화 재현성을 동시에 떨어뜨린다.

관련 근거:

- `CLAUDE_HARNESS_IMPORTANT.md` 의 `tools/md_agents.py` 언급
- `AGENTS.md` 부록 A 의 `python tools/md_agents.py`
- 실제 `tools/md_agents.py` 부재

### 2.3 테스트 기대값과 구현 불일치

cycle 169.715 — `youtube_client` 삭제 (사용자 directive). 잔존 streaming client = chzzk/kick/twitch 3종. 본 항목 해소.

관련 근거:

- `tests/app/bot/streaming/test_streaming_clients.py` (3 platform x 3 test = 9 PASS)

### 2.4 coverage 게이트 약화

CI의 coverage 80% 단계가 `continue-on-error: true`로 설정되어 있다. 문서상 품질 게이트로는 강하게 설명되지만 실제 PR 차단력은 약하다.

관련 근거:

- `.github/workflows/ci.yml` coverage 단계

### 2.5 `MainWindow` 과대화

`app/ui/main_window.py`는 약 4,000줄 규모다. 채팅, 친구 요청, 트레이, 로그아웃/재로그인, 봇, 원격, 폴더, 배지 갱신 흐름이 한 클래스에 몰려 있다. 단기 개발 속도에는 유리했지만, 회귀 대응과 테스트 작성에는 불리하다.

특히 최근 추가된 흐름 중 다음 영역은 분리 후보다.

- system tray 및 close-to-hide 동작
- 로그아웃 후 LoginDialog 재진입
- 친구 요청 수신 dialog와 pending badge
- 친구 검색 및 요청 발신
- drawer geometry 동기화

### 2.6 제품화 평가 문서의 낙관 편향

`docs/assessments/productization.md`에는 “pytest 1817 retain”, “telegram align 98%”처럼 강한 표현이 많다. 현재 로컬 상태의 CI 리스크와 테스트 불일치를 반영하면 실제 제품화 점수는 해당 문서보다 낮게 보는 편이 타당하다.

## 3. 강점

- 기능 폭이 넓고 제품 방향이 명확하다.
- 서버 API, repository, migration 구조는 비교적 체계적이다.
- 테스트 파일 수가 많고 영역도 넓다.
- 문서화 문화와 운영 규칙이 강하다.
- Toonation BI, 봇, 원격 지원을 결합한 차별화 방향이 있다.
- 자체 호스팅, Docker, SMTP, nginx, release workflow 등 운영 기반이 이미 갖춰져 있다.

## 4. 제품화 판단

현 단계는 **외부 사용자 배포 직전 단계가 아니라 내부 dogfooding 안정화 단계**로 보는 것이 적절하다.

출시 판단에 필요한 최소 조건:

- CI root-freeze 실패 요인 해소
- `tools/md_agents.py` 정본 참조 복구 또는 제거
- pytest 기대값과 구현 상태 정합
- `MainWindow` 주요 책임 분리
- 제품화 평가 문서의 실제 검증 결과 반영
- 핵심 사용자 흐름 수동 QA 재확인

## 5. 우선순위

1. 루트 마크다운 19개 문제 정리
2. `tools/md_agents.py` 부재 문제 정리
3. streaming client 테스트와 구현 정합
4. `MainWindow` 책임 분리 계획 수립
5. coverage 게이트 차단력 복구
6. 평가 문서 점수와 근거 재작성

## 6. 결론

TooTalk 는 “만들 수 있음”은 충분히 보여준 프로젝트다. 다음 단계의 핵심은 새 기능 확대가 아니라 “계속 안전하게 고칠 수 있음”을 증명하는 일이다. 기능 개발 속도보다 검증 신뢰도와 구조 안정성을 우선해야 제품화 가능성이 올라간다.
