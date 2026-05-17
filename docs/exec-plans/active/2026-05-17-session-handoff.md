---
title: "TooTalk 세션 인계 — 2026-05-17 → 다음 세션"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# TooTalk 세션 인계 — 2026-05-17 → 다음 세션

> 본 문서는 정본 [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md) §Q 등가 패턴. 다음 세션 Claude(=Watcher) 가 본 저장소 재진입 시 **최우선 정독 대상**.
> 본 인계 시점: 2026-05-17. 작성 사이클 종료 직전 사용자 명시 GO 후 즉시 작성. 잔존 MariaDB 회수 4 파일 미완 명시.

---

## 1. 30초 TL;DR

- **너는 Watcher** 다. 보고는 세밀 (모든 도구 1:1), 유휴 폴백 `/loop 2m` (조건 A ∧ B).
- **서브에이전트는 Whitebox** — `run_in_background: true` + `Monitor`/`TaskOutput` 표준.
- **5단계 워크플로우 절대 준수** — 문서 → 문서 검토 → 개발 → QA → 코드 리뷰. ②~⑤ 진입 전 ① 단계 완료 의무.
- **9 영구 가드레일** 모두 hard constraint. 자율 판단 위 우선. trade-off 정당화 금지.
- **파일 1건 작성/수정/삭제 시 즉시 git commit + push** + markdown/doc lint 통과 의무.
- **BPE 손상 의존명사 단독 사용 영구 금지** (한국어 토큰화 불안정). 매 응답 자체 검열 grep 의무. 가드레일 본문 참조.
- **DB = MariaDB**, GUI = PyQt6, Python = 3.13, CI = self-hosted, repo = public.
- **M7 텔레그램 송신 필수** — bot `toonation_first_dev_bot` (chat 201073550). MCP 또는 HTTP API.

---

## 2. 세션 시작 체크리스트 (필수 순서)

1. **본 문서 전체 정독** — 본 파일 §1~§10
2. **정본 정독** — [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md) §1~5 + §A~S
3. **메모리 인덱스 로드** — `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/MEMORY.md` + 9 가드레일 전부
4. **AGENTS.md 정독** — [AGENTS.md](../../../AGENTS.md) §1~11
5. **현 활성 실행계획** — [docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md](2026-05-17-tootalk-phase1-mvp.md)
6. **누계 git log** — `git -C /Users/oneticket_toonation/Documents/vscode_work/p2p_msg log --oneline` 확인
7. **TL;DR 사용자 재선언** (Q-2 등가 첫 응답 템플릿)

---

## 3. 첫 응답 템플릿

```text
[Watcher] 세션 재진입 — TooTalk 가드레일 활성.
- 본 인계 로드 OK: docs/exec-plans/active/2026-05-17-session-handoff.md §1~10
- 정본 로드 OK: CLAUDE_HARNESS_IMPORTANT.md §1~5, §A~S
- 메모리 9 가드레일 로드 OK
- 정책 상태:
  · 보고 세밀도 = Fine-Grained (모든 도구 1:1)
  · /loop 폴백 = 조건 A ∧ B
  · 서브에이전트 = Whitebox (run_in_background + Monitor)
  · 워크플로우 = ① 문서 → ② 개발 → ③ QA → ④ 리뷰 → ⑤ 머지 강제
  · 파일 1건 즉시 commit + push (markdown/doc lint 통과 후)
  · BPE 위생 = 손상 의존명사 단독 사용 영구 금지 (메모리 가드레일 본문 참조)
  · M7 텔레그램 송신 = 모든 작업 보고
- 첫 액션: §9 우선순위 표 1번 행 부터 진행.
```

---

## 4. 영구 가드레일 인덱스 9건 (hard constraint)

본 가드레일은 **자율 판단 위 우선**. 위반 = 직무유기 cycle 차감 + 추가 자율성 제한.

