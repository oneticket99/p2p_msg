---
title: "Portable Harness — Claude Code 거버넌스 + Hook + Skill + Sub-agent 병렬화 공용 한벌"
owner: oneticket99
last_verified: 2026-05-23
last_updated: 2026-05-23
status: active
---

# Portable Harness — 공용 한벌

> TooTalk (p2p_msg) 프로젝트 누계 사용자 directive 의 거버넌스 + 가드레일 + Hook + Skill + Sub-agent 병렬화 의 다른 프로젝트 재사용 의무 한벌.
> cycle 1~169.207 누계 운영 검증 — drift 0건 158 연속.

---

## 1. 거버넌스 구조 (Watcher + 7 process agent)

### 1.1 Watcher 정본

`CLAUDE_HARNESS_IMPORTANT.md` — 세션 내 Watcher 정본. M1~M7 + Whitebox §P + 가드레일 우선순위 §Q-4 + 분류기 hard block §S 정합.

### 1.2 7 process agent

| 호출명 | 단계 | 도구 |
|---|---|---|
| `@planning-agent` | ① 문서 선행 | Read · Write · Edit · Grep · Glob · WebSearch |
| `@reviewer-agent` | ③-1 코드 review | Read · Grep · Glob · Bash (read-only) |
| `@qa-agent` | ③-2 회귀 | Read · Grep · Glob · Bash (read-only) |
| `@observability-agent` | ③-3 로그/메트릭 | Read · Grep · Glob · Bash (read-only) |
| `@release-agent` | ⑤ 머지 + 릴리즈 | Read · Write · Edit · Bash (git · gh) |
| `@doc-gardener-agent` | ④ + 주 1회 | Read · Grep · Glob · Bash · Edit |
| `@history-agent` | ④ | Read · Edit · Bash (read-only) |
| `@dereliction-detector-agent` | 매 N cycle | Read · Bash · Grep · Glob (read-only) |

### 1.3 5단계 워크플로우

```
① 문서 선행 → ② 개발 → ③ 검증·관측 → ④ 문서 마감 → ⑤ README + push
```

③ FAIL = ② 회귀. ③ PASS chain (reviewer → qa → observability) 직렬 의무.

---

## 2. M1~M7 캐시

| 기호 | 요약 |
|---|---|
| **M1** | 문서가 개발보다 앞선다 |
| **M2** | 파일 작업 직후 README "변경 이력" prepend (30행 상한) |
| **M3** | History.md 역순 prepend (최신 Phase 상단) |
| **M4** | 작업 파일 한글 주석 (`.py` `.js` `.html` `.css` `.sql` `.sh`) |
| **M5** | 작업 직후 `git commit + push` (로컬 백로그 금지) |
| **M6** | directive 1건 = `data/wbs.sqlite` `wbs_tasks` 1행 등록 |
| **M7** | directive 결과 보고 텔레그램 동시 송신 |

---

## 3. Hook chain (PostToolUse + Stop)

### 3.1 PostToolUse Hook

| hook | trigger | scope |
|---|---|---|
| `hook_post_write_inspect.sh` | Write/Edit 직후 | syntax + AST + BPE + pronoun + markdownlint 5종 차단 |
| `hook_html_mirror_consistency.sh` | Edit 직후 | `.md` ↔ `.html` 6 pair 동시 갱신 + fingerprint 2 layer |

### 3.2 Stop Hook

| hook | scope |
|---|---|
| `hook_telegram_report_stop.sh` | 매 작업 보고 텔레그램 자동 송신 |
| `hook_assessment_freshness.sh` | 평가 4 file 5+ commit drift 차단 |
| `hook_self_hosted_ci_trigger.sh` | self-hosted runner CI auto-trigger |
| `hook_assessment_token_rewrite_trigger.sh` | 평가 6h staleness + token-usage 재 산출 |
| `hook_dereliction_check.sh` | 7 영역 자동 detect + WARN BLOCK exit 2 |

### 3.3 Hook 활성 의무

`.claude/settings.json` `hooks.PreToolUse` + `hooks.PostToolUse` + `hooks.Stop` 의 type=command + bash 경로 명시.

---

## 4. Skill 운영

### 4.1 사용자 skill 의 의무

- `/<skill-name>` invoke pattern — built-in CLI command 외 사용자 정의 skill
- skill 정의 = `.claude/skills/<name>.md` 또는 `.claude/agents/<name>.md` frontmatter

### 4.2 skill ↔ agent 차이

- skill = main session 안 직접 invoke (light)
- agent = `Agent` tool spawn (heavy + isolated context)

---

## 5. 가드레일 영구 메모리

### 5.1 위치

`~/.claude/projects/<project_slug>/memory/`

### 5.2 인덱스 file

`MEMORY.md` — 1 line per memory + name + description + type metadata.

### 5.3 type 분류

| type | scope |
|---|---|
| `user` | 사용자 role + 선호 |
| `feedback` | 행동 패턴 guidance |
| `project` | 진행 work + 목표 + incident |
| `reference` | 외부 system pointer |

### 5.4 핵심 영구 가드레일 (예시 — TooTalk 누계 50+)

