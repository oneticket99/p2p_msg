---
title: "Portable Harness — Claude Code 거버넌스 + Hook + Guardrail + Trigger + 문서/코드 분리 공용 한벌"
owner: oneticket99
last_verified: 2026-05-24
last_updated: 2026-05-24
status: active
---

# Portable Harness — 공용 한벌

> TooTalk (p2p_msg) 프로젝트 누계 사용자 directive 의 거버넌스 + 하네스 + Hook + Guardrail + Trigger + 문서화 + 코드 분리 구조를 다른 프로젝트로 이식하기 위한 공용 한벌.
> cycle 1~169.743 누계 운영 검증 — M1~M7, Whitebox, Stop hook, L5 meta-enforcement 작성 가이드, dereliction detector, HTML mirror, token usage trigger, feature branch + PR push policy 반영.

---

## 1. 거버넌스 구조 (Watcher + 7 process agent)

### 1.1 Watcher 정본

`CLAUDE_HARNESS_IMPORTANT.md` — 세션 내 Watcher 정본. M1~M7 + Whitebox §P + 가드레일 우선순위 §Q-4 + 분류기 hard block §S 정합.

### 1.2 9 process agent

| 호출명 | 단계 | 도구 |
|---|---|---|
| `@planning-agent` | ① 문서 선행 | Read · Write · Edit · Grep · Glob · WebSearch |
| `@reviewer-agent` | ③-1 코드 review | Read · Grep · Glob · Bash (read-only) |
| `@qa-agent` | ③-2 회귀 | Read · Grep · Glob · Bash (read-only) |
| `@observability-agent` | ③-3 로그/메트릭 | Read · Grep · Glob · Bash (read-only) |
| `@release-agent` | ⑤ 머지 + 릴리즈 | Read · Write · Edit · Bash (git · gh) |
| `@doc-gardener-agent` | ④ + 주 1회 | Read · Grep · Glob · Bash · Edit |
| `@history-agent` | ④ | Read · Edit · Bash (read-only) |
| `@ssh-deploy-agent` | ⑤ 후속 배포 | Read · Bash · Grep · Glob |
| `@dereliction-detector-agent` | 매 N cycle | Read · Bash · Grep · Glob (read-only) |

### 1.3 5단계 워크플로우

```
① 문서 선행 → ② 개발 → ③ 검증·관측 → ④ 문서 마감 → ⑤ README + branch push + PR
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
| **M5** | 작업 직후 `git commit + feature branch push + PR` (로컬 백로그 금지) |
| **M6** | directive 1건 = `data/wbs.sqlite` `wbs_tasks` 1행 등록 |
| **M7** | directive 결과 보고 텔레그램 동시 송신 |

---

## 3. Hook chain (PreToolUse + PostToolUse + Stop)

### 3.0 활성 설정 파일

| file | role |
|---|---|
| `.claude/settings.json` | 공유 hook + permission baseline. PreToolUse/PostToolUse/Stop 등록. |
| `.claude/settings.local.json` | 로컬 머신 권한 cache. git 추적 금지. |
| `.claude/dereliction_disabled.flag` | dereliction Stop hook 임시 retain sentinel. 존재 시 hook 즉시 exit 0. |
| `.claude/dereliction_last_fire.txt` | 동일 HEAD 반복 차단 TTL marker. |

이식 시 `.claude/settings.json` 은 복사하되 local 파일과 sentinel 파일은 프로젝트 정책에 맞게 별도 생성한다.

### 3.1 PreToolUse Hook

| hook | trigger | scope |
|---|---|---|
| `hook_check_bpe_token_input.sh` | Edit/Write/NotebookEdit 입력 전 | BPE 손상 토큰 + 금지 대명사 입력 차단 |

### 3.2 PostToolUse Hook

| hook | trigger | scope |
|---|---|---|
| `hook_post_write_inspect.sh` | Write/Edit 직후 | syntax + AST + BPE + pronoun + markdownlint 5종 차단 |
| `hook_html_mirror_consistency.sh` | Edit 직후 | `.md` ↔ `.html` 6 pair 동시 갱신 + fingerprint 2 layer |

### 3.3 Stop Hook

| hook | scope |
|---|---|
| `hook_telegram_report_stop.sh` | 매 작업 보고 텔레그램 자동 송신 |
| `hook_assessment_freshness.sh` | 평가 4 file 5+ commit drift 차단 |
| `hook_doc_consistency.sh` | ARCHITECTURE/Structure 실 path drift 차단 |
| `hook_html_mirror_consistency.sh` | Stop 시점 HTML mirror 재검증 |
| `hook_chat_bpe_check.sh` | 마지막 assistant message BPE/조사 chain 검수 |
| `hook_self_hosted_ci_trigger.sh` | self-hosted runner CI auto-trigger |
| `hook_assessment_token_rewrite_trigger.sh` | 평가 6h staleness + token-usage 재 산출 |
| `hook_dereliction_check.sh` | 7 영역 자동 detect + WARN BLOCK exit 2 |

### 3.4 Git Hook / CI Hook 계층

| layer | trigger | script / file | role |
|---|---|---|---|
| L1 post-commit | commit 직후 | `hook_postcommit_wbs_auto_register.sh` 계열 | WBS row 자동 등록 패턴 |
| L1 post-commit | commit 직후 | `hook_postcommit_auto_telegram.sh` 계열 | commit summary telegram 송신 패턴 |
| L1 pre-push | push 직전 | `.git/hooks/pre-push` | `PRE_PUSH=1` 로 ahead-check self-reference 회피 |
| L5 meta | CI + local | `tools/meta_enforce.py` | enforcement 파일 실재성, root markdown freeze, soft-fail 금지, meta job 등록, local noise 추적 금지 |

TooTalk 현 저장소에는 L5가 실제 파일로 존재한다. post-commit 계열은 정본 §S 에서 portable pattern 으로 관리하며, 대상 프로젝트에서 `.git/hooks/` 또는 installer script 로 생성한다.

### 3.5 `tools/meta_enforce.py` 작성 가이드

`meta_enforce.py` 는 일반 lint 의 대체재가 아니라 **하네스 자기검증기**다. 새 프로젝트에 이식할 때는 "규칙을 검사"하기보다 "규칙을 검사하는 도구와 CI가 약화되지 않았는지"를 확인한다.

#### 3.5.1 기본 골격

```python
#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _run_git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    checks: List[Tuple[str, Callable[[], Tuple[bool, str]]]] = [
        ("required-files", check_required_files),
    ]
    failures: list[str] = []
    for name, fn in checks:
        ok, message = fn()
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {message}")
        if not ok:
            failures.append(name)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
