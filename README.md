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
상태로 시작한다. 좌측 ChatListPanel 에서 친구·방·봇 대화를 선택해 진입하며,
그룹방은 "그룹 만들기" wizard + 멤버 초대로 생성한다 (cycle 169.838 "방 입장"
방번호 직접 입력 폐지 정합).

> 시그널링 클라이언트는 WebSocket 연결 + 비정상 drop 시 지수 backoff 자동 재연결 +
> 마지막 JOIN 식별자 기반 reJOIN 복구를 수행한다 (cycle 169.775, `app/net/signaling_client.py`).
> 자세한 사용은 [app/README.md](app/README.md) 참조.

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
│   ├── rtc/                  # WebRTC peer_connection · mesh_manager · file 송수신
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
| 8 운영 문서 (루트) | [Specification.md](Specification.md) · [Structure.md](Structure.md) · [CheckList.md](CheckList.md) · [History.md](History.md) · README.md (본 문서) · [EXTENSION_GUIDE.md](EXTENSION_GUIDE.md) · [MIGRATION_MARIADB.md](MIGRATION_MARIADB.md) · [CLAUDE.md](CLAUDE.md) |
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
- 신규 DB 테이블 — [MIGRATION_MARIADB.md](MIGRATION_MARIADB.md) `tables` 배열 FK 순서 + Structure.md ERD
- 작업 완료 직후 — 본 README §11 변경 이력에 한 줄 prepend (M2 의무)

확장 가이드 정본은 [EXTENSION_GUIDE.md](EXTENSION_GUIDE.md) (운영 8 문서 중 7번째)
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
> 항목 제거 + 상세는 [History.md](History.md) 위임.
>
> 본 시점 = 30행 상한 회전 완료 (2026-05-21 — release-agent cycle 169.189 M2 53 entry batch prepend + dereliction-detector HIGH 회수 정합).
> 상세 History.md 전체 보존.