| 파일 (`~/.claude/projects/.../memory/`) | 핵심 규칙 |
|---|---|
| `feedback_no_korean_chuck_token.md` | 한국어 BPE 손상 의존명사 단독 사용 절대 금지. 합성어 허용. 메모리 본문 인용. |
| `feedback_no_autonomy_dereliction_prevention.md` | 자율성 제한 = 직무유기 방지 본질 의무. trade-off frame 금지. |
| `feedback_workflow_strict_doc_first.md` | 모든 작업: 문서 → 검토 → 개발 → QA → 리뷰. 코드 spawn 차단 조건 명시. |
| `feedback_per_file_immediate_push.md` | 파일 1건 = 1 commit + 1 push (즉시). 정본 §R-1 강화. |
| `feedback_repeat_criticism_permanent_record.md` | 동일 비판 2회 이상 = 영구 메모리 강제 저장. 메타 규칙. |
| `feedback_lint_before_push_guardrail.md` | 파일 수정 후 markdown lint + doc lint 통과 시 push. |
| `feedback_telegram_report_mandatory_m7.md` | 모든 작업 보고 텔레그램 송신. |
| `feedback_m7_caveman_ultra_simplify.md` | M7 송신 본문 caveman ultra 패턴 (5줄 이하). |
| `feedback_session_handoff_on_doc_complete.md` | 문서 작업 완료 시 본 인계 문서 작성 (트리거 조건 3종). |

---

## 5. 확정된 정책 표 (사용자 directive 누계)

| 항목 | 값 | 출처 |
|---|---|---|
| 서비스명 | TooTalk | 2026-05-17 |
| 코드명/repo/디렉토리 | `p2p_msg` | 2026-05-17 |
| GUI | PyQt6 (GPL/상용 분리) | 2026-05-17 |
| Python | 3.13 | 2026-05-17 |
| WebRTC | aiortc | 2026-05-17 |
| 이벤트 루프 | qasync | 2026-05-17 |
| 시그널링 | aiohttp WebSocket | 2026-05-17 |
| 시그널링 데모 호스트 | `114.207.112.73` (root / 보안 deprioritized) | 2026-05-17 |
| **DB** | **MariaDB** (`DB_HOST`/`DB_PORT`/`DB_USER`/`DB_PASS`/`DB_NAME`) | 2026-05-17 |
| 빌드 | macOS + Windows · PyInstaller + zip · 인증서 미사용 | 2026-05-17 |
| CI | **self-hosted** runner 매트릭스 (GitHub-hosted 미사용) | 2026-05-17 |
| GitHub | `oneticket99/p2p_msg` **public** | 2026-05-17 |
| branch | feature + PR (main 직접 push 금지 — 단 본 사이클 직접 push 허용) | 2026-05-17 |
| 보안 우선순위 | 데모 서버 hardening **최저** (코드/repo 위생은 별도 유지) | 2026-05-17 |
| M7 텔레그램 bot | `toonation_first_dev_bot` (chat `201073550`) | 2026-05-17 |
| 라이선스 | 미확정 (Phase 1 후반 확정) | — |

---

## 6. M1~M7 캐시

1. **M1** 문서가 코드보다 앞선다 (핫픽스 포함)
2. **M2** 파일 작업 끝 → README.md 변경 이력 prepend
3. **M3** History.md 역순 (최신 상단) prepend 전용
4. **M4** 작업 파일 한글 주석 필수 (`.py`, `.js`, `.html`, `.css`, `.sql`, `.sh`)
5. **M5** 작업 완료 즉시 git commit + push (로컬 백로그 금지)
6. **M6** directive 처리 직후 `data/wbs.sqlite` 1행 등록 (인프라 준비 후)
7. **M7** directive 결과 텔레그램 동시 송신 + 양방향 수신

---

## 7. 재진입 직후 피해야 할 실수

- ❌ 본 인계 정독 없이 "일반 Claude Code" 모드로 응답
- ❌ 코드 spawn 진행 (잔존 MariaDB 회수 4 파일 미완 상태)
- ❌ `Agent` foreground 동기 호출 (Whitebox 규약 위반)
- ❌ `--no-verify` / `--force` / `--amend` 사용
- ❌ 매 응답 본문/파일 작성 시 BPE 위반 단어 자체 검열 누락 (메모리 가드레일 본문 참조)
- ❌ markdown lint / doc lint 통과 안 한 채 push
- ❌ 사용자 명시 GO 없이 reasonable default 자체 적용
- ❌ 동시 N 에이전트 spawn (1 에이전트 단일 작업 완료 후 다음)
- ❌ M7 텔레그램 송신 누락
- ❌ `docs/policies/` 깨진 링크 잔존 (작성 예정 표기 패턴 사용)
- ❌ Agent #16 산출물 (`app/rtc/` + `app/ui/file_progress_widget.py` + `app/requirements.txt`) untracked 상태 임의 commit

