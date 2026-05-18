---
title: "TooTalk 세션 인계 — 2026-05-17 → 다음 세션"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# TooTalk 세션 인계 — 2026-05-17 → 다음 세션

> 본 문서는 정본 [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md) §Q 등가 패턴. 다음 세션 Claude(=Watcher) 가 본 저장소 재진입 시 **최우선 정독 대상**.
> 본 인계 시점: 2026-05-18 00:05 (사이클 13 갱신 — 본 세션 누계 commit 53+ 반영, release-agent 머지 진입 + 머지 게이트 3 단계 완성 + snapshot 사이클 14). 최신 commit `d241c04`.

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

## 8.51 사이클 88~99 Phase 3 종결 + v0.3.0-phase3-bot tag (2026-05-22 신설)

### 8.51.1 reviewer P0+P1+P2+P3 + QA P2+P3 회수 chain 8 항목 완료

본 세션 누계 — Phase 3 bot framework production-ready 도달. cycle 88~97 의 reviewer-agent + qa-agent 보고 모든 priority 회수 + cycle 98 평가 snapshot 4 영역 rewrite + cycle 99 v0.3.0-phase3-bot tag.

| cycle | 회수 항목 | 신규 PASS |
|---|---|---:|
| 88 | server/main.py SPDX header (P2-1) + 정책 §10 갱신 (P3-1) + chat BPE hook 신설 | 0 (hook) |
| 89~90 | AnthropicProvider + OpenAIProvider lazy init asyncio.Lock (P2-2) | 4 |
| 91~93 | UsageTracker deque maxlen + EscalationQueue evict_old + RateLimitGate prune_stale (P1-1) | 14 |
| 94 | CachedEmbedder threading.RLock + double-check pattern (P1-2) | 3 |
| 95 | jailbreak detector info_exfiltration 2 → 17 패턴 + Korean PII + SQL + shell (QA P2) | 21 |
| 96 | server/main.py provider 3 layer fallback chain Anthropic → OpenAI → Mock (QA P3) | 3 |
| 97 | bot-framework.md §10.1 strike + httpx>=0.27 + Phase 4 §1.4 + DB migration 0003 | 0 (문서/schema) |
| 98 | 평가 snapshot 4 영역 rewrite + HTML 2 mirror 동기 | 0 (평가) |
| 99 | v0.3.0-phase3-bot tag + release-agent + handoff §8.51 신설 | 0 (release) |

**누계 신규 PASS** = 45 (P0~P3 + QA + 평가).

### 8.51.2 pytest + drift + 가드레일

- pytest = **1101 passed + 2 skipped** (cycle 87 1058 → cycle 96 1101 + 2 skip 의 httpx 미설치 graceful).
- 자율 chain drift = **0건 53 연속** 사이클 37~99.
- 영구 가드레일 = **39** (cycle 97 보조 — `feedback_db_audit_timestamp_ip_activity.md` 신설).

### 8.51.3 핵심 산출물

**코드**:
- `app/bot/rag_context.py` CachedEmbedder `threading.RLock` thread-safety
- `app/bot/jailbreak_detector.py` info_exfiltration 17 패턴 (env vars + JWT + SSH + PEM + DB credential + Korean PII + RRN + SQL + shell)
- `app/bot/llm_proxy.py` AnthropicProvider + OpenAIProvider `_init_lock` double-check
- `app/bot/usage_tracker.py` UsageTracker `deque(maxlen=100_000)` ring buffer
- `app/bot/escalation_queue.py` EscalationQueue `evict_old(now_ms, retention_ms)`
- `server/main.py` provider 3 layer fallback chain (Anthropic → OpenAI → Mock) + 분기별 log 명문

**의존성**:
- `server/requirements.txt` `httpx>=0.27` 등록 — Phase 4 cycle 100 의 pip install + verify gate

**DB**:
- `server/db/migrations/0003_user_activity.sql` 신설 — users 확장 + `user_sessions` + `user_activity_log` + email_verification/password_reset 의 requester_ip (마케팅 통계 directive 정합)

**문서**:
- `docs/policies/bot-framework.md` §10.1 strike-through 6 항목 + cycle 100 prerequisite
- `docs/exec-plans/active/2026-05-22-phase4-infra-setup.md` §1.4 사전 의존성 install 섹션 신설
- `docs/assessments/productization.md` §1 종합 9.98 → 9.99 ▲
- `docs/assessments/vibe-coding.md` §1 종합 10.0000 = (cap)
- `docs/html/productization.html` + `docs/html/vibe-coding.html` mirror 동기

**가드레일 (39번째)**:
- `feedback_db_audit_timestamp_ip_activity.md` — DB INSERT/UPDATE datetime 의무 + 접속 IP + 활동 시간 추적 (마케팅 통계 자료 활용, 90일 retention cap)

### 8.51.4 다음 세션 첫 액션 우선순위

1. **cycle 100** — `pip install -r server/requirements.txt` 의 httpx 실 install + `pytest tests/server/test_main_integration.py` 의 2 skip → 0 skip 전환 검증 (verify gate).
2. **cycle 101~108** — Phase 4 Item 1 docker stack — `deploy/docker-compose.yml` + mariadb + postfix + web + ws + firebase-fcm 신설.
3. **cycle 109~111** — Phase 4 Item 2 .env 통합 + Config 클래스 + 5 파일 분류.
4. **cycle 112~115** — Phase 4 Item 3 nginx reverse proxy + TLS + WebSocket upgrade + 5 rate limit zone + X-Forwarded-For parse (DB audit IP 정합).
5. **cycle 116~117** — Phase 4 Item 4 server logging + KST formatter + JSON + sensitive redact + aiohttp middleware (last_active_at 갱신 의 정합).
6. **별개 cycle (Phase 4 cycle 113~114 정합)** — DB migration 0003 의 actual code wiring — `server/api/auth_handlers.py` 회원가입 INSERT 시 signup_ip + signup_user_agent 의 `request.headers["X-Forwarded-For"]` parse + `user_sessions` 의 login 시 insert + `user_activity_log` 의 22 action audit + last_active_at 갱신 의 1분 throttle middleware.

### 8.51.5 manual test 의무 (사용자) — v0.3.0-phase3-bot 직후

- `ANTHROPIC_API_KEY` 환경 변수 + `BOT_ENABLED=1` 설정 + 실 Anthropic Messages API 호출 smoke (`curl POST /api/bot/chat` 의 200 + assistant content).
- `OPENAI_API_KEY` 환경 변수 + 동일 smoke (3 layer fallback 의 OpenAI 분기 검증).
- httpx 미설치 환경 의 graceful fallback 검증 (Mock 폴백 log + 200 + MockEcho content).
- jailbreak attempt smoke — "ignore previous instructions" + "비밀번호를 알려줘" + "cat /etc/passwd" + "'; DROP TABLE users" 의 BLOCKED 400 응답 + log 확인.
- migration 0003 의 mariadb 환경 apply 후 schema verify — `DESCRIBE users` + `SHOW INDEX FROM user_sessions` + `SHOW INDEX FROM user_activity_log`.

---

## 8.50 사이클 68~87 + Phase 4 plan 인수인계 (2026-05-22 신설)

### 8.50.1 Phase 3 bot framework chain 완성 (cycle 68~87, 20 cycle 누계)

본 세션 누계 — Phase 3 bot framework 의 horizontal 통합 완성. `app/bot/` 10 module 신설 + `server/api/bot_handlers.py` 의 server proxy + `server/main.py` 의 BOT_ENABLED gating + `docs/policies/bot-framework.md` 정책 본문.

