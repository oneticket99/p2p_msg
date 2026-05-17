<!-- markdownlint-disable MD041 -->
<!--
TooTalk(p2p_msg) PR 템플릿 — release-agent 정합
사용자 directive 2026-05-17 — 모든 PR 의 본 양식 충족 의무.
정본 [CLAUDE_HARNESS_IMPORTANT.md] §L (CI 강제 게이트) + §R (작업 완료 정의) 정합.
PR 본문 = H2 시작 의무 (GitHub PR 제목 → H1 역할), MD041 disable 정합.
-->

## 요약 (1~3 문장)

<!-- 본 PR 의 핵심 변경 1~3 문장. WHY 우선 (WHAT 은 diff 의 자명). -->

## 변경 분류

<!-- 해당 항목 [x] 표시 (다중 가능). -->

- [ ] feat (신규 기능)
- [ ] fix (버그 정정)
- [ ] docs (문서 단독 변경)
- [ ] chore (빌드/도구/메타)
- [ ] refactor (의미 변경 없는 리팩터)
- [ ] test (테스트 단독)
- [ ] ci (CI workflow 변경)
- [ ] perf (성능 최적화)

## 영향 범위

<!-- 변경이 영향을 미치는 모듈 / 사용자 / 운영 영역 명시. -->

| 영역 | 영향 | 비고 |
|---|---|---|
| 클라 (`app/`) | / | |
| 서버 (`server/`) | / | |
| 도구 (`tools/`) | / | |
| 문서 (`docs/` + 루트 .md) | / | |
| CI (`.github/workflows/`) | / | |
| 메모리 가드레일 | / | |

## M1~M7 게이트 체크리스트

- [ ] **M1** 문서가 코드보다 앞선다 — `docs/` 또는 `*.md` 동행 변경
- [ ] **M2** `README.md` "변경 이력" 1줄 prepend (30행 상한)
- [ ] **M3** `History.md` 역순 prepend (최신 Phase 상단)
- [ ] **M4** 신규/수정 `.py` / `.js` / `.html` / `.css` / `.sql` / `.sh` 한글 주석 1줄 이상
- [ ] **M5** 작업 완료 즉시 `git commit` + `push` 정합 (로컬 백로그 0)
- [ ] **M6** `data/wbs.sqlite` 의 directive 1행 등록 (인프라 준비 후)
- [ ] **M7** 텔레그램 작업 보고 송신 (HTTP API 또는 MCP)

## lint + 가드레일 통과

- [ ] `npx markdownlint-cli2 "**/*.md"` 0 위반
- [ ] `bash tools/doc-lint.sh` 통과 (BPE + 링크 + frontmatter + 빈 줄 + 1인칭/3인칭 5종)
- [ ] BPE 위생 — U+CE21 단독 의존명사 0건
- [ ] 1인칭/3인칭 대명사 — 0건 (사용자 인용 영역 마스킹)
- [ ] 루트 .md 정확히 18 (정본 §K 동결)

## CI 3 workflow 결과

- [ ] `ci.yml` 7 게이트 GREEN
- [ ] `docs-lint.yml` GREEN
- [ ] `doc-gardener.yml` (스케쥴 외 dispatch 시) GREEN

## reviewer-agent + qa-agent + observability-agent

- [ ] `@reviewer-agent` PASS (M1~M7 + 금지 패턴 + 정본 §A~§S 정합)
- [ ] `@qa-agent` PASS (회귀 + 스모크 통과)
- [ ] `@observability-agent` PASS (로그/메트릭/성능 baseline 정합)

## 사용자 directive 정합

<!-- 본 PR 의 사용자 directive 원문 인용 + 출처 commit/메모리 명시. -->

- 출처:
- 원문:
- 가드레일 정합 (해당 시): [[feedback-...]]

## 후속 task

<!-- 본 PR 의 후속으로 발생한 task 목록. handoff §9 또는 신규 task 추가 명시. -->

-

## 머지 후 조치

- [ ] 머지 직후 `@history-agent` 의 `History.md` SHA 갱신
- [ ] 머지 직후 텔레그램 송신 (커밋 SHA + 누계 cycle 명시)
- [ ] `docs/exec-plans/active/` 의 해당 task 상태 갱신
- [ ] `docs/assessments/productization.md` + `vibe-coding.md` snapshot 갱신 (CLAUDE.md §10-7 정합)
- [ ] `docs/html/` 의 `.html` 동시 갱신 (CLAUDE.md §10-6 정합)

<!--
참고:
- 정본: ../CLAUDE_HARNESS_IMPORTANT.md
- 운영 규약: ../CLAUDE.md
- 저장소 맵: ../AGENTS.md
- 메모리 인덱스: ~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/MEMORY.md
- 본 PR 의 force push (--force, --no-verify, --no-gpg-sign) 절대 금지 — 사용자 명시 허용 외
-->