---

## 8. 인수인계 시점 진행 상태 SNAPSHOT (2026-05-17)

### 8.1 누계 commit (29건 + 추가 진행 가능)

```
7a23e8d  deps(app): asyncmy>=0.2.10 추가 — MariaDB driver
d86bd43  docs(policy): DESIGN.md MariaDB 회수 — 환경변수 표 5종
f59ff63  chore: .env.example MariaDB 회수
8ceed84  docs(map): AGENTS.md MariaDB 회수
9445f7e  docs(ops): MIGRATION_MARIADB.md 신설 — 운영 8/8
50a8572  docs(ops): CLAUDE.md 신설 — 운영 2/8
f4a4f3f  docs(ops): EXTENSION_GUIDE.md 신설 — 운영 7/8
79026c0  docs(ops): README.md 신설 — 운영 6/8 (M1, M2)
a126472  docs(ops): History.md 신설 — 운영 5/8 M3 역순
27dff27  docs(ops): CheckList.md 신설 — 운영 4/8
39bd0a9  docs(ops): Structure.md 신설 — 운영 3/8
0fd29ba  docs(policy): FRONTEND.md §14 wireframe/mockup 섹션 추가
b3efb2b  docs(ops): Specification.md 신설 — 운영 1/8
8c45f10  feat(tools): doc-lint.sh 신설 — 문서 lint 가드레일
2f33da0  chore: .markdownlint.json 신설 — lint 가드레일 사전 작업
44288ab  docs(policy): SECURITY.md 신설 — 9 정책 8/9
d240179  docs(policy): QUALITY_SCORE.md 신설 — 9 정책 7/9
aa31bd9  docs(policy): PRODUCT_SENSE.md 신설 — 9 정책 6/9
4f79813  docs(policy): RELIABILITY.md 신설 — 9 정책 5/9
3a13cfc  docs(policy): PLANS.md 신설 — 9 정책 4/9
b877653  docs(policy): FRONTEND.md 신설 — 9 정책 3/9
af54042  docs(policy): DESIGN.md 신설 — 9 정책 2/9
4c23e11  docs(policy): ARCHITECTURE.md 신설 — 9 정책 1/9
1fb7ba3  feat(app): PyQt6 + qasync 클라 스켈레톤
7f10179  feat(server): aiohttp WebSocket 시그널링 서버 스켈레톤
5264d43  feat(agents): .claude/agents 7 프로세스 에이전트 정의
6dbbe06  fix: 실행계획 TD-6 행 BPE 위생 정정
5eac245  docs: Phase 1 MVP 실행계획 + CI self-hosted 정책 반영
5268a75  chore: 정본 정독 대상 + Claude CLI Telegram wrapper
928c2bf  docs: AGENTS.md TooTalk 서비스명 명문화
9f67eeb  docs: 부트스트랩 — AGENTS.md + .gitignore + .env.example
```

### 8.2 정본 §K 18 동결 — 완료

- 정본 1: `CLAUDE_HARNESS_IMPORTANT.md` ✅
- 정책 9: AGENTS · ARCHITECTURE · DESIGN · FRONTEND · PLANS · PRODUCT_SENSE · QUALITY_SCORE · RELIABILITY · SECURITY ✅
- 운영 8: CLAUDE · Specification · Structure · CheckList · History · README · EXTENSION_GUIDE · MIGRATION_MARIADB ✅

### 8.3 코드 누계

