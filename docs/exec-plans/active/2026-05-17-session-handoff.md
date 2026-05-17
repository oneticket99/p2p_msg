---
title: "TooTalk 세션 인계 — 2026-05-17 → 다음 세션"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# TooTalk 세션 인계 — 2026-05-17 → 다음 세션

> 본 문서는 정본 [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md) §Q 등가 패턴. 다음 세션 Claude(=Watcher) 가 본 저장소 재진입 시 **최우선 정독 대상**.
> 본 인계 시점: 2026-05-17 14:42 (사이클 2 갱신 — 본 세션 누계 commit 28 반영). 최신 commit `67c898a`.

---

## 1. 30초 TL;DR

- **Watcher 역할** — 보고 Fine-Grained (모든 도구 1:1), 유휴 폴백 `/loop 2m`
- **서브에이전트 Whitebox** — `run_in_background: true` + 자동 notify
- **5단계 워크플로우 절대** — 문서 → 검토 → 개발 → QA → 리뷰. ②~⑤ 진입 전 ① 완료 의무
- **16 영구 가드레일** 모두 hard constraint. 자율 판단 위 우선 (신규 사이클 2 — phase1-priority + remote-control + auth-otp + design-html)
- **8 체크리스트** ([[feedback-doc-perfection-before-code]]) 충족 후 코드 진입
- **파일 1건 작성/수정/삭제 시 즉시 commit + push** + lint 5 검사 통과 의무
- **BPE U+CE21 단독 + 1인칭/3인칭 대명사 영구 금지** — doc-lint.sh 자동 grep
- **DB = MariaDB 7 테이블** (users + email_verification + password_reset + rooms + peers + file_meta + messages), GUI = PyQt6, Python = 3.13, CI = self-hosted
- **회원가입 + 이메일 OTP 인증 필수** (Phase 1 의무 — bcrypt 12 + OTP 3분 + 아이디/비번 찾기, [[project-auth-email-otp-required]])
- **Phase 3 막바지 원격 데스크탑 제어 차별화** (친구간 1:1, 패턴 A 도움 + 패턴 B 제어, [[project-phase2-remote-control-differentiator]])
- **M7 텔레그램 송신 강제** — HTTP API 직접 (bot `8753967007` + chat `201073550`). 매 응답 종료 직전 + task 완료 시
- **HTML 동시 정리 6종** — Structure / ARCHITECTURE / FRONTEND / DESIGN / productization / vibe-coding
- **평가 snapshot 2종** — productization (3.6/5) + vibe-coding (4.85/5) 매 task 종료 시 전체 rewrite (사이클 4 완료)

---

## 2. 세션 시작 체크리스트 (필수 순서)

1. **본 문서 전체 정독** — §1~§10
2. **정본 정독** — [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md) §1~5 + §A~S
3. **메모리 인덱스 로드** — `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/MEMORY.md` + 14 가드레일 전부
4. **CLAUDE.md §10-6/7 정독** — HTML 6종 + 평가 snapshot 2종 동시 갱신 의무
5. **AGENTS.md 정독** — §1~11
6. **현 활성 실행계획** — [2026-05-17-tootalk-phase1-mvp.md](2026-05-17-tootalk-phase1-mvp.md)
7. **누계 git log** — `git -C /Users/oneticket_toonation/Documents/vscode_work/p2p_msg log --oneline`
8. **CheckList §2 진행률 표 정독** — 16행 진행률 표 (drift 차단)
9. **TL;DR 사용자 재선언** (Q-2 등가 첫 응답 템플릿)
10. **텔레그램 세션 재진입 송신** — HTTP API 의 첫 송신 의무

---

## 3. 첫 응답 템플릿