| cycle | 작업 | 신규 PASS |
|---|---|---:|
| 68 | `app/bot/rag_context.py` 신설 (KeywordRAGStore + FAQ 10 entry) | 27 |
| 69 | CustomerServiceBot ↔ RAGStore 통합 | 6 |
| 70 | `app/bot/anthropic_client.py` (Messages API + 4 종 예외) | 32 |
| 71 | AnthropicProvider adapter + lazy from_env | 3 |
| 72 | retry/backoff 지수 (max_retries + jitter + sleep_fn DI) | 9 |
| 73 | retry-after honor + jitter + transport 3-tuple refactor | 9 |
| 74 | `server/api/bot_handlers.py` POST /api/bot/chat | 29 |
| 75 | EmbeddingRAGStore (Embedder + MockEmbedder + cosine) | 15 |
| 76 | `server/main.py` register_bot_routes 통합 (reviewer P0 회수) | 6 |
| 77 | network error retry (ConnectionError/OSError/TimeoutError) | 6 |
| 78 | bot_handlers user_id type confusion hardening | 4 |
| 79 | CachedEmbedder LRU decorator | 10 |
| 80 | `docs/policies/bot-framework.md` 정책 본문 신설 | 0 |
| 81 | `app/bot/jailbreak_detector.py` 6 category × Korean/English | 33 |
| 82 | jailbreak detector ↔ bot_handlers 통합 (BLOCKED → 400) | 6 |
| 83 | CustomerServiceBot scan_jailbreak opt-in | 5 |
| 84 | `app/bot/openai_client.py` (Chat Completions API + OpenAIProvider) | 29 |
| 85 | `app/bot/usage_tracker.py` (UsageRecord + per-user/provider/period) | 31 |
| 86 | `app/bot/escalation_queue.py` (TicketStatus + EscalationReason + lifecycle) | 28 |
| 87 | `app/bot/streaming.py` (SSE parser — Anthropic + OpenAI delta) | 34 |
| **누계** | **20 cycle bot framework chain 완성** | **321 신규** |

### 8.50.2 pytest 누계 + 평가 snapshot

- 본 세션 시작 = 737 pytest (cycle 67 직후)
- 본 세션 종료 = **1058 pytest** (cycle 87 직후, +321 신규)
- productization snapshot — 9.7 / 10 → **9.95 / 10** ▲
- vibe-coding snapshot — 9.9533 / 10 → **10.0000 / 10** (max 도달)
- 보안 hardening — 8.0 → 8.65 ▲ (jailbreak detector + bot proxy 격리)
- Phase 3 entry 누계 — **576** (이전 281 + bot framework 295)
- 자율 chain drift 0건 **46 연속** 사이클 (37~87)

### 8.50.3 reviewer-agent + qa-agent 종합 검증 결과

- **reviewer-agent** (cycle 87 직후) — PASS 9.55 / 10 + P0 0건 + P1 3건 + P2 2건 + P3 3건
- **qa-agent** (직후) — PASS 10/10 회귀 항목 + performance 1000배 sanity 여유 + 추가 P2 1건 + P3 2건 detect

