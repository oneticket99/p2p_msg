---
title: "TooTalk 작업 체크리스트 (CheckList)"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# CheckList.md — TooTalk(p2p_msg) 작업 체크리스트

> 본 문서는 **항목 추적·매핑·진행률 관리** 의 정본이다.
> 정본 정합: [CLAUDE_HARNESS_IMPORTANT.md §D](CLAUDE_HARNESS_IMPORTANT.md) —
> "checklist-agent · CheckList.md · 항목 추적·매핑·진행률" 담당 정의.
> 저장소 맵: [AGENTS.md](AGENTS.md) · 정본 워크플로우: [§B](CLAUDE_HARNESS_IMPORTANT.md).

---

## 1. 문서 목적

본 문서는 TooTalk(코드명 `p2p_msg`) Phase 1 MVP 의 **무엇이 끝났고 무엇이 남았는가** 를
체크박스 단위로 추적하는 정본이다. 정본 §D 표 — "checklist-agent ·
CheckList.md · 항목 추적·매핑·진행률" — 그대로 본 문서의 역할 정의다.

본 문서가 담당하는 범위.

- **FR / NFR 체크리스트** — [Specification.md](Specification.md) §3·§4 와 1:1 매핑
- **마일스톤 진행률** — [실행계획](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md) §4 와 정합
- **정책 문서 9 / 운영 문서 8 작성 상태** — 정본 §K 루트 18 동결 정합
- **`.claude/agents/` 7 에이전트 사양 등재 상태** — 정본 §C HARNESS 7역할 정합
- **CI 게이트 5 통과 상태** — 정본 §L 3 워크플로우 정합
- **외부 결정 대기 항목 (TBD)** — [Specification.md §12](Specification.md) 정합

담당하지 않는 범위 (위임).

- 요구사항 명세 본문 → [Specification.md](Specification.md)
- 파일 트리 / ERD → [Structure.md](Structure.md)
- 실행 일정·결정 로그 → [docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)
- 변경 이력 prepend → `History.md` (운영 8 작성 예정)

---

## 2. 진행률 요약 (2026-05-20 23:20 KST cycle 169.82 sign-off — 누계 commit 1000+ 반영)

### 2.1 Phase 1 DoD sign-off (cycle 169.82)

| Phase | 상태 | sign-off marker |
|---|---|---|
| Phase 1 MVP — 기본 8 (text + image + file + room + signaling + auth + signature sound + telegram desktop align) | **PASS** | cycle 37~169.82 누계 + 1418 pytest + drift 0건 143 연속 |
| Phase 2 — 친구간 1:1 원격 데스크탑 제어 entry | **PARTIAL** | cycle 148 좌표 보정 coord_transform + cycle 119 prereq doc |
| Phase 3 — bot framework (BotFather + Bot API + webhook + inline + payment) | **DONE** | cycle 119~131 + Anthropic + OpenAI + RAG + jailbreak 17 + 3 layer fallback |
| Phase 4 — production infra (docker compose 6 + nginx TLS + SMTP postfix + certbot + JSON log) | **DONE** | cycle 100~129 + v0.4.0-phase4-infra release |
| Phase 5 — Item 5 (i18n + emoji pack share + bot 마무리 + 원격 제어 + mobile) | **ACTIVE** | cycle 119~169.82 — i18n actual binding + bot 고객센터 봇 + 방송 도우미 봇 진입 |
| CI 3종 GREEN (ci + docs-lint + doc-gardener) | **GREEN** | cycle 169.81 docs-lint PASS 67 file + ci d55fa10 in_progress |
| reviewer + qa audit chain — HIGH 2 + MEDIUM 4 + LOW 3 finding 전수 회수 | **PASS** | cycle 169.78~80 chain |
| folder test coverage (repository 8 + handlers 7 + client 6 + signaling 12 + call_env 6 = 70 PASS) | **PASS** | cycle 169.80~82 |
| WebRTC TURN env override + coturn install script (deploy/scripts/coturn_install.sh) | **READY** | cycle 169.81 — local script + 사용자 manual SSH install path |
| Portable Harness 최신화 (거버넌스 + hook + guardrail + trigger + 코드 분리 + skill 분리) | **DONE** | cycle 169.559~562 — `docs/PORTABLE_HARNESS.md` + `Structure.md` + `$portable-harness` skill 정합 갱신 |
| 사용자 manual visual ack (10 항목) | **PENDING** | A 1~10 재 빌드 후 사용자 직접 verify |

