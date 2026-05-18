# TooTalk (코드명 p2p_msg)

**TooTalk** 은 PyQt6 기반 데스크탑 P2P 메신저 — 시그널링 서버 한 곳만
거치고 실 데이터(텍스트·이미지·파일)는 WebRTC DataChannel 직결로
운반한다. 저장소 코드명은 `p2p_msg` 다.

> 본 문서는 저장소 루트의 **운영 README** 다. 빠른 시작 + 빌드 + Gatekeeper /
> SmartScreen 우회 안내 + 변경 이력(M2) 30행 캐시를 한 곳에 모은다.
> 저장소 맵: [AGENTS.md](AGENTS.md) · 정본: [CLAUDE_HARNESS_IMPORTANT.md](CLAUDE_HARNESS_IMPORTANT.md) §H (M2 규약).

---

## 1. 기능 (Phase 1 MVP)

| 기능 | 설명 | FR |
|---|---|---|
| 텍스트 송수신 | WebRTC DataChannel 경유 JSON envelope 1:1 송수신 (타임스탬프·발신자 식별자 포함) | FR-02 |
| 이미지 송수신 | Pillow 썸네일 인라인 표시 + 원본은 별도 청크 스트림으로 DataChannel 운반 | FR-03 |
| 파일 송수신 | 청크 backpressure 기반 대용량 파일 전송 (SHA-256 무결성 확인) | FR-04 |
| 양방향 ProgressBar | 송신 buffer / acked 두 단계 + 수신 확정 — PyQt `QProgressBar` 로 양쪽 동기 갱신 (100ms 이내 1회 이상) | FR-04 |
| 메시지 영속화 | 대화·이미지·파일 메타데이터 로컬 영속 — 앱 재실행 시 이전 히스토리 복원 | FR-05 |
| 자동 재연결 | 시그널링 단절 시 지수 백오프 (1s → 30s) 재연결, 대기 동안 입력 큐잉 | FR-10 |
| 첫 실행 onboarding | nickname 입력 + STUN·시그널링 호스트 안내 + Gatekeeper/SmartScreen 우회 가이드 | FR-09 |

상세 요구사항(FR-01 ~ FR-10) · 비기능 지표(NFR-01 ~ NFR-07) · 인수 기준은
[Specification.md](Specification.md) 정본 참조.

---

## 2. 빠른 시작

### 2.1 의존성 설치 (클라이언트)

```bash
# 저장소 루트에서
python3.13 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r app/requirements.txt
```

### 2.2 실행 (클라이언트)

```bash
# 저장소 루트에서 (app 패키지를 모듈로 호출)
python -m app.main
```

윈도우 타이틀 "TooTalk" 가 노출되고, StatusBar 가 `DISCONNECTED · peers: 0`
상태로 시작한다. 메뉴바 "방 → 입장" 다이얼로그에서 `room id` + `peer_id`
입력 후 JOIN.

> 본 Phase 스켈레톤은 시그널링 자동 연결을 수행하지 않는다. 실 연결 활성화는
> Task #16 (`app.net.webrtc` 결합) 에서 적용된다. 자세한 사용은
> [app/README.md](app/README.md) 참조.

### 2.3 의존성 설치 + 실행 (시그널링 서버)

자체 시그널링 서버를 구동하는 경우.

```bash
# 저장소 루트에서
python3.13 -m venv .venv-server
source .venv-server/bin/activate
pip install -r server/requirements.txt
python -m server.main
```

기본 바인딩: `ws://0.0.0.0:8765/ws` · health-check: `http://0.0.0.0:8765/health`.
서버 운영·프로토콜 명세는 [server/README.md](server/README.md) 정독.

---

## 3. 시그널링 서버

데모 호스트가 운영된다. 클라이언트 `.env` 또는 `.env.local` 에 다음
값으로 주입한다 (하드코딩 금지 — 정본 §E).

| 키 | 데모 값 | 설명 |
|---|---|---|
| `SIGNAL_SERVER_HOST` | `114.207.112.73` | 데모 호스트 IP |
| `SIGNAL_SERVER_WS_PORT` | `8765` | WebSocket TCP 포트 |
| `SIGNAL_SERVER_WS_SCHEME` | `ws` | Phase 1 은 `ws` 만 — `wss` 는 Phase 2 (TD-1) |

데모 서버 연결 URL: `ws://114.207.112.73:8765/ws`

> 데모 서버는 인증·rate limit·TLS 가 없는 공개 노출 상태다. 실서비스
> 전환 이전에 TD-1 (시그널링 서버 hardening) 해소 의무
> ([server/README.md §5](server/README.md)).

프로토콜 envelope 9종(클라이언트→서버 5 + 서버→클라이언트 4) 상세는
[server/README.md §3](server/README.md) · [server/protocol.py](server/protocol.py).

---

## 4. 빌드 (PyInstaller — macOS / Windows)

