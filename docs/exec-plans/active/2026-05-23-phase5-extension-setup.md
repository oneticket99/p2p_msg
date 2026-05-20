---
title: "TooTalk Phase 5 — extension setup plan"
owner: oneticket99
last_verified: 2026-05-20
status: finalize
phase: 5
---

> **finalize ack (cycle 169.73)** — Phase 5 priority 재 배치 영구화:
>
> 1. i18n 5 locale + tr() wrap 완성 (cycle 144~148 PASS)
> 2. emoji pack share 차별화 (sticker / custom emoji 공개 공유)
> 3. bot framework 마무리 (BotFather + Bot API + webhook + inline + payment + 공개 디렉토리)
> 4. 원격 데스크탑 제어 본격 (친구 A OBS ↔ 친구 B 도움자 chain — cycle 166+ prerequisite)
> 5. mobile Flutter 가장 마지막 (cycle 181+ — libsignal-dart + Apple/Google/Firebase 사용자 manual)
> 6. 4 streaming platform actual binding (YouTube/Twitch/CHZZK/Kick — OAuth + API key)
> 7. KT PTR reverse DNS — 최후 또는 skip (dopa.co.kr 데모 전용)

# Phase 5 — TooTalk 확장 plan (initial draft)

> 본 plan = cycle 117 Phase 4 production infra base 완성 직후 Phase 5 진입 base.
> 정합: [phase4-infra-setup.md](2026-05-22-phase4-infra-setup.md) §1.3 + handoff §8.54.5 우선순위 5.
> 본 plan 의 실 진입 = 사용자 명시 GO directive 의무 (현 = 검토 단계).

---

## 1. 본 계획 개요

### 1.1 범위

Phase 5 = TooTalk 의 **확장 단계**. Phase 1~4 의 메신저 base + bot framework + production infra 완성 직후 의 시장 확장 + 차별화 강화. 다음 5 영역:

1. **다국어 (i18n)** — 영어 + 중국어 (간체/번체) + 일본어 system prompt + UI 문자열 i18n.
2. **모바일 (iOS / Android)** — Flutter 또는 native + WebRTC 호환 + push 알림 통합.
3. **차별화 — emoji pack share** — Telegram sticker / custom emoji pack 등가 + 공개 디렉토리 + 누구나 사용 가능.
4. **bot framework 마무리** — Toonation API 직접 통합 (옵션 B) + 방송 도우미 봇 OBS WebSocket + 4 streaming platform (YouTube / Twitch / CHZZK / Kick) + 외부 개발자 봇 등록 + 공개 디렉토리.
5. **원격 데스크탑 제어 본격 진입** — Phase 3 cycle 57~58 skeleton 의 production-ready 완성. patternA (도움) + patternB (제어) + screen capture + input forward + WebRTC DataChannel multiplex.

### 1.2 사용자 directive 누계

- 2026-05-17 emoji pack share (Phase 3+)
- 2026-05-17 + 2026-05-20 + 2026-05-21 bot framework 마무리
- 2026-05-21 원격 데스크탑 제어 차별화 (cycle 57~58 base)
- 2026-05-22 Phase 4 종결 직후 진입 검토 directive

### 1.3 의무

- 4 item 순서 priority — i18n 우선 (사용자 base 확장 base) → mobile → emoji pack → bot framework 마무리 → 원격 제어.
- 매 item 의 commit 단위 = 1 cycle 1 commit (M5 정합).
- ③ 단계 chain (reviewer + qa + observability) 의무.
- manual test 의무 항목 (MANUAL_TESTS.md §2 갱신).

---

## 2. Item 1 — 다국어 (i18n) 진입

### 2.1 범위

- UI 문자열 i18n (PyQt6 QTranslator + .ts/.qm 파일 chain).
- bot framework system prompt 의 다국어 분기 (Korean default + en/zh-CN/zh-TW/ja 4 alt).
- 이메일 OTP 본문 의 다국어 분기.
- 회원가입 + 로그인 + reset 의 form label 의 다국어.

### 2.2 컴포넌트