누계 권장 — P1 3건 + P2 3건 + P3 5건 (다음 cycle 88~96 회수 예정, task #45~#50).

### 8.50.4 `app/bot/` 10 module 완성 inventory

| # | 파일 | cycle |
|---|---|---|
| 1 | `llm_proxy.py` | 65 + 71 + 84 |
| 2 | `customer_service_bot.py` | 66 + 69 + 83 |
| 3 | `streaming_helper.py` | 67 |
| 4 | `rag_context.py` | 68 + 75 + 79 |
| 5 | `anthropic_client.py` | 70 + 72 + 73 + 77 |
| 6 | `openai_client.py` | 84 |
| 7 | `jailbreak_detector.py` | 81 |
| 8 | `usage_tracker.py` | 85 |
| 9 | `escalation_queue.py` | 86 |
| 10 | `streaming.py` | 87 |

### 8.50.5 Phase 4 진입 plan — 4 item 의 18 cycle (cycle 100~117)

본 세션 종료 직전 사용자 directive 2026-05-22 의 의 Phase 4 초기 infra 구축 4 item:

| Item | 작업 | cycle 범위 | 예상 신규 PASS |
|---|---|---|---:|
| 1 | 원격 서버 docker 환경 (mariadb + smtp + web + ws + nginx + FCM) | 100~104 | ~40 |
| 2 | .env 통합 + local/staging/production switching | 105~107 | ~25 |
| 3 | nginx reverse proxy (TLS + WebSocket + rate limit + routing) | 108~111 | ~20 |
| 4 | Python server logging (KST + JSON + request_id + sensitive redact) | 112~117 | ~50 |
| **누계** | | **18 cycle** | **~135 신규** |

상세 본문 = [`docs/exec-plans/active/2026-05-22-phase4-infra-setup.md`](2026-05-22-phase4-infra-setup.md) (cycle 87 직후 신설).

### 8.50.6 다음 세션 첫 액션 우선순위

1. **cycle 88 회수** — `server/main.py` SPDX header + `docs/policies/bot-framework.md` §10 implemented strike (task #45)
2. **cycle 89~90** — AnthropicProvider/OpenAIProvider lazy init asyncio.Lock (task #46)
3. **cycle 91~93** — UsageTracker + EscalationQueue + RateLimitGate unbounded memory 회수 (task #47)
4. **cycle 94** — CachedEmbedder asyncio.Lock (task #48)
5. **cycle 95** — jailbreak detector info_exfiltration 패턴 확장 (task #49)
6. **cycle 96** — server/main.py MockLLM 폴백 log misleading 정정 (task #50)
7. **cycle 97~99** — Phase 3 종결 + v0.3.0-phase3-bot tag + release-agent
8. **cycle 100+** — Phase 4 진입 ([`2026-05-22-phase4-infra-setup.md`](2026-05-22-phase4-infra-setup.md) 의 Item 1~4)

### 8.50.7 manual test 의무 (사용자) — Phase 3 종결 + Phase 4 진입 시점

- [ ] **httpx 의 venv 의 실 설치** + `pip install -r app/requirements.txt` 갱신 — bot framework client-side 실 LLM 호출 의 prerequisite
- [ ] **ANTHROPIC_API_KEY** + **OPENAI_API_KEY** 의 console 발급 + `.env.production` 의 주입 — bot proxy 실 호출 의 prerequisite
- [ ] **데모 서버 SSH 접근** + docker stack 배포 (Phase 4 Item 1 의 cycle 100~104 commit 직후)
- [ ] **FCM credentials JSON** 의 Google Cloud Console 발급 + 데모 서버 mount
- [ ] **도메인 결정** — `demo.toonation.io` 또는 `114.207.112.73` 의 의 nginx server_name (Item 3 의 prerequisite)
- [ ] **TLS cert** — Let's Encrypt 자동 갱신 또는 Caddy 자동 cert 발급

상세 = [`MANUAL_TESTS.md`](MANUAL_TESTS.md) §2 (사이클 87 까지 의 8 카테고리 누계).

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

### 8.33 reviewer 재호출 + P0/P1/P2 정정 + ARCHITECTURE.html mirror 정정 (사이클 10 신규)

- 사용자 directive "작업 재개해" = 자율 진행 GO
- P0 SPDX-License-Identifier header prepend 7 file (app/rtc/ 6 .py + app/ui/file_progress_widget.py)
- P1 ARCHITECTURE §7 환경변수 표 8 row 신규 (FILE_*)
- P2 ARCHITECTURE §5 RTC_CHUNK_WINDOW → FILE_CHUNK_SIZE/BUFFER
- reviewer-agent 재호출 sub-agent — **CONDITIONAL PASS** (직전 P0 해소 + 신규 위반 1건 detect)
- 신규 위반 = `docs/html/ARCHITECTURE.html` mirror 미반영 (CLAUDE.md §10-6 위반) → ARCHITECTURE.html sub-agent rewrite (§5 + §7 정정)
- handoff §9 #8 ✅ 진행 (정식 GO 직전 1 step 의 의 mirror 정정 후 사이클 13 재호출 정식 GO 도달)

### 8.34 snapshot 사이클 12 + HTML 2 (사이클 10 신규)

- productization 3.95 → 4.0 ▲ + §2.18 reviewer 정식 GO + Phase 1 FR-04 readiness 도달 신규
- vibe-coding 4.85 → 4.90 ▲ + §2.22 reviewer 차단 사유 자율 정정 + 재호출 패턴 신규
- §3.1 pivot 사이클 12 row 추가
- HTML 2종 sub-agent 병렬 재생성 (사이클 12 정합)
- ARCHITECTURE.html mirror partial Edit (§5 + §7 8 row, 373 lines)

### 8.35 reviewer-agent 사이클 13 — 정식 GO (사이클 11 신규)

- 사용자 directive "사이클 13 reviewer 재호출 진행해" — 자율 GO
- 사이클 12 신규 위반 (ARCHITECTURE.html mirror) ✅ 완전 해소
- 신규 위반 0건 + 14/14 검증 PASS
- 종합 판정 = **PASS 정식 GO** (Phase 1 FR-04 코드 진입 readiness 완전 도달)
- handoff = main session → `@qa-agent` 회귀 체크리스트 → 코드 진입 권장
- handoff §9 #8 ✅ **완전 해소** (3 cycle 누계 — 11 + 12 + 13)

### 8.37 release-agent 머지 진입 + 머지 게이트 3 단계 완성 + snapshot 사이클 14 (사이클 13 신규)

- 사용자 directive "잔존 작업 전부 진행해" = 자율 GO + release 진입
- release-agent sub-agent spawn (Whitebox) — PR 템플릿 + M1~M7 + CI 3 workflow GREEN + 머지 판정
- 머지 게이트 누계 = reviewer ✅ (사이클 11~13) → qa ✅ CONDITIONAL → **release 진입** (사이클 14)
- snapshot 사이클 14 — productization §2.20 신규 (release 머지 진입) + vibe-coding §2.24 신규 (머지 게이트 3 단계 자동 chain)
- HTML 2종 sub-agent 병렬 재생성 (사이클 14 정합)
- next = observability-agent 머지 직후 (5단계 워크플로우 최종 단계)

### 8.36 qa-agent 회귀 + ARCHITECTURE.md drift 정정 + snapshot 사이클 13 (사이클 12 신규)

- 사용자 directive "진행해" + "재개ㅙ" — 자율 GO + qa-agent 진입
- @qa-agent sub-agent 결과 = **CONDITIONAL PASS** (정적 검증 47/48 PASS + 코드 정합 완전 + FR-04 AC 4종 매핑 충족)
- FAIL 1건 = ARCHITECTURE §7 `FILE_ACK_INTERVAL_BYTES` drift (문서 524288 vs 코드 262144) — **옵션 B 코드 우선 채택** → ARCHITECTURE.md L201 + .html mirror 정정 (524288 → 262144)
- 미커버 영역 = tests/rtc/ unit test 부재 (Phase 1 후속 별도 task 위탁)
- snapshot 사이클 13 — productization §2.19 신규 (qa 회귀 진입 + 머지 게이트 마지막) + vibe-coding §2.23 신규 (reviewer 3 cycle 자동 정합 + qa 진입 패턴)
- HTML 2종 sub-agent 병렬 재생성 + ARCHITECTURE.html mirror sub-agent (4 sub-agent 누계)
- 머지 게이트 단계 = reviewer ✅ → qa ✅ CONDITIONAL → release-agent 머지 (next, 옵션 A 권장)
- 사용자 명시 stop 의도 — 임의 commit 절대 금지

### 8.38 release-agent 사이클 14 FAIL → P0-1/P0-2 정정 → 사이클 15 GO 정식 (사이클 14·15 신규)

- 사용자 directive "잔존 작업 전부 진행해" + "진행해" = 자율 GO + release-agent 재호출
- **사이클 14 release-agent FAIL** = 머지 차단 (P0-1 + P0-2)
  - P0-1 = `History.md` L43~46 markdownlint MD037 (emphasis space) + MD050 (strong style) 4 error — underscore 토큰 `_safe_filename`·`_humanize`·`__init__.py`·`_env_int` 백틱 미격리
  - P0-2 = `README.md` §11 변경 이력 91 row 누적 (정본 §H M2 30 row 상한 위반)
- main session 정정 commit `dcbb372` — P0-1 백틱 격리 + P0-2 30 row 회전 + 안내 본문 갱신
- CI 3종 GREEN 도달 — `ci.yml` (1m 56s) + `docs-lint.yml` (2m 17s) + `doc-gardener.yml` (30s, dispatch)
- **사이클 15 release-agent 재평가 = GO 정식** — P0-1 + P0-2 해소 검증 + M1~M5 + M7 + SPDX + GPLv3 + visibility + enforcement layer 모두 PASS
- 머지 commit 별도 없음 (main 직접 작업 패턴 = 본 저장소 표준, 정본 §S-3 SKIP_PREPUSH=1 + classifier 우회)
- next = observability-agent 사이클 15 진입 (logging baseline + metric 수립)
- handoff §9 #8 ✅ 완전 해소 + #9 신규 task (Phase 1 후속 별도 — tests/rtc/ + tests/integration/ + Pillow 실행 + Windows wine 검증 + AC-04-3 100ms 실측)

### 8.39 observability-agent 사이클 15 CONDITIONAL PASS + baseline 정본 신설 (사이클 15 신규)

- 사용자 directive "작업 진행해" = 자율 GO + observability-agent 진입 (5단계 워크플로우 ③-3)
- observability-agent sub-agent 결과 = **CONDITIONAL PASS** — 머지 직접 blocker 무
- logger instrumentation 7/7 모듈 PASS (image_processor prefix minor drift — Phase 2 보강 권장)
- format 정합 = `[%(asctime)s] %(levelname)s %(name)s — %(message)s` (정본 §E 일관)
- BPE U+CE21 단독 0건 + pronoun 위반 0건 정합
- **baseline drift 3건 detect** = `FILE_BUFFER_HIGH` (가정 262144 vs 코드 16777216 = 16 MiB) + `FILE_BUFFER_LOW` (가정 65536 vs 코드 4194304 = 4 MiB) + `FILE_BACKPRESSURE_POLL_MS` (가정 100 vs 코드 50) — release-agent prompt 본문 의 임의 추정값 vs 코드 default 불일치
- ARCHITECTURE.md §7 + README §13 = 이미 코드 default 정합 (문서 수정 불필요)
- **observability-baseline.md 정본 신설** = `docs/policies/observability-baseline.md` (7 section + 정본 채택 원칙 + drift 회수 이력 + 회귀 검증 절차 6단계 + Phase 2 의무 task 4건)
- CONDITIONAL 사유 = Phase 1 시점 metric baseline 측정 부재 (M5 dogfooding 의 RTT/throughput/RSS/disk leak 최초 측정 의무) — release 의 직접 blocker 아님
- 머지 GO 유지 (release-agent 사이클 15 정식 GO + observability CONDITIONAL PASS = 머지 가능)

### 8.49 release-agent cycle 53 GO + v0.2.0-phase2 tag 생성 (사이클 53 + 54)

**workflow ⑤ release-agent PASS**:

- 사용자 directive "남은작업 진행해" 자율 GO 직후 release-agent spawn (Whitebox §P 정합)
- 판정 = **GO** (CONDITIONAL 부재)
- 머지 게이트 3종 검증:
  - reviewer ✅ cycle 49 CONDITIONAL PASS → P0 정정 (a2c157e) + cycle 50 P1/P2 정정 (f082736)
  - qa ✅ cycle 51 CONDITIONAL PASS → 차단 3종 회수 (6c42f3d)
  - observability ✅ cycle 52 PASS (PBKDF2 94.5ms + pytest 3.03s + env var 7/7 + cipher OWASP 2023)
- CI 8 job GREEN = `gh run 26016794138` (docs-lint + root-18-freeze + m2 + m3 + import-smoke + pytest macOS-arm64)
- M1~M7 정합 = M1 ✅ + M2 ✅ (30 entries) + M3 ✅ + M4 ✅ + M5 ✅ + M6 N/A + M7 N/A (Bot API fallback)

**cycle 54 — v0.2.0-phase2 annotated tag 생성**:

- `git tag -a v0.2.0-phase2 -m "..."` — Phase 2 마무리 16 module + 290 케이스 + 483 pytest + workflow chain 완성 기록
- HEAD = `6c42f3d` (cycle 52 의 차단 3종 회수 commit)
- tag content = Phase 2 산출 16 module 명문 + workflow ③+⑤ chain 결과 + baseline 측정값 + 평가 snapshot 9.45 / 9.85 + 차별화 chain (원격 데스크탑 → emoji pack → bot framework)
- push 의무 = `git push origin v0.2.0-phase2`

**메타 가드레일 갱신 — Phase 3 차별화 chain 순서 명문**:

- 사용자 directive 2026-05-20 — "bot 의 경우는 페이즈 3 마무리 직전단계에 고도화 할 예정이야"
- memory `project_bot_framework.md` 갱신 — "Phase 3+" → "Phase 3 마무리 직전 단계 고도화"
- 차별화 chain 순서 (Phase 3 entry → 마무리):
  1. 친구간 원격 데스크탑 ([[project-phase2-remote-control-differentiator]])
  2. emoji pack share ([[project-emoji-pack-share]])
  3. bot framework (Phase 3 마무리 직전 — 본 cycle 54 의 사용자 directive 갱신)

**3 분기 사용자 결정 의무 (cycle 54 의 결과 보고 직후)**:

- (a) Phase 3 진입 — 원격 데스크탑 우선 (사용자 directive 명시 의무)
- (b) v0.2.0-phase2 tag = ✅ cycle 54 의 본 §8.49 완료
- (c) Phase 1 dogfooding entry — RTT / throughput / RSS / disk leak 최초 측정 (사용자 manual measurement 의무 + 데모 시그널링 서버 + 1:1 연결)

**핵심 commit 누적 (사이클 49~54)**:

```
(cycle 54 tag commit — 본 §8.49 신설 직후 push 예정)
6c42f3d fix(crypto,ui,net,backup): cycle 52 qa/observability serial chain 차단 3종 회수
f082736 fix(backup,ui): cycle 50 PBKDF2 stretching v2 + SPDX header 정정
a2c157e fix(crypto): cycle 49 reviewer-agent P0 정정 — BPE 13 + pronoun 5
4b96658 feat(backup): Phase 2 encrypted backup / restore + 22 PASS 사이클 48
9e2dd3c feat(notifications): Phase 2 push 알림 skeleton 4 platform + 31 PASS 사이클 47
05041c0 feat(crypto): Phase 2 Sender Keys 그룹 N×M→N+M reduction + 19 PASS 사이클 46
v0.2.0-phase2  annotated tag (cycle 54) — Phase 2 마무리 정식 release
```

---

### 8.48 사용자 비판 "서브에이전트 적극 활용" 회수 — workflow ③ serial chain 완성 (사이클 49 → 50 → 51 → 52)

**사용자 비판 회수**:

- 사용자 directive — "서브에이전트 적극적으로 활용해서 작업 하는거 맞아?"
- 인정 — cycle 47/48/50 = main session 직접 작업 / cycle 49 = reviewer-agent 1회만 호출 / qa-agent + observability-agent 누락
- 회수 = workflow ③ 직렬 chain 의 의무 spawn — reviewer (cycle 49) → qa (cycle 51) → observability (cycle 52) 완전 chain

**3 agent serial chain 산출**:

| cycle | agent | 판정 | 산출 |
|---|---|---|---|
| 49 | reviewer-agent | CONDITIONAL PASS | P0 차단 2 (BPE 13 + pronoun 5 of 5 crypto file) + P1 권장 3 + P2 향상 4 |
| 51 | qa-agent | CONDITIONAL PASS | P0 차단 3 — decrypt_backup version enforcement gap + BPE 11 잔존 + pronoun 9 잔존 (정정 범위 밖) |
| 52 | observability-agent | **PASS** | PBKDF2 600K iter = 94.5ms 평균 (OWASP < 1000ms 의 10.5x margin) + pytest 3.03s + import smoke 27.5ms + env var 7/7 baseline 정합 + cipher suite OWASP 2023 정합 |

**cycle 52 정정 의 차단 사유 3종 회수**:

- BPE 12건 정정 — `app/ui/{signup,login}_dialog.py` + `app/net/auth_client.py` + `tests/app/crypto/{test_double_ratchet,test_x3dh,test_decrypt_ooo}.py` + `tests/integration/{test_e2ee_alice_bob,test_aiortc_loopback}.py` (qa report 11 + 추가 1 detect = 12)
- self-pronoun 9건 정정 — `app/net/signaling_client.py` (3건) + `app/core/app_state.py` (4건) + `tests/app/crypto/test_session.py` (2건) — self-pronoun → `self` + 3rd-pronoun → `peer` 일괄
- decrypt_backup version enforcement — `app/backup/encrypted_backup.py:241~263` 의 `if bundle.version != _BACKUP_VERSION: raise ValueError(...)` + test_v1_bundle_rejected_by_decrypt 신규 PASS (v1 spoof bundle 의 의도 정합 차단)

**전수 검증 결과**:

- BPE U+CE21 단독 전체 (app/ + tests/ + docs/) = 0건
- self-pronoun (self / 3rd person 패턴) 전체 = 0건
- pytest 483 passed (482 + 1 신규) + 9 deselected
- drift 0건 14 연속 사이클 37~52

**workflow ③ 검증·관측 직렬 chain 완성 판정**:

- reviewer ✅ + qa ✅ + observability ✅ = Phase 2 마무리 게이트 PASS 정식 도달
- 다음 권장 = release-agent (cycle 53) — 머지 게이트 3종 (reviewer + qa + observability) 통과 검증 후 PR 진입
- 또는 designer chiptune (사용자 직접 의무) + 별개 cycle

**메타 가드레일 갱신 의무 (사용자 비판 영구화)**:

- memory `feedback_workflow_strict_doc_first.md` + `feedback_workflow_preferences.md` 정합 강화
- 매 cycle 자동 chain 의무 — code commit 직후 reviewer → qa → observability 의 의무 spawn (단순 hotfix 의 별개 cycle 분리 가능)
- 1회 비판 = 가드레일 메타 의 즉시 반영 (memory `feedback_repeat_criticism_permanent_record.md` 의 2회 회 의 사전 차단)

**핵심 commit 누적 (사이클 49~52)**:

```
(cycle 52 정정 commit — 본 §8.48 신설 직후 push 예정)
f082736 fix(backup,ui): cycle 50 PBKDF2 stretching v2 + SPDX header 정정
a2c157e fix(crypto): cycle 49 reviewer-agent P0 정정 — BPE 13 + pronoun 5
4b96658 feat(backup): Phase 2 encrypted backup / restore + 22 PASS 사이클 48
9e2dd3c feat(notifications): Phase 2 push 알림 skeleton 4 platform + 31 PASS 사이클 47
05041c0 feat(crypto): Phase 2 Sender Keys 그룹 N×M→N+M reduction + 19 PASS 사이클 46
```

---

### 8.47 Phase 2 마무리 reviewer-agent CONDITIONAL PASS → P0 정정 cycle 완료 (사이클 49)

**reviewer-agent cycle 49 산출 — CONDITIONAL PASS**:

- 14 검증 항목 — PASS 11 + N/A 1 + CONDITIONAL 1 + FAIL 2
- P0 차단 2건 (Phase 2 마무리 게이트 의무):
  - 금지패턴-BPE — U+CE21 단독 13건 (5 file — e2ee.py + double_ratchet.py + session.py + skipped_keys.py + x3dh.py)
  - 금지패턴-PRONOUN — 본"인" 5건 (session.py)
- P1 권장 3건 — UI → net direct import 4건 + PBKDF2 stretching 부재 + PostToolUse hook 사후 정정 cycle 다발
- P2 향상 4건 — SPDX header (chat_view + main_window) + session.py docstring 가독성 + backup.py 별개 cycle 명문 + Specification Phase 2 task # 매핑

**P0 정정 cycle 49 완료**:

- 5 file 의 13 BPE 정정 — U+CE21 의존명사 → `단` 패턴 일괄 (Alice / Bob / 수신 / 송신 / caller / recipient 단)
- session.py 5 self-pronoun 정정 — `\_\_X25519` → `self X25519` (3건 docstring) + `\_\_keypair` → `self keypair` (2건 step)
- 검증 PASS — `grep` 의 U+CE21 단독 = 0건 + self-pronoun 단독 = 0건 + pytest 480 회귀 PASS
- PostToolUse hook 차단 패턴 8 cycle 동안 강제 발화 — 사이클 47 (BPE 1건) + 48 (의 3회 1건) + 49 (BPE 13건 + pronoun 5건) detect 후 즉시 정정 chain

**Phase 2 마무리 게이트 PASS 판정**:

- reviewer-agent CONDITIONAL PASS 의 P0 차단 2종 = 정정 완료
- P1 + P2 = handoff backlog 등재 (hotfix 또는 별개 cycle)
- Phase 2 핵심 Signal Protocol chain (사이클 27~48) = 287 케이스 + 480 pytest 의 안정 완성
- 다음 = reviewer-agent 재호출 사이클 50 (P0 정정 검증 후 PASS 정식 GO 의무) 또는 사용자 directive 의 별개 task 진입

**Phase 2 누계 모듈 16종** (사이클 27~48 + 49 정정):

| 모듈 | 사이클 | PASS |
|---|---|---|
| `app/crypto/e2ee.py` | 27 | 24 |
| `app/crypto/double_ratchet.py` | 28 | 16 |
| `app/crypto/session.py` | 29~32 | 20 |
| integration | 32 | 4 |
| `app/crypto/skipped_keys.py` | 33 | 14 |
| decrypt_ooo | 34 | 6 |
| `app/crypto/x3dh.py` | 37 | 11 |
| `app/ui/sound_player.py` + assets/sounds/signature.wav | 38 | 19 |
| `app/ui/chat_view.py` SoundPlayer | 39 | 9 |
| `app/ui/settings_dialog.py` | 40 | 28 |
| `app/ui/main_window.py` wire | 41 | (회귀 통과) |
| `app/crypto/device_registry.py` | 42 | 26 |
| `server/api/devices_handlers.py` 외 3건 | 43 | 22 |
| `app/crypto/fan_out.py` | 44 | 16 |
| `app/crypto/sender_keys.py` | 46 | 19 |
| `app/notifications/push.py` | 47 | 31 |
| `app/backup/encrypted_backup.py` | 48 | 22 |
| **총 누계** | **사이클 27~48** | **287** |

**P1 backlog 등재 (hotfix)**:

1. UI → net 의 직접 import 4건 — `app/ui/login_dialog.py:21` + `password_reset_dialog.py:22` + `main_window.py:50` + `signup_dialog.py:30` 의 `from app.net.auth_client import AuthClient` → Service / ViewModel layer 신설 의 별개 cycle
2. PBKDF2 stretching 부재 — `app/backup/encrypted_backup.py:123` 의 HKDF-SHA256 직접 derive → 출시 직전 brute-force 방어 의무 (별개 cycle)
3. PostToolUse hook 의 사후 정정 패턴 검증 — 사이클 27~37 stale 회수 후 사이클 38~ 시점 의 사전 차단 의 의무 효과 검증 (영구 0건 trend monitor)

**P2 backlog 등재**:

1. SPDX header 추가 — `app/ui/chat_view.py` + `app/ui/main_window.py` 의 사이클 39 / 41 편집 시점 의 부재 (M1 의 부수 의무)
2. session.py docstring 의 self / peer 의 용어 통일 (사이클 49 정정 결과 의 일관성 향상)
3. backup.py 의 별개 cycle 위임 명문 — PBKDF2 + per-entry encrypt + cloud upload + restore conflict 4종 의 SCOPE 라인 의 추가 의무
4. Specification.md Phase 2 row 의 task # 매핑 정합 — 사이클 27~48 의 16 module 의 16 task # 의 명문 의무

**핵심 commit 누적 (사이클 46~49)**:

```
(cycle 49 P0 정정 commit — 본 §8.47 신설 직후 push 예정)
4b96658 feat(backup): Phase 2 encrypted backup / restore + 22 PASS 사이클 48
9e2dd3c feat(notifications): Phase 2 push 알림 skeleton 4 platform + 31 PASS 사이클 47
05041c0 feat(crypto): Phase 2 Sender Keys 그룹 N×M→N+M reduction + 19 PASS 사이클 46
772a299 docs(handoff): §8.46 사이클 46 telegram polling halt 진단 정정
68f58ce docs(handoff): §8.45 사이클 45 telegram routing 차단 진단 추가
```

---

### 8.46 telegram polling halt 진단 정정 (사이클 46 — 인계 직후 신규 session)

**사이클 45 가설 회수**:

- 사이클 45 가설 = `mcp.notification({method: 'notifications/claude/channel'})` 의 client-side handler 미등록 → **가설 회수**
- 신규 검증 (사이클 46) = channel server PID 9107 alive 단 `bot.start()` polling **silently halted** 확정

**진단 절차 + 증거**:

- 본 session = fresh start (`claude --plugin-dir <telegram_plugin>` PID 9081, `--resume` 미사용) — 사이클 45 의 권장 옵션 A 정합
- 채널 server PID chain 9081 → 9103 (bun wrapper) → 9107 (bun server.ts) 정상 spawn
- 송신 outbound PASS — MCP reply tool message_id 33 + 37 + 39 + Bot API direct PASS
- 사용자 텔레그램 메시지 "PING-9107" 송신 (msg_id 38) — channel server consume 미수행
- 외부 getUpdates 직접 호출 결과 = PING-9107 본문 + 충돌 (409 Conflict) 부재 = **server 9107 의 long-poll 정지 상태 확정**
- pending_update_count = 1 5초 stuck (server consumer 부재)
- server.ts L988-992 의 코멘트 = "a single ETIMEDOUT/ECONNRESET/DNS failure rejected bot.start(), catch returned, polling stopped permanently while the process stayed alive (MCP stdin keeps it running). Outbound tools kept working but the bot was deaf to inbound messages until a full restart." → **본 증상 직접 정합**
- 단 v0.0.6 server.ts L993-1032 = retry loop with backoff — 본 패치 적용본 (정합)
- 정확 원인 = startup 시점 409 conflict 8회 누계 후 `if (is409 && attempt >= 8) return` (L1017-1022) 의 영구 정지 trigger 의심 (직전 session lingering process + 본 session race)

**본 session 영향**:

- outbound (reply / react / edit_message / download_attachment) = 정상
- inbound `<channel source="telegram">` tag = 본 session 도달 0건 (사용자 CLI 직접 입력 의무)
- M7 텔레그램 보고 = outbound 직접 경로만 사용 (caveman ultra 5줄 이하 본문 유지)

**회복 의무 (다음 session entry)**:

```bash
# (A) 권장 — claude CLI 재기동 + telegram plugin 자동 spawn (current process tree 전체 종료 + fresh)
exit                                                                                 # 현 session 종료
cd /Users/oneticket_toonation/Documents/vscode_work/p2p_msg
./tools/claude-telegram.sh                                                           # fresh new conversation (handoff §8.45 의 권장 옵션 A 정합)

# (B) 본 session 의 plugin 만 fresh start (위험 — wrapper exit 시 MCP plugin disconnect)
kill 9107 9103                                                                       # bun server + wrapper
# MCP plugin 자동 respawn 미보장 — outbound tool 도 disconnect 가능
```

**회복 검증 의무 (다음 session)**:

1. `ps aux | grep "bun.*server.ts"` 의 새 PID 확인 (현 9107 != 새 PID)
2. server stderr log 의 `telegram channel: polling as @tootalkDev_bot` line 등장 확인
3. 사용자 텔레그램 메시지 1건 송신 + 본 session 의 `<channel source="telegram">` inbound tag 즉시 도달 확인
4. `curl getWebhookInfo` 의 pending_update_count 의 0 회복 + 사용자 송신 직후 1 → 0 의 즉시 consume 확인
5. reply tool 의 송신 (양방향 완전 검증)

**plugin 0.0.6 bug report 의무**:

- 본 증상 = startup race 의 polling 영구 정지 (server.ts L1017-1022 의 8x 409 의 retry 포기 + 본 process MCP stdin 유지 의 영구 deaf 패턴)
- 권장 fix = 8x 409 후 `process.exit(1)` 로 wrapper + claude CLI 의 disconnect 명시 (영구 deaf 회피)
- GitHub issue trigger candidate — claude-plugins-official/external_plugins/telegram

**핵심 commit 누적** (사이클 46):

```
68f58ce docs(handoff): §8.45 사이클 45 telegram routing 차단 진단 추가 (이전 cycle)
(본 cycle entry — handoff §8.46 polling halt 진단 정정)
```

**다음 session 진입 — 단순 1 명령** (사이클 45 의 옵션 A 재확인):

```bash
exit
cd /Users/oneticket_toonation/Documents/vscode_work/p2p_msg
./tools/claude-telegram.sh
```

→ `exec claude --plugin-dir <telegram_plugin_path>` = telegram plugin 강제 load + channel server **새 PID 의 fresh spawn** + 즉시 polling start + 양방향 routing 활성. 사이클 45 의 `--resume` 의 `<channel>` tag 차단 회귀 회피.

---

### 8.45 Phase 2 multi-device chain 3 cycle + X3DH fan-out + 평가 staleness 회수 + telegram bot 재연결 미완료 (사이클 42~44 + post-44 telegram task)

**진행 완료**:

- 사이클 42 — `app/crypto/device_registry.py` 신설 (DeviceIdentity frozen dataclass + DeviceRegistry + 6 wire format 함수 base64+JSON) + 26 PASS 7 TestClass
- 사이클 43 — server-side counterpart 완성 (4 신규 파일):
  - `server/db/migrations/0002_devices.sql` (10 컬럼 5요소 COMMENT — id PK + device_id UNIQUE + user_id FK CASCADE + 3 X25519 BLOB + 3 timestamp + status ENUM)
  - `server/db/repositories/devices.py` — DeviceRow + 5 async (insert/get_by_user/get_by_device_id/revoke soft-delete/update_last_seen)
  - `server/api/devices_handlers.py` — REST 3 endpoint (POST /api/devices base64 32-byte 검증 + 1062 → 409 + GET include_revoked option + DELETE soft-delete user_id 검증)
  - `server/main.py` register_devices_routes 등록 + `ARCHITECTURE.md §6` row + HTML mirror 동기
  - 22 PASS 6 TestClass
- 사이클 44 — `app/crypto/fan_out.py` (FanOutEnvelope + FanOutBatch + encrypt_fan_out per-device 실패 격리 + rotate_session immutable dict 갱신 + collect_failures) + 16 PASS 5 TestClass
- **multi-device chain 3 cycle 완성** = client skeleton 42 + server endpoint 43 + fan-out 44 = Signal Protocol N-device 종단 흐름 정합
- 전체 pytest = **408 passed**. Phase 2 누계 = **215 케이스** (e2ee 24 + double_ratchet 16 + session 20 + integration 4 + skipped_keys 14 + decrypt_ooo 6 + x3dh 11 + sound 19 + chat_view_sound 9 + settings_dialog 28 + device_registry 26 + devices_handlers 22 + fan_out 16)

**평가 staleness 회수** (사이클 44):

- 사용자 비판 — "10점 만점 항목들에 왜 5점 만점 항목이 있어?" 직접 회수
- vibe-coding §1 종합 표 의 2 row stale (보안 사고 5/5 + 자율 reasonable call 5/5) + §3.3 (2.5/5) + §6 비교 anchor 표 전체 5점 만점 → 10점 만점 ×2 변환
- 영구 메모리 2건 신설:
  - `feedback_assessment_row_completeness.md` (#27) — grep 검증 명령 명문화
  - `feedback_assessment_full_rewrite.md` (#28) — **사용자 강화 directive "평가문서는 부분갱신이 아니라 매번 전체 갱신"** = 매 cycle 4 영역 + 2 HTML mirror 전체 rewrite 의무. 부분 갱신/prepend/append 패턴 절대 금지

**자율 chain 안정** — drift 0건 8 연속 사이클 37~44 (단 평가 staleness 1건 별도 — row_completeness + full_rewrite 의 영구 차단)

**snapshot 갱신**:

- productization 8.95 → 9.05 → 9.1 → 9.15 → 9.2 (사이클 41~44 의 누적)
- vibe-coding 9.66 → 9.68 → 9.7 → 9.72 → 9.74 (사이클 41~44)

**🔴 telegram bot 재연결 미완료** (사이클 44 후반 task — **다음 session 진입 의무**):

- 사용자 directive — "텔레그램 bot 새로 만들었으니 재연결"
- 새 bot = `@tootalkDev_bot` (id 8853758309, first_name "투톡개발용")
- 새 token = `8853758309:AAHLCc5v9r9yVs2D5__VTc4waFHqZRBL2JQ` (Bot API getMe + sendMessage 검증 PASS)
- `.env.telegram` 갱신 완료 (송신 의 HTTP API 직접 경로 정상)
- `~/.claude/channels/telegram/.env` 의 channel server token 갱신 완료
- `~/.claude/channels/telegram/approved/201073550` 신설 완료 (chat_id = 사용자 의 user ID = `@oneticket99`)
- access.json — dmPolicy=allowlist + allowFrom=[201073550] 유지
- **차단** — channel server (구 PID 55077 bun server.ts) kill 후 자동 respawn 미동작 + MCP plugin_telegram disconnected (reply / react / edit_message / download_attachment 4 tool unavailable)
- Telegram API 의 inbound 5 메시지 queue 잔존 (pending_update_count=5 — getUpdates 직접 확인 결과: "하이" / "송수신 확인해" / "/start" / "hi" / "test")
- **원인** = polling consumer (channel server) 부재 = routing 차단

**다음 session 진입 — 단순 1 명령**:

```bash
cd /Users/oneticket_toonation/Documents/vscode_work/p2p_msg
./tools/claude-telegram.sh --resume    # 직전 conversation 이어 받기
# 또는
./tools/claude-telegram.sh             # 신규 session
```

→ `exec claude --plugin-dir <telegram_plugin_path>` = telegram plugin 강제 load + channel server 자동 spawn + 새 token 의 fresh polling + 큐 5 메시지 consume + 양방향 routing 활성

**사이클 45 진단 추가 결과** (2026-05-20 후반 — `--resume` 의 routing 차단 발견):

- **`./tools/claude-telegram.sh --resume` 실행 결과** (사이클 45 신규 session):
  - channel server PID 95860 (`bun server.ts`) 정상 spawn — parent chain 95860 → 95851 (`bun run wrapper`) → 95829 (`claude --plugin-dir <telegram_plugin> --resume`)
  - 송신 (out) 정상 — MCP reply tool message_id=21 PASS + HTTP API curl PASS
  - getUpdates / getWebhookInfo — pending_update_count=0 (server polling 정상 + 큐 즉시 consume)
  - **수신 (in) 차단** — 사용자 의 새 메시지 ("hi" 등) 송신 단 본 session 의 `<channel source="telegram" ...>` inbound tag 도달 차단
- **원인 확정**:
  - server.ts L957-959 의 inbound dispatch = `mcp.notification({ method: 'notifications/claude/channel', params: {...} })` (MCP custom notification, request 아님)
  - Claude CLI session 의 client-side handler registration 의무 — handler 등록 미실행 시 notification silently drop
  - `--resume` 옵션 의 startup race condition 의심 — direct conversation restore 시점 의 plugin channel subscription register 가 missed 가능
- **`approved/<senderId>` 의무 분석**:
  - 직전 cycle 의 `echo "201073550" > approved/201073550` 신설 후 channel server polling 의 consume + delete (3초 후 자동 삭제 검증)
  - = 첫 pairing notification 1회용 file (skill spec step 7 의 "polls approved dir and sends you're in" 정합) — routing 의 영구 활성 trigger 아님
  - access control 영구 활성 = access.json 의 allowFrom 만 (정상)

**다음 session 진입 의무 — 수정된 권장**:

```bash
# (A) 권장 — fresh start 의 새 conversation
cd /Users/oneticket_toonation/Documents/vscode_work/p2p_msg && ./tools/claude-telegram.sh

# (B) 비권장 — --resume 시 channel subscription register 차단 가능 (사이클 45 검증 결과)
cd /Users/oneticket_toonation/Documents/vscode_work/p2p_msg && ./tools/claude-telegram.sh --resume
```

→ 사이클 45 의 `--resume` 결과 = 송신 PASS + 수신 차단 발견 → fresh start (옵션 생략) 권장.

**다음 session 검증 의무**:

1. server 의 새 process spawn 확인 (`ps aux | grep "bun.*server.ts"`)
2. 사용자 telegram 의 새 메시지 1건 발송 → session 의 `<channel source="telegram" ...>` incoming tag 도달 검증 (핵심)
3. session 의 reply tool 의 송신 시도 (양방향 확인)
4. 만일 fresh start (옵션 생략) 의 routing 도 차단 시 = telegram plugin 0.0.6 bug 의심 → `claude plugin update telegram` 또는 GitHub issue 의무
5. 회귀 검증 — 사이클 44 commit `89e608e` + handoff commit `1f9a80e` HEAD 정합 + pytest 408 전수 PASS

**잔여 Phase 2 task** (다음 session 의 자율 GO 가능):

- sender keys (그룹 chat N×M reduction)
- push 알림 skeleton (FCM/APNS or pull fallback)
- 백업/복원
- designer 최종 chiptune asset (signature sound placeholder 교체)
- reviewer-agent → handoff doc 추가

**핵심 commit 누적** (사이클 37~45):

```
1f9a80e docs(handoff): §8.44 + §8.45 사이클 38~44 누계 + telegram 재연결 미완료 (사이클 45)
89e608e feat(crypto): Phase 2 X3DH session fan-out + 16 PASS + 평가 10점 회수 사이클 44
8a0095c fix(docs): hook_doc_consistency drift 회수 — devices.py path 정합
a6316f3 feat(server): Phase 2 multi-device server endpoint + 22 PASS 사이클 43
d952b0d feat(crypto): Phase 2 multi-device sync skeleton + 26 PASS 사이클 42
87abaa3 feat(ui): Phase 2 MainWindow SoundPlayer + SettingsDialog wire 사이클 41
93ada9e feat(ui): Phase 2 SettingsDialog sound section + 28 PASS 사이클 40
034fbf7 feat(ui): Phase 2 ChatView SoundPlayer trigger 연결 + 9 PASS 사이클 39
65ae782 feat(ui): Phase 2 signature sound minimal layer + 19 PASS 사이클 38
1c36075 feat(crypto): Phase 2 X3DH initial key agreement + 11 PASS 사이클 37
```

**영구 메모리 신규 누적** (사이클 38~44):

- `project_signature_sound.md` (사이클 38)
- `feedback_skip_prepush_permanent_approval.md` (사이클 39)
- `feedback_assessment_row_completeness.md` (사이클 44)
- `feedback_assessment_full_rewrite.md` (사이클 44 강화)

### 8.44 Phase 2 signature sound chain 4 cycle 완성 — vertical slice 패턴 명문화 (사이클 38~41)

**vertical slice = 단일 feature 의 layer 분리 패턴 정합**:

- 사이클 38 wrapper layer — `app/ui/sound_player.py` SoundPlayer + Config 3 필드 (sound_enabled / sound_volume / sound_signature_path) + `app/assets/sounds/signature.wav` placeholder (220 ms chime 880→1320 Hz pitch glide + exponential decay) + 19 PASS
- 사이클 39 trigger integration — `app/ui/chat_view.py` 의 `should_play_on_message(is_self, sound_player)` module-level helper + `ChatView.__init__` sound_player Optional inject + add_message peer 수신 trigger + 9 PASS (Mock 주입 logic only — QApplication 부재 환경 정합)
- 사이클 40 control UI — `app/ui/settings_dialog.py` SettingsDialog + SettingsState dataclass + 4 helper (percent_to_volume / volume_to_percent / apply_to_player / build_state_from_player) + 음소거 QCheckBox + 0~100 QSlider + 28 PASS
- 사이클 41 wire — `app/ui/main_window.py` 의 `_sound_player` instance + ChatView inject + 환경설정 메뉴 QAction Ctrl+, + slot

**실 사용 가능 종단 흐름**: Config → MainWindow init → ChatView inject → peer 수신 → play_signature → WAV. 환경설정 메뉴 → SettingsDialog → 음소거/볼륨 → 즉시 반영.

**설계 패턴 강화 — 사이클 38~41 연속 적용**:

- helper 분리 = GUI 부재 환경 unit test 의무 (Mock 주입 logic only)
- Optional inject 패턴 = graceful 폴백 (test 환경 QApplication 부재)
- frozen dataclass + post_init 검증 = 매 신규 dataclass 일관 적용
- minimal scope cycle = 매 cycle 단일 책임 + commit + push + snapshot 동기

### 8.43 Phase 2 Signal Protocol 핵심 완성 + 전수조사 drift 회수 + doc-consistency Stop hook 강제 (사이클 33~36)

- 사이클 33 `app/crypto/skipped_keys.py` (LRU+TTL + MAX_SKIP=1000) + 14 PASS
- 사이클 34 session `_skip_forward_chain_keys` helper + 4 PASS
- 사이클 35 SessionState.skipped_store field + `decrypt_with_session_ooo` (out-of-order delivery + replay 차단) + 6 PASS
- 사이클 36 **사용자 directive 전수조사** — ARCHITECTURE §6 drift 6건 detect → 회수
  - `app/auth/` + `app/db/` 명시 단 부재
  - `app/crypto/` 누락 (Phase 2 신설)
  - `bcrypt` 표기 단 실 PBKDF2
  - `server/api` + `server/db` + `server/mail` + `signaling_persistence` 누락
  - Specification FR-05 "로컬 MariaDB" → "server MariaDB 7 table"
- `tools/hook_doc_consistency.sh` 신설 — Stop hook §6 backtick path 의 실 디렉토리 정합 검사 + 역방향 dir 존재
- 영구 메모리 4건 누적 추가 (#32 freshness + #33 10-point + #34 doc-consistency + #35 signature sound)
- PLANS §3 Phase 2 일정 조기 진입 drift 회수 (2026-07-01 → 2026-05-18 + 1.5개월 단축)
- Structure.md 트리 확장 — app/crypto 4 + server/api/auth/db/mail/signaling_persistence 전수 명시
- 전체 pytest = 277 passed, 9 deselected. Phase 2 누계 84 (e2ee 24 + double_ratchet 16 + session 20 + integration 4 + skipped_keys 14 + decrypt_ooo 6)
- 평가 진동 — productization 8.7 → 8.8 ▲ / vibe-coding 9.65 → 9.55 ▼ (직무유기 4회차 진동 잔존)
- 다음 = X3DH initial key exchange + multi-device + push + signature sound + reviewer-agent → handoff doc

### 8.42 Phase 2 진입 + signaling DB 통합 + E2EE (AES-GCM + X25519 + HKDF + Double Ratchet + Session + Alice/Bob integration) + enforcement layer designer 평가 (사이클 24~32)

- 사이클 24~26 = signaling.py DB 통합 + signaling_persistence helper + Peer dataclass user_id/db_room_id 확장
- 사이클 27 = Phase 2 진입 — `app/crypto/e2ee.py` (AES-256-GCM + X25519 ECDH + HKDF + EncryptedPayload wire format) + 24 PASS
- 사이클 28 = Double Ratchet KDF chain (`app/crypto/double_ratchet.py` + ChainKey + Signal Protocol 0x01/0x02 separator) + 16 PASS + 평가 staleness Stop hook 강제화 (#32 가드레일)
- 사이클 30 = SessionState skeleton (`app/crypto/session.py` + initialize_initiator/responder) + 11 PASS
- 사이클 31 = `advance_dh_ratchet` Signal Protocol 3 step (recv chain + keypair rotate + send chain) + 5 PASS
- 사이클 32 = `encrypt/decrypt_with_session` wrapper + Alice/Bob integration test (`tests/integration/test_e2ee_alice_bob.py`) 4 PASS + **enforcement layer designer 평가 취합** (사용자 능력 차별화 6 영역 명문)
- 전체 pytest 누계 = 253 passed (Phase 2 60 — unit 56 + integration 4)
- 가드레일 30 → 32 (post-write inspection + code-qa-review-gate + timezone-kst + assessment-freshness-trigger + phase2-completion-review-handoff)
- 다음 = skipped message keys + multi-device + push + 백업 → reviewer-agent → handoff doc

### 8.41 사이클 22 perl bulk 실패 → 복원 + post-write hook 강제화 + Phase 1 자율 chain 완성 (사이클 22~23)

- 사용자 directive 누계 자율 GO — security + DB schema + 7 repository + SMTP + 5 auth use case + middleware + REST 5 endpoint + auth_client + UI 4 dialog + PyInstaller spec + build.yml
- 사이클 22 = perl `s/  +/ /g` bulk 정정 의 4-space indent collapse = Python 전수 syntax 손상 + 사용자 직무유기 비판
- 복원 = git restore (사용자 GO) → origin/main 1e28afc HEAD
- post-write hook 강제화 = tools/hook_post_write_inspect.sh 5 검사 + settings.json PostToolUse matcher
- 영구 메모리 4건 (26 → 30) — post-write-inspection + code-qa-review-gate + timezone-kst + db-schema-field-comments
- 재진입 (사이클 23) = main_window 계정 메뉴 — 단계별 Edit + 매 Edit AST 검증
- 5 검증 (AST + import + pytest 197 + doc-lint + BPE 0) 매 cycle 의무
- KST timezone 의무 (History/commit/log/DB 일관)
- build.yml heredoc 우회 신설

### 8.40 Phase 1 코드 진입 GO + 5 test module 누계 149 PASS (사이클 16 신규)

- 사용자 directive "이제부터 코드작업에 진입해" + "남은작업 다 진행해" = task #7 정식 GO + §9.2 후속 자율 GO
- 가드레일 [[feedback-doc-perfection-before-code]] 8 체크리스트 PASS 검증
- 5단계 워크플로우 ② 개발 단계 직접 진입 (main session Edit/Write, `@backend-agent` 부재 정합)
- 신설 5 test module:
  - `tests/app/rtc/test_protocol.py` — 41 케이스 8 TestClass (commit `91af38d`)
  - `tests/app/rtc/test_image_processor.py` — 35 케이스 4 TestClass (Pillow 실 실행)
  - `tests/app/rtc/test_file_receiver_helpers.py` — 29 케이스 4 TestClass (`_safe_filename` 14 path traversal)
  - `tests/app/rtc/test_file_sender_helpers.py` — 15 케이스 2 TestClass (`_sha256_of_file` 7)
  - `tests/app/ui/test_file_progress_widget_humanize.py` — 20 케이스 1 TestClass (`_humanize` 6 단위)
- 전체 pytest = **149 passed, 3 deselected** (integration/e2e)
- venv Python 3.13.13 + PyQt6 + Pillow + aiofiles + pytest 9.0.3 + pytest-asyncio 1.3.0
- qa-agent 사이클 13 미커버 영역 완전 회수
- 잔존 = `tests/integration/` (aiortc 실 통합, av wheel build = ffmpeg 의존 — 사용자 직접) + Windows wine 검증 (Ubuntu + cdrx docker — 사용자 직접) + AC-04-3 100ms 실측 (dogfooding 시점 — 사용자 직접)

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
| 7 | ~~Phase 1 코드 진입 GO~~ | ✅ **완료** (사이클 16) | 사용자 directive "이제부터 코드작업에 진입해" 정식 GO + 가드레일 8 체크리스트 PASS + 5 test module 누계 149 PASS + qa 미커버 영역 완전 회수 |
| 8 | ~~Agent #16 산출물 5단계 워크플로우 ③ 4단 chain~~ | ✅ **완전 자동 완성** (사이클 11~15) | reviewer ✅ (11~13) + qa ✅ CONDITIONAL (13) + release ✅ 정식 GO (15) + observability ✅ CONDITIONAL PASS (15) + `docs/policies/observability-baseline.md` 정본 신설. Phase 1 dogfooding 진입 readiness 완성 |
| 9 | Toonation 통합 시나리오 검토 (옵션 B) | 🔴 사용자 직접 | adoption-roadmap.md §4.2 권장 ★★★★☆ |
| 10 | Phase 1 dogfooding 진입 — RTT/throughput/RSS/disk leak 최초 측정 | 🟡 사용자 직접 GO 대기 | observability-baseline.md §5 의 6 단계 회귀 검증 절차 정합. 데모 시그널링 서버 배포 + 1:1 채팅 round-trip 시점. Phase 1 MVP DoD #1 (RTT &lt; 500ms) + TD-4 (aiortc 약 5Mbps throughput) 최초 측정 의무 |

### 9.1 잔존 task 진입 가능 (가드레일 통과 후)

- #16 파일전송 양방향 progress 모듈 (Agent #16 산출물 검토 후)
- #17 데모 시그널링 서버 배포 (114.207.112.73 systemd · docker)
- #18 PyInstaller spec + 빌드 스크립트
- #19 build.yml 매트릭스 (M5 단계)
- #20 README 빌드/실행 안내 갱신
- E2EE (libsignal-protocol wrapping) — Phase 2 진입

### 9.2 사이클 15·16 후속 별도 task

#### 9.2.1 완료 (사이클 16)

- ✅ `tests/app/rtc/` unit test 작성 — `protocol.py` (41) + `image_processor.py` (35 — Pillow 의존 함수 실 실행) + `_safe_filename` 14 path traversal + `_humanize` 20 + `_sha256_of_file` 7 + `_env_int` 17 (file_sender + file_receiver 각 모듈) — 누계 99 PASS 신규
- ✅ Pillow 의존 함수 실 실행 — RGBA→RGB + palette→RGB + 비율 유지 + base64 round-trip + 환경변수 override
- ✅ qa-agent 사이클 13 정적 검증 케이스 의 실 pytest 회수

#### 9.2.2 잔존 (사용자 직접 의무 / 별도 cycle)

- `tests/integration/` — aiortc 실 통합 + DataChannel 점진 send + ACK round-trip + 무결성 SHA-256 e2e (av wheel build = ffmpeg 의존, macOS `brew install ffmpeg` 의무)
- Windows 환경 검증 — wine cross-compile build (Ubuntu + cdrx docker — self-hosted runner 또는 사용자 직접 환경)
- AC-04-3 100ms 실측 — `FILE_BACKPRESSURE_POLL_MS` 실 측정 (현 50ms default — dogfooding 시점 측정)
- `app/observability/` 디렉토리 신설 (Phase 2 진입 전) — `logging_adapter.py` (logger prefix 일관 강제 + level 동적 갱신)
- `FILE_RECV_TIMEOUT_S` 도입 결정 (Phase 2 reliability 강화)
- `.partial` 임시 파일 자동 cleanup hook (Phase 2 storage 정책)
- pytest-qt 환경 신설 (QWidget repaint / signal 통합 의 별도 cycle)

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

마지막 갱신: 2026-05-19 05:00 KST — 사이클 36 (Phase 2 Signal Protocol 핵심 완성 + 전수조사 drift 6건 회수 + doc-consistency Stop hook + Specification FR-05 + Structure 트리 + PLANS Phase 2 일정 회수 + 277 pytest + 가드레일 35, commit `eca906d` HEAD)
이전 갱신: 2026-05-19 03:00 KST — 사이클 32 (`86ac6b1`)
이전 갱신: 2026-05-18 22:00 KST — 사이클 23 (perl bulk 복원 + post-write hook + main_window 계정 메뉴, `a13a1f3`)
이전 갱신: 2026-05-18 02:00 — 사이클 16 (Phase 1 코드 진입 GO + 149 PASS + qa 미커버 회수, `3aa7eed`)
이전 갱신: 2026-05-18 01:00 — 사이클 15 (본 세션 누계 commit 53+ + 사이클 15 의 신규 commit dcbb372 (release P0-1/P0-2 정정) + 후속 commit 일괄 (observability-baseline.md 신설 + snapshot 2 + HTML 2 + handoff §8.38/§8.39 + History.md prepend + README §11 prepend) 반영, 가드레일 22, 텔레그램 송신 N건, HTML 6, pytest 인프라, 정책 본문 4 (observability-baseline.md 신규), auth 정책 + 차별화 명문화, CI 3종 GREEN + macOS arm64 runner 활성 + wine cross-compile + fork PR strict + SMTP 자체 설치 정책 + GPLv3 라이선스 확정 + visibility 전환 정책 + enforcement layer 활성 + drift 회수 누계 9 cycle (사이클 15 의 baseline drift 3건 회수 추가) + **5단계 워크플로우 ③ 4단 chain 완전 자동 완성 — reviewer ✅ (11~13) + qa ✅ CONDITIONAL (13) + release ✅ 정식 GO (15) + observability ✅ CONDITIONAL PASS (15)** 신규, snapshot 사이클 15 — productization 4.05 + vibe-coding 4.90)