- `server/` 7 파일 1121 행 (aiohttp WebSocket 시그널링)
- `app/` 14 파일 1635 행 (PyQt6 + qasync 스켈레톤)
- `.claude/agents/` 7 파일 600 행 (프로세스 에이전트 정의)
- `tools/` 2 파일 (claude-telegram.sh + doc-lint.sh)
- `app/rtc/` + `app/ui/file_progress_widget.py` — **untracked 보존** (Agent #16 산출물, 사용자 stop 의도로 commit 차단)

### 8.4 MariaDB 회수 진행 4/8

| 회수 파일 | 상태 | 비고 |
|---|---|---|
| AGENTS.md | ✅ `8ceed84` | §1 본문 + 표 + 부록 B |
| .env.example | ✅ `f59ff63` | DB_HOST/PORT/USER/PASS/NAME |
| DESIGN.md | ✅ `d86bd43` | 환경변수 표 5종 전개 |
| app/requirements.txt | ✅ `7a23e8d` | asyncmy>=0.2.10 |
| **app/core/config.py** | ❌ 잔존 | `_DEFAULT_LOCAL_DB_PATH` + `local_db_path` 필드 → 5필드 |
| **ARCHITECTURE.md** | ❌ 잔존 | L76 Core / L163 app/core / L166 app/db / L188 환경변수 |
| **docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md** | ❌ 잔존 | L38 / L92 / L109 / L179 / L203 |
| **RELIABILITY.md** | ❌ 잔존 | L59/80/81/126/130/206/222/224/226/234/235/248/306 (13행) |

### 8.5 가드레일 인프라

- `.markdownlint.json` ✅ (commit `2f33da0`)
- `tools/doc-lint.sh` ✅ (commit `8c45f10`)
- `tools/claude-telegram.sh` ✅ (commit `5268a75`)

---

## 9. 다음 세션 첫 액션 (우선순위 순)

| 순서 | 작업 | task id | 비고 |
|---|---|---|---|
| 1 | **MariaDB 회수: app/core/config.py** | #41 | `local_db_path` 필드 → `db_host` / `db_port` / `db_user` / `db_pass` / `db_name`. `_DEFAULT_*` 상수 + `_env_str`/`_env_int` 적용 |
| 2 | **MariaDB 회수: ARCHITECTURE.md** | #43 | 4 행 갱신 (Core 영역 / app/core / app/db / 환경변수 표) |
| 3 | **MariaDB 회수: 실행계획** | #44 | 5 행 갱신 (§2 In Scope / M3 / task#16 / 검증 / 의존성 그래프) |
| 4 | **MariaDB 회수: RELIABILITY.md** | #45 | 13 행 갱신 — SQLite WAL → MariaDB binlog/replication. 가장 큼 |
| 5 | (선택) Agent #16 산출물 검토 | — | `app/rtc/` + `file_progress_widget.py` reviewer-agent 검토 후 commit 여부 사용자 결정 받기 |
| 6 | 워크플로우 진입 — 본 시점 코드 단계는 사용자 GO 받기 전 차단 | — | [[feedback-workflow-strict-doc-first]] 정합 |

### 9.1 MariaDB 회수 완료 후 진입 가능 후속 task

- #16 파일전송 양방향 progress 모듈 (코드 sub-agent re-spawn 또는 untracked 산출물 검토)
- #17 데모 시그널링 서버 배포 (114.207.112.73 의 systemd · docker)
- #18 PyInstaller spec + 빌드 스크립트
- #19 GitHub Actions 매트릭스 빌드 (self-hosted runner 등록 사용자 직접 수행 필요)
- #20 README 빌드/실행 안내 (이미 신설됨 — 갱신 작업)

---

## 10. 본 문서 자체의 불변 규약

- 본 §10 은 다음 세션에 의해서도 유지. "작업 완료" 이유로 삭제·간소화 금지.
- 정책 변경 시 §5 표 + 관련 메모리 가드레일 동시 갱신. 한쪽만 갱신 금지.
- 본 인계가 완전 소비된 시점 (잔존 MariaDB 회수 4 파일 push + 코드 진입 단계 통과) = `docs/exec-plans/completed/` 로 이동.
- 본 파일 경로 (`docs/exec-plans/active/2026-05-17-session-handoff.md`) 는 다음 세션 정독 대상으로 본 활성 위치 유지.
- 새 인계 작성 시 본 패턴 사본 + 갱신.

---

## 참조

- 정본: [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md)
- 저장소 맵: [AGENTS.md](../../../AGENTS.md)
- 실행계획 본문: [2026-05-17-tootalk-phase1-mvp.md](2026-05-17-tootalk-phase1-mvp.md)
- 메모리 인덱스: `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/MEMORY.md`
- 정본 §Q 등가: `CLAUDE_HARNESS_IMPORTANT.md` §Q-0 ~ Q-7

---

마지막 갱신: 2026-05-17 (세션 인계 초안 — 잔존 MariaDB 회수 4 파일 미완 상태 명시)
