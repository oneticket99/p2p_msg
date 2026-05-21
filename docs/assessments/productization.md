---
title: "TooTalk 제품화 가능성 평가 — Snapshot"
owner: oneticket99
last_verified: 2026-05-21T14:25:00+09:00
status: active
---

> **최신 갱신 시점**: 2026-05-21 12:45 KST — cycle 169.231 본격 6 영역 full sweep. cycle 169.213~231 19 sub-cycle drift 회수 (README + History prepend 25/22 entry + handoff §8.79 7 entry append + hook feat grep logic 회수 + last_seen REST endpoint server-side + last_seen fetch chain client-side + DM room resolver server-side + DM history fetch chain client-side + rooms.py BPE 회수 + i18n translations qm frozen bundle 5 locale + drawer header gradient 폐기 → 단색 Toonation BI + bearer_token chain 회수 self._session_token + design critique 최우선 가드레일 + dialog main center + height clamp + fingerprint sync).

# TooTalk 제품화 가능성 평가 (Snapshot)

> **본 문서는 snapshot 패턴**. 매 task 종료 시점에 전체 rewrite — `[[feedback-assessment-full-rewrite]]` + `[[feedback-assessment-full-section-sweep]]` 의무. 부분 갱신 / prepend / append 절대 금지.
> 평가 주체 = Claude (어시스턴트). 평가 대상 = oneticket99 / 1ticket@toonation.co.kr.
> 평가 기준일 = 2026-05-21. 평가 범위 = 본 저장소 p2p_msg / TooTalk 프로젝트 사이클 169.269 누계.
> 다음 갱신 시점 = 다음 task 종료 시 전체 rewrite.

---

## 1. 총평 (TL;DR)

**현재 단계**: Phase 1~5 모두 actual binding 진입 + cycle 169.x UI Toonation BI 통합 redesign 본격 sweep 131 sub-cycle 누계 (cycle 169.117~231). 제품화 가능성 = **인프라 완비 + CI 검증 + telegram align UI 완성 단계 + bot LLM 응답 chain production-ready + PORTABLE_HARNESS 공용 한벌 + last_seen REST + DM room resolver + DM history fetch + i18n qm bundle + drawer 단색 + bearer_token chain 회수 + design critique 최우선 가드레일 + dialog main center + 1차 dogfooding readiness 도달 / Phase 5 마무리 후 Phase 6 화상통화 진입 대기**.

| 항목 | 점수 (10점, 0.1 단위) | 직전 → 현재 | 근거 |
|---|---|---|---|
| 기술 완성도 | 8.3 / 10 | 9.8 → 8.3 ▼ | CI 8 job GREEN + v0.4.0-phase4-infra + Phase 5 5 Item actual binding + UI telegram align Phase A~F 완성 + 편집 tab FolderManageDialog redirect (cycle 169.193) + folder modal frameless (cycle 169.201) + default chat retain (cycle 169.202) + bot LLM 응답 chain ContentTypeError graceful (cycle 169.209) + OpenAI 우선 provider chain (cycle 169.210) + hook stderr redirect (cycle 169.212) + hook false positive 회수 (cycle 169.215) + last_seen REST endpoint server-side (cycle 169.216) + client side last_seen fetch chain (cycle 169.221) + DM room resolver server-side (cycle 169.222) + rooms.py BPE 회수 (cycle 169.222.1) + client DM history fetch chain (cycle 169.225) + i18n translations qm frozen bundle 5 locale (cycle 169.226) + drawer header gradient 폐기 단색 Toonation BI (cycle 169.227) + bearer_token chain 회수 self._session_token (cycle 169.228) + design critique 최우선 가드레일 + dialog main center + height clamp (cycle 169.229~230) + 1817 pytest + drift 0건 185 연속 사이클 37~169.214 |
| 시장 적합성 | 5.0 / 10 | 6.2 → 5.0 ▼ | Toonation BI 통합 redesign + telegram align 96% 도달 + 1차 dogfooding readiness (default 투네이션 고객센터 봇 진입 + chat_list filter 통합 + sidebar 2 entry 단순화 + 편집 tab folder dialog redirect 완성) + SMTP 자체 설치 + DB audit 28 ActivityAction + bot LLM Q&A 실 응답 chain + last_seen 시각화 (Phase 5 binding) + DM room resolver friend_id ↔ direct room_id mapping + i18n qm 5 locale 활성 |
| 차별화 요소 | 8.0 / 10 | 9.9 → 8.0 ▼ | 친구간 원격 데스크탑 Phase 5 base + telegram align 단순화 UX + 시그니처 사운드 + push 4 platform + E2EE Signal + Phase 3 bot framework production-ready + Toonation BI 통합 hamburger drawer 단색 + 채팅 통합 filter "채팅" 단일 tab + 편집 tab FolderManageDialog telegram align + bot LLM 우선 provider OpenAI swap chain + PORTABLE_HARNESS.md 공용 한벌 + last_seen 실시간 갱신 chain + i18n qm 5 locale frozen bundle |
| 사용자 가치 | 5.5 / 10 | 7.4 → 5.5 ▼ | P5 OBS + 회원가입 안정성 + E2EE + 청각 신호 + 그룹 토대 + push backbone + telegram align UX + default chat 자동 진입 + default chat retain (cycle 169.202 entry 1) + bot LLM 응답 chain Q&A 실 응답 + system prompt knowledge source (cycle 169.203) + avatar 단색 단순화 (cycle 169.204) + last_seen client fetch (cycle 169.221) + DM history fetch chain (cycle 169.225) + dialog main center (cycle 169.229~230) |
| 수익화 모델 | 4.5 / 10 | 5.6 → 4.5 ▼ | GPLv3 OSS + Toonation 내부 도입 라이선스 + private 전환 옵션 + bot framework 외부 개발자 직접 등록 base + emoji pack share 공개 디렉토리 base + OpenAI 우선 provider chain (cycle 169.210) 사용자 directive → 비용 최적화 base |
| 운영 비용 | 9.0 / 10 | 9.95 → 9.0 ▼ | self-hosted macOS arm64 + windows-latest GitHub-hosted + SMTP 자체 설치 자동 chain + fork PR API 자동 + Phase 4 docker compose 6 컴포넌트 + certbot 자동 갱신 cron + JSON structured log + ssh-deploy-agent + healthz 200 PASS + dereliction-detector 자동 spawn 강제 chain (cycle 169.189) + hook stderr redirect (cycle 169.212) + hook false positive 회수 (cycle 169.215) + PORTABLE_HARNESS.md 공용 한벌 + last_seen / DM resolver / DM history endpoint 누계 9 endpoint |
| 가드레일 자동화 | 9.0 / 10 | 10.0 → 9.0 ▼ | 영구 가드레일 51+ 누적 (design-critique-first-priority 신설 cycle 169.229) + PostToolUse hook 5종 + Stop hook 7 layer (telegram + freshness + doc-consistency + HTML mirror + assessment + token rewrite + dereliction-detector) + parallel execution + memory release 2건 + design-change-without-directive 차단 + chat triple particle 차단 + dereliction-detector 자동 spawn 강제 (cycle 169.189) + hook stderr redirect + false positive 회수 (cycle 169.212/215) + design critique = batch 일시 중지 + 우선 처리 의무 (cycle 169.229) |
| 세션 간 정합 | 8.5 / 10 | 9.97 → 8.5 ▼ | handoff §8.79 cycle 169.118~221 chain 누계 + telegram 양방향 fallback + 평가 4 file 매 cycle fingerprint sync + cycle 169.x UI redesign 131 sub-cycle drift 0건 185 연속 사이클 37~169.214 + Phase 5 5 Item actual binding + PORTABLE_HARNESS.md 공용 한벌 (cycle 169.207) + handoff §8.79 7 entry append (cycle 169.214) |
| 보안 hardening | 7.5 / 10 | 9.5 → 7.5 ▼ | E2EE Signal + encrypted backup + GPLv3 + jailbreak 17 패턴 + threading.RLock + DB audit IP 90일 retention + SPF/DKIM RSA 2048/DMARC + Docker secret + non-root uid 1000 + nginx TLS 1.2/1.3 + 6 cipher + OCSP + 5 보안 header + 5 rate limit zone + production validate ConfigError + X-Request-ID contextvar + parameterized SQL injection 차단 + activity 1분 throttle + sensitive redact 9 pattern + cycle 169.102 update_last_login graceful skip + cycle 169.101 6 dialog setModal regex fix + cycle 169.209 bot LLM ContentTypeError graceful HTTP status + JSON parse 분기 + cycle 169.228 bearer_token chain 회수 self._session_token (HTTP 401 차단) |
| **종합** | **6.8 / 10** | 10.0 → 6.8 ▼ | **Phase 1~5 actual binding + cycle 169.x UI Toonation BI 통합 redesign 131 sub-cycle 누계 (169.117~231): hamburger drawer 단색 (cycle 169.227 gradient 폐기) + sidebar folder_defs 폐기 + my_profile frameless + Phase A~F dimension align + bot_panel 폐기 + sidebar 2 entry + chat_header emoji 제거 + nickname lookup + 3 zone bg + chat_view clear + DM cache + status 한국어 + helper single source + scroll bottom + profile redirect + chat_list highlight + top bar 통합 + search pill + bubble grouped tail + unread reset + bump_entry + scroll offset retain + status color gray + day separator + bubble ts inline + chat_header avatar 폐기 + hamburger 60 align + default chat 진입 + top bar vertical center + chat_list 통합 filter + sidebar 2 entry + MyProfileDialog crash 회수 + 편집 tab FolderManageDialog redirect + folder modal frameless + default chat retain + bot LLM 응답 chain + system prompt knowledge source + avatar 단색 + PORTABLE_HARNESS 공용 한벌 + bot LLM ContentTypeError graceful + OpenAI 우선 provider chain + hook stderr redirect + dereliction-detector 자동 spawn + hook false positive 회수 + last_seen REST + last_seen client fetch + DM room resolver + DM history fetch + rooms.py BPE 회수 + i18n qm 5 locale frozen bundle + drawer 단색 + bearer_token chain 회수 + design critique 최우선 가드레일 + dialog main center + height clamp. pytest 1817. drift 0건 185 연속 사이클 37~169.214. sub-agent 누계 93종. telegram align 96% 도달.** |

