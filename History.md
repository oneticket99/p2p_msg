---
title: "TooTalk 개발 히스토리"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# TooTalk 개발 히스토리

> 로그 형식: `[YYYY-mm-dd H:i:s] 내용 (단축 SHA)`
> M3 — 역순 기록: 최신 Phase·최신 타임스탬프가 문서 상단
> append 금지, prepend 전용 (`tools/md_agents.py` 가 추후 검증 예정)

---

## 0. 본 문서 운영 규약

본 문서는 [CLAUDE_HARNESS_IMPORTANT.md](CLAUDE_HARNESS_IMPORTANT.md) §A M3 와 §I 의 정본 규약을
저장소 루트에 구현한 운영 문서다. 다음 규칙을 강제한다.

1. **역순 기록 (prepend 전용)** — 최신 타임스탬프가 항상 문서 상단. 오래된 항목을 상단에 끼워
   넣는 append 패턴은 금지한다. `@history-agent` 가 단일 진입점이며 `tools/md_agents.py` 의
   `agent_history()` 가 Phase 번호·타임스탬프 내림차순을 강제할 예정이다.
2. **Phase 그룹화** — 동일 Phase 내부에서도 최신 → 과거 내림차순. Phase 헤더 자체도 큰 번호가
   상단. 본 문서 시점은 Phase 1 진행 중이며 Phase 0 (정본 인계) 한 항목이 하단에 위치한다.
3. **M2 동시 갱신 의무** — 모든 파일 작업 단위 완료 시 `README.md` 변경 이력에도 한 줄
   prepend (정본 §H). 본 문서가 단독으로 갱신되는 일은 없다. (현 시점 `README.md` 미생성 상태
   — Phase 1 후반 신설 예정. 신설 시 본 항도 동시 갱신.)
4. **BPE 위생** — 한국어 의존명사 단독 사용 금지 (합성어 측면·관측·측정·좌측·우측·추측만
   허용). `tools/doc-lint.sh` 의 검사 1번이 grep -E 정규식으로 단독 의존명사 토큰을 차단한다.
   허용 합성어 6 종 외 문맥은 다른 표현으로 정정해야 한다.
5. **타임스탬프 출처** — `git log --pretty=format:'%aI %h'` 의 실 commit 메타. 가짜 commit
   발명 금지. 본 문서의 모든 행은 실재 SHA 와 1:1 대응한다.

---

## Phase 1 MVP 부트스트랩 (2026-05-17 진행 중)

본 Phase 의 목표는 PyQt6 + aiortc + qasync 기반 데스크탑 P2P 메신저 의 MVP 골격 확보다.
시그널링 서버·클라이언트 스켈레톤, 9 정책 문서, 운영 문서(Specification·Structure), 가드레일
도구(doc-lint·markdownlint), 7 프로세스 에이전트 정의를 단일 일자에 집중 투입한다.