```text
[Watcher] 세션 재진입 — TooTalk 가드레일 활성.
- 본 인계 로드 OK: docs/exec-plans/active/2026-05-17-session-handoff.md §1~10
- 정본 로드 OK: CLAUDE_HARNESS_IMPORTANT.md §1~5, §A~S
- 메모리 14 가드레일 로드 OK
- CLAUDE.md §10-6/7 동시 갱신 의무 인지 OK
- 정책 상태:
  · 보고 세밀도 = Fine-Grained
  · 서브에이전트 = Whitebox (run_in_background + 자동 notify)
  · 워크플로우 = ① 문서 → ② 개발 → ③ QA → ④ 리뷰 → ⑤ 머지 강제
  · 파일 1건 즉시 commit + push (lint 5 검사 통과 후)
  · BPE 위생 = U+CE21 단독 영구 금지
  · 1인칭/3인칭 대명사 = 영구 금지 (가드레일 [[feedback-no-self-other-pronoun]])
  · M7 텔레그램 송신 = HTTP API 직접 (매 응답 + task 완료)
  · 8 체크리스트 = 큰 프로젝트 코드 진입 전 필수
  · HTML 6종 동시 정리 = 매 .md 갱신 시 .html 동시
  · 평가 snapshot 2종 = 매 task 종료 시 전체 rewrite
- 텔레그램 송신 완료 (msg ID)
- 첫 액션: §9 우선순위 표 1번 행부터 진행
```

---

## 4. 영구 가드레일 인덱스 16건 (hard constraint)

본 가드레일은 **자율 판단 위 우선**. 위반 = 직무유기 cycle 차감 + 추가 자율성 제한.

| 파일 (`~/.claude/projects/.../memory/`) | 핵심 규칙 |
|---|---|
| `feedback_no_korean_chuck_token.md` | BPE 손상 U+CE21 단독 사용 절대 금지 |
| `feedback_no_self_other_pronoun.md` | **신규 본 세션**. 1인칭/3인칭 대명사 영구 금지 (3회차 강화) |
| `feedback_no_autonomy_dereliction_prevention.md` | 자율성 제한 = 직무유기 방지 본질 의무 |
| `feedback_workflow_strict_doc_first.md` | 문서 → 검토 → 개발 → QA → 리뷰 절대 워크플로우 |
| `feedback_doc_perfection_before_code.md` | **신규 본 세션**. 큰 프로젝트 8 체크리스트 + 간단 작업 완화 |
| `feedback_per_file_immediate_push.md` | 파일 1건 = 1 commit + 1 push (즉시) |
| `feedback_repeat_criticism_permanent_record.md` | 동일 비판 2회 이상 = 영구 메모리 강제 저장 메타 규칙 |
| `feedback_lint_before_push_guardrail.md` | 파일 수정 후 markdown + doc-lint.sh 5 검사 통과 후 push |
| `feedback_telegram_report_mandatory_m7.md` | **본 세션 강화**. HTTP API 직접 + 매 응답/task 종료 강제 송신 |
| `feedback_m7_caveman_ultra_simplify.md` | 텔레그램 송신 본문 caveman ultra (5줄 이하) |
| `feedback_session_handoff_on_doc_complete.md` | 문서 작업 완료 시 본 인계 문서 작성 트리거 |
| `feedback_design_interactive_html.md` | **신규 본 세션**. 디자인 directive HTML interactive 권장 |
| `project_phase1_completion_priority.md` | **신규 본 세션**. Phase 1 기본 8 완성 후 추가 차별화 진입 (scope creep 차단) |
| `project_phase2_remote_control_differentiator.md` | **신규 본 세션 (사이클 2)**. Phase 3 막바지 친구간 원격 데스크탑 제어 차별화 (P5/P6 OBS 도움) |
| `project_auth_email_otp_required.md` | **신규 본 세션 (사이클 2)**. Phase 1 회원가입 + 이메일 OTP 필수 (bcrypt 12 + 3분 + DB 3 테이블 + 아이디/비번 찾기) |
| `feedback_workflow_preferences.md` | 서브에이전트 적극 활용 + mermaid + 즉시 push |

---

## 5. 확정된 정책 표 (사용자 directive 누계)