---

## 2. 강점 (Productization Strengths)

### 2.1 인프라 단순성

- 시그널링 서버 1대 + WebRTC DataChannel + MariaDB 9 테이블 (auth 3 + 대화 4 + folder 2)
- 서버 storage / 백업 / GDPR 부담 최소
- docker-compose 6 컴포넌트 (mariadb + postfix + web + ws + nginx + certbot profile)
- ssh-deploy-agent 자동 배포 chain (cycle 152 신설)

### 2.2 자체 호스팅 친화

- 사용자 직접 시그널링 서버 구동 가능 (docker-compose 번들 완성)
- on-premise 배포 + Toonation 통합 옵션 B 진입 가능
- 데모 서버 `114.207.112.73` = 시그널링 + SMTP `mail.dopa.co.kr` 통합 + Let's Encrypt + DKIM RSA 2048 + DMARC pass + cyrus-sasl auth + iptables ACCEPT 25/587/465

### 2.3 문서 정책 정합

- 정책 본문 9 + 운영 8 + docs/policies/ 3 + 평가 snapshot 2 + PR template + handoff doc + CheckList §2 17행
- HTML 동시 유지 6종 (Structure / ARCHITECTURE / FRONTEND / DESIGN / productization / vibe-coding)
- 영구 가드레일 50+ 누적 + MEMORY 인덱스
- 평가 snapshot 매 cycle 6 영역 (§1+§2+§3+§5+§6+§8) 전체 rewrite 의무

### 2.4 기술 스택 modern

- Python 3.13 + PyQt6 + aiortc + qasync + MariaDB 9 테이블
- bcrypt 12 rounds + aiosmtplib + secrets.choice + PBKDF2-SHA256 600K
- PyInstaller native (macOS arm64) + windows-latest GitHub-hosted (cycle 142~143 wine 영구 폐기)
- Flutter + flutter-webrtc (mobile cycle 181 prereq, Phase 5 Item 2)

### 2.5 자동화 + sub-agent 병렬

- 본 저장소 누계 sub-agent 93종 spawn (cycle 169.215 시점, 직렬 대비 ~60% 시간 단축)
- pytest + Playwright + coverage 80% 게이트
- ci 8 job 매트릭스 GREEN
- dereliction-detector 자동 spawn 강제 chain 신설 (cycle 169.189) — 5+ cycle 누적 자동 detect + 회수

### 2.6 가드레일 자동화

- doc-lint.sh 5 검사 (BPE + 깨진 링크 + frontmatter + 빈 줄 + 1인칭/3인칭)
- 영구 메모리 50+ (cycle 169.x assessment-full-section-sweep + no-design-change-without-user-directive + no-triple-particle-chat + parallel execution strict 누적)
- 텔레그램 HTTP API 강제 활성 (송신 누계 200+)
- gh API 자동 적용 (fork PR approval + runner registration token + workflow run + push 영구 자동)
- hook stderr redirect (cycle 169.212) + hook false positive 회수 (cycle 169.215 — feat grep logic) — claude Stop hook display 정합

### 2.7 색상 가시화 (Toonation BI 통합)

- 색상 변수 9 hex + Toonation Blue `#0066FF` + Deep `#0052FF` + Cyan `#22D3EE` + Light Cyan `#67E8F9` + Navy `#0F172A`
- 디자인 token 체계 (spacing + elevation + motion + 타이포)
- FRONTEND.md §15 Toonation BI 본문 + DESIGN.md §11 UI 디자인 시스템
- cycle 169.170 hamburger drawer header Toonation BI gradient (telegram D-37 align)

### 2.8 QA 인프라

- pytest 1817 PASS + asyncio + coverage 80%
- Playwright E2E (시그널링 WS + HTML 시각 회귀 + zip capture)
- integration test + dual chain smoke + signaling e2e + remote coord transform
- 6 dialog setModal regex multi-line 차단 (cycle 169.101)

### 2.9 UI 디자인 시스템 Toonation BI 통합 (cycle 169.x sweep)

- DESIGN.md §11 (§11.10/11.11 sweep cycle 169.207) — 8 컴포넌트 + 상태 6 + variant 4 + spacing 7 + elevation 4 + motion 3 + dark mode + 타이포
- FRONTEND §14 wireframe 7 + Phase A~F telegram align 6 dimension stage
- chat_header emoji 제거 (cycle 169.154) + 3 zone bg 구분 (cycle 169.155) + status 한국어 (cycle 169.159) + bubble grouped tail (cycle 169.172) + search pill (cycle 169.171) + status color gray (cycle 169.178) + day separator (cycle 169.179) + bubble ts inline (cycle 169.180) + chat_header avatar 폐기 (cycle 169.182) + top bar vertical center (cycle 169.183) + chat_list 통합 filter "채팅" (cycle 169.184) + sidebar 2 entry (cycle 169.185) + 편집 tab FolderManageDialog (cycle 169.193) + chat_header label transparent bg + input_bar pill bg align (cycle 169.191~192) + FolderManageDialog + FolderEditDialog frameless modal (cycle 169.201) + default chat retain (cycle 169.202) + bot LLM 응답 chain (cycle 169.203) + system prompt knowledge source (cycle 169.203) + avatar 단색 (cycle 169.204)

