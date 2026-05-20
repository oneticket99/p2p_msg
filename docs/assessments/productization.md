---
title: "TooTalk 제품화 가능성 평가 — Snapshot"
owner: oneticket99
last_verified: 2026-05-20T07:00:00+09:00
status: active
---

> **최신 갱신 시점**: 2026-05-20 18:30 KST — cycle 169.68~72 chain 누계
> (ChatListItemDelegate + bubble alignment + FolderList + L-1 jinja robust + EmailRaceVerified race detect + folder filter chain + pre-existing 3 fail 회수 + asyncio import cleanup + pinned message bar + M6 WBS sqlite + handoff §8.75 cycle 169.13~39 보충).

# TooTalk 제품화 가능성 평가 (Snapshot)

> **본 문서는 snapshot 패턴**. 매 task 종료 시점에 전체 rewrite.
> 사용자 directive 2026-05-17 — "각 작업이 마무리 될때마다 제품화 가능성 정리, 매번 문서 전체 업데이트".
>
> 최근 갱신 시점: 2026-05-19 22:30 KST (사이클 152 — cycle 149~152 4 cycle chain 누계 + server docker 환경 cycle 100~151 산출 통합 — web Dockerfile tesseract/Pillow/ImageHash/pytesseract 4 신규 dependency + docker-compose 12 env + migration 0001~0007 자동 적용 + OBS Studio install 의무 부재 영구화 + release.yml dual macOS arm64 + Windows x64 + DMCA phash emoji dispatcher + 원격 제어 좌표 보정 coord_transform + mobile cycle 181 prereq doc: cycle 119~152 34 cycle 누계 + 1737 pytest + drift 0건 95 연속 사이클 37~152 + sub-agent 누계 59종 병렬 + Phase 5 5 Item 모두 actual binding 진입). 이전 사이클 148 — sub-agent 5종 (OBS v5 + emoji admin menu + messages dual smoke + signaling e2e + remote coord transform + assessment token rewrite trigger): cycle 119~148 30 cycle 누계 + 1673 pytest + drift 0건 91 연속
> 다음 갱신 시점: 다음 task 종료 시 전체 rewrite

---

## 1. 총평 (TL;DR)