[2026-05-17 11:23:50] Structure.md 신설 — 운영 3/8, 527행 mermaid 6 ERD + MariaDB 4 테이블 (39bd0a9)
[2026-05-17 11:19:01] FRONTEND.md §14 wireframe/mockup 섹션 추가 — UI 표면 5 mermaid 도식 (0fd29ba)
[2026-05-17 11:18:48] Specification.md 신설 — 운영 1/8, FR 10 + User Story 9 + DB MariaDB 명시 (b3efb2b)
[2026-05-17 11:09:05] tools/doc-lint.sh 신설 — M4 가드레일 (BPE 위생·링크·frontmatter·연속 빈 줄) (8c45f10)
[2026-05-17 11:03:51] .markdownlint.json 신설 — markdown lint 가드레일 사전 작업 (2f33da0)
[2026-05-17 11:03:07] SECURITY.md 신설 — 9 정책 8/9 (44288ab)
[2026-05-17 10:55:07] QUALITY_SCORE.md 신설 — 9 정책 7/9 (d240179)
[2026-05-17 10:54:55] PRODUCT_SENSE.md 신설 — 9 정책 6/9 (aa31bd9)
[2026-05-17 10:54:20] RELIABILITY.md 신설 — 9 정책 5/9 (4f79813)
[2026-05-17 10:54:06] PLANS.md 신설 — 9 정책 4/9 (3a13cfc)
[2026-05-17 10:53:53] FRONTEND.md 신설 — 9 정책 3/9 (b877653)
[2026-05-17 10:53:20] DESIGN.md 신설 — 9 정책 2/9 (af54042)
[2026-05-17 10:52:29] ARCHITECTURE.md 신설 — 9 정책 1/9 (4c23e11)
[2026-05-17 10:33:00] PyQt6 + qasync 클라이언트 스켈레톤 push (1635행, 14 파일, M1·M4) (1fb7ba3)
[2026-05-17 10:23:58] aiohttp WebSocket 시그널링 서버 스켈레톤 push (1121행, 7 파일, M1·M4) (7f10179)
[2026-05-17 10:16:16] .claude/agents 7 프로세스 에이전트 정의 push (600행, M1·M4) (5264d43)
[2026-05-17 10:08:44] 실행계획 TD-6 행 BPE 위생 정정 — 단독 의존명사 제거 (6dbbe06)
[2026-05-17 10:08:22] Phase 1 MVP 실행계획 + CI self-hosted 정책 반영 (M1) (5eac245)
[2026-05-17 10:01:17] 정본 정독 대상 등록 + Claude CLI Telegram wrapper 추가 (M1·M4) (5268a75)
[2026-05-17 09:54:13] AGENTS.md TooTalk 서비스명 명문화 (M1) (928c2bf)
[2026-05-17 09:36:27] 부트스트랩 — AGENTS.md + .gitignore + .env.example 초기화 (M1) (9f67eeb)

### Phase 1 누계 (2026-05-17 기준)

- commit 수: 21 건 (`9f67eeb` ~ `39bd0a9`)
- 신규 루트 마크다운: 14 종 (AGENTS, ARCHITECTURE, DESIGN, FRONTEND, PLANS, PRODUCT_SENSE,
  QUALITY_SCORE, RELIABILITY, SECURITY, Specification, Structure, .markdownlint.json,
  History.md — 본 문서, 본 누계 행 prepend 시점)
- 신규 코드 산출물: PyQt6 클라이언트 스켈레톤 14 파일 / aiohttp 시그널링 서버 7 파일
- 신규 가드레일: `tools/doc-lint.sh` (4 검사) + `tools/claude-telegram.sh` wrapper
- 신규 에이전트 정의: `.claude/agents/` 7 종 (7 프로세스 분리)

---

## Phase 0 정본 인계 (2026-05-15)

[2026-05-15 15:57:00] CLAUDE_HARNESS_IMPORTANT.md 정본 인계 — 저장소 외부 watcher 산출물,
저장소 루트 직접 배치 (44706 bytes). 본 정본이 M1~M5, 9 정책, 루트 동결(18 한도), CI 강제
게이트, docs/policies 위임 구조 전부를 단일 출처로 정의한다. 본 시점부터 모든 신규 문서·코드·
운영 변경의 1차 정합 기준이 된다.

---

## 부록 A. 명령 인용 (검증용)

본 문서의 실재성을 재현하려면 저장소 루트에서 다음 명령을 실행한다.

```bash
# 실 commit 목록 (최신 → 과거 내림차순)
git log --pretty=format:'%aI %h %s'

# 누계 commit 수
git log --pretty=format:'%h' | wc -l

# BPE 위생 + 전체 doc-lint 게이트 (본 문서 단독)
bash tools/doc-lint.sh History.md
```

세 명령 모두 0 매치·exit 0 가 정상이다. 매치 발생 시 해당 행을 합성어로 정정하거나 다른 표현
으로 대체한 뒤 재실행한다.

---

## 부록 B. Phase 정의 (작업 단위 구분)