> Phase 1 MVP DoD 정합 — 기본 8 + telegram desktop align + folder backend full stack + reviewer/qa audit PASS + CI 3종 GREEN + 1418 pytest + drift 0건 143 연속 — **Phase 1 sign-off**.
> 잔존 — 사용자 manual visual ack 10 항목 + coturn install SSH (사용자 manual) + Phase 2/5 진행.

### 2.2 직전 cycle marker (2026-05-17 시점 누적 표 — 영구 참고)

| 영역                  | 완료 / 전체     | 비고                                                              |
|-----------------------|-----------------|-------------------------------------------------------------------|
| 정책 문서 9           | 9 / 9           | AGENTS · ARCHITECTURE · DESIGN(§11 UI 시스템 추가) · FRONTEND(§14 wireframe + 색상 swatch) · PLANS · PRODUCT_SENSE · QUALITY_SCORE · RELIABILITY · SECURITY 모두 작성 완료 |
| 운영 문서 8           | 8 / 8           | Specification · Structure · CheckList(본 문서) · History · README · EXTENSION_GUIDE · MIGRATION_MARIADB · CLAUDE 모두 작성 완료 |
| 정책 본문 (docs/policies/) 3 | 3 / 3           | doc-gardening · adoption-roadmap · execution-harness 모두 active (깨진 링크 12 → 0) |
| 평가 snapshot 2       | 2 / 2           | productization (2.6/5) · vibe-coding (4.5/5) — 매 task 종료 시 전체 rewrite (CLAUDE.md §10-7) |
| HTML 동시 정리 6       | 6 / 6           | Structure · ARCHITECTURE · FRONTEND · DESIGN · productization · vibe-coding (CLAUDE.md §10-6) |
| `.claude/agents/` 7    | 7 / 7           | doc-gardener · history · observability · planning · qa · release · reviewer 모두 등재 |
| `.github/` 인프라     | 4 / 4           | ci.yml · docs-lint.yml · doc-gardener.yml · pull_request_template.md |
| pytest 인프라         | 1 / 1           | pyproject.toml + requirements-dev.txt + tests/{app,server,e2e} + conftest + 첫 test 12개 |
| 영구 메모리 가드레일 | 14 / 14         | 신규 4 (no-self-other-pronoun + doc-perfection-before-code + design-interactive-html + phase1-completion-priority) |
| 코드 task #11~#22      | 0 / 12          | M1 #11 done · #12 in_progress · #13 in_progress (실행계획 §5 정합)         |
| FR P0/P1              | 0 / 13          | FR-01 ~ FR-10 + FR-11/12/13 (회원가입/로그인/아이디·비번 찾기, 사용자 directive 2026-05-17) — 코드 진입 전 |
| NFR                   | 0 / 7           | NFR-01 ~ NFR-07 — 측정 인프라 부분 구축 (pytest + Playwright 스켈레톤) |
| 마일스톤              | M1 in_progress  | M2 ~ M5 pending (실행계획 §4 정합)                                 |
| CI 워크플로우         | 3 / 4 (GREEN)   | ci (8 job GREEN — Windows matrix 영구 비활성 → wine 대체) · docs-lint · doc-gardener 모두 macOS-arm64 GREEN 도달 (2026-05-17 15:40). build.yml = M5 단계 (Phase 1 후반 — macOS self-hosted + Ubuntu wine cross-compile 듀얼 job) |
| self-hosted runner    | 1 / 1 (충족)    | macOS arm64 등록 OK (id=2 online, launchd PID 62533, workflow 픽업 검증). Windows self-hosted runner 의 의무 = **영구 회수** (사용자 directive 2026-05-17 — wine cross-compile 대체, [[project-windows-build-via-wine]]) |
| Windows 빌드 패턴     | wine docker     | GitHub-hosted Ubuntu (`ubuntu-latest`) + docker `cdrx/pyinstaller-windows` 의 wine cross-compile. Phase 1 후반 build.yml 신설 시점 동작 검증 |
| fork PR 승인 정책     | strict 적용     | `all_external_contributors` 적용 OK (2026-05-17 cycle, gh API 자동) — public repo + self-hosted runner 의 보안 hardening |
| SMTP 서버 (OTP 발신)  | 정책 + 절차 OK  | 데모 서버 (`114.207.112.73`) postfix 자체 설치 (사용자 directive 2026-05-17 — `docs/references/smtp-setup.md` 13 섹션 + 영구 메모리 `project_smtp_demo_server.md`). 실제 설치 = 사용자 직접 SSH (Phase 1 후반) |
| **라이선스**          | **GPLv3 확정**  | LICENSE 저장소 루트 (GNU 표준 본문 674 lines, 사용자 directive 2026-05-17). PyQt6 GPLv3 정합 + SPDX header 의무 (Phase 1 코드 진입 시). 영구 메모리 [[project-license-gpl]] |
| **GitHub visibility** | public (현재)   | Phase 완료 시 private 전환 가능성 (사용자 directive 2026-05-17). self-hosted runner 의 의무 quota 회피 정합. 영구 메모리 [[project-visibility-transition]] |
| **enforcement layer sketch** | 미활성 (sketch) | `.claude/settings.json.disabled` 의 PreToolUse Edit/Write (BPE 차단) + Stop (텔레그램 자동 송신) 듀얼. `tools/hook_check_bpe_token_input.sh` + `tools/hook_telegram_report_stop.sh` (executable + self-test PASS). 다음 BPE 위반/텔레그램 누락 발견 시 `mv .disabled → settings.json` 즉시 활성 — [[feedback-bpe-script-trigger-warning]] + [[feedback-telegram-report-script-trigger-warning]] |
| **영구 메모리 가드레일** | 22 / 22 | 직전 14 → 22 (신규 8 — windows-build-via-wine + smtp-demo-server + license-gpl + visibility-transition + bpe-script-trigger-warning + telegram-report-script-trigger-warning + + 직전 누계 14 의 4 정합 — phase1-completion-priority + phase2-remote-control-differentiator + auth-email-otp-required + design-interactive-html + doc-perfection-before-code + no-self-other-pronoun) |
| BPE 위생 자동 검사    | 1 / 1           | tools/doc-lint.sh 5 검사 (BPE + 깨진 링크 + frontmatter + 빈 줄 + 1인칭/3인칭) |
| 텔레그램 보고 (M7)    | 강제 활성       | HTTP API 직접 (bot toonation_first_dev_bot + chat 201073550) — 본 세션 송신 누계 13건 |