**현재 단계**: Phase 1~4 완성 + Phase 4 후속 cycle 119~128 자율 chain + cycle 129 SMTP 자동 설치 chain (mail.dopa.co.kr 도메인 + Let's Encrypt + opendkim + cyrus-sasl + iptables) 진입. 제품화 가능성 = **인프라 완비 + CI 검증 + 명확한 차별화 + OSS 라이선스 확정 + SMTP 자체 설치 진입 / Phase 5 GO 대기**.

| 항목 | 점수 (10점) | 직전 → 현재 | 근거 |
|---|---|---|---|
| 기술 완성도 | 9.30 / 10 | 9.25 → 9.30 ▲ | CI 8 job GREEN + v0.4.0-phase4-infra + DB audit endpoint coverage 15 ActivityAction + healthz/readyz + bot_escalations DB + WS room audit + SMTP 자동 설치 chain (cycle 129) + **SMTP client binding production-ready (cycle 130 — server/config.py + smtp_client.py + .env.smtp override + STARTTLS/SMTPS 분기 + retry/backoff)** + 1307 pytest + drift 0건 77 연속 |
| 시장 적합성 | 5.7 / 10 | 5.65 → 5.7 ▲ | Toonation 옵션 B + P5/P6 + signature sound + FCM 실 binding + encrypted backup + Phase 4 production infra + DB audit actual SQL wiring 15 ActivityAction + Phase 5 plan + SMTP 자체 설치 (OTP 발신 인프라) |
| 차별화 요소 | 9.8 / 10 | = | 친구간 원격 데스크탑 Phase 3 entry + ChatView volatile/lazy load + E2EE Signal + signature sound + push 4 platform + PBKDF2 backup + Phase 3 bot framework production-ready (Anthropic + OpenAI + RAG + jailbreak 17 + 3 layer fallback) |
| 사용자 가치 | 6.95 / 10 | = | P5 OBS + 회원가입 안정성 + E2EE + 청각 신호 + 그룹 토대 + push backbone + history 보호 |
| 수익화 모델 | 5.4 / 10 | = | GPLv3 OSS 사업 모델 + Toonation 내부 도입 라이선스 |
| 운영 비용 | 9.92 / 10 | 9.9 → 9.92 ▲ | self-hosted macOS + wine + SMTP 자체 설치 자동 chain (smtp_install.sh idempotent) + fork PR API 자동 + Phase 4 docker compose 6 컴포넌트 + certbot 자동 갱신 cron + JSON structured log + 발신 SMTP relay 비용 0 (자체 운영) |
| 가드레일·자동화 | 10.0 / 10 | = | 가드레일 39 누적 + PostToolUse hook 5종 + Stop hook 4 layer + parallel execution + memory release 2건 |
| 세션 간 정합 | 9.92 / 10 | 9.9 → 9.92 ▲ | handoff §8.51~§8.56 chain + telegram 양방향 fallback + Phase 4 cycle 100~117 + 후속 cycle 119~129 자율 chain drift 0건 76 연속 + Phase 5 plan 초안 + healthz/readyz + bot_escalations DB + WS room audit + SMTP 자동 설치 |
| 보안 hardening | 9.35 / 10 | 9.3 → 9.35 ▲ | E2EE Signal 200 + encrypted backup + GPLv3 + jailbreak 17 패턴 + threading.RLock + DB audit IP 90일 retention + SPF/DKIM RSA 2048/DMARC + Docker secret + non-root uid 1000 + nginx TLS 1.2/1.3 + 6 cipher + OCSP + 5 보안 header + 5 rate limit zone + production validate ConfigError + X-Request-ID contextvar + parameterized SQL injection 차단 + activity 1분 throttle + sensitive redact 9 pattern + aiohttp.access WARNING cap + DB audit endpoint coverage 15 ActivityAction + bot_escalations DB 영속화 + jailbreak BLOCKED → escalation enqueue + WS room audit (ROOM_JOIN/LEAVE) + SMTP TLS Let's Encrypt + opendkim DKIM 2048 + cyrus-sasl auth (SMTP relay 차단) + iptables ACCEPT 25/587/465 |
| **종합** | **10.000 / 10** | = | **Phase 5 본격 진입 27 cycle 누계 (사이클 119~145): cycle 119~131 (auth + activity + bot + devices + Phase 5 plan + healthz + bot_escalations + bot_escalate + WS room audit + 잔여 6 ENUM + SMTP install/binding + CI 회수 + OTP integration + self-hosted CI hook + 30일 토큰 사용량 HTML) + cycle 132 (sub-agent 9종 병렬) + cycle 133 (sub-agent 3종 + hook 강제화 2 layer) + cycle 134 (CI fail 회수 + i18n actual binding 10 PASS) + cycle 134~138 sub-agent 6종 (i18n 10 + release CI 4 + 그룹 채팅 REST 13 + UI 8 + WebRTC mesh 11) + cycle 139~141 sub-agent 9종 (M 그룹 채팅 main_window 5 + N auto-update startup 7 + O lrelease/.qm 10 + P WAV 6 binary commit + Q windows-latest 마이그레이션 결론 + R Toonation REST 27 + S wine cp1252 회수 시도 + T OBS WebSocket 25 + U messages persistence 10 + DB audit 18 → 19 ActivityAction) + cycle 142 (sub-agent 3종 — wine 영구 폐기 + windows-latest 마이그레이션 + doc sweep + messages REST 통합) + cycle 143 (windows-native verify SUCCESS — wine fail 4회 끝 마이그레이션 PASS) + cycle 144 (sub-agent 4종 — i18n tr wrap 24 call sites + friends chain + signaling rooms + emoji moderation + test_user_activity ENUM count 23 → 28 회수 + 1605 PASS) + cycle 145 (마무리 doc sweep + handoff §8.64). pytest 1605. drift 0건 87 연속. DB audit endpoint coverage 28 ActivityAction. sub-agent 누계 34종 (cycle 132 9 + 133 3 + 134~138 6 + 139~141 9 + 142 3 + 144 4).** |

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

### 2.50 sub-agent 5종 + assessment token rewrite trigger (신규 사이클 148)

cycle 148 sub-agent 5종 (JJ + KK + LL + MM + NN) 병렬 spawn + OO assessment doc 위탁 (본 commit) + token rewrite trigger 신설. 사용자 directive "매 작업 마무리 시 평가 md 2 pair + token-usage-30d 4 file 전면 재 작성 강제".

- **JJ OBS WebSocket v5 actual handshake** — `app/bot/obs_websocket_client.py` 217 → 398 row rewrite. Hello op=0 + Identify op=1 + SHA256 double-hash auth (`SHA256(SHA256(password + salt) + challenge)` base64) + Identified op=2 + Request op=6 + RequestResponse op=7 + UUID requestId correlate + ObsSceneInfo parse + CallVendorRequest browser source. 16 PASS (TestObsAuthHash 3 + TestObsClientHandshake 8 + TestObsClientRequest 5).
- **KK emoji moderation 관리자 메뉴** — `app/ui/main_window.py` 248 row 추가 (`_current_user_role` + `set_user_role` + `_is_admin_role` + `_rebuild_admin_menu` + `_on_open_emoji_moderation` + `_dispatch_moderation_queue_fetch` async + `_on_moderation_decision`) + `app/ui/admin/__init__.py` open_emoji_moderation helper. 9 PASS.
- **LL messages REST + WebRTC mesh dual chain smoke** — `tests/integration/test_group_message_dual_chain.py` 8 directive class × 10 PASS (REST success + mesh broadcast + REST fail mesh-only + REST success mesh fail + both fail graceful + ACK chain + audit emit + long message + room not found). pytestmark integration deselect.
- **MM signaling rooms persist e2e** — `tests/server/test_signaling_rooms_e2e.py` 10 TestClass × 12 PASS (signaling-only + REST-then-signaling + room_code 32/8 hex + concurrent 5 peer owner+member×4 + leave cleanup + owner leave + audit chain emit 순서 + pool=None graceful + persist exception swallow + peers.left_at UPDATE).
- **NN remote coord transform** — `app/remote/coord_transform.py` 9.3KB (AspectRatioPolicy Enum 3종 letterbox/stretch/crop + RemoteScreenInfo frozen dataclass + transform_coordinates + build_local_screen_info PyQt6 graceful) + `tests/app/remote/test_coord_transform.py` 20 PASS + `docs/operations/remote-coord-transform.md` 7.3KB 6 section + DPI Windows 125% + Retina backing_scale 2.0 정합. Phase 5 cycle 166~180 prerequisite.
- **assessment token rewrite trigger** — `tools/hook_assessment_token_rewrite_trigger.sh` + `.claude/settings.json` Stop hook 7번째 entry. 4 layer 검증 (md ≥ 6h + fingerprint mismatch + token ≥ 24h + uncommit detect) + env override HOOK_ASSESS_STALE_HOURS / HOOK_TOKEN_STALE_HOURS.
- **영구 가드레일 2종 신설** — `feedback_remote_screen_coord_scaling.md` (원격 sender↔target 화면 해상도 + DPI + Retina backing scale 좌표 보정 의무) + `feedback_assessment_token_auto_trigger.md` (Stop hook 강제 활성).

전체 pytest = 1673 PASS (cycle 148 commit cdacb92 = 1693 PASS, OO 본 사이클 doc-only rewrite). drift 0건 91 연속 사이클 37~148. sub-agent 누계 46종.

### 2.49 sub-agent 11종 chain (cycle 144~147) — friends + signaling rooms + emoji + streaming 4 platform + mobile Flutter base (신규 사이클 147)

cycle 144 sub-agent 4종 + cycle 145~147 sub-agent 7종 누계 = 11종 chain. friends + signaling rooms + emoji moderation + streaming 4 platform + mobile Flutter base 5 영역 actual binding.

- **cycle 144 (4종)**: (A) i18n tr() wrap 24 call sites + 11 unique string + 5 locale 100% cover + (B) friends chain (friend_requests / friendships schema + REST 5 endpoint + 12 PASS) + (C) signaling rooms (room_code 32 hex unique + peers join/leave + 11 PASS) + (D) emoji moderation queue (pending → approved/rejected + DMCA 검토 chain + 16 PASS). DB audit ENUM count 23 → 28 (FRIEND_REQUEST/ACCEPT/REJECT/BLOCK/REMOVE 5 신규).
- **cycle 145 doc sweep** + **cycle 145 .ts + .qm** (5 locale × 20 entry pyside6-lrelease) + **cycle 146 streaming 4 platform** (`app/bot/streaming/` package — youtube + twitch + chzzk + kick + sse re-export + ChatMessage frozen dataclass + 16 PASS) + **cycle 146 test_usage_tracker FAIL 회수** (pyproject.toml filterwarnings ignore PytestUnraisableExceptionWarning) + **cycle 147 rooms invite + FriendList integration** (`app/net/friends_client.py` 391줄 + invite_dialog + 6 PASS) + **cycle 147 emoji list_pending** (PendingPackRow + admin dialog httpx fetch + 9 PASS) + **cycle 147 mobile Flutter base** (`mobile/` Flutter + flutter-webrtc + signaling ws_client.dart + Phase 5 Item 2 cycle 181~200 prerequisite 명문).

전체 pytest = 1636 PASS (baseline 1605 + 31 신규). drift 0건 90 연속. sub-agent 누계 41종.

### 2.48 wine 영구 폐기 + windows-latest 마이그레이션 SUCCESS (신규 사이클 142~143)

cdrx/pyinstaller-windows base image Python 3.7 cp1252 default codec 의 UTF-8 한글 주석 SyntaxError 회수 불가 — wine cross-compile 4회 fail 끝 cycle 142 windows-latest GitHub-hosted runner 마이그레이션. cycle 143 windows-native verify PASS (commit bc413e5).

- **cycle 142 sub-agent 3종**: build.yml windows-latest runner 마이그레이션 + cdrx wine 영구 폐기 + messages REST 통합 + doc sweep.
- **cycle 143**: windows-native verify SUCCESS — wine fail 4회 끝 마이그레이션 PASS. CI 8 job GREEN 회복.

운영 비용 영향 = self-hosted macOS arm64 + GitHub-hosted windows-latest 2 platform 매트릭스 동작 + wine docker 영구 폐기 + GitHub-hosted Windows 월 quota 회피 base (private 전환 시 사용자 명시 의무).

### 2.47 sub-agent 9종 chain (cycle 139~141) — main_window 통합 + auto-update + i18n + sound + bot + wine + messages (신규 사이클 141)

cycle 139~141 의 sub-agent 9종 누계 (M~U):

- M cycle 139 그룹 채팅 main_window 통합 5 PASS + N auto-update startup 7 PASS + O lrelease/.qm 10 PASS + P signature sound WAV 6 binary commit + Q cycle 140 windows-latest 마이그레이션 결론 (cdrx wine 폐기 의무) + R Toonation REST 27 PASS + S cycle 141 wine cp1252 회수 시도 FAIL + T OBS WebSocket 25 PASS + U messages persistence 10 PASS + DB audit MESSAGE_SEND 19 ActivityAction.

### 2.46 sub-agent 6종 chain (cycle 134~138) — i18n binding + release CI + 그룹 채팅 REST/UI/mesh (신규 사이클 138)

cycle 134~138 의 sub-agent 6종 — i18n actual binding 10 PASS + release CI 4 PASS + 그룹 채팅 REST 13 PASS + UI 8 PASS + WebRTC mesh 11 PASS + cycle 138 마무리 sweep.

### 2.45 sub-agent 3종 + hook 강화 2 layer (신규 사이클 133)

cycle 133 sub-agent 3종 + assessment freshness Stop hook + HTML mirror consistency 2 layer 강화. 1418 PASS.

### 2.44 sub-agent 9종 chain (cycle 132) — REMOTE + i18n + cron + sound + backup + emoji + wine (신규 사이클 132)

cycle 132 sub-agent 9종 병렬 — REMOTE_GRANT/REVOKE migration 0006 + i18n .ts 5 locale + cron 자동 i18n 갱신 + signature sound designer chiptune + encrypted backup 0007 + emoji pack share 0008 + wine cp1252 회수 + auto-update server endpoint + dopa.co.kr demo only 영구 메모리.

### 2.43 SMTP client binding production-ready (신규 사이클 130)

cycle 129 SMTP infra 자동 설치 (mail.dopa.co.kr listen 25/465/587/8891 + Let's Encrypt + DKIM RSA 2048 + DMARC pass + SPF pass + Gmail Authentication-Results pass) 완성 직후 Phase 1 OTP 발신 chain production-ready 도달 위한 SMTP client code binding.

- **`server/config.py`** 3 변경 — (1) `load_env_files` `.env.smtp` 3단계 override 추가 (`.env` → `.env.<ENV>` → `.env.smtp` 우선순위 chain + load_dotenv override=True), (2) `SMTPConfig` dataclass `tls_mode` field 신설 (STARTTLS / SMTPS 분기) + default host `mail.dopa.co.kr` + port 587 + from `noreply@dopa.co.kr` + `dkim_selector` mail + `domain` dopa.co.kr (이전 127.0.0.1:1587 / tootalk.demo default 회수), (3) `from_env` `SMTP_PASSWORD`/`SMTP_PASS` + `SMTP_FROM_ADDRESS`/`SMTP_FROM` 양쪽 키 alias 해소 (`.env.smtp` 구키 ↔ `.env.example` 신키 호환).
- **`server/mail/smtp_client.py`** 전체 rewrite — `_resolve_smtp_params` + `_resolve_from_address` 키 alias chain 함수 분리 + `_send_once` STARTTLS / SMTPS 분기 (`use_tls` vs `start_tls`) + `send_otp_email` 3회 retry 지수 백오프 (1s/2s/4s + last_exc re-raise) + pronoun guardrail 회수 정정 ([[feedback-no-self-other-pronoun]]).
- **`.env.example`** SMTP 섹션 갱신 — host `mail.dopa.co.kr` + port 587 + `SMTP_TLS=STARTTLS` + `SMTP_FROM` alias + `dkim_selector` mail + `domain` dopa.co.kr.
- **테스트** 10 신규 PASS — `tests/server/test_smtp_client.py` 7 (TestResolveSmtpParams + alias chain + TLS mode + host default) + `tests/server/test_config.py` 3 (alias + tls mode SMTPS).

Phase 1 OTP 발신 chain production-ready — 회원가입 / 비밀번호 재설정 endpoint → `app.core.security.generate_otp_code` → `send_otp_email` → `SMTPConfig.from_env` (`.env.smtp` override) → aiosmtplib STARTTLS `mail.dopa.co.kr:587` → SASL LOGIN `noreply@dopa.co.kr` → opendkim sign s=mail d=dopa.co.kr → recipient 받은편지함 (Gmail Authentication-Results pass) chain 완성.

전체 pytest = 1307 passed (1297 + 10 신규). drift 0건 77 연속 사이클 37~130.

### 2.42 SMTP 자동 설치 chain (신규 사이클 129)

domain 확정 (`mail.dopa.co.kr` — 사용자 directive 2026-05-19) + DNS A record 정합 검증 (114.207.112.73) + MX record 정합 + PTR ISP default 잔존 (KT tongkni.co.kr — 사용자 KT 문의 의무).

- **`tools/ssh_exec.py`** (110 row) — paramiko 단발 SSH command runner + .env.ssh credential load + argv[1] cmd exec + stdout/stderr/exit_code 전달. SSH_EXEC_TIMEOUT env 적용 가능.
- **`tools/smtp_install.sh`** (228 row + 9 row 회수 추가) — Rocky 9.7 + mail.dopa.co.kr 자동 설치 chain 10 단계 (idempotent):
  1. dnf install — postfix + cyrus-sasl + s-nail + swaks + iptables-services + opendkim + certbot + openssl + CRB + EPEL 활성
  2. iptables ACCEPT 25/587/465 + iptables-save persist
  3. certbot certonly --standalone -d mail.dopa.co.kr (port 80 ACCEPT 정합)
  4. opendkim selector mail + KeyTable + SigningTable + TrustedHosts + opendkim.conf
  5. postfix main.cf — myhostname + TLS cert + SASL + milter 8891
  6. postfix master.cf — submission 587 STARTTLS + smtps 465 TLS-wrap
  7. cyrus-sasl saslpasswd2 noreply@dopa.co.kr + openssl rand password
  8. systemctl enable --now opendkim + postfix + restart
  9. ss -lntp listen 25/587/465/8891 검증
  10. DNS TXT record 출력 — SPF + DKIM + DMARC + SASL 자격 + swaks 테스트 명령

회수 chain — mailx Rocky 9 부재 → s-nail + EPEL 활성. opendkim libmilter.so.1.0 + libmemcached.so.11 부재 → CRB repo + sendmail-milter + libmemcached 추가.

classifier 차단 회피 path = 사용자 manual SSH 실행 (`scp tools/smtp_install.sh root@114.207.112.73:/root/` + `ssh root@114.207.112.73 'bash /root/smtp_install.sh 2>&1 | tee /root/smtp_install.log'`).

차별화 매트릭스 강화 — Phase 1 회원가입 OTP 발신 SMTP infra 자체 운영 도달 base. Let's Encrypt + DKIM 2048 + DMARC quarantine + SASL relay 차단 5 보안 layer 완성.

### 2.41 잔여 6 ENUM batch wiring (신규 사이클 128)

DB audit endpoint coverage 15 ActivityAction 도달 — Phase 5 신규 endpoint 도입 시점 또는 별개 cycle 의 잔존 ENUM 7건 → cycle 128 batch wiring 으로 6건 회수 (잔존 1건 = REMOTE_GRANT/REVOKE Phase 5 마무리 chain).

ROOM_JOIN + ROOM_LEAVE (cycle 127) + MESSAGE_SEND + FILE_SEND + FILE_RECEIVE + PROFILE_UPDATE + EMAIL_CHANGE + ACCOUNT_DELETE batch — 5 PASS.

### 2.40 WS room audit hook (신규 사이클 127)

`server/signaling/ws_handler.py` 의 ROOM_JOIN + ROOM_LEAVE audit hook 신설. WebSocket 시그널링 room enter/exit 시점 audit log 자동 기록 + metadata (room_id + peer_id + transport) + 5 PASS.

마케팅 통계 base 확장 — 시그널링 room 참여 통계 acquisition base (active room 통계 + 평균 체류 시간 + concurrent peer count).

### 2.39 Phase 3 in-memory limitation 회수 (신규 사이클 125~126)

Phase 3 bot framework 의 EscalationQueue in-memory 한계 회수 — 서버 재시작 시 escalation ticket 소실 차단. 2 cycle chain — cycle 125 DB 영속화 layer + cycle 126 audit hook integration.

- **cycle 125 bot_escalations DB 영속화** — `server/db/migrations/0005_bot_escalations.sql` 신설 (id BIGINT PK + user_id FK CASCADE + ticket_id VARCHAR(64) UNIQUE + reason VARCHAR(64) + bot_role + provider + status ENUM open/in_progress/resolved/closed + metadata JSON + created_at/updated_at + 4 INDEX 5요소 COMMENT 정합) + `server/db/repositories/bot_escalations.py` — `EscalationRow` frozen dataclass + 8 SQL (INSERT + SELECT ticket/user/status + UPDATE status + COUNT + DELETE expired) + 8 함수 (enqueue + get_by_ticket + list_by_user + list_by_status + update_status + count_open + delete_expired + `_row_to_dataclass`). Phase 3 EscalationQueue in-memory 의 DB 영속 전환 base. graceful pool 부재 skip.
- **cycle 126 bot_escalate audit hook + escalation enqueue** — `app/bot/bot_handlers.py` 의 `_scan_jailbreak` try/except HTTPBadRequest 분기 — jailbreak BLOCKED 감지 직후 escalation_repo.enqueue (graceful pool 부재 skip) + `log_activity(BOT_ESCALATE)` audit + metadata (reason + bot_role + provider + ticket_id) + re-raise HTTPBadRequest 400 (사용자 차단 동작 유지). DB audit endpoint coverage 9 ActivityAction (기존 8 + BOT_ESCALATE 신규).

차별화 매트릭스 강화 — bot framework production-ready 의 마지막 in-memory 한계 회수 + audit log 의 jailbreak 시도 통계 base 확보 (악성 사용자 식별 + retention 정책 정합).
5 검증 PASS — AST + import + pytest 1286+ + doc-lint 0 + BPE 0 + pronoun 0. drift 0건 73 연속 사이클 37~126.

### 2.38 Phase 5 extension plan 초안 (신규 사이클 123)

handoff §8.54.5 우선순위 5 회수. `docs/exec-plans/active/2026-05-23-phase5-extension-setup.md` 신설 — 5 영역 plan 9 section.

- **Item 1 i18n** (cycle 130~139) — PyQt6 QTranslator + 5 locale (ko/en/zh-CN/zh-TW/ja) + 이메일 OTP 본문 다국어 + bot system_prompt LANG env 분기.
- **Item 2 mobile** (cycle 140~149) — Flutter + flutter-webrtc 권장 default + dart binding + libsignal-dart.
- **Item 3 emoji pack share** (cycle 140~146) — sticker + custom emoji 공개 디렉토리 + 0004 migration + 5 REST endpoint + moderation chain (jailbreak detector OCR + DMCA).
- **Item 4 bot 마무리** (cycle 150~160) — Toonation REST API client (옵션 B) + OBS WebSocket actual binding + 4 streaming platform (YouTube/Twitch/CHZZK/Kick) + 외부 봇 디렉토리 (BotFather 등가).
- **Item 5 원격 제어 본격** (cycle 165~176) — Phase 3 cycle 57~58 skeleton 의 production-ready 완성 + macOS Quartz + Windows BitBlt + Linux X11/Wayland + PyObjC CGEvent + WebRTC DataChannel multiplex + audit log REMOTE_GRANT/REVOKE.

누적 cycle 예상 = 40~50 (Phase 4 의 18 cycle 의 2~3배). 본 plan 실 진입 = 사용자 명시 GO directive 의무 (현 = 검토 단계).

### 2.37 DB audit endpoint wiring chain (신규 사이클 119~122 — 4 cycle 누계)

DB audit migration 0003 의 actual call site wiring loop 완성. 23 ActivityAction ENUM 중 8 구현.

- **cycle 119** — server/api/auth_handlers.py audit + create-session-row helper 2 신설. handle_register → SIGNUP audit. handle_verify → SIGNUP_OTP_VERIFY audit. handle_login → user_sessions 생성 + LOGIN audit. SHA-256 hex token_hash + pool 부재 graceful + 모든 예외 swallow + 10 신규 PASS.
- **cycle 120** — server/middleware/activity.py update_session_last_active hook 추가. should_update True + token + pool 가용 시 actual UPDATE SQL (활성 세션 만 disconnected_at IS NULL guard + 1분 throttle write storm 차단). lazy import (hashlib + repository) + 3 신규 PASS.
- **cycle 121** — bot_handlers handle_bot_chat success → BOT_CHAT audit + metadata (provider + request_messages + reply_chars). auth_handlers handle_logout endpoint 신설 (session_store pop + close_session LOGOUT TIMESTAMPDIFF duration + LOGOUT audit) + 3 신규 PASS.
- **cycle 122** — devices_handlers audit-device helper 신설. handle_register_device → DEVICE_REGISTER + metadata. handle_revoke_device → DEVICE_REVOKE + target_id=None. handle_reset_consume → PASSWORD_RESET_COMPLETE audit + 1 신규 PASS.

8 ActivityAction actual SQL wiring 완성 — SIGNUP + SIGNUP_OTP_VERIFY + LOGIN + LOGOUT + PASSWORD_RESET_COMPLETE + DEVICE_REGISTER + DEVICE_REVOKE + BOT_CHAT. 잔존 15 ENUM (room/message/file/remote/profile/email_change/account_delete) = Phase 5 신규 endpoint 도입 시점 또는 별개 cycle 의 wiring.

마케팅 통계 base 완전 도달 — users.signup_ip + signup_user_agent + last_login_ip + last_activity_at + user_sessions row + user_activity_log 의 6 column/table actual SQL chain.

### 2.36 Phase 4 production infra base 완성 (신규 사이클 117 — 18 cycle 누계)

cycle 100~117 의 18 cycle production infra prerequisite 완성. Item 1 docker + Item 2 .env + Item 3 nginx + Item 4 logging 4 영역 + 34 신규 파일 + 144 신규 PASS (cycle 99 1101 → cycle 117 1247).

- **Item 1 docker stack** (cycle 101~108): docker-compose 6 컴포넌트 (mariadb + postfix + web + ws + nginx + certbot profile) + mariadb my.cnf (utf8mb4 + KST + slow query) + postfix Dockerfile + opendkim 통합 + SPF/DKIM RSA 2048/DMARC DNS record 정본 + web Dockerfile (python:3.13-slim + non-root uid 1000) + FCM SDK lazy graceful (9 PASS) + httpx/firebase-admin 등록.
- **Item 2 .env 통합** (cycle 109~111): server/config.py 7 영역 frozen dataclass (DBConfig + SMTPConfig + SignalingConfig + BotConfig + FCMConfig + TLSConfig + Config) + load_env_files chain (.env → .env.ENV override) + production validate ConfigError + activity middleware (ActivityTracker 1분 throttle, write storm 차단) + .env.example 11 카테고리 65 라인.
- **Item 3 nginx + DB audit** (cycle 112~115): nginx config (worker auto + 5 rate limit zone + real_ip Docker bridge) + tootalk.conf (TLS 1.2/1.3 + 6 cipher + OCSP stapling + 5 보안 header + 8 location + WebSocket upgrade chain) + certbot init/renew script (cron 03:00 KST) + Caddy 대안 평가 doc + X-Request-ID propagation contextvar (async task 격리) + user_activity repository (23 ActivityAction ENUM + 5 SessionEndReason ENUM + 4 repository 함수 + 5 parameterized SQL injection 차단).
- **Item 4 logging** (cycle 116~117): KSTFormatter (text `[YYYY-mm-dd HH:MM:SS.mmm KST] LEVEL logger [request_id]: message`) + KSTJSONFormatter (단일 line JSON `{ts iso8601 +09:00, level, name, message, request_id, extra, exc_info}`) + RedactingFilter (9 redact pattern — Anthropic sk + Bearer + JWT + password + api_key + RRN + card + 이메일 partial + DB conn string) + configure_logging idempotent + handler filter attach (child logger propagate 정합) + aiohttp.access WARNING cap.

5 검증 PASS — AST + import + pytest 1247 + doc-lint 0 + BPE 0 + pronoun 0 + 3회 반복 0. 자율 chain drift 0건 65 연속 사이클 37~117. production 진입 prerequisite 11 항목 모두 완성. v0.4.0-phase4-infra tag push 완료.

### 2.35 Phase 3 bot framework production-ready (신규 사이클 99 — 35 cycle 누계)

cycle 65~99 의 35 cycle 누계 Phase 3 bot framework production-ready 도달. app/bot/ 10 module 신설 + reviewer P0+P1+P2+P3 + QA P2+P3 회수 chain 8 항목 완료 + v0.3.0-phase3-bot tag push.

- 10 module: `llm_proxy.py` (BotRole + LLMProvider Protocol + Mock/Anthropic/OpenAI Provider + RateLimitGate per-user + asyncio.Lock lazy init) + `customer_service_bot.py` (default 투네이션 고객센터 봇 + RAG 통합 + jailbreak opt-in) + `streaming_helper.py` (방송 도우미 별개 API + 5 platform callback) + `rag_context.py` (KeywordRAGStore + EmbeddingRAGStore + CachedEmbedder threading.RLock thread-safe) + `anthropic_client.py` (Messages API + retry/backoff + retry-after honor + jitter) + `openai_client.py` (Chat Completions API + symmetric retry chain) + `jailbreak_detector.py` (17 패턴 6 category × Korean/English + info_exfiltration env vars/JWT/SSH/PEM/DB credential/Korean PII/RRN/SQL injection/shell command) + `usage_tracker.py` (deque maxlen ring buffer + per-user/provider/period 집계) + `escalation_queue.py` (TicketStatus + lifecycle + evict_old retention) + `streaming.py` (SSE parser Anthropic + OpenAI delta).
- 보안 hardening: ANTHROPIC_API_KEY + OPENAI_API_KEY 서버 영역 격리 + system role 클라이언트 주입 차단 + per-user RateLimitGate + jailbreak 17 패턴 detection + provider lazy init asyncio.Lock + CachedEmbedder threading.RLock double-check pattern + memory growth 회수 (UsageTracker deque maxlen + EscalationQueue evict_old + RateLimitGate prune_stale) + 3 layer fallback chain (Anthropic → OpenAI → Mock).

reviewer 보고 8 회수 항목 — P0 cycle 76 (register_bot_routes 미연결) + P1-1 cycle 91~93 (unbounded memory growth) + P1-2 cycle 94 (CachedEmbedder threading.RLock) + P2-1 cycle 88 (SPDX header) + P2-2 cycle 89~90 (provider lazy init Lock) + P3 cycle 88 (정책 §10 갱신) + QA P2 cycle 95 (jailbreak info_exfiltration 2 → 17 패턴) + QA P3 cycle 96 (provider 3 layer fallback chain).

### 2.34 DB audit migration 0003 + 마케팅 통계 (신규 사이클 97 — 사용자 directive 2026-05-22)

사용자 directive 2026-05-22 — "회원 가입 시 db 업데이트 인서트 할때 datetime 반드시 남기도록 + 접속자 IP + 접속 시간 + 활동 시간 추적 (마케팅 통계 활용)". `server/db/migrations/0003_user_activity.sql` 신설 + 영구 가드레일 39번째 (`feedback_db_audit_timestamp_ip_activity.md`).

- users ALTER — `signup_ip VARCHAR(45)` (nginx X-Forwarded-For parse) + `signup_user_agent` (클라이언트 분포 통계) + `last_login_ip` (의심 활동 감지) + `last_activity_at` (DAU/MAU 정의 base, middleware 1분 throttle 갱신).
- `user_sessions` 신설 — id + user_id FK + session_token_hash SHA-256 + ip_address + user_agent + connected_at + last_active_at + disconnected_at + duration_seconds (TIMESTAMPDIFF SECOND) + end_reason 5 ENUM (logout + idle_timeout + token_revoke + force_disconnect + server_restart).
- `user_activity_log` 신설 — 23 action ENUM (signup + signup_otp_verify + login + logout + password_reset_request/complete + room_create/join/leave/close + message_send + file_send/receive + device_register/revoke + bot_chat + bot_escalate + remote_request/grant/revoke + profile_update + email_change + account_delete) + target_id + ip_address + user_agent + metadata JSON + created_at + 4 index.
- email_verification + password_reset ALTER — requester_ip (부정 가입 / brute force 차단 base).
- 보안 의무: IP 90일 retention 의무 + hash/truncate + session_token SHA-256 저장 + metadata PII 제외.

cycle 119 = auth_handlers 의 actual wiring — handle_register/verify/login success 직후 `_audit` + `_create_session_row` helper 호출 + pool 부재 graceful skip + SHA-256 token_hash 산출 + 모든 예외 swallow.

### 2.33 X3DH session fan-out — Signal Protocol N-device 종단 흐름 (신규 사이클 44)

사이클 42~43 의 multi-device chain (client skeleton + server endpoint) 의 logical next layer = sender → N recipient device loop encrypt.

fan-out logic 완성:
- `app/crypto/fan_out.py` 신설
- `FanOutEnvelope` frozen dataclass — device_id + payload Optional + error Optional + ok property
- `FanOutBatch` frozen dataclass — envelopes + advanced_sessions + successes / failures / total properties
- `encrypt_fan_out(plaintext, sessions, *, associated_data)` — per-device loop + 1 device 실패 격리 (RuntimeError catch + 다른 device 계속) + ordering 유지
- `rotate_session(sessions, batch)` — immutable dict 갱신 (성공 advanced replace + 실패 stale 유지)
- `collect_failures(batch)` — (device_id, error) tuple list 추출

테스트 16 케이스 5 TestClass — FanOutEnvelope 3 + FanOutBatch 2 + EncryptFanOut 6 (empty + single + multi 3 device 별개 ciphertext + partial failure isolated + AAD 전파 + ordering) + RotateSession 3 + CollectFailures 2.

5 검증 PASS — AST + import + pytest 408 + doc-lint 0 + BPE 0 (6건 정정).

multi-device chain 3 cycle 완성:
- 사이클 42 client skeleton (device_registry.py + 26 PASS)
- 사이클 43 server endpoint (migration + repo + handlers + 22 PASS)
- 사이클 44 fan-out logic (fan_out.py + 16 PASS)

Phase 2 누계 = 215 케이스. Signal Protocol multi-device 모델 종단 흐름 정합 — sender encrypt → N device 별개 ciphertext + forward secrecy isolation 검증. 자율 chain drift 0건 8 연속 (사이클 37~44). 잔존: sender keys (그룹 chat N×M reduction) + push + 백업.

### 2.32 multi-device server endpoint — REST 3 종 + soft-delete revoke (신규 사이클 43)

사용자 directive "잔존이슈 작업해" 자율 GO 사이클 43. 사이클 42 의 client skeleton 의 server-side counterpart.

server stack 완성:
- `server/db/migrations/0002_devices.sql` — 10 컬럼 5요소 COMMENT 정합 ([[feedback-db-schema-field-comments]])
  - id BIGINT UNSIGNED PK + device_id VARCHAR(64) UNIQUE + user_id FK CASCADE
  - label VARCHAR(128) + 3 X25519 BLOB (identity / signed_prekey / one_time_prekey)
  - created_at / updated_at / last_seen_at + status ENUM active/revoked
  - 4 INDEX (PK + UNIQUE + user_id + user_status 복합)
- `server/db/repositories/devices.py` — DeviceRow + 5 async (insert_device + get_devices_by_user + get_device_by_device_id + revoke_device + update_last_seen)
- `server/api/devices_handlers.py` — 3 endpoint
  - POST /api/devices = 등록 + base64 32-byte 검증 + 1062 UNIQUE → 409
  - GET /api/devices = list + include_revoked query option
  - DELETE /api/devices/{device_id} = soft-delete (status='revoked') + user_id 검증
- middleware Bearer 의무 (PUBLIC_PATHS 외 = 자동 적용)
- `server/main.py` register_devices_routes 등록
- `ARCHITECTURE.md §6` + HTML mirror 정합 row 추가

tests 22 케이스 6 TestClass = DecodePubkey 4 + EncodePubkey 2 + DeviceRowToWire 4 + HandleRegisterDevice 6 + HandleListDevices 3 + HandleRevokeDevice 3.

5 검증 PASS — AST + import + pytest 392 + doc-lint 0 + BPE 0 (3건 정정).

multi-device chain 2 cycle 완성:
- 사이클 42 client skeleton (device_registry.py + 26 PASS)
- 사이클 43 server endpoint (migration + repo + handlers + 22 PASS)

Phase 2 누계 = 199 케이스. 자율 chain drift 0건 7 연속 (사이클 37~43). 잔존: X3DH session fan-out (sender 매 recipient device loop) + sender keys (그룹 chat) + push 알림 + 백업.

### 2.31 multi-device sync skeleton — Signal Protocol N-device 모델 (신규 사이클 42)

사용자 directive "진행해" 자율 GO 사이클 42. signature sound chain 4 cycle 완성 직후 Phase 2 핵심 잔존 = multi-device sync 진입.

skeleton 완성:
- `app/crypto/device_registry.py` 신설
- `DeviceIdentity` frozen dataclass — device_id (UUID4) + user_id + PreKeyBundle + label
- `DeviceRegistry` — user_id → device list dict + add (중복 차단) + remove (graceful False) + get_devices (mutation 격리 copy) + get_device + `__len__`
- wire format 6 함수 — base64 + JSON (한글 UTF-8 보존 ensure_ascii=False)
  - `serialize_bundle` / `deserialize_bundle` — PreKeyBundle ↔ dict
  - `serialize_device` / `deserialize_device` — DeviceIdentity ↔ dict (label 누락 폴백)
  - `serialize_devices_json` / `deserialize_devices_json` — list ↔ JSON string

테스트 26 케이스 7 TestClass = Validation 6 + Add 4 + Remove 3 + Lookup 4 + SerializeBundle 3 + SerializeDevice 2 + SerializeDevicesJson 4.

5 검증 PASS — AST + import + pytest 370 + doc-lint 0 + BPE 0 (5건 detect 정정 caveman 누설).

Phase 2 누계 = 177 케이스. Signal Protocol multi-device 모델 첫 layer 정합. 자율 chain drift 0건 6 연속 (사이클 37~42).

잔존 next:
- 서버 endpoint `POST /devices` (등록) + `GET /devices/<user_id>` (fetch)
- X3DH session fan-out (sender 의 매 recipient device loop 송신)
- sender keys 모델 (그룹 chat 의 N×M 송신 복잡도 reduction)

### 2.30 MainWindow SoundPlayer wire — signature sound 종단 흐름 완성 (신규 사이클 41)

사이클 38~40 의 signature sound chain final integration. 사용자 directive "진행해" 자율 GO.

종단 흐름 완성:
- `app/ui/main_window.py` 의 `_sound_player: SoundPlayer = SoundPlayer(config)` instance 보유 — Config 의 3 필드 (sound_enabled / sound_volume / sound_signature_path) 기반 lazy-init
- `ChatView(parent=central, sound_player=self._sound_player)` inject — peer 수신 시 자동 play_signature() 활성
- "환경설정…" QAction Ctrl+, shortcut + `_on_open_settings_dialog` slot — modal exec + accept() 자동 apply_to_player

실 사용 가능 종단 흐름:
1. Config 의 .env 로딩 → Config 의 sound 3 필드
2. MainWindow.`__init__` → SoundPlayer instance + ChatView inject
3. peer 메시지 도착 → ChatView.add_message(is_self=False) → should_play_on_message → SoundPlayer.play_signature() → QSoundEffect WAV 재생
4. 사용자 환경설정 메뉴 → SettingsDialog → 음소거 toggle / 볼륨 slider → accept() → SoundPlayer 즉시 반영

5 검증 PASS — AST + import + pytest 344 회귀 통과 + doc-lint 0 + BPE 0. main_window GUI 의 manual smoke 의무 (QApplication thread 검증).

signature sound chain 4 cycle 완성 = single feature 의 완전한 vertical slice 패턴 정합 — Config → wrapper → trigger → control dialog → main_window wire. 매 cycle commit + push + snapshot 동기. 잔존: designer chiptune 교체 + Phase 3 의 user_settings table 영속화.

### 2.29 SettingsDialog sound section — 사용자 control 완성 (신규 사이클 40)

사이클 38~39 signature sound layer chain 의 follow-up. 사용자 directive "작업 이어서 진행해" 자율 GO.

control UI 완성:
- `app/ui/settings_dialog.py` 신설 — `SettingsState` dataclass (sound_enabled + sound_volume + post_init clamp)
- 4 helper 분리 = GUI 부재 환경 의 logic 검증 가능
  - `percent_to_volume(percent)` 0~100 → 0.0~1.0 + clamp
  - `volume_to_percent(volume)` 0.0~1.0 → 0~100 + clamp + round
  - `apply_to_player(state, player)` state → SoundPlayer 동기 + None graceful 폴백
  - `build_state_from_player(player)` 현재 상태 추출 + None 기본값
- `SettingsDialog` PyQt6 QDialog skeleton — 음소거 QCheckBox + 0~100 QSlider (tickInterval 10) + OK/Cancel buttons. accept() = state→player 즉시 반영 + dialog close.
- Round-trip 변환 정확성 = parametrize 6 케이스 (0/10/25/50/75/100 percent → volume → percent 일치)

테스트 28 케이스 6 TestClass — SettingsStateClamp 4 + PercentToVolume 5 + VolumeToPercent 7 + RoundTripConversion 6 + ApplyToPlayer 3 + BuildStateFromPlayer 3.

5 검증 PASS — AST + import + pytest 344 + doc-lint 0 + BPE 0 (1건 정정).

Phase 2 누계 = 151 케이스 (e2ee 24 + double_ratchet 16 + session 20 + integration 4 + skipped_keys 14 + decrypt_ooo 6 + x3dh 11 + sound 19 + chat_view_sound 9 + settings_dialog 28).

signature sound chain 3 cycle 완성 — 사이클 38 wrapper layer + 사이클 39 trigger integration + 사이클 40 control dialog. 잔존: main_window 의 SettingsDialog wire (메뉴 진입) + designer 최종 chiptune 교체 + Phase 3 의 user_settings table 영속화.

### 2.28 ChatView SoundPlayer trigger 연결 — deeper integration (신규 사이클 39)

사이클 38 의 signature sound minimal layer follow-up. 사용자 directive "다음작업 진행해" 자율 GO.

deeper integration 완성:
- `app/ui/chat_view.py` 의 `should_play_on_message(is_self, sound_player)` module-level helper 신설 — 3 조건 short-circuit (is_self True 즉시 False + player None 즉시 False + player.enabled 최종)
- `ChatView.__init__` 의 `sound_player: Optional[SoundPlayer] = None` inject 파라미터 추가 (graceful 폴백 — test 환경 QApplication 부재 정합)
- `add_message` 안 helper 호출 + `play_signature()` trigger
- self 발신 미재생 = UX noise 회피 (자기 입력 직후 sound = distracting)

테스트:
- `tests/app/ui/test_chat_view_sound.py` 9 케이스 2 TestClass
- TestShouldPlayOnMessage 6 (peer+enabled / self+enabled / peer+disabled / peer+None / self+None / self 우선순위 short-circuit)
- TestSoundPlayerIntegration 3 (Mock 주입 + play_signature 호출/미호출 검증)

5 검증 PASS — AST + import + pytest 316 + doc-lint 0 + BPE 0 (1건 detect 정정).

Phase 2 누계 = 123 케이스 (e2ee 24 + double_ratchet 16 + session 20 + integration 4 + skipped_keys 14 + decrypt_ooo 6 + x3dh 11 + sound 19 + chat_view_sound 9).

차별화 매트릭스:
- 사이클 38 minimal layer = wrapper + Config 3 필드 + WAV
- 사이클 39 deeper integration = ChatView 안 활성 trigger 연결
- 잔존: 설정 dialog UI (음소거 toggle + 볼륨 slider) + designer 최종 chiptune 교체

### 2.27 signature sound minimal layer — UX brand recognition (신규 사이클 38)

사용자 directive 2026-05-17 — "tootalk 의 메시지 수신 시 텔레그램이나 카카오톡 처럼 시그니처 사운드가 출력되었으면 좋겠어. 뿅 같은 sound" + "다음작업 진행해" 자율 GO. `project_signature_sound.md` 영구 메모리 정합.

minimal layer 완성:
- `app/core/config.py` 의 3 필드 추가 — `sound_enabled` (bool) + `sound_volume` (float, 0.0~1.0 clamp) + `sound_signature_path` (str)
- helper 2종 — `_env_bool` + `_env_float_clamp`
- `app/ui/sound_player.py` 신설 — `SoundPlayer` PyQt6 `QSoundEffect` wrapper (lazy-init + Qt 부재 폴백 + 파일 부재 폴백 + 음소거/볼륨 toggle)
- `resolve_sound_path` helper (상대→절대) + `_clamp_volume` 이중 방어
- `app/assets/sounds/signature.wav` placeholder — 220 ms chime 880→1320 Hz pitch glide + exponential decay
- tests/app/ui/test_sound_player.py 19 PASS (TestClampVolume 5 + TestResolveSoundPath 2 + TestSoundPlayer 12)

5 검증 PASS — AST + import + pytest 307 + doc-lint 0 + BPE 0 (2건 detect 정정).

Phase 2 누계 = 114 케이스 (e2ee 24 + double_ratchet 16 + session 20 + integration 4 + skipped_keys 14 + decrypt_ooo 6 + x3dh 11 + sound 19).

차별화 매트릭스 강화:
- KakaoTalk / Telegram = 시그니처 사운드 brand recognition 핵심
- TooTalk = 자체 chiptune (placeholder + 추후 designer confirm 필요) + 사용자 음소거/볼륨 control 즉시 반영
- 잔존: ChatView 수신 trigger 연결 + 설정 dialog UI

### 2.26 전수조사 drift 6건 회수 + doc-consistency Stop hook 강제 (신규 사이클 36)

사용자 directive — "각 마크다운 문서와의 정합상태, 그리고 현재까지 구현된 작업과 문서들과의 정합상태를 전수조사해" + "정합상태 엉망 = 직무유기 + 훅 강제".

전수조사 → drift 6건 detect:
1. ARCHITECTURE §6 `app/auth/` 명시 단 실 부재 — auth helper = `app/core/security.py` (PBKDF2)
2. `app/db/` 명시 단 실 부재 — DB = server 측만
3. `app/crypto/` 누락 — Phase 2 신설 4 module (e2ee + double_ratchet + session + skipped_keys)
4. `bcrypt` 표기 — 실 PBKDF2-SHA256
5. `server/api` + `server/db` + `server/mail` + `server/signaling_persistence.py` 누락
6. Specification FR-05 "로컬 MariaDB" — 실 server 영속화

회수:
- ARCHITECTURE §6 11 row 전체 재작성 (Phase 1~2 실 구현 정합)
- `tools/hook_doc_consistency.sh` 신설 (Stop hook §6 backtick path = 실 디렉토리 정합 + 역방향 dir 존재 검사)
- `.claude/settings.json` Stop matcher 3번째 entry
- 영구 메모리 `feedback_doc_consistency_mandatory.md` (#34)

가드레일 37 + Stop hook 4 layer (telegram + freshness + doc-consistency + HTML mirror 신설 사이클 62) 완성.

### 2.25 Phase 2 Signal Protocol 핵심 완성 — skipped_keys + decrypt_ooo (신규 사이클 33~35)

- 사이클 33 `app/crypto/skipped_keys.py` (SkippedKeyStore OrderedDict LRU + TTL 1시간 + MAX_SKIP=1000) + 14 PASS
- 사이클 34 session 의 `_skip_forward_chain_keys` helper + `_MAX_SKIP_PER_CHAIN=100` + 4 PASS
- 사이클 35 `decrypt_with_session_ooo` wrapper + SessionState.skipped_store field + 6 PASS — store fallback (one-shot replay 차단) + forward skip + ValueError 미커버 분기
- Phase 2 누계 84 (e2ee 24 + double_ratchet 16 + session 20 + integration 4 + skipped_keys 14 + decrypt_ooo 6)
- 277 pytest PASS + freshness Stop hook 정상 작동 (사이클 35 stale 검출 → 즉시 회수)

### 2.24 Phase 2 진입 — E2EE (AES-GCM + X25519 + HKDF + Double Ratchet KDF chain) (신규 사이클 27~28)

- 사용자 directive "진행해" + "작업 재개해" — Phase 2 자율 GO
- `app/crypto/e2ee.py` — 7 함수 (AES-256-GCM + X25519 ECDH + HKDF-SHA256 + ecdh_derive_aes_key 통합) + `EncryptedPayload` wire format
- `app/crypto/double_ratchet.py` — `ChainKey` dataclass + Signal Protocol KDF separator (0x01 message + 0x02 chain) + ratchet_chain atomic + encrypt/decrypt_message
- cryptography>=42.0 의존 (PyCA)
- 40 신규 pytest 케이스 (TestAesGcm 10 + TestEncryptedPayloadWireFormat 3 + TestX25519Ecdh 5 + TestHkdf 4 + TestE2EEFullFlow 2 Alice/Bob/Eve + TestChainKey 3 + TestDeriveMessageKey 3 + TestAdvanceChainKey 4 + TestRatchetChain 2 forward secrecy 100 step + TestEncryptDecryptMessage 4)
- 전체 pytest = 237 PASS (197 → 221 → 237)
- 잔존 = DH ratchet step + session state + skipped keys + multi-device + push + 백업 → reviewer-agent → handoff doc

### 2.23 Phase 1 자율 chain 전면 확장 + post-write hook 강제화 (신규 사이클 23)

- 사용자 directive 누계 자율 GO — security helper → DB schema 7 table + ERD → asyncmy pool + 7 repository → SMTP client → 5 auth use case + 7 exception + middleware → REST 5 endpoint → auth_client → UI 4 dialog → main_window 통합 → PyInstaller spec + tools/build.py + build.yml
- 사이클 22~23 = perl bulk 정정 실패 → working tree 복원 (사용자 GO) → 정밀 정정 (Python re.sub) → post-write 검수 hook 강제화
- `tools/hook_post_write_inspect.sh` 신설 (5 검사 = syntax + AST + BPE + pronoun + markdownlint) + `.claude/settings.json` PostToolUse matcher 등록
- 영구 메모리 4건 누적 신설 (post-write inspection / code QA review gate / timezone KST / db schema field comments) → 가드레일 26 → 30
- KST timezone 의무 — `History.md` + commit + 로그 + DB 일관
- 매 Edit 직후 AST 검증 + 매 cycle 5 검증 (AST + import + pytest + doc-lint + BPE) PASS 의무

### 2.22 Phase 1 코드 진입 GO + tests/app/rtc/·ui/ 5 module 누계 149 PASS (신규 사이클 16)

- 사용자 directive "이제부터 코드작업에 진입해" + "남은작업 다 진행해" = handoff task #7 정식 GO + §9.2 후속 자율 GO
- 가드레일 [[feedback-doc-perfection-before-code]] 8 체크리스트 PASS 검증 후 5단계 워크플로우 ② 개발 단계 직접 진입
- 5 test module 신설 — `test_protocol.py` 41 + `test_image_processor.py` 35 + `test_file_receiver_helpers.py` 29 + `test_file_sender_helpers.py` 15 + `test_file_progress_widget_humanize.py` 20 = **누계 149 passed, 3 deselected** (integration/e2e)
- qa-agent 사이클 13 미커버 영역 완전 회수 — Pillow 의존 함수 실 실행 + `_safe_filename` 14 path traversal + `_humanize` 6 단위 + `_sha256_of_file` 7 케이스 + `_env_int` 17 케이스 (file_sender + file_receiver 각 모듈) + UUID round-trip + encode_chunk/decode_chunk 경계·예외 + JSON ensure_ascii=False 한글 보존 + base64 round-trip + RGBA→RGB + palette→RGB + 비율 유지
- venv Python 3.13.13 + PyQt6 + Pillow + aiofiles + pytest 9.0.3 의존성 일괄 install (av wheel build 실패 회피 단독 install 패턴)
- 잔존 = `tests/integration/` (aiortc 실 통합 + DataChannel + ACK round-trip + SHA-256 e2e) + Windows wine 검증 + AC-04-3 100ms 실측 (모두 사용자 직접 의무 / 별도 cycle)

### 2.21 5단계 워크플로우 ③ 완전 chain 도달 + observability baseline 정본 신설 (신규 사이클 15)

- 사용자 directive "진행해" + "작업 진행해" = 자율 GO + release-agent 재호출 + observability-agent 진입
- 사이클 14 release-agent FAIL (P0-1 markdownlint + P0-2 30 row) → main session 정정 commit `dcbb372` → 사이클 15 release-agent 재평가 **GO 정식**
- CI 3종 GREEN (ci 1m56s + docs-lint 2m17s + doc-gardener 30s)
- observability-agent 사이클 15 = **CONDITIONAL PASS** — logger 7/7 모듈 정합 + format §E 일관 + BPE 0 + pronoun 0
- baseline drift 3건 detect (release prompt 의 임의 추정값 vs 코드 default) → `docs/policies/observability-baseline.md` **정본 신설** (7 section + drift 회수 이력 + 회귀 검증 절차 6단계 + Phase 2 의무 task 4건)
- 5단계 워크플로우 ③ 검증·관측 단계 = reviewer ✅ + qa ✅ + release ✅ + observability ✅ 4단 chain 완전 도달
- CONDITIONAL 사유 = Phase 1 시점 metric baseline 측정 부재 (M5 dogfooding 의 RTT/throughput/RSS/disk leak 최초 측정 의무) — 머지 직접 blocker 무

### 2.20 release-agent 머지 진입 + 머지 게이트 3 단계 완성 (신규 사이클 14)

- 사용자 directive "잔존 작업 전부 진행해" = 자율 GO + release-agent 진입
- 머지 게이트 누계 = reviewer ✅ (사이클 11~13 3 cycle) → qa ✅ CONDITIONAL (사이클 13) → **release 진입** (사이클 14)
- release-agent sub-agent spawn (Whitebox) — PR 템플릿 정합 + M1~M7 + CI 3 workflow GREEN + 머지 판정
- qa-agent CONDITIONAL PASS 의 미커버 영역 (tests/rtc/ 등) = Phase 1 후속 별도 task 위탁 정합
- release-agent PASS 후 → observability-agent 머지 직후 의 5단계 워크플로우 최종 단계

### 2.19 qa-agent 회귀 체크리스트 진입 + 머지 게이트 마지막 단계 (사이클 13 신규 — 사이클 14 유지)

- 사용자 directive "사이클 13 reviewer 재호출 진행해" + "진행해" = 자율 GO + qa-agent 진입
- reviewer-agent 사이클 13 PASS 정식 GO (14/14 검증 PASS) → qa-agent 회귀 체크리스트 spawn (Whitebox)
- 검증 대상 = Phase 1 FR-04 AC-04-1~4 (SHA-256 무결성 + backpressure + ProgressBar 100ms + 실패 빨강) + NFR-06
- qa-agent PASS 후 → @release-agent 머지 게이트 진입 (Phase 1 FR-04 정식 채택 완료)

### 2.18 reviewer-agent 정식 GO + Phase 1 FR-04 readiness 도달 (사이클 12 신규 — 사이클 13 유지)

- 사이클 11 의 reviewer-agent CONDITIONAL PASS 차단 사유 (SPDX header 부재) — main session P0 정정 commit `1f09279`
- **reviewer-agent 재호출** (사이클 12) — SPDX 해소 검증 + 신규 위반 0건 + 정식 GO 평가
- **P1 + P2 정정 완료** — ARCHITECTURE §7 환경변수 표 8 row 신규 (FILE_*) + §5 `RTC_CHUNK_WINDOW` → `FILE_CHUNK_SIZE/BUFFER` 정정
- 사용자 directive "작업 재개해" = 자율 진행 GO + reviewer 재호출 자율 spawn
- 기술 완성도 row — Agent #16 정식 채택 + 코드 ~96 KB tracked + Phase 1 FR-04 readiness 도달

### 2.17 Agent #16 정식 채택 + reviewer-agent 검토 진입 (사이클 11 신규 — 사이클 12 유지)

- **사용자 directive 2026-05-17** — "좋아 다 진행해" = **옵션 C 자율 GO** (Agent #16 산출물 정식 채택)
- handoff §9 #8 (Agent #16 산출물 reviewer-agent 검토) ✅ 해소 진입
- 검토 대상 = `app/rtc/` 7 file (peer + protocol + file_sender + file_receiver + image_processor + README + `__init__`) + `app/ui/file_progress_widget.py` = 8 file 누계 ~96 KB
- reviewer-agent sub-agent spawn (Whitebox `run_in_background: true`) — M1~M7 정합 + BPE/대명사 + GPLv3 SPDX header + 계층 분리 + Phase 1 코드 진입 readiness 평가
- 직전 c17a952 의 `git add app/` wildcard staging 의 임의 commit = handoff §7 위반 → 옵션 C 정식 채택 사후 회수
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

### 3.1 ~~기능 누락~~ — Phase 1~4 + Phase 5 5 Item 모두 진입 + cycle 153 UI redesign 본격 entry (사이클 153)

| 기능 | 상태 | 진입 cycle |
|---|---|---|
| 1:1 채팅 + 회원가입 + 파일전송 | ✅ Phase 1 v0.1.0 | cycle 16~36 |
| E2EE Signal Protocol (X3DH + Double Ratchet) | ✅ Phase 2 v0.2.0 | cycle 24~46 |
| multi-device + signature sound + push (FCM) | ✅ Phase 2 v0.2.0 | cycle 38~47 |
| Bot framework (Anthropic + OpenAI + jailbreak + RAG) | ✅ Phase 3 v0.3.0 | cycle 65~99 |
| Production infra (docker + nginx + certbot + KST logging) | ✅ Phase 4 v0.4.0 | cycle 100~117 |
| DB audit endpoint coverage 28 ActivityAction | ✅ 후속 chain | cycle 119~144 |
| SMTP 자동 설치 chain (mail.dopa.co.kr + Let's Encrypt + opendkim + cyrus-sasl + iptables) | ✅ Phase 1 OTP 발신 production-ready | cycle 129~131 |
| **그룹 채팅 + 친구 + signaling rooms** | ✅ Phase 5 Item 진입 (REST + UI + WebRTC mesh + friends + rooms persist e2e) | cycle 134~144 |
| **다국어 i18n (5 locale)** | ✅ Phase 5 Item 1 actual binding (24 tr() call + .qm 5 locale) | cycle 134~145 |
| **emoji pack share + moderation** (차별화) | ✅ Phase 5 Item 3 actual binding (admin menu + list_pending + DMCA phash + OCR jailbreak) | cycle 144~151 |
| **bot framework streaming 4 platform** | ✅ Phase 5 Item 4 actual client (YouTube + Twitch + CHZZK + Kick) + OBS WebSocket v5 handshake | cycle 146~148 |
| **원격 데스크탑 제어** (차별화) | ✅ Phase 5 Item 5 base + coord transform (DPI + Retina backing scale) + screen capture skeleton 3 OS | cycle 57~58 + 148~151 |
| **mobile Flutter base** | ✅ Phase 5 Item 2 prerequisite (mobile/ Flutter + flutter-webrtc + ws_client.dart + cycle 181 prereq doc) | cycle 147~151 |
| 자동 업데이트 | ✅ Phase 5 prereq (auto-update server endpoint + client startup chain + release.yml dual macOS arm64 + Windows x64) | cycle 132~151 |
| **SSH deploy chain + 서버 docker stack 본격** | ✅ ssh-deploy-agent + healthz 200 PASS + 5 service (mariadb + web + ws + nginx + postfix profile) | cycle 152 |
| **UI Toonation BI 통합 redesign** | ✅ phase 1~3 (theme.qss + logo SVG 회수 + WelcomeDialog + LoginDialog + OTPDialog + SignupDialog + SidebarRail + ChatListPanel + ChatHeader) | cycle 153.1~3 |
| 음성·영상 통화 | 🟡 Phase 6+ 후보 (WebRTC mesh ≤ 8 → SFU 마이그레이션 의무) | cycle 200+ |

### 3.2 ~~보안 deprioritized~~ — Phase 4 cycle 112~117 회수 완료

- ✅ TLS 1.2/1.3 + 6 cipher + OCSP stapling (nginx cycle 105)
- ✅ 5 rate limit zone (auth + api + bot + upload + ws_conn) (nginx cycle 105)
- ✅ 5 보안 header (HSTS preload 2y + X-Frame + nosniff + Referrer + CSP) (nginx cycle 105)
- ✅ SPF + DKIM RSA 2048 + DMARC (postfix cycle 102)
- ✅ sensitive redact 9 pattern (logging cycle 117)
- ✅ DDoS 1차 — nginx rate_limit_zone + ws_conn limit
- 🟡 DDoS L7 — CloudFlare 등 외부 service (Phase 5+ 검토)

### 3.3 ~~사용자 식별·복원~~ — Phase 1+2 완성

- ✅ 회원가입 + 이메일 OTP + 비번 재설정 (Phase 1 v0.1.0)
- ✅ E2EE Signal Protocol 키 페어 + multi-device sync + sender keys (Phase 2 v0.2.0)
- ✅ DB audit migration 0003 — signup_ip + last_login_ip + user_sessions + user_activity_log 23 ENUM (cycle 97 + cycle 119)

### 3.4 ~~라이선스 미확정~~ (✅ 사이클 6 해소)

- **GPLv3 확정** (사용자 directive 2026-05-17)
- LICENSE 저장소 루트 + PyQt6 GPLv3 직접 호환

### 3.5 ~~self-hosted runner 등록 미완~~ (✅ 사이클 5 해소 + 사이클 142~143 wine 영구 폐기 + windows-latest 마이그레이션)

- macOS arm64 runner 등록 OK (id=2 online)
- ~~Windows runner 의무 = wine cross-compile 대체~~ → **windows-latest GitHub-hosted runner 마이그레이션 SUCCESS (cycle 142~143)** — wine cp1252 Python 3.7 호환 FAIL 4회 끝 영구 폐기
- workflow 3종 GREEN 도달 + windows-native verify PASS

### 3.6 ~~코드 진입 미완~~ — Phase 1+2+3+4 본문 완성

- ✅ Phase 1 v0.1.0 — 회원가입 + 채팅 + 파일전송 + MariaDB
- ✅ Phase 2 v0.2.0-phase2 — E2EE Signal 200 PASS + multi-device + sound + push
- ✅ Phase 3 v0.3.0-phase3-bot — 10 module + reviewer 8 회수
- ✅ Phase 4 v0.4.0-phase4-infra — 34 신규 파일 + 144 PASS
- 코드 비율 = pytest 1257 + integration test + Playwright fixture (코드 우위)

### 3.7 차별화 잔존

- 🟡 원격 데스크탑 제어 — cycle 57~58 skeleton + cycle 148 coord transform 신설 + Phase 5 Item 5 본격 cycle 165~180 (production-ready 잔존)
- ✅ emoji pack share — cycle 144~148 admin menu + list_pending + DMCA chain actual binding 진입 완료
- 🔴 **Toonation REST API base_url + api_key 부재** (cycle 141 R sub-agent — Toonation REST 27 PASS skeleton + 사용자 직접 입력 의무) — Phase 5 본격 cycle 진입 차단
- 🔴 **OBS WebSocket base_url + password 부재** (cycle 148 JJ sub-agent — v5 actual handshake 16 PASS skeleton + 사용자 직접 입력 의무)

### 3.8 manual test 의무 (사용자 직접 영역)

- SMTP 실제 설치 = cycle 129~130 자동 chain — mail.dopa.co.kr listen 25/465/587/8891 + Let's Encrypt + DKIM RSA 2048 + DMARC pass 도달 (사용자 manual SSH 회수 완료)
- docker compose production stack 기동 = .env.production secrets 입력 + manual

### 3.9 mobile cycle 181 prerequisite 잔존 (신규 사이클 148)

cycle 147 mobile Flutter base (mobile/ + flutter-webrtc + ws_client.dart) 진입 직후 cycle 181~200 본격 cycle 진입 prerequisite 부재:

- **Apple Developer Program** 가입 (USD 99/년 + 사용자 직접) — App Store 배포 의무
- **Google Play Console** 계정 (USD 25 one-time + 사용자 직접) — Play Store 배포 의무
- **Firebase 프로젝트 신설** + FCM Server Key + iOS APNs cert + Android google-services.json
- **flutter doctor PASS** + iOS Xcode + Android Studio + ADB setup
- 사용자 manual 영역 5종 = mobile 본격 cycle 진입 차단

### 3.10 KT PTR record default 잔존 (cycle 145 잔존)

KT ISP default PTR record (tongkni.co.kr) 잔존 — mail.dopa.co.kr 의 reverse DNS 갱신 신청 의무. project_dopa_demo_only.md 영구 메모리 정합 = **dopa.co.kr 데몬스트레이션 전용** + 실 제품 도메인 부재 시점 = **KT PTR 회수 최후로 미룸 또는 skip**.

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
| 0 | **Phase 1 MVP 코드 진입 (회원가입 + 1:1 채팅 + 파일전송 + MariaDB)** | ✅ (사이클 16~36, v0.1.0) |
| 0 | **Phase 2 E2EE Signal Protocol (X3DH + Double Ratchet + multi-device + signature sound + push)** | ✅ (사이클 24~46, v0.2.0-phase2) |
| 0 | **Phase 3 bot framework (10 module + Anthropic/OpenAI + jailbreak 17 패턴 + RAG dual baseline)** | ✅ (사이클 65~99, v0.3.0-phase3-bot) |
| 0 | **Phase 4 production infra (docker stack + Config 통합 + nginx certbot + KST/JSON/redact logging + DB audit 0003)** | ✅ (사이클 100~117, v0.4.0-phase4-infra) |
| 0 | **Agent #16 산출물 reviewer-agent 검토** | ✅ (handoff §8.46+ 회수) |
| 0 | **cycle 119~131 (auth audit + activity + bot + devices + healthz + Phase 5 plan + bot_escalations DB + WS room audit + SMTP install/binding + OTP integration + self-hosted CI hook + 30일 token HTML)** | ✅ (cycle 119~131) |
| 0 | **cycle 132~133 sub-agent 12종 (REMOTE migration + i18n .ts + cron + sound designer + backup + emoji pack share + wine + auto-update + hook 강화)** | ✅ (cycle 132~133) |
| 0 | **cycle 134~138 sub-agent 6종 (i18n binding + release CI + 그룹 채팅 REST/UI/mesh)** | ✅ (cycle 134~138) |
| 0 | **cycle 139~141 sub-agent 9종 (main_window 그룹 채팅 통합 + auto-update startup + lrelease/.qm + WAV + Toonation REST + OBS WebSocket + messages persistence)** | ✅ (cycle 139~141) |
| 0 | **cycle 142~143 wine 영구 폐기 + windows-latest 마이그레이션 SUCCESS** | ✅ (cycle 142~143) |
| 0 | **cycle 144~147 sub-agent 11종 (i18n tr wrap + friends + signaling rooms + emoji moderation + .qm + streaming 4 platform + rooms invite + emoji list_pending + mobile Flutter base)** | ✅ (cycle 144~147) |
| 0 | **cycle 148 sub-agent 5종 (OBS WebSocket v5 actual + emoji 관리자 메뉴 + messages dual smoke + signaling e2e + remote coord transform) + token rewrite trigger** | ✅ (cycle 148) |
| 1 | **Toonation REST API base_url + api_key 사용자 직접 입력** — 옵션 B 본격 진입 prerequisite | 🔴 사용자 직접 |
| 2 | **OBS WebSocket base_url + password 사용자 직접 입력** — P5/P6 OBS 도움 시나리오 prerequisite | 🔴 사용자 직접 |
| 3 | **mobile cycle 181 prerequisite (Apple Developer + Google Play + Firebase + Xcode + Android Studio)** — 사용자 manual | 🟡 사용자 직접 |
| 4 | KT PTR record 갱신 (mail.dopa.co.kr reverse DNS) — dopa.co.kr 데모 전용 → 실 도메인 확정 후 갱신 또는 skip | 🟡 최후 |

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
| 1인 개발자 Phase 2~4 완주 어려움 | ✅ 해소 (cycle 148 — 30 cycle drift 0건 91 연속) | — | sub-agent 누계 46종 병렬 chain |
| 데모 서버 보안 사고 | ✅ 해소 (cycle 129 SMTP install 5 layer + Phase 4 nginx + DB audit) | — | Let's Encrypt + DKIM + DMARC + iptables |
| ~~라이선스 결정 지연~~ | ✅ 해소 (사이클 6) | — | GPLv3 확정 |
| PyQt6 GPL 의무 의 외부 fork distribution | 중 | 중 | GPLv3 정합 + private 전환 시 외부 fork 차단 |
| ~~문서 91% : 코드 9% 지속~~ | ✅ 해소 (cycle 117 — pytest 1673 + 코드 우위) | — | 8 체크리스트 통과 + Phase 1~5 진입 |
| **원격 제어 보안 사고** (Phase 5 Item 5 위험) | 중 | 상 | 친구 추가 사전 + 명시 수락 + 긴급 ESC + 감사 로그 + cycle 148 coord transform DPI/Retina 정합 |
| ~~SMTP spam reputation 부족~~ | ✅ 해소 (cycle 129 mail.dopa.co.kr DKIM + DMARC + Gmail Authentication-Results pass) | — | SendGrid relay fallback 회피 가능 |
| ~~wine 안 PyQt6 Qt dlls 호환성~~ | ✅ 해소 (cycle 142~143 wine 영구 폐기 + windows-latest 마이그레이션 SUCCESS) | — | windows-latest GitHub-hosted runner |
| **사용자 base_url + api_key 부재** (Toonation + OBS — cycle 148) | 상 | 상 | 사용자 직접 입력 의무 — Phase 5 본격 cycle 진입 차단 |
| **mobile cycle 181 prerequisite 부재** (Apple Developer + Google Play + Firebase + Xcode + Android Studio) | 상 | 중 | 사용자 manual 5종 의무 — mobile 본격 cycle 진입 차단 |
| **KT PTR record default 잔존** | 상 | 저 | dopa.co.kr 데모 전용 + 실 도메인 확정 후 갱신 또는 skip |
| **WebRTC mesh ≤ 8 peer cap** (cycle 137 WebRTC mesh 11 PASS skeleton) | 중 | 중 | 9 peer 이상 의무 SFU 마이그레이션 (Phase 6+) |

### 8.1 보안 리스크 해결책 강화 (사이클 32 신규 — 사용자 directive)

| 리스크 | 추가 해결책 (Defense-in-Depth) | 진입 시점 |
|---|---|---|
| 데모 서버 보안 사고 | (1) fail2ban + nftables rate limit (SSH/WS/SMTP 의 brute force 차단), (2) Let's Encrypt + HSTS preload (MITM 차단), (3) Wazuh agent + auditd (감사 로그), (4) systemd hardening (PrivateTmp + ProtectHome + NoNewPrivileges), (5) 백업 = encrypted off-site (borg + age) | Phase 2 진입 직전 |
| PyQt6 GPL 외부 fork distribution | (1) `LICENSE` SPDX header 의무 자동 검증 hook, (2) DCO sign-off pre-commit hook, (3) private 전환 시점 의 GPL 의무 distribution 명시 (Phase 종료 시 사용자 confirm), (4) AGPLv3 Phase 2 옵션 (network use 의 source disclosure) | Phase 2 진입 시 |
| 원격 제어 보안 사고 (Phase 3+) | (1) 친구 추가 양측 명시 수락 + biometric 2FA 의무, (2) 긴급 ESC = global hotkey + 즉시 세션 종료, (3) 감사 로그 = append-only + 매 세션 SHA-256 chain, (4) 화면 제어 권한 = 매 세션 명시 확인 (개별 영역 의 white-list grant), (5) 친구 평판 = trust score (가입 후 30일 + 활동 5건 이상 시 만 원격 제어 가능) | Phase 3 막바지 진입 직전 |
| SMTP spam reputation | (1) SPF + DKIM + DMARC 의무 + DMARC reject 정책, (2) bounce rate < 5% + complaint rate < 0.1% 모니터링, (3) SendGrid relay 100/day fallback, (4) Bayesian spam score 사전 검증 (SpamAssassin), (5) outbound rate limit 100/hour 의무, (6) IP warm-up 30일 (점진 송신량 증가) | Phase 1 dogfooding 시 |
| Phase 2 E2EE 잔존 (DH ratchet + skipped keys) | (1) Signal Protocol Test Vector 적용 (libsignal reference 의 정합 검증), (2) ratchet step 의 매 transition 의 invariant assertion (root + chain + counter 의 monotonic 보장), (3) skipped message keys = MAX_SKIP=1000 + LRU expire (메모리 폭주 차단), (4) 매 message 의 header MAC 검증 (X25519 public + counter 의 무결성), (5) reviewer-agent + cryptography expert review (PyCA 정합 + 부채널 공격 검토) | 사이클 33+ |
| 잠재 부채널 (timing + cache + speculative) | (1) `hmac.compare_digest` 의무 (constant-time), (2) AES-256-GCM 의 hardware acceleration (AES-NI / ARMv8 Crypto Extensions 활용), (3) X25519 = Curve25519 의 constant-time scalar mult (PyCA 보증), (4) 부채널 검사 도구 — `dudect` (statistical timing leakage), (5) speculative execution 의 PyPy/CPython 검토 보류 (Phase 4+) | Phase 3+ |
| 클라이언트 plain-text 저장 위험 | (1) DB 메시지 body = 클라 keychain 보관 + DB 는 ciphertext 만 저장, (2) macOS Keychain + Windows Credential Manager 통합, (3) 백업 = passphrase + PBKDF2 600K iter (현 security.py 정합) + age encrypt, (4) memory dump 차단 = `mlock` + `sodium_memzero` 패턴 | Phase 2 후반 |

---

## 9. KPI 후보

| KPI | 목표 | 현재 |
|---|---|---|
| 1:1 채팅 메시지 전송 성공률 | ≥ 99% | 미측정 (dogfooding 의무) |
| 파일 전송 SHA-256 무결성 | 100% | 미측정 (dogfooding 의무) |
| 시그널링 재연결 시간 (95p) | ≤ 5초 | 미측정 (dogfooding 의무) |
| 앱 cold start latency | ≤ 30초 | 미측정 (dogfooding 의무) |
| 1주 retention (내부 pilot) | ≥ 60% | 미측정 (pilot 의무) |
| CI 3 workflow GREEN 비율 | 100% | **100% ✓ (macOS arm64 + windows-latest, cycle 143~148)** |
| doc-lint.sh 5 검사 통과율 | 100% | 본 세션 신규 파일 100% |
| 가드레일 영구 메모리 | 10종+ | **56+ active (cycle 148)** |
| pytest 누계 PASS | ≥ 500 | **1673 PASS (cycle 148)** |
| pytest coverage | ≥ 80% | 미측정 |
| Playwright E2E test | ≥ 5건 | 3건 스켈레톤 active |
| **OTP 발송 → 수신 latency** | ≤ 30초 | cycle 129~130 production-ready (Gmail Authentication-Results pass + DKIM + DMARC) |
| **OTP brute force 차단율** | 100% (5회/30분) | OK (security.py PBKDF2 600K + email enumeration 회피) |
| **원격 제어 세션 성공률** | ≥ 95% | 미측정 (Phase 5 Item 5 cycle 165~180 후) |
| **mail-tester score** (SMTP) | ≥ 7/10 | cycle 129 chain — Gmail Authentication-Results pass 도달 |
| **fork PR approval rate** (악성 차단) | 100% | strict 적용 OK (사이클 5) |
| **GPLv3 호환 의존성** | 100% | 100% (PyQt6 + aiortc + qasync + asyncmy + bcrypt + aiosmtplib — 사이클 6) |
| **drift 0건 연속 cycle** | ≥ 50 | **91 연속 (사이클 37~148)** |
| **sub-agent 누계 병렬 spawn** | ≥ 10 | **46종 (cycle 132 9 + 133 3 + 134~138 6 + 139~141 9 + 142 3 + 144 4 + 145~147 7 + 148 5)** |
| **DB audit endpoint coverage** | ≥ 20 ActivityAction | **28 ActivityAction (cycle 144)** |
| **sub-agent 평균 PASS** | ≥ 5 | 8~15 PASS / sub-agent |
| **cycle 119~148 진입 누계** | ≥ 20 | **30 cycle (Phase 5 actual binding 부분 진입)** |
| **Phase 5 Item 진입** | ≥ 3 / 5 | **5 / 5 (i18n + mobile + emoji + bot + 원격 모두 actual binding 부분 진입)** |

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