| 항목 | 값 | 출처 |
|---|---|---|
| 서비스명 | TooTalk | 2026-05-17 |
| 코드명/repo | `p2p_msg` | 2026-05-17 |
| GUI | PyQt6 (GPL/상용 분리) | 2026-05-17 |
| Python | 3.13 | 2026-05-17 |
| WebRTC | aiortc | 2026-05-17 |
| 이벤트 루프 | qasync | 2026-05-17 |
| 시그널링 | aiohttp WebSocket | 2026-05-17 |
| 시그널링 데모 호스트 | `114.207.112.73` (root / 보안 deprioritized) | 2026-05-17 |
| **DB** | **MariaDB 7 테이블** (auth 3: users + email_verification + password_reset / 대화 4: rooms + peers + file_meta + messages) + asyncmy + bcrypt 12 + InnoDB redo log + binlog PITR | 2026-05-17 |
| **회원가입** | 이메일 OTP 인증 필수 (Phase 1 의무) — email + username + password 필수 + nickname + avatar 선택 + OTP 3분 + 5회/30분 차단 + 아이디/비번 찾기 (reset_token UUID4 30분) | 2026-05-17 |
| **차별화** | Phase 3 막바지 친구간 원격 데스크탑 제어 (패턴 A 도움 + 패턴 B 제어, P5/P6 OBS 도움 시나리오) | 2026-05-17 |
| 빌드 | macOS + Windows · PyInstaller + zip · 인증서 미사용 | 2026-05-17 |
| CI | **self-hosted** runner 매트릭스 (macOS arm64 + Windows x64) | 2026-05-17 |
| GitHub | `oneticket99/p2p_msg` **public** | 2026-05-17 |
| branch | feature + PR (main 직접 push 금지 — 단 본 사이클 직접 허용) | 2026-05-17 |
| **테스트** | **pytest + Playwright E2E** (DESIGN.md §10 정합, 본 세션 인프라 신설) | 2026-05-17 |
| HTML 동시 정리 | 6종 (Structure/ARCHITECTURE/FRONTEND/DESIGN/productization/vibe-coding) | 2026-05-17 |
| 평가 snapshot | 2종 (productization 3.6/5 + vibe-coding 4.85/5, 사이클 4 완료) | 2026-05-17 |
| M7 텔레그램 bot | `8753967007` (chat `201073550`) — HTTP API 강제 활성 | 2026-05-17 |
| 라이선스 | 미확정 (Phase 1 후반 확정) | — |

---

## 6. M1~M7 캐시

1. **M1** 문서가 코드보다 앞선다
2. **M2** 파일 작업 끝 → README.md 변경 이력 prepend (30행)
3. **M3** History.md 역순 prepend (최신 상단)
4. **M4** 작업 파일 한글 주석 (`.py`·`.js`·`.html`·`.css`·`.sql`·`.sh`)
5. **M5** 작업 완료 즉시 commit + push (로컬 백로그 0)
6. **M6** directive 처리 직후 `data/wbs.sqlite` 1행 등록 (인프라 준비 후)
7. **M7** directive 결과 텔레그램 강제 송신 (HTTP API 직접)

---

## 7. 재진입 직후 피해야 할 실수

- ❌ 본 인계 정독 없이 일반 모드 응답
- ❌ 코드 spawn 진입 (사용자 GO 없이 — 가드레일 [[feedback-doc-perfection-before-code]] 위반)
- ❌ `Agent` foreground 동기 호출 (Whitebox 위반)
- ❌ `--no-verify` / `--force` / `--amend`
- ❌ 1인칭 / 3인칭 대명사 표현 사용 (3회차 영구 가드레일)
- ❌ BPE U+CE21 단독 의존명사 사용
- ❌ 텔레그램 송신 누락 (HTTP API 강제 활성 — 매 응답 종료 직전)
- ❌ 동시 N sub-agent spawn (단 병렬 가능 영역은 허용 — 사용자 directive 2026-05-17)
- ❌ HTML 동시 갱신 누락 (.md 갱신 시 .html 의 stale)
- ❌ 평가 snapshot 동시 갱신 누락 (CLAUDE.md §10-7 의무)
- ❌ Agent #16 산출물 (`app/rtc/` + `app/ui/file_progress_widget.py`) untracked 임의 commit
- ❌ Phase 1 기본 8 완성 전 추가 차별화 진입 ([[project-phase1-completion-priority]] 위반)