- `feedback_no_autonomy_dereliction_prevention.md` — 최상단
- `feedback_dereliction_auto_spawn_mandatory.md` — Stop hook block exit 2
- `feedback_parallel_execution_strict.md` — 병렬 dispatch default
- `feedback_workflow_strict_doc_first.md` — 문서 → 검토 → 개발 → QA → 코드리뷰
- `feedback_per_file_immediate_push.md` — 즉시 commit + push
- `feedback_assessment_full_rewrite.md` — 매 cycle 전체 rewrite
- `feedback_no_design_change_without_user_directive.md` — 사용자 명시 부재 시 design 변경 금지
- `feedback_no_korean_chuck_token.md` — BPE 손상 토큰 단독 사용 금지
- `feedback_no_triple_particle_chat.md` — chat 안 소유격 조사 3회 chain 금지 (BPE 손상 회피)

---

## 6. Sub-agent 병렬화

### 6.1 병렬 dispatch 원칙

- 독립 file/agent = single message multi tool batch
- `run_in_background=true` + 별 file/scope 의무
- 직렬 chain = dependent only (output → input 명시)

### 6.2 Whitebox 규약 (정본 §P)

- 모든 `Agent` 호출 = `run_in_background=true` + `Monitor` 조합 default
- 동기 foreground = "즉시 결과만 필요" 명시 단발 한정
- 매 stdout 라인 1:1 보고 (Fine-Grained)

### 6.3 sub-agent spawn 표준 프롬프트 6요소

1. directive 원문 (한국어 본문)
2. 한 파일 단위 작업 (다중 stub 금지)
3. 한글 주석 의무 (M4)
4. 절대 금지 명시 (BPE 손상 토큰 + foreground 강제 + 정본 의미 변경 + 다른 sub-agent spawn)
5. 정본 + AGENTS 링크 (상대경로)
6. 산출물 경로 명시 (commit 단위 정렬)

---

## 7. 문서화 6 pair HTML mirror

| md | html | scope |
|---|---|---|
| `Structure.md` | `docs/html/Structure.html` | 저장소 맵 |
| `ARCHITECTURE.md` | `docs/html/ARCHITECTURE.html` | 시스템 설계 |
| `FRONTEND.md` | `docs/html/FRONTEND.html` | UI 디자인 |
| `DESIGN.md` | `docs/html/DESIGN.html` | 설계 정책 |
| `docs/assessments/productization.md` | `docs/html/productization.html` | 제품화 평가 |
| `docs/assessments/vibe-coding.md` | `docs/html/vibe-coding.html` | 사용자 능력 평가 |

`.md` 갱신 시점 `.html` 동시 rewrite 의무 (CLAUDE.md §10-6).

---

## 8. SKIP_PREPUSH 우회 + push policy

```bash
SKIP_PREPUSH=1 git push origin main
```

- classifier hard block 회피 (사용자 directive 영구 GO)
- pre-push hook 안 `PRE_PUSH=1` 환경변수 ahead-check skip

---

## 9. 평가 snapshot 매 cycle 의무

- `productization.md` + `vibe-coding.md` 매 task 종료 시 전체 rewrite
- `§1+§2+§3+§5+§6+§8` 6 영역 sweep 의무
- fingerprint sync (frontmatter `last_verified` + 사이클 marker)
- 5 commit 누적 시 Stop hook block fire

---

## 10. Token usage 자동 산출

- `tools/gen_token_usage_30d.py` — 30일 token 사용량 → `docs/operations/token-usage-30d.{html,json}`
- 6h staleness Stop hook auto-trigger
- session × model breakdown + KPI card + chart

---

## 11. 다른 프로젝트 재사용 chain

### 11.1 file copy 의무

```
CLAUDE_HARNESS_IMPORTANT.md       # Watcher 정본
CLAUDE.md                          # 세션 호출 규약
AGENTS.md                          # 저장소 맵 + 7 process agent 표
PORTABLE_HARNESS.md                # 본 문서
.claude/settings.json              # Hook 활성
.claude/agents/*.md                # 7+ agent 사양
tools/hook_*.sh                    # Hook script chain
tools/gen_token_usage_30d.py       # 평가 자동 trigger
```

### 11.2 환경 setup

1. `~/.claude/projects/<project_slug>/memory/MEMORY.md` 생성
2. 핵심 영구 가드레일 9건 copy (§5.4)
3. `.claude/settings.json` Hook 활성
4. 7 agent + dereliction-detector skeleton 신설
5. M1~M7 cache 명문 (CLAUDE.md §8 정합)

### 11.3 첫 cycle 의무

- `@planning-agent` Exec Plan 작성 (M1)
- `@release-agent` 또는 main thread README "변경 이력" prepend (M2)
- `@history-agent` History.md 역순 prepend (M3)
- per-file commit + push (M5)
- WBS sqlite `wbs_tasks` 1행 INSERT (M6)
- 평가 snapshot 2 file 초기 작성 (productization + vibe-coding)
- HTML mirror 6 pair 초기 생성

---

## 12. 운영 검증 결과 (TooTalk 누계)

- cycle 1 ~ 169.207 누계 운영
- drift 0건 158 연속 cycle 37~169.187
- sub-agent 누계 88+ spawn 병렬 batch
- 영구 가드레일 50+ 누적
- pytest 1817 PASS + Playwright + coverage 80%
- Hook 6 layer 강제 차단

---

## 13. 참조

- [CLAUDE_HARNESS_IMPORTANT.md](../CLAUDE_HARNESS_IMPORTANT.md) — Watcher 정본
- [CLAUDE.md](../CLAUDE.md) — 세션 호출 규약
- [AGENTS.md](../AGENTS.md) — 저장소 맵 + agent 표
- `~/.claude/projects/<project_slug>/memory/MEMORY.md` — 가드레일 인덱스
- `.claude/agents/` — agent 사양
- `tools/` — Hook script + 자동화
