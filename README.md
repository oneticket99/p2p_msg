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

- [2026-05-22 18:00:00 KST] cycle 114~115 middleware chain integration smoke + user_activity repository skeleton + 20 신규 PASS (사용자 directive 다음작업 진행해 자율 chain) — Phase 4 Item 3 마무리 + DB audit migration 0003 actual SQL wiring. cycle 114 — tests/server/test_middleware_chain_integration.py 4 신규 2 TestClass — TestRequestIDEndToEnd 3 (real aiohttp TestServer wire-level: incoming header propagated to handler + missing generates uuid4 + 3 sequential 의 distinct request_id) + TestMiddlewareChainOrder 1 (request_id 의 handler + activity_middleware 양쪽 available). cycle 115 — server/db/repositories/user_activity.py 신설 — DDL 0003 의 user_activity_log + user_sessions repository. ActivityAction Enum 23 종 (signup + signup_otp_verify + login + logout + password_reset_request + complete + room_create/join/leave/close + message_send + file_send/receive + device_register/revoke + bot_chat + bot_escalate + remote_request/grant/revoke + profile_update + email_change + account_delete). SessionEndReason Enum 5 종 (logout + idle_timeout + token_revoke + force_disconnect + server_restart). ActivityLogRow + SessionRow frozen dataclass. SQL 5 종 — INSERT user_activity_log + INSERT user_sessions + UPDATE users.last_activity_at + UPDATE users.last_login_at + UPDATE user_sessions.last_active_at + close_session (TIMESTAMPDIFF SECOND duration_seconds 계산). 4 repository 함수 — log_activity (pool DI + user_id 양수 + 22 ENUM + metadata JSON serialize + lastrowid 반환 + 부수 update users.last_activity_at + commit) + create_session (token_hash 64자 SHA-256 + ip_address 의무 + 부수 last_login_at/last_login_ip 갱신) + update_session_last_active (활성 세션 만 + disconnected_at IS NULL guard + rowcount 반환) + close_session (TIMESTAMPDIFF duration + end_reason). tests/server/db/test_user_activity.py 16 신규 7 TestClass — ActivityAction 1 (23 ENUM defined) + SessionEndReason 1 (5 ENUM) + LogActivityValidation 3 (none pool + zero user_id + negative reject) + LogActivityExecution 3 (minimal INSERT + metadata JSON serialize + no metadata None) + CreateSessionValidation 3 (none pool + 64자 token + empty IP) + CreateSessionExecution 1 (INSERT + last_login update + ip_address parameter chain) + UpdateSessionLastActive 2 (active update + empty token reject) + CloseSession 2 (logout end_reason + idle_timeout). 전체 pytest = 1215 passed (1195 + 20 신규). drift 0건 64 연속. 5 검증 PASS. Phase 4 Item 3 본문 완성. 다음 cycle 116~117 Item 4 logging — KST formatter + JSON structured + sensitive redact + request_id contextvar 의 JSON field auto-injection + 7 logger 분류
- [2026-05-22 17:30:00 KST] cycle 113 X-Request-ID propagation middleware + 8 신규 PASS (사용자 directive 진행해 자율 chain) — Phase 4 Item 3 server-side wiring + Item 4 logging prerequisite. server/middleware/request_id.py 신설 — contextvar current_request_id 의 async task 격리 + get_request_id() helper + nginx X-Request-ID header propagation (가용 시 본 값 / 부재 또는 whitespace 시 uuid4 hex 32자 fallback) + request scope attribute 등록 + response header echo back (클라이언트 trace 가능) + finally token reset (context cleanup 의무). server/middleware package init 의 export 추가. server/main.py middleware chain `[request_id_middleware, auth_middleware, activity_middleware]` 의 3 layer (request_id 최상단 — 모든 request trace 의무, log correlation base). tests/server/test_middleware_request_id.py 8 신규 4 TestClass — TestRequestIDGeneration 3 (incoming header used + missing generates uuid4 + whitespace treated as missing) + TestResponseHeaderEcho 2 (echo back + generated id echoed) + TestContextVarIsolation 2 (concurrent tasks asyncio.gather 격리 + after middleware cleared finally) + TestGetRequestIDOutsideMiddleware 1 (default None). FakeRequest helper class — aiohttp Request 의 dict-like + headers.get 의 minimal. 전체 pytest = 1195 passed (1187 + 8 신규). drift 0건 63 연속. 5 검증 PASS. Item 4 logging 의 JSON formatter 의 request_id field auto-injection prerequisite 완성. 다음 cycle 114~115 = WebSocket upgrade smoke 검증 + manual TLS smoke. cycle 116~117 Item 4 KST formatter + JSON structured + sensitive redact
- [2026-05-22 17:00:00 KST] cycle 112 Phase 4 Item 3 nginx 본문 — certbot 통합 + nginx config 35 신규 PASS + Caddy 대안 doc (사용자 directive 다음작업 진행해 자율 chain) — Phase 4 Item 3 본문 진입. (1) deploy/scripts/certbot_init.sh 신설 — Let's Encrypt 초기 인증서 발급 (webroot challenge + RSA 2048 + ACME_EMAIL + TLS_PRIMARY_DOMAIN env + STAGING flag 의 rate limit 회피 + 의무 -d domain + mail.domain dual SAN + bash strict mode set -euo pipefail). (2) deploy/scripts/certbot_renew.sh 신설 — cron 등록 의무 (매일 03:00 KST) + 60일 cutoff 자동 갱신 + 갱신 발생 시 nginx -t 검증 + nginx -s reload (live config swap) + nginx 미가동 시 graceful skip. (3) deploy/docker-compose.yml — certbot service entry 추가 (profile certbot 명시 활성 의 one-shot + certbot/certbot:latest image + letsencrypt + certbot_webroot volume mount) + nginx volume 의 certbot_webroot:ro 추가 + named volume certbot_webroot 추가. docker compose config --quiet 검증 PASS. (4) tests/deploy/test_nginx_config.py 35 신규 7 TestClass — TestNginxBaseConfig 5 (file exists + worker_processes auto + include conf.d + server_tokens off + gzip on) + TestNginxRateLimitZones 5 (auth + api + bot + upload + ws_conn 5 zone 정합) + TestNginxRealIP 3 (set_real_ip_from 172.16/12 + real_ip_header XFF + real_ip_recursive on) + TestNginxVirtualHostHTTPS 6 (443 ssl http2 + 80 redirect 301 + ACME challenge webroot + TLSv1.2 1.3 only + Let's Encrypt fullchain/privkey + OCSP stapling on) + TestNginxSecurityHeaders 5 (HSTS + X-Frame SAMEORIGIN + X-Content-Type nosniff + Referrer-Policy + CSP default-src self) + TestNginxProxyHeaders 4 (X-Request-ID + X-Real-IP + X-Forwarded-For proxy_add + X-Forwarded-Proto) + TestNginxLocations 5 (auth + bot streaming buffering off + file upload 100M + WebSocket Upgrade chain + 3600s timeout + healthz no log) + TestNginxUpstreamHosts 2 (web:8080 + ws:8765 docker service name). (5) deploy/nginx/CADDY_ALTERNATIVE.md 신설 — nginx 1.27 vs Caddy 2 의 10 기준 비교 표 + Phase 4 nginx 유지 권장 근거 5건 + Phase 5+ 전환 조건 + Caddyfile sample (참고용). 전체 pytest = 1187 passed (1152 + 35 신규). drift 0건 62 연속. 5 검증 PASS. 다음 cycle 113~115 = nginx server-side wiring (X-Forwarded-For middleware 의 activity_middleware 정합) + WebSocket upgrade smoke + manual TLS smoke. cycle 116~117 Item 4 logging
- [2026-05-22 16:30:00 KST] cycle 111 aiohttp activity middleware + ActivityTracker 1분 throttle + 20 신규 PASS (사용자 directive 다은작업 진행해 자율 chain) — Phase 4 Item 2 완성 + DB audit migration 0003 actual code wiring base. server/middleware/ sub-package 신설 (activity.py + package init). ActivityTracker dataclass — in-memory Dict[user_id, last_seen_seconds] + throttle_seconds default 60 + should_update (user_id + now_seconds 기준 throttle 안 False / 외 True + 양수 user_id 의무) + size + prune_stale (cutoff 이전 evict, 메모리 누수 회피). extract_client_ip helper — X-Forwarded-For 의 첫 토큰 (nginx 정합) + 공백 strip + 부재 시 request.remote fallback. activity_middleware (auth_middleware 직후 chain) — request["user_id"] 의 양수 int 검증 + tracker 가용 시 should_update + IP + UA + path log. APP_KEY_ACTIVITY web.AppKey type-safe. server/main.py build_app — middleware chain `[auth_middleware, activity_middleware]` 변경 + app[APP_KEY_ACTIVITY] = ActivityTracker(throttle_seconds=60) 등록. tests/server/test_middleware_activity.py 20 신규 5 TestClass — ActivityTrackerValidation 4 (default 60 + custom + zero reject + negative reject) + ActivityTrackerThrottle 6 (first call updates + within throttle skip + after throttle updates + distinct users independent + zero user_id skipped + negative skipped) + ActivityTrackerPrune 2 (stale evict + empty no removal) + ExtractClientIP 5 (XFF single + multi-proxy first + empty fallback remote + both empty + spaces stripped) + ActivityMiddleware 3 (no user_id skip + valid updates once + no tracker graceful). 전체 pytest = 1152 passed (1132 + 20 신규). drift 0건 61 연속. 5 검증 PASS. DB audit migration 0003 의 wiring base 완성 — 별개 cycle 의 actual SQL UPDATE 의 wiring 의 prerequisite. 다음 cycle 112~115 = Phase 4 Item 3 nginx 본문 + cycle 116~117 Item 4 logging
- [2026-05-22 16:00:00 KST] cycle 110 server/main.py Config 통합 refactor + test 의 env pollution 회수 (사용자 directive 다음작업 진행해 자율 chain) — Phase 4 Item 2 마무리. server/main.py 의 build_app refactor — Optional Config 인자 추가 (caller 명시 주입 가능 + None 시 Config.from_env() lazy single entry) + app["config"] 의 의존성 주입 등록 + bot 활성 분기 `os.environ.get(ENV_BOT_ENABLED)` → `cfg.bot.enabled` 변경 + `_read_int_env(ENV_BOT_RATE_PER_MINUTE)` → `cfg.bot.rate_per_minute` 변경. `from .config import Config` import 추가. `from typing import Final, Optional`. tests/server/test_config.py 의 test_load_env_files_picks_specific_env 의 cross-test pollution 회수 — load_dotenv 의 monkeypatch 우회 의 직접 os.environ 변경 의 finally cleanup 도입 (ENV + DB_HOST snapshot + 복원). 전체 pytest = 1132 passed (변경 무 — refactor + test cleanup). drift 0건 60 연속. 5 검증 PASS. 다음 cycle 111 = aiohttp middleware last_active_at 갱신 1분 throttle (DB audit migration 0003 actual code wiring). cycle 112~115 Item 3 본문 + cycle 116~117 Item 4 logging
- [2026-05-22 15:30:00 KST] cycle 109 Phase 4 Item 2 — server/config.py Config 통합 클래스 + 20 신규 PASS (사용자 directive 작업 재개해 자율 chain) — Phase 4 Item 2 진입. server/config.py 신설 — `_load_order = (.env, .env.<ENV>)` 의 override chain + ENV 식별 (local/staging/production) + 7 영역 @dataclass(frozen=True) (DBConfig + SMTPConfig + SignalingConfig + BotConfig + FCMConfig + TLSConfig + 통합 Config) + 각 영역 from_env classmethod + load_env_files factory + production validate (db.password + bot.api_key + tls.acme_email + tls.primary_domain 의무 키 누락 시 ConfigError raise). parse helper 3종 — _str_env (strip) + _int_env (ValueError fallback + warn log) + _bool_env (1/true/yes/on truthy + 0/false/no/off falsy). tests/server/test_config.py 20 신규 7 TestClass — TestParseHelpers 4 (default ENV local + int invalid fallback + bool 5 truthy + bool 5 falsy) + TestDBConfig 2 (defaults + from_env override) + TestSMTPConfig 2 (defaults + DKIM_SELECTOR override) + TestSignalingConfig 1 (defaults) + TestBotConfig 2 (disabled default + enabled with keys) + TestFCMConfig 1 (defaults) + TestTLSConfig 1 + TestConfigFromEnv 2 (local defaults + load chain specific ENV pick) + TestConfigValidate 5 (local passes + production missing DB_PASSWORD raise + missing TLS raise + bot enabled missing API_KEY raise + all set passes). 전체 pytest = 1132 passed (1112 + 20 신규). drift 0건 59 연속. 5 검증 PASS. 다음 cycle 110 = server/main.py 의 Config 통합 (os.environ 분산 access → Config.from_env single entry). cycle 111 = aiohttp middleware last_active_at 갱신 + cycle 112~115 Item 3 본문 + cycle 116~117 Item 4 logging
- [2026-05-22 15:00:00 KST] cycle 105~107 Phase 4 nginx config + .env.example 본문 + docker compose syntax verify (사용자 directive 작업 재개해 자율 chain) — cycle 105 nginx — deploy/nginx/nginx.conf 신설 (worker_processes auto + 4096 connections + JSON log format main_kst + iso8601 + remote_addr + x_forwarded_for + request_id + upstream_response_time + 보안 server_tokens off + 25M client_max_body_size + gzip 6 + 5 rate limit zone (auth_zone 10r/m + api_zone 60r/m + bot_zone 20r/m + upload_zone 30r/m + ws_conn 동시 연결) + Docker bridge real_ip_recursive on + Strict-Transport-Security 2y preload) + deploy/nginx/conf.d/tootalk.conf 신설 (HTTP 80 → HTTPS 301 redirect + ACME challenge webroot + HTTPS 443 TLS 1.2/1.3 + Let's Encrypt fullchain + ECDHE-ECDSA-AES-GCM 6 cipher + OCSP stapling + 5 보안 header (HSTS + X-Frame SAMEORIGIN + nosniff + Referrer-Policy + CSP default-src self) + request_id 의 upstream 전파 + X-Real-IP + X-Forwarded-For + X-Forwarded-Proto + 8 location (auth 5r/m + bot per-user 10r + upload 100MB no buffer + 일반 30r + WS upgrade 3600s timeout + healthz no-log + static 7d expires + 404 JSON)). cycle 106 .env.example 본문 rewrite — 기존 9 라인 → 11 카테고리 65 라인 의 정본 (ENV + LOG + TZ + MariaDB + SMTP + 시그널링 + STUN/TURN + 봇 + FCM + nginx/TLS + Toonation + 미디어 캐시) + pre-existing 4건 BPE U+CE21 정정 (단독 U+CE21 4 instance 모두 제거 — 환경변수 예시 + .env.local 분리 + 사용자 식별 + 키 페어 표현 정정). cycle 107 docker compose syntax verify — `docker compose config --quiet` 검증 PASS (env 의 stub MARIADB_ROOT_PASSWORD/MARIADB_USER/MARIADB_PASSWORD 주입 후 syntax PASS, env 부재 시 의 ":?의무" guard 동작 검증 PASS). 전체 pytest = 1112 passed (변경 무 — infra 단독). drift 0건 58 연속. 5 검증 PASS. Phase 4 entry 누계 = 20 신규 파일 (cycle 101 6 + cycle 102 8 + cycle 103~104 3 + cycle 105 2 + cycle 106 1 rewrite). 다음 cycle 108 = local override smoke 검증 + cycle 109~111 Item 2 본문 (Config 클래스 + 5 파일 load 순서)
- [2026-05-22 14:30:00 KST] cycle 103~104 Phase 4 firebase-admin SDK + FCMClient 실 binding skeleton + 9 신규 PASS (사용자 directive "작업 재개해" 자율 chain) — Phase 4 Item 1 push 통합 layer. server/requirements.txt 에 firebase-admin>=7.0 entry 추가 (rationale comment — Phase 4 cycle 103~104 FCM v1 SDK 실 binding, 미설치 시 graceful log warning + push skip, production 의무). app/notifications/fcm_client.py 신설 — firebase_admin import try/except graceful (_FIREBASE_AVAILABLE 모듈 상수), FCMClient dataclass (credential_path + project_id + app_name "tootalk") + lazy initialize (FCM_CREDENTIAL_PATH env + Docker secret /run/secrets/fcm_service_account.json default + 파일 부재 시 FCMUnavailableError + 기존 app get_app / 신규 initialize_app), send(payload) → Messaging API v1 (Message + data + Notification 의 title/body 옵션 + AndroidConfig priority high + collapse_key) + 4 종 예외 (FCMError base + FCMUnavailableError + FCMInvalidTargetError + 일반 FCMError exception 변환). is_available() classmethod + from_env() factory. tests/app/notifications/test_fcm_client.py 9 신규 4 TestClass — TestFCMClientAvailability 2 (is_available bool + lazy construction) + TestFCMClientInitialize 3 (SDK 미설치 UnavailableError + cred_path 부재 UnavailableError + 비존재 파일 UnavailableError) + TestFCMSendValidation 2 (non-FCM platform reject + missing token reject) + TestFromEnv 2 (env read + no credentials no raise). 전체 pytest = 1112 passed (1103 + 9 신규). drift 0건 57 연속. 5 검증 PASS. 다음 cycle 105 = nginx conf.d/ + Item 3 base. cycle 106~107 = .env.example 본문 (Item 2 일부 선행) + secrets sample
- [2026-05-22 14:00:00 KST] cycle 102 Phase 4 postfix + opendkim 통합 image + SPF/DKIM/DMARC DNS doc (사용자 directive "작업 재개해" 자율 chain) — 7 신규 파일 `deploy/postfix/`. (1) `Dockerfile` — debian:bookworm-slim + postfix + opendkim + ca-certificates + supervisor + tzdata KST + opendkim group postfix 합산 + EXPOSE 25/587 + entrypoint chain. (2) `main.cf` — postfix base config (myhostname/mydomain entrypoint 치환 + open relay 차단 + TLS Let's Encrypt 의무 path + smtpd_milters inet:8891 opendkim chain + smtpd_helo/sender/recipient_restrictions 3 layer + bounce/delay warning). (3) `master.cf` — service 정의 (smtp 25 + submission 587 + smtpd_sasl_auth_enable + smtpd_client_restrictions permit_sasl_authenticated). (4) `opendkim.conf` — Mode sv + SignatureAlgorithm rsa-sha256 + Socket inet:8891 + KeyTable + SigningTable refile + TrustedHosts ExternalIgnoreList + Canonicalization relaxed/relaxed + MinimumKeyBits 2048. (5) `opendkim/KeyTable` + `SigningTable` + `TrustedHosts` — placeholder pattern (entrypoint env 치환). (6) `supervisord.conf` — postfix start-fg + opendkim -f foreground 2 program supervise + stdout/stderr unbuffered. (7) `entrypoint.sh` — MAILDOMAIN + DKIM_SELECTOR env → postconf -e 치환 + sed -i KeyTable/SigningTable + DKIM 키 부재 시 `opendkim-genkey -b 2048` 자동 생성 + DNS TXT record 출력. (8) `DNS_RECORDS.md` — SPF (v=spf1 ip4:114.207.112.73 -all) + DKIM (2048 bit RSA SHA-256) + DMARC (v=DMARC1 p=quarantine adkim=s aspf=s) + PTR + Let's Encrypt certbot 명령 + mail-tester score 8+ 의무. 전체 pytest = 1103 passed (변경 무). drift 0건 56 연속. 다음 cycle 103~104 = firebase-admin SDK + service-account placeholder + app/notify/push.py 실 binding 전환
- [2026-05-22 13:30:00 KST] cycle 101 Phase 4 Item 1 docker stack base 신설 (사용자 directive "다음작업 진행해" 자율 chain) — `deploy/` 디렉토리 + 6 컴포넌트 docker-compose stack base. `deploy/docker-compose.yml` 신설 — 5 service 정의 (mariadb + postfix + web + ws + nginx) + 2 network (tootalk-internal isolated bridge + tootalk-edge nginx 격리) + 4 named volume (mariadb_data + postfix_spool + nginx_cache + letsencrypt) + 1 Docker secret (fcm_service_account.json) + healthcheck (mariadb 30s + web /healthz) + env 의존성 chain. `deploy/docker-compose.local.yml` 신설 — 개발자 mariadb + postfix 만 기동 + 127.0.0.1 port bind + profiles disabled. `deploy/docker-compose.production.yml` 신설 — resources limits (mariadb 2G/1.5cpu + web 1G/1cpu × 2 replicas + ws 512M + nginx 256M) + json-file log rotation + LOG_FORMAT=json. `deploy/README.md` 신설 — 구조 + 6 서비스 매핑 표 + 시작 명령 + 보안 의무 5건. `deploy/mariadb/my.cnf` 신설 — utf8mb4_unicode_ci + KST timezone (+09:00) + max_connections 200 + innodb_buffer_pool 1G + slow_query_log + binary log row format. `deploy/web/Dockerfile` 신설 — python:3.13-slim + non-root user (uid 1000) + tzdata KST + server/requirements.txt install + healthcheck `/healthz` + EXPOSE 8080/8765. `.gitignore` 갱신 — `deploy/secrets/` + `deploy/postfix/dkim/` ignore + `.gitkeep` 허용 + BPE U+CE21 3건 정정. `deploy/secrets/.gitkeep` + `deploy/postfix/dkim/.gitkeep` placeholder. 전체 pytest = 1103 passed (변경 무 — infra 단독). drift 0건 55 연속. 5 검증 PASS. 다음 cycle 102~108 = postfix Dockerfile + main.cf + DKIM + nginx conf + secrets sample
- [2026-05-22 13:00:00 KST] cycle 100 Phase 4 진입 — httpx pip install + verify gate 2 skip → 0 skip 전환 (사용자 directive "다음작업 진행해" 자율 chain, Phase 4 §1.4 사전 의존성 install) — `.venv/bin/pip install "httpx>=0.27"` 실행 (httpx 0.28.1 + h11 + httpcore + anyio + certifi 의존성 chain). `import httpx; print(httpx.__version__)` verify PASS (0.28.1). `pytest tests/server/test_main_integration.py` 결과 — 직전 7 PASS + 2 SKIPPED (httpx 미설치 graceful skip) → 9 PASS 전환 (`test_openai_fallback_when_only_openai_key_present` + `test_anthropic_preferred_over_openai` 의 skip 해소). 전체 pytest = **1103 passed** (직전 1101 + 2 skip → 1103 active, +2 skip 해소). `AnthropicProvider.is_available()` + `OpenAIProvider.is_available()` 가 `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` 환경 변수 가용 시 True 반환 가능 도달 (이전 httpx ImportError graceful False). drift 0건 54 연속. 5 검증 PASS. Phase 4 본문 진입 (cycle 101~108 Item 1 docker stack) prerequisite 완성. 사용자 manual test prerequisite — `ANTHROPIC_API_KEY` 또는 `OPENAI_API_KEY` 의 .env 또는 환경 변수 설정 후 `BOT_ENABLED=1` + 실 LLM API 호출 smoke
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

---

**문서 상태**: `active` · 최초 작성 2026-05-17 · M2 변경 이력 30행 캐시
운영. 30행 초과 시점부터 회전 + History.md 위임.