| 영역 | 변경 | cycle |
|---|---|---|
| `app/i18n/` | 신설 — locale loader + Qt translator manager | 130~131 |
| `app/i18n/strings/` | en.ts + zh-CN.ts + zh-TW.ts + ja.ts + ko.ts (5 locale) | 132~134 |
| `server/templates/email/` | OTP 본문 5 locale | 135 |
| `app/bot/customer_service_bot.py` | system_prompt 의 LANG env 분기 | 136 |
| `app/ui/` | 모든 string Qt tr() wrap | 137~139 |

### 2.3 manual test 의무

- 사용자 의 5 locale 의 OTP 메일 수신 검증.
- UI 의 locale 전환 (Settings + LANG env) 의 한글 → 영어 → 중국어 → 일본어 검증.

---

## 3. Item 2 — 모바일 (iOS / Android)

### 3.1 기술 선택지

| 선택지 | 장점 | 단점 |
|---|---|---|
| **Flutter + dart aiortc 등가** | 단일 codebase + UI 빠름 | aiortc dart binding 미성숙 |
| **React Native + react-native-webrtc** | WebRTC 안정 + JS ecosystem | UI 의 platform-specific divergence |
| **native (Swift / Kotlin)** | 성능 + native API | 2 codebase 의 의무 |

권장 default = **Flutter + flutter-webrtc** (Phase 5+ 검토 시점 의 사용자 confirm 의무).

### 3.2 컴포넌트

- `mobile/` 디렉토리 신설 (Flutter project).
- WebRTC DataChannel 의 dart binding (`flutter_webrtc`).
- 시그널링 WS client (Phase 1~2 의 protocol 정합).
- Push 알림 (FCM mobile SDK + cycle 103~104 의 server 영역 정합).
- E2EE (libsignal-dart 또는 자체 X25519 + AES-GCM dart 구현).

### 3.3 manual test 의무

- iOS + Android 의 실 device 의 실 회원가입 + 채팅 + 파일 송수신 smoke.
- push 알림 의 background + foreground 의 양쪽 검증.

---

## 4. Item 3 — emoji pack share (차별화)

### 4.1 범위

- TooTalk 의 텔레그램 sticker / custom emoji pack 등가 + 공개 디렉토리 + 누구나 사용 가능.
- emoji pack 생성 + 업로드 + 검색 + 다운로드 + 사용 의 5 flow.
- moderation chain (jailbreak detector 정합 + 부정 image 차단).

### 4.2 컴포넌트

| 영역 | 변경 | cycle |
|---|---|---|
| `server/db/migrations/0004_emoji_pack.sql` | emoji_packs + emoji_pack_items 2 테이블 | 140 |
| `app/emoji/` | sticker viewer + 업로드 dialog | 141~142 |
| `server/api/emoji_handlers.py` | 5 REST endpoint (create + search + download + list + delete) | 143~144 |
| `app/ui/ChatView` | emoji picker 통합 | 145 |
| `docs/policies/emoji-pack.md` | 정책 본문 (moderation + license + DMCA) | 146 |

### 4.3 보안 의무

- 업로드 image 의 MIME 검증 + 크기 cap (1 MB / item).
- jailbreak detector 의 image-to-text OCR + 부정 컨텐츠 차단.
- DMCA takedown chain (별개 cycle).

---

## 5. Item 4 — bot framework 마무리

### 5.1 범위

- 투네이션 고객센터 봇 (default) 의 Toonation API 직접 통합 (옵션 B 핵심).
- 방송 도우미 봇 (별개 API) 의 OBS WebSocket + 4 streaming platform 통합.
- 외부 개발자 봇 등록 + 공개 디렉토리 (Telegram BotFather 등가).

### 5.2 컴포넌트

| 영역 | 변경 | cycle |
|---|---|---|
| `app/bot/toonation_client.py` | Toonation REST API client (donation + payout + user 조회) | 150~151 |
| `app/bot/customer_service_bot.py` | Toonation client 의 통합 (RAG 의 추가 source) | 152 |
| `app/bot/streaming_helper.py` | OBS WebSocket actual binding (cycle 67 placeholder 회수) | 153 |
| `app/bot/streaming_platforms/` | YouTube + Twitch + CHZZK + Kick 4 client | 154~157 |
| `server/api/bot_directory_handlers.py` | 외부 개발자 봇 등록 + 공개 list endpoint | 158~159 |
| `docs/policies/bot-framework.md` | §10 잔존 항목 strike-through + §11 외부 봇 등록 정책 | 160 |

### 5.3 manual test 의무