---

## 8. 인수인계 시점 진행 상태 SNAPSHOT (2026-05-17 14:42)

### 8.1 누계 commit (본 세션 28건, 직전 인계 시점 = `f500104`)

```text
67c898a  docs: 평가 snapshot 사이클 4 (productization 3.6 + vibe-coding 4.85)
5486c72  docs(html): HTML 3종 재생성 — auth + wireframe + 모듈 책임
ec3f90c  docs(auth): auth 인프라 정책 본문 5 — P3 재조정 + DB 4→7 + 모듈 + wireframe
17a2e98  feat(auth): 회원가입 + 이메일 OTP 인증 정책 — Phase 1 필수
247e94d  feat(product): 차별화 계획 정리 — 친구간 원격 데스크탑 제어 (Phase 3 막바지)
6e45f89  docs: 평가 snapshot 사이클 3 — productization 2.9 + vibe-coding 4.7
0fd2bcf  docs(handoff): 세션 인계 사이클 1 전체 rewrite
b2b5bcb  docs(agents): AGENTS PR 게이트 — build.yml (M5)
ee10273  docs(checklist): CheckList §2 진행률 표 drift 차단 갱신
050acca  feat(qa): pytest 인프라 + Playwright E2E + DESIGN UI 디자인 시스템 + HTML
86868b9  docs: 평가 snapshot 사이클 2
461f196  docs(frontend): FRONTEND 색상 변수 표 swatch 가시화
dc9170f  docs(policies): docs/policies/ 3 문서 (깨진 링크 12 → 0)
96ad8e4  docs(release): .github/pull_request_template.md
db0b634  chore(tools): doc-lint.sh bash 3.2 호환 + 1인칭/3인칭 검사
794c251  docs: vibe-coding snapshot + HTML 2 + 가드레일 강화
26f60ed  fix(guardrail): 1인칭/3인칭 전수 회수 + 텔레그램 가드레일 강제
5d898b2  docs: docs/html/ 5 HTML + CLAUDE.md §10-6/7
87e71e3  fix(policy): RELIABILITY.md MariaDB 회수 (13 위반)
9477e9c  fix(plan): 실행계획 MariaDB 회수 (5 위반)
6ab9952  docs: assessments productization + vibe-coding 신설
aff2cde  fix(policy): ARCHITECTURE.md MariaDB 회수 (4 위반)
34d4707  fix(app): app/core/config.py MariaDB 회수 (5필드)
0b0e010  docs: ci-self-hosted-setup.md
6f39d32  ci: doc-gardener.yml
76313fe  ci: docs-lint.yml
df7f581  ci: ci.yml (게이트 7종 self-hosted 매트릭스)
```

### 8.2 정본 §K 18 동결 — 유지

- 루트 .md 정확히 18 (변동 없음)

### 8.3 docs/ 하위 신규

- `docs/policies/doc-gardening.md` · `docs/policies/adoption-roadmap.md` · `docs/policies/execution-harness.md` (3 active)
- `docs/assessments/productization.md` · `docs/assessments/vibe-coding.md` (2 snapshot)
- `docs/html/Structure.html` · `ARCHITECTURE.html` · `FRONTEND.html` · `DESIGN.html` · `productization.html` · `vibe-coding.html` (6 동시 정리)
- `docs/references/ci-self-hosted-setup.md` (1)

### 8.4 .github/ 신규

- `.github/workflows/ci.yml` (7 게이트)
- `.github/workflows/docs-lint.yml` (cron daily)
- `.github/workflows/doc-gardener.yml` (cron 주간)
- `.github/pull_request_template.md` (release-agent 정합 9 섹션)

