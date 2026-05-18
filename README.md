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

- [2026-05-22 12:30:00 KST] cycle 98 평가 snapshot 4 영역 rewrite + HTML 2 mirror 동기 — `docs/assessments/productization.md` §1 종합 9.98 → 9.99 ▲ (cycle 94~98 reviewer + QA 회수 chain 8 항목 + httpx + DB audit). 기술 완성도 8.65 → 8.75, 차별화 9.75 → 9.8, 세션 정합 9.74 → 9.78, 보안 hardening 8.65 → 8.85. `docs/assessments/vibe-coding.md` §1 종합 10.0000 유지 (가드레일 9.9800 → 9.9900, directive 명확성 8.2000 → 8.3000, 도메인 비전 9.7500 → 9.8000, 기술 의사결정 9.6000 → 9.6500, 세션 정합 9.6500 → 9.7000, enforcement layer 9.7500 → 9.8000). `docs/html/productization.html` + `docs/html/vibe-coding.html` 2 mirror title + last_verified + 종합 row + meta callout 동기. 전체 pytest = 1101 + 2 skipped (변경 무 — 평가 snapshot). drift 0건 53 연속. Phase 3 종결 prerequisite 완전 도달 — cycle 99 v0.3.0-phase3-bot tag + release-agent + handoff §8.51+ 갱신
- [2026-05-22 12:00:00 KST] cycle 97 보조2 — DB audit timestamp + IP + activity tracking migration 0003 + 영구 memory 신설 (사용자 directive "회원 가입 시 db 업데이트 인서트 할때 datetime 반드시 남기도록 + 마케팅 통계 + 접속자 IP + 접속 시간 + 활동 시간 추적") — `server/db/migrations/0003_user_activity.sql` 신설. (1) users ALTER — `signup_ip` (IPv4/IPv6, nginx X-Forwarded-For parse) + `signup_user_agent` (클라이언트 분포 통계) + `last_login_ip` (의심 활동 감지) + `last_activity_at` (DAU/MAU 정의 base, aiohttp middleware 1분 throttle 갱신) + 2 index. (2) `user_sessions` 신설 — id + user_id (FK) + session_token_hash (SHA-256) + ip_address + user_agent + connected_at + last_active_at + disconnected_at + duration_seconds + end_reason (5 ENUM) + 5 index. (3) `user_activity_log` 신설 — id + user_id (FK) + action (22 ENUM: signup/login/message_send/file_send/bot_chat/remote_request 등) + target_id + ip_address + user_agent + metadata JSON + created_at + 4 index. (4) email_verification + password_reset ALTER — `requester_ip` 추가 (부정 가입 / brute force 차단 base) + 2 index. 모든 필드 5요소 comment 정합 ([[feedback-db-schema-field-comments]]). 영구 memory `feedback_db_audit_timestamp_ip_activity.md` 신설 — DB INSERT/UPDATE datetime 의무 + IP retention 90일 cap + Phase 4 cycle 109~110 nginx X-Forwarded-For + cycle 113~114 aiohttp middleware. MEMORY.md 인덱스 갱신 39 영구 가드레일. 전체 pytest = 1101 + 2 skipped (변경 무, schema migration). drift 0건 53 연속
- [2026-05-22 11:30:00 KST] cycle 97 보조 — httpx 의존성 등록 + Phase 4 §1.4 사전 의존성 install 섹션 신설 (사용자 directive "httpx 설치도 계획에 잡아") — `server/requirements.txt` 에 `httpx>=0.27` entry 추가 (AnthropicClient + OpenAIClient httpx_transport factory 실 binding 의무, 미설치 시 graceful is_available False → MockLLMProvider 폴백). `docs/exec-plans/active/2026-05-22-phase4-infra-setup.md` §1.4 사전 의존성 install 섹션 신설 — httpx>=0.27 (cycle 100 의무) + firebase-admin>=7.0 (cycle 103~104) + obs-websocket-py (Phase 5+ 보류) 의 3 패키지 install 순서 + verify gate (`pytest test_main_integration.py` 의 2 skip → 0 skip 전환) + 보안 의무 (`pip install --require-hashes` + `httpx[http2]` + `httpx[socks]` + service-account.json git ignore). `docs/policies/bot-framework.md` §10.1 갱신 — cycle 97 strike-through (정책 §10.1 + httpx entry + Phase 4 §1.4 신설) + cycle 100 prerequisite (httpx install + 2 skip → 0 skip 검증) + cycle 101~117 (Phase 4 본문). 전체 pytest = 1101 passed + 2 skipped (변경 무 — 의존성 등록 + 문서). drift 0건 53 연속
- [2026-05-22 11:00:00 KST] cycle 97 bot-framework.md §10.1 strike-through (cycle 88~96 implemented 6 항목 완료 마킹) (사용자 directive 진행해 자율 chain) — Phase 3 종결 chain 진입. `docs/policies/bot-framework.md` §10.1 갱신 — cycle 88 (SPDX P2-1 + 정책 §10) + cycle 89~90 (provider lazy init asyncio.Lock P2-2) + cycle 91~93 (UsageTracker deque maxlen + EscalationQueue evict_old + RateLimitGate prune_stale P1-1) + cycle 94 (CachedEmbedder threading.RLock P1-2) + cycle 95 (jailbreak detector info_exfiltration 2 → 17 QA P2) + cycle 96 (server/main.py provider 3 layer fallback chain QA P3) 6 항목 strike-through + 항목별 핵심 산출물 명문. 본 cycle 97 = 정책 본문 갱신. cycle 98 = 평가 snapshot rewrite. cycle 99 = v0.3.0-phase3-bot tag + release-agent + handoff. 전체 pytest = 1101 passed + 2 skipped (변경 무 — 문서 단독). drift 0건 53 연속. 5 검증 PASS
- [2026-05-22 10:00:00 KST] cycle 96 server/main.py LLM provider 3 layer fallback chain + 3 신규 PASS (사용자 directive 진행해 자율 chain) — QA P3 회수. 기존 `build_app()` 의 provider 선택은 Anthropic 가용 시 `AnthropicProvider`, 부재 시 즉시 `MockLLMProvider` 폴백 (`OpenAIProvider` 미고려). 신규 chain — `AnthropicProvider.is_available()` → `OpenAIProvider.is_available()` → `MockLLMProvider` 3 layer. import 변경 (`OpenAIProvider` 추가). 분기별 log 명문 — Anthropic 활성 info, OpenAI 폴백 info + ANTHROPIC 부재 명시, Mock 폴백 warning + "두 key 모두 부재 + 프로덕션 배포 시 환경 변수 설정 필수" 명시. `tests/server/test_main_integration.py` 3 신규 — `test_openai_fallback_when_only_openai_key_present` (httpx 미설치 시 graceful skip) + `test_anthropic_preferred_over_openai` (둘 다 가용 시 Anthropic 우선) + `test_mock_when_both_keys_absent` (Mock 폴백 검증). 전체 pytest = 1101 passed + 2 skipped. reviewer P0+P1+P2+P3 + QA P2+P3 회수 chain 완료 — Phase 3 종결 prerequisite 확보. drift 0건 52 연속. 5 검증 PASS
- [2026-05-22 09:00:00 KST] cycle 95 jailbreak detector `info_exfiltration` 패턴 확장 + 21 신규 PASS (사용자 directive 진행해 자율 chain) — QA P2 회수. `app/bot/jailbreak_detector.py` info_exfiltration category 2 → 17 패턴 확장. 신규 14 패턴 — (1) 환경 변수 추출 (`show/print/dump/cat .env`, `os.environ[]`, `process.env[]`), (2) JWT/Bearer/refresh token 추출, (3) SSH/private key 추출 (`id_rsa`, `id_ed25519`, PEM header `-----BEGIN ... PRIVATE KEY-----`), (4) DB credential 추출 (mysql/postgres/mariadb/mongo password) + connection string (`mysql://user:pw@host`), (5) Korean credential 노출 시도 (비밀번호/패스워드/암호/키/토큰/시크릿/크리덴셜 + 알려/공개/출력/보여/노출), (6) Korean PII 노출 시도 (주민등록번호/카드번호/전화번호/이메일), (7) 주민등록번호 regex `\d{6}-[1-4]\d{6}`, (8) SQL injection (`DROP/TRUNCATE/DELETE TABLE`, `UNION SELECT`, `OR 1=1`), (9) Shell command (`cat /etc/passwd`, `cat ~/.aws/credentials`, `~/.ssh/`, `~/.config/`). `tests/app/bot/test_jailbreak_detector.py` `TestInfoExfiltration` 21 신규 — dump_env + os_environ + process_env + reveal_jwt + show_private_key + cat_ssh_key + pem_header + db_password + db_connection_string + korean_password + korean_apikey + korean_env_vars + korean_pii_phone + korean_resident_number + rrn_pattern + sql_drop + sql_union + sql_or_1_eq_1 + cat_etc_passwd + aws_credentials + benign_password_question (trade-off 명시). pytest 1100 (+21). server-side bot endpoint (cycle 82) + CustomerServiceBot (cycle 83) 의 jailbreak detector dual integration 의 detection 범위 확장 — credential exfiltration + Korean PII + SQL injection + shell command injection 의 13 신규 vector 차단. drift 0건 51 연속. 5 검증 PASS
- [2026-05-22 08:00:00 KST] cycle 94 CachedEmbedder `threading.RLock` thread-safety + 3 신규 PASS (사용자 directive 진행해 자율 chain) — reviewer P1-2 회수. `app/bot/rag_context.py` CachedEmbedder 에 `threading.RLock` 도입, LRU 연산 atomic 보장 (move_to_end + popitem + hits/misses counter increment race 차단). `import threading` 추가, `self._lock` field 신설, `embed()` cache lookup + counter increment 는 lock 안, backend `embedder.embed()` 호출은 lock 외 (contention 회피), double-check pattern (lock 재획득 시 existing cache entry 재확인 + duplicate compute 폐기), `size()`/`reset_stats()`/`clear()` 모두 lock 안. docstring 갱신 — "thread-safety 미보장" 표기 회수 + multi-thread atomic 보장 명문. `TestCachedEmbedderConcurrency` 3 신규 — `concurrent_same_text` (50 thread 동일 text, size=1, hits+misses=50), `concurrent_distinct_text` (32 distinct, size=32, misses=32), `concurrent_lru_eviction` (100 호출 max_cache=8, size ≤ 8, 합산 100). pytest 1079 (+3). reviewer P1-2 회수 완료 — async sentence-transformers / OpenAI text-embedding-3 전환 prerequisite. drift 0건 50 연속. 5 검증 PASS
- [2026-05-22 07:00:00 KST] cycle 91 unbounded memory growth 회수 batch + 14 신규 PASS (사용자 directive 진행해 자율 chain) — reviewer P1-1 회수 (3 module batch). (a) UsageTracker `collections.deque(maxlen)` ring buffer 의 oldest FIFO evict + `max_records: int = 100_000` default + 0 = 무제한 fixture + max_records property. (b) EscalationQueue `evict_old(now_ms, retention_ms)` — RESOLVED / CLOSED 의 resolved_at_ms < cutoff evict + retention 음수 차단 + PENDING / ASSIGNED 의 resolved_at_ms 부재 skip. (c) RateLimitGate `prune_stale(now_seconds)` — 모든 timestamp cutoff 이전 인 user_id key 자체 삭제 + `active_users()` monitoring helper. tests 14 신규 — TestUsageTrackerMaxRecords 4 + TestEvictOld 6 + TestRateLimitGateStalePrune 4. pytest 1076 (+14). drift 0건 49 연속
- [2026-05-22 06:00:00 KST] cycle 89 provider lazy init asyncio.Lock + 4 신규 PASS (사용자 directive 진행해 자율 chain) — reviewer P2-2 회수. `app/bot/llm_proxy.py` 의 AnthropicProvider + OpenAIProvider 의 race condition 차단. `_init_lock: Optional[asyncio.Lock] = None` field 추가 (lazy create + sync `__init__` event loop 부재 회피) + chat() pipeline 의 double-check pattern (lock 획득 후 self._client 재확인). asyncio import 추가. tests/app/bot/test_llm_proxy.py 의 TestProviderConcurrentInit 4 신규 — Anthropic + OpenAI 의 symmetric concurrent 5 chat → from_env 1회 (monkeypatch counting from_env) + lazy lock None 초기 + client 명시 주입 시 lock 부재. pytest 1062 (+4). drift 0건 48 연속. 5 검증 PASS
- [2026-05-22 05:00:00 KST] cycle 88 reviewer P2+P3 회수 + chat BPE hook 신설 (사용자 directive 자율 chain + 비판 회수) — (1) `server/main.py` 의 SPDX-License-Identifier 첫 줄 prepend (reviewer P2-1 회수 — 정책 bot-framework.md §4 의 모든 .py SPDX 의무 정합). (2) `docs/policies/bot-framework.md` §10 갱신 — cycle 81~87 implemented 5종 strike-through (streaming response SSE + OpenAI provider + jailbreak detector + 사용 통계 추적 + escalation 사람 상담) + §10.1 신설 (cycle 88~96 reviewer/QA 회수 + cycle 100~117 Phase 4 진입 timeline). (3) chat output BPE pollution 회수 chain — `tools/hook_chat_bpe_check.sh` 신설 (Stop hook + transcript JSONL last assistant message scan + 의 3회 + 의 4회 escalation + density >8 per line + U+CE21 보강 + exit 2 사용자 노출) + `.claude/settings.json` Stop array 5번째 entry 등록 + `_related_memory` 추가 + `hook_post_write_inspect.sh` 확장 (의 4회 escalation 분리 메시지 + 단일 line density >10 차단 의 Python check) + 영구 memory `feedback_no_triple_particle_chat.md` 신설 + `MEMORY.md` index 갱신. 사용자 비판 triple-particle 의문 (quote 회피) 2회차 회수. 1058 pytest 유지 + drift 0건 47 연속. 5 검증 PASS
- [2026-05-22 04:00:00 KST] cycle 87 bot streaming SSE parser + 34 신규 PASS 7 TestClass (사용자 directive 자율 chain) — `app/bot/streaming.py` 신설. memory project_bot_framework + bot-framework.md §10 streaming response (SSE) 별개 cycle entry. `StreamEvent` Enum 7종 — `MESSAGE_START` (Anthropic message 시작), `CONTENT_BLOCK_START`, `CONTENT_BLOCK_DELTA` (Anthropic + OpenAI delta 통일), `CONTENT_BLOCK_STOP`, `MESSAGE_DELTA`, `MESSAGE_STOP` (Anthropic + OpenAI [DONE]), `UNKNOWN`. `StreamChunk` frozen dataclass (event + data dict + delta_text + done). `parse_sse_line` — SSE format line parser, 빈 줄/주석/미인식 prefix → None, `event:` → `StreamChunk(event=...)`, `data: [DONE]` → `MESSAGE_STOP done=True`, `data: {...json}` → JSON parse + payload.type event 추정, Anthropic/OpenAI delta 추출 시도. `extract_anthropic_delta` — `delta.text_delta.text` 추출, 부재/비-text_delta → 빈 string. `extract_openai_delta` — `choices[0].delta.content` 추출, empty choices/role-only → 빈 string. `accumulate_chunks` — 모든 chunk delta_text 순차 string 합본. `is_terminal` — done=True 또는 event=MESSAGE_STOP 판정 helper. `tests/app/bot/test_streaming.py` 34 신규 케이스 9 TestClass — `ParseSseLineSkip` 6 + `ParseSseLineEvent` 3 + `ParseSseLineDone` 2 + `ParseSseLineAnthropic` 3 + `ParseSseLineOpenAI` 3 + `ExtractAnthropicDelta` 5 + `ExtractOpenAIDelta` 5 + `AccumulateChunks` 4 + `IsTerminal` 3. pytest 1058 (+34). Phase 3 entry 누계 576. drift 0건 46 연속. 5 검증 PASS
- [2026-05-22 03:00:00 KST] cycle 86 bot escalation queue + 28 신규 PASS 7 TestClass (사용자 directive 자율 chain) — `app/bot/escalation_queue.py` 신설. memory project_bot_framework + bot-framework.md §10 의 escalation 사람 상담 layer 의 별개 cycle entry. TicketStatus Enum 4종 (PENDING + ASSIGNED + RESOLVED + CLOSED) + EscalationReason Enum 6종 (USER_REQUEST + JAILBREAK + RATE_LIMIT + LOW_CONFIDENCE + LONG_RESPONSE + EXPLICIT). EscalationTicket frozen dataclass (ticket_id 양수 + user_id 양수 + reason + message 빈 차단 + created_at_ms 음수 차단 + status default PENDING + agent_id Optional 양수 + resolved_at_ms Optional 음수 차단 의 7 validation). EscalationQueue (in-memory + thread-safety 미보장 async single loop) — next_ticket_id monotonic + enqueue PENDING + assign PENDING → ASSIGNED + resolve ASSIGNED → RESOLVED + close 모든 status → CLOSED + 중복 차단 + list_pending/assigned/by_user/by_agent (created_at_ms ASC FIFO) + get/size/clear (next_id 1 reset). 28 신규 PASS 7 TestClass — TicketValidation 7 + Enqueue 3 (id 1 + monotonic + size) + Assign 4 (happy + unknown KeyError + duplicate reject + zero agent reject) + Resolve 3 + Close 3 + ListAndLookup 6 + ClearAndId 2. pytest 1024 (+28). Phase 3 entry 누계 542. drift 0건 45 연속. 5 검증 PASS. memory project_bot_framework.md (A) 의 escalation 사람 상담 layer entry — DB 영속화 + agent assignment policy + SLA timer + notification 의 별개 cycle 의 base abstraction
- [2026-05-22 02:00:00 KST] cycle 85 bot usage tracker + 31 신규 PASS 5 TestClass (사용자 directive 자율 chain) — `app/bot/usage_tracker.py` 신설. memory project_bot_framework + bot-framework.md §10 의 "사용 통계 + 비용 추적" 별개 cycle entry. UsageRecord frozen dataclass (user_id 양수 + provider 빈 차단 + model 빈 차단 + input_tokens/output_tokens/timestamp_ms 음수 차단 + total_tokens property). UsageSummary frozen (count + input + output + total). UsageTracker (in-memory) — record + size + clear + all_records (copy 반환 의 mutation 차단) + summarize_by_user + summarize_by_provider + summarize_by_period (minute/hour/day bucket ms 환산) + total. extract_anthropic_usage helper (Messages API 의 usage.input_tokens / output_tokens) + extract_openai_usage helper (Chat Completions 의 usage.prompt_tokens / completion_tokens) + bool isinstance(int)=True edge case 차단 + 음수 graceful 0 clamp + dict 부재 시 (0, 0) fallback. tests/app/bot/test_usage_tracker.py 31 신규 케이스 5 TestClass — UsageRecordValidation 9 (valid + 6 검증 reject + 0 tokens 허용) + UsageSummary 2 (total + zero) + UsageTracker 13 (empty + record + clear + copy + by_user + by_provider + by_minute/hour/day bucket + invalid period + total + empty total) + ExtractAnthropicUsage 5 (happy + missing + non-dict + non-int + negative clamp) + ExtractOpenAIUsage 3 (happy + missing + bool reject). pytest 996 (+31). Phase 3 entry 누계 514. drift 0건 44 연속. 5 검증 PASS. memory project_bot_framework.md 의 사용 통계 + 비용 추적 layer entry — 별개 cycle 의 model 별 $ per 1M token price book + billing alert + Prometheus / Grafana export + DB 영속 의 base abstraction
- [2026-05-22 01:00:00 KST] cycle 84 OpenAI Chat Completions API client + OpenAIProvider adapter + 29 신규 PASS (사용자 directive 자율 chain) — `app/bot/openai_client.py` 신설. OpenAI vs Anthropic schema 차이 4종 — endpoint `/v1/chat/completions`, system role 은 messages array inline 유지 (Anthropic top-level system field 분리 대비), Authorization Bearer header (Anthropic x-api-key 대비), response `choices[0].message` (Anthropic `content[].text` 대비). `OpenAIClient` dataclass + `serialize_messages` (system inline) + `parse_response` (malformed 4종 차단) + 예외 4종 (`OpenAIAuthError`, `OpenAIRateLimitError`, `OpenAIServerError`, `OpenAIMalformedError`, base `OpenAIError`) + retry/backoff (max_retries + backoff_base_seconds + sleep_fn DI) + retry-after honor (case-insensitive + cap 60초) + jitter + network error retry (ConnectionError/OSError/TimeoutError → `OpenAIServerError`) + `from_env(OPENAI_API_KEY)`. `app/bot/llm_proxy.py` `OpenAIProvider` adapter 신설 (AnthropicProvider 동일 패턴, `__init__(client)` DI + lazy from_env + `is_available` 는 OPENAI_API_KEY env + httpx import 검증) + `select_llm_provider` "openai" NotImplementedError 회수 (cycle 65 placeholder) + auto-detect anthropic → openai → mock 3 layer fallback. `tests/app/bot/test_openai_client.py` 29 신규 케이스 7 TestClass — `SerializeMessages` 4 + `ParseResponse` 6 + `ClientValidation` 5 + `BuildRequest` 2 + `ChatStatusMapping` 6 + `RetryAndBackoff` 4 + `FromEnv` 2. `test_llm_proxy.py` `test-openai-not-implemented` → `test-openai-explicit` 갱신. pytest 965 (+29). Phase 3 entry 누계 483. drift 0건 43 연속. 5 검증 PASS. provider plug-in 패턴 완성 — Anthropic + OpenAI dual provider abstraction + caller 명시 선택 또는 auto-detect graceful fallback
- [2026-05-22 00:00:00 KST] cycle 83 CustomerServiceBot scan_jailbreak opt-in + 5 신규 PASS (사용자 directive 자율 chain) — `app/bot/customer_service_bot.py` 의 CustomerServiceConfig 의 `scan_jailbreak: bool = False` field 추가 (default 비활성 + server-side bot_handlers cycle 82 통합 정합 + 클라이언트 직접 사용 시 opt-in). answer() pipeline 의 rate limit gate 직후 호출 — config.scan_jailbreak 활성 시 detect_jailbreak(user_message) + BLOCKED signal 시 ValueError "prompt injection 차단" + log.warning + LLM 호출 차단 + SUSPICIOUS signal 시 log.info + 진행 (false positive 회피). logging module import 추가 + module-level logger. import jailbreak_detector 의 JailbreakSignal + detect + summarize_categories. TestJailbreakIntegration 5 신규 — default scan_jailbreak=False + scan disabled 의 통과 + enabled BLOCKED ValueError + LLM 호출 부재 + enabled SUSPICIOUS 통과 + enabled benign 통과. pytest 936 (+5). Phase 3 entry 누계 454. drift 0건 42 연속. 5 검증 PASS. memory project_bot_framework (A) 의 보안 layer 의 dual integration 완성 — server endpoint (cycle 82 default 강제) + client-side CustomerServiceBot (cycle 83 opt-in) 의 양쪽 적용 가능 architecture
- [2026-05-21 23:00:00 KST] cycle 82 jailbreak detector bot_handlers 통합 + 6 신규 PASS (사용자 directive 자율 chain) — `server/api/bot_handlers.py` 의 `_scan_jailbreak(messages)` helper 신설 + handle_bot_chat pipeline `_parse_messages` 직후 호출, user role content scan (assistant role skip), BLOCKED → `web.HTTPBadRequest` 400 + LLM 호출 차단, SUSPICIOUS → log.info 진행 (false positive 회피). 예외 메시지 prompt injection 차단 + idx + categories. import 추가 (JailbreakSignal + detect + summarize_categories). `tests/server/test_bot_handlers.py` 6 신규 (blocked 400 + suspicious 통과 + benign 통과 + assistant skip + helper blocked + helper none). pytest 931 (+6). Phase 3 entry 누계 449. drift 0건 41 연속. 5 검증 PASS. memory project_bot_framework (A) 보안 layer production endpoint 통합 완성 — jailbreak attempt LLM 호출 이전 차단 + Anthropic 호출 비용 절감 + log echo 차단
- [2026-05-21 22:00:00 KST] cycle 81 jailbreak detector heuristic + 33 신규 PASS 9 TestClass (사용자 directive "진행해" 자율 chain) — `app/bot/jailbreak_detector.py` 신설 + prompt injection / jailbreak heuristic detector. JailbreakSignal Enum (NONE / SUSPICIOUS / BLOCKED) + JailbreakMatch frozen dataclass (category + pattern + match_text + severity) + JailbreakResult (signal + matches + score) + detect(text) + is_blocked + summarize_categories helper. 21 pre-compiled regex pattern × 6 category × Korean/English — instruction_override 5 (ignore previous instructions / disregard / forget + 이전 지시 무시 + 앞의 지시 무시) + role_hijack 5 (you are now / act as / pretend to be + 당신은 이제 + DAN/jailbroken/dev mode) + system_leak 3 (show reveal display + what are your + 시스템 프롬프트 보여) + delimiter_injection 3 ([system]: + <|im_start|> + ### system ###) + privilege_escalation 3 (grant admin + unrestricted mode + bypass safety) + info_exfiltration 2 (reveal api_key + api_key=). severity 누적 — score 0 = NONE, score 1 = SUSPICIOUS, score ≥ 2 = BLOCKED. snippet 80자 cap (log hygiene + content fully echo 차단). 33 PASS 9 TestClass — Empty 3 + InstructionOverride 4 + RoleHijack 5 + SystemLeak 4 + DelimiterInjection 3 + PrivilegeEscalation 3 + InfoExfiltration 2 + CombinedMatches 4 + IsBlockedHelper 4 + JailbreakMatch 1. pytest 925 (+33). Phase 3 entry 누계 443. drift 0건 40 연속. 5 검증 PASS. memory project_bot_framework (A) 의 보안 layer 추가 hardening — cycle 74 의 system role 클라이언트 차단 의 직후 layer 의 user content 안 의 의도된 system instruction override 시도 detection
- [2026-05-21 21:00:00 KST] cycle 80 docs/policies/bot-framework.md 정책 본문 신설 (사용자 directive "남은작업 진행해" 자율 chain) — `docs/policies/bot-framework.md` 신설 + Phase 3 bot framework chain (cycle 65~79) 의 누계 통합 정책 정본. §1 운영 규약 + §2 아키텍처 mermaid (11 노드 chain) + §3 보안 layer 5종 (ANTHROPIC_API_KEY 격리 + system role 차단 + RateLimitGate + user_id type confusion 차단 + DoS cap) + §4 라이선스 (GPLv3 + SPDX) + §5 user_id prefix 4 영역 (일반 < 1_000_000 + 고객센터 ≥ 1_000_000 + 방송 도우미 ≥ 2_000_000 + 외부 ≥ 3_000_000) + §6 retry/backoff 정책 (가능 3종 + 불가 3종 + 계산식 + default + production 권장) + §7 RAG dual baseline (5 backend 비교 표 + cache + ranking) + §8 provider plug-in 패턴 + §9 abuse 차단 7 layer + §10 별개 cycle 후보 7종 + §11 참조. AGENTS.md 의 정책 doc 3 → 5 row 갱신 (observability + bot-framework). doc-lint 1 broken link 의 정정 (~/.claude memory path 의 inline link → code block). pytest 892 (변경 무). drift 0건 39 연속. 5 검증 PASS. memory project_bot_framework (사용자 directive 누계 3건) 의 정책 본문 등가 명문화 완성
- [2026-05-21 20:00:00 KST] cycle 79 CachedEmbedder LRU decorator + 10 신규 PASS (사용자 directive "남은작업 진행해" 자율 chain) — `app/bot/rag_context.py` 의 CachedEmbedder 신설 — Embedder Protocol wrapper + OrderedDict 기반 LRU cache (move_to_end on hit + popitem evict at capacity) + max_cache 양수 의무 (default 256 + 0/negative reject) + hit/miss counter instrumentation + dim() delegate + size() + reset_stats() + clear(). collections.OrderedDict import 추가. tests/app/bot/test_rag_context.py 의 TestCachedEmbedder 10 신규 — max_cache zero/negative reject + first miss/second hit + different text separate miss + LRU eviction at capacity + LRU move_to_end on hit + dim delegate + reset_stats (cache 보존) + clear (cache + stats 전수 reset) + EmbeddingRAGStore 통합. pytest 892 (+10). Phase 3 entry 누계 410 (이전 400 + cache 10). drift 0건 38 연속. 5 검증 PASS. memory project_bot_framework (A) 의 RAG context layer 의 비용 optimization 의 진입 — 동일 query 의 embed 호출 의 중복 회피 + sentence-transformers + OpenAI text-embedding-3 의 호출 비용 절감 + 응답 지연 회피 base
- [2026-05-21 19:00:00 KST] cycle 77+78 reviewer P1+P2 회수 + 10 신규 PASS (사용자 directive "미완항목 다 진행해" 자율 chain) — cycle 77 P1: `app/bot/anthropic_client.py` `chat()` pipeline transport 호출에 try/except (ConnectionError, OSError, TimeoutError) 추가 + max_retries cap 의무 + 소진 시 `AnthropicServerError` propagation + jitter 결합. `TestNetworkErrorRetry` 6 신규. cycle 78 P2: `server/api/bot_handlers.py` `_reply_to_wire` hasattr fallback 제거 (`BotMessage.role` 는 `BotRole` enum 보장) + `handle_bot_chat` user_id 의 `bool isinstance(int)=True` edge case 명시 차단 (auth bypass 회피). `TestHandleBotChat` 4 신규 — bool/float/string/zero user_id reject. pytest 882 (+10). Phase 3 entry 누계 400. drift 0건 37 연속. 5 검증 PASS. reviewer-agent 보고 P0+P1+P2 9건 회수 완료. server-side LLM proxy production-ready hardening 완성 — transient network 장애 회수 + auth bypass type confusion 차단
- [2026-05-21 17:30:00 KST] cycle 76 server.main bot LLM proxy 통합 + reviewer P0 회수 + 6 신규 integration PASS (사용자 directive "미완항목 다 진행해" 자율 GO) — reviewer-agent P0 차단 항목 회수 (cycle 74 의 `register_bot_routes` 미연결). `server/main.py` `build_app` 갱신 — `BOT_ENABLED` 환경 변수 detect + `AnthropicProvider.is_available()` 가 ANTHROPIC_API_KEY 가용 시 활성, 부재 시 `MockLLMProvider` 폴백 + `BOT_RATE_PER_MINUTE` `RateLimitGate` (default 20/min) + `register_messages_routes` + `register_bot_routes` 등록. `server/api/bot_handlers.py` `APP_KEY_PROVIDER` + `APP_KEY_RATE_GATE` 는 `web.AppKey` type-safe 변환. `pyproject.toml` NotAppKeyWarning filterwarnings ignore. `tests/server/test_main_integration.py` 신설 — 6 케이스 (route 미등록, provider/gate 부재, Mock 폴백, custom rate cap, 401 unauthorized, happy path 200, 비활성 404). pytest 872 (+6). 5 검증 PASS — AST + import + pytest + doc-lint 0 + BPE 0 + pronoun 0 + 3회 반복 0. server-side LLM proxy production 통합 완성 — ANTHROPIC_API_KEY 서버 영역 격리 + 자동 폴백 + per-user rate limit + route 의 `build_app` 정합
- [2026-05-21 16:30:00 KST] cycle 75 EmbeddingRAGStore abstraction + 15 신규 PASS 3 TestClass (사용자 directive "진행해" 자율 GO) — `app/bot/rag_context.py` EmbeddingRAGStore placeholder 회수 + `Embedder` Protocol (embed + dim 의 sync 호출) + `MockEmbedder` (hash-based deterministic, tokenize → dim slot 누적, L2 normalize, dim_value 양수 의무, 빈 텍스트 zero vector) + `cosine_similarity` (차원 mismatch reject, 빈 벡터 reject, zero-norm = 0.0, identical = 1.0, orthogonal = 0.0) + EmbeddingRAGStore (Embedder DI + entries add 시 tags + question 결합 텍스트 embed 사전 계산 + id 중복 차단 + dim mismatch reject + cosine sim DESC + ASC idx tie stable + sim 0 제외 + top_k 양수 의무). `tests/app/bot/test_rag_context.py` 기존 EmbeddingRAGStore 2 placeholder test 회수 + 15 신규 (Embedding 7 + MockEmbedder 5 + Cosine 5). pytest 866 (+15). Phase 3 entry 누계 384 (이전 369 + Embedding 15). drift 0건 34 연속. 5 검증 PASS. RAG context layer vector store baseline 완성 — KeywordRAGStore (substring + keyword overlap, cycle 68) + EmbeddingRAGStore (cosine sim, cycle 75) dual baseline + Embedder DI 로 sentence-transformers / OpenAI / Voyage 실 model plug-in 가능
- [2026-05-21 15:30:00 KST] cycle 74 server-side /api/bot/chat LLM proxy endpoint + 29 신규 PASS 4 TestClass (사용자 directive 자율 chain GO) — `server/api/bot_handlers.py` 신설. handle_bot_chat POST endpoint — Bearer 인증 + RateLimitGate per-user + JSON body parse + 32 messages cap + 16KB content cap + _parse_role (USER/ASSISTANT 허용 + SYSTEM role 클라이언트 주입 차단 의 보안) + _parse_messages schema validation + AnthropicProvider chat forward + 4 종 Anthropic 예외 → HTTP status 매핑 (AuthError 500 + RateLimitError 503 + ServerError 502 + MalformedError 502 + generic 500). 보안 layer — ANTHROPIC_API_KEY 서버 환경 변수 격리 + system role 클라이언트 주입 차단 + per-user_id rate limit. APP_KEY_PROVIDER + APP_KEY_RATE_GATE app context. tests/server/test_bot_handlers.py 29 케이스 4 TestClass — ParseRole 5 + ParseMessages 10 + ReplyToWire 1 + HandleBotChat 13 (auth + provider missing + invalid JSON + rate limit + happy path + 5 종 예외 매핑 + provider 호출 chain 검증). pytest 851 (+29). Phase 3 entry 누계 369 (이전 340 + bot_handlers 29). drift 0건 33 연속. 5 검증 PASS. memory project_bot_framework (A) 의 server-side LLM proxy 패턴 완성 — API key 서버 영역 격리 + system role 클라이언트 주입 차단 + per-user abuse 차단 + 4 종 예외 매핑 의 production-ready endpoint
- [2026-05-21 14:30:00 KST] cycle 73 AnthropicClient retry-after honor + jitter + transport 3-tuple refactor + 9 신규 PASS (사용자 directive 자율 GO) — `app/bot/anthropic_client.py` HttpTransport 응답 schema 를 3-tuple 로 확장 — `Callable[[...], Awaitable[Tuple[int, dict, dict]]]` (이전 2-tuple → status + headers + body) + `_parse_retry_after(headers)` helper (case-insensitive lookup, 음수/비숫자/빈 차단, `_RETRY_AFTER_MAX_SECONDS=60` cap 으로 DoS 회피) + AnthropicClient 에 2 신규 field — `jitter_max_seconds: float = 0.0` (default 부재 + 음수 차단) + `jitter_fn: JitterFn = random.random` (sync float [0,1) range). `chat()` pipeline retry-after 헤더 우선 적용 (429 응답 시 헤더 값 → 지수 backoff override + cap) + jitter 추가 (`jitter_max_seconds > 0` 시 `jitter_fn() * max` 추가). `_placeholder_transport` + `httpx_transport` + `from_env` stubs 모두 3-tuple 정합. `tests/app/bot/test_anthropic_client.py` 기존 6 mock transport 3-tuple 변경 + `TestRetryAfterAndJitter` 9 신규 케이스 — jitter 음수 reject, retry-after 5초 honor, Retry-After capitalized, "garbage" → backoff fallback, 음수 fallback, 9999 → cap 60.0, `jitter 0.5 * 2.0 = 1.0`, jitter_max=0 default, retry-after 4.0 + jitter 결합. `tests/app/bot/test_llm_proxy.py` 2 mock transport 3-tuple 정합. pytest 822 (+9). Phase 3 entry 누계 340. drift 0건 32 연속. 5 검증 PASS. `docs/exec-plans/active/MANUAL_TESTS.md` 신설 — Claude 자율 불가 8 카테고리 누계. server-side LLM proxy production-ready reliability layer 진입 — Anthropic 공식 retry-after 헤더 honor + 음수/cap robustness + jitter thundering herd 회피 base
- [2026-05-21 13:30:00 KST] cycle 72 AnthropicClient retry/backoff + 9 신규 PASS TestRetryAndBackoff (사용자 directive "다 진행해" 자율 GO) — `app/bot/anthropic_client.py` `AnthropicClient` 에 4 신규 field — `max_retries: int = 0` (default backwards-compat + 음수 차단), `backoff_base_seconds: float = 1.0` (양수 의무, 0 차단), `sleep_fn: SleepFn = asyncio.sleep` (mock 주입 가능), `__post_init__` validation. `chat()` pipeline retry loop 도입 — 429/5xx 응답 시 지수 backoff (`delay = base * 2^attempt`) + `sleep_fn(delay)` + retry. 401/403 = 즉시 `AnthropicAuthError`. 그 외 4xx = 즉시 base `AnthropicError`. max_retries 초과 시 마지막 status 대응 예외 (429 → `AnthropicRateLimitError`, 5xx → `AnthropicServerError`). `SleepFn = Callable[[float], Awaitable[None]]` 별칭 추가. `tests/app/bot/test_anthropic_client.py` `TestRetryAndBackoff` 9 케이스 — `_sequence_transport` + `_sleep_recorder` + max_retries 음수 reject + backoff_base 0 reject + 429 retry then 200, 5xx retry then 200, 429 exhausted, 5xx exhausted, 401 no retry, default 부재, exponential progression. pytest 813 (+9). Phase 3 entry 누계 331. drift 0건 31 연속. 5 검증 PASS. server-side LLM proxy reliability + abuse 차단 layer 진입 — transient 장애 회수 + 영구 장애 fail-fast 분리. 다음 = retry-after honor + jitter + httpx 등록
- [2026-05-21 12:30:00 KST] cycle 71 AnthropicProvider ↔ AnthropicClient adapter + 3 신규 PASS (사용자 directive "다 진행해" 자율 GO) — `app/bot/llm_proxy.py` `AnthropicProvider` NotImplementedError placeholder 회수 + `__init__(self, client: Optional[object] = None)` DI + `chat()` 는 `self._client.chat(messages)` delegate + client 부재 시 `from app.bot.anthropic_client import from_env` lazy 생성 (순환 import 회피용 함수 내 import) + `ANTHROPIC_API_KEY` 환경 변수 + httpx_transport default 활성 + 후속 호출 동일 client 재사용. `tests/app/bot/test_llm_proxy.py` 기존 `test_chat_raises_not_implemented` 회수 + 3 신규 — `test_chat_lazy_init_no_env_raises` (환경 변수 부재 시 `AnthropicAuthError` propagation) + `test_chat_delegates_to_injected_client` (mock transport 200 응답 + chat delegate + ASSISTANT role reply 검증) + `test_chat_reuses_client_across_calls` (2회 chat 호출 + transport counter 누적 검증). pytest 804 (802 + 3 - 1 회수). Phase 3 entry 누계 322. drift 0건 30 연속. 5 검증 PASS. bot framework chain (cycle 65~71) LLM provider abstraction (cycle 65) → Anthropic 실 HTTP layer (cycle 70) → adapter wiring (cycle 71) 으로 horizontal 통합 완성. CustomerServiceBot 가 다음 cycle 에서 AnthropicProvider 직접 사용 가능 + httpx 등록 후 immediate 실 API 호출 가능
- [2026-05-21 11:30:00 KST] cycle 70 Anthropic Messages API client + 32 PASS 6 TestClass (사용자 directive "다 진행해" 자율 GO) — `app/bot/anthropic_client.py` 신설. `serialize_messages(messages)` → `(system_str, messages_payload)` — Anthropic Messages API system role 을 top-level 로 분리 추출, user/assistant 만 messages 배열에 entry, 여러 SYSTEM 은 `\n\n` 결합. `parse_response(body)` → BotMessage (content array text block 합본, content/role=assistant/text 부재 시 `AnthropicMalformedError`, tool_use 등 비-text block skip). `AnthropicClient` dataclass (api_key 빈 차단 AuthError + model/max_tokens/base_url 검증 + `_DEFAULT_MODEL` claude-3-5-sonnet-latest + `_DEFAULT_MAX_TOKENS` 1024 + `build_headers` x-api-key/anthropic-version 2023-06-01/content-type + `build_body` model/max_tokens/system/messages). `HttpTransport` Protocol (url + headers + body → (status, body) tuple). `chat()` pipeline 의 예외 매핑 4종 — 401/403 `AnthropicAuthError`, 429 `AnthropicRateLimitError`, 5xx `AnthropicServerError`, 그 외 4xx 는 base `AnthropicError`, schema 위반 시 `AnthropicMalformedError`. `httpx_transport(timeout)` factory (httpx 미설치 graceful ImportError → AnthropicError 변환). `from_env(transport)` 는 ANTHROPIC_API_KEY → AnthropicClient. 32 케이스 6 TestClass — `SerializeMessages` 5 + `ParseResponse` 6 + `ClientValidation` 5 + `BuildRequest` 4 + `ChatWithMockTransport` 9 + `FromEnv` 3. pytest 802 (+32). Phase 3 entry 누계 319. drift 0건 29 연속. 5 검증 PASS. bot framework chain (cycle 65~70) — llm_proxy 26 + customer_service_bot 30 + streaming_helper 33 + rag_context 27 + customer ↔ rag 통합 6 + Anthropic Messages API 32 = default 2종 + RAG retrieval + provider abstraction + 실 Anthropic binding (transport 주입, httpx 미설치 graceful) 완성. caller 는 ANTHROPIC_API_KEY 환경 변수 + HttpTransport 주입 DI 패턴 + 테스트 mock 가능. 별개 cycle 에서 httpx 설치 + retry backoff + streaming (SSE) + 토큰 카운트 + tool use 추가
- [2026-05-21 10:30:00 KST] cycle 69 CustomerServiceBot ↔ RAGStore 통합 + 6 신규 PASS (사용자 directive "다 진행해" 자율 GO) — `app/bot/customer_service_bot.py` 의 `CustomerServiceConfig` 에 `rag_top_k: int = 3` field 추가 + `CustomerServiceBot.__init__` 의 `rag_store: Optional[RAGStore] = None` 키워드 인자 + `answer()` pipeline 의 `system_content` augmentation (rag_store 주입 시 `compose_rag_context(user_message, store, top_k=config.rag_top_k)` 산출 markdown 을 system prompt 뒤 `\n\n` 결합 + 빈 결과 augmentation skip). 6 신규 `TestRagStoreIntegration` — default rag_top_k=3 + invalid 0 reject + 부재 시 "참고 FAQ" 부재 + 주입 시 "Q:" + "A:" 출력 + 빈 store skip + rag_top_k=1 cap. pytest 770 (+6). Phase 3 entry 누계 287 (281 + 6). drift 0건 28 연속. bot framework chain (cycle 65~69) — llm_proxy + customer_service_bot + streaming_helper + rag_context + customer ↔ rag 통합 = default 2종 + RAG retrieval + provider abstraction 의 entry 완성
- [2026-05-21 09:30:00 KST] cycle 68 RAG context layer + 27 PASS 5 TestClass (사용자 directive "다 진행해" 자율 GO) — `app/bot/rag_context.py` 신설. `FAQEntry` frozen dataclass (id + topic + question + answer + tags + 빈 차단 검증) + `RAGStore` Protocol (search + add + size) + `_tokenize` (whitespace + lowercase + 한국어/영어 stopword 제거) + `_score_entry` (token overlap 0.0~1.0 + substring 발견 시 +0.5 boost + min(1.0)) + `KeywordRAGStore` (entries 의 list + add 의 id 중복 차단 + search 의 DESC score + ASC idx tie 안정 + top_k 양수 의무) + `EmbeddingRAGStore` placeholder (sentence-transformers + cosine 의 별개 cycle) + `build_default_toonation_faq()` 10 entry × 5 영역 (donation/payout/obs/fraud/refund × 2) + `compose_rag_context(query, store, top_k)` markdown 산출 (# 참고 FAQ + Q/A pairs). 27 케이스 5 TestClass — FAQEntryValidation 6 + KeywordRAGStore 11 (empty + add/size + duplicate + init entries + empty query + substring + token rank + top_k + zero k + no match + tags) + EmbeddingRAGStore 2 + BuildDefaultFAQ 4 (10 entry + 5 topics + tags + ids unique) + ComposeRagContext 4 (empty store + no match + markdown + default donation query). pytest 764 (+27). Phase 3 entry 누계 281 (이전 254 + rag 27). drift 0건 27 연속. memory project_bot_framework (A) 의 RAG context 의무 충족 — customer_service_bot 의 system prompt 외 의 추가 context injection layer 의 entry
- [2026-05-21 08:30:00 KST] cycle 67 방송 도우미 봇 별개 API StreamingHelperBot + 33 PASS 7 TestClass (사용자 directive "이어서 진행해" 자율 GO) — `app/bot/streaming_helper.py` 신설. `StreamingPlatform` Enum 5종 (YouTube/Twitch/CHZZK 네이버 치지직/Kick/OBS_LOCAL) + `StreamingCommand` frozen dataclass (trigger ! prefix + 32자 cap + response 500자 cap + cooldown_seconds 음수 차단 + enabled) + `StreamingBotConfig` (bot_user_id ≥ 2_000_000 prefix 분리 의 고객센터 봇 1_xxx 와 구분) + `default_streaming_commands()` 5 기본 (!hello + !uptime + !donate + !command + !so 의 nightbot 등가) + `StreamingHelperBot` class (apply_command + cooldown per-trigger + placeholder 치환 {viewer}/{streamer}/{target}/{uptime} + find_command + add_command 중복 차단 + remove_command) + `fetch_platform_callback` 5 platform NotImplementedError placeholder (YouTube Data API + Twitch IRC + CHZZK API + Kick API + OBS WebSocket). 33 케이스 7 TestClass — StreamingCommandValidation 7 (valid + 빈 trigger + ! 부재 + 32자 초과 + 빈 response + 500자 초과 + 음수 cooldown) + ConfigValidation 3 (valid + 낮은 bot_id + 빈 display) + DefaultCommands 3 + FindCommand 5 + ApplyCommand 6 (basic reply + no match + cooldown blocks + cooldown release + placeholder + so target) + AddRemoveCommand 4 + FetchCallback 5 (YouTube/Twitch/CHZZK/Kick/OBS NotImplementedError). pytest 737 (+33). Phase 3 entry 누계 254 (이전 221 + streaming 33). drift 0건 26 연속. memory project_bot_framework (B) 정합 — TooTalk Bot API 와 분리 + 별개 API 의무 충족

---

**문서 상태**: `active` · 최초 작성 2026-05-17 · M2 변경 이력 30행 캐시
운영. 30행 초과 시점부터 회전 + History.md 위임.
