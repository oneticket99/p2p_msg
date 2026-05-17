---
title: "TooTalk 세션 인계 — 2026-05-17 → 다음 세션"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# TooTalk 세션 인계 — 2026-05-17 → 다음 세션

> 본 문서는 정본 [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md) §Q 등가 패턴. 다음 세션 Claude(=Watcher) 가 본 저장소 재진입 시 **최우선 정독 대상**.
> 본 인계 시점: 2026-05-17 22:05 (사이클 9 갱신 — 본 세션 누계 commit 49+ 반영, Agent #16 정식 채택 + reviewer-agent 검토 진입 + snapshot 사이클 11). 최신 commit `a260190`.

---

## 1. 30초 TL;DR

- **Watcher 역할** — 보고 Fine-Grained (모든 도구 1:1), 유휴 폴백 `/loop 2m`
- **서브에이전트 Whitebox** — `run_in_background: true` + 자동 notify
- **5단계 워크플로우 절대** — 문서 → 검토 → 개발 → QA → 리뷰. ②~⑤ 진입 전 ① 완료 의무
- **22 영구 가드레일** 모두 hard constraint. 자율 판단 위 우선 (신규 사이클 5 — bpe-script-trigger-warning + telegram-report-script-trigger-warning)
- **8 체크리스트** ([[feedback-doc-perfection-before-code]]) 충족 후 코드 진입
- **파일 1건 작성/수정/삭제 시 즉시 commit + push** + lint 5 검사 통과 의무
- **BPE U+CE21 단독 + 1인칭/3인칭 대명사 영구 금지** — doc-lint.sh 자동 grep
- **DB = MariaDB 7 테이블** (users + email_verification + password_reset + rooms + peers + file_meta + messages), GUI = PyQt6, Python = 3.13, CI = self-hosted macOS arm64 + GitHub-hosted Ubuntu (Windows wine cross-compile)
- **회원가입 + 이메일 OTP 인증 필수** (Phase 1 의무 — bcrypt 12 + OTP 3분 + 아이디/비번 찾기, [[project-auth-email-otp-required]])
- **Phase 3 막바지 원격 데스크탑 제어 차별화** (친구간 1:1, 패턴 A 도움 + 패턴 B 제어, [[project-phase2-remote-control-differentiator]])
- **M7 텔레그램 송신 강제** — HTTP API 직접 (bot `8753967007` + chat `201073550`). 매 응답 종료 직전 + task 완료 시
- **HTML 동시 정리 6종** — Structure / ARCHITECTURE / FRONTEND / DESIGN / productization / vibe-coding
- **평가 snapshot 2종** — productization (3.95/5) + vibe-coding (4.85/5) 매 task 종료 시 전체 rewrite (사이클 9 완료)
- **CI 8 job GREEN** — self-hosted macOS arm64 runner 등록 + workflow 3종 (ci + docs-lint + doc-gardener) 모두 GREEN
- **wine cross-compile** — Windows 빌드 = GitHub-hosted Ubuntu + `cdrx/pyinstaller-windows` docker (Windows self-hosted runner 의무 영구 회수)
- **fork PR strict** — `all_external_contributors` (gh API 자동 적용)
- **SMTP 자체 설치** — 데모 서버 (114.207.112.73) postfix + Let's Encrypt + SPF/DKIM/DMARC + aiosmtplib + SendGrid fallback ([docs/references/smtp-setup.md](../../references/smtp-setup.md))
- **라이선스 = GPLv3** — LICENSE 저장소 루트 + PyQt6 GPLv3 직접 호환 + SPDX header convention ([[project-license-gpl]])
- **visibility = public → private 전환 가능성** — Phase 완료 시점 사용자 명시 의무. self-hosted runner 의 quota 회피 정합 ([[project-visibility-transition]])
- **enforcement layer 활성** — `.claude/settings.json` (PreToolUse Edit/Write BPE 차단 + Stop 텔레그램 자동 송신) — 5회차 BPE 위반 직접 비판 시점 발동 (2026-05-17 cycle 10, [[feedback-bpe-script-trigger-warning]] + [[feedback-telegram-report-script-trigger-warning]])
- **Toonation 브랜드 컬러 통합** — FRONTEND.md §4 의 3 미확정 후크 확정 (#0066FF Toonation Blue + #22D3EE 네온 시안 + #0F172A Deep Navy) + §15 BI 가이드 신규 (사용자 directive 2026-05-17 — 2023-04 BI 리뉴얼 정합)

---

## 2. 세션 시작 체크리스트 (필수 순서)

1. **본 문서 전체 정독** — §1~§10
2. **정본 정독** — [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md) §1~5 + §A~S
3. **메모리 인덱스 로드** — `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/MEMORY.md` + 22 가드레일 전부
4. **CLAUDE.md §10-6/7 정독** — HTML 6종 + 평가 snapshot 2종 동시 갱신 의무
5. **AGENTS.md 정독** — §1~11
6. **현 활성 실행계획** — [2026-05-17-tootalk-phase1-mvp.md](2026-05-17-tootalk-phase1-mvp.md)
7. **누계 git log** — `git -C /Users/oneticket_toonation/Documents/vscode_work/p2p_msg log --oneline`
8. **CheckList §2 진행률 표 정독** — 20행 진행률 표 (drift 차단) + 신규 enforcement layer sketch 인지
9. **TL;DR 사용자 재선언** (Q-2 등가 첫 응답 템플릿)
10. **텔레그램 세션 재진입 송신** — HTTP API 의 첫 송신 의무

---

## 3. 첫 응답 템플릿

```text
[Watcher] 세션 재진입 — TooTalk 가드레일 활성.
- 본 인계 로드 OK: docs/exec-plans/active/2026-05-17-session-handoff.md §1~10
- 정본 로드 OK: CLAUDE_HARNESS_IMPORTANT.md §1~5, §A~S
- 메모리 22 가드레일 로드 OK
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

## 4. 영구 가드레일 인덱스 22건 (hard constraint)

본 가드레일은 **자율 판단 위 우선**. 위반 = 직무유기 cycle 차감 + 추가 자율성 제한.

| 파일 (`~/.claude/projects/.../memory/`) | 핵심 규칙 |
|---|---|
| `feedback_no_korean_chuck_token.md` | BPE 손상 U+CE21 단독 사용 절대 금지 (3회차 강화 영구화) |
| `feedback_no_self_other_pronoun.md` | 1인칭/3인칭 대명사 영구 금지 (3회차 강화) |
| `feedback_no_autonomy_dereliction_prevention.md` | 자율성 제한 = 직무유기 방지 본질 의무 |
| `feedback_workflow_strict_doc_first.md` | 문서 → 검토 → 개발 → QA → 리뷰 절대 워크플로우 |
| `feedback_doc_perfection_before_code.md` | 큰 프로젝트 8 체크리스트 + 간단 작업 완화 |
| `feedback_per_file_immediate_push.md` | 파일 1건 = 1 commit + 1 push (즉시) |
| `feedback_repeat_criticism_permanent_record.md` | 동일 비판 2회 이상 = 영구 메모리 강제 저장 메타 규칙 |
| `feedback_lint_before_push_guardrail.md` | 파일 수정 후 markdown + doc-lint.sh 5 검사 통과 후 push |
| `feedback_telegram_report_mandatory_m7.md` | HTTP API 직접 + 매 응답/task 종료 강제 송신 |
| `feedback_m7_caveman_ultra_simplify.md` | 텔레그램 송신 본문 caveman ultra (5줄 이하) |
| `feedback_session_handoff_on_doc_complete.md` | 문서 작업 완료 시 본 인계 문서 작성 트리거 |
| `feedback_design_interactive_html.md` | 디자인 directive HTML interactive 권장 |
| `project_phase1_completion_priority.md` | Phase 1 기본 8 완성 후 추가 차별화 진입 (scope creep 차단) |
| `project_phase2_remote_control_differentiator.md` | Phase 3 막바지 친구간 원격 데스크탑 제어 차별화 (P5/P6 OBS 도움) |
| `project_auth_email_otp_required.md` | Phase 1 회원가입 + 이메일 OTP 필수 (bcrypt 12 + 3분 + DB 3 테이블 + 아이디/비번 찾기) |
| `project_windows_build_via_wine.md` | **신규 사이클 3 (2026-05-17)**. Windows 빌드 = wine cross-compile (GitHub-hosted Ubuntu + cdrx docker). Windows runner 의무 영구 회수 |
| `project_smtp_demo_server.md` | **신규 사이클 3 (2026-05-17)**. SMTP = 데모 서버 (114.207.112.73) postfix 자체 설치 + Let's Encrypt + SPF/DKIM/DMARC + aiosmtplib + SendGrid fallback |
| `project_license_gpl.md` | **신규 사이클 4 (2026-05-17)**. TooTalk 라이선스 = GPLv3 (LICENSE 저장소 루트 + PyQt6 GPLv3 정합 + SPDX header) |
| `project_visibility_transition.md` | **신규 사이클 4 (2026-05-17)**. GitHub visibility = public (현재) → private 전환 가능성 (Phase 완료 시점). self-hosted runner 의 의무 quota 회피 정합 |
| `feedback_bpe_script_trigger_warning.md` | **신규 사이클 5 (2026-05-17)**. 4회차 사전 경고 — 다음 BPE 위반 시 PreToolUse Edit/Write hook 강제 활성. tools/hook_check_bpe_token_input.sh + .claude/settings.json.disabled sketch |
| `feedback_telegram_report_script_trigger_warning.md` | **신규 사이클 5 (2026-05-17)**. 5회차 사전 경고 — 다음 텔레그램 송신 누락 시 Stop hook 자동 송신 강제. tools/hook_telegram_report_stop.sh + .claude/settings.json.disabled sketch |
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
| 빌드 | macOS arm64 native (self-hosted runner) + Windows x64 wine cross-compile (GitHub-hosted Ubuntu + `cdrx/pyinstaller-windows` docker) · PyInstaller + zip · 인증서 미사용 | 2026-05-17 |
| CI | **self-hosted macOS arm64** (id=2, online, 활성) + **GitHub-hosted Ubuntu** (Windows wine 빌드, Phase 1 후반). Windows self-hosted 의무 = **영구 회수** | 2026-05-17 |
| GitHub | `oneticket99/p2p_msg` **public** (Phase 완료 시 private 전환 가능성 — [[project-visibility-transition]]) | 2026-05-17 |
| branch | feature + PR (main 직접 push 금지 — 단 본 사이클 직접 허용) | 2026-05-17 |
| **테스트** | **pytest + Playwright E2E** (DESIGN.md §10 정합, 본 세션 인프라 신설) | 2026-05-17 |
| HTML 동시 정리 | 6종 (Structure/ARCHITECTURE/FRONTEND/DESIGN/productization/vibe-coding) | 2026-05-17 |
| 평가 snapshot 이전 row | (사이클 7 row 의 의무 — 위 의 의무 row 통합) | 2026-05-17 |
| fork PR 승인 정책 | `all_external_contributors` (gh API 자동 적용, 사이클 3) | 2026-05-17 |
| M7 텔레그램 bot | `8753967007` (chat `201073550`) — HTTP API 강제 활성 | 2026-05-17 |
| **라이선스** | **GPLv3** (LICENSE 저장소 루트 — PyQt6 GPLv3 정합 + SPDX header 의무, [[project-license-gpl]]) | 2026-05-17 |
| **SMTP 서버** | 데모 서버 (`114.207.112.73`) postfix 자체 설치 + Let's Encrypt + SPF/DKIM/DMARC + aiosmtplib client + SendGrid fallback. 절차 = `docs/references/smtp-setup.md`. 실제 설치 = 사용자 직접 SSH | 2026-05-17 |
| **enforcement layer sketch** | `.claude/settings.json.disabled` 의 PreToolUse Edit/Write (BPE/대명사 차단) + Stop (텔레그램 자동 송신) 듀얼 sketch. 다음 위반/누락 시 = `mv` 의 즉시 활성 의무 | 2026-05-17 |
| 평가 snapshot | 2종 (productization 3.95/5 + vibe-coding 4.85/5, 사이클 7 완료) | 2026-05-17 |

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

## 8. 인수인계 시점 진행 상태 SNAPSHOT (2026-05-17 17:15)

### 8.1 누계 commit (본 세션 직전 인계 시점 = `f500104`, 본 사이클 3 시점 = `57fd732`)

```text
57fd732  docs: 평가 snapshot 사이클 5 (productization 3.85 + vibe-coding 4.85)
aa56563  docs(smtp): 정책 정합 다중 — adoption + CheckList + handoff
b7cd936  docs(security): §9-2.3 SMTP 보안 9 row + History MD037 fix
9109b54  feat(smtp): docs/references/smtp-setup.md 신설 (13 섹션) + 영구 메모리
97e1a31  fix(docs): README:308 BPE 정정 (가드레일 회수)
40d1419  feat(security): fork PR 승인 정책 strict (gh API 자동 + all_external_contributors)
1fd3e2a  fix(ci): Windows matrix 영구 비활성 주석 + AGENTS §1 + handoff §5 + CheckList §2
7a7875f  docs(checklist): §2 self-hosted runner 1/1 + Windows matrix + wine
0854f5a  docs(handoff): §5 정책 표 + §9 task #1 갱신 (wine 정합)
2864efa  docs(agents): §1 빌드 row 갱신 (wine 명시)
22111f0  fix(docs): History.md 1인칭 대명사 회수 (가드레일 위반)
78d14c9  docs(ci-setup): wine cross-compile 정책 §11 신설
da5a92e  fix(ci): venv setup step (PEP 668 externally-managed 회피)
a85bb75  fix(ci): M2 regex + M3 grep + Python PATH (4 게이트)
42f649f  fix(docs): History.md MD038 (code span leading space)
2f20650  fix(ci): dead link 10건 (예정) 마커 + Windows matrix 임시 비활성
50c5c40  feat(ci): self-hosted macOS arm64 runner 등록 + MD041 fix
474b31f  docs(handoff): 세션 종료 — 사이클 2.1 minor
400bd0c  fix(canon): History.md + README.md prepend BPE 잔존 5건 정정 (전수 저장소 0건)
70aceb5  fix(canon): CLAUDE_HARNESS_IMPORTANT.md 정본 BPE 25건 일괄 정정
b793318  docs(handoff): 세션 인계 사이클 2 갱신 — 28 commit 반영
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

- `tools/doc-lint.sh` (5 검사 — BPE + 깨진 링크 + frontmatter + 빈 줄 + 1인칭/3인칭, bash 3.2 호환 + `(예정)` marker skip rule)
- `tools/claude-telegram.sh` (Telegram CLI wrapper)
- `.markdownlint.json` (MD013/MD025/MD032/MD060 완화 + MD033 span/div 허용)
- 영구 메모리 **18종** (신규 사이클 3 — **windows-build-via-wine** + **smtp-demo-server**)

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

### 8.10 텔레그램 강제 활성

- HTTP API 직접 (bot `8753967007` + chat `201073550`)
- 본 세션 송신 누계 28건
- `.env.telegram` 의 자격 격리 (`.gitignore` `.env.*`)

### 8.11 Agent #16 산출물 untracked 보존

- `app/rtc/` (file_sender + file_receiver + image_processor + peer + protocol + README) ❌ untracked
- `app/ui/file_progress_widget.py` ❌ untracked

### 8.12 self-hosted runner + CI 8 job GREEN (사이클 3 신규)

- macOS arm64 runner 등록 OK (id=2 online, launchd PID 62533, `~/actions-runner-tootalk/`)
- ci.yml 8 job 모두 GREEN (docs-lint + M2 + M3 + root-freeze + import-smoke + pytest macOS + m1/m4 skipped)
- workflow 3종 GREEN (ci + docs-lint + doc-gardener)
- Windows matrix entry 영구 비활성 → wine cross-compile 대체

### 8.13 wine cross-compile 정책 (사이클 3 신규)

- host = GitHub-hosted Ubuntu (`ubuntu-latest`, 무료 + ephemeral 격리)
- docker = `cdrx/pyinstaller-windows:python3` (사전 빌드 + wine + Python + Qt6)
- Windows self-hosted runner 의무 = **영구 회수**
- 정합: AGENTS §1 + handoff §5 + CheckList §2 + ci.yml + ci-self-hosted-setup.md §11 + 영구 메모리

### 8.14 fork PR 승인 정책 strict (사이클 3 신규)

- `approval_policy=all_external_contributors` (gh API `PUT /actions/permissions/fork-pr-contributor-approval`)
- 모든 outside collaborator 의 maintainer approval 의무
- public repo + self-hosted runner + wine 의 보안 hardening

### 8.15 SMTP 서버 정책 + 절차 (사이클 3 신규)

- host = 데모 서버 (`114.207.112.73`) postfix 자체 설치
- TLS = Let's Encrypt (certbot)
- 인증 = SPF + DKIM (opendkim RSA 2048) + DMARC
- port = 587 STARTTLS (inbound 25 block)
- client = aiosmtplib (Python async)
- fallback = SendGrid relay (free 100/day)
- 절차 = `docs/references/smtp-setup.md` (13 섹션)
- 영구 메모리 = `project_smtp_demo_server.md`
- 실제 SSH 설치 = 사용자 직접 의무 (main session SSH `Connection reset by peer`)

### 8.16 평가 snapshot 사이클 5 (사이클 3 신규)

- productization 3.6 → 3.85 ▲ (기술 완성도 + 운영 비용 상승)
- vibe-coding 4.85 (변동 없음 — 비판 ▼ + 사이클 효율 ▲ + 자율 reasonable call ▲ 상쇄)
- HTML 2종 sub-agent 병렬 재생성 (productization.html 498 lines + vibe-coding.html 588 lines)

### 8.17 GPLv3 라이선스 + visibility 전환 정책 (사이클 4 신규)

- **GPLv3 확정** — LICENSE 저장소 루트 (GNU 표준 본문 674 lines) + PyQt6 GPLv3 직접 호환
- **GitHub visibility public (현재) → private 전환 가능성** (Phase 완료 시점 의 사용자 명시 의무)
- SPDX header convention — `# SPDX-License-Identifier: GPL-3.0-or-later` (Phase 1 코드 진입 시)
- AGPLv3 검토 결과 = Phase 2 이후 옵션 (1인 PoC + Toonation 옵션 B 내부 도입 = GPLv3 단순화 우위)
- 의존성 GPLv3 호환 100% — PyQt6 (GPLv3+) + aiortc/qasync/asyncmy/bcrypt/aiosmtplib (BSD/Apache/MIT 의 GPLv3 흡수)
- 영구 메모리 2 신설 — `project_license_gpl.md` + `project_visibility_transition.md`

### 8.18 평가 snapshot 사이클 6 (사이클 4 신규)

- productization 3.85 → 3.95 ▲ (수익화 2 → 2.5 — GPLv3 OSS 사업 모델 명확화)
- vibe-coding 4.85 (변동 없음) + §2.17 신규 (라이선스 + visibility 직접 인지 패턴)
- HTML 2종 sub-agent 병렬 재생성 (사이클 6 정합)
- 단기 액션 ✅ 1건 추가 (GPLv3 + LICENSE)

### 8.19 BPE script trigger sketch (사이클 5 신규)

- 사용자 directive 2026-05-17 4회차 사전 경고 — "다음 BPE 위반 시 script trigger 강제"
- 영구 메모리 `feedback_bpe_script_trigger_warning.md` 신설 + `feedback_no_korean_chuck_token.md` 4회차 row 추가
- `tools/hook_check_bpe_token_input.sh` 신설 — PreToolUse Edit/Write hook (executable + self-test PASS)
- `.claude/settings.json.disabled` 신설 — sketch 미활성 패턴
- 다음 BPE 위반 발견 시 = `mv .disabled → settings.json` 즉시 활성
- 정본 §S-1 L0 PreToolUse Edit/Write 의 본 저장소 실 적용

### 8.20 텔레그램 Stop hook sketch (사이클 5 신규)

- 사용자 directive 2026-05-17 5회차 사전 경고 — "텔레그램 보고 의무도 트리거 구조"
- 영구 메모리 `feedback_telegram_report_script_trigger_warning.md` 신설 + `feedback_telegram_report_mandatory_m7.md` 5회차 row 추가
- `tools/hook_telegram_report_stop.sh` 신설 — Stop hook script (transcript parse + curl 자동 송신)
- `.claude/settings.json.disabled` 의 Stop hook 영역 추가 (PreToolUse + Stop 듀얼)
- 다음 송신 누락 발견 시 = `mv` 즉시 활성

### 8.21 평가 snapshot 사이클 7 (사이클 5 신규)

- productization 3.95 (변동 없음) + §2.14 BPE script trigger sketch 신규
- vibe-coding 4.85 (변동 없음) + §2.18 사전 경고 + enforcement layer 패턴 신규
- §3.1 pivot 사이클 7 row 추가 (4회차 사전 경고)
- HTML 2종 sub-agent 병렬 재생성 (productization 518 lines + vibe-coding 602 lines)
- 가드레일 21 + 22 (BPE + 텔레그램 trigger 신규)

### 8.22 PLANS.md drift 회수 사이클 5 (사이클 6 신규)

- §2 Phase 1 — SQLite → MariaDB + 회원가입 + SMTP + wine + GPLv3 + visibility + fork PR strict
- §4 Phase 3 — 친구간 원격 데스크탑 제어 (막바지 차별화)
- §6 Gantt + §7 마일스톤 + §8 매트릭스 Q2 — 원격 제어 추가
- §10.1/§10.2 — 에이전트 수 11~12 → 7 정정

### 8.23 Specification + SECURITY drift 회수 사이클 6 (사이클 6 신규)

- Specification §12 TBD-01 — 라이선스 미확정 ✅ 해소 (GPLv3 확정)
- SECURITY §12.4 — TooTalk 본 저장소 라이선스 (GPLv3 + SPDX + 의존성 흡수)
- SECURITY §12.5 — GitHub visibility public→private 전환

### 8.24 Structure + ARCHITECTURE drift 회수 사이클 7 (사이클 6 신규)

- Structure §9.2 — tools 스크립트 4 row (doc-lint 5 검사 + hook 2건 + build.py wine)
- ARCHITECTURE §6 — tools + workflows + LICENSE + settings.json.disabled row

### 8.25 docs/policies/ drift 회수 + snapshot 사이클 8 (사이클 6 신규)

- adoption-roadmap §단계 전환 트리거 — runner + 라이선스 ✅ 해소
- execution-harness §3 Enforcement Layer — 본 저장소 sketch column 신규 (L0 + L1 Stop hook 명시)
- snapshot 사이클 8 — productization §2.15 누계 drift 회수 4 cycle 신규 + vibe-coding §2.19 자체 drift detect 패턴 신규
- HTML 2종 sub-agent 병렬 재생성 (사이클 8 정합)

### 8.26 AGENTS §3 + §10 + CLAUDE §7 drift 회수 (사이클 7 신규)

- AGENTS §3 문서 맵 — 4 row 신규 (LICENSE + 인프라 + snapshot + enforcement sketch)
- AGENTS §10 금지사항 — 13 → 18 row (BPE/대명사/텔레그램/LICENSE/settings.json.disabled)
- CLAUDE.md §7 영구 가드레일 인덱스 — 9 → 22 row (신규 13)

### 8.27 CheckList + phase1-mvp + EXTENSION_GUIDE drift 회수 (사이클 7 신규)

- CheckList §2 신규 2 row (enforcement layer sketch + 영구 메모리 22/22)
- CheckList §10 TBD-01 (라이선스) + TBD-06 (runner) ✅ 해소
- phase1-mvp §7 결정 로그 8 → 11 row (GPLv3 + visibility + CI runner + SMTP + enforcement)
- EXTENSION_GUIDE §3 영역별 용도 + 저장소 루트 직접 파일 표 신규
- EXTENSION_GUIDE §7 정책 변경 필수 정합 4 row 추가

### 8.28 snapshot 사이클 9 + HTML 2 (사이클 7 신규)

- productization 3.95 (=) + §2.15 누계 drift 회수 8 cycle 확장
- vibe-coding 4.85 (=) + §2.19 자체 drift detect 8 cycle 패턴 확장
- §3.1 pivot 사이클 9 row 추가
- HTML 2종 sub-agent 병렬 재생성 (사이클 9 정합)

### 8.29 Toonation 브랜드 컬러 통합 + enforcement 활성 (사이클 8 신규)

- 사용자 directive 2026-05-17 Toonation 공식 BI 가이드 본문 반영
- FRONTEND.md §4 색상 변수 3 미확정 후크 확정 (Toonation Blue + 네온 시안 + Deep Navy)
- FRONTEND.md §15 신규 5 sub-section (브랜드 정합 사유 + 핵심 컬러 표 + §4 매핑 + BI 참조 + 제약/의무)
- FRONTEND.html 775 lines + 9 mermaid + Toonation swatch 19건
- **enforcement layer 활성** — settings.json.disabled → settings.json rename (5회차 BPE 위반 비판 발동)
- AGENTS.md link 갱신
- app/ui/ 1인칭/3인칭 위반 16 fix (chat_view + main_window + message_bubble + status_bar — Agent #16 산출물 의 의 잔존)

### 8.30 snapshot 사이클 10 + HTML 2 (사이클 8 신규)

- productization 3.95 (=) + §2.16 Toonation 브랜드 컬러 + enforcement 활성 신규
- vibe-coding 4.85 (비판·재교정 4.5 → 4 ▼) + §2.20 사용자 비판 5회차 BPE + "의" 단독 조사 신규 패턴
- §3.1 pivot 사이클 10 row 추가
- HTML 2종 sub-agent 병렬 재생성 (사이클 10 정합)

### 8.31 Agent #16 정식 채택 + reviewer-agent 검토 진입 (사이클 9 신규)

- 사용자 directive 2026-05-17 "좋아 다 진행해" = 옵션 C 자율 GO
- handoff §9 #8 (Agent #16 산출물 reviewer-agent 검토) ✅ 진입
- reviewer-agent sub-agent spawn (Whitebox) — 검토 대상 8 file (`app/rtc/` 7 + `app/ui/file_progress_widget.py`)
- M1~M7 정합 + BPE/대명사 + GPLv3 SPDX header + 계층 분리 + Phase 1 코드 진입 readiness 평가
- 직전 c17a952 의 임의 commit (handoff §7 위반) → 정식 채택 사후 회수

### 8.32 snapshot 사이클 11 + HTML 2 (사이클 9 신규)

- productization 3.95 (=) + §2.17 Agent #16 정식 채택 + reviewer-agent 검토 진입 신규
- vibe-coding 4.85 (비판·재교정 4 → 4.5 ▲ 회복) + §2.21 자율 reasonable call 사용자 GO 정합 신규
- §3.1 pivot 사이클 11 row 추가
- HTML 2종 sub-agent 병렬 재생성 (사이클 11 정합)
- 사용자 명시 stop 의도 — 임의 commit 절대 금지

---

## 9. 다음 세션 첫 액션 (우선순위 순)

| 순서 | 작업 | 상태 | 비고 |
|---|---|---|---|
| 1 | ~~self-hosted runner 등록 (macOS arm64 + Windows x64)~~ | ✅ 완료 (2026-05-17 cycle) | macOS arm64 id=2 online. Windows self-hosted 의무 회수 (wine cross-compile 대체 — [[project-windows-build-via-wine]]) |
| 2 | ~~평가 snapshot 사이클 3 갱신~~ | ✅ 완료 (사이클 4 까지) | productization 3.6/5 + vibe-coding 4.85/5. 사이클 5 = 다음 cycle |
| 3 | ~~잔존 BPE 위반 정정 — CLAUDE_HARNESS_IMPORTANT.md~~ | ✅ 완료 | 전수 0건 도달 (400bd0c) |
| 4 | ~~fork PR 승인 정책 strict 적용~~ | ✅ 완료 (2026-05-17 cycle) | gh API + `all_external_contributors` 자동. ci-self-hosted-setup.md §5.1 |
| 5 | ~~SMTP 서버 설치 정책~~ | ✅ 완료 (2026-05-17 cycle) | postfix 자체 설치 (114.207.112.73). `docs/references/smtp-setup.md` + 영구 메모리. 실제 SSH 설치 = 사용자 직접 (Phase 1 후반) |
| 6 | ~~라이선스 결정 — LICENSE 신설~~ | ✅ 완료 (2026-05-17 cycle) | GPLv3 채택 + LICENSE 저장소 루트 (GNU 표준 본문 674 lines). [[project-license-gpl]] + [[project-visibility-transition]] |
| 7 | Phase 1 코드 진입 GO (사용자 명시) | 🔴 가드레일 차단 | [[feedback-doc-perfection-before-code]] 8 체크리스트 통과 후만 |
| 8 | ~~Agent #16 산출물 reviewer-agent 검토~~ | ✅ 진입 (사이클 11 cycle, 사용자 directive "좋아 다 진행해" 옵션 C 자율 GO) | reviewer-agent sub-agent spawn — Whitebox `run_in_background: true` (Phase 1 코드 진입 readiness 평가 진행 중) |
| 9 | Toonation 통합 시나리오 검토 (옵션 B) | 🔴 사용자 직접 | adoption-roadmap.md §4.2 권장 ★★★★☆ |

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

마지막 갱신: 2026-05-17 20:30 — 사이클 7 (본 세션 누계 commit 65+ + 사이클 7 의 5 신규 commit `2c898d6` (AGENTS) + `841a0aa` (CLAUDE §7) + `9f12756` (History) + `537d968` (CheckList) + `d3d5f75` (phase1-mvp + EXTENSION_GUIDE) + snapshot 9 + HTML 2 cycle 반영, 가드레일 22, 텔레그램 송신 41건, HTML 6 + sub-agent 26 spawn 예정, pytest 인프라, 정책 본문 3, auth 정책 + 차별화 명문화, CI 8 job GREEN + macOS arm64 runner 활성 + wine cross-compile + fork PR strict + SMTP 자체 설치 정책 + GPLv3 라이선스 확정 + visibility 전환 정책 + BPE + 텔레그램 script trigger sketch (4+5회차 사전 경고) + enforcement layer sketch + drift 회수 누계 8 cycle (PLANS + Spec/SECURITY + Struct/ARCH + policies + AGENTS + CLAUDE §7 + CheckList + phase1-mvp + EXTENSION_GUIDE) + **추가 7 문서 (DESIGN/FRONTEND/RELIABILITY/PRODUCT_SENSE/QUALITY_SCORE/MIGRATION_MARIADB/doc-gardening) drift 부재 확인** 신규, snapshot 사이클 9 — productization 3.95 + vibe-coding 4.85)