- Toonation 실 API key + 실 donation history 조회 smoke.
- OBS WebSocket 실 instance + 명령 chain 검증.
- 4 streaming platform 의 callback 의 실 stream key + 메시지 수신 smoke.

---

## 6. Item 5 — 원격 데스크탑 제어 본격 진입

### 6.1 범위

- Phase 3 cycle 57~58 의 skeleton 의 production-ready 완성.
- patternA = 도움 (controller 의 target screen 보기 만).
- patternB = 제어 (controller 의 target 키보드/마우스 OS 적용).
- screen capture (macOS Quartz + Windows GDI + Linux X11/Wayland) + input forward (PyObjC CGEvent + win32 + xdotool).

### 6.2 컴포넌트

| 영역 | 변경 | cycle |
|---|---|---|
| `app/remote/capture_macos.py` | Quartz CGDisplayCreateImage 실 binding + CFRelease 의무 | 165~166 |
| `app/remote/capture_windows.py` | win32 BitBlt 실 binding | 167 |
| `app/remote/input_forward_macos.py` | CGEventCreateMouseEvent + CGEventCreateKeyboardEvent 실 binding | 168~169 |
| `app/remote/input_forward_windows.py` | SendInput 실 binding | 170 |
| `app/remote/protocol.py` | WebRTC DataChannel multiplex (screen + input) chain | 171~172 |
| `app/ui/RemoteView` | screen viewer + 컨트롤 toggle | 173~175 |
| `docs/policies/remote-control.md` | 보안 + 권한 + 감사 정책 | 176 |

### 6.3 보안 의무

- target 의 명시 동의 의무 (1회 directive + per-session ack).
- 화면 capture 의 PII 차단 (algorithmic blur + 사용자 toggle).
- audit log 의 모든 키 입력 + 마우스 클릭 의 trace (DB audit migration 0003 정합 — REMOTE_GRANT + REMOTE_REVOKE 의 23 ENUM 정합).

---

## 7. 누적 cycle 의 예상 + 진행 순서

**진행 순서 — 사용자 directive 2026-05-19 정합** ([[project-phase5-mobile-last]]):

| 순서 | Item | cycle 범위 | 누계 |
|---|---|---|---|
| 1 | Item 1 i18n | 131~140 | 10 cycle |
| 2 | Item 3 emoji pack share | 141~150 | 10 cycle |
| 3 | Item 4 bot 마무리 | 151~165 | 15 cycle |
| 4 | Item 5 원격 제어 본격 | 166~180 | 15 cycle |
| 5 | **Item 2 mobile (가장 마지막)** | 181~200 | 20 cycle |

**Phase 5 누계 = 70 cycle 추정** (Phase 4 의 18 cycle 의 약 4배 — mobile codebase 별개 + Flutter / dart binding / libsignal-dart / FCM mobile SDK 의 추가 prerequisite).

**Item 2 mobile 의무 prerequisite**: Item 1 (i18n) + Item 3 (emoji pack share) + Item 4 (bot framework 마무리) + Item 5 (원격 제어) 의 모든 완료 후 진입. 데스크탑 client (PyQt6) 완전 안정화 + 차별화 emoji + bot production + 원격 제어 본격 도입 후 mobile dogfooding base 확보 정합.

---

## 8. 본 계획 의 의무

- M5 정합 — 매 cycle 1 commit + push.
- 매 cycle ③ chain — reviewer + qa + observability.
- 매 cycle 평가 snapshot 4 영역 + HTML 2 mirror sweep 의무 ([[feedback-assessment-full-section-sweep]]).
- 사용자 manual test 의무 항목 (MANUAL_TESTS.md §2 갱신).

---

## 9. 참조

- [Phase 4 plan](2026-05-22-phase4-infra-setup.md)
- [Phase 1 MVP plan](2026-05-17-tootalk-phase1-mvp.md)
- [bot framework 정책](../../policies/bot-framework.md)
- memory `project_emoji_pack_share.md` — `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_emoji_pack_share.md` (Phase 3+ emoji pack 차별화)
- memory `project_bot_framework.md` — `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_bot_framework.md` (Phase 3 마무리 + Phase 5 본격)
- memory `project_phase2_remote_control_differentiator.md` — `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_phase2_remote_control_differentiator.md` (원격 제어 차별화)
