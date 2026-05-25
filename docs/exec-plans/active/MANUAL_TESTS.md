---
title: "TooTalk 사용자 manual test 항목 — Claude 자율 불가 분리"
owner: oneticket99
last_verified: 2026-05-21
status: active
---

# TooTalk 사용자 manual test 항목 (Claude 자율 불가)

> 본 문서 = 사용자 directive "내가 직접 테스트할 항목을 따로 분리하고" 정합.
> Claude 의 자율 chain 의 외 의 사용자 직접 수행 의무 항목 누계. 매 cycle 진행
> 시 본 문서 의 항목 의 사용자 confirm 후 Claude 의 다음 단계 진입.

---

## 1. 분리 기준 (Claude 불가 vs 자율 가능)

| 분류 | 기준 | 본 문서 등재 여부 |
|---|---|---|
| 실 외부 API smoke | 실 endpoint + 실 API key + 네트워크 응답 검증 | ✅ 사용자 |
| GUI 동작 검증 | QApplication eventloop + 마우스 클릭 + 시각 confirm | ✅ 사용자 |
| 실 디바이스 동작 | macOS Accessibility 권한 + Windows UAC + 실 디스플레이 | ✅ 사용자 |
| CI runner 상태 | self-hosted runner 의 GitHub Actions 의 GREEN 확인 | ✅ 사용자 |
| 외부 SaaS 인증 | OAuth + API key 발급 + dashboard 확인 | ✅ 사용자 |
| 의존성 설치 + 환경 변수 주입 | venv pip install + .env 편집 + 권한 설정 | ✅ 사용자 |
| Mock + transport injection 테스트 | sleep_fn mock + transport stub + 단위 test | Claude 자율 |
| 데이터 직렬화 + 파싱 로직 | dict → dataclass + JSON wire format | Claude 자율 |
| 코드 skeleton + abstraction layer | Protocol + dataclass + placeholder + NotImplementedError | Claude 자율 |
| 문서 정합 + HTML mirror | markdown + HTML 동시 갱신 | Claude 자율 |
| 평가 snapshot rewrite | 매 cycle productization + vibe-coding 전수 | Claude 자율 |

---

## 2. 사용자 manual test 항목 누계 (Phase 3 bot framework + Phase 1 dogfooding)

### 2.1 Anthropic 실 API smoke (cycle 70~72 follow-up)

- [ ] `pip install httpx` 의 venv 의 의존성 등록 (현 `app/requirements.txt` 부재)
- [ ] `ANTHROPIC_API_KEY` 환경 변수 의 console.anthropic.com 발급 + .env 의 주입
- [ ] `from app.bot.anthropic_client import from_env` → `client.chat([BotMessage(USER, "ping", 0)])` 의 실 응답 확인
- [ ] 429 응답 의 retry/backoff 의 실 환경 trigger (의도된 rate limit 도달 + retry 회수 확인)
- [ ] 5xx 응답 의 retry/backoff (Anthropic 의 일시 장애 시점 의 capture — 자율 trigger 불가)
- [ ] `httpx_transport` 의 timeout 30초 default 의 실 환경 적합도 — 응답 지연 의 측정 후 confirm
- 검증 도구: 실 console.anthropic.com dashboard 의 호출 카운트 + claude-3-5-sonnet-latest 의 응답 quality
- 권한: ANTHROPIC_API_KEY (사용자 발급 + 비용 책임)

### 2.2 Toonation API 직접 통합 — 옵션 B 핵심 (Phase 3 endgame)

- [ ] Toonation API spec 의 사용자 직접 제공 — 후원 알림 webhook + 정산 조회 + auth 의 endpoint URL + 요청 schema
- [ ] Toonation 서비스 의 API key 발급 + .env 의 주입 (사용자 권한 의 dashboard)
- [ ] webhook 의 시그널링 서버 의 endpoint 등록 (114.207.112.73 의 별개 path)
- [ ] 후원 알림 의 실 trigger 시 의 TooTalk 의 push 알림 의 실 송수신 확인
- [ ] 정산 조회 API 의 응답 schema 의 사용자 confirm
- 검증 도구: Toonation dashboard 의 webhook log + 실 후원 시점 의 TooTalk 알림 도달
- 권한: Toonation 의 API key 발급 + webhook URL 등록 의 사용자 권한
- Claude 자율 가능 부분: spec confirm 후 의 client wrapper + serialize/parse + 4 종 예외 매핑

### 2.3 PyQt6 UI 통합 + ChatView lazy load (cycle 59~62 follow-up)

