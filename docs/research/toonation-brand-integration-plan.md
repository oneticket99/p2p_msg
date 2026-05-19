---
title: "Toonation 브랜드 + 로고 TooTalk UI 통합 계획 — cycle 152.6"
owner: oneticket99
last_verified: 2026-05-20T00:20:00+09:00
status: active
cycle: 152.6
phase: Phase 5 UI redesign — brand 통합
---

<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- 사용자 directive 2026-05-19 cycle 152.6 "투네이션 브랜드컬러와 로고 사용해서 반영 계획 세워" 회수. -->
<!-- FRONTEND.md §15 (Toonation BI 가이드 정합) ground truth 활용 + 외부 도메인 참조 부재. -->

# Toonation 브랜드 + 로고 TooTalk UI 통합 계획

> 본 doc = TooTalk UI 전면 redesign 시점 의 Toonation 브랜드 자산 통합 manifest. **ground truth = [FRONTEND.md §15 BI 가이드](../../FRONTEND.md)** (사용자 정의 본격 정본).
> cycle 153~ design entry prereq + [telegram-ui-survey.md](telegram-ui-survey.md) 14 영역 mapping 정합.

---

## 1. ground truth = FRONTEND.md §15 (재 정의 부재)

### 1.1 BI 가이드 6 컬러 (FRONTEND.md L440~L445)

| 역할 | hex | 활용 |
|---|---|---|
| 메인 컬러 (Toonation Blue) | `#0066FF` | 보내기 + 강조 액션 + 후원 CTA |
| 메인 변형 (Blue Deep) | `#0052FF` | dark mode + hover/active |
| 서브 (Deep Navy) | `#0F172A` | dark mode bg + 코인/텍스트 bg |
| 베이스 (White) | `#FFFFFF` | light mode 기본 bg |
| 포인트 (네온 cyan) | `#22D3EE` | 후원 금액 + 배너 + 시선 끌기 |
| 포인트 (light cyan) | `#67E8F9` | dark mode 포인트 + ACK 진행 |

### 1.2 변수 ↔ BI mapping (FRONTEND.md L450~L456)

| 변수 | light | dark |
|---|---|---|
| `--primary` | `#0066FF` | `#0052FF` |
| `--progress-acked` | `#22D3EE` | `#67E8F9` |
| `--progress-inflight` | `#0F172A` | `#1E293B` |

**본 doc = 본 정의 변경 부재**. cycle 153~ entry 시 그대로 활용.

---

## 2. 로고 SVG mismatch detect + 회수 의무

### 2.1 현 logo (`app/assets/branding/tootalk_logo.svg`) 색상

| 영역 | 현 색상 | FRONTEND.md §15 정합 |
|---|---|---|
| plus icon (T) | `#4B95FC` (medium blue) | ⚠️ mismatch — `#0066FF` 정합 의무 |
| 좌측 ring (첫 O) | `#A8C5FF` (light blue) | ⚠️ mismatch — `#67E8F9` 또는 `#22D3EE` 정합 의무 |
| 우측 ring (둘째 O) | `#4B95FC` | ⚠️ mismatch — `#0066FF` 정합 의무 |
| Talk wordmark | `#1F2937` | partial match — `#0F172A` Deep Navy 정합 권장 |

### 2.2 logo update 의무 (cycle 153 entry)

`app/assets/branding/tootalk_logo.svg` 색상 4건 회수:

```svg
<!-- plus icon — Toonation Blue primary -->
<g fill="#0066FF">
  <rect x="10" y="40" width="50" height="20" rx="10" ry="10"/>
  <rect x="25" y="25" width="20" height="50" rx="10" ry="10"/>
</g>

<!-- 좌측 ring — 네온 cyan (포인트) -->
<circle cx="98" cy="50" r="22" fill="none" stroke="#22D3EE" stroke-width="14"/>

<!-- 우측 ring — Toonation Blue primary -->
<circle cx="148" cy="50" r="22" fill="none" stroke="#0066FF" stroke-width="14"/>

<!-- Talk wordmark — Deep Navy -->
<text x="186" y="68" fill="#0F172A" font-weight="700">Talk</text>
```

→ 로고 SVG 1 file rewrite + History.md prepend 의무.

