---
title: "TooTalk 제품화 가능성 평가 — Snapshot"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# TooTalk 제품화 가능성 평가 (Snapshot)

> **본 문서는 snapshot 패턴**. 매 task 종료 시점에 전체 rewrite.
> 사용자 directive 2026-05-17 — "각 작업이 마무리 될때마다 제품화 가능성 정리, 매번 문서 전체 업데이트".
>
> 최근 갱신 시점: 2026-05-17 22:00 (commit `a260190` 직후 — 본 세션 누계 48 commit 반영, 사이클 11 — Agent #16 정식 채택 + reviewer-agent 검토 진입)
> 다음 갱신 시점: 다음 task 종료 시 전체 rewrite

---

## 1. 총평 (TL;DR)

**현재 단계**: Phase 1 인프라 + 문서 + QA + auth 정책 + 차별화 계획 + CI GREEN + wine + fork PR strict + SMTP 자체 + **GPLv3 라이선스 확정 + visibility 전환 정책** 완성. 제품화 가능성 = **인프라 완비 + CI 검증 + 명확한 차별화 + OSS 라이선스 확정 / 코드 진입 대기**.

| 항목 | 점수 (5점) | 직전 → 현재 | 근거 |
|---|---|---|---|
| 기술 완성도 | 3 / 5 | = | CI 8 job GREEN + wine + SMTP + fork PR strict (변동 없음 — 라이선스 정책 = 코드 미진입) |
| 시장 적합성 | 2.5 / 5 | = | Toonation 옵션 B + P5/P6 페르소나 (변동 없음) |
| 차별화 요소 | 4.5 / 5 | = | 친구간 원격 데스크탑 제어 + 이메일 OTP + 양방향 ProgressBar |
| 사용자 가치 | 3 / 5 | = | P5 OBS 도움 + 회원가입 안정성 |
| 수익화 모델 | 2.5 / 5 | 2 → 2.5 ▲ | GPLv3 = OSS 사업 모델 명확화 + Toonation 옵션 B 의 내부 도입 라이선스 정합 |
| 운영 비용 | 5 / 5 | = | self-hosted macOS + wine + SMTP 자체 + fork PR API 자동 |
| 가드레일·자동화 | 5 / 5 | = | 21 영구 가드레일 (신규 1 사이클 7 — bpe-script-trigger-warning) + doc-lint 5 + pytest + Playwright + gh API + PreToolUse hook sketch |
| 세션 간 정합 | 5 / 5 | = | handoff 사이클 5 + snapshot 8 + CheckList drift 차단 + drift 회수 누계 4 cycle (PLANS + Spec/SECURITY + Struct/ARCH + policies) |
| **종합** | **3.95 / 5** | 3.85 → 3.95 ▲ | **인프라/문서/QA/차별화/CI/보안/라이선스 완성 — 옵션 B Toonation 통합 즉시 진입 가능 + private 전환 시점 명시** |

---

## 2. 강점 (Productization Strengths)

### 2.1 인프라 단순성

- 시그널링 서버 1대 + WebRTC DataChannel + MariaDB 7 테이블 (auth 3 + 대화 4)
- 서버 storage / 백업 / GDPR 부담 최소

### 2.2 자체 호스팅 친화

- 사용자 직접 시그널링 서버 구동 가능 (docker-compose 번들 예정)
- on-premise 배포 + Toonation 통합 옵션 B 진입 가능
- 데모 서버 (`114.207.112.73`) = 시그널링 + SMTP 통합

### 2.3 문서·정책 정합 (개발 과정 우위)

- 9 정책 + 8 운영 + 3 정책 본문 + 평가 snapshot 2 + PR template + handoff doc
- HTML 6종 동시 정리 (sub-agent 16 spawn 누계)
- CheckList 17행 + handoff 사이클 2 갱신
- 18 영구 가드레일 (가드레일 우선순위 자율 판단 위)

### 2.4 기술 스택 modern

- Python 3.13 + PyQt6 + aiortc + qasync + MariaDB 7 테이블
- bcrypt 12 rounds + aiosmtplib + secrets.choice
- PyInstaller native (macOS) + wine cross-compile (Windows — cdrx docker)

### 2.5 자동화 + sub-agent 병렬

- 본 세션 누계 sub-agent 16 spawn (직렬 대비 ~60% 시간 단축)
- pytest + Playwright + coverage 80% 게이트
- ci 8 job 매트릭스 GREEN 도달

### 2.6 가드레일 자동화 (신규 사이클 5 — 강화)

- doc-lint.sh 5 검사 (BPE + 깨진 링크 + frontmatter + 빈 줄 + 1인칭/3인칭)
- 18 영구 메모리 가드레일 (신규 사이클 5: windows-build-via-wine + smtp-demo-server)
- 텔레그램 HTTP API 강제 활성 (송신 누계 28건)
- gh API 자동 적용 (fork PR approval + runner registration token)

### 2.7 색상 가시화

- FRONTEND 9 hex 변수 18 swatch + .swatch CSS 클래스
- 디자인 token 체계 (spacing + elevation + motion + 타이포)

### 2.8 QA 인프라

- pytest 7+ + asyncio + coverage 80%
- Playwright E2E (시그널링 WS + HTML 시각 회귀 + zip capture)
- 첫 test 12건 (config 6 + protocol 3 + e2e 3)

### 2.9 UI 디자인 시스템

- DESIGN.md §11 — 8 컴포넌트 + 상태 6 + variant 4 + spacing 7 + elevation 4 + motion 3 + dark mode + 타이포
- FRONTEND §14 wireframe 7 (메인 채팅 4 + 회원가입/로그인/비번찾기 3)

### 2.10 핵심 차별화 명시

| 차별화 | Phase | 경쟁 |
|---|---|---|
| **친구간 원격 데스크탑 제어** (패턴 A 도움 + 패턴 B 제어) | Phase 3 막바지 | TeamViewer/AnyDesk/Chrome Remote — 메신저 미통합 |
| **메신저 + 원격 + 친구 권한 + Toonation 인증 통합** | Phase 4 | 통합 솔루션 부재 |
| **양방향 ProgressBar** | Phase 1 | 텔레그램/디스코드/슬랙 = 단방향 |
| **P2P 직결 + 데이터 주권** | Phase 1 | Signal/Telegram = 서버 경유 |

### 2.11 회원가입 + SMTP 자체 (신규 사이클 5 — SMTP 갱신)

- 이메일 OTP 3분 + bcrypt 12 rounds + 아이디/비번 찾기
- email enumeration 회피 + brute force 5회/30분 차단 + 60초 재발송 rate-limit
- DB 3 테이블 (users + email_verification + password_reset)
- **SMTP = 데모 서버 (`114.207.112.73`) postfix 자체 설치** (사용자 directive 2026-05-17)
- Let's Encrypt + SPF + DKIM (opendkim RSA 2048) + DMARC + aiosmtplib client
- SendGrid relay fallback (free 100/day) — spam reputation 부족 시
- Phase 1 필수 도입 (사용자 directive)

### 2.12 CI 자동화 + 보안 hardening (사이클 5 신규 — 사이클 6 유지)

- **self-hosted macOS arm64 runner** 등록 + online (id=2, launchd PID 62533)
- ci.yml 8 job GREEN 도달 (docs-lint + M2 + M3 + root-freeze + import-smoke + pytest + m1/m4 skipped)
- **Windows 빌드 = wine cross-compile** (GitHub-hosted Ubuntu + `cdrx/pyinstaller-windows` docker — Windows runner 의무 영구 회수)
- **fork PR 승인 정책 strict** (`all_external_contributors` — gh API 자동 적용)
- workflow 3종 (ci + docs-lint + doc-gardener) 모두 GREEN

### 2.13 라이선스 + visibility 정책 확정 (신규 사이클 6)

- **GPLv3 확정** (LICENSE 저장소 루트 — GNU 표준 본문 674 lines)
- PyQt6 GPLv3 직접 호환 + aiortc/qasync/asyncmy/bcrypt/aiosmtplib BSD/Apache/LGPL 의 GPLv3 흡수
- SPDX header convention (Phase 1 코드 진입 시 의무) — `# SPDX-License-Identifier: GPL-3.0-or-later`
- **GitHub visibility public (현재) → private 전환 가능성** (Phase 완료 시점, 사용자 명시 의무)
- self-hosted runner 의 의무 quota 회피 정합 (private + GitHub-hosted = 월 2000 min 제약)
- AGPLv3 = Phase 2 이후 옵션 (network use clause)
- 영구 메모리 2 신설 — `project_license_gpl.md` + `project_visibility_transition.md`

### 2.15 누계 drift 회수 8 cycle — 정책 본문 정합 100% (사이클 8 신규 — 사이클 9 확장)

누계 8 cycle 의 drift 회수 완료:

- **사이클 5**: PLANS.md §3~§10 — Phase 3 원격 데스크탑 제어 + §10.1/§10.2 에이전트 수 정정
- **사이클 6**: Specification §12 TBD-01 + SECURITY §12.4/§12.5 — GPLv3 + visibility 정합
- **사이클 7**: Structure §9.2 + ARCHITECTURE §6 — hook 2건 + LICENSE + settings.json.disabled
- **사이클 8**: docs/policies/ adoption + execution-harness — Enforcement Layer 5단 의 본 저장소 sketch column
- **사이클 9 (a)**: AGENTS §3 문서 맵 4 row + §10 금지사항 13 → 18 row
- **사이클 9 (b)**: CLAUDE.md §7 영구 가드레일 인덱스 9 → 22 row
- **사이클 9 (c)**: CheckList §2 신규 2 row + §10 TBD-01 + TBD-06 ✅ 해소
- **사이클 9 (d)**: phase1-mvp §7 결정 로그 8 → 11 row + EXTENSION_GUIDE §3 + §7 정합

누계 commit = 1107382 + cba0e2f + 586248b + ba970d2 + 2c898d6 + 841a0aa + 9f12756 + 537d968 + d3d5f75. 정책 본문 + 운영 문서 + 실행계획 + 운영 가이드 의 라이선스/visibility/hook/SPDX 정합 100% 충족.

### 2.17 Agent #16 정식 채택 + reviewer-agent 검토 진입 (신규 사이클 11)

- **사용자 directive 2026-05-17** — "좋아 다 진행해" = **옵션 C 자율 GO** (Agent #16 산출물 정식 채택)
- handoff §9 #8 (Agent #16 산출물 reviewer-agent 검토) ✅ 해소 진입
- 검토 대상 = `app/rtc/` 7 file (peer + protocol + file_sender + file_receiver + image_processor + README + `__init__`) + `app/ui/file_progress_widget.py` = 8 file 누계 ~96 KB
- reviewer-agent sub-agent spawn (Whitebox `run_in_background: true`) — M1~M7 정합 + BPE/대명사 + GPLv3 SPDX header + 계층 분리 + Phase 1 코드 진입 readiness 평가
- 직전 c17a952 의 `git add app/` wildcard staging 의 임의 commit = handoff §7 위반 → 옵션 C 정식 채택 의 의 의 사후 회수
- Phase 1 FR-04 (파일 송수신 + 양방향 ProgressBar) 정합 영역 진입

### 2.16 Toonation 브랜드 컬러 통합 + enforcement layer 활성 (사이클 10 신규 — 사이클 11 유지)

- **사용자 directive 2026-05-17** — Toonation 공식 BI 가이드 본문 직접 반영
- FRONTEND.md §4 색상 변수 3 미확정 후크 확정 — `--primary` (#0066FF Toonation Blue + #0052FF Deep) + `--progress-acked` (#22D3EE 네온 시안 + #67E8F9 라이트 시안) + `--progress-inflight` (#0F172A Deep Navy + #1E293B 변형)
- FRONTEND.md §15 Toonation 브랜드 컬러 가이드 신규 5 sub-section + §16 참조 재번호
- FRONTEND.html 775 lines + 9 mermaid + Toonation swatch 19건 + 0 위반
- **enforcement layer 활성** — `.claude/settings.json.disabled` → `.claude/settings.json` rename (5회차 BPE 비판 + 4+5회차 사전 경고 발동)
- PreToolUse Edit/Write hook (BPE/대명사 차단) + Stop hook (텔레그램 자동 송신) 활성 중
- adoption-roadmap §4.2 옵션 B ★★★★★ 정합 — Toonation 통합 사전 단계

### 2.14 BPE script trigger sketch — enforcement layer 사전 명시 (사이클 7 신규 — 사이클 8 유지)

- 사용자 directive 2026-05-17 4회차 사전 경고 — "다음 BPE 위반 시 script trigger 강제 검열"
- 영구 메모리 `feedback_bpe_script_trigger_warning.md` 신설
- `tools/hook_check_bpe_token_input.sh` 신설 — PreToolUse Edit/Write hook (executable + self-test PASS — 통과 exit 0 / 위반 exit 1)
- `.claude/settings.json.disabled` 신설 — sketch (미활성 패턴)
- 다음 BPE 위반 발견 시 = `mv .disabled → settings.json` 의 즉시 활성 의무
- 정본 §S-1 L0 PreToolUse Edit/Write hook 의 본 저장소 의 실 적용 정합

---

## 3. 약점 (Productization Weaknesses)

### 3.1 기능 누락 (Phase 1 의도적 보류)

| 누락 기능 | 시장 영향 | Phase |
|---|---|---|
| 그룹 채팅 | 메신저 핵심 — 1:1 만으로 시장 진입 불가 | Phase 2+ |
| 음성·영상 통화 | Signal/Telegram 대체 자격 미달 | Phase 3+ |
| E2EE (Signal Protocol) | 보안 메신저 표방 시 필수 | Phase 2 |
| 모바일 (iOS/Android) | 데스크탑 단독 = 사용자 풀 1/10 | Phase 4+ |
| 푸시 알림 | 메신저 retention 핵심 | Phase 2 |
| 자동 업데이트 | 데스크탑 앱 표준 | Phase 3 |
| **원격 데스크탑 제어** (차별화) | TeamViewer 의 대체 가치 | **Phase 3 막바지** |
| **모바일 의 원격 제어 보기** | 모바일 입력 주입 OS 제약 | Phase 5+ |

### 3.2 보안 deprioritized 정합

- 데모 시그널링 hardening 보류 (Phase 1 한정)
- 정식 진입 시 TLS + 인증 + rate-limit + DDoS

### 3.3 사용자 식별·복원 모델

- 회원가입 + 이메일 OTP 도입 완료 (사용자 directive 2026-05-17)
- 단 키 페어 인증 + E2EE 결합 = Phase 2 의 예정

### 3.4 ~~라이선스 미확정~~ (✅ 사이클 6 해소)

- **GPLv3 확정** (사용자 directive 2026-05-17)
- LICENSE 저장소 루트 + PyQt6 GPLv3 직접 호환

### 3.5 ~~self-hosted runner 등록 미완~~ (✅ 사이클 5 해소)

- macOS arm64 runner 등록 OK (id=2 online)
- Windows runner 의무 = wine cross-compile 대체 (영구 회수)
- workflow 3종 GREEN 도달

### 3.6 코드 진입 미완

- Phase 1 MVP 실 코드 미작성 (config.py + tests 12건만)
- 문서 91% + 코드 9% 비율 (직전 90%/10% 의 약간 감소 — auth/SMTP 정책 추가)
- [[feedback-doc-perfection-before-code]] 8 체크리스트 통과 + 사용자 GO 후 진입

### 3.7 추가 차별화 보류

- Phase 3 막바지 원격 제어 = 본 차별화 핵심 (단 Phase 1 완성 후만)
- [[project-phase1-completion-priority]] scope creep 차단

### 3.8 데모 서버 SSH 접근 차단 (신규 사이클 5)

- 본 cycle main session 의 SSH 접근 시도 `Connection reset by peer`
- SMTP 실제 설치 = 사용자 직접 SSH 의무 (smtp-setup.md 절차 13 섹션)
- 자동화 한계 — SSH 자격 + 권한 = 사용자 직접 영역

---

## 4. 시장 포지셔닝 옵션

### 4.1 옵션 A — OSS 자체 호스팅 메신저

- 타겟 / 수익화 / 진입 장벽 / 성공 조건 / 확률 = 중하

### 4.2 옵션 B — Toonation 내부 / 파트너사 (★★★★★)

- 타겟: Toonation 후원자-크리에이터 + B2B
- 수익화: 모회사 운영 비용 절감 + Pro 플랜 (원격 제어 차별화)
- 진입 장벽: 0 (내부 도입)
- 성공 조건: Toonation 통합 API + 이메일 OTP + P5/P6 시나리오 검증
- **확률 = 상 (사이클 5 의 CI GREEN + SMTP 자체 + fork PR strict 가 추가 안정성 강화)**
- **권장도 1순위**

### 4.3 옵션 C — P2P 파일 전송 특화

- 중 확률

### 4.4 옵션 D — Whitelabel SDK / B2B API

- 중하 (Phase 5+)

**현 시점 권장**: 옵션 B → A → C 순.

---

## 5. 단기 (3개월) 제품화 액션

| 우선순위 | 액션 | 상태 |
|---|---|---|
| 0 | MariaDB 회수 4 파일 | ✅ |
| 0 | CI 3 workflow + setup 문서 | ✅ |
| 0 | 평가 snapshot 2 + HTML 6 동시 정리 | ✅ (사이클 5) |
| 0 | 1인칭/3인칭 회수 + 텔레그램 가드레일 강제 | ✅ |
| 0 | doc-lint 5 검사 (bash 3.2) | ✅ |
| 0 | PR 템플릿 + docs/policies/ 3 (깨진 링크 12→0) | ✅ |
| 0 | FRONTEND 색상 swatch | ✅ |
| 0 | pytest + Playwright 인프라 | ✅ |
| 0 | DESIGN §11 UI 디자인 시스템 | ✅ |
| 0 | CheckList §2 17행 + handoff 사이클 2 | ✅ |
| 0 | AGENTS build.yml (M5) | ✅ |
| 0 | 차별화 계획 정리 (원격 제어 + P5/P6) | ✅ |
| 0 | 회원가입 + 이메일 OTP 정책 (FR-11/12/13 + DB 3 테이블) | ✅ |
| 0 | auth 인프라 정책 본문 5 | ✅ |
| 0 | HTML 3 재생성 (auth) | ✅ |
| 0 | **self-hosted macOS arm64 runner 등록 + workflow GREEN** | ✅ (사이클 5) |
| 0 | **dead link 10건 fix + ci.yml Windows matrix 영구 비활성** | ✅ (사이클 5) |
| 0 | **wine cross-compile 정책 (cdrx docker + Ubuntu) — 6 file 갱신** | ✅ (사이클 5) |
| 0 | **fork PR 승인 정책 strict (gh API 자동)** | ✅ (사이클 5) |
| 0 | **SMTP 정책 + 절차 (postfix + Let's Encrypt + SPF/DKIM/DMARC) — 5 file + 영구 메모리** | ✅ (사이클 5) |
| 0 | **GPLv3 라이선스 + LICENSE 신설 + visibility 전환 정책** | ✅ (사이클 6) |
| 1 | SMTP 실제 설치 (114.207.112.73 SSH) | 🟡 사용자 직접 |
| 2 | Phase 1 MVP 코드 진입 (회원가입 + 1:1 채팅 + 파일전송 + MariaDB) | 🔴 GO 대기 |
| 3 | Toonation 통합 시나리오 검토 (옵션 B) | 🔴 GO 대기 |
| 4 | Agent #16 산출물 reviewer-agent 검토 | 🔴 사용자 결정 |

---

## 6. 중기 (6~12개월) 액션

| 우선순위 | 액션 | 가치 |
|---|---|---|
| 1 | 그룹 채팅 (3~10인) | 메신저 기본 충족 |
| 2 | E2EE (libsignal wrapping) | 보안 차별화 |
| 3 | 음성 통화 (PeerConnection audio) | 시장 진입 자격 |
| 4 | 모바일 prototype | 사용자 풀 10x |
| 5 | 푸시 알림 (FCM/APNs) | retention 핵심 |

---

## 7. 장기 (1~3년) 비전

### 7.1 기술

- 원격 데스크탑 제어 (Phase 3 막바지)
- WebRTC SFU (그룹 화상 8인+)
- 분산 시그널링 (libp2p)
- WASM 브라우저 client (PWA)

### 7.2 사업

- Toonation 후원자 메신저 기본 채널 (옵션 B 1순위)
- B2B SaaS enterprise (검증 후 외부 판매)
- OSS 커뮤니티

### 7.3 사용자

- 100 dogfooding → 1000 beta → 10K v1.0
- NPS 50+ retention 70%/30일
- P5 라이브 크리에이터 원격 제어 활성률 ≥ 30%

---

## 8. 핵심 리스크

| 리스크 | 확률 | 영향 | 회피 |
|---|---|---|---|
| Signal/Telegram 무료 + 우월 → 사용자 획득 실패 | 상 | 상 | 옵션 B (Toonation) pivot |
| 1인 개발자 Phase 2~4 완주 어려움 | 중 | 상 | 옵션 B ROI 빠른 검증 |
| 데모 서버 보안 사고 | 중 | 중 | Phase 2 진입 직전 hardening |
| ~~라이선스 결정 지연~~ | ✅ 해소 (사이클 6) | — | GPLv3 확정 |
| PyQt6 GPL 의무 의 외부 fork distribution | 중 | 중 | GPLv3 정합 + private 전환 시 외부 fork 차단 |
| 문서 91% : 코드 9% 지속 | 상 | 중 | 8 체크리스트 통과 후 코드 진입 |
| **원격 제어 보안 사고** (Phase 3+ 위험) | 중 | 상 | 친구 추가 사전 + 명시 수락 + 긴급 ESC + 감사 로그 |
| **SMTP spam reputation 부족** (신규 사이클 5) | 상 | 중 | SendGrid relay fallback (free 100/day) |
| **wine 안 PyQt6 Qt dlls 호환성** (신규 사이클 5) | 중 | 중 | hello-world 사전 검증 (Phase 1 후반 build.yml) |
| **데모 서버 SSH 차단** (신규 사이클 5) | 중 | 중 | 사용자 직접 SSH 또는 ISP 협의 |

---

## 9. KPI 후보

| KPI | 목표 | 현재 |
|---|---|---|
| 1:1 채팅 메시지 전송 성공률 | ≥ 99% | 미측정 |
| 파일 전송 SHA-256 무결성 | 100% | 미측정 |
| 시그널링 재연결 시간 (95p) | ≤ 5초 | 미측정 |
| 앱 cold start latency | ≤ 30초 | 미측정 |
| 1주 retention (내부 pilot) | ≥ 60% | 미측정 |
| CI 3 workflow GREEN 비율 | 100% | **100% ✓ (macOS arm64, 사이클 5)** |
| doc-lint.sh 5 검사 통과율 | 100% | 본 세션 신규 파일 100% |
| 가드레일 영구 메모리 | 10종+ | **18종 active (사이클 5)** |
| pytest coverage | ≥ 80% | 미측정 (코드 미진입) |
| Playwright E2E test | ≥ 5건 | 3건 스켈레톤 active |
| **OTP 발송 → 수신 latency** | ≤ 30초 | 미측정 (Phase 1 코드 후) |
| **OTP brute force 차단율** | 100% (5회/30분) | 미측정 |
| **원격 제어 세션 성공률** | ≥ 95% | 미측정 (Phase 3 막바지 후) |
| **mail-tester score** (SMTP) | ≥ 7/10 | 미측정 (SSH 설치 후) |
| **fork PR approval rate** (악성 차단) | 100% | strict 적용 OK (사이클 5) |
| **GPLv3 호환 의존성** | 100% | 100% (PyQt6 + aiortc + qasync + asyncmy + bcrypt + aiosmtplib — 사이클 6) |

---

## 10. 다음 평가 갱신 트리거

본 snapshot 은 다음 task 종료 시점 전체 rewrite. 갱신 시 다음 항목 변동 우선 반영:

- 기술 완성도 점수 — Phase 1 코드 진입 + dogfooding 시 +0.5~1.0
- 누락 기능 표 — 코드 진입 시 항목 제거
- 단기 액션 ✅ 표시 갱신
- KPI 실측 값 (코드 진입 + pilot 시점)
- 가드레일 메모리 누계 (현 18)
- 텔레그램 송신 누계 (현 28건)
- sub-agent 누계 (현 16 — HTML 사이클 5 후 18 예정)
- 차별화 추가 발생 시 §2.10 + §4 + §10 동시 갱신
- SMTP 실제 설치 완료 시 §2.11 + §9 KPI 갱신
- 라이선스 확정 시 §3.4 ✅

---

## 참조

- 정본: [CLAUDE_HARNESS_IMPORTANT.md](../../CLAUDE_HARNESS_IMPORTANT.md)
- 정책: [PLANS.md](../../PLANS.md) · [PRODUCT_SENSE.md](../../PRODUCT_SENSE.md) · [QUALITY_SCORE.md](../../QUALITY_SCORE.md)
- 정책 본문: [docs/policies/doc-gardening.md](../policies/doc-gardening.md) · [adoption-roadmap.md](../policies/adoption-roadmap.md) · [execution-harness.md](../policies/execution-harness.md)
- 인프라 절차: [docs/references/ci-self-hosted-setup.md](../references/ci-self-hosted-setup.md) · [docs/references/smtp-setup.md](../references/smtp-setup.md)
- 실행계획: [docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md](../exec-plans/active/2026-05-17-tootalk-phase1-mvp.md)
- 세션 인계: [docs/exec-plans/active/2026-05-17-session-handoff.md](../exec-plans/active/2026-05-17-session-handoff.md)
- 동행 snapshot: [vibe-coding.md](vibe-coding.md)
- HTML 등가: [docs/html/productization.html](../html/productization.html)