- [ ] `python -m app.main` 의 실 GUI 기동 확인 — MainWindow + ChatView + StatusBar 의 render
- [ ] `ChatView.add_message` 의 30일 volatile 의 실 trigger — 31일 이전 메시지 의 fade out + 메모리 회수 확인
- [ ] scroll top 도달 의 lazy load 의 실 API 호출 — `MessagesClient.list_messages_in_range` 의 server 응답 의 ChatView 의 chunk prepend
- [ ] tracemalloc + RSS 측정 — 1만 메시지 누적 시 의 메모리 100 MB 이하 confirm
- [ ] PyQt6 의 macOS Gatekeeper + Windows SmartScreen 의 첫 실행 의 사용자 절차 확인
- 검증 도구: macOS Activity Monitor + Windows Task Manager + Python tracemalloc + objgraph
- 권한: 실 디바이스 + 실 PyQt6 설치 + venv 활성

### 2.4 PyObjC + Quartz 실 binding (cycle 57~58 follow-up — Phase 3 차별화)

- [ ] macOS Accessibility 권한 의 사용자 grant — 시스템 설정 → 개인정보 보호 → 손쉬운 사용 → TooTalk.app 의 check
- [ ] `pip install pyobjc-framework-Quartz` 의 venv 등록
- [ ] `MacOSQuartzBackend.capture()` 의 실 호출 — 1920x1080 RGB capture 의 < 50ms 의 응답 의 confirm
- [ ] `MacOSCGEventBackend.apply(events)` 의 실 호출 — mouse_move + key_down 의 target OS 의 입력 의 실 적용 confirm
- [ ] tracemalloc + objgraph 의 GB-scale 누수 차단 검증 — 60 fps × 1080p RGB capture 1분 의 RSS 변화 의 측정
- [ ] CGImage / CGEvent / CFData 의 CFRelease 의무 의 실 trigger 시 의 leak 부재 confirm
- 검증 도구: macOS Activity Monitor + Console.app (Accessibility 권한 거부 시 log) + Instruments.app (Leaks)
- 권한: macOS Accessibility (시스템 설정) + 실 디스플레이 capture 권한

### 2.5 Phase 1 dogfooding 실 측정 (cycle 56 follow-up)

- [ ] 2 호스트 의 실 P2P 연결 — 1 호스트 (Mac) + 1 호스트 (Mac / Windows) 의 friend 등록 + 실 메시지 송수신
- [ ] 회원가입 + 이메일 OTP 의 실 SMTP 의 도달 확인 — 114.207.112.73 의 postfix 의 사용자 inbox 의 OTP 코드 도달
- [ ] 이미지 + 파일 송수신 의 실 100 MB 의 progress bar 의 양방향 동기 확인
- [ ] WebRTC DataChannel 의 STUN 의 외 의 NAT traversal 의 실 환경 confirm (라우터 + ISP)
- [ ] `tools/dogfooding/harness.py` 의 18 PASS 의 실 실행 — 사용자 매뉴얼 의 check
- 검증 도구: 2 호스트 + 실 네트워크 + SMTP 의 inbox + Wireshark (옵션)
- 권한: 실 사용자 + 실 호스트 2 대 + 실 SMTP 의 도메인 (Toonation 의 의)

### 2.6 telegram MCP 복원 (cycle 45~47 follow-up)

- [ ] claude CLI 의 fresh restart — `claude` (no `-c` 의 신규 conversation) + MCP plugin auto-respawn
- [ ] `/loop` 의 양방향 polling 의 inbound 의 사용자 메시지 의 Claude 의 receive 의 확인
- [ ] PID 의 변경 의 확인 — `ps -ef | grep claude` 의 신규 PID (이전 PID 9107 외)
- 검증 도구: `claude` CLI + 텔레그램 의 송수신 양방향 확인
- 권한: 사용자 의 claude CLI 의 직접 실행
- Claude 자율 우회: Bot API direct curl + `/tmp/telegram_poll.sh` (현 임시 운영 중)

### 2.7 CI runner GREEN 확인 (8 job 의 매 cycle 회귀)

- [ ] GitHub Actions runner 의 self-hosted macOS arm64 의 online 의 확인 (사용자 의 직접 호스트)
- [ ] 매 push 시 의 8 job (ci.yml + docs-lint.yml + doc-gardener.yml) 의 GREEN 의 확인
- [ ] wine cross-compile (Windows 빌드) 의 GitHub-hosted Ubuntu 의 GREEN 의 확인
- [ ] fork PR strict 의 외부 contributor 의 의도된 fork PR 의 차단 의 확인
- 검증 도구: GitHub Actions 의 dashboard + runner host 의 monitoring
- 권한: GitHub 의 repo owner 권한 + self-hosted runner host

### 2.8 서버 영역 LLM proxy endpoint 실 동작 (cycle 74 예정 follow-up)