| Phase | 기간 | 주제 | 산출물 핵심 |
|---|---|---|---|
| Phase 0 | 2026-05-15 | 정본 인계 | `CLAUDE_HARNESS_IMPORTANT.md` 저장소 배치 |
| Phase 1 | 2026-05-17 ~ 진행 중 | MVP 부트스트랩 | 9 정책 + 운영 2종 + 코드 스켈레톤 + 가드레일 |
| Phase 2 | (예정) | 시그널링 ↔ 클라이언트 결선 | WebRTC DataChannel E2E 송수신 검증 |
| Phase 3 | (예정) | SQLite 로컬 저장 + 진행률 UI | 송수신 ProgressBar + 메시지 영속화 |
| Phase 4 | (예정) | macOS·Windows 매트릭스 빌드 | PyInstaller + GitHub Actions self-hosted |

Phase 전환은 다음 조건 충족 시 `@history-agent` 가 새 Phase 헤더를 본 문서 상단에 prepend
한다.

1. 직전 Phase 의 목표(`PLANS.md` 측면 정의) 가 100% 달성됨
2. 정본 `CLAUDE_HARNESS_IMPORTANT.md` 의 M1~M5 게이트 전부 통과
3. `tools/doc-lint.sh` 와 `.github/workflows/ci.yml` 전체 강제 게이트 통과
4. `README.md` 변경 이력(M2) 에도 Phase 전환 행이 동시 prepend

---

## 부록 C. 정본 정합 매핑

| 본 문서 항목 | 정본 위치 | 강제 |
|---|---|---|
| 역순 prepend | §A M3 / §I | CI "History.md 역순 검증(M3)" |
| 30 행 상한 (README) | §H | CI "README.md 변경 이력 존재 확인" |
| BPE 위생 | §J 인접 운영 합의 | `tools/doc-lint.sh` 검사 1 |
| frontmatter 필수 필드 | docs-lint.yml | `tools/doc-lint.sh` 검사 3 (본 문서는 루트라 면제) |
| Phase 그룹화 | §I 구조 도식 | `@history-agent` `tools/md_agents.py` |
| 루트 마크다운 18 동결 | §K | CI "Root markdown 개수 동결 확인" |

본 문서는 루트 직접 배치이므로 `docs/**` frontmatter 강제 검사(검사 3) 의 대상이 아니다. 다만
가독성·소유권 명시 목적으로 동일 4 필드(title·owner·last_verified·status) frontmatter 를
자발 부착한다.

---

## 부록 D. 갱신 절차 (운영자용)

1. 작업 단위 완료 → `git commit` (M5 즉시 push 포함)
2. `git log -1 --pretty=format:'%aI %h %s'` 로 신규 commit 메타 추출
3. 본 문서 "Phase 1 MVP 부트스트랩" 헤더 바로 아래 빈 줄 다음 행에 다음 형식으로 **prepend**
   - `[YYYY-mm-dd HH:MM:SS] 요약 — 산출물 핵심 (단축 SHA)`
4. 동일 단위 변경을 `README.md` 변경 이력에도 prepend (M2)
5. `bash tools/doc-lint.sh History.md` 0 위반 확인
6. `tools/doc-lint.sh` 의 검사 1번 (BPE 위생) 0 매치 확인 — 단독 의존명사 토큰 부재
7. `git add History.md README.md && git commit && git push`

Phase 전환 시는 새 `## Phase N` 헤더를 본 문서 가장 위 Phase 블록보다 상단에 prepend 한다.
직전 Phase 의 "누계" 서브헤더(`### Phase N 누계`) 를 동결 시점에 한 번 더 갱신한다.

---

## 부록 E. 변경 이력 (본 문서 자체)

[2026-05-17] History.md 신설 — Phase 1 MVP 부트스트랩 누계 21 건 + Phase 0 정본 인계 1 건
포함. M3 역순 구조·BPE 위생·doc-lint 통과 상태로 commit. 본 항부터 본 문서 자체의 변경도
한 줄씩 prepend 한다.

---

## 부록 F. 누락 회수 정책 (운영 합의)

본 문서 신설 시점에는 누계 21 건의 commit 이 이미 적재된 상태였고, 본 문서 자체가 그 누계를
"한 번에" 흡수하는 형태로 출발한다. 향후 단발성 누락이 발생한 경우의 회수 절차는 다음과
같이 운영한다.