Phase 1 배포 산출물은 `TooTalk-{ver}-{os}.zip` 한 개씩, 인증서 미사용
(FR-08). 빌드 스크립트는 `tools/build.py` (Task #21 에서 활성).

### 4.1 macOS (arm64)

```bash
# 저장소 루트에서
source .venv/bin/activate
pip install pyinstaller
python tools/build.py --target=macos
# 산출물: dist/TooTalk-0.1.0-macos-arm64.zip
```

내부 동작.

1. `pyinstaller --onedir --windowed --name=TooTalk app/main.py`
2. `dist/TooTalk.app` 트리 생성
3. `zip -r dist/TooTalk-{ver}-macos-arm64.zip dist/TooTalk.app`

### 4.2 Windows (x64)

```powershell
# PowerShell — 저장소 루트
.\.venv\Scripts\Activate.ps1
pip install pyinstaller
python tools\build.py --target=windows
# 산출물: dist\TooTalk-0.1.0-windows-x64.zip
```

내부 동작.

1. `pyinstaller --onedir --windowed --name=TooTalk app\main.py`
2. `dist\TooTalk\` 디렉토리 생성
3. `Compress-Archive -Path dist\TooTalk\* -DestinationPath dist\TooTalk-{ver}-windows-x64.zip`

### 4.3 CI 매트릭스 (GitHub Actions self-hosted)

`.github/workflows/build.yml` (Task #22 에서 활성) 가 다음 runner 2종에서
빌드를 수행한다.

- `[self-hosted, macOS, arm64]`
- `[self-hosted, Windows, x64]`

빌드 산출물은 zip 단일 파일로만 첨부된다. zip 안에 `.env` · 빌드 시크릿 ·
빌드 호스트 사용자명 은 포함되지 않는다 (AC-08-3 정합).

---

## 5. macOS Gatekeeper 우회 안내 (인증서 미서명 빌드)

Phase 1 배포본은 Apple Developer 인증서 미서명이다. 첫 실행 시
"확인되지 않은 개발자" 경고 다이얼로그가 노출된다. 다음 절차로 우회한다.

### 5.1 GUI 절차

1. zip 압축 해제 → `TooTalk.app` 더블 클릭
2. 차단 다이얼로그 노출 → "확인" 한 번 클릭 (실행은 안 됨, 등록만 됨)
3. 시스템 설정 → 개인정보 보호 및 보안 → 보안 섹션 스크롤
4. "TooTalk.app 은 확인되지 않은 개발자이므로 차단되었습니다" 옆 **그대로 열기** 클릭
5. 관리자 비밀번호 입력 → "열기" 한 번 더 클릭

### 5.2 CLI 절차 (Terminal)

```bash
# zip 압축 해제 위치에서 — quarantine 속성 제거
xattr -dr com.apple.quarantine TooTalk.app
# 그 뒤 더블 클릭으로 정상 실행
open TooTalk.app
```

> `xattr -dr` 는 `com.apple.quarantine` 확장 속성 1개만 제거한다. 그 외
> 시스템 속성에는 영향을 주지 않는다.

### 5.3 주의

- 위 절차는 본 저장소가 배포한 zip 에 한해 수행한다. 출처 불명 zip 에
  동일 절차를 적용하는 것은 보안 위험을 키운다.
- Phase 2 진입 시 Apple Developer ID 서명 + Notarization 도입 (TD-3 해소
  로드맵), 본 절차는 점진적으로 deprecated 처리한다.

---

## 6. Windows SmartScreen 우회 안내 (Authenticode 미서명 빌드)

Phase 1 배포본은 Authenticode 인증서 미서명이다. 첫 실행 시 "Windows 가
PC 를 보호했습니다" SmartScreen 경고가 노출된다. 다음 절차로 우회한다.

### 6.1 GUI 절차

1. zip 압축 해제 → `TooTalk\TooTalk.exe` 더블 클릭
2. SmartScreen 파란색 경고창 노출
3. 작은 글씨 **추가 정보** 클릭
4. "이 앱을 실행 안 함" 옆 **실행** 버튼 클릭

### 6.2 파일 차단 해제 (PowerShell)

zip 압축 해제 직후에도 NTFS 보조 데이터 스트림(`Zone.Identifier`) 차단이
남는 경우가 있다. PowerShell 에서 일괄 해제 가능.

```powershell
# zip 압축 해제 위치에서
Get-ChildItem -Path .\TooTalk -Recurse | Unblock-File
.\TooTalk\TooTalk.exe
```

### 6.3 Windows Defender 방화벽 인바운드 허용

시그널링 데모 호스트(`114.207.112.73:8765`) 접속이 막히는 경우.

1. 시작 메뉴 → "Windows Defender 방화벽" 검색
2. "앱 또는 기능이 Windows Defender 방화벽을 통과하도록 허용" 클릭
3. "다른 앱 허용..." → `TooTalk.exe` 추가
4. **개인** 네트워크 체크박스 활성화 (공용 네트워크에서는 미체크 권장)

---

## 7. 디렉토리 구조 (간략)

```text
p2p_msg/
├── app/                      # PyQt6 + qasync 클라이언트
│   ├── core/                 # AppState · Config (.env 로딩)
│   ├── net/                  # 시그널링 WebSocket 클라이언트
│   ├── rtc/                  # WebRTC peer / transfer (예정)
│   └── ui/                   # MainWindow · ChatView · StatusBar · 위젯
├── server/                   # aiohttp 시그널링 서버
│   ├── signaling.py          # Router — WebSocket 핸들러
│   ├── room.py               # Service — Peer/Room/Registry
│   └── protocol.py           # Model — envelope TypedDict
├── docs/exec-plans/          # 활성 실행계획
├── tools/                    # 운영 스크립트 (doc-lint · claude-telegram)
├── .claude/agents/           # 7 프로세스 에이전트 정의
└── (루트 9 정책 + 운영 8 문서 + 정본 1 — 정본 §K 18 동결)
```

전체 트리 + ERD + 흐름도 4종은 [Structure.md](Structure.md) 정본 참조.

---

## 8. 문서 맵

| 분류 | 진입점 |
|---|---|
| 저장소 맵 (네비게이션) | [AGENTS.md](AGENTS.md) |
| Watcher 정본 + M1~M7 규약 | [CLAUDE_HARNESS_IMPORTANT.md](CLAUDE_HARNESS_IMPORTANT.md) |
| 9 정책 문서 (루트) | [ARCHITECTURE.md](ARCHITECTURE.md) · [DESIGN.md](DESIGN.md) · [FRONTEND.md](FRONTEND.md) · [PLANS.md](PLANS.md) · [PRODUCT_SENSE.md](PRODUCT_SENSE.md) · [QUALITY_SCORE.md](QUALITY_SCORE.md) · [RELIABILITY.md](RELIABILITY.md) · [SECURITY.md](SECURITY.md) (+ AGENTS.md) |
| 8 운영 문서 (루트) | [Specification.md](Specification.md) · [Structure.md](Structure.md) · CheckList.md (작성 예정) · History.md (작성 예정) · README.md (본 문서) · EXTENSION_GUIDE.md (작성 예정) · MIGRATION_MARIADB.md (작성 예정) · CLAUDE.md (작성 예정) |
| 활성 실행계획 | [docs/exec-plans/](docs/exec-plans/) |
| 영역 README | [app/README.md](app/README.md) · [server/README.md](server/README.md) |
| 에이전트 개별 사양 | [.claude/agents/](.claude/agents/) |

루트 마크다운 **18개 동결** ([정본 §K](CLAUDE_HARNESS_IMPORTANT.md)) — 신규
문서는 반드시 `docs/` 하위에 생성. 본 README 는 운영 8 문서 중 1개 슬롯
점유.

---

## 9. 라이선스

**GPLv3 확정** (사용자 directive 2026-05-17). LICENSE 저장소 루트 의 GNU
표준 본문 (674 lines) 의 의무 적용.

- 본 저장소 의 코드 + 문서 + 산출물 (zip) = GPLv3 의무 의 자동 발동
- PyQt6 GPLv3 의 직접 호환 (downstream GPL 의 자연 흡수)
- Phase 1 코드 진입 시 의 source file 의 SPDX header 의무:
  `# SPDX-License-Identifier: GPL-3.0-or-later`
- 영구 메모리 정합: `project_license_gpl.md`

### 9.1 GitHub visibility

**public (Phase 1 현재)** — Phase 완료 시점 의 **private 전환 가능성**
(사용자 directive 2026-05-17). self-hosted runner 의 의무 quota 회피
정합 (private + GitHub-hosted = 월 2000 min free tier 제약).

영구 메모리 정합: `project_visibility_transition.md` — 전환 시점 의
GPL 의무 영향 + CI 비용 + 외부 fork 의 GPL 권한 영구 유지 분석.

---

## 10. 기여 가이드

본 저장소는 **AGENTS.md 맵 + 정본 §B 5단계 워크플로우** 가 기여 절차의
정본이다. 신규 에이전트·문서·DB 모델·기능 확장 시 다음 문서를 정독한다.

- 신규 에이전트 추가 — [AGENTS.md §6](AGENTS.md) + `.claude/agents/<name>.md` 정의
- 신규 정책 문서 — `docs/` 하위에만 (정본 §K 18 동결), AGENTS.md 문서 맵 갱신
- 신규 FR · 코드 위치 — [Specification.md §8 매핑 테이블](Specification.md) + [Structure.md](Structure.md) ERD 동시 갱신
- 신규 DB 테이블 — MIGRATION_MARIADB.md (작성 예정) `tables` 배열 FK 순서 + Structure.md ERD
- 작업 완료 직후 — 본 README §11 변경 이력에 한 줄 prepend (M2 의무)

확장 가이드 정본은 EXTENSION_GUIDE.md (작성 예정 — 운영 8 문서 중 7번째)
가 출시되면 그쪽으로 위임된다. 본 절은 그 전까지 임시 입구다.

### 10.1 PR 제출 전 체크리스트 ([AGENTS.md §8](AGENTS.md) 인용)

- M1 관련 문서 선행 업데이트 완료 (Specification.md · CheckList.md · Structure.md)
- M2 본 README "변경 이력" 섹션에 한 줄 prepend (최신 상단, 30행 상한)
- M3 History.md 역순 prepend 적용 (Phase·타임스탬프 내림차순)
- M4 변경된 코드 파일에 한글 주석 존재 (`.py`·`.js`·`.html`·`.css`·`.sql`·`.sh`)
- M5 `git status -sb` 클린 + `origin/main` 동기
- `bash tools/doc-lint.sh` PASS — 깨진 링크 · frontmatter · BPE 위생 · 연속 빈 줄 4종 모두 GREEN
- `@reviewer-agent` · `@qa-agent` · `@observability-agent` 순차 통과

---

## 11. 변경 이력

> M2 규약 ([정본 §H](CLAUDE_HARNESS_IMPORTANT.md)) — 최신 30행 상한, 행 형식
> `- [YYYY-mm-dd H:i:s] 요약 (파일/영역)`, prepend 전용. 30행 초과 시 오래된
> 항목 제거 + 상세는 [History.md](History.md) (작성 예정) 위임.
>
> 본 시점 = 30행 상한 회전 완료 (2026-05-18 — release-agent 사이클 15 정식 GO 정합).
> 상세 History.md 전체 보존.

- [2026-05-22 03:00:00 KST] cycle 86 bot escalation queue + 28 신규 PASS 7 TestClass (사용자 directive 자율 chain) — `app/bot/escalation_queue.py` 신설. memory project_bot_framework + bot-framework.md §10 의 escalation 사람 상담 layer 의 별개 cycle entry. TicketStatus Enum 4종 (PENDING + ASSIGNED + RESOLVED + CLOSED) + EscalationReason Enum 6종 (USER_REQUEST + JAILBREAK + RATE_LIMIT + LOW_CONFIDENCE + LONG_RESPONSE + EXPLICIT). EscalationTicket frozen dataclass (ticket_id 양수 + user_id 양수 + reason + message 빈 차단 + created_at_ms 음수 차단 + status default PENDING + agent_id Optional 양수 + resolved_at_ms Optional 음수 차단 의 7 validation). EscalationQueue (in-memory + thread-safety 미보장 async single loop) — next_ticket_id monotonic + enqueue PENDING + assign PENDING → ASSIGNED + resolve ASSIGNED → RESOLVED + close 모든 status → CLOSED + 중복 차단 + list_pending/assigned/by_user/by_agent (created_at_ms ASC FIFO) + get/size/clear (next_id 1 reset). 28 신규 PASS 7 TestClass — TicketValidation 7 + Enqueue 3 (id 1 + monotonic + size) + Assign 4 (happy + unknown KeyError + duplicate reject + zero agent reject) + Resolve 3 + Close 3 + ListAndLookup 6 + ClearAndId 2. pytest 1024 (+28). Phase 3 entry 누계 542. drift 0건 45 연속. 5 검증 PASS. memory project_bot_framework.md (A) 의 escalation 사람 상담 layer entry — DB 영속화 + agent assignment policy + SLA timer + notification 의 별개 cycle 의 base abstraction
- [2026-05-22 02:00:00 KST] cycle 85 bot usage tracker + 31 신규 PASS 5 TestClass (사용자 directive 자율 chain) — `app/bot/usage_tracker.py` 신설. memory project_bot_framework + bot-framework.md §10 의 "사용 통계 + 비용 추적" 별개 cycle entry. UsageRecord frozen dataclass (user_id 양수 + provider 빈 차단 + model 빈 차단 + input_tokens/output_tokens/timestamp_ms 음수 차단 + total_tokens property). UsageSummary frozen (count + input + output + total). UsageTracker (in-memory) — record + size + clear + all_records (copy 반환 의 mutation 차단) + summarize_by_user + summarize_by_provider + summarize_by_period (minute/hour/day bucket ms 환산) + total. extract_anthropic_usage helper (Messages API 의 usage.input_tokens / output_tokens) + extract_openai_usage helper (Chat Completions 의 usage.prompt_tokens / completion_tokens) + bool isinstance(int)=True edge case 차단 + 음수 graceful 0 clamp + dict 부재 시 (0, 0) fallback. tests/app/bot/test_usage_tracker.py 31 신규 케이스 5 TestClass — UsageRecordValidation 9 (valid + 6 검증 reject + 0 tokens 허용) + UsageSummary 2 (total + zero) + UsageTracker 13 (empty + record + clear + copy + by_user + by_provider + by_minute/hour/day bucket + invalid period + total + empty total) + ExtractAnthropicUsage 5 (happy + missing + non-dict + non-int + negative clamp) + ExtractOpenAIUsage 3 (happy + missing + bool reject). pytest 996 (+31). Phase 3 entry 누계 514. drift 0건 44 연속. 5 검증 PASS. memory project_bot_framework.md 의 사용 통계 + 비용 추적 layer entry — 별개 cycle 의 model 별 $ per 1M token price book + billing alert + Prometheus / Grafana export + DB 영속 의 base abstraction
- [2026-05-22 01:00:00 KST] cycle 84 OpenAI Chat Completions API client + OpenAIProvider adapter + 29 신규 PASS (사용자 directive 자율 chain) — `app/bot/openai_client.py` 신설. OpenAI vs Anthropic 의 schema 차이 4종 — endpoint /v1/chat/completions + system role 의 messages array inline 유지 (Anthropic 의 top-level system field 분리 대비) + Authorization Bearer header (Anthropic 의 x-api-key 대비) + response choices[0].message (Anthropic 의 content[].text 대비). OpenAIClient dataclass + serialize_messages (system inline) + parse_response (choices[0].message 의 4 종 malformed 차단) + 4 종 예외 (OpenAIAuthError + OpenAIRateLimitError + OpenAIServerError + OpenAIMalformedError + base OpenAIError) + retry/backoff (max_retries + backoff_base_seconds + sleep_fn DI) + retry-after honor (case-insensitive + cap 60초) + jitter (jitter_max_seconds + jitter_fn) + network error retry (ConnectionError + OSError + TimeoutError → AnthropicServerError 의 등가 OpenAIServerError) + from_env(OPENAI_API_KEY). app/bot/llm_proxy.py 의 OpenAIProvider adapter 신설 (AnthropicProvider 와 동일 패턴 의 __init__(client) DI + lazy from_env + is_available 의 OPENAI_API_KEY env + httpx import 검증) + select_llm_provider 의 "openai" NotImplementedError 회수 (cycle 65 placeholder) + auto-detect 의 anthropic → openai → mock 의 3 layer fallback. tests/app/bot/test_openai_client.py 29 신규 케이스 7 TestClass — SerializeMessages 4 + ParseResponse 6 + ClientValidation 5 + BuildRequest 2 + ChatStatusMapping 6 + RetryAndBackoff 4 + FromEnv 2. test_llm_proxy.py 의 test_openai_not_implemented → test_openai_explicit 갱신. pytest 965 (+29). Phase 3 entry 누계 483. drift 0건 43 연속. 5 검증 PASS. memory project_bot_framework (A) 의 provider plug-in 패턴 완성 — Anthropic + OpenAI 의 dual provider abstraction + caller 의 의 명시 선택 또는 auto-detect 의 graceful fallback
- [2026-05-22 00:00:00 KST] cycle 83 CustomerServiceBot scan_jailbreak opt-in + 5 신규 PASS (사용자 directive 자율 chain) — `app/bot/customer_service_bot.py` 의 CustomerServiceConfig 의 `scan_jailbreak: bool = False` field 추가 (default 비활성 + server-side bot_handlers cycle 82 통합 정합 + 클라이언트 직접 사용 시 opt-in). answer() pipeline 의 rate limit gate 직후 호출 — config.scan_jailbreak 활성 시 detect_jailbreak(user_message) + BLOCKED signal 시 ValueError "prompt injection 차단" + log.warning + LLM 호출 차단 + SUSPICIOUS signal 시 log.info + 진행 (false positive 회피). logging module import 추가 + module-level logger. import jailbreak_detector 의 JailbreakSignal + detect + summarize_categories. TestJailbreakIntegration 5 신규 — default scan_jailbreak=False + scan disabled 의 통과 + enabled BLOCKED ValueError + LLM 호출 부재 + enabled SUSPICIOUS 통과 + enabled benign 통과. pytest 936 (+5). Phase 3 entry 누계 454. drift 0건 42 연속. 5 검증 PASS. memory project_bot_framework (A) 의 보안 layer 의 dual integration 완성 — server endpoint (cycle 82 default 강제) + client-side CustomerServiceBot (cycle 83 opt-in) 의 양쪽 적용 가능 architecture
- [2026-05-21 23:00:00 KST] cycle 82 jailbreak detector bot_handlers 통합 + 6 신규 PASS (사용자 directive 자율 chain) — `server/api/bot_handlers.py` 의 `_scan_jailbreak(messages)` helper 신설 + handle_bot_chat pipeline 의 _parse_messages 직후 호출 + user role content scan (assistant role skip) + BLOCKED signal → web.HTTPBadRequest 400 + LLM provider 호출 차단 + SUSPICIOUS signal → log.info + 진행 (false positive 회피). 예외 메시지 prompt injection 차단 + idx + categories. import 추가 (JailbreakSignal + detect + summarize_categories). tests/server/test_bot_handlers.py 6 신규 (blocked 400 + suspicious 통과 + benign 통과 + assistant skip + helper blocked + helper none). pytest 931 (+6). Phase 3 entry 누계 449. drift 0건 41 연속. 5 검증 PASS. memory project_bot_framework (A) 의 보안 layer 의 production endpoint 통합 완성 — jailbreak attempt 의 LLM 호출 이전 시점 차단 + Anthropic 호출 비용 절감 + log echo 차단
- [2026-05-21 22:00:00 KST] cycle 81 jailbreak detector heuristic + 33 신규 PASS 9 TestClass (사용자 directive "진행해" 자율 chain) — `app/bot/jailbreak_detector.py` 신설 + prompt injection / jailbreak heuristic detector. JailbreakSignal Enum (NONE / SUSPICIOUS / BLOCKED) + JailbreakMatch frozen dataclass (category + pattern + match_text + severity) + JailbreakResult (signal + matches + score) + detect(text) + is_blocked + summarize_categories helper. 21 pre-compiled regex pattern × 6 category × Korean/English — instruction_override 5 (ignore previous instructions / disregard / forget + 이전 지시 무시 + 앞의 지시 무시) + role_hijack 5 (you are now / act as / pretend to be + 당신은 이제 + DAN/jailbroken/dev mode) + system_leak 3 (show reveal display + what are your + 시스템 프롬프트 보여) + delimiter_injection 3 ([system]: + <|im_start|> + ### system ###) + privilege_escalation 3 (grant admin + unrestricted mode + bypass safety) + info_exfiltration 2 (reveal api_key + api_key=). severity 누적 — score 0 = NONE, score 1 = SUSPICIOUS, score ≥ 2 = BLOCKED. snippet 80자 cap (log hygiene + content fully echo 차단). 33 PASS 9 TestClass — Empty 3 + InstructionOverride 4 + RoleHijack 5 + SystemLeak 4 + DelimiterInjection 3 + PrivilegeEscalation 3 + InfoExfiltration 2 + CombinedMatches 4 + IsBlockedHelper 4 + JailbreakMatch 1. pytest 925 (+33). Phase 3 entry 누계 443. drift 0건 40 연속. 5 검증 PASS. memory project_bot_framework (A) 의 보안 layer 추가 hardening — cycle 74 의 system role 클라이언트 차단 의 직후 layer 의 user content 안 의 의도된 system instruction override 시도 detection
- [2026-05-21 21:00:00 KST] cycle 80 docs/policies/bot-framework.md 정책 본문 신설 (사용자 directive "남은작업 진행해" 자율 chain) — `docs/policies/bot-framework.md` 신설 + Phase 3 bot framework chain (cycle 65~79) 의 누계 통합 정책 정본. §1 운영 규약 + §2 아키텍처 mermaid (11 노드 chain) + §3 보안 layer 5종 (ANTHROPIC_API_KEY 격리 + system role 차단 + RateLimitGate + user_id type confusion 차단 + DoS cap) + §4 라이선스 (GPLv3 + SPDX) + §5 user_id prefix 4 영역 (일반 < 1_000_000 + 고객센터 ≥ 1_000_000 + 방송 도우미 ≥ 2_000_000 + 외부 ≥ 3_000_000) + §6 retry/backoff 정책 (가능 3종 + 불가 3종 + 계산식 + default + production 권장) + §7 RAG dual baseline (5 backend 비교 표 + cache + ranking) + §8 provider plug-in 패턴 + §9 abuse 차단 7 layer + §10 별개 cycle 후보 7종 + §11 참조. AGENTS.md 의 정책 doc 3 → 5 row 갱신 (observability + bot-framework). doc-lint 1 broken link 의 정정 (~/.claude memory path 의 inline link → code block). pytest 892 (변경 무). drift 0건 39 연속. 5 검증 PASS. memory project_bot_framework (사용자 directive 누계 3건) 의 정책 본문 등가 명문화 완성
- [2026-05-21 20:00:00 KST] cycle 79 CachedEmbedder LRU decorator + 10 신규 PASS (사용자 directive "남은작업 진행해" 자율 chain) — `app/bot/rag_context.py` 의 CachedEmbedder 신설 — Embedder Protocol wrapper + OrderedDict 기반 LRU cache (move_to_end on hit + popitem evict at capacity) + max_cache 양수 의무 (default 256 + 0/negative reject) + hit/miss counter instrumentation + dim() delegate + size() + reset_stats() + clear(). collections.OrderedDict import 추가. tests/app/bot/test_rag_context.py 의 TestCachedEmbedder 10 신규 — max_cache zero/negative reject + first miss/second hit + different text separate miss + LRU eviction at capacity + LRU move_to_end on hit + dim delegate + reset_stats (cache 보존) + clear (cache + stats 전수 reset) + EmbeddingRAGStore 통합. pytest 892 (+10). Phase 3 entry 누계 410 (이전 400 + cache 10). drift 0건 38 연속. 5 검증 PASS. memory project_bot_framework (A) 의 RAG context layer 의 비용 optimization 의 진입 — 동일 query 의 embed 호출 의 중복 회피 + sentence-transformers + OpenAI text-embedding-3 의 호출 비용 절감 + 응답 지연 회피 base
- [2026-05-21 19:00:00 KST] cycle 77+78 reviewer P1+P2 회수 + 10 신규 PASS (사용자 directive "미완항목 다 진행해" 자율 chain) — cycle 77 P1 회수: `app/bot/anthropic_client.py` 의 chat() pipeline 의 transport 호출 의 try/except (ConnectionError, OSError, TimeoutError) 추가 + max_retries 의 cap 의무 + 소진 시 AnthropicServerError 의 propagation + jitter 의 결합 정합. TestNetworkErrorRetry 6 신규 — ConnectionError retry then 200 + OSError retry + TimeoutError retry + ConnectionError 소진 ServerError + max_retries=0 즉시 raise + jitter 결합. cycle 78 P2 회수: `server/api/bot_handlers.py` 의 _reply_to_wire 의 hasattr fallback 제거 (BotMessage.role 의 BotRole enum 보장) + handle_bot_chat 의 user_id 의 bool isinstance(int)=True edge case 명시 차단 (auth bypass 회피). TestHandleBotChat 4 신규 — bool/float/string/zero user_id reject. pytest 882 (+10). Phase 3 entry 누계 400. drift 0건 37 연속. 5 검증 PASS. reviewer-agent 보고 P0+P1+P2 의 9건 회수 완료. memory project_bot_framework (A) 의 server-side LLM proxy 의 production-ready hardening 완성 — transient network 장애 회수 + auth bypass 의 type confusion 차단
- [2026-05-21 17:30:00 KST] cycle 76 server.main bot LLM proxy 통합 + reviewer P0 회수 + 6 신규 integration PASS (사용자 directive "미완항목 다 진행해" 자율 GO) — reviewer-agent 코드리뷰 의 P0 차단 항목 회수 (cycle 74 의 register_bot_routes 미연결). `server/main.py` 의 build_app 갱신 — BOT_ENABLED 환경 변수 detect + AnthropicProvider.is_available() 의 ANTHROPIC_API_KEY 가용 시 활성 / 부재 시 MockLLMProvider 폴백 + BOT_RATE_PER_MINUTE 의 RateLimitGate (default 20/min) + register_messages_routes + register_bot_routes 의 등록. `server/api/bot_handlers.py` 의 APP_KEY_PROVIDER + APP_KEY_RATE_GATE 의 web.AppKey type-safe 변환. pyproject.toml 의 NotAppKeyWarning filterwarnings ignore. tests/server/test_main_integration.py 신설 — 6 케이스 (BOT_ENABLED 부재 시 route 미등록 + provider/gate 부재 + Mock 폴백 + custom rate cap + TestClient 의 401 unauthorized + happy path 200 + 비활성 404). pytest 872 (+6). 5 검증 PASS — AST + import + pytest + doc-lint 0 + BPE 0 + pronoun 0 + 의 3회 반복 0. memory project_bot_framework (A) 의 server-side LLM proxy 의 production 통합 완성 — ANTHROPIC_API_KEY 의 서버 영역 격리 + 자동 폴백 + per-user rate limit + route 의 build_app 의 정합
- [2026-05-21 16:30:00 KST] cycle 75 EmbeddingRAGStore abstraction + 15 신규 PASS 3 TestClass (사용자 directive "진행해" 자율 GO) — `app/bot/rag_context.py` 의 EmbeddingRAGStore placeholder 회수 + `Embedder` Protocol (embed + dim 의 sync 호출) + `MockEmbedder` (hash-based deterministic + tokenize → dim slot 누적 + L2 normalize + dim_value 양수 의무 + 빈 텍스트 zero vector) + `cosine_similarity` (차원 mismatch reject + 빈 벡터 reject + zero-norm = 0.0 + identical = 1.0 + orthogonal = 0.0) + EmbeddingRAGStore (Embedder DI + entries add 시 tags + question 결합 텍스트 의 embed 사전 계산 + id 중복 차단 + dim mismatch reject + cosine sim DESC + ASC idx tie stable + sim 0 제외 + top_k 양수 의무). tests/app/bot/test_rag_context.py 의 기존 EmbeddingRAGStore 2 placeholder test 회수 + 15 신규 (Embedding 7 + MockEmbedder 5 + Cosine 5). pytest 866 (+15). Phase 3 entry 누계 384 (이전 369 + Embedding 15). drift 0건 34 연속. 5 검증 PASS — AST + import + pytest + doc-lint 0 + BPE 0 + pronoun 0 + 의 3회 반복 0. memory project_bot_framework (A) 의 RAG context layer 의 vector store baseline 완성 — substring + keyword overlap 의 KeywordRAGStore (cycle 68) + cosine sim 의 EmbeddingRAGStore (cycle 75) 의 dual baseline + Embedder DI 의 sentence-transformers / OpenAI / Voyage 의 실 model 의 plug-in 가능 + caller 의 store type 의 의 선택 가능
- [2026-05-21 15:30:00 KST] cycle 74 server-side /api/bot/chat LLM proxy endpoint + 29 신규 PASS 4 TestClass (사용자 directive 자율 chain GO) — `server/api/bot_handlers.py` 신설. handle_bot_chat POST endpoint — Bearer 인증 + RateLimitGate per-user + JSON body parse + 32 messages cap + 16KB content cap + _parse_role (USER/ASSISTANT 허용 + SYSTEM role 클라이언트 주입 차단 의 보안) + _parse_messages schema validation + AnthropicProvider chat forward + 4 종 Anthropic 예외 → HTTP status 매핑 (AuthError 500 + RateLimitError 503 + ServerError 502 + MalformedError 502 + generic 500). 보안 layer — ANTHROPIC_API_KEY 서버 환경 변수 격리 + system role 클라이언트 주입 차단 + per-user_id rate limit. APP_KEY_PROVIDER + APP_KEY_RATE_GATE app context. tests/server/test_bot_handlers.py 29 케이스 4 TestClass — ParseRole 5 + ParseMessages 10 + ReplyToWire 1 + HandleBotChat 13 (auth + provider missing + invalid JSON + rate limit + happy path + 5 종 예외 매핑 + provider 호출 chain 검증). pytest 851 (+29). Phase 3 entry 누계 369 (이전 340 + bot_handlers 29). drift 0건 33 연속. 5 검증 PASS. memory project_bot_framework (A) 의 server-side LLM proxy 패턴 완성 — API key 서버 영역 격리 + system role 클라이언트 주입 차단 + per-user abuse 차단 + 4 종 예외 매핑 의 production-ready endpoint
- [2026-05-21 14:30:00 KST] cycle 73 AnthropicClient retry-after honor + jitter + transport 3-tuple refactor + 9 신규 PASS (사용자 directive "내가 직접 테스트할 항목을 따로 분리하고 할수있는 작업을 먼저 진행해" 자율 GO) — `app/bot/anthropic_client.py` 의 HttpTransport 응답 schema 의 3-tuple 확장 — `Callable[[...], Awaitable[Tuple[int, dict, dict]]]` (이전 2-tuple → status + headers + body) + `_parse_retry_after(headers)` helper (case-insensitive lookup + 음수/비숫자/빈 차단 + ``_RETRY_AFTER_MAX_SECONDS=60`` cap 의 DoS 회피) + AnthropicClient 의 2 신규 field — `jitter_max_seconds: float = 0.0` (default 부재 + 음수 차단 의 validation) + `jitter_fn: JitterFn = random.random` (sync float [0,1) range 의 함수). chat() pipeline 의 retry-after 헤더 우선 적용 (429 응답 시 헤더 값 → 지수 backoff override + cap) + jitter 추가 (jitter_max_seconds > 0 시 `jitter_fn() * max` 의 추가). `_placeholder_transport` + `httpx_transport` + `from_env` stubs 의 3-tuple 정합 변경. `tests/app/bot/test_anthropic_client.py` 의 기존 6 mock transport 의 3-tuple 의 변경 + `TestRetryAfterAndJitter` 9 신규 케이스 — jitter 음수 reject + retry-after 5초 honor (sleep [5.0]) + Retry-After capitalized (sleep [3.0]) + invalid "garbage" → backoff fallback (sleep [2.0]) + 음수 → fallback (sleep [1.5]) + 9999 → cap 60.0 (sleep [60.0]) + `jitter 0.5 * 2.0 = 1.0` 추가 (sleep [2.0]) + jitter_max=0 default 부재 (sleep [1.0]) + retry-after 4.0 + `jitter 0.25 * 1.0 = 4.25` 결합 (sleep [4.25]). `tests/app/bot/test_llm_proxy.py` 의 2 mock transport 의 3-tuple 정합. pytest 822 (+9). Phase 3 entry 누계 340 (이전 331 + retry-after/jitter 9). drift 0건 32 연속. 5 검증 PASS — AST + import + pytest + doc-lint 0 + BPE 0 + pronoun 0 + 의 3회 반복 0. `docs/exec-plans/active/MANUAL_TESTS.md` 신설 — Claude 자율 불가 항목 8 카테고리 누계 (Anthropic 실 smoke + Toonation API + PyQt6 GUI + PyObjC Quartz + dogfooding + telegram MCP + CI runner + 서버 영역 LLM proxy 실 동작) + Claude 자율 가능 6 cycle (73~78) chain. memory project_bot_framework (A) 의 server-side LLM proxy 의 production-ready reliability layer 진입 — Anthropic 공식 retry-after 헤더 의 honor + 음수/cap 의 robustness + jitter 의 thundering herd 회피 base
- [2026-05-21 13:30:00 KST] cycle 72 AnthropicClient retry/backoff + 9 신규 PASS TestRetryAndBackoff (사용자 directive "다 진행해" 자율 GO) — `app/bot/anthropic_client.py` 의 `AnthropicClient` 의 4 신규 field 추가 — `max_retries: int = 0` (default backwards-compat + 음수 차단) + `backoff_base_seconds: float = 1.0` (양수 의무 + 0 차단) + `sleep_fn: SleepFn = asyncio.sleep` (테스트 mock 주입 가능) + `__post_init__` 의 추가 validation. `chat()` pipeline 의 retry loop 도입 — 429 + 5xx 응답 시 지수 backoff (delay = base * 2^attempt) + `sleep_fn(delay)` 호출 + retry. 401/403 = 재시도 없음 + 즉시 `AnthropicAuthError`. 그 외 4xx = 즉시 base `AnthropicError`. max_retries 초과 시 마지막 status 의 대응 예외 (429 → `AnthropicRateLimitError`, 5xx → `AnthropicServerError`, 메시지 "소진" 포함). `SleepFn = Callable[[float], Awaitable[None]]` 타입 별칭 추가. tests/app/bot/test_anthropic_client.py 신규 `TestRetryAndBackoff` 9 케이스 — `_sequence_transport` (응답 list 의 순차 반환) + `_sleep_recorder` (delays list 의 기록 + 실 대기 없음) + max_retries 음수 reject + backoff_base 0 reject + 429 retry then 200 (delays [1.0, 2.0]) + 5xx retry then 200 (delays [1.0]) + 429 exhausted (delays [1.0, 2.0]) + 5xx exhausted (delays [1.0]) + 401 no retry (delays []) + max_retries=0 default (delays []) + exponential progression (delays [0.5, 1.0, 2.0, 4.0]). pytest 813 (+9). Phase 3 entry 누계 331 (이전 322 + retry 9). drift 0건 31 연속. 5 검증 PASS — AST + import + pytest + doc-lint 0 + BPE 0 + pronoun 0 + 의 3회 반복 0. memory project_bot_framework (A) 의 server-side LLM proxy 의 reliability + abuse 차단 layer 진입 — transient 장애 (Anthropic API 의 의도된 rate limit + 서버 일시 장애) 의 회수 + 영구 장애 (auth 의 영구 차단) 의 빠른 fail-fast 의 분리. 다음 = retry-after 헤더 의 honor + jitter 추가 + 외부 server-side LLM proxy endpoint + httpx 의존성 등록
- [2026-05-21 12:30:00 KST] cycle 71 AnthropicProvider ↔ AnthropicClient adapter + 3 신규 PASS (사용자 directive "다 진행해" 자율 GO) — `app/bot/llm_proxy.py` 의 `AnthropicProvider` 의 NotImplementedError placeholder 회수 + `__init__(self, client: Optional[object] = None)` dependency injection + `chat()` 의 `self._client.chat(messages)` delegate + client 부재 시 `from app.bot.anthropic_client import from_env` 의 lazy 생성 (순환 import 회피 의 함수 내 import) + ANTHROPIC_API_KEY 환경 변수 + httpx_transport default 의 활성 + 후속 호출 의 동일 client 재사용. tests/app/bot/test_llm_proxy.py 의 기존 `test_chat_raises_not_implemented` 회수 (1건) + 3 신규 — `test_chat_lazy_init_no_env_raises` (환경 변수 부재 시 `AnthropicAuthError` propagation) + `test_chat_delegates_to_injected_client` (mock transport 의 200 응답 + AnthropicClient 의 chat delegate + ASSISTANT role reply 검증) + `test_chat_reuses_client_across_calls` (동일 provider 의 2회 chat 호출 + transport counter 누적 검증). pytest 804 (802 + 3 - 1 회수). Phase 3 entry 누계 322 (이전 319 + adapter 3). drift 0건 30 연속. 5 검증 PASS — AST + import + pytest + doc-lint 0 + BPE 0 + pronoun 0 + 의 3회 반복 0. bot framework chain (cycle 65~71) 의 LLM provider abstraction (cycle 65) → Anthropic 의 실 HTTP layer (cycle 70) → adapter wiring (cycle 71) 의 horizontal 통합 완성. memory project_bot_framework (A) 의 server-side LLM proxy 의 실 binding entry 의 wiring 단계 도달 — CustomerServiceBot 의 next cycle 의 AnthropicProvider 의 직접 사용 가능 + httpx 의존성 등록 후 의 immediate 실 API 호출 가능
- [2026-05-21 11:30:00 KST] cycle 70 Anthropic Messages API client + 32 PASS 6 TestClass (사용자 directive "다 진행해" 자율 GO) — `app/bot/anthropic_client.py` 신설. `serialize_messages(messages)` → (system_str, messages_payload) — Anthropic Messages API 의 system role 분리 의 top-level 추출 + user/assistant 만 messages 배열 entry + 여러 SYSTEM 의 `\n\n` 결합 + `parse_response(body)` → BotMessage (content array 의 text block 합본 + content/role=assistant/text 부재 시 `AnthropicMalformedError` + tool_use 등 비-text block 자동 skip) + `AnthropicClient` dataclass (api_key 빈 차단 의 AuthError + model/max_tokens/base_url 검증 + `_DEFAULT_MODEL` claude-3-5-sonnet-latest + `_DEFAULT_MAX_TOKENS` 1024 + build_headers 의 x-api-key/anthropic-version 2023-06-01/content-type + build_body 의 model/max_tokens/system/messages) + `HttpTransport` Protocol (url + headers + body → (status, body) tuple) + `chat()` pipeline 의 4 종 예외 매핑 — 401/403 `AnthropicAuthError` + 429 `AnthropicRateLimitError` + 5xx `AnthropicServerError` + 그 외 4xx `AnthropicError` base + 응답 schema 위반 `AnthropicMalformedError` + `httpx_transport(timeout)` factory (httpx 미설치 graceful ImportError → AnthropicError 의 변환) + `from_env(transport)` 환경 변수 ANTHROPIC_API_KEY → AnthropicClient. 32 케이스 6 TestClass — SerializeMessages 5 (empty + single sys + multi sys 의 `\n\n` 결합 + user/assistant 순서 + sys 의 payload 제외) + ParseResponse 6 (single text + multi text + missing content + role != assistant + text 부재 + tool_use skip) + ClientValidation 5 (empty api_key/model/max_tokens=0/base_url + default fields) + BuildRequest 4 (headers + body model/max_tokens + system field 존재 + system field 부재) + ChatWithMockTransport 9 (empty messages reject + 200 happy + 401/403 auth + 429 rate + 500/503 server + 400 generic + transport spy URL/header/body 검증) + FromEnv 3 (no env reject + env present + transport override). pytest 802 (+32). Phase 3 entry 누계 319 (이전 287 + anthropic 32). drift 0건 29 연속. 5 검증 PASS — AST + import + pytest + doc-lint 0 + BPE 0 + pronoun 0 + 의 3회 반복 0. bot framework chain (cycle 65~70) — llm_proxy 26 + customer_service_bot 30 + streaming_helper 33 + rag_context 27 + customer ↔ rag 통합 6 + Anthropic Messages API 32 = default 2종 + RAG retrieval + provider abstraction + 실 Anthropic binding (transport 주입 의무 의 httpx 미설치 graceful) 완성. memory project_bot_framework (A) 의 server-side LLM proxy 의 실 binding entry 완성 — caller 의 ANTHROPIC_API_KEY 의 환경 변수 + HttpTransport 주입 의 dependency injection 패턴 의 test mock + 별개 cycle 의 httpx 설치 + retry backoff + streaming 응답 (SSE) + 토큰 카운트 + tool use 의 의무
- [2026-05-21 10:30:00 KST] cycle 69 CustomerServiceBot ↔ RAGStore 통합 + 6 신규 PASS (사용자 directive "다 진행해" 자율 GO) — `app/bot/customer_service_bot.py` 의 `CustomerServiceConfig` 에 `rag_top_k: int = 3` field 추가 + `CustomerServiceBot.__init__` 의 `rag_store: Optional[RAGStore] = None` 키워드 인자 + `answer()` pipeline 의 `system_content` augmentation (rag_store 주입 시 `compose_rag_context(user_message, store, top_k=config.rag_top_k)` 산출 markdown 을 system prompt 뒤 `\n\n` 결합 + 빈 결과 augmentation skip). 6 신규 `TestRagStoreIntegration` — default rag_top_k=3 + invalid 0 reject + 부재 시 "참고 FAQ" 부재 + 주입 시 "Q:" + "A:" 출력 + 빈 store skip + rag_top_k=1 cap. pytest 770 (+6). Phase 3 entry 누계 287 (281 + 6). drift 0건 28 연속. bot framework chain (cycle 65~69) — llm_proxy + customer_service_bot + streaming_helper + rag_context + customer ↔ rag 통합 = default 2종 + RAG retrieval + provider abstraction 의 entry 완성
- [2026-05-21 09:30:00 KST] cycle 68 RAG context layer + 27 PASS 5 TestClass (사용자 directive "다 진행해" 자율 GO) — `app/bot/rag_context.py` 신설. `FAQEntry` frozen dataclass (id + topic + question + answer + tags + 빈 차단 검증) + `RAGStore` Protocol (search + add + size) + `_tokenize` (whitespace + lowercase + 한국어/영어 stopword 제거) + `_score_entry` (token overlap 의 0.0~1.0 + substring 발견 시 +0.5 boost + min(1.0)) + `KeywordRAGStore` (entries 의 list + add 의 id 중복 차단 + search 의 DESC score + ASC idx tie 안정 + top_k 양수 의무) + `EmbeddingRAGStore` placeholder (sentence-transformers + cosine 의 별개 cycle) + `build_default_toonation_faq()` 10 entry × 5 영역 (donation/payout/obs/fraud/refund × 2) + `compose_rag_context(query, store, top_k)` markdown 산출 (# 참고 FAQ + Q/A pairs). 27 케이스 5 TestClass — FAQEntryValidation 6 + KeywordRAGStore 11 (empty + add/size + duplicate + init entries + empty query + substring + token rank + top_k + zero k + no match + tags) + EmbeddingRAGStore 2 + BuildDefaultFAQ 4 (10 entry + 5 topics + tags + ids unique) + ComposeRagContext 4 (empty store + no match + markdown + default donation query). pytest 764 (+27). Phase 3 entry 누계 281 (이전 254 + rag 27). drift 0건 27 연속. memory project_bot_framework (A) 의 RAG context 의무 충족 — customer_service_bot 의 system prompt 의 외 의 추가 context injection layer 의 entry
- [2026-05-21 08:30:00 KST] cycle 67 방송 도우미 봇 별개 API StreamingHelperBot + 33 PASS 7 TestClass (사용자 directive "이어서 진행해" 자율 GO) — `app/bot/streaming_helper.py` 신설. `StreamingPlatform` Enum 5종 (YouTube/Twitch/CHZZK 네이버 치지직/Kick/OBS_LOCAL) + `StreamingCommand` frozen dataclass (trigger ! prefix + 32자 cap + response 500자 cap + cooldown_seconds 음수 차단 + enabled) + `StreamingBotConfig` (bot_user_id ≥ 2_000_000 prefix 분리 의 고객센터 봇 1_xxx 와 구분) + `default_streaming_commands()` 5 기본 (!hello + !uptime + !donate + !command + !so 의 nightbot 등가) + `StreamingHelperBot` class (apply_command + cooldown per-trigger + placeholder 치환 {viewer}/{streamer}/{target}/{uptime} + find_command + add_command 중복 차단 + remove_command) + `fetch_platform_callback` 5 platform NotImplementedError placeholder (YouTube Data API + Twitch IRC + CHZZK API + Kick API + OBS WebSocket). 33 케이스 7 TestClass — StreamingCommandValidation 7 (valid + 빈 trigger + ! 부재 + 32자 초과 + 빈 response + 500자 초과 + 음수 cooldown) + ConfigValidation 3 (valid + 낮은 bot_id + 빈 display) + DefaultCommands 3 + FindCommand 5 + ApplyCommand 6 (basic reply + no match + cooldown blocks + cooldown release + placeholder + so target) + AddRemoveCommand 4 + FetchCallback 5 (YouTube/Twitch/CHZZK/Kick/OBS NotImplementedError). pytest 737 (+33). Phase 3 entry 누계 254 (이전 221 + streaming 33). drift 0건 26 연속. memory project_bot_framework (B) 정합 — TooTalk Bot API 와 분리 + 별개 API 의무 충족
- [2026-05-21 07:30:00 KST] cycle 66 default 투네이션 고객센터 봇 CustomerServiceBot + 24 PASS 5 TestClass (사용자 directive "진행해" 자율 GO) — `app/bot/customer_service_bot.py` 신설. `CustomerServiceConfig` frozen dataclass (bot_user_id ≥ 1_000_000 의무 + display_name + system_prompt + max_history_turns + rate_limit_per_minute, 5 영역 검증) + `default_system_prompt()` Toonation 5 영역 (후원 / 정산 / OBS 설정 / 사기 신고 / 환불) + 보안 (사용자 prompt injection override 차단 + 개인정보 금지 + 800자 한도 의 escalation) + `default_customer_service_config()` (bot_user_id 1_000_001 + "Toonation 고객센터" + 5 turns + 20 rate) + `truncate_history(history, max_turns)` (max_turns × 2 cap + 최근 우선) + `CustomerServiceBot` class (config + provider + gate Optional + answer async + remaining_calls + config property). answer 의 pipeline = user_id 양수 + user_message 빈 차단 + RateLimitGate.allow + system prompt + history trim + user message 의 LLM chain. 24 케이스 5 TestClass — DefaultSystemPrompt 4 (non-empty + 5 영역 + 보안 + Toonation) + ConfigValidation 6 (valid + low bot_id + 빈 display + 빈 prompt + 0 history + 0 rate) + TruncateHistory 5 (empty + under + at + over + zero) + CustomerServiceBot 9 (basic + zero user + empty msg + rate block + history passed + history trimmed + remaining + config + external gate). pytest 704 (+24). Phase 3 entry 누계 221 (이전 197 + bot customer 24). drift 0건 25 연속
- [2026-05-21 06:30:00 KST] cycle 65 Phase 3 bot LLM proxy skeleton + 26 PASS 5 TestClass + cycle 63+64 평가 HTML 정정 (사용자 directive "디제 작업 재개해" + 3 추가 비판 회수 — 평가 html 미갱신 + 분포비율 누락 + 4자리 미적용 + 현재 단계 명시) — `app/bot/__init__.py` + `app/bot/llm_proxy.py` 신설. `BotRole` Enum (USER + ASSISTANT + SYSTEM) + `BotMessage` frozen dataclass (role + content 빈 차단 + content 16 KB cap + timestamp_ms 음수 차단) + `LLMProvider` Protocol (is_available classmethod + chat async) + `MockLLMProvider` (deterministic echo + last user message extraction + empty list / no user role 의 ValueError) + `AnthropicProvider` placeholder (ANTHROPIC_API_KEY env + httpx import 의 is_available + chat NotImplementedError 의 graceful) + `select_llm_provider(name)` factory (mock / anthropic / openai NotImplementedError / gemini NotImplementedError / unknown ValueError / None 의 auto detect 의 anthropic 우선 + 가용 부재 시 mock 폴백) + `RateLimitGate` (rate_per_minute default 20 + token bucket per user_id + allow + remaining + 1분 prune + monotonic timestamp + user_id 양수 의무). 26 케이스 5 TestClass (BotMessageValidation 5 + MockLLMProvider 5 + AnthropicProvider 2 + SelectLLMProvider 6 + RateLimitGate 8). pytest 680 (+26). Phase 3 entry 누계 197 (이전 171 + bot 26). 부수 cycle 63 (bd1b14c) = vibe-coding HTML drift 8건 정정 (callout + 종합 row + 사이클 효율 + meta badge + last_verified + L3 가드레일 + productization 가드레일·자동화 34 → 37 sweep). 부수 cycle 64 (50e64bf + 501e5b6) = vibe-coding HTML §1.1 enforcement layer designer 분포 비율 표 신규 추가 (cycle 61 .md 갱신 의 mirror sneak through 회수) + §6 비교 기준 표 의 4자리 소수점 적용 (점수 X.XXXX/10 + 추정 비율 X.XXXX% + 세계/국내 2 column 분리 + L0~L5 6 row 점진 향상) + L5 row 의 ✅ "현재 본 사용자 자리" badge + 그라데이션 callout (현재 본 사용자 단계 = L5 enforcement layer designer 의 명시). drift 0건 24 연속
- [2026-05-21 05:30:00 KST] cycle 62 MessagesClient REST wrapper + 20 PASS + HTML mirror Stop hook 신설 + 병렬 작업 의무 영구화 (사용자 directive "다시 작업 재개해" + 2 추가 directive) — `app/net/messages_client.py` 신설 (`MessagePayload` frozen dataclass + `from_wire` 변환 + `MessageFetchResult` (messages/count/limit) + `MessagesClient` aiohttp wrapper + Bearer 인증 + query string room_id/start_ts_ms/end_ts_ms/limit + 4 종 exception MessagesAuthError/BadRequest/ServerError/NetworkError). 20 케이스 4 TestClass (MessagePayloadFromWire 4 + MessagesClientValidation 3 + ListMessagesInRangeValidation 4 + ListMessagesInRangeResponse 9 — 200 + 401 + 400 + 500 + 302 + network + bearer header + query string). pytest 654 (+20). 부수: `tools/hook_html_mirror_consistency.sh` 신설 (CLAUDE.md §10-6 6 pair drift Stop hook block) + .claude/settings.json Stop matcher 4번째 entry 등록 + 영구 memory 신설 `feedback_parallel_execution_mandatory.md` (사용자 directive "병렬작업 할 수 있는 항목은 무조건 병렬작업으로 해"). MEMORY.md 37 영구 가드레일. Phase 3 entry 누계 171 (이전 151 + messages_client 20). drift 0건 23 연속
- [2026-05-21 03:30:00 KST] cycle 60 server list_messages_in_range REST + 18 PASS + TooTalk SVG 로고 신설 (사용자 directive "잔여 작업 진행해" + 투네이션 logo 의 Talk 텍스트 부착 SVG directive) — `server/db/repositories/messages.py` 의 `list_messages_in_range(pool, room_id, start_ts, end_ts, limit)` 함수 신규 (end_ts 의 start_ts 초과 의무 + limit 양수 의무 + created_at DESC + id DESC 정렬 + ChatView lazy load 의 server-side counterpart) + `server/api/messages_handlers.py` 신설 (GET /api/messages?room_id&start_ts_ms&end_ts_ms&limit query endpoint + `_DEFAULT_LIMIT` 1000 + `_MAX_LIMIT` 5000 의 unbounded SELECT 차단 + auth_middleware Bearer 의무 + ms → datetime UTC 변환 + MessageRow → JSON wire 의 한글 보존 ensure_ascii=False). tests/server/test_messages_handlers.py 18 케이스 4 TestClass — ParseIntQuery 4 + MsToDatetime 3 + MessageRowToWire 3 + HandleListMessagesInRange 8 (missing user_id Unauthorized + missing room_id BadRequest + end_ts before start + limit 0/exceeds max/invalid string BadRequest + valid 2 messages + empty result). pytest 634 (+18). Phase 3 entry 누계 = 151 (permission 20 + protocol 19 + capture 22 + input_forward 17 + dogfooding 18 + chat_history_policy 37 + messages_handlers 18). TooTalk 로고 — `app/assets/branding/tootalk_logo.svg` 신설 (Toonation `apple-touch-icon.png` 의 "+OO" 패턴 SVG 등가 + plus rounded bars medium blue #4B95FC + ring 2개 light blue #A8C5FF + medium blue #4B95FC + "Talk" wordmark dark slate #1F2937 Inter / SF Pro 48px 700 weight + viewBox 0 0 380 100 + GPLv3 SPDX). drift 0건 21 연속
- [2026-05-21 02:30:00 KST] cycle 59 ChatView volatile + lazy load 정책 layer + 37 PASS 8 TestClass + bot framework 사양 명문 (사용자 directive "좋아 진행해" + Phase 3 bot 신규 사양 directive) — `app/ui/chat_history_policy.py` 신설. `MessageMetadata` frozen dataclass (message_id + timestamp_ms + room_id 양수 검증) + `LazyLoadRequest` frozen dataclass (room_id + before_ts + limit_days + start_ts property clamped to 0) + `_MAX_VOLATILE_DAYS = 30` constant + `_MS_PER_DAY = 86_400_000` + `_ESTIMATED_KB_PER_MESSAGE = 10.0` + `volatile_threshold_ms(now_ms, days)` (now - days * 86_400_000 clamped 0) + `should_purge(meta, now_ms, days)` (정확 cutoff 시점 = keep ≥ 의 정합) + `partition_volatile_active(metas, now_ms, days)` ((purge, keep) tuple + 입력 순서 의무 보존) + `next_load_request(room_id, oldest_loaded_ts, days)` (scroll top 도달 의 server fetch request 산출) + `estimate_purged_memory_kb(count, kb_per_message)` (10 KB / message default + 회수 memory 의 추산) + `oldest_timestamp(metas)` (빈 list None 폴백). tests/app/ui/test_chat_history_policy.py 37 케이스 8 TestClass — MessageMetadataValidation 4 + LazyLoadRequestValidation 7 (start_ts property + clamped 검증) + VolatileThreshold 6 (custom days + clamped + reject) + ShouldPurge 4 (boundary 정확 + plus 1ms purge) + PartitionVolatileActive 5 (empty + all kept + all purged + split + order preserved) + NextLoadRequest 3 (default 30 + custom 7 + start_ts chain) + EstimatePurgedMemory 5 (zero + default 10KB + custom + 음수 차단 + zero kb_per_message 차단) + OldestTimestamp 3. pytest 616 (+37). 사용자 directive 2026-05-21 — Phase 3 bot framework 신규 사양: (a) **투네이션 고객센터 봇 (default 배치)** = LLM 연동 인터랙티브 대화형 Q&A (Toonation FAQ + 정책 + RAG, Anthropic Claude / OpenAI / Gemini server-side proxy, rate limit + prompt injection 차단) + (b) **방송 도우미 봇** = OBS + YouTube / Twitch / CHZZK / Kick 통합 (나이트봇 등가, 사용자 설정 추가 가능, 명령 + 자동응답 + 타이머 + 단어 필터 + 후원 알림) + **별개 API 의무** (TooTalk Bot API 와 분리 + streaming platform callback + OBS WebSocket + Toonation 직접 통합 옵션 B 핵심). memory project_bot_framework.md 갱신 + MEMORY.md 인덱스 정합. Phase 3 entry 누계 = 133 (permission 20 + protocol 19 + capture 22 + input_forward 17 + dogfooding 18 + chat_history_policy 37). drift 0건 20 연속
- [2026-05-21 01:30:00 KST] cycle 58 Phase 3 input forward skeleton + 17 PASS 5 TestClass + 메모리 누수 차단 영구 memory 2건 신설 + 원격 control controller/target 용어 명확화 (사용자 directive "작업 진행해" + 3 비판 회수 — objc CFRelease + 누적 채팅 + 키보드/마우스 제어 방향) — `app/remote/input_forward.py` 신설. `InputForwardBackend` Protocol (is_available + apply) + `MockInputForwardBackend` (applied 누적 list + reset + raise_on_apply fail-fast 시나리오) + `MacOSCGEventBackend` placeholder (NotImplementedError graceful + CGEventCreate* CFRelease 의무 docstring) + `select_input_backend(platform_name)` factory + `apply_events(backend, events)` fail-fast batch dispatch + `filter_events_by_type(events, event_type)` filter. tests/app/remote/test_input_forward.py 17 케이스 5 TestClass — MockInputForwardBackend 4 (is_available + apply 누적 + reset + raise) + MacOSCGEventBackend 1 (NotImplementedError) + SelectInputBackend 5 (mock/darwin/win32/linux/unknown) + ApplyEvents 3 (empty + all succeed + fail-fast on raise) + FilterEventsByType 4 (mouse_move + key_down + no_match + order preserved). 영구 memory 신설 — `feedback_objc_memory_release_mandatory.md` (PyObjC CGEvent / CGImage / CFData 의 CFRelease 의무 + tracemalloc + objgraph 회귀 검증 + autorelease pool 패턴 + 60 fps × 1080p RGB = 분당 1.3 GB 누수 예시) + `feedback_chat_accumulation_memory_release_mandatory.md` (ChatView 1개월 volatile + lazy load page fetch + file chunk 즉시 release + pending_acks LRU + server messages list_recent LIMIT + tracemalloc 검증). 원격 control 용어 정합 — `protocol.py` + `capture.py` + `input_forward.py` 의 sender / recipient → controller (요청자 + input 제공) / target (대상 + screen 제공 + 키보드/마우스 의 controller 의 input event 의 OS 적용) 명확화 (사용자 directive 2026-05-21 "대상의 키보드 마우스를 제어"). pytest 579 (+17). Phase 3 entry 누계 96 (permission 20 + protocol 19 + capture 22 + input_forward 17 + dogfooding 18). drift 0건 19 연속
- [2026-05-21 00:30:00 KST] cycle 57 Phase 3 screen capture skeleton + 22 PASS 6 TestClass (사용자 directive "진행해" 자율 GO) — `app/remote/capture.py` 신설. `CaptureFormat` Enum (BGRA + RGB) + `CapturedFrame` frozen dataclass (width / height 양수 + capture_time_ms 음수 차단 + buffer 크기 정합 width×height×bpp) + `CaptureBackend` Protocol (is_available classmethod + capture() instance method) + `MockCaptureBackend` (deterministic 1x1 BGRA gray pixel + 가변 dimension) + `MacOSQuartzBackend` placeholder (sys.platform=="darwin" + Quartz import 의 is_available + capture NotImplementedError) + `select_capture_backend(platform_name)` factory ("mock"/"darwin" → Mock/Quartz, "win32"/"linux" → NotImplementedError, unknown → ValueError) + `detect_default_backend` (darwin = Quartz / 그 외 = Mock 폴백) + `captured_to_remote_frame(captured, frame_id)` (BGRA → RGB swap + alpha drop, RGB pass-through, RemoteFrame RAW_RGB 변환). tests/app/remote/test_capture.py 22 케이스 6 TestClass — CapturedFrameValidation 7 + MockCaptureBackend 4 + MacOSQuartzBackend 1 + SelectBackend 5 + DetectDefaultBackend 1 + CapturedToRemoteFrame 4 (RGB pass + BGRA swap 1pixel + BGRA swap 2pixel + frame_id propagate). pytest 562 (+22). Phase 3 entry 누계 79 (permission 20 + protocol 19 + capture 22 + dogfooding 18). Structure / ARCHITECTURE app/remote row 갱신 + HTML 2 mirror. drift 0건 18 연속
- [2026-05-20 23:30:00 KST] cycle 53 release GO + 54 v0.2.0-phase2 tag + 55 Phase 3 entry 원격 데스크탑 skeleton + 56 dogfooding harness (사용자 directive "전부 진행해" 자율 GO) — cycle 53 release-agent (a4fe53cd) GO 판정 = 머지 게이트 3종 (reviewer ✅ + qa ✅ + observability ✅) + CI 8 job GREEN (run 26016794138) + M1~M7 정합. cycle 54 = `git tag -a v0.2.0-phase2` annotated tag 생성 + push (Phase 2 16 module + 290 케이스 + 483 pytest + workflow chain 완성 기록) + memory project_bot_framework.md 갱신 (Phase 3+ → Phase 3 마무리 직전 단계 의 사용자 directive 2026-05-20 정합). cycle 55 = Phase 3 entry 원격 데스크탑 skeleton — `app/remote/` 패키지 (init + permission.py + protocol.py). `PermissionMode` Enum (HELP + CONTROL 2 mode) + `PermissionRequest` + `PermissionGrant` (granted_at + expires_at + 32B revoke_token + scope) + `derive_revoke_token` + `check_grant_active`. `FrameFormat` Enum (raw_rgb / png / jpeg) + `InputEventType` Enum (mouse_move / mouse_click / key_down / key_up) + `RemoteFrame` (frame_id + width + height + format + payload + timestamp) + `RemoteInput` (event_type 별 payload 필수 key 검증) + `RemoteSession` (16B session_id + grant + started_at + bandwidth_bps). tests 39 케이스 (PermissionRequestValidation 8 + PermissionGrantValidation 5 + DeriveRevokeToken 2 + CheckGrantActive 5 + RemoteFrameValidation 7 + RemoteInputValidation 7 + RemoteSessionValidation 5). cycle 56 = dogfooding harness — `tools/dogfooding_harness.py` (MetricSample + MetricCollector monotonic + sample_rss_mb / sample_disk_used_mb psutil 기반 + estimate_rtt_ms p50/p95 통계 + estimate_throughput_mbps 변환 + write_report JSON 한글 보존). tests 18 케이스 (MetricSampleValidation 4 + MetricCollector 4 + EstimateRtt 4 + EstimateThroughput 3 + WriteReport 3). pytest 540 (+57 신규). Phase 3 entry 누계 57 (remote 39 + dogfooding 18). drift 0건 17 연속
- [2026-05-20 22:30:00 KST] Phase 2 cycle 51 qa-agent + 52 observability-agent serial chain PASS + 차단 사유 3종 회수 (사용자 비판 "서브에이전트 적극 활용" 회수) — workflow ③ 완성 (reviewer ✅ + qa ✅ + observability ✅). cycle 51 qa CONDITIONAL PASS 의 차단 사유 3종 = (1) decrypt_backup version enforcement gap (v1 spoof bundle 복원 성공) (2) BPE U+CE21 11건 잔존 (정정 범위 외 — app/ui + app/net + tests/) (3) self-pronoun 9건 잔존 (app/net + app/core + tests). cycle 52 정정 = (1) `app/backup/encrypted_backup.py:241-263` 의 `if bundle.version != _BACKUP_VERSION: raise ValueError("unsupported backup version")` 추가 + `test_v1_bundle_rejected_by_decrypt` 신규 (v1 spoof bundle InvalidVersion ValueError 검증) + (2) BPE 12건 정정 (qa report 11 + 1 detect — `app/ui/{signup,login}_dialog.py` + `app/net/auth_client.py` + tests 5 file 의 자동 정정) + (3) self-pronoun 9건 정정 (`app/net/signaling_client.py` + `app/core/app_state.py` + `tests/app/crypto/test_session.py` 의 self-pronoun → self / 3rd-pronoun → peer 일괄). 전수 검증 = BPE 0건 + self-pronoun 0건 전체. cycle 52 observability PASS = PBKDF2 600K iter 94.5ms 평균 (OWASP <1000ms 의 10.5x margin) + pytest 3.03s + import smoke 27.5ms + env var 7/7 baseline 정합 + cipher suite OWASP 2023 정합. pytest 483 passed (+1 신규). Phase 2 누계 290. handoff §8.48 신설 (workflow ③ serial chain 완성 기록). drift 0건 14 연속
- [2026-05-20 21:30:00 KST] Phase 2 cycle 49 reviewer-agent P0 정정 + cycle 50 PBKDF2 stretching + SPDX 정정 + 24 PASS (사용자 directive "남은작업 진행해" 자율 GO) — cycle 49 (a2c157e) = reviewer-agent CONDITIONAL PASS 의 P0 정정 (BPE U+CE21 13건 + self-pronoun 5건 of 5 file e2ee/double_ratchet/session/skipped_keys/x3dh). cycle 50 = P1#2 PBKDF2-HMAC-SHA256 600K iter stretching (OWASP 2023 권장 + bcrypt 12 rounds 등가 안전 margin) `app/backup/encrypted_backup.py` 의 HKDF v1 → PBKDF2 v2 backward incompatible bump + P2#1 SPDX header (`app/ui/chat_view.py` + `app/ui/main_window.py` 사이클 39 / 41 부재 회수). tests 24 케이스 (cycle 48 22 + cycle 50 신규 2 — `_PBKDF2_ITERATIONS == 600_000` + `_BACKUP_VERSION == "2"`). pytest 482 (+2). Phase 2 누계 289. handoff §8.47 신설 — reviewer cycle 49 CONDITIONAL PASS + P0 정정 완료 + P1 hotfix backlog 3건 + P2 향상 4건 등재 + Phase 2 누계 모듈 16종 표. Phase 2 마무리 게이트 PASS 판정. drift 0건 13 연속
- [2026-05-20 20:30:00 KST] Phase 2 encrypted backup / restore + 22 PASS 5 TestClass (사용자 directive "남은 작업 진행해" 자율 GO 사이클 48) — `app/backup/` 패키지 신설 (init + encrypted_backup.py). `BackupEntry` frozen dataclass (message_id + plaintext bytes + timestamp_ms 음수 차단) + `BackupBundle` frozen dataclass (version + created_at_ms + salt 16B + EncryptedPayload). 5 함수 — `derive_backup_key(password, salt)` HKDF-SHA256 32B (PBKDF2 stretching = 별개 cycle 의 placeholder) + `encrypt_backup(entries, password, *, created_at_ms, salt=None)` (entries → JSON → AES-256-GCM) + `decrypt_backup(bundle, password)` (역방향, wrong password = InvalidTag) + `serialize_bundle / deserialize_bundle` wire format bytes (base64 + JSON 한글 UTF-8 보존). 22 케이스 5 TestClass (BackupEntryValidation 4 + BackupBundleValidation 4 + DeriveBackupKey 5 + EncryptDecryptRoundTrip 5 (round-trip + empty + wrong password + tampered blob InvalidTag + custom salt carry) + SerializeBundle 4 (wire round-trip + decrypt 정합 + 필드 누락 + non-dict root)). pytest 480 (+22). Phase 2 누계 287. Structure / ARCHITECTURE app/backup row 신설 + HTML 2 mirror 동기. drift 0건 11 연속

---

**문서 상태**: `active` · 최초 작성 2026-05-17 · M2 변경 이력 30행 캐시
운영. 30행 초과 시점부터 회전 + History.md 위임.