---

## 3. logo 변형 manifest (cycle 153 신설 4 file)

| 변형 | 사용처 | size | 신설 file |
|---|---|---|---|
| Full (현재) | WelcomeDialog banner + 시작 화면 | 380×100 | `tootalk_logo.svg` (rewrite) |
| Icon-only | 메인 윈도우 title + tray icon + 알림 | 64×64 | `tootalk_icon.svg` 신설 |
| Wordmark-only | 상단 header 좁은 영역 | 48px height | `tootalk_wordmark.svg` 신설 |
| Favicon | 브라우저 tab + Linux Window icon | 16×16 + 32×32 | `tootalk_favicon.ico` 신설 |

본 4 file = `app/assets/branding/` 안 통합 배치.

---

## 4. cycle 153~ entry 우선순위 5 phase

### 4.1 phase 1 — theme 변수 통합 (cycle 153)

| 우선 | 파일 | 작업 |
|---|---|---|
| 1 | `app/ui/theme.qss` 신설 | FRONTEND.md §15 + DESIGN.md §11 정의 QSS 변환 |
| 2 | `app/ui/theme.py` 신설 | QSS load + dark/light auto-detect |
| 3 | `app/main.py` | `theme.load_theme(qt_app)` 호출 |
| 4 | `app/assets/branding/tootalk_logo.svg` | 색상 4건 update (위 §2.2) |
| 5 | `tootalk_icon.svg` + `tootalk_wordmark.svg` + `tootalk_favicon.ico` 신설 | 변형 3종 |

### 4.2 phase 2 — Welcome + Login dialog (cycle 154)

| 우선 | 파일 | 작업 |
|---|---|---|
| 1 | `app/ui/welcome_dialog.py` 신설 | banner (Toonation Blue + Deep Navy gradient) + 로고 full + CTA + 4 locale switch |
| 2 | `app/ui/login_dialog.py` redesign | email + password + 로고 icon-only top |
| 3 | `app/ui/signup_dialog.py` redesign | email + username + password 6 field + 로고 |
| 4 | `app/ui/otp_dialog.py` 신설 | 6 box auto-advance + 재 송신 link |

### 4.3 phase 3 — 메인 + ChatView (cycle 155~156)

| 우선 | 파일 | 작업 |
|---|---|---|
| 1 | `app/ui/main_window.py` | QSplitter 3 분할 + tray icon = icon-only |
| 2 | `app/ui/sidebar_rail.py` 신설 | 64px vertical icon column 4 tab |
| 3 | `app/ui/chat_list_panel.py` 신설 | 280px middle column |
| 4 | `app/ui/chat_header.py` 신설 | right column 상단 header bar |
| 5 | `app/ui/message_bubble.py` | self bubble bg = `--primary` + peer bubble bg = `--bg-elevated` |

### 4.4 phase 4 — Settings + Profile (cycle 157~158)

| 우선 | 파일 | 작업 |
|---|---|---|
| 1 | `app/ui/settings_dialog.py` 신설 | 10 section tabbed |
| 2 | `app/ui/profile_view.py` 신설 | 친구 / self 프로필 |
| 3 | `app/ui/theme_picker.py` 신설 | dark/light/auto 토글 |

### 4.5 phase 5 — sticker + bot + 통화 (cycle 160~200)

| 우선 | 파일 | 작업 |
|---|---|---|
| 1 | `app/ui/emoji_picker.py` 신설 | 9 category + 검색 + custom pack |
| 2 | `app/ui/bot_panel.py` 신설 | inline mode + command list |
| 3 | `app/ui/call_window.py` 신설 | WebRTC voice/video |

---

## 5. QSS theme skeleton (cycle 153 entry prereq)

FRONTEND.md §15 변수 ↔ QSS mapping:

```qss
/* SPDX-License-Identifier: GPL-3.0-or-later
   TooTalk Toonation BI 통합 theme — cycle 153 entry.
   ground truth = FRONTEND.md §15 BI 가이드. */

QWidget {
    background-color: #0F172A;
    color: #e5e7eb;
    font-family: -apple-system, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    font-size: 13px;
}

QPushButton[variant="primary"] {
    background-color: #0066FF;
    color: #ffffff;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton[variant="primary"]:hover {
    background-color: #0052FF;
}

QFrame#messageBubbleSelf {
    background-color: #0066FF;
    border-radius: 12px;
    padding: 8px 12px;
}

QFrame#messageBubbleSelf QLabel {
    color: #ffffff;
}

QFrame#messageBubblePeer {
    background-color: #1F2937;
    border: 1px solid #374151;
    border-radius: 12px;
    padding: 8px 12px;
}

QFrame#messageBubblePeer QLabel {
    color: #e5e7eb;
}

QLineEdit:focus, QTextEdit:focus {
    border-color: #0066FF;
}

QFrame#sidebarRail {
    background-color: #0a0f1c;
    border-right: 1px solid #1f2937;
    min-width: 64px;
}

QListWidget#chatList::item:selected {
    background-color: #1F2937;
}

QListWidget#chatList::item:hover {
    background-color: rgba(0, 102, 255, 0.1);
}
```

---

## 6. 검증 chain (cycle 153 PASS gate)

| layer | 검증 |
|---|---|
| visual | WelcomeDialog + LoginDialog + 메인창 macOS + Windows + Linux screenshot 3 platform pixel 정합 |
| accessibility | WCAG 2.1 AA contrast ≥ 4.5:1 |
| dark mode | palette lightness < 128 자동 감지 + manual override |
| i18n | 5 locale 정렬 정합 |
| reduce motion | OS 설정 시 transition 0ms |
| logo SVG render | 380×100 + 64×64 + 48px height 3 variant render 정합 |

---

## 7. 차별화 영역 (TooTalk 만 — 텔레그램 부재)

| 영역 | brand 통합 패턴 |
|---|---|
| 원격 데스크탑 도움 | sidebar rail 안 🖥️ tab + `--primary` highlight |
| OBS 도움 chain | 친구 프로필 안 "OBS 설정 도움 요청" `--primary` CTA |
| 자체 host 표기 | settings 안 server endpoint + `--progress-acked` cyan badge |
| GPLv3 OSS 표기 | about dialog + footer license link `--primary` |
| emoji pack share | bot panel + emoji picker 안 "내 pack 등록" `--primary` button |

---

## 8. 진행 제약 + 사용자 ack

### 8.1 cycle 153 본격 entry prereq

| 항목 | 결정 사항 |
|---|---|
| 로고 SVG 색상 update | FRONTEND.md §15 정합 → 4건 색상 회수 (위 §2.2) |
| theme.qss 신설 | FRONTEND.md §15 변수 그대로 활용 |
| logo 변형 3종 신설 | icon + wordmark + favicon |
| 추가 텔레그램 screenshot paste (selectable) | 14 영역 의 13건 정확도 강화 |

### 8.2 가드레일 정합

- [[feedback-design-interactive-html]] — HTML interactive 보고
- [[feedback-doc-perfection-before-code]] — 코드 entry 전 8 체크리스트
- [[feedback-no-autonomy-dereliction-prevention]] — 사용자 직접 ack 의무
- [[feedback-parallel-execution-mandatory]] — 독립 file 신설 병렬

### 8.3 차단 항목

- FRONTEND.md §15 본격 정의 변경 차단 (사용자 ack 부재 시)
- 외부 brand 자료 참조 차단 (사용자 자체 정의 ground truth)
- `app/ui/theme.qss` 신설 = cycle 153 사용자 GO 의무

---

## 9. 참조

- **ground truth**: [FRONTEND.md §15](../../FRONTEND.md) Toonation BI 가이드 + 변수 mapping
- 텔레그램 14 영역 조사: [telegram-ui-survey.md](telegram-ui-survey.md) + [.html](telegram-ui-survey.html)
- 현 디자인 시스템: [DESIGN.md §11](../../DESIGN.md)
- 현 로고: [`app/assets/branding/tootalk_logo.svg`](../../app/assets/branding/tootalk_logo.svg)
- 사용자 directive 2026-05-19 cycle 152.6

---

마지막 갱신: 2026-05-20 00:20 KST — 사이클 152.6 brand 통합 계획 신설 (FRONTEND.md §15 ground truth 정합 + 로고 SVG 색상 update + 5 phase 16 file)
