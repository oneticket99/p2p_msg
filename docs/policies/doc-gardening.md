---
title: "Doc Gardening Policy — 문서·코드 drift 자동 보정"
owner: oneticket99
last_verified: 2026-05-25
status: active
---

# Doc Gardening Policy

> 문서·코드·메타데이터 간 drift 감지 + 자동 보정 정책.
> `@doc-gardener-agent` (`.claude/agents/doc-gardener-agent.md`) + `.github/workflows/doc-gardener.yml` 등가 정합.
> 정본 [CLAUDE_HARNESS_IMPORTANT.md](../../CLAUDE_HARNESS_IMPORTANT.md) §H (문서 최신성) + §L (CI 게이트) + §M (위임 의무).

---

## 1. 목적

세션 누적 + 다중 contributor 환경에서 다음 4 drift 차단:

1. **문서-코드 drift** — Structure.md 트리 ↔ 실 파일시스템, MIGRATION_MARIADB.md tables ↔ 코드 `__tablename__`
2. **메타데이터 drift** — frontmatter 필수 4 필드 (title · owner · last_verified · status) 누락
3. **링크 drift** — 깨진 상대 markdown 링크
4. **스테일 drift** — `last_verified` 의 90일 초과
5. **평가 큐 drift** — `current-project-review.md` 가 최신 commit/WBS/MIGRATION 상태와 반대로 말하는 상황

---

## 2. 적용 대상