- [ ] 서버 호스트 (114.207.112.73) 의 ANTHROPIC_API_KEY 환경 변수 의 주입 (사용자 권한)
- [ ] `POST /api/bot/chat` 의 실 호출 의 Anthropic Messages API 의 forward 의 확인
- [ ] 클라이언트 의 API key 차단 의 확인 — 클라이언트 의 .env 의 ANTHROPIC_API_KEY 부재 의 정합
- [ ] 서버 의 abuse 차단 (RateLimitGate per-user) 의 실 trigger 의 확인
- 검증 도구: 서버 log + httpx 의 직접 호출 + Anthropic console
- 권한: 서버 호스트 SSH + 환경 변수 주입

### 2.9 원격 데스크탑 M4 session 실 OS 검증 (cycle 169.776~788 follow-up — Phase 5 G3 게이트)

> 자동 검증 완료분 (G2): RemoteSessionRunner + permission handshake + coord_transform + 실 aiortc DataChannel loopback (headless). 아래는 실 OS + 물리 2 장비 의 사용자 직접 ack 만 가능한 잔여(M4).

- [ ] macOS Screen Recording 권한 grant — 시스템 설정 → 개인정보 보호 → 화면 기록 → TooTalk 의 check (host 쪽 capture)
- [ ] macOS Accessibility 권한 grant — 손쉬운 사용 → TooTalk 의 check (host 쪽 input dispatch)
- [ ] friend 2 장비 의 실 P2P 원격 세션 — chat_header 원격 요청/연결 → RemoteCallDialog accept → `_start_remote_session` 의 RemoteSessionRunner 기동
- [ ] friend peer connection 의 `_remote_data_channel` 실 생성 + runner send callable 의 실 채널 결선 확인 (현 production 경로 no-op — M4 binding 의무)
- [ ] HOST runner 의 PermissionGrant 실 주입 — 현 grant=None fail-closed(input 전량 거부) → handshake GRANT 수신 시 runner grant 주입 경로 확인
- [ ] **controller 창에 host 화면 frame 실 표시** + **controller 클릭/키 의 host OS 실 적용** 의 사람 눈 visual ack (mock dispatch 아닌 실 OS event)
- [ ] expiry + 1-click revoke 의 실 동작 — grant 만료/revoke 시 input 즉시 차단 확인
- 검증 도구: 2 물리 장비(Mac + Mac/Windows) + 화면 녹화 + 사용자 직접 관찰
- 권한: macOS Screen Recording + Accessibility + 양 장비 친구 등록

---

## 3. Claude 자율 가능 chain (manual test 의 외)

본 list = Claude 의 직접 진행 의 차기 cycle 의 후보. 사용자 directive 의 없이 진행 가능.

### 3.1 즉시 진입 가능 (외부 의존 무)

- [ ] cycle 73 — retry-after 헤더 honor + jitter 추가 (cycle 72 follow-up)
- [ ] cycle 74 — 서버 영역 `/api/bot/chat` LLM proxy endpoint skeleton + mock provider tests
- [ ] cycle 75 — EmbeddingRAGStore 기본 abstraction (vector store interface + mock embedder + cosine sim helper)
- [ ] cycle 76 — Toonation API client 추상 skeleton (spec 의 사용자 confirm 의 외 의 base abstraction)
- [ ] cycle 77 — httpx 의존성 등록 (requirements.txt 의 entry — 의존성 lock 별개 cycle)
- [ ] cycle 78 — chat_history_policy 의 server-side helper (UI 의 외 의 정책 로직 추출 + tests)

### 3.2 사용자 confirm 의 후 의 진입

- [ ] Toonation API spec 의 사용자 제공 후 의 client wrapper (cycle 76 의 진입)
- [ ] httpx 설치 후 의 실 transport 의 smoke test (사용자 manual 의 후)

---

## 4. 본 문서 운영

- 매 cycle 종료 시 의 본 문서 의 §2 의 누계 항목 추가
- 사용자 가 manual test 의 completion 시 의 본 문서 의 check (- [x])
- check 의 누계 가 항목 의 80% 도달 시 의 Claude 의 dogfooding cycle 진입
- 본 문서 의 자체 갱신 = Claude 의 자율 가능 (manual test 의 항목 의 추가 의 외)

---

## 5. 참조

- [CLAUDE.md](../../../CLAUDE.md) — 세션 내 서브에이전트 호출 규약
- [CLAUDE_HARNESS_IMPORTANT.md](../../../CLAUDE_HARNESS_IMPORTANT.md) §Q — 세션 인계 + dogfooding 의 pattern
- 본 문서 의 cycle 별 매핑: cycle 68 (RAG) + 69 (RAG 통합) + 70 (Anthropic client) + 71 (adapter) + 72 (retry/backoff)
- [docs/exec-plans/active/2026-05-17-session-handoff.md](2026-05-17-session-handoff.md) — 세션 인계 전체 본문

---

마지막 갱신: 2026-05-21 14:00 KST (cycle 72 직후 의 신설 — 사용자 directive "내가 직접 테스트할 항목을 따로 분리하고")