- [2026-06-09 16:19:00] cycle 169.861 — **webmail M4 IMAP 결선 완결 + Dovecot 잔존 버그 2 fix + 실 서버 install/deploy + 자체 loopback PASS**. 사용자 directive "설치는 니가 직접 해줘" + "잔존 진행하고 imap 결선 작업까지 진행해" 정합. **Dovecot install 직접 SSH 실행**: `bash ~/p2p_msg/tools/dovecot_install.sh` → dnf install + vmail uid 5000 + 6 conf 파일 + passwd-file + Postfix virtual_* + iptables 143/993/4190 + systemctl enable 전수 성공. **잔존 버그 2 진단/회수**: (1) `tools/mail_user_add.sh` passwd-file line 형식 — `${USER_NAME}:` → `${USER_EMAIL}:` 정정 (username_format=%u 정합, bare name 시 userdb lookup FAIL). (2) `tools/dovecot_install.sh` §3.1 SELinux fcontext mail_spool_t — `semanage fcontext -a -t mail_spool_t "/var/vmail(/.*)?"` + `restorecon -Rv /var/vmail` 추가 (Rocky 9 enforcing 정합, var_t default 시 SERVERBUG "ACL/MAC wrong"). 동시 `mail_user_add.sh` §6.1 신규 maildir restorecon 추가. **자체 loopback 검증** = test@dopa.co.kr 계정 + SMTP 587 STARTTLS AUTH OK + IMAP 993 LOGIN OK + SELECT INBOX OK + sendmail self + 즉시 FETCH RFC822 수신 확인 (LMTP delivery 정합). **M4 IMAP 결선 코드**: `server_webmail/imap_service.py`(180 line — IMAPError + MailSummary/MailBody dataclass + connect_and_login + list_inbox + fetch_body + ENVELOPE/RFC822 parse), `server_webmail/main.py`(380 line, 8 route — /healthz + / + /login GET/POST + /logout + /inbox + /mail/<uid> + aiohttp_session EncryptedCookieStorage WEBMAIL_SESSION_KEY env + secrets.token_bytes 32 fallback + IMAP imap_service 호출 asyncio.to_thread, HTML render = _render_login/_render_inbox/_render_mail inline string, 로그인 폼 + INBOX list paginate 50 + 메일 view + 로그아웃 정합), `server_webmail/requirements.txt` aiohttp-session>=2.12 + cryptography>=42 add. **e2e** `tests/integration/test_webmail_backend_imap.py` 11 test PASS (route 등록 7 + /healthz 200 cycle=169.861 stage=M4-imap-integrated + 세션 부재 redirect + /login GET HTML + IMAP 실패 401 + IMAP 성공 mock 302 /inbox + 세션 정합 /inbox list HTML + 세션 정합 /mail/<uid> body HTML + /logout invalidate + imap_service IMAPError ssl 분기). (server_webmail · tools · tests/integration)
- [2026-06-09 15:43:00] cycle 169.860 — **평가 staleness sweep + reviewer BLOCKER 회수 (dereliction-detector 자동 spawn 환류)**. dereliction-detector-agent 자동 spawn 결과 HIGH 2건(평가 staleness 4 file marker 169.857 동결) + MEDIUM 1건(cycle 169.859 reviewer-agent 게이트 미실행) detect. **HIGH 회수**: productization.md + vibe-coding.md + HTML mirror 2 file last_verified 11:39→15:43 + 사이클 169.857→169.859 marker bump + §1 최신 갱신 chain + 평가 기준일 + sweep markers (§5/§6/§8 productization + §394/§423/§477 vibe) 전수. **MEDIUM 회수**: reviewer-agent cycle 169.859 산출물 검토 BLOCKER 1건 + RISK 2건 + NITY 1건 detect — Dockerfile healthcheck `wget` python:3.13-slim base 부재 → stdlib urllib 으로 swap(`["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen(...)"]`), main.py handle_login_post body 미소비 async stream 점유 risk → `await request.post()` 의도 폐기 명시(M4 후속 cycle 결선 의무). 5 test 재 PASS + doc-lint PASS 88 file. 본 cycle = workflow 회수 cycle (직무유기 자동 환류 정합, 사용자 directive 부재 dereliction-detector 자동 spawn 결과 처리). (docs/assessments · docs/html · deploy/docker-compose.yml · server_webmail/main.py)
- [2026-06-09 15:30:00] cycle 169.859 — **webmail.dopa.co.kr M3 Python aiohttp backend skeleton + docker-compose webmail 서비스 + 실 서버 deploy**. 사용자 directive "반영을 좀 직접 해줘" 정합. 트리거 = cycle 169.858 PR #29 merge 후 사용자 접속 → `{"error":"not_found"}` (tootalk.conf catch-all). 원인 = nginx upstream resolve FAIL `host not found in upstream "webmail"` (webmail container 부재). 산출물 = `server_webmail/main.py`(aiohttp app — /healthz + / → /login redirect + /login GET placeholder HTML 로그인 폼 + /login POST 503 placeholder) + `server_webmail/Dockerfile`(python:3.13-slim + aiohttp + EXPOSE 8090) + `server_webmail/requirements.txt`(aiohttp>=3.9) + `deploy/docker-compose.yml` webmail service add(build context ../server_webmail + healthcheck wget /healthz + nginx depends_on webmail). e2e `tests/integration/test_webmail_backend_skeleton.py` 5 test PASS — route 4종 + /healthz 200 JSON status=ok + / → /login 302 + /login GET 200 HTML + /login POST 503 placeholder. 실 서버 deploy = SSH `~/p2p_msg` git pull + `docker compose --profile certbot run --rm certbot certonly --webroot -d webmail.dopa.co.kr` Let's Encrypt cert 발급 성공(만료 2026-09-07) + docker compose up -d webmail nginx + nginx reload + curl /healthz 200. (server_webmail · deploy · tests/integration)
- [2026-06-09 13:00:00] cycle 169.858 — **webmail.dopa.co.kr Python 웹메일 backend M1 doc + M2 nginx 서브도메인 vhost**. 사용자 directive "이메일을 웹페이지에서 볼 수 있게끔 웹페이지화" + "php로 작업하지말고 python 웹페이지로 만들어 통일성이 없어" + "webmail.dopa.co.kr 서브도메인 신설" + "nginx 버추얼 호스트 만들어야 할꺼야" 정합. M1 Exec Plan(`docs/exec-plans/active/2026-06-09-webmail-python-backend.md` 282 line — Python aiohttp + imaplib + smtplib + Jinja2/HTMX, webmail.dopa.co.kr 서브도메인, cycle 169.857 G-final dependency, M1~M6 마일스톤 분해 + 본 cycle scope = M1+M2 만) + M2 `deploy/nginx/conf.d/webmail.conf`(87 line — server_name webmail.dopa.co.kr 명시(catch-all `_` 회피) + TLS Let's Encrypt 별도 cert + upstream webmail:8090 + 보안 header 5종 + CSP 메일 본문 정합(img-src https: + script unsafe-inline HTMX) + location 4종 + client_max_body_size 25M + proxy timeout 60s). `tests/integration/test_webmail_nginx_vhost.py` 18 test PASS — structural smoke(SPDX/cycle marker/server_name/TLS path/upstream/proxy headers/security headers/CSP/location/static alias/healthz no log/upload 한도/timeout/brace balance/single server/한글 주석). M3 docker-compose + Python backend skeleton = 후속 cycle 169.859 분리. (deploy/nginx · docs/exec-plans · tests/integration)
- [2026-06-09 12:00:00] cycle 169.857 — **mail.dopa.co.kr Dovecot+IMAP 수신 메일박스 신설 M1~M5**. 사용자 directive "mail.dopa.co.kr 계정 추가" + "기존 워크플로우대로 문서부터 만들고 작업을 진행하되 e2e 까지 고려" 정합. M1 Exec Plan(`docs/exec-plans/active/2026-06-09-dovecot-imap-install.md` 329 line, virtual mailbox 모델 + Postfix LMTP 통합 + passwd-file 계정 store) + M2 `tools/dovecot_install.sh`(Rocky 9.7 idempotent 268 line, 10 단계 — vmail uid 5000 / maildir root / Dovecot 6 conf 파일 / passwd-file / Postfix virtual_* 4 키 / iptables 143+993+4190 / systemctl / listen 검증) + M3 `tools/mail_user_add.sh`(100 line, 1 명령 = passwd-file + maildir + sasldb2 동시 등록 + openssl 패스워드 생성 + Dovecot/Postfix reload + stdout 자격 안내) + M4 `tests/integration/test_dovecot_imap_e2e.py`(7 test, IMAP CAPABILITY/SMTP 587 auth 강제/LMTP socket 정합/bash -n syntax/usage 검증, 6 PASS + 1 SKIP IMAP unreachable expected) + M5 `.env.example` IMAP_* 5 keys add. 한글 주석 의무 M4 + bash -n syntax PASS + pytest 6 PASS. SSH 수동 (Exec Plan §6 G-final). (docs/exec-plans · tools · tests/integration · .env.example)
- [2026-06-09 11:12:00] cycle 169.856 — **원격 origin/main 143 commit fast-forward pull catchup 로컬 sync**. 신규 작업 머신 `/Users/1ticket/Documents/vscode_work/p2p_msg/` 가 원격 main 대비 143 commit 뒤(cycle 169.849~855 시리즈 = M6 app/ui 51/51 + e2e 9/9 + server 15/48 batch s1~s7 + avatar M1~M7 + room broadcast→통합 ChatView 마이그레이션 M3~M6 + codex §8 큐 회수)였고 `git pull --ff-only` 단일 명령으로 fast-forward sync(HEAD=`e7d0f53`, working tree clean). 평가 2종 + HTML mirror 4종 marker bump(2026-05-28→2026-06-09, cycle 169.855→169.856) + token-usage-30d 재 산출(window_end 2026-05-27→2026-06-09, sessions 4→9, msgs 22307→27447, cost \$24217→\$28889). 신규 feat 작업 부재 — pull catchup 단독. (assessment + html mirror + token-usage + README/History)
- [2026-05-28 11:00:00] cycle 169.855 — **한글 주석 페이즈 M7 server s7 (T-7) — tests/server 3종 (health_handlers + logging_setup + main_integration)**. 3종 모두 filler 전환 — health_handlers(healthz liveness/readyz readiness dependency check + PUBLIC_PATHS bypass wire smoke, colon 1) + logging_setup(KSTFormatter/KSTJSONFormatter/RedactingFilter 민감정보 마스킹/configure_logging test, colon 6) + main_integration(build_app route 등록 + BOT_ENABLED OpenAI strict + TestClient e2e, dash 5). 기능 diff 0 — verify_comment_only 3 PASS + 대상 45 passed(server 실 pytest) + BPE/대명사/이중조사 0. M7 server 21/48 (test 30/256). (tests/server)
- [2026-05-28 10:40:00] cycle 169.855 — **한글 주석 페이즈 M7 server s6 (T-7) — tests/server 3종 (folder_repository + friends_handlers + friends_repo)**. 3종 모두 filler 전환 — folder_repository(folders insert/list/delete/invite/aggregate atomic commit+rollback repo test, dash 1) + friends_handlers(8 endpoint × 정상/권한/edge + FRIEND_* user_activity_log audit 검증, colon 다수) + friends_repo(친구 insert/lookup/list/pending/accept/status/delete/search/nickname repo test, dash 4). 기능 diff 0 — verify_comment_only 3 PASS + 대상 34 passed(server 실 pytest) + BPE/대명사/이중조사 0("자기 자신" = 권장 대체어+런타임 match string 보존). M7 server 18/48 (test 27/256). (tests/server)
- [2026-05-28 10:20:00] cycle 169.855 — **한글 주석 페이즈 M7 server s5 (T-7) — tests/server 3종 (emoji_packs_schema + file_meta_password_reset_repo + folder_handlers_integration)**. folder_handlers_integration = filler 0(무변경 검수) + emoji_packs_schema(0004 emoji_packs DDL schema 정합 SQL parse test, colon filler 1건) + file_meta_password_reset_repo(file_meta 송수신 영속 + password_reset 토큰 발급/검증/소진 repo test, dash filler 3건). 기능 diff 0 — verify_comment_only 2 PASS + 대상 35 passed(server 실 pytest) + BPE/대명사/이중조사 0. M7 server 15/48 (test 24/256). (tests/server)
- [2026-05-28 10:00:00] cycle 169.855 — **한글 주석 페이즈 M7 server s4 (T-7) — tests/server 3종 (email_verification_devices_repo + email_verification_retry + emoji_moderation_handlers)**. 3종 모두 filler 전환 — email_verification_devices_repo(OTP 발급/검증/소진/cleanup + device register/list/revoke repo test, dash filler 3건) + email_verification_retry(MariaDB 1020 Record-changed retry helper 3 path test, inline 포함 dash filler 4건) + emoji_moderation_handlers(emoji moderation 4 endpoint admin Bearer 401 + UPDATE/SELECT call_args 검증, colon filler 14건). 기능 diff 0 — verify_comment_only 3 PASS + 대상 29 passed(server 실 pytest) + BPE/대명사/이중조사 0. M7 server 12/48 (test 21/256). (tests/server)
- [2026-05-28 09:40:00] cycle 169.855 — **한글 주석 페이즈 M7 server s3 (T-7) — tests/server 3종 (config + contacts_app_versions_repo + devices_handlers)**. contacts_app_versions_repo = filler 0 으로 표준 충족(무변경 검수). config(env load + 7 from_env + production validate test — Python filler `한글 주석` prefix 5건 전환 + line 45 주어 누락 "의" 잔재 → "DB_PORT invalid int" 의미 복원 + class docstring "환경 의 의무 키" → "환경 필수 키" 정정) + devices_handlers(multi-device register/list/revoke handler test — filler 1건 전환 + fixture comment "미테스트 의 의도" → "미테스트 의도" 정정). 기능 diff 0 — verify_comment_only PASS + 대상 64 passed(server 실 pytest) + BPE/대명사/이중조사 0. M7 server 9/48 (test 18/256). (tests/server)
- [2026-05-28 09:20:00] cycle 169.855 — **한글 주석 페이즈 M7 server s2 (T-7) — tests/server 3종 (avatars_repo + bot_handlers + bots_repo)**. avatars_repo = cycle 169.852 최신 작성으로 주석 표준 충족(무변경 검수). bot_handlers + bots_repo Python filler `한글 주석` prefix 6건 전환 + bot_handlers audit metadata inline 주석 명확화. 기능 diff 0 — verify_comment_only PASS + 대상 81 passed(server 실 pytest, browser 무관) + BPE/대명사/이중조사 0. M7 server 6/48 (test 15/256). (tests/server)
- [2026-05-28 09:00:00] cycle 169.855 — **한글 주석 페이즈 M7 server s1 (T-7) — tests/server 3종 (bot_escalations + user_activity + auth_handlers_audit)**. test module docstring 선존 양호(test 대상·전략 명시) + Python filler `한글 주석` prefix 전환. 기능 diff 0 — verify_comment_only PASS + 대상 48 passed(server test 실 pytest 실행, browser 무관) + BPE/대명사/이중조사 0. M7 server 3/48 (test 12/256). (tests/server)
- [2026-05-28 08:40:00] cycle 169.855 — **한글 주석 페이즈 M7 e2e e2 (T-7) — tests/e2e 잔여 6 전수 review → e2e 9/9 완료**. html_visual_smoke + __init__ SPDX header 추가 + html_visual 테스트 전략 line + Python filler 전환. image/signaling/video_call/voice_call 4종 = Python docstring 선존 양호(변경 부재, JS `//` filler 는 page.evaluate 문자열이라 diff-0 보존). 기능 diff 0 — verify_comment_only 2 PASS + e2e 10 collect 무결성. **M7 e2e 9/9 전수 완료** — 다음 server 48. (tests/e2e)
- [2026-05-28 08:20:00] cycle 169.855 — **한글 주석 페이즈 M7 e2e e1 (T-7) — tests/e2e 3종 (conftest + datachannel_browser + datachannel_file)**. 사용자 directive "e2e 부터" 순서 — M7 e2e 우선. conftest SPDX header 추가 + 테스트 전략 line + Python filler prefix 전환. **잔존 `// 한글 주석` 은 Playwright page.evaluate() JS 문자열 내용(AST Constant)이라 diff-0 보존**(런타임 string 미변경 규율). 기능 diff 0 — verify_comment_only 3 PASS + e2e 10 collect 무결성. M7 e2e 3/9 (test 4/256). (tests/e2e)
- [2026-05-28 08:00:00] cycle 169.855 — **한글 주석 페이즈 M6 dialog d9 (T-7) — app/ui dialog 5종 (remote_control + settings + signup + update + welcome) → dialog 29/29 완료**. dialog 계층 §E 보강 + filler prefix 전환 + settings 선존 이중조사 "의 의" 2건 정정. **M6 app/ui 51/51 전수 완료(mixin 22 + dialog 29)** — 다음 M7 test·e2e. 기능 diff 0 — verify_comment_only 5 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 51/51. (app/ui)
- [2026-05-28 07:40:00] cycle 169.855 — **한글 주석 페이즈 M6 dialog d8 (T-7) — app/ui dialog 3종 (call + _camera_capture + remote_call)**. d1에서 누락된 call_dialog 포함. dialog 계층 §E 보강 + filler prefix 전환. call CallClient attach·camera QtMultimedia release·remote_call RemoteSessionRunner 회신 명시. 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 dialog 24/29 — M6 46/51. (app/ui)
- [2026-05-28 07:20:00] cycle 169.855 — **한글 주석 페이즈 M6 dialog d7 (T-7) — app/ui dialog 3종 (otp + password_reset + pending_requests)**. dialog 계층 §E 보강 + filler prefix 전환 + otp 선존 이중조사 "의 의" 3건 정정. OTP nested exec_modal·비번 재설정 단계 chain·친구 요청 accept/reject signal 명시. 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 dialog 21/29 — M6 43/51. (app/ui)
- [2026-05-28 07:00:00] cycle 169.855 — **한글 주석 페이즈 M6 dialog d6 (T-7) — app/ui dialog 3종 (new_channel + new_contact + new_group)**. dialog 계층 §E 보강 + filler prefix 전환 + new_contact 선존 이중조사 "의 의" 1건 정정. 채널/그룹 wizard signal 회신 + 서버 room 승격 caller 책임 명시. 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 dialog 18/29 — M6 40/51. (app/ui)
- [2026-05-28 06:40:00] cycle 169.855 — **한글 주석 페이즈 M6 dialog d5 (T-7) — app/ui dialog 3종 (login + my_account + my_profile)**. dialog 계층 §E 보강 + filler prefix 전환 + login/my_profile 선존 이중조사 "의 의" 2건 정정. login startup+auth chain instantiate·token 발급 명시(런타임 string "문의 의무"는 diff-0 보존). 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 dialog 15/29 — M6 37/51. (app/ui)
- [2026-05-28 06:20:00] cycle 169.855 — **한글 주석 페이즈 M6 dialog d4 (T-7) — app/ui dialog 3종 (group_call + group_info + invite)**. dialog 계층 §E 보강 + filler 1건 전환 + invite 선존 이중조사 "의 의" 2건 정정. group_call SFU 미디어 협상 무관·UI 전용 명시. 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 dialog 12/29 — M6 34/51. (app/ui)
- [2026-05-28 06:00:00] cycle 169.855 — **한글 주석 페이즈 M6 dialog d3 (T-7) — app/ui dialog 3종 (find_id + folder_edit + folder_manage)**. dialog 계층 §E 보강 + filler `한글 주석` prefix 7건 전환. find_id enumeration 방어 server 책임 명시. 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 dialog 9/29 — M6 31/51. (app/ui)
- [2026-05-28 05:40:00] cycle 169.855 — **한글 주석 페이즈 M6 dialog d2 (T-7) — app/ui dialog 3종 (chat_picker + confirm + contacts)**. dialog 계층 §E 보강 + filler `한글 주석` prefix 20건 전환 + contacts 선존 이중조사 "의 의" 정정. confirm = 전역 40+ 호출 공용 얼럿 진입점 명시. 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 dialog 6/29 — M6 28/51. (app/ui)
- [2026-05-28 05:20:00] cycle 169.855 — **한글 주석 페이즈 M6 dialog d1 (T-7) — app/ui dialog 3종 (add_friend_by_username + add_friend + calls)**. dialog 계층 §E(app/ui QDialog — caller instantiate + signal 회신) 보강 + filler `한글 주석` prefix 8건 전환. dialog 흐름 docstring 선존 양호(add_friend §E 선참조). 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 dialog 3/29 — M6 25/51. (app/ui)
- [2026-05-28 05:00:00] cycle 169.855 — **한글 주석 페이즈 M6 batch-8 (T-7) — app/ui mixin drawer 마지막 1종 → mixin 22/22 완료**. `_drawer_mixin.py` module 계층 §E(MainWindow MRO 합성) 보강 + filler `한글 주석` prefix 12건 의도 기반 전환. HamburgerDrawer 9 slot + avatar 업로드·room 생성 chain docstring 선존 양호. 기능 diff 0 — verify_comment_only PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. **M6 mixin 22/22 완료 — 다음 dialog 29**. M6 22/51. (app/ui)
- [2026-05-28 04:45:00] cycle 169.855 — **한글 주석 페이즈 M6 batch-7 (T-7) — app/ui mixin 3종 (menu_bar + tray + chat_send)**. 3 mixin module 계층 §E(MainWindow MRO 합성) 보강 + filler `한글 주석` prefix 24건(menu_bar 6·tray 9·chat_send 9) 의도 기반 전환. method docstring 선존 양호. 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 mixin 21/22(잔여 drawer 1) — M6 21/51. (app/ui)
- [2026-05-28 04:20:00] cycle 169.855 — **한글 주석 페이즈 M6 batch-6 (T-7) — app/ui mixin 3종 (chat_navigation + dialog_center + friend_search)**. 3 mixin module 계층 §E(MainWindow MRO 합성) 보강 + filler `한글 주석` prefix 14건(chat_navigation 7·dialog_center 4·friend_search 3) 의도 기반 전환. method docstring 선존 양호. 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 18/51(mixin 18/22). (app/ui)
- [2026-05-28 03:55:00] cycle 169.855 — **한글 주석 페이즈 M6 batch-5 (T-7) — app/ui mixin 3종 (bot_chat + chat_header + chat_helper)**. 3 mixin module 계층 §E(MainWindow MRO 합성) 보강 + filler `한글 주석` prefix 5건(bot_chat 3·chat_header 1·chat_helper 1) 의도 기반 전환. method docstring 선존 양호. 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 15/51. (app/ui)
- [2026-05-28 03:30:00] cycle 169.855 — **한글 주석 페이즈 M6 batch-4 (T-7) — app/ui mixin 3종 (auth_chain + folder + rest_post)**. 3 mixin module 계층 §E(MainWindow MRO 합성) 보강 + auth_chain filler `한글 주석` prefix 2건 의도 기반 전환(i18n 바인딩·tray logout chain 단일화). 분리 대상 method/의존 구조·docstring 선존 양호. 기능 diff 0 — verify_comment_only 3 PASS + offscreen 1963 passed 무변경 + BPE/대명사/이중조사 0. M6 12/51. (app/ui)
- [2026-05-28 03:05:00] cycle 169.855 — **한글 주석 페이즈 M6 batch-3 (T-7) — app/ui mixin 3종 (friend_profile + update_lifecycle + sfu_call)**. 3 mixin module 계층 §E(MainWindow MRO 합성) 보강 + filler `한글 주석` prefix sed 전환. 분리 대상 method/의존 구조·sfu 배선 method docstring 선존 양호. 기능 diff 0 — verify_comment_only 3 PASS + offscreen 130 passed 무변경 + BPE/대명사/이중조사 0. M6 9/51. (app/ui)
---

**문서 상태**: `active` · 최초 작성 2026-05-17 · M2 변경 이력 30행 캐시
운영. 30행 초과 시점부터 회전 + History.md 위임.