| 영역 | 의무도 |
|---|---|
| 루트 .md 18 종 (정본 §K 동결) | 의무 |
| docs/** 모든 .md | 의무 |
| docs/html/** HTML 5종 (동시 정리) | 의무 |
| .claude/agents/ 7 에이전트 정의 | 의무 |
| server/README.md + app/README.md | 의무 |
| `tools/*.sh` 의 한글 주석 | 권장 |

---

## 3. 검사 5종 (tools/doc-lint.sh 정합)

1. **BPE 위생** — 한국어 의존명사 U+CE21 단독 사용 금지 (합성어 측면·관측·측정·예측·추측·관측치·관측성·측근·측정값 허용)
2. **깨진 상대 링크** — 모든 markdown 링크 패턴 (대괄호 + 괄호 의 상대 경로) 의 대상 존재 검증
3. **frontmatter 필수 필드** — `docs/**/*.md` 의 `title` · `owner` · `last_verified` · `status` 4 필드
4. **연속 빈 줄** — 3 줄 이상 공백 줄 차단
5. **1인칭/3인칭 대명사** — 1인칭 + 3인칭 대명사 단독 사용 금지 (사용자 가드레일 [[feedback-no-self-other-pronoun]] 정합)

---

## 4. 검사 주기

| 검사 | 주기 | 트리거 |
|---|---|---|
| `ci.yml` 의 docs-lint job | 매 PR / push main | GitHub Actions |
| `docs-lint.yml` | cron 매일 00:00 UTC + dispatch + path-filter | GitHub Actions |
| `doc-gardener.yml` | cron 매주 월요일 00:00 UTC + dispatch | GitHub Actions |
| `tools/doc-lint.sh` (로컬) | 파일 수정 직후 (사용자 가드레일 [[feedback-lint-before-push-guardrail]]) | 사용자 직접 |
| `tools/check_assessment_consistency.py` | doc-gardener + meta-enforcement | GitHub Actions / 로컬 |

---

## 5. 오너십 정책

| 영역 | 오너 | 갱신 의무 |
|---|---|---|
| 정본 (`CLAUDE_HARNESS_IMPORTANT.md`) | oneticket99 | 사용자 directive 단독 |
| 정책 9 (`AGENTS` + 8) | oneticket99 | 사용자 directive 또는 reviewer-agent 검토 통과 |
| 운영 8 (`Specification` + 7) | oneticket99 | reviewer-agent 검토 후 |
| 평가 snapshot 2 (`productization` + `vibe-coding`) | Claude (어시스턴트) | 매 task 종료 시 전체 rewrite (CLAUDE.md §10-7) |
| HTML 5 (`docs/html/`) | Claude (sub-agent 위임) | .md 갱신과 동시 (CLAUDE.md §10-6) |
| 메모리 가드레일 (`~/.claude/projects/.../memory/`) | oneticket99 + Claude | 사용자 비판 2회 이상 → Claude 즉시 영구화 |
| 실행계획 (`docs/exec-plans/active/`) | oneticket99 + Claude | Phase 진입 시 갱신 |

---

## 6. drift 감지 → 보정 워크플로우

### 6.1 자동 감지

- `doc-gardener.yml` 의 주 1회 실행
- 5 검사 모두 실행 + `$GITHUB_STEP_SUMMARY` 의 결과 보고
- 90일 스테일 항목 = `::warning::` 로그 + summary 등재
- 위반 1건 이상 = workflow `failure` (사용자 수동 정정 유도)

### 6.2 자동 보정

- `@doc-gardener-agent` spawn → 보정 PR (feature branch `auto/doc-gardener-<run_id>`)
- `.github/workflows/doc-gardener.yml` 이 의미 본문 변경 없이 90일 초과 `docs/**`
  frontmatter `last_verified` 를 현재 UTC 날짜로 자동 갱신한다.
- 변경 발생 시 workflow 안에서 `git commit` + `git push origin "$BRANCH"` + `gh pr create`
  를 실행한다. main 직접 push 는 금지한다.
- 보정 가능 항목 (의미 변경 0):
  - frontmatter 의 누락 필드 = 기본값 채우기
  - 깨진 링크 = 자동 정정 시도 (rename 추적)
  - 스테일 항목 = `last_verified` 갱신 (자동 PR 후 사용자 검토)
- 보정 불가 항목 (사용자 직접):
  - 정본 본문 의미 변경
  - 신규 정책 도입
  - 오너십 변경
  - BPE / 1인칭/3인칭 위반 정정 (의미 정합 필요)
  - 평가 문서 큐 의미 정정 (`current-project-review.md` 최신 cycle/WBS/MIGRATION 모순)

### 6.4 평가 문서 consistency 검사

`tools/check_assessment_consistency.py` 는 Claude 협업 진입점인
`docs/assessments/current-project-review.md` 를 별도로 검사한다.

- HEAD commit 의 `cycle169.NNN` marker 가 평가 문서에 없으면 실패한다.
- `data/wbs.sqlite` 가 존재하고 최신 row 가 HEAD commit `completed` 상태이면, M6 를
  `PARTIAL` 또는 마감 잔존 작업으로 표현하는 문장을 실패 처리한다.
- `tools/check_migration_tables.py --strict` 가 통과하면, MIGRATION strict 를 잔존
  작업으로 표현하는 문장을 실패 처리한다.
- 본 검사는 doc-gardener 와 `tools/meta_enforce.py` 의 자기검증에 모두 연결한다.

### 6.5 머지 게이트

- 보정 PR = `@reviewer-agent` PASS + 사용자 직접 승인 의무
- main 직접 push 금지 (정본 §K 정합)

---

## 7. 위반 처리

| 위반 종류 | 1차 대응 | 2차 대응 |
|---|---|---|
| BPE 단독 의존명사 | doc-lint.sh push 차단 | sed 일괄 정정 |
| 1인칭/3인칭 대명사 | doc-lint.sh push 차단 | 자연 대체 (내/상대/owner/사용자) |
| 깨진 링크 | doc-lint.sh push 차단 | 대상 신설 또는 텍스트 변경 |
| frontmatter 누락 | doc-lint.sh push 차단 | 4 필수 필드 추가 |
| 90일 스테일 | doc-gardener.yml warning | 오너 직접 갱신 또는 archive 이동 |
| 평가 큐 drift | check_assessment_consistency.py 차단 | current-project-review.md 최신 cycle 기준 rewrite |
| 루트 18 동결 위반 | ci.yml root-18-freeze 차단 | docs/ 하위로 이동 |

---

## 8. 본 정책 자체 갱신 절차

본 문서 변경 시:

1. `docs/policies/doc-gardening.md` 본 파일 직접 수정
2. `last_verified` 필드 갱신
3. `tools/doc-lint.sh` 의 5 검사 통과
4. `README.md` 의 변경 이력 1줄 prepend (M2)
5. `History.md` 역순 prepend (M3)
6. `SKIP_PREPUSH=1 git push origin main`

---

## 9. 참조

- 정본: [CLAUDE_HARNESS_IMPORTANT.md](../../CLAUDE_HARNESS_IMPORTANT.md) §H · §L · §M · §S
- 에이전트 정의: [.claude/agents/doc-gardener-agent.md](../../.claude/agents/doc-gardener-agent.md)
- 워크플로우: [.github/workflows/doc-gardener.yml](../../.github/workflows/doc-gardener.yml) · [.github/workflows/docs-lint.yml](../../.github/workflows/docs-lint.yml)
- 도구: [tools/doc-lint.sh](../../tools/doc-lint.sh) · [tools/check_assessment_consistency.py](../../tools/check_assessment_consistency.py) · [.markdownlint.json](../../.markdownlint.json)
- 메모리 가드레일: `feedback-no-korean-chuck-token` · `feedback-no-self-other-pronoun` · `feedback-lint-before-push-guardrail` · `feedback-doc-perfection-before-code`
- 관련 정책: [adoption-roadmap.md](adoption-roadmap.md) · [execution-harness.md](execution-harness.md)
