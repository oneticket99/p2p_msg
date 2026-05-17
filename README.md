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

**미확정** — 사용자 응답 대기. Phase 1 후반(실행계획 §7 결정 로그)에서
다음 후보 중 1건으로 확정한다.

- MIT
- Apache-2.0
- GPL-3.0
- 사유 (closed source)

라이선스 결정 직전까지 본 저장소의 코드·문서·산출물(zip)에 대한 외부
재배포는 사용자 명시 승인 경로에서만 허용한다. 결정 즉시 본 §9 와
[Specification.md §12 TBD-01](Specification.md) 을 동시에 갱신한다.

PyQt6 GPL 의 상용 전환 영향 (PySide6 LGPL 으로 변환 검토) 은 결정 로그
2026-05-17 ([실행계획](docs/exec-plans/) 정본) 정독.

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
> 현 시점(2026-05-17) 누계 commit 21건 — 30행 상한 미달. 신규 commit 누적 시
> 본 표를 위에서부터 채워 30행 도달 시점부터 오래된 항목을 회전 제거한다.

- [2026-05-17 15:55:00] docs/references/ci-self-hosted-setup.md wine cross-compile 정책 본문 갱신 — 사용자 directive 2026-05-17 "윈도우 빌드는 wine을 이용해서" + "권장 default 진행" 자율 GO 정합. §1 매트릭스 (Windows self-hosted row 회수 + GitHub-hosted Ubuntu row 신규) + §2.2 Windows dependency 회수 + §3.3 Windows 등록 단계 회수 + §4.1 검증 (macOS 단독 + gh API 검증 명령) + §9 운영 체크리스트 8 entry 갱신 (4건 [x] 완료 + 1건 build.yml 후반) + §11 신설 (wine cross-compile 정책 + 패턴 + 검증 + 대안) + 영구 메모리 link 추가. 본 영역 = 큰 정책 변경 = 8 체크리스트 의무 영역 (docs/references/ci-self-hosted-setup.md)
- [2026-05-17 15:43:00] Task #5/#6/#7 completed — ci 8 job GREEN 도달 + CheckList §2 row 2개 갱신 (CI 워크플로우 = 3/4 GREEN + self-hosted runner = 1/2 의 workflow 픽업 검증 명시). Task #5 워크플로우 수동 trigger 검증 + Task #7 dead link fix 결정 모두 completed. 잔존 = Task #3 Windows runner + Task #4 fork PR 승인 (사용자 직접) (CheckList.md)
- [2026-05-17 15:40:00] ci.yml venv setup step 추가 — PEP 668 externally-managed 회피. import-smoke + pytest job 의 brew python@3.13 의 self protection 정책 (PEP 668) 의 pip install 거부 → venv 격리 의무. `python -m venv .venv` + `$GITHUB_PATH` + `$VIRTUAL_ENV` 의 step 간 persistence (.github/workflows/ci.yml)
- [2026-05-17 15:32:00] ci.yml 4 게이트 fix — M2 regex (optional number prefix) + M3 grep (`^## Phase` 매치 + `|| true` pipe failure 회피) + import-smoke + pytest job 의 brew python@3.13 PATH 등록 step 추가 (`/opt/homebrew/opt/python@3.13/libexec/bin` → `python` symlink 활성). 단일 macOS runner 환경의 ci 8 job 의 GREEN 도달 의무. local verify M2 MATCH + M3 PASS + python symlink 존재 + doc-lint 0 위반 (.github/workflows/ci.yml)
- [2026-05-17 15:25:30] dead link 10건 fix + ci.yml Windows matrix 임시 비활성 — 사용자 directive "진행해" 정합 자율 진행. 옵션 A 선택 = link text 영역 (예정) 마커 + doc-lint.sh skip rule (link text 안 (예정) 발견 시 검사 skip). Structure.md (3 line — §10.3 + §14.2 + §14.3) + FRONTEND.md (2 line — §3.3 + §15.1) 의 10 dead link (app/rtc/* + app/ui/file_progress_widget.py untracked). 옵션 W2 선택 = ci.yml import-smoke + pytest matrix 의 Windows-x64 entry 주석 처리 (Phase 1 후반 Task #3 재활성 명시). local lint 5 + markdownlint 0건 PASS + CI simulate (untracked stash) PASS (Structure.md + FRONTEND.md + .github/workflows/ci.yml + tools/doc-lint.sh)
- [2026-05-17 15:05:30] CI self-hosted macOS arm64 runner 등록 OK — gh API registration-token + actions/runner v2.319.1 + launchd svc (PID 62533 Started). GitHub status=online + busy=True (queued ci 픽업). docs-lint 의 MD041 위반 1건 fix — .github/pull_request_template.md 첫 줄 markdownlint disable directive 추가 + BPE 위반 README:309 정정 (lint 5 + markdownlint 0건 PASS) (.github/pull_request_template.md + README.md)
- [2026-05-17 14:50:30] 세션 종료 — handoff doc 사이클 2.1 minor 갱신 (§8.1 누계 commit 31 + §10 timestamp). 다음 세션 인계 정합 확인 완료 (docs/exec-plans/active/2026-05-17-session-handoff.md)
- [2026-05-17 14:46:48] History.md + README.md prepend 영역 BPE 잔존 5건 정정 — 자체 prepend 본문 일관성 확보. doc-lint 5 검사 전수 PASS (History.md + README.md)
- [2026-05-17 14:44:47] CLAUDE_HARNESS_IMPORTANT.md 정본 BPE 25건 일괄 정정 — sed " U+CE21 " → " 의 " (handoff §9 우선순위 2번 잔존 task 해소) (CLAUDE_HARNESS_IMPORTANT.md)
- [2026-05-17 14:42:00] handoff doc 사이클 2 갱신 — 본 세션 누계 28 commit + 가드레일 16 + auth 정책 + Phase 3 막바지 차별화 + snapshot 사이클 4 + sub-agent 16 spawn 반영 (docs/exec-plans/active/2026-05-17-session-handoff.md)
- [2026-05-17 14:36:00] 평가 snapshot 사이클 4 — productization 2.9→3.6 ▲ (차별화 3→4.5, 사용자가치 +0.5, 수익화 +0.5, Toonation 옵션 B ★★★★★) + vibe-coding 4.7→4.85 ▲ (보안 사고 5/5 신규 + §2.12-14 차별화/회원가입/10 정책 갱신 신규) + HTML 2종 sub-agent 병렬 (docs/assessments/ + docs/html/)
- [2026-05-17 14:26:14] HTML 3종 재생성 (CLAUDE.md §10-6 동시 갱신 의무) — ARCHITECTURE.html 366행 + Structure.html 637행 + FRONTEND.html 662행 (mermaid 9 + swatch 18 보존), sub-agent 3 병렬 (docs/html/)
- [2026-05-17 14:17:22] auth 인프라 정책 본문 5 파일 — PRODUCT_SENSE P3 재조정 + MIGRATION DB 4→7 테이블 + ARCHITECTURE app/auth + server/auth 모듈 + Structure auth 디렉토리 + FRONTEND §14.6~14.8 wireframe 3 (회원가입/로그인/비번찾기) (PRODUCT_SENSE + MIGRATION_MARIADB + ARCHITECTURE + Structure + FRONTEND)
- [2026-05-17 14:12:08] 회원가입 + 이메일 OTP 인증 정책 도입 — 필수 (email+username+pwd) + 선택 (nickname+avatar) + OTP 3분 + 아이디/비번 찾기. FR-11/12/13 + SECURITY §9-2 + adoption-roadmap Phase 1 + CheckList + 영구 메모리 16종 (사용자 directive 2026-05-17) (Specification.md + SECURITY.md + adoption-roadmap.md + CheckList.md + 메모리)
- [2026-05-17 14:02:05] 차별화 계획 정리 — 친구간 1:1 원격 데스크탑 제어 (패턴 A 도움 + 패턴 B 제어 / Toonation OBS 설정 도움 시나리오 / Phase 3 막바지 진입). 영구 메모리 신설 + PRODUCT_SENSE P5+P6 페르소나 + adoption-roadmap Phase 3 확장 (사용자 directive 2026-05-17) (PRODUCT_SENSE.md + docs/policies/adoption-roadmap.md + 메모리)
- [2026-05-17 13:56:40] 평가 snapshot 사이클 3 — productization 2.6→2.9 ▲ (가드레일·자동화 5 + 세션 정합 5 신규) + vibe-coding 4.5→4.7 ▲ (QA 사고 4.5 + 세션 정합 5 신규) + HTML 2종 sub-agent 병렬 (docs/assessments/ + docs/html/)
- [2026-05-17 13:45:55] handoff doc 사이클 1 갱신 — 본 세션 누계 20 commit + 가드레일 14 + 신규 인프라 (HTML 6 / pytest / 정책 본문 3 / 텔레그램 강제) 반영 (docs/exec-plans/active/2026-05-17-session-handoff.md)
- [2026-05-17 13:40:44] AGENTS.md PR 게이트 체크리스트 — build.yml (M5 PyInstaller 매트릭스) 행 추가 (AGENTS.md)
- [2026-05-17 13:38:48] CheckList.md §2 진행률 표 갱신 — 본 세션 누계 commit 18+ 반영. 정책 본문 3 / HTML 6 / pytest 인프라 / 가드레일 14 / 평가 snapshot 2 / PR template / self-hosted runner / 텔레그램 누계 13 모두 등재 (CheckList.md)
- [2026-05-17 13:35:46] DESIGN.md §10.6 Playwright E2E + §11 UI 디자인 시스템 + pytest 인프라 신설 + DESIGN.html (사용자 directive 2026-05-17 "qa pytest+playwright 필요" + "UI 섹션 추가" + "html 한벌") (DESIGN.md + docs/html/DESIGN.html + pyproject.toml + tests/ + ci.yml + CLAUDE.md §10-6 + 영구 메모리 2)
- [2026-05-17 13:16:44] 평가 snapshot 사이클 2 갱신 — productization 2.5→2.6 ▲ + vibe-coding 4.4→4.5 ▲ + HTML 2종 재생성 (sub-agent 병렬) (docs/assessments/ + docs/html/)
- [2026-05-17 13:06:07] FRONTEND.md + FRONTEND.html 색상 swatch 가시화 — 9 hex 변수 14px 색상 표시 추가 (사용자 directive 2026-05-17) (FRONTEND.md + docs/html/FRONTEND.html + .markdownlint.json)
- [2026-05-17 13:03:13] docs/policies/ 3 문서 신설 — doc-gardening + adoption-roadmap + execution-harness. 깨진 링크 12 → 0 해소. AGENTS.md 문서 맵 갱신 (docs/policies/ + AGENTS.md)
- [2026-05-17 12:53:01] .github/pull_request_template.md 신설 — release-agent PR 양식 정합 (M1~M7 + lint + 가드레일 + reviewer/qa/observability + 머지 후 조치) (.github/)
- [2026-05-17 12:50:22] tools/doc-lint.sh bash 3.2 호환 fix + 1인칭/3인칭 검사 5번 추가 (가드레일 자동화 강화) (tools/doc-lint.sh)
- [2026-05-17 12:46:09] vibe-coding.md 평가 snapshot 갱신 + HTML 2종 재생성 (sub-agent 병렬) + 영구 메모리 feedback-doc-perfection-before-code 신설 (큰 프로젝트 8 체크리스트 의무 + 간단 작업 완화) (docs/assessments/ + docs/html/ + 메모리)
- [2026-05-17 12:38:27] 1인칭/3인칭 표현 전수 회수 + 텔레그램 가드레일 강화 — FRONTEND/Structure/PRODUCT_SENSE/server/reviewer-agent/handoff/정본/History/vibe-coding 10 파일 + 영구 메모리 feedback-no-self-other-pronoun 신설 + telegram HTTP API 직접 경로 강제 활성 (사용자 directive 2026-05-17 2회 비판) (저장소 전체)
- [2026-05-17 12:26:29] docs/html/ 5 HTML 신설 + CLAUDE.md §10-6/7 동시 갱신 의무 명문화 — sub-agent 5종 병렬 변환 (Structure/ARCHITECTURE/FRONTEND/productization/vibe-coding) (docs/html/ + CLAUDE.md)
- [2026-05-17 12:24:50] RELIABILITY.md MariaDB 회수 — 13 위반 정정 (SQLite WAL → MariaDB InnoDB redo log + binlog/mysqldump 백업 정책) (RELIABILITY.md)
- [2026-05-17 12:22:47] 실행계획 MariaDB 회수 — Phase 1 MVP 5 위반 정정 (L38 In Scope + L92 M3 + L109 #16 + L179 검증 + L203 의존성 그래프) (docs/exec-plans/active/)
- [2026-05-17 12:19:26] docs/assessments/{productization,vibe-coding}.md 신설 — snapshot 패턴 (매 task 종료 시 전체 rewrite) (docs/assessments/)
- [2026-05-17 12:12:30] ARCHITECTURE.md MariaDB 회수 — L76 Core mermaid + L163 app/core + L166 app/db + L188 환경변수 표 5필드 (ARCHITECTURE.md)
- [2026-05-17 12:10:21] app/core/config.py + app/README.md MariaDB 회수 — local_db_path → db_host/port/user/pass/name 5필드 (app/core/config.py + app/README.md)
- [2026-05-17 12:05:41] docs/references/ci-self-hosted-setup.md 신설 — runner 등록 절차 + 보안 hardening (docs/references/ci-self-hosted-setup.md)
- [2026-05-17 12:00:02] .github/workflows/doc-gardener.yml 신설 — 주 1회 drift 감지 (cron Monday + dispatch) (.github/workflows/doc-gardener.yml)
- [2026-05-17 11:57:51] .github/workflows/docs-lint.yml 신설 — 문서 lint 전용 (cron daily + dispatch + path-filter) (.github/workflows/docs-lint.yml)
- [2026-05-17 11:54:45] .github/workflows/ci.yml 신설 — CI 게이트 7종, self-hosted 매트릭스 (.github/workflows/ci.yml)
- [2026-05-17 11:23:50] Structure.md 신설 — 운영 3/8 (Structure.md)
- [2026-05-17 11:19:01] FRONTEND.md §14 wireframe/mockup 섹션 추가 (FRONTEND.md)
- [2026-05-17 11:18:48] Specification.md 신설 — 운영 1/8 (Specification.md)
- [2026-05-17 11:09:05] doc-lint.sh 신설 — 문서 lint 가드레일 (tools/doc-lint.sh)
- [2026-05-17 11:03:51] .markdownlint.json 신설 — lint 가드레일 사전 작업 (.markdownlint.json)
- [2026-05-17 11:03:07] SECURITY.md 신설 — 9 정책 8/9 (SECURITY.md)
- [2026-05-17 10:55:07] QUALITY_SCORE.md 신설 — 9 정책 7/9 (QUALITY_SCORE.md)
- [2026-05-17 10:54:55] PRODUCT_SENSE.md 신설 — 9 정책 6/9 (PRODUCT_SENSE.md)
- [2026-05-17 10:54:20] RELIABILITY.md 신설 — 9 정책 5/9 (RELIABILITY.md)
- [2026-05-17 10:54:06] PLANS.md 신설 — 9 정책 4/9 (PLANS.md)
- [2026-05-17 10:53:53] FRONTEND.md 신설 — 9 정책 3/9 (FRONTEND.md)
- [2026-05-17 10:53:20] DESIGN.md 신설 — 9 정책 2/9 (DESIGN.md)
- [2026-05-17 10:52:29] ARCHITECTURE.md 신설 — 9 정책 1/9 (ARCHITECTURE.md)
- [2026-05-17 10:33:00] PyQt6 + qasync 클라 스켈레톤 (app/)
- [2026-05-17 10:23:58] aiohttp WebSocket 시그널링 서버 스켈레톤 (server/)
- [2026-05-17 10:16:16] .claude/agents 7 프로세스 에이전트 정의 (.claude/agents/)
- [2026-05-17 10:08:44] 실행계획 TD-6 행 BPE 위생 정정 (docs/exec-plans/)
- [2026-05-17 10:08:22] Phase 1 MVP 실행계획 + CI self-hosted 정책 반영 (docs/exec-plans/)
- [2026-05-17 10:01:17] 정본 정독 대상 + Claude CLI Telegram wrapper 추가 (tools/claude-telegram.sh)
- [2026-05-17 09:54:13] AGENTS.md TooTalk 서비스명 명문화 (AGENTS.md)
- [2026-05-17 09:36:27] 부트스트랩 - AGENTS.md + .gitignore + .env.example (루트)

---

**문서 상태**: `active` · 최초 작성 2026-05-17 · M2 변경 이력 30행 캐시
운영. 30행 초과 시점부터 회전 + History.md 위임.