```

#### 3.5.2 필수 검사 세트

| check | 목적 | TooTalk 예시 |
|---|---|---|
| `required-files` | 정본/CI가 참조하는 도구 실재성 | `tools/doc-lint.sh`, `tools/md_agents.py`, hook scripts, workflows |
| `root-markdown-freeze` | 루트 문서 증식 차단 | root `.md` cap 검증 |
| `ci-soft-fail` | CI gate 약화 차단 | active YAML 안 `continue-on-error: true` 금지 |
| `ci-meta-job` | meta-enforcement 자기등록 확인 | `ci.yml` 안 `python3 tools/meta_enforce.py` |
| `history/readme freshness` | 최신 cycle marker 문서화 확인 | commit subject → README/History label search |
| `hook-wired` | hook 파일이 실제 settings에 연결됐는지 확인 | `.claude/settings.json` Stop hook command search |
| `push-policy` | main 직접 push 안내 전파 차단 | main 대상 직접 push 명령 금지 + feature branch PR token 요구 |
| `tracked-noise-files` | 로컬 파일 추적 차단 | `.DS_Store`, `.claude/settings.local.json` |

#### 3.5.3 작성 원칙

- 검사는 `Tuple[bool, str]` 를 반환한다. 실패 메시지는 바로 조치 가능한 파일/토큰을 포함한다.
- YAML은 가능하면 parser 를 쓰되, 단순 self-check 는 token scan 으로 시작해도 된다. 단, 주석과 active line 을 구분해야 한다.
- `git ls-files` 기반 검사를 넣어 untracked/ignored/local noise 와 tracked artifact 를 구분한다.
- "문서가 말하는 것"과 "실제 CI/hook이 하는 것"을 같은 함수에서 비교한다.
- 새 hook 또는 workflow 를 추가하면 `required-files`, `hook-wired`, `ci-meta-job` 계열 검사를 함께 추가한다.
- portable guide 자체도 검사 대상에 넣는다. 하네스 문서가 main 직접 push 같은 낡은 지시를 다시 퍼뜨리면 `meta_enforce.py` 가 실패해야 한다.
- `main()` 의 check list 순서는 빠른 구조 검사 → CI 약화 검사 → freshness 검사 → hook/policy 검사 → noise 검사 순으로 둔다.

#### 3.5.4 CI 연결

```yaml
meta-enforcement:
  runs-on: self-hosted
  steps:
    - uses: actions/checkout@v4
    - name: meta-enforcement 실행
      run: python3 tools/meta_enforce.py