> 갱신 정책. 본 표는 문서·코드·CI 어느 하나가 PASS / 등재 / 완료 전이될 때 즉시 한 줄
> 갱신한다. 누락 시 `@reviewer-agent` 차단 + `@doc-gardener-agent` 보정 PR.

---

## 3. FR 체크리스트 (Specification §3 정합)

10 개 기능 요구사항의 매핑 정본. FR 행 1건 = task 매핑 1행 + 코드 위치 1+ + 상태.
체크박스 정의: `[ ]` 미착수 / `[~]` 진행 중 / `[x]` 완료.

| 상태 | ID    | 제목                              | 매핑 task                                                                                                       | 코드 위치 (예정)                                                  | 상태 라벨   |
|------|-------|-----------------------------------|-----------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|-------------|
| `[ ]` | FR-01 | 시그널링 서버 연결 + JOIN          | [#14 server/signaling.py](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)                              | [server/signaling.py](server/signaling.py) · [server/room.py](server/room.py) | pending     |
| `[ ]` | FR-02 | DataChannel 텍스트 송수신          | [#17 app/rtc/peer.py · #18 채팅뷰 wiring](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)              | `app/rtc/peer.py` · `app/ui/chat_view.py`                          | pending     |
| `[ ]` | FR-03 | 이미지 송수신 (썸네일 + 원본)      | [#19 transfer.py · #20 썸네일](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)                          | `app/rtc/file_sender.py` · `app/rtc/image_processor.py` · `app/ui/message_bubble.py` | pending     |
| `[ ]` | FR-04 | 파일 송수신 + 양방향 ProgressBar   | [#19 청크 스트림 · #20 ProgressBar](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)                     | `app/rtc/file_sender.py` · `app/rtc/file_receiver.py` · `app/ui/file_progress_widget.py` | pending     |
| `[ ]` | FR-05 | 메시지 영속화 (MariaDB)            | [#16 db_init.py · #18 영구화](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)                           | `app/core/app_state.py` · `tools/db_init.py` (예정)                | pending     |
| `[ ]` | FR-06 | peer 연결 상태 표시                | [#15 main_window.py](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)                                   | `app/ui/status_bar.py` · `app/ui/main_window.py`                    | pending     |
| `[ ]` | FR-07 | 방 입장 / 퇴장                     | [#14 signaling.py · #15 main_window](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)                    | [server/room.py](server/room.py) · `app/ui/main_window.py`         | pending     |
| `[ ]` | FR-08 | PyInstaller 빌드 (mac+win zip)     | [#21 build.py · #22 build.yml](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)                          | `tools/build.py` · `.github/workflows/build.yml` (예정)            | pending     |
| `[ ]` | FR-09 | 첫 실행 onboarding                 | [#15 main_window.py](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)                                   | `app/ui/onboarding_dialog.py` (예정)                                | pending     |
| `[ ]` | FR-10 | 시그널링 단절 자동 재연결          | [#14 signaling reconnect](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)                              | `app/net/signaling_client.py`                                      | pending     |

> 완료 정의 (per FR). (1) [Specification §7 Acceptance Criteria](Specification.md) 의 해당 AC 라인 전부
> PASS, (2) 코드 위치 컬럼의 모든 파일이 실재, (3) `@qa-agent` 회귀 체크리스트 PASS, (4)
> `@reviewer-agent` M1~M7 통과, (5) [Specification.md §8 매핑 테이블](Specification.md) 의
> "코드 위치 (예정)" 컬럼이 실제 트리 노드 링크로 갱신됨.

---

## 4. NFR 체크리스트 (Specification §4 정합)

7 개 비기능 요구사항. CI / QA 게이트가 본 표를 회귀 검사한다.

| 상태 | ID    | 분류    | 지표                                        | 목표값                             | 측정 도구 / 위치 (예정)                              |
|------|-------|---------|---------------------------------------------|-------------------------------------|------------------------------------------------------|
| `[ ]` | NFR-01| 성능    | 1:1 텍스트 메시지 왕복 RTT (LAN)            | 평균 < 100ms · 95p < 200ms          | `tools/bench_rtt.py` (예정)                          |
| `[ ]` | NFR-02| 성능    | 100MB 파일 송신 throughput (LAN)            | ≥ 30Mbps 평균                       | `tools/bench_transfer.py` (예정)                     |
| `[ ]` | NFR-03| 성능    | 앱 cold start → 메인 윈도우 노출            | < 2.0s (M2 MacBook 기준)            | PyInstaller 빌드 산출물 5회 평균                     |
| `[ ]` | NFR-04| 가용성  | 시그널링 단절 후 자동 재연결 성공률         | 30초 안 99% 이상                    | `tools/chaos_signaling.py` (예정)                    |
| `[~]` | NFR-05| 보안    | 시그널링 envelope 외부 입력 검증             | 화이트리스트 5종 외 거부             | `tests/server/test_protocol.py` + `tests/e2e/test_signaling_browser_flow.py` |
| `[ ]` | NFR-06| UX      | ProgressBar 진행률 갱신 빈도                | 100ms 안 1회 이상 (정지·역행 0)     | `tests/ui/test_progress_widget.py` (예정)            |
| `[ ]` | NFR-07| UX      | 한국어 UI 텍스트 가독성 (DPI 100~200%)      | 잘림 없음                           | macOS / Windows DPI 매트릭스 수동 캡처 (qa-agent)    |

> NFR-04 ↔ [RELIABILITY.md](RELIABILITY.md) · NFR-05 ↔ [SECURITY.md](SECURITY.md) 교차 정합.
> 본 문서의 체크박스가 정량 게이트 정본이며, 위 두 정책 문서는 정성 절차를 정의한다.

---

## 5. 마일스톤 진행률 (실행계획 §4 정합)

| 상태  | ID | 목표일       | 제목                                           | 산출물 요약                                                         |
|-------|----|--------------|------------------------------------------------|---------------------------------------------------------------------|
| `[~]` | M1 | 2026-05-24   | 부트스트랩 + 정책 문서 + 에이전트 정의          | 루트 18 문서 · `docs/` 골격 · `.claude/agents/` 7 에이전트 · CI 3 워크플로우 |
| `[ ]` | M2 | 2026-05-31   | 시그널링 서버 + PyQt 스켈레톤                  | `server/signaling.py` · `app/main.py` · qasync 통합                  |
| `[ ]` | M3 | 2026-06-14   | WebRTC DataChannel 텍스트 송수신                | `app/rtc/peer.py` · Offer/Answer/ICE 교환 · MariaDB 영구화           |
| `[ ]` | M4 | 2026-06-21   | 파일 / 이미지 송수신 + 양방향 ProgressBar       | `app/rtc/file_sender.py` · `file_receiver.py` · `image_processor.py` |
| `[ ]` | M5 | 2026-06-30   | PyInstaller 빌드 + GitHub Actions + README     | `tools/build.py` · `.github/workflows/build.yml` · README            |

핵심 경로 (실행계획 §11 정합). **M1 → 시그널링 서버 → DataChannel → 파일전송 → 빌드**.
한 단계라도 FAIL 시 직후 단계 진행 금지. 차단 발생은 [실행계획 §10 차단점 추적](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md) 에 1행 누적.

---

## 6. 정책 문서 9 작성 체크리스트 (정본 §K 정합)

루트 9 정책. 모두 작성 완료 — 9 / 9.

- [x] [AGENTS.md](AGENTS.md) — 저장소 맵 · 7대 규칙 요약 · 금지사항 · 문서 맵 (15.3 KB)
- [x] [ARCHITECTURE.md](ARCHITECTURE.md) — 모듈 경계 · 계층 의존 · 시스템 다이어그램 (16.4 KB)
- [x] [DESIGN.md](DESIGN.md) — UX 컨셉 · 정보 구조 · 디자인 토큰 (15.8 KB)
- [x] [FRONTEND.md](FRONTEND.md) — UI 표준 · QSS · 와이어프레임 5종 (19.2 KB)
- [x] [PLANS.md](PLANS.md) — 전체 일정 인덱스 · Phase 로드맵 (17.7 KB)
- [x] [PRODUCT_SENSE.md](PRODUCT_SENSE.md) — 기능 우선순위 판단 근거 (19.3 KB)
- [x] [QUALITY_SCORE.md](QUALITY_SCORE.md) — PR 머지 게이트 정량 지표 (17.0 KB)
- [x] [RELIABILITY.md](RELIABILITY.md) — 장애 대응 · 재연결 정책 (16.8 KB)
- [x] [SECURITY.md](SECURITY.md) — 외부 입력 위협 모델 · 시크릿 관리 (20.9 KB)

> 정본 §K 루트 18 동결 정합. 9 정책 + 8 운영 + 1 정본 (CLAUDE_HARNESS_IMPORTANT) = 18.

---

## 7. 운영 문서 8 작성 체크리스트 (정본 §K · §D 정합)

루트 8 운영. 현재 4 / 8 완료.

- [x] [CLAUDE_HARNESS_IMPORTANT.md](CLAUDE_HARNESS_IMPORTANT.md) — Watcher 정본 · §A M1~M7 · §B 5단계 워크플로우 · §D Doc Gardener 매핑
- [x] [Specification.md](Specification.md) — 요구사항 · FR 10건 · NFR 7건 · User Story 9건 · Acceptance Criteria
- [x] [Structure.md](Structure.md) — 파일 트리 · 모듈 책임 · 데이터 흐름 · ERD
- [x] CheckList.md — 본 문서. 항목 추적 · 매핑 · 진행률
- [ ] History.md — 개발 히스토리 (M3 — 역순 prepend 전용)
- [ ] README.md — 빌드 / 실행 안내 + 변경 이력 30행 (M2 정합)
- [ ] EXTENSION_GUIDE.md — 서브에이전트 활용 · 신규 에이전트 도입 절차
- [ ] MIGRATION_MARIADB.md — MariaDB 스키마 · FK 정렬 · 마이그레이션 절차

> 진행 정책. 본 문서 갱신 시 [§11 변경 절차](#11-변경-절차) 의 동시 갱신 의무 5건 수행.

---

## 8. `.claude/agents/` 7 에이전트 정의 체크리스트 (정본 §C 정합)

HARNESS 7역할 프로세스 에이전트. 모두 등재 — 7 / 7.

- [x] [.claude/agents/planning-agent.md](.claude/agents/planning-agent.md) — 요구사항 분석 · Exec Plan 초안
- [x] [.claude/agents/reviewer-agent.md](.claude/agents/reviewer-agent.md) — 코드 / 설계 리뷰 · M1~M7 위반 차단
- [x] [.claude/agents/qa-agent.md](.claude/agents/qa-agent.md) — 수동 회귀 체크리스트 · 스모크
- [x] [.claude/agents/observability-agent.md](.claude/agents/observability-agent.md) — 로그 · 메트릭 · 성능 검증
- [x] [.claude/agents/release-agent.md](.claude/agents/release-agent.md) — PR 템플릿 · 머지 게이트 · 릴리즈 노트
- [x] [.claude/agents/doc-gardener-agent.md](.claude/agents/doc-gardener-agent.md) — 주간 드리프트 감지 · 자동 보정 PR
- [x] [.claude/agents/history-agent.md](.claude/agents/history-agent.md) — History.md 역순 기록 관리

> 정본 §D 표의 도큐먼트 전담 에이전트 4종(`@spec-agent` · `@structure-agent` ·
> `@checklist-agent` · `@history-agent`) 중 `@history-agent` 만 본 디렉토리에 단독 파일로 등재되며,
> 나머지 3종은 위 7 에이전트의 책임 분담으로 흡수 운용한다. 단일 에이전트 파일로의 분리는
> [실행계획 §5 task #13](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md) 에서 검토.

---

## 9. CI 게이트 5 체크리스트 (M1~M5 · 정본 §L 정합)

마일스톤별 1 CI 게이트. 모두 작성 예정 — 0 / 5.

- [ ] **M1 게이트** — `.github/workflows/ci.yml` "Root markdown 개수 동결 확인" (루트 18 동결 · 정본 §K)
- [ ] **M2 게이트** — `.github/workflows/ci.yml` "앱 import 스모크" (`app/main.py` · `server/main.py` 양쪽 import OK)
- [ ] **M3 게이트** — `.github/workflows/ci.yml` "History 역순 검증" (M3 — `tools/md_agents.py` 강제)
- [ ] **M4 게이트** — `.github/workflows/ci.yml` "한글 주석 검사" (M4 — diff 범위 `.py` · `.js` · `.html` · `.css` · `.sql` · `.sh`)
- [ ] **M5 게이트** — `.github/workflows/ci.yml` "README 변경 이력 존재 확인" (M2 — `## 변경 이력` 30행 상한)

추가 워크플로우 2종 (정본 §L 정합) 도 같은 시기 작성.

- [ ] `.github/workflows/docs-lint.yml` — `*.md` 변경 시 trigger. 깨진 상대 링크 · frontmatter (title · owner · last_verified · status) · 연속 빈 줄 · BPE 위생 검사 (의존명사 단독 사용 차단)
- [ ] `.github/workflows/doc-gardener.yml` — 주 1회 cron + 수동. 트리 실재성 · MIGRATION tables ↔ 모델 `__tablename__` · 90일 스테일 · 실패 시 Issue 자동 생성

> 로컬 등가는 [tools/doc-lint.sh](tools/doc-lint.sh) 가 4 검사 항목을 1:1 으로 반영한다.
> push 직전 본 스크립트 실행 후 통과 시 push 진행, 1건이라도 위반 시 push 차단.

---

## 10. 외부 결정 대기 항목 (TBD)

본 시점(2026-05-17) 까지 사용자 directive 가 확정되지 않은 항목. 결정 즉시 본 표에서 §3 / §4 / §6~§9 로 승급.

- [x] ~~**TBD-01** — 라이선스 종류~~ ✅ **해소 2026-05-17**: **GPLv3 확정** (사용자 directive). [LICENSE](LICENSE) 저장소 루트 (GNU 표준 본문 674 lines) + SPDX header convention. 영구 메모리 [[project-license-gpl]] + [[project-visibility-transition]] (public → private 전환 가능성).
- [ ] **TBD-02** — TURN 서버 도입 시점 · 운영 주체. Phase 2 진입 시점 결정 보류. [Specification.md §9](Specification.md) 외부 의존성 행 참조.
- [ ] **TBD-03** — MariaDB 운영 모드 (앱 내장 single-instance vs 외부 인스턴스). `tools/db_init.py` 설계 시점 확정.
- [ ] **TBD-04** — 한국어 외 UI 언어 추가 정책. Phase 1 한국어 단일 · Phase 2 i18n 도입 시 [Specification.md §6 User Story](Specification.md) 확장 의무.
- [ ] **TBD-05** — 그룹 채팅 토폴로지 (mesh n^2 vs SFU). Phase 2 결정 로그.
- [x] ~~**TBD-06** — `.github/workflows/build.yml` self-hosted runner 등록~~ ✅ **해소 2026-05-17**: macOS arm64 등록 OK (id=2 online, launchd PID 62533). Windows runner 의 의무 = 영구 회수 (wine cross-compile 대체 — GitHub-hosted Ubuntu + `cdrx/pyinstaller-windows` docker). 영구 메모리 [[project-windows-build-via-wine]].
- [ ] **TBD-07** — 데모 시그널링 서버(`114.207.112.73:8765`) 의 systemd 또는 docker 운영 모드 확정.

> TBD 항목은 [Specification.md §12](Specification.md) 와 동기 갱신. 한쪽만 변경 금지.

---

## 11. 변경 절차

본 문서 갱신 시 **동시 갱신 의무** 가 발생한다. 누락 시 `@reviewer-agent` 차단 + `@doc-gardener-agent` 자동 보정 PR.

1. **Specification.md** — FR / NFR 행 1건 추가 / 수정 시 본 문서 §3 / §4 의 동일 ID 행 1행 동시 갱신. 본 문서 §3 / §4 ↔ Specification §3 / §4 의 ID 와 행 수 정합 유지.
2. **Structure.md** — 코드 위치 컬럼에 신규 파일 등장 시 트리 노드 + 모듈 책임 표 동시 갱신. 본 문서 §3 "코드 위치 (예정)" 컬럼이 실제 트리 노드 링크로 자동 승급.
3. **실행계획** — task 상태 (pending / in_progress / done) 가 바뀌면 [실행계획 §5 task breakdown](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md) 동시 갱신. 마일스톤 PASS / FAIL 도 §9 검증 결과 표 1행 추가.
4. **History.md** — 본 문서 변경 즉시 History.md (작성 예정 — 운영 8) 상단에 한 줄 prepend (M3 역순).
5. **README.md** — README.md (작성 예정 — 운영 8) `## 변경 이력` 섹션에 한 줄 prepend (M2 · 30행 상한).

> 본 5단계는 정본 [§B 5단계 워크플로우](CLAUDE_HARNESS_IMPORTANT.md) 의 ① 단계 안에서 모두 끝나야 한다.
> 코드 수정(② 단계) 이전에 본 절차 완료가 M1 의 핵심.

### 11.1 갱신 트리거 — 사건별 정합

| 사건                                          | 본 문서에서 즉시 갱신할 위치                      |
|-----------------------------------------------|---------------------------------------------------|
| FR / NFR 1건 신설 또는 폐지                    | §3 또는 §4 + §2 진행률 요약                       |
| 코드 task 1건 상태 전이 (pending → done 등)    | §3 상태 컬럼 + §2 진행률                          |
| 정책 / 운영 문서 1건 신규 작성                  | §6 또는 §7 체크박스 + §2 진행률                   |
| `.claude/agents/` 신규 에이전트 등재           | §8 체크박스 + §2 진행률                           |
| CI 워크플로우 1건 신규 작성 / PASS 전이        | §9 체크박스 + §2 진행률                           |
| 마일스톤 PASS 선언                             | §5 상태 라벨 + §2 진행률                          |
| TBD 항목 결정                                  | §10 → §3 / §4 / §9 로 승급 + §2 진행률             |

---

## 12. 참조

### 12.1 정본 · 맵

- [CLAUDE_HARNESS_IMPORTANT.md](CLAUDE_HARNESS_IMPORTANT.md) — Watcher 정본. §A M1~M7 · §B 5단계 워크플로우 · §C HARNESS 7역할 · §D Doc Gardener 매핑 · §E 코딩 불변 · §K 루트 18 동결 · §L CI 3 워크플로우 · §R M5 즉시 push.
- [AGENTS.md](AGENTS.md) — 저장소 맵. §3 문서 맵 · §5 7대 규칙 · §10 금지사항.

### 12.2 운영 4 문서 (작성 완료)

- [Specification.md](Specification.md) — 요구사항 명세 (FR 10 · NFR 7 · User Story 9 · Acceptance Criteria).
- [Structure.md](Structure.md) — 파일 트리 + 모듈 책임 + 데이터 흐름 + ERD.
- CheckList.md — 본 문서.
- CLAUDE_HARNESS_IMPORTANT.md — Watcher 정본 (위).

### 12.3 운영 4 문서 (작성 예정 — 운영 8 잔여)

- `History.md` — 개발 히스토리 (M3 — 역순 prepend 전용).
- `README.md` — 빌드 / 실행 안내 + 변경 이력 30행 (M2).
- `EXTENSION_GUIDE.md` — 서브에이전트 활용 · 신규 에이전트 도입 절차.
- `MIGRATION_MARIADB.md` — MariaDB 스키마 · FK 정렬 · 마이그레이션 절차.

### 12.4 정책 9 문서

- [AGENTS.md](AGENTS.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [DESIGN.md](DESIGN.md) · [FRONTEND.md](FRONTEND.md) · [PLANS.md](PLANS.md) · [PRODUCT_SENSE.md](PRODUCT_SENSE.md) · [QUALITY_SCORE.md](QUALITY_SCORE.md) · [RELIABILITY.md](RELIABILITY.md) · [SECURITY.md](SECURITY.md)

### 12.5 실행계획 · 코드 · CI

- [docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md](docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md) — Phase 1 MVP 실행 / 검증 / 결정 기록.
- [server/README.md](server/README.md) — 시그널링 서버 빠른 시작 · 프로토콜 명세.
- [app/README.md](app/README.md) — PyQt6 클라이언트 개요.
- [tools/doc-lint.sh](tools/doc-lint.sh) — 로컬 doc-lint (정본 §L docs-lint.yml 등가).

### 12.6 `.claude/agents/` 7 에이전트

- [.claude/agents/planning-agent.md](.claude/agents/planning-agent.md) · [reviewer-agent.md](.claude/agents/reviewer-agent.md) · [qa-agent.md](.claude/agents/qa-agent.md) · [observability-agent.md](.claude/agents/observability-agent.md) · [release-agent.md](.claude/agents/release-agent.md) · [doc-gardener-agent.md](.claude/agents/doc-gardener-agent.md) · [history-agent.md](.claude/agents/history-agent.md)

---

**문서 상태**: `active` · 최초 작성 2026-05-17 · 다음 검증 예정 M1 종료일 (2026-05-24)