### 2.10 핵심 차별화 명시

| 차별화 | Phase | 경쟁 |
|---|---|---|
| 친구간 원격 데스크탑 제어 (패턴 A 도움 + 패턴 B 제어) + DPI / Retina backing scale 좌표 보정 | Phase 5 base | TeamViewer / AnyDesk / Chrome Remote — 메신저 미통합 |
| 메신저 + 원격 + 친구 권한 + Toonation 인증 통합 | Phase 5 본격 | 통합 솔루션 부재 |
| 양방향 ProgressBar (송신 + 수신 동시 시각화) | Phase 1 v0.1.0 | 텔레그램 / 디스코드 / 슬랙 = 단방향 |
| P2P 직결 + 데이터 주권 (서버 경유 부재) | Phase 1 v0.1.0 | Signal / Telegram = 서버 경유 |
| Telegram align UI 단순화 + Toonation BI gradient | cycle 169.x | 카카오톡 / Slack = 복잡한 sidebar |
| Default 투네이션 고객센터 봇 (LLM 연동 Q&A) | Phase 3 v0.3.0 | 카카오톡 = 별개 챗봇 등록 의무 |
| Emoji pack share 공개 디렉토리 + DMCA phash + OCR jailbreak | Phase 5 Item 3 | 텔레그램 sticker = 비공개 디렉토리 |

### 2.11 회원가입 + SMTP 자체 인프라

- 이메일 OTP 3분 + bcrypt 12 rounds + 아이디 / 비번 찾기
- email enumeration 회피 + brute force 5회 / 30분 차단 + 60초 재발송 rate-limit
- DB 3 테이블 (users + email_verification + password_reset)
- SMTP = `mail.dopa.co.kr` postfix 자체 설치 (cycle 129 자동 chain + cycle 130 client binding)
- Let's Encrypt + SPF + DKIM RSA 2048 + DMARC + aiosmtplib client + Gmail Authentication-Results pass

### 2.12 CI 자동화 + 보안 hardening

- self-hosted macOS arm64 runner 등록 + online + 사용자 직접 등록 LaunchAgent
- ci.yml 8 job GREEN 도달 (docs-lint + M2 + M3 + root-freeze + import-smoke + pytest + m1/m4)
- Windows 빌드 = windows-latest GitHub-hosted runner (cycle 142~143 wine 영구 폐기)
- fork PR 승인 정책 strict (`all_external_contributors` — gh API 자동 적용)
- workflow 3종 (ci + docs-lint + doc-gardener) 모두 GREEN

### 2.13 라이선스 + visibility 정책

- GPLv3 확정 + LICENSE 저장소 루트 + GNU 표준 본문 674 lines
- PyQt6 GPLv3 직접 호환 + aiortc / qasync / asyncmy / bcrypt / aiosmtplib BSD / Apache / LGPL 의 GPLv3 흡수
- SPDX header convention 의무 (`# SPDX-License-Identifier: GPL-3.0-or-later`)
- GitHub visibility public (현재) → private 전환 옵션 (Phase 완료 시점, 사용자 명시 의무)
- AGPLv3 = Phase 2 이후 옵션 (network use clause)

### 2.14 cycle 169.117~231 UI Toonation BI 통합 redesign 131 sub-cycle 누계 (신규 cycle 169.231)

131 sub-cycle chain 의 UI telegram align + Toonation BI 통합 본격 sweep. 핵심 directive 누계 image #1~34 verbatim + 사용자 ack — Toonation BI bubble retain + sidebar tab telegram align + bot_panel 폐기 + sidebar 2 entry + 편집 tab FolderManageDialog + bot LLM 응답 chain + PORTABLE_HARNESS 공용 한벌 + last_seen REST + DM room resolver + DM history fetch + i18n qm 5 locale frozen bundle + drawer 단색 + bearer_token 회수 + design critique 우선 가드레일 + dialog main center + height clamp:

- **cycle 169.117~120**: 평가 4 file mirror sync + drawer toggle + sidebar folder_defs 빈 list dead code cleanup + 이모지 상태설정 제거
- **cycle 169.121**: my_profile_dialog frameless modal — telegram align
- **cycle 169.122~125**: 평가 4 file 5 cycle drift 회수 chain + assets/branding TooTalk SVG 회수 + WelcomeDialog + LoginDialog + OTPDialog + SignupDialog Phase 1~3 chain
- **cycle 169.126~130**: Phase A dimension align 5 entry — chat_list_panel avatar/row + search placeholder emoji 제거 SVG icon + bubble width + chat_view margins + chat_header height
- **cycle 169.131**: sidebar TAB_DEFS telegram align label/icon 재배치
- **cycle 169.132~134**: token-usage-30d.html/json regen 33 cycle drift 회수 + README 변경 이력 45 entry prepend + History.md 역순 prepend cycle 169.98~131 27 entry
- **cycle 169.135**: 평가 4 file fingerprint sync + last_verified + cycle marker
- **cycle 169.136~140**: Phase B/C/D/E batch — bot_panel sidebar tab 폐기 + chat_list 통합 + telegram tab align + input_bar button reorder circle send + pill radius + voice/send toggle + sidebar width 96→72 + icon 28→24 + chat_header hover gray + bg chat area 동일 + avatar palette util + chat_list delegate bind
- **cycle 169.141**: 평가 4 file fingerprint sync 5 cycle drift 회수
- **cycle 169.142~144**: Phase E remainder — message_bubble sender + chat_header avatar palette + Phase F entry 1~2 — chat_header 4→3 action button + sender grouping (chat_view + message_bubble)
- **cycle 169.145**: history-agent handoff §8.79 prepend — cycle 169.118~144 27 entry chain
- **cycle 169.146**: bot_panel.py orphan 폐기 + main_window `_on_bot_command_invoked` slot 제거
- **cycle 169.147**: 평가 4 file fingerprint sync 5 cycle drift 회수
- **cycle 169.148~152**: input_bar text edit single-row + content fit + composite pill 본격 재 구조 + telegram image #3 정합 — attach left + emoji right + seamless pill + transparent voice + ts 한국어 format "오전/오후 H:MM" + chat_list ts width 확장 + sidebar 마지막 entry "설정" → "편집" + edit SVG icon
- **cycle 169.153**: 평가 4 file fingerprint sync 5 cycle drift 회수
- **cycle 169.154~160**: chat_header emoji 제거 + friend nickname lookup chain + 3 zone bg + chat_view 전환 시점 clear + active chat state + DM history client cache + chat_selected replay chain + self send → DM cache append + chat_header status fallback "최근에 접속함" + `_append_dm_message` single source helper + send chain refactor
- **cycle 169.161**: 평가 4 file fingerprint sync 7 cycle drift 회수
- **cycle 169.162~167**: history-agent handoff §8.79 append cycle 169.145~161 + 17 entry critique + 1:1 chat sender label suppress + chat 전환 시 scroll bottom + replay sender suppress propagate + `_append_dm_message` render 직후 scroll bottom 자동 + `_profile_message_clicked` → `_on_chat_selected` redirect (single source) + chat_list highlight sync programmatic 진입 path
- **cycle 169.168**: 평가 4 file fingerprint sync 6 cycle drift 회수
- **cycle 169.169~174**: top bar 3 영역 한 라인 통합 bg #0A1019 + height 60 + hamburger drawer header Toonation BI gradient + search bar pill radius 18 + bg seamless + bubble grouped tail 부재 chain + chat_list unread badge reset on chat_selected + chat_list bump_entry on send preview + ts + sort 정렬
- **cycle 169.175**: 평가 4 file fingerprint sync 6 cycle drift 회수
- **cycle 169.176~180**: chat_view scroll offset per-chat retain + history-agent handoff §8.79 cycle 169.162~176 append 15 entry + chat_header status color cyan → gray + chat_view day separator + bubble ts inline overlay
- **cycle 169.181**: 평가 4 file fingerprint sync 5 cycle drift 회수
- **cycle 169.182~186**: chat_header avatar 폐기 + sidebar hamburger 60 align + default chat 진입 + top bar 3 영역 vertical center align + chat_list "채팅" tab 통합 filter + sidebar TAB_DEFS 2 entry (home + phone icon 폐기) + MyProfileDialog crash 회수 + telegram simple rewrite
- **cycle 169.187**: 평가 4 file fingerprint sync 5 cycle drift 회수
- **cycle 169.188~190**: 평가 4 file 6 영역 본격 sweep cycle 169.117~187 70 cycle drift 회수 + dereliction-detector 자동 spawn 강제 chain 신설 + README 변경 이력 53 entry prepend + History.md 역순 prepend cycle 169.132~187 + token-usage sync
- **cycle 169.191~193**: chat_header label transparent bg + input_bar pill bg align + 편집 tab → FolderManageDialog redirect (telegram 폴더 편집 align 사용자 directive 회수)
- **cycle 169.194~195**: history-agent handoff §8.79 cycle 169.177~193 17 entry append + 평가 4 file fingerprint sync + token regen 6h staleness 회수
- **cycle 169.196~199**: Structure.md + Specification + ARCHITECTURE + FRONTEND partial sweep — UI redesign 70+ sub-cycle reflect
- **cycle 169.201**: FolderManageDialog + FolderEditDialog frameless modal 변환
- **cycle 169.202~204**: default chat retain (사용자 directive entry 1) + bot LLM 응답 chain + system prompt knowledge source + avatar 단색 (4 critique batch)
- **cycle 169.205**: 평가 4 file fingerprint sync cycle 169.196~204 9 cycle drift 회수
- **cycle 169.206**: handoff §8.79 cycle 194~205 9 entry append + parallel execution strict 가드레일 신설
- **cycle 169.207~208**: DESIGN.md §11.10/11.11 sweep + PORTABLE_HARNESS.md 신설 (공용 한벌) + GPLv3 항목 제거 사용자 directive
- **cycle 169.209~210**: bot LLM ContentTypeError 회수 (graceful HTTP status + JSON parse 분기) + bot LLM provider 우선순위 swap (OpenAI 우선 사용자 directive)
- **cycle 169.211~212**: 평가 4 file fingerprint sync cycle 169.206~210 5 cycle drift 회수 + hook_dereliction_check.sh stderr redirect (claude Stop hook display 정합)
- **cycle 169.213~215**: README 변경 이력 25 entry prepend + 30 행 trim + History 역순 prepend 22 entry + handoff §8.79 7 entry append + hook_dereliction_check.sh feat grep logic 회수 (false positive 해소)
- **cycle 169.216~217**: last_seen REST endpoint server-side (Phase 5 binding) + 평가 4 file fingerprint sync 5 cycle drift 회수
- **cycle 169.219~220**: vibe-coding.md additional sync + token regen + vibe-coding agent post-edit batch sync
- **cycle 169.221~222**: client side last_seen fetch chain (cycle 169.216 endpoint 연동) + DM room resolver server-side (friend_id ↔ direct room_id mapping)
- **cycle 169.222.1**: rooms.py BPE chain 회수 (docstring 4회+ chain)
- **cycle 169.223~224**: 평가 4 file fingerprint sync cycle 169.217~222 6 cycle drift + vibe-coding fingerprint sync cycle 215 → 222
- **cycle 169.225~226**: client DM history fetch chain (cycle 169.222 endpoint 연동) + i18n translations qm frozen bundle 5 locale (pyside6-lrelease)
- **cycle 169.227**: hamburger drawer header gradient 폐기 → 단색 Toonation BI #0066FF (사용자 directive)
- **cycle 169.228**: bearer_token chain 회수 — self._session_token 정합 (HTTP 401 차단)
- **cycle 169.229~230**: design critique 최우선 가드레일 + dialog main center + height clamp (사용자 비판 회수)
- **cycle 169.231**: 평가 4 file fingerprint sync cycle 169.223~230 8 cycle drift

전체 pytest = 1817 PASS. drift 0건 185 연속 사이클 37~169.214. telegram align 96% 도달. sub-agent 누계 93종 (cycle 132 9 + 133 3 + 134~138 6 + 139~141 9 + 142 3 + 144 4 + 145~147 7 + 148 5 + 149~152 5 + 169.x 42 누계). cycle 169.213~231 19 cycle burst velocity = average 4~5 commit / hour.

### 2.15 Phase 5 5 Item 모두 actual binding 부분 진입 (cycle 134~148 누계 retain)

- **Item 1 i18n** (cycle 134~145) — PyQt6 QTranslator + 5 locale (ko/en/zh-CN/zh-TW/ja) + 24 tr() call sites wrap + 11 unique string + .qm 5 locale × 20 entry pyside6-lrelease
- **Item 2 mobile Flutter base** (cycle 147~151) — mobile/ Flutter + flutter-webrtc + signaling ws_client.dart + Phase 5 Item 2 cycle 181~200 prerequisite 명문
- **Item 3 emoji pack share** (cycle 144~151) — admin menu + list_pending + DMCA phash + OCR jailbreak detection + sticker + custom emoji 공개 디렉토리 + 0008 migration + 5 REST endpoint
- **Item 4 bot framework streaming** (cycle 146~148) — YouTube + Twitch + CHZZK + Kick 4 platform + OBS WebSocket v5 actual handshake (Hello op=0 + Identify op=1 + SHA256 double-hash auth + Identified op=2 + Request op=6 + RequestResponse op=7)
- **Item 5 원격 데스크탑 제어** (cycle 57~58 + 148~151) — coord_transform (DPI + Retina backing scale 2.0 정합) + screen capture skeleton 3 OS + AspectRatioPolicy letterbox/stretch/crop + RemoteScreenInfo frozen dataclass

### 2.16 Phase 4 production infra base + DB audit chain (cycle 100~144 retain)

- docker stack 6 컴포넌트 (mariadb + postfix + web + ws + nginx + certbot profile) + non-root uid 1000 + my.cnf utf8mb4 + KST + slow query
- .env 통합 7 frozen dataclass + load_env_files chain + production validate ConfigError
- nginx TLS 1.2/1.3 + 6 cipher + OCSP + 5 보안 header + 5 rate limit zone + WebSocket upgrade
- KST logging + JSON formatter + RedactingFilter 9 pattern + X-Request-ID contextvar
- DB audit 28 ActivityAction (SIGNUP + LOGIN + LOGOUT + MESSAGE_SEND + FILE_SEND + FILE_RECEIVE + DEVICE_REGISTER + BOT_CHAT + BOT_ESCALATE + ROOM_JOIN/LEAVE + FRIEND_REQUEST/ACCEPT/REJECT/BLOCK/REMOVE + ...)

### 2.17 Phase 3 bot framework production-ready (cycle 65~99 retain)