### 8.5 pytest + Playwright 인프라 신규

- `pyproject.toml` (pytest 7+ + asyncio + coverage + 5 marker)
- `app/requirements-dev.txt` + `server/requirements-dev.txt` (pytest + playwright)
- `tests/{__init__,conftest}.py`
- `tests/app/test_config.py` (6 test — MariaDB 5필드 + DSN + 폴백)
- `tests/server/test_protocol.py` (3 test — 화이트리스트 + 거부 + 비문자열)
- `tests/e2e/{conftest,test_html_visual_smoke}.py` (3 e2e test)
- `ci.yml` pytest job 매트릭스 추가

### 8.6 MariaDB 회수 완료 (handoff §9 우선순위 1~4 모두 ✅)

- `app/core/config.py` (5필드 + db_dsn) ✅
- `ARCHITECTURE.md` (4 위반) ✅
- 실행계획 (5 위반) ✅
- `RELIABILITY.md` (13 위반) ✅
- `app/README.md` 동행 ✅

### 8.7 가드레일 인프라

- `tools/doc-lint.sh` (5 검사 — BPE + 깨진 링크 + frontmatter + 빈 줄 + 1인칭/3인칭, bash 3.2 호환)
- `tools/claude-telegram.sh` (Telegram CLI wrapper)
- `.markdownlint.json` (MD013/MD025/MD032/MD060 완화 + MD033 span/div 허용)
- 영구 메모리 **16종** (신규 본 세션 6 — no-self-other-pronoun + doc-perfection-before-code + design-interactive-html + phase1-completion-priority + **phase2-remote-control-differentiator** + **auth-email-otp-required**)

### 8.8 회원가입 + 이메일 OTP 정책 (Phase 1 필수, 사이클 2 신규)

- FR-11 회원가입 (P0 / M2) — email + username + password 필수 + nickname + avatar 선택 + OTP 3분
- FR-12 로그인 (P0 / M2) — email + password + bcrypt 검증
- FR-13 아이디/비번 찾기 (P0 / M2) — email 미존재 → "가입된 내역 없음" / 일치 → reset_token UUID4 + 30분
- DB 3 테이블 (users + email_verification + password_reset)
- SECURITY §9-2 (bcrypt 12 + OTP 5회/30분 차단 + 60초 재발송 rate-limit + SMTP TLS + STRIDE 6)
- 페르소나 P3 재조정 ("가입 마찰 0" → "가입 마찰 최소", 1회 가입 후 영구 이용)

### 8.9 차별화 — 원격 데스크탑 제어 (Phase 3 막바지, 사이클 2 신규)

- 패턴 A — 원격 도움 요청 (피요청자 = 원격 제어 대상, P5 OBS 설정 시나리오)
- 패턴 B — 원격 제어 요청 (요청자 = 원격 제어 주체, P6 가 P5 컴퓨터 제어)
- 권한 모델 — 친구 추가 사전 + 명시 수락 모달 + 긴급 ESC + 감사 로그
- 기술 — WebRTC video track 추가 + 화면 캡처 (mss/Qt QScreen) + 입력 주입 (pynput/pywinauto/pyobjc) + x264/VP9/AV1 인코딩
- 페르소나 P5 (라이브 크리에이터) + P6 (기술 도움 제공자) 신규
- Toonation 옵션 B (★★★★★ 권장도 1순위) 핵심 차별화

### 8.8 텔레그램 강제 활성

- HTTP API 직접 (bot `8753967007` + chat `201073550`)
- 본 세션 송신 누계 14건 (msg 1052 ~ 1066)
- `.env.local` 의 자격 격리 (`.gitignore` `.env.*`)

### 8.9 Agent #16 산출물 untracked 보존

- `app/rtc/` (file_sender + file_receiver + image_processor + peer + protocol + README) ❌ untracked
- `app/ui/file_progress_widget.py` ❌ untracked
- 사용자 명시 stop 의도 — 임의 commit 절대 금지