```

CI job 에 `continue-on-error: true` 를 붙이지 않는다. meta-enforcement 실패는 PR merge 차단 대상이다.

### 3.6 Hook 활성 의무

`.claude/settings.json` `hooks.PreToolUse` + `hooks.PostToolUse` + `hooks.Stop` 의 `type=command` + `bash ${CLAUDE_PROJECT_DIR}/tools/...` 경로 명시. Stop hook 은 차단 목적 hook 과 보고 목적 hook 을 함께 두되, 텔레그램 송신 hook 은 응답 차단을 피하기 위해 항상 exit 0 패턴을 유지한다.

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
- `feedback_no_self_other_pronoun.md` — 금지 대명사 사용 차단
- `feedback_telegram_report_mandatory_m7.md` — 매 결과 보고 텔레그램 송신
- `feedback_assessment_full_rewrite.md` — 평가 snapshot 전면 rewrite
- `feedback_auto_commit_push_deploy.md` — commit + push + 서버 변경 시 deploy chain
- `feedback_code_qa_review_gate_mandatory.md` — code 작업 후 review/qa gate 의무

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

## 8. Branch Push + PR Policy

```bash
git checkout -b codex/<task-slug>
git commit -m "<type>(cycleN): <scope>"
git push origin HEAD:codex/<task-slug>
gh pr create --base main --head codex/<task-slug> --fill
```

- main 직접 push 는 금지한다. 모든 이식 대상의 기본값은 feature branch + PR 이다.
- 자동 보정 workflow 도 `auto/<name>-<run_id>` 같은 임시 branch 로 push 한 뒤 PR 을 만든다.
- `SKIP_PREPUSH=1` 같은 classifier 우회 prefix 는 target repo 가 명시적으로 요구하는 경우에만 feature branch push 에 붙인다.
- pre-push hook 안 ahead-check skip 은 self-reference loop 회피 목적 한정이며, review 우회 수단이 아니다.
- local noise (`.claude/settings.local.json`, build 산출물, IDE cache) 는 `.gitignore` 에 넣고 L5 `tracked-noise-files` 로 이중 차단한다.

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

## 11. 문서화 · 코드 분리 규칙

### 11.1 Root 문서 freeze

| rule | value |
|---|---|
| root markdown cap | TooTalk 기준 18개 |
| 신규 정책 문서 | `docs/` 하위에만 생성 |
| portable doc 위치 | `docs/PORTABLE_HARNESS.md` |
| 검증 | `tools/meta_enforce.py` + CI `meta-enforcement` |

루트는 진입점과 정본만 둔다. 장문 정책, 평가, handoff, portable guide 는 `docs/` 하위로 이동한다.

### 11.2 Markdown ↔ HTML mirror

6 pair 동시 유지:

| md | html |
|---|---|
| `Structure.md` | `docs/html/Structure.html` |
| `ARCHITECTURE.md` | `docs/html/ARCHITECTURE.html` |
| `FRONTEND.md` | `docs/html/FRONTEND.html` |
| `DESIGN.md` | `docs/html/DESIGN.html` |
| `docs/assessments/productization.md` | `docs/html/productization.html` |
| `docs/assessments/vibe-coding.md` | `docs/html/vibe-coding.html` |

평가 문서 pair 는 `last_verified` + cycle marker fingerprint 를 같이 맞춘다.

### 11.3 Code split 기준

| area | 기준 |
|---|---|
| UI 대형 class | mixin 또는 helper method 로 기능 단위 분리 |
| server route | Router → Service → Repository/Model 계층 유지 |
| config | `.env`, DB 상수 테이블, settings loader 경유 |
| test | 실제 binding 테스트로 skeleton-only test 교체 |
| docs | 작업 전 Specification/CheckList/Structure/Exec Plan 갱신 |

대형 UI 파일은 트레이, 친구 검색, drawer, bot chat, lifecycle, invite, status 같은 사용성 단위로 나눈다. 단순 줄 수 감축이 아니라 테스트 가능한 책임 경계를 만드는 것이 기준이다.

### 11.4 Local / shared 파일 분리

| shared | local |
|---|---|
| `.claude/settings.json` | `.claude/settings.local.json` |
| `.claude/agents/*.md` | `.claude/dereliction_last_fire.txt` |
| `tools/hook_*.sh` | `.claude/dereliction_disabled.flag` |
| `docs/**` | `dist/`, `build/`, `.venv/` |

portable package 는 shared 파일만 복사한다. local 파일은 machine bootstrap 단계에서 생성한다.

---

## 12. 다른 프로젝트 재사용 chain

### 12.0 Codex skill invoke

본 문서는 타 프로젝트 시작 시 개인 skill 로도 호출한다.

| item | value |
|---|---|
| skill name | `$portable-harness` |
| local path | `~/.codex/skills/portable-harness/` |
| core file | `SKILL.md` |
| checklist | `references/bootstrap.md` |

사용 예:

```text
Use $portable-harness to bootstrap governance, hooks, guardrails, and project-start documentation.
```

skill 은 타 프로젝트에서 현재 저장소의 긴 정본 전체를 즉시 로드하지 않고, 먼저 대상 저장소를 조사한 뒤 필요한 경우 `references/bootstrap.md` 와 본 문서를 읽도록 설계한다.

### 12.1 file copy 의무

```
CLAUDE_HARNESS_IMPORTANT.md       # Watcher 정본
CLAUDE.md                          # 세션 호출 규약
AGENTS.md                          # 저장소 맵 + 7 process agent 표
docs/PORTABLE_HARNESS.md           # 본 문서
.claude/settings.json              # Hook 활성
.claude/agents/*.md                # 7+ agent 사양
tools/hook_*.sh                    # Hook script chain
tools/gen_token_usage_30d.py       # 평가 자동 trigger
tools/meta_enforce.py              # L5 자기검증
tools/md_agents.py                 # M2/M3/M4/root freeze 검증
.github/workflows/ci.yml           # meta-enforcement job 포함
```

### 12.2 환경 setup

1. `~/.claude/projects/<project_slug>/memory/MEMORY.md` 생성
2. 핵심 영구 가드레일 copy (§5.4)
3. `.claude/settings.json` Hook 활성
4. process agent + ssh-deploy + dereliction-detector skeleton 신설
5. M1~M7 cache 명문 (CLAUDE.md §8 정합)
6. `.gitignore` 에 local noise + build 산출물 추가
7. CI 안 `python tools/meta_enforce.py` job 등록

### 12.3 첫 cycle 의무

- `@planning-agent` Exec Plan 작성 (M1)
- `@release-agent` 또는 main thread README "변경 이력" prepend (M2)
- `@history-agent` History.md 역순 prepend (M3)
- per-file commit + push (M5)
- WBS sqlite `wbs_tasks` 1행 INSERT (M6)
- 평가 snapshot 2 file 초기 작성 (productization + vibe-coding)
- HTML mirror 6 pair 초기 생성
- `tools/meta_enforce.py` PASS
- `hook_dereliction_check.sh` sentinel/TTL 동작 검증

---

## 13. Trigger catalog

| trigger | action |
|---|---|
| directive 수령 | WBS row INSERT + CheckList 매핑 |
| 큰 작업 | Exec Plan `active/` 신설 |
| Edit/Write 전 | BPE/pronoun PreToolUse 검사 |
| Edit/Write 후 | syntax/AST/markdownlint/HTML mirror 검사 |
| commit 후 | WBS/telegram hook pattern |
| Stop | telegram + assessment + doc consistency + BPE chat + CI + token usage + dereliction |
| 5 commit drift | assessment rewrite block |
| 6h staleness | assessment/token rewrite trigger |
| CI | md_agents + doc-lint + meta_enforce |
| server/deploy 변경 | ssh-deploy-agent chain |

---

## 14. 운영 검증 결과 (TooTalk 누계)

- cycle 1 ~ 169.5xx 누계 운영
- drift 0건 연속 구간 다수 유지
- sub-agent 누계 100+ spawn 병렬 batch
- 영구 가드레일 50+ 누적
- pytest 1800+ PASS + Playwright + coverage gate
- Hook 8 Stop entry + L5 meta-enforcement
- root markdown 18 freeze 유지
- PORTABLE_HARNESS 루트 이동 회수 완료 (`docs/` 하위)

---

## 15. 참조

- [CLAUDE_HARNESS_IMPORTANT.md](../CLAUDE_HARNESS_IMPORTANT.md) — Watcher 정본
- [CLAUDE.md](../CLAUDE.md) — 세션 호출 규약
- [AGENTS.md](../AGENTS.md) — 저장소 맵 + agent 표
- `~/.claude/projects/<project_slug>/memory/MEMORY.md` — 가드레일 인덱스
- `.claude/agents/` — agent 사양
- `tools/` — Hook script + 자동화
- `tools/meta_enforce.py` — L5 enforcement 자기검증
- `.claude/settings.json` — hook activation baseline
