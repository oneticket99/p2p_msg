---
title: "텔레그램 데스크톱 UI 14 영역 조사 — TooTalk redesign 의 base"
owner: oneticket99
last_verified: 2026-05-19T23:50:00+09:00
status: active
cycle: 152.5
phase: Phase 5 UI redesign prereq
---

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- 텔레그램 데스크톱 UI 14 영역 조사 manifest — 사용자 directive 2026-05-19 cycle 152.5 "지금부터 텔레그램의 각 레이아웃 다 조사해" 회수. TooTalk redesign base. cycle 153~ frontend-design skill 본격 entry prereq. -->

# 텔레그램 데스크톱 UI 14 영역 조사 manifest

> 본 doc = 텔레그램 데스크톱 (tdesktop) UI 각 영역 의 구조 + 색상 + 상호작용 패턴 조사 누적. TooTalk 본격 redesign (cycle 153~) base. 사용자 screenshot + WebSearch + tdesktop 공식 GitHub 자료 통합.
>
> 정합 = [[project-p2p-msg-overview]] (텔레그램 모델 참고) + [[feedback-design-interactive-html]] (HTML interactive 권장) + cycle 152 SSH deploy chain 완료 직후 진입.

---

## 0. 조사 방법론

| 자료 | 신뢰도 | 사용 시점 |
|---|---|---|
| 사용자 screenshot 직접 paste | ★★★★★ | 정확 layout 추출 |
| tdesktop GitHub source (https://github.com/telegramdesktop/tdesktop) | ★★★★★ | 색상 / 위젯 hierarchy 정합 |
| telegram.org/blog | ★★★★ | 최신 변경 history |
| Figma Community Telegram UI Screens | ★★★ | reference 디자인 |
| Dribbble / Medium / createbytes UX 분석 | ★★ | inspiration |

---

## 1. Welcome 화면 (intro)

**사용자 screenshot ack 2026-05-19**

| 영역 | 본문 |
|---|---|
| 상단 banner | navy `#0F172A` ~ blue gradient + 종이비행기 logo center + cloud illustration + 7 icon cluster (mic + music + camera + chat + lock + photo + emoji) |
| 타이틀 | "Telegram Desktop" 큰 bold |
| sub | "공식 텔레그램 데스크톱 앱에 오신 것을 환영합니다." + "빠르고 안전합니다." 2 line gray |
| CTA primary | "시작하기" 파란 full-width button (color `#3390EC` 등가) |
| 보조 link | "Continue in English" 파란 link (locale switch) |
| bg | dark `#1a1a1a` |

**TooTalk 등가 design**:
- banner = Toonation primary `#0066FF` + cloud + 8 icon (mic + WAV + 카메라 + chat + lock + emoji + 원격 + bot)
- 타이틀 = "TooTalk"
- sub = "친구와 직접 연결 P2P 메신저" + "원격 데스크탑 도움 + GPLv3 OSS"
- CTA = "시작하기" → `LoginDialog`
- 보조 = "한국어 | English | 中文 | 日本語" 4 locale switch row

---

## 2. Login — phone number entry

**텔레그램 본문 (자료 + 일반 패턴 추론)**:

| 영역 | 본문 |
|---|---|
| 상단 logo | 작은 종이비행기 circular |
| 타이틀 | "당신의 휴대전화" |
| sub | "휴대전화 번호 입력 (국제 형식)" |
| input | 국가 dropdown (flag + name + +xx code) + 전화번호 input |
| CTA | "다음" full-width 파란 button |
| 보조 | "Continue in English" link bottom |

**TooTalk 등가 = email 기반 (Phase 1 directive)**:
- email input + "@" suffix highlight
- username input (handle)
- password input + show/hide 토글
- CTA = "회원가입" + "이미 계정 있음? 로그인"

---

## 3. OTP code verify

**텔레그램 본문**:

| 영역 | 본문 |
|---|---|
| 상단 logo | 작은 |
| 타이틀 | 전화번호 표기 + edit pencil icon |
| sub | "사용자 다른 텔레그램 앱 안 6자리 코드 송신" |
| input | 6 digit code box (각 box 분리 + auto-advance) |
| 보조 link | "코드 재 송신" + "SMS 송신 요청" |

**TooTalk 등가**:
- email 표기 + edit
- "OTP 6 digit 메일 송신 (3분 유효)" sub
- 6 box input (auto-advance + paste 지원)
- "재 송신 (남은 횟수 N/5)" link

---

## 4. Password 2FA (cloud password)

**텔레그램 본문 (Telegram SRP 6a 정합)**:

| 영역 | 본문 |
|---|---|
| 상단 lock icon | 큰 padlock illustration |
| 타이틀 | "Cloud Password" |
| sub | "사용자 cloud password 입력" |
| input | password (mask) + show/hide |
| 보조 | "비밀번호 잊었음" link |

**TooTalk 등가**:
- 2FA = Phase 2~3 진입 시점 entry (현 미진입)
- placeholder skeleton 만 cycle 153~

---

## 5. 메인 화면 — 3 column layout

**텔레그램 본문 (사용자 screenshot 26 정합)**:

| column | 본문 |
|---|---|
| Left rail (icon column) | width 64~80px + folder icon vertical + badge unread count + 검색 + 새 chat + profile circle bottom |
| Middle (chat list) | width 280~320px + 검색 bar top + chat row (avatar + name + last message + timestamp + unread badge) + pinned 표기 (📌) + 우선순위 sort |
| Right (chat view) | flex remainder + header (avatar + name + status + 검색 + 통화 + sidebar + menu) + message bubble area + input bar bottom |

**TooTalk 등가 mapping**:
- left rail = 친구 / 방 / 봇 / 설정 4 tab vertical
- middle = FriendList + GroupRoomList + 검색 통합
- right = ChatView (현 단일 column만) → 3 column 전환 의무

---

## 6. 채팅 view — message bubble + 첨부 + reaction + reply

**텔레그램 본문**:

| 영역 | 본문 |
|---|---|
| message bubble self | 우측 + 연두 gradient `#dcf8c6` → `#b7e89c` + tail right |
| message bubble peer | 좌측 + 흰색 `#ffffff` + tail left |
| timestamp | bubble 안 우측 하단 회색 + read receipt ✓✓ |
| reply | 메시지 위 thin border-left + 원본 발신자 + 첫 line preview |
| reaction | bubble 우측 하단 pill (emoji + count) — double-tap quick + tap once panel |
| reaction picker | radial popup + frequent top + 전체 emoji list |
| 첨부 | image thumbnail inline + video preview + file row (icon + name + size + download) |
| sticker | 큰 image bubble 없이 + 단독 표시 + animated lottie |
| voice message | waveform + duration + play button + speed 1x/1.5x/2x |
| forward | "from {name}" 헤더 + 메시지 body |
| 입력 bar | 첨부 icon + emoji icon + text input multi-line + voice mic + send button |

**TooTalk 현재 vs 등가**:
- bubble 색상 ✅ (cycle 152.4 fix)
- reply 부재 → cycle 153 entry
- reaction 부재 → cycle 154 entry
- 첨부 ✅ (file chunk transfer + 진행 widget)
- sticker / emoji picker 부재 → Phase 5 entry (cycle 140~146)
- voice message 부재 → Phase 5 진입 prereq
- forward 부재 → cycle 154

---

## 7. 친구 / contact 추가

**텔레그램 본문**:

| 영역 | 본문 |
|---|---|
| 검색 | global 검색 bar — 사용자명 / 전화번호 / 메시지 |
| QR code scan | "Add Contact" QR scan |
| invite link | t.me/{username} share |
| contact import | 전화 contact 자동 매치 |

**TooTalk 등가**:
- email 검색 + username 검색
- QR code = 친구 invite link generate (uuid 32 hex)
- 친구 요청 chain (cycle 144 friends REST 8 endpoint 정합)

---

## 8. 그룹 / channel 생성

**텔레그램 본문**:

| 영역 | 본문 |
|---|---|
| 메뉴 진입 | New Group / New Channel / New Chat |
| dialog | 사진 upload + 이름 + 설명 |
| 멤버 선택 | contact list checkbox + 검색 |
| 권한 | admin role + permission matrix |
| privacy | public link (t.me/group_id) / private |

**TooTalk 등가**:
- New Room dialog (cycle 135 rooms REST 정합)
- room_code 32 hex unique
- 친구 invite chain (cycle 147 rooms invite endpoint)
- mesh ≤ 8 peer cap (current)

---

## 9. 설정 (Settings)

**텔레그램 본문**:

| section | 본문 |
|---|---|
| 계정 | profile 사진 / 이름 / username / bio / 전화번호 |
| 개인정보 | last seen + 사진 + invite + 통화 + 메시지 + 활성 session |
| 보안 | 2FA + passcode lock + active sessions |
| 알림 + 소리 | message + group + channel + reaction + 통화 + system + in-chat |
| 데이터 + 저장공간 | 자동 download (cellular/wifi/roaming) + 캐시 size + storage usage |
| 채팅 themes | bubble color + background + font size |
| 언어 | 14+ locale (한국어 + English + 中文 + 日本語 + …) |
| 디바이스 | 활성 device list + 종료 |
| 폴더 | custom 폴더 + 자동 필터 |
| 고급 | 네트워크 사용량 + 디버그 + 클라이언트 정보 |

**TooTalk 등가 mapping**:
- 계정 = email + username + bio + avatar
- 보안 = E2EE Signal + 자동 로그아웃 + jailbreak detect
- 알림 = signature sound (cycle 132 WAV) + 음소거 + per-friend mute
- 데이터 = chat_history_policy (cycle 119+) + auto-download cap
- themes = Toonation 5 컬러 + dark/light
- 언어 = 5 locale (ko/en/zh-CN/zh-TW/ja) cycle 132~149
- 디바이스 = devices endpoint (cycle 119) actual binding

---

## 10. 프로필 view

**텔레그램 본문**:

| 영역 | 본문 |
|---|---|
| header | 큰 avatar + 이름 + status (online / last seen N min ago) |
| info | 전화 + username + bio |
| 통화 + 메시지 + mute + 차단 | 4 button row |
| 공통 그룹 | "Groups in common" list |
| 미디어 | media tab + files + links + voice |

**TooTalk 등가**:
- avatar + username + status + bio
- 통화 (cycle 200+ 진입) + 메시지 + 음소거 + 차단 4 button
- 공통 방 list
- 미디어 + 파일 + sticker tab

---

## 11. 검색 (Global Search)

**텔레그램 본문**:

| 영역 | 본문 |
|---|---|
| 검색 bar top | 키 입력 시 즉시 result |
| result section | Chats / Contacts / Messages / Channels / Bots 분류 |
| filter | from user + date range + has media |
| 메시지 검색 | 채팅 내부 + 전역 |
| 다음 / 이전 | 결과 안 navigation arrow |

**TooTalk 등가**:
- chat 안 검색 = ChatView 본문 안 substring (cycle 119+)
- 친구 검색 = email + username (cycle 144)
- 방 검색 = room_code (cycle 135)
- 전역 검색 = cycle 154+ entry

---

## 12. sticker / emoji picker

**텔레그램 본문**:

| 영역 | 본문 |
|---|---|
| picker popup | 입력 bar 안 emoji 아이콘 click |
| tab row | Smileys + Animals + Food + Activity + Travel + Objects + Symbols + Flags + Custom |
| sticker pack | grid + animated preview + add/remove |
| emoji 검색 | 키워드 입력 시 filter |
| 최근 사용 | 별도 tab + sticky top |
| custom emoji | premium + custom emoji pack |

**TooTalk 등가 (cycle 140~146 Phase 5)**:
- emoji pack share = Phase 3+ 차별화 ([[project-emoji-pack-share]])
- sticker / custom emoji pack 등록 + 공개 디렉토리
- DMCA phash fuzzy check (cycle 150)
- moderation queue (cycle 144 pending/approved/rejected)

---

## 13. bot interaction

**텔레그램 본문**:

| 영역 | 본문 |
|---|---|
| BotFather | bot 등록 + token + webhook |
| inline mode | @bot 입력 시 inline result popup |
| command list | / 입력 시 bot command 자동 완성 popup |
| inline button | 메시지 안 button (URL + callback + login + payment) |
| payment | invoice + 결제 confirm |
| 봇 디렉토리 | t.me/bot_username public |

**TooTalk 등가 (cycle 150~160)**:
- 투네이션 고객센터 봇 (default — LLM 인터랙티브 대화형 Q&A)
- 방송 도우미 봇 (OBS + YouTube + Twitch + CHZZK + Kick — Nightbot 등가)
- BotFather 등가 + Bot API + webhook + inline + payment
- 외부 개발자 봇 등록 + 공개 디렉토리 ([[project-bot-framework]])

---

## 14. 파일 첨부 picker

**텔레그램 본문**:

| 영역 | 본문 |
|---|---|
| 입력 bar | clip icon click |
| 메뉴 popup | Photo + Video + File + Location + Contact + Poll |
| 사진 / 비디오 | 시스템 picker + grid + multi-select |
| caption | 첨부 직전 caption input |
| 압축 | 사진 = 자동 압축 vs 원본 (file mode) |
| drag & drop | window 안 drop file 자동 attach |

**TooTalk 등가**:
- 입력 bar 안 첨부 icon (cycle 119+ FileSender)
- 사진 / 비디오 + 파일 통합 (chunk transfer 정합)
- drag & drop (PyQt6 dropEvent — 부분 진입)
- location / contact / poll = Phase 5 entry

---

## 15. 통화 (voice / video call)

**텔레그램 본문**:

| 영역 | 본문 |
|---|---|
| 통화 진입 | 프로필 통화 button or 친구 row 통화 icon |
| 통화 ring | 큰 avatar + 이름 + accept / decline 큰 button |
| 통화 진행 | mute + speaker + camera + end + record |
| 그룹 통화 | voice chat / video chat (Telegram group 정합) |
| screen share | 통화 안 사용자 screen 공유 |

**TooTalk 등가**:
- WebRTC SDP offer/answer (현 mesh chain 진입)
- mute / speaker / camera 토글
- screen share = 원격 데스크탑 chain 정합 (cycle 166~180)
- 그룹 통화 mesh ≤ 8 peer cap

---

## 16. cycle 153~ design 본격 entry manifest

| 우선 | 영역 | scope |
|---|---|---|
| 1 | WelcomeDialog (§1) 신설 — TooTalk SVG 로고 + 8 icon cluster + 시작하기 CTA + 4 locale switch | `app/ui/welcome_dialog.py` + main.py 안 LoginDialog 직전 호출 |
| 2 | LoginDialog (§2+§3) polish — email + username + password + OTP 6 box + auto-advance + 재 송신 link | `app/ui/login_dialog.py` 본문 redesign |
| 3 | 메인 화면 3 column layout (§5) | `app/ui/main_window.py` QSplitter + left rail + chat list + chat view |
| 4 | ChatView reply + reaction (§6) | `app/ui/chat_view.py` + `message_bubble.py` 본문 확장 |
| 5 | 설정 dialog (§9) — 6 section tabbed | `app/ui/settings_dialog.py` 신설 |
| 6 | sticker / emoji picker (§12) | Phase 5 entry — emoji_pack_share 정합 |
| 7 | bot interaction (§13) — inline mode + command list | Phase 3 bot framework 정합 |
| 8 | 통화 (§15) — WebRTC audio/video | Phase 5 cycle 200+ entry |

---

## 17. 사용자 screenshot 누적 chain (사용자 manual paste 의무)

다음 영역 의 사용자 screenshot paste 시 본 doc 의 §x 영역 갱신:

| 우선 | 영역 | 사용자 paste 의무 |
|---|---|---|
| 1 | §1 welcome | ✅ 사용자 paste 완료 (Image #30) |
| 2 | §2 phone entry | ⏳ 사용자 screenshot 의무 |
| 3 | §3 OTP code | ⏳ |
| 4 | §4 2FA | ⏳ |
| 5 | §5 main 3 column | ✅ 부분 (Image #27) |
| 6 | §6 chat view | ✅ 부분 (Image #27) |
| 7 | §7 친구 추가 | ⏳ |
| 8 | §8 그룹 생성 | ⏳ |
| 9 | §9 설정 | ⏳ |
| 10 | §10 프로필 | ⏳ |
| 11 | §11 검색 | ⏳ |
| 12 | §12 sticker picker | ⏳ |
| 13 | §13 bot | ⏳ |
| 14 | §14 파일 첨부 | ⏳ |
| 15 | §15 통화 | ⏳ |

---

## 18. 참조

- 정본: [CLAUDE.md](../../CLAUDE.md) §3 7 + ssh-deploy-agent
- 사용자 directive 2026-05-19 cycle 152.5 "지금부터 텔레그램의 각 레이아웃 다 조사해"
- tdesktop 공식: https://github.com/telegramdesktop/tdesktop
- Telegram Theme Reference: https://github.com/telegramdesktop/tdesktop/wiki/Theme-Reference
- 가드레일: [[feedback-design-interactive-html]] + [[project-p2p-msg-overview]] + [[project-emoji-pack-share]] + [[project-bot-framework]]

---

마지막 갱신: 2026-05-19 23:50 KST — 사이클 152.5 신설 (텔레그램 14 영역 base + TooTalk 등가 mapping + cycle 153~ design entry manifest)