---

## 9. 다음 세션 첫 액션 (우선순위 순)

| 순서 | 작업 | 상태 | 비고 |
|---|---|---|---|
| 1 | self-hosted runner 등록 (macOS arm64 + Windows x64) | 🟡 사용자 직접 | docs/references/ci-self-hosted-setup.md 절차. 1일. CI 3 workflow `queued` 해소 |
| 2 | 평가 snapshot 사이클 3 갱신 (CLAUDE.md §10-7 의무) | 🔴 미진입 | 본 세션 누계 commit 20+ 반영. productization + vibe-coding rewrite + HTML 2 sub-agent |
| 3 | 잔존 BPE 위반 정정 — CLAUDE_HARNESS_IMPORTANT.md | 🔴 미진입 | 정본 광범위 (BPE 다수). doc-lint.sh 의 grep |
| 4 | 라이선스 결정 — LICENSE 신설 | 🟡 사용자 직접 | OSS / 상용 분기. contributor 진입 가능 시점 |
| 5 | Phase 1 코드 진입 GO (사용자 명시) | 🔴 가드레일 차단 | [[feedback-doc-perfection-before-code]] 8 체크리스트 통과 후만 |
| 6 | Agent #16 산출물 reviewer-agent 검토 | 🔴 사용자 결정 | `app/rtc/` + `file_progress_widget.py` commit 여부 |
| 7 | Toonation 통합 시나리오 검토 (옵션 B) | 🔴 사용자 직접 | adoption-roadmap.md §4.2 권장 ★★★★☆ |

### 9.1 잔존 task 진입 가능 (가드레일 통과 후)

- #16 파일전송 양방향 progress 모듈 (Agent #16 산출물 검토 후)
- #17 데모 시그널링 서버 배포 (114.207.112.73 systemd · docker)
- #18 PyInstaller spec + 빌드 스크립트
- #19 build.yml 매트릭스 (M5 단계)
- #20 README 빌드/실행 안내 갱신
- E2EE (libsignal-protocol wrapping) — Phase 2 진입

---

## 10. 본 문서 자체의 불변 규약

- 본 §10 = 다음 세션에 의해서도 유지. "작업 완료" 이유로 삭제·간소화 금지.
- 정책 변경 시 §5 표 + 관련 메모리 가드레일 동시 갱신. 한쪽만 갱신 금지.
- 본 인계가 완전 소비된 시점 (Phase 1 기본 8 완성 + 코드 진입 통과) = `docs/exec-plans/completed/` 이동.
- 본 파일 경로 (`docs/exec-plans/active/2026-05-17-session-handoff.md`) = 다음 세션 정독 대상 = 본 활성 위치 유지.
- 새 인계 작성 시 본 패턴 사본 + 갱신.

---

## 참조

- 정본: [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md)
- 운영 규약: [CLAUDE.md](../../../CLAUDE.md) §10-6/7 (HTML + snapshot 동시 갱신)
- 저장소 맵: [AGENTS.md](../../../AGENTS.md)
- 실행계획 본문: [2026-05-17-tootalk-phase1-mvp.md](2026-05-17-tootalk-phase1-mvp.md)
- 정책 본문: [docs/policies/doc-gardening.md](../../policies/doc-gardening.md) · [adoption-roadmap.md](../../policies/adoption-roadmap.md) · [execution-harness.md](../../policies/execution-harness.md)
- 평가 snapshot: [docs/assessments/productization.md](../../assessments/productization.md) · [vibe-coding.md](../../assessments/vibe-coding.md)
- 메모리 인덱스: `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/MEMORY.md`

---

마지막 갱신: 2026-05-17 14:42 — 사이클 2 갱신 (본 세션 누계 commit 28 반영, 가드레일 16, 텔레그램 송신 24건, HTML 6, pytest 인프라, 정책 본문 3, auth 정책 + 차별화 명문화, snapshot 사이클 4 — productization 3.6 + vibe-coding 4.85, sub-agent 누계 16 spawn)