1. **단일 누락** — 누락 commit 1 건을 발견한 시점에 즉시 해당 commit 의 정확한 타임스탬프와
   단축 SHA 로 본 문서에 prepend (역순 무시 금지: 새 행은 항상 본 Phase 헤더 직하 첫 행에 삽입
   되지 않고, 자체 타임스탬프가 정합되는 위치 — 즉 더 최신 행보다 아래·더 과거 행보다 위 —
   에 삽입한다). 본 절차는 `@history-agent` 의 단발 회수 모드로 실행된다.
2. **다수 누락 (5 건 이상)** — `git log --since=<누락 시작> --until=<누락 끝>` 의 출력 전체를
   본 Phase 헤더 직하에 시간 내림차순으로 prepend 한 뒤 단일 commit "docs(history): 누락
   회수 N 건 흡수" 으로 마감. 회수 commit 본인도 다음 갱신 사이클에서 prepend 된다.
3. **타임스탬프 충돌** — 동일 초 단위 commit 이 둘 이상인 경우 단축 SHA 사전순으로 정렬해
   본 문서 내 행 순서를 결정한다. SHA 사전순은 안정적 정렬이므로 재실행 결과가 동일하다.
4. **회수 후 검증** — `tools/doc-lint.sh History.md` + 본 문서 부록 A 의 self-check 명령을
   순차 실행해 0 위반·실재성을 확보한 뒤 push.

---

## 부록 G. 본 문서가 답하지 않는 것 (위임 경계)

본 문서는 "언제 무엇이 일어났는가" 의 시계열 로그다. 다음 항목은 본 문서가 다루지 않으며,
각각 명시된 정본·운영 문서로 위임한다.

| 위임 대상 질문 | 답하는 문서 |
|---|---|
| "왜 그 결정을 내렸나" 의 논거 | `DESIGN.md` · `ARCHITECTURE.md` · `PLANS.md` |
| "어떤 기능을 만들기로 했나" | `Specification.md` (FR 10 + User Story 9) |
| "코드 구조는 어떻게 되나" | `Structure.md` (mermaid 6 + ERD MariaDB 4 테이블) |
| "보안/품질 정책은 무엇인가" | `SECURITY.md` · `QUALITY_SCORE.md` · `RELIABILITY.md` |
| "현재 진행률은" | `CheckList.md` (Phase 1 후반 신설 예정) |
| "정본 규약 자체는" | `CLAUDE_HARNESS_IMPORTANT.md` (저장소 외부 watcher 산출물) |
| "운영자 가이드는" | `AGENTS.md` (저장소 맵) |

본 문서를 읽는 사람이 "왜?" 를 묻는다면 위 표의 우측 컬럼으로 이동해야 한다. 본 문서는
"무엇이·언제" 만 답한다.

---

## 부록 H. CI 강제 게이트 진척 (Phase 1 시점)

본 문서 신설 시점에 정본 §L 의 3 종 워크플로우 중 로컬 등가 가드레일만 가용 상태다. 원격
GitHub Actions self-hosted runner 구성은 Phase 1 후반에 합류한다.

| 게이트 | 현 상태 | 책임 |
|---|---|---|
| `ci.yml` 본체 | 미구성 | Phase 1 후반 신설 |
| `docs-lint.yml` 등가 | `tools/doc-lint.sh` 로컬 가용 | 본 문서 부록 A 의 self-check 로 매 commit 전 확인 |
| `doc-gardener.yml` | 미구성 | Phase 1 종료 후 합류 |
| History.md 역순 검증 (M3) | 미구성 → 부록 D 절차로 수동 보장 | `@history-agent` 합류 시 자동화 |
| README.md 변경 이력 (M2) | `README.md` 미존재 → 신설 시 동시 도입 | Phase 1 후반 |
| 한글 주석 (M4) | 코드 스켈레톤 단계에서 수동 준수 중 | CI 합류 시 자동 검사 |
| 루트 마크다운 18 동결 (K) | 현 13 / 18 (본 문서 포함) | 추가 5 개 여유 |

본 표는 Phase 1 마감 시점에 모든 항이 "구성 완료"로 전환되어야 한다. 미전환 항이 남아 있다면
Phase 2 진입 조건(부록 B 의 4 조건) 을 충족하지 않은 것으로 간주한다.