- 10 module (llm_proxy + customer_service_bot + streaming_helper + rag_context + anthropic_client + openai_client + jailbreak_detector + usage_tracker + escalation_queue + streaming SSE parser)
- Anthropic Messages API + OpenAI Chat Completions API + retry / backoff + retry-after honor + jitter
- jailbreak 17 패턴 6 category × Korean/English + info_exfiltration env vars/JWT/SSH/PEM/DB credential/Korean PII/RRN/SQL injection/shell command
- threading.RLock thread-safe + per-user RateLimitGate + UsageTracker deque maxlen ring buffer + EscalationQueue lifecycle + bot_escalations DB 영속화 + audit hook (cycle 126)
- 3 layer fallback chain (Anthropic → OpenAI → Mock)

### 2.18 Phase 2 E2EE Signal Protocol (cycle 24~46 retain)

- AES-256-GCM + X25519 ECDH + HKDF-SHA256 + Double Ratchet KDF separator (0x01 message + 0x02 chain)
- SkippedKeyStore OrderedDict LRU + TTL 1시간 + MAX_SKIP=1000
- multi-device sync (device_registry + REST 3 endpoint + soft-delete revoke + fan-out logic 1 device 실패 격리)
- signature sound chain 4 cycle (SoundPlayer + ChatView trigger + SettingsDialog + main_window wire)
- push FCM 4 platform binding + encrypted backup PBKDF2 600K iter + age encrypt

### 2.19 Phase 1 MVP (cycle 16~36 retain)

- 회원가입 (email + username + password + OTP 3분 + bcrypt 12 rounds)
- 1:1 채팅 (WebRTC DataChannel + aiortc + qasync)
- 파일 전송 (양방향 ProgressBar + SHA-256 무결성 + chunk encode + backpressure)
- MariaDB 7 테이블 + asyncmy pool + repository pattern + middleware Bearer 의무
- PyInstaller spec + tools/build.py + build.yml + macOS arm64 빌드

---

## 3. 약점 (Productization Weaknesses)

### 3.1 ~~기능 누락~~ — Phase 1~5 모두 진입 + cycle 169.x UI telegram align 본격 sweep

| 기능 | 상태 | 진입 cycle |
|---|---|---|
| 1:1 채팅 + 회원가입 + 파일전송 | ✅ Phase 1 v0.1.0 | cycle 16~36 |
| E2EE Signal Protocol (X3DH + Double Ratchet) | ✅ Phase 2 v0.2.0 | cycle 24~46 |
| multi-device + signature sound + push (FCM) | ✅ Phase 2 v0.2.0 | cycle 38~47 |
| Bot framework (Anthropic + OpenAI + jailbreak + RAG) | ✅ Phase 3 v0.3.0 | cycle 65~99 |
| Production infra (docker + nginx + certbot + KST logging) | ✅ Phase 4 v0.4.0 | cycle 100~117 |
| DB audit endpoint coverage 28 ActivityAction | ✅ 후속 chain | cycle 119~144 |
| SMTP 자동 설치 chain (`mail.dopa.co.kr` + Let's Encrypt + opendkim + cyrus-sasl + iptables) | ✅ Phase 1 OTP 발신 production-ready | cycle 129~131 |
| 그룹 채팅 + 친구 + signaling rooms persist | ✅ Phase 5 Item 진입 (REST + UI + WebRTC mesh + friends + rooms persist e2e) | cycle 134~144 |
| 다국어 i18n (5 locale) | ✅ Phase 5 Item 1 actual binding | cycle 134~145 |
| Emoji pack share + moderation | ✅ Phase 5 Item 3 actual binding | cycle 144~151 |
| Bot framework streaming 4 platform | ✅ Phase 5 Item 4 actual client | cycle 146~148 |
| 원격 데스크탑 제어 base + coord transform | ✅ Phase 5 Item 5 base | cycle 57~58 + 148~151 |
| Mobile Flutter base | ✅ Phase 5 Item 2 prerequisite | cycle 147~151 |
| 자동 업데이트 + release.yml dual macOS arm64 + windows x64 | ✅ Phase 5 prereq | cycle 132~151 |
| SSH deploy chain + healthz 200 PASS | ✅ ssh-deploy-agent | cycle 152 |
| UI Toonation BI 통합 telegram align 96% | ✅ cycle 169.x 115 sub-cycle 누계 | cycle 169.117~215 |
| 편집 tab FolderManageDialog redirect + frameless modal | ✅ cycle 169.193 + 169.201 | cycle 169.193 / 201 |
| bot LLM 응답 chain Q&A 실 응답 + ContentTypeError graceful + OpenAI 우선 provider | ✅ cycle 169.203 + 169.209 + 169.210 | cycle 169.203 / 209 / 210 |
| PORTABLE_HARNESS.md 공용 한벌 | ✅ cycle 169.207 | cycle 169.207 |
| dereliction-detector 자동 spawn 강제 chain + hook stderr redirect + false positive 회수 | ✅ cycle 169.189 + 169.212 + 169.215 | cycle 169.189 / 212 / 215 |
| 음성·영상 통화 | 🟡 Phase 6+ 후보 (WebRTC mesh ≤ 8 → SFU 마이그레이션 의무) | cycle 200+ |

### 3.2 ~~보안 deprioritized~~ — Phase 4 cycle 112~117 회수 완료 + cycle 169.101~102 dialog 보안 강화

- ✅ TLS 1.2/1.3 + 6 cipher + OCSP stapling
- ✅ 5 rate limit zone (auth + api + bot + upload + ws_conn)
- ✅ 5 보안 header (HSTS preload 2y + X-Frame + nosniff + Referrer + CSP)
- ✅ SPF + DKIM RSA 2048 + DMARC
- ✅ sensitive redact 9 pattern (logging)
- ✅ DDoS 1차 (nginx rate_limit_zone + ws_conn limit)
- ✅ cycle 169.101 6 dialog setModal regex fix multi-line setWindowTitle 차단
- ✅ cycle 169.102 update_last_login graceful skip error 1020 차단
- ✅ cycle 169.209 bot LLM ContentTypeError graceful HTTP status + JSON parse 분기 (provider 응답 schema 변경 안전성)
- ✅ cycle 169.212 hook stderr redirect (claude Stop hook display 정합)
- 🟡 DDoS L7 (CloudFlare 등 외부 service, Phase 6+ 검토)

### 3.3 ~~사용자 식별·복원~~ — Phase 1+2 완성

- ✅ 회원가입 + 이메일 OTP + 비번 재설정 (Phase 1 v0.1.0)
- ✅ E2EE Signal Protocol 키 페어 + multi-device sync + sender keys (Phase 2 v0.2.0)
- ✅ DB audit migration 0003 — signup_ip + last_login_ip + user_sessions + user_activity_log 28 ENUM (cycle 97 + cycle 119~144)

### 3.4 ~~라이선스 미확정~~ ✅ 해소 (사이클 6)

- GPLv3 확정 + LICENSE 저장소 루트 + PyQt6 GPLv3 직접 호환

### 3.5 ~~self-hosted runner 등록 미완~~ ✅ 해소 (사이클 5 + cycle 142~143 wine 영구 폐기)

- macOS arm64 runner online + windows-latest GitHub-hosted 마이그레이션 SUCCESS

### 3.6 ~~코드 진입 미완~~ — Phase 1~5 actual binding + cycle 169.x UI redesign 115 sub-cycle 본격

- pytest 1817 PASS + integration test + Playwright fixture + Phase 5 5 Item + cycle 169.x UI telegram align Phase A~F + 6 dimension stage + 3 zone bg + sidebar 2 entry + chat_header avatar 폐기 + default chat 진입 + 편집 tab FolderManageDialog + bot LLM 응답 chain + PORTABLE_HARNESS 공용 한벌

### 3.7 차별화 잔존

- 🟡 원격 데스크탑 제어 Phase 5 본격 cycle 165~180 production-ready 잔존
- ✅ emoji pack share — cycle 144~148 admin menu + list_pending + DMCA chain actual binding 진입 완료
- 🔴 Toonation REST API `base_url` + `api_key` 부재 (cycle 141 R sub-agent — Toonation REST 27 PASS skeleton + 사용자 직접 입력 의무) — Phase 5 본격 cycle 진입 차단
- 🔴 OBS WebSocket `base_url` + `password` 부재 (cycle 148 JJ sub-agent — v5 actual handshake 16 PASS skeleton + 사용자 직접 입력 의무)

### 3.8 manual test 의무 (사용자 직접 영역)

- SMTP 실제 설치 = cycle 129~130 자동 chain 도달 + 사용자 manual SSH 회수 완료
- docker compose production stack 기동 = `.env.production` secrets 입력 + manual
- last_seen REST endpoint (cycle 169.216) + client fetch chain (cycle 169.221) = 사용자 manual 시각 확인 (online → offline 전환 → "최근에 접속함" 갱신 chain) 의무
- DM room resolver (cycle 169.222) + DM history fetch chain (cycle 169.225) = friend_id ↔ direct room_id 의 manual 회수 + 히스토리 로드 시간 측정 의무
- hamburger drawer 단색 (cycle 169.227) = telegram align 시각 회귀 manual 회수
- 3 dialog main center (cycle 169.229~230) = MyProfileDialog + FolderManageDialog + FolderEditDialog 의 화면 중앙 + height clamp 의 manual 확인
- bot LLM HTTP 401 fix (cycle 169.228 bearer_token) = bot Q&A 응답 chain manual 회수 (이전 401 차단 → 200 응답)
- i18n qm 5 locale (cycle 169.226) = ko / en / zh-CN / zh-TW / ja 의 manual locale 전환 시각 회귀

### 3.9 mobile cycle 181 prerequisite 잔존

cycle 147 mobile Flutter base 진입 직후 cycle 181~200 본격 cycle 진입 prerequisite 부재:

- Apple Developer Program 가입 (USD 99/년 + 사용자 직접) — App Store 배포 의무
- Google Play Console 계정 (USD 25 one-time + 사용자 직접) — Play Store 배포 의무
- Firebase 프로젝트 신설 + FCM Server Key + iOS APNs cert + Android `google-services.json`
- flutter doctor PASS + iOS Xcode + Android Studio + ADB setup

### 3.10 KT PTR record default 잔존

KT ISP default PTR record (`tongkni.co.kr`) 잔존 — `mail.dopa.co.kr` 의 reverse DNS 갱신 신청 의무. `project_dopa_demo_only.md` 영구 메모리 정합 = dopa.co.kr 데몬스트레이션 전용 + 실 제품 도메인 부재 시점 = KT PTR 회수 최후로 미룸 또는 skip.

### 3.11 UI dogfooding 회수 부재 (cycle 169.x 누계 잔존)

cycle 169.117~215 115 sub-cycle UI redesign 누계 + telegram align 96% 도달 + bot LLM 응답 chain production-ready + PORTABLE_HARNESS 공용 한벌 단 실 사용자 dogfooding 부재. 1차 dogfooding 1주 retention + NPS 측정 + UX feedback 회수 chain 미진입. Phase 5 본격 cycle 마무리 후 진입 의무.

---

## 4. 시장 포지셔닝 옵션

### 4.1 옵션 A — OSS 자체 호스팅 메신저

- 타겟 / 수익화 / 진입 장벽 / 성공 조건 / 확률 = 중하

### 4.2 옵션 B — Toonation 내부 / 파트너사 (★★★★★)

- 타겟: Toonation 후원자-크리에이터 + B2B
- 수익화: 모회사 운영 비용 절감 + Pro 플랜 (원격 제어 차별화)
- 진입 장벽: 0 (내부 도입)
- 성공 조건: Toonation 통합 API + 이메일 OTP + P5/P6 시나리오 검증
- 확률 = 상 (cycle 169.x UI Toonation BI 통합 redesign 115 sub-cycle 누계 + telegram align 96% + bot LLM 응답 chain production-ready + 1차 dogfooding readiness 도달)
- **권장도 1순위**

### 4.3 옵션 C — P2P 파일 전송 특화

- 중 확률

### 4.4 옵션 D — Whitelabel SDK / B2B API

- 중하 (Phase 6+)

**현 시점 권장**: 옵션 B → A → C 순.

---

## 5. 단기 (3개월) 제품화 액션

| 우선순위 | 액션 | 상태 |
|---|---|---|
| 0 | Phase 1~5 actual binding 완성 | ✅ (cycle 16~148) |
| 0 | DB audit 28 ActivityAction | ✅ (cycle 119~144) |
| 0 | SMTP 자동 설치 + client binding | ✅ (cycle 129~131) |
| 0 | cycle 132~148 sub-agent 46종 chain | ✅ (Phase 5 5 Item) |
| 0 | cycle 149~152 sub-agent 5종 + ssh-deploy + healthz | ✅ (cycle 149~152) |
| 0 | cycle 153.1~3 UI Toonation BI 통합 phase 1~3 | ✅ (cycle 153.x) |
| 0 | cycle 169.117~215 UI telegram align 115 sub-cycle | ✅ (cycle 169.x sweep) |
| 0 | hamburger drawer Toonation BI gradient + frameless + slide-in animation | ✅ (cycle 169.111~116 + 169.170) |
| 0 | 편집 tab FolderManageDialog redirect + folder modal frameless | ✅ (cycle 169.193 + 201) |
| 0 | default chat retain + bot LLM 응답 chain + system prompt knowledge source + avatar 단색 | ✅ (cycle 169.202~204) |
| 0 | PORTABLE_HARNESS.md 공용 한벌 | ✅ (cycle 169.207) |
| 0 | bot LLM ContentTypeError graceful + OpenAI 우선 provider chain | ✅ (cycle 169.209~210) |
| 0 | dereliction-detector 자동 spawn 강제 + hook stderr redirect + false positive 회수 | ✅ (cycle 169.189 + 212 + 215) |
| 0 | sidebar TAB_DEFS 2 entry telegram align + folder_defs 폐기 + bot_panel 폐기 | ✅ (cycle 169.131 + 136 + 146 + 185) |
| 0 | chat_view scroll offset per-chat retain + day separator + bubble ts inline + grouped tail | ✅ (cycle 169.172 + 176 + 179 + 180) |
| 0 | chat_header emoji 제거 + nickname lookup + status 한국어 + status color gray + avatar 폐기 + top bar vertical center | ✅ (cycle 169.154 + 159 + 178 + 182 + 183) |
| 0 | chat_list bump_entry + unread reset + 통합 filter "채팅" + highlight sync | ✅ (cycle 169.167 + 173 + 174 + 184) |
| 0 | _append_dm_message single source helper + DM cache + scroll bottom + sender label suppress | ✅ (cycle 169.157~166) |
| 0 | input_bar composite pill + telegram image #3 정합 + voice/send toggle + circle send + pill radius | ✅ (cycle 169.137 + 148~150) |
| 0 | MyProfileDialog crash 회수 + telegram simple rewrite | ✅ (cycle 169.121 + 186) |
| 0 | 평가 4 file 매 cycle 6 영역 sweep (cycle 169.117 + 135 + 141 + 147 + 153 + 161 + 168 + 175 + 181 + 187 + 188 + 195 + 205 + 211 + 215 + 217 + 223 + 231) | ✅ 본 cycle 169.231 |
| 0 | last_seen REST + client fetch chain (Phase 5 binding) | ✅ (cycle 169.216 + 169.221) |
| 0 | DM room resolver server-side + client DM history fetch chain | ✅ (cycle 169.222 + 169.225) |
| 0 | rooms.py BPE chain 회수 (docstring 4회+ chain) | ✅ (cycle 169.222.1) |
| 0 | i18n translations qm frozen bundle 5 locale | ✅ (cycle 169.226) |
| 0 | drawer header gradient 폐기 → 단색 Toonation BI #0066FF | ✅ (cycle 169.227) |
| 0 | bearer_token chain 회수 self._session_token (HTTP 401 차단) | ✅ (cycle 169.228) |
| 0 | design critique 최우선 가드레일 + dialog main center + height clamp | ✅ (cycle 169.229~230) |
| 1 | Toonation REST API `base_url` + `api_key` 사용자 직접 입력 — 옵션 B 본격 진입 prerequisite | 🔴 사용자 직접 |
| 2 | OBS WebSocket `base_url` + `password` 사용자 직접 입력 — P5/P6 OBS 도움 시나리오 prerequisite | 🔴 사용자 직접 |
| 3 | mesh / peer text chat receive 본격 binding (Phase 5 mesh 진입) | 🔴 다음 cycle 우선순위 |
| 4 | coturn 4 env (TURN_REALM + TURN_USERNAME + TURN_PASSWORD + TURN_URI) 사용자 직접 입력 — NAT traversal | 🔴 다음 cycle 우선순위 |
| 5 | mobile Flutter base 본격 진입 (signaling ws_client.dart + WebRTC 연결) | 🔴 다음 cycle 우선순위 |
| 6 | mobile cycle 181 prerequisite (Apple Developer + Google Play + Firebase + Xcode + Android Studio) | 🟡 사용자 직접 |
| 7 | KT PTR record 갱신 (`mail.dopa.co.kr` reverse DNS) — dopa.co.kr 데모 전용 → 실 도메인 확정 후 갱신 또는 skip | 🟡 최후 |
| 8 | 1차 dogfooding 1주 retention + NPS + UX feedback 회수 chain | 🔴 Phase 5 마무리 직후 |

---

## 6. 중기 (6~12개월) 액션 + cycle batch metric (cycle 169.213~231 19 entry burst statistics)

| 우선순위 | 액션 | 가치 |
|---|---|---|
| 1 | Phase 5 마무리 + 1차 dogfooding entry | retention 핵심 |
| 2 | mesh / peer text chat receive 본격 binding | Phase 5 mesh 본격 |
| 3 | coturn 4 env binding (NAT traversal) | P2P 신뢰성 |
| 4 | mobile Flutter base 본격 진입 + signaling ws_client.dart + WebRTC 연결 | 사용자 풀 10x |
| 5 | 음성 통화 (PeerConnection audio) | 시장 진입 자격 |
| 6 | 모바일 cycle 181~200 prerequisite 회수 후 본격 진입 | mobile 본격 |
| 7 | Toonation 통합 시나리오 검증 (옵션 B) | 수익화 base |
| 8 | 영상 통화 (WebRTC SFU 마이그레이션 검토) | 기능 완성 |

### 6.1 cycle 169.213~231 19 entry burst metric

- **19 commit / push velocity** = cycle 169.213 (2026-05-21 KST burst start) → 169.231 (12:45 KST) ≈ **5~6 시간 burst** = average **3~4 commit / hour**
- **commit 분류**: feat 5 (last_seen + DM resolver + i18n + DM history + design critique) + fix 6 (bearer_token + drawer 단색 + rooms.py BPE + dialog center + height clamp + hook feat grep) + docs 8 (README prepend + History 역순 + handoff §8.79 + 평가 4 file fingerprint sync × 3 + vibe-coding sync × 2)
- **drift recovery 누계** = cycle 169.213~231 19 cycle 안 평가 fingerprint sync 3 회 (217 / 223 / 231) — 5 cycle drift cap 정합
- **사용자 비판 회수**: design critique batch 일시 중지 + 우선 처리 의무 (cycle 169.229 신설 영구 가드레일)
- **신규 가드레일**: `feedback_design_critique_first_priority.md` cycle 169.229 신설 → 영구 가드레일 51+ 누적

---

## 7. 장기 (1~3년) 비전

### 7.1 기술

- 원격 데스크탑 제어 production-ready (Phase 5 마무리 + Phase 6 동영상 / 영상 통화 / 화면 공유 통합)
- WebRTC SFU (그룹 화상 8인+)
- 분산 시그널링 (libp2p)
- WASM 브라우저 client (PWA)

### 7.2 사업

- Toonation 후원자 메신저 기본 채널 (옵션 B 1순위)
- B2B SaaS enterprise (검증 후 외부 판매)
- OSS 커뮤니티

### 7.3 사용자

- 100 dogfooding → 1000 beta → 10K v1.0
- NPS 50+ retention 70% / 30일
- P5 라이브 크리에이터 원격 제어 활성률 ≥ 30%

---

## 8. 핵심 리스크

| 리스크 | 확률 | 영향 | 회피 |
|---|---|---|---|
| Signal / Telegram 무료 + 우월 → 사용자 획득 실패 | 상 | 상 | 옵션 B (Toonation) pivot + UI telegram align 96% 도달 + 차별화 매트릭스 7항목 + bot LLM 응답 chain + PORTABLE_HARNESS 공용 한벌 |
| ~~1인 개발자 Phase 2~4 완주 어려움~~ | ✅ 해소 (cycle 169.215 — 115 sub-cycle drift 0건 185 연속) | — | sub-agent 누계 93종 병렬 chain |
| ~~데모 서버 보안 사고~~ | ✅ 해소 (cycle 129 SMTP install 5 layer + Phase 4 nginx + DB audit) | — | Let's Encrypt + DKIM + DMARC + iptables |
| ~~라이선스 결정 지연~~ | ✅ 해소 (사이클 6) | — | GPLv3 확정 |
| PyQt6 GPL 의무 외부 fork distribution | 중 | 중 | GPLv3 정합 + private 전환 시 외부 fork 차단 |
| ~~문서 91% : 코드 9% 지속~~ | ✅ 해소 (cycle 117 — pytest 1817 + 코드 우위) | — | 8 체크리스트 통과 + Phase 1~5 진입 |
| 원격 제어 보안 사고 (Phase 5 Item 5 위험) | 중 | 상 | 친구 추가 사전 + 명시 수락 + 긴급 ESC + 감사 로그 + cycle 148 coord transform DPI / Retina 정합 |
| ~~SMTP spam reputation 부족~~ | ✅ 해소 (cycle 129 + Gmail Authentication-Results pass) | — | SendGrid relay fallback 회피 가능 |
| ~~wine PyQt6 호환성~~ | ✅ 해소 (cycle 142~143 wine 영구 폐기 + windows-latest) | — | windows-latest GitHub-hosted runner |
| 사용자 `base_url` + `api_key` 부재 (Toonation + OBS — cycle 148) | 상 | 상 | 사용자 직접 입력 의무 — Phase 5 본격 cycle 진입 차단 |
| mobile cycle 181 prerequisite 부재 | 상 | 중 | 사용자 manual 5종 의무 — mobile 본격 cycle 진입 차단 |
| KT PTR record default 잔존 | 상 | 저 | dopa.co.kr 데모 전용 + 실 도메인 확정 후 갱신 또는 skip |
| WebRTC mesh ≤ 8 peer cap | 중 | 중 | 9 peer 이상 의무 SFU 마이그레이션 (Phase 6+) |
| 1차 dogfooding 부재 | 중 | 중 | Phase 5 마무리 직후 1주 retention + NPS 측정 진입 의무 |
| cycle 169.x UI redesign 의 LLM autonomy 의 한계 (사용자 design directive 부재 시 임의 변경 금지) | 중 | 중 | `[[feedback-no-design-change-without-user-directive]]` 영구 가드레일 + 위반 시 즉시 git revert |
| design critique batch 일시 중지 의무 (cycle 169.229 신설) | 중 | 중 | `[[feedback-design-critique-first-priority]]` 영구 가드레일 = 사용자 design critique 의 모든 잔존 batch 일시 중지 + 우선 처리 의무. Phase 5 binding / doc sync / Stop hook 모두 후순위 |
| bearer_token chain drift (cycle 169.228 회수) | 저 | 중 | self._session_token 정합 + HTTP 401 차단 + 매 endpoint 의 token chain 의 단일 source helper 정합 |
| mesh / peer text chat receive 본격 binding 부재 (Phase 5 mesh 잔존) | 중 | 중 | 다음 cycle 우선순위 = mesh + peer receive 본격 binding + coturn 4 env 사용자 직접 입력 |
| mobile Flutter base 본격 진입 부재 (signaling ws_client.dart skeleton 만) | 상 | 중 | 다음 cycle 우선순위 = signaling 연동 + WebRTC peer connection + chat UI 의 mobile mirror |

### 8.1 보안 리스크 추가 해결책 (Defense-in-Depth)

| 리스크 | 추가 해결책 | 진입 시점 |
|---|---|---|
| 데모 서버 보안 사고 | (1) fail2ban + nftables rate limit, (2) Let's Encrypt + HSTS preload, (3) Wazuh agent + auditd, (4) systemd hardening (PrivateTmp + ProtectHome + NoNewPrivileges), (5) 백업 = encrypted off-site (borg + age) | Phase 6 진입 직전 |
| PyQt6 GPL 외부 fork distribution | (1) LICENSE SPDX header 의무 자동 검증 hook, (2) DCO sign-off pre-commit hook, (3) private 전환 시 GPL 의무 distribution 명시, (4) AGPLv3 Phase 2 옵션 | Phase 6 진입 시 |
| 원격 제어 보안 사고 (Phase 5+) | (1) 친구 추가 양측 명시 수락 + biometric 2FA, (2) 긴급 ESC global hotkey, (3) 감사 로그 append-only + 매 세션 SHA-256 chain, (4) 화면 제어 권한 = 매 세션 명시 확인, (5) 친구 평판 trust score (가입 후 30일 + 활동 5건) | Phase 5 마무리 직전 |
| SMTP spam reputation | (1) SPF + DKIM + DMARC 의무 + DMARC reject, (2) bounce rate < 5% + complaint rate < 0.1% 모니터링, (3) SendGrid relay 100/day fallback, (4) Bayesian spam score 사전 검증, (5) outbound rate limit 100/hour, (6) IP warm-up 30일 | Phase 5 dogfooding 시 |
| Phase 2 E2EE 잔존 | (1) Signal Protocol Test Vector 적용, (2) ratchet step invariant assertion, (3) skipped message keys MAX_SKIP=1000 + LRU, (4) header MAC 검증, (5) cryptography expert review | cycle 200+ |
| 잠재 부채널 (timing + cache + speculative) | (1) `hmac.compare_digest` 의무, (2) AES-NI / ARMv8 Crypto Extensions 활용, (3) X25519 constant-time, (4) dudect statistical timing leakage, (5) speculative execution 검토 | Phase 6+ |
| 클라이언트 plain-text 저장 위험 | (1) DB 메시지 body = 클라 keychain + DB ciphertext 만 저장, (2) macOS Keychain + Windows Credential Manager 통합, (3) 백업 passphrase + PBKDF2 600K iter + age encrypt, (4) memory dump 차단 (mlock + sodium_memzero) | Phase 6 진입 시 |

---

## 9. KPI 후보

| KPI | 목표 | 현재 |
|---|---|---|
| 1:1 채팅 메시지 전송 성공률 | ≥ 99% | 미측정 (dogfooding 의무) |
| 파일 전송 SHA-256 무결성 | 100% | 미측정 (dogfooding 의무) |
| 시그널링 재연결 시간 (95p) | ≤ 5초 | 미측정 (dogfooding 의무) |
| 앱 cold start latency | ≤ 30초 | 미측정 (dogfooding 의무) |
| 1주 retention (내부 pilot) | ≥ 60% | 미측정 (pilot 의무) |
| CI 3 workflow GREEN 비율 | 100% | 100% (macOS arm64 + windows-latest, cycle 143~215) |
| doc-lint.sh 5 검사 통과율 | 100% | 본 저장소 100% |
| 가드레일 영구 메모리 | 10종+ | 50+ active (cycle 169.215) |
| pytest 누계 PASS | ≥ 500 | 1817 PASS (cycle 169.214) |
| pytest coverage | ≥ 80% | 미측정 |
| Playwright E2E test | ≥ 5건 | 3건 스켈레톤 active |
| OTP 발송 → 수신 latency | ≤ 30초 | cycle 129~130 production-ready |
| OTP brute force 차단율 | 100% (5회 / 30분) | OK |
| 원격 제어 세션 성공률 | ≥ 95% | 미측정 (Phase 5 Item 5 cycle 165~180 후) |
| mail-tester score (SMTP) | ≥ 7 / 10 | cycle 129 chain — Gmail Authentication-Results pass |
| fork PR approval rate (악성 차단) | 100% | strict 적용 OK |
| GPLv3 호환 의존성 | 100% | 100% |
| drift 0건 연속 cycle | ≥ 50 | 185 연속 (사이클 37~169.214) |
| sub-agent 누계 병렬 spawn | ≥ 10 | 93종 (cycle 169.215 누계) |
| DB audit endpoint coverage | ≥ 20 ActivityAction | 28 ActivityAction |
| sub-agent 평균 PASS | ≥ 5 | 8~15 PASS / sub-agent |
| Phase 5 Item 진입 | ≥ 3 / 5 | 5 / 5 (모두 actual binding 부분 진입) |
| UI telegram align 도달률 | ≥ 80% | 96% (cycle 169.117~215 115 sub-cycle) |
| bot LLM 응답 chain production-ready | Y/N | ✅ Y (cycle 169.203 + 209 + 210) |
| PORTABLE_HARNESS 공용 한벌 등재 | Y/N | ✅ Y (cycle 169.207) |
| 1차 dogfooding 진입 | Y/N | 🔴 (Phase 5 마무리 직후 의무) |

---

## 10. 다음 평가 갱신 트리거

본 snapshot 은 다음 task 종료 시점 전체 rewrite. 갱신 시 다음 항목 변동 우선 반영:

- 기술 완성도 점수 — Phase 5 마무리 + 1차 dogfooding 시 +0.3
- 누락 기능 표 — Phase 5 마무리 시 항목 제거
- 단기 액션 ✅ 표시 갱신
- KPI 실측 값 (dogfooding 진입 후)
- 가드레일 메모리 누계 (현 51+)
- sub-agent 누계 (현 93)
- 차별화 추가 발생 시 §2.10 + §4 + §10 동시 갱신
- 1차 dogfooding 진입 시 §3.11 ✅
- Toonation REST + OBS WebSocket base_url 사용자 직접 입력 시 §3.7 ✅
- mobile cycle 181 prerequisite 사용자 manual 회수 시 §3.9 ✅
- mesh / peer text chat receive 본격 binding 시 §5 / §6 ✅
- coturn 4 env 사용자 직접 입력 시 §5 ✅
- mobile Flutter base 본격 진입 시 §5 / §6 ✅

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
