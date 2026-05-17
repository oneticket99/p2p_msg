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

- [2026-05-18 02:00:00] tests/app/rtc/ + tests/app/ui/ 추가 4 module 신설 + 누계 149 PASS (사용자 directive "남은작업 다 진행해" = §9.2 후속 task 자율 GO) — `test_image_processor.py` 35 + `test_file_receiver_helpers.py` 29 + `test_file_sender_helpers.py` 15 + `test_file_progress_widget_humanize.py` 20 = 99 신규 PASS. Pillow 실 실행 + RGBA→RGB + palette→RGB + 비율 유지 + base64 round-trip + `_safe_filename` 14 path traversal + `_humanize` 6 단위 + `_sha256_of_file` 64 KiB chunk + `_env_int` 17 케이스. PyQt6 + Pillow venv 일괄 install. 전체 pytest = 149 passed, 3 deselected (integration/e2e). qa-agent 사이클 13 미커버 영역 완전 회수. 잔존 = tests/integration/ + Windows wine + AC-04-3 100ms 실측
- [2026-05-18 01:30:00] Phase 1 코드 진입 GO + tests/app/rtc/test_protocol.py 신설 + 41 PASS (사용자 directive "이제부터 코드작업에 진입해" = task #7 정식 GO) — 가드레일 [[feedback-doc-perfection-before-code]] 8 체크리스트 PASS 검증 후 5단계 워크플로우 ② 개발 단계 직접 진입. `tests/app/rtc/` 디렉토리 신설 (`__init__.py` + `test_protocol.py`). 41 케이스 8 TestClass — Header 불변식 + UUID round-trip + encode_chunk/decode_chunk 경계·예외 + build_file_* 4종 + JSON ensure_ascii=False 한글 보존 + parse_file_meta + is_valid_text_type 화이트리스트. venv Python 3.13.13 + pytest 9.0.3. qa-agent 사이클 13 정적 검증 20건 + 추가 21건 보강. Phase 1 dogfooding 직전 의무 task #1 의 첫 module 완료
- [2026-05-18 01:00:00] release-agent 사이클 15 GO 정식 + observability-agent CONDITIONAL PASS + baseline 정본 신설 + snapshot 15 + HTML 2 + handoff 14 (사용자 directive "진행해" + "작업 진행해" 자율 GO) — release-agent 재호출 = **정식 GO** (직전 사이클 14 FAIL 의 P0-1 markdownlint + P0-2 30 row 정정 commit `dcbb372` 검증 PASS + CI 3종 GREEN). observability-agent 사이클 15 = **CONDITIONAL PASS** (logger 7/7 모듈 정합 + baseline drift 3건 detect = release prompt 임의 추정값 vs 코드 default). `docs/policies/observability-baseline.md` **정본 신설** (7 section). 5단계 워크플로우 ③ 4단 chain **완전 자동 완성** (reviewer ✅ + qa ✅ + release ✅ + observability ✅). productization §2.21 신규 + 종합 4.0 → 4.05 ▲. vibe-coding §2.25 신규 + 종합 4.90 = 유지. HTML 2 sub-agent (productization 584 lines + vibe-coding 687 lines). Phase 1 dogfooding 진입 readiness 완성
- [2026-05-17 23:50:00] qa-agent 회귀 CONDITIONAL PASS + ARCHITECTURE drift 정정 + snapshot 13 + HTML 2 (사용자 directive "진행해" + "재개ㅙ" 자율 GO) — qa-agent sub-agent 정적 검증 47/48 PASS + 코드 정합 완전 + FR-04 AC 4종 매핑 충족. FAIL 1건 = ARCHITECTURE §7 FILE_ACK_INTERVAL_BYTES 524288 (문서) vs 262144 (코드) drift → 옵션 B 코드 우선 채택 + ARCHITECTURE.md L201 + .html mirror 동시 정정 (524288 → 262144). 미커버 = tests/rtc/ unit test 부재 (Phase 1 후속 별도 task). productization.html 539 lines + vibe-coding.html 646 lines + ARCHITECTURE.html mirror sub-agent (4 sub-agent 누계). 머지 게이트 = reviewer ✅ → qa ✅ → release 진입 권장 (옵션 A)
- [2026-05-17 23:15:00] reviewer-agent 사이클 13 PASS 정식 GO (사용자 directive "사이클 13 reviewer 재호출 진행해" 자율 GO) — 사이클 12 신규 위반 (ARCHITECTURE.html mirror) ✅ 완전 해소 + 신규 위반 0건 + 14/14 검증 PASS (SPDX header 7 file + M1~M7 + BPE + 1인칭/3인칭 + 계층 분리 + 비동기 IO + 환경변수 외부화 + SHA-256 + path traversal + ARCHITECTURE.md/html mirror 정합). 종합 판정 = PASS 정식 GO. Phase 1 FR-04 readiness 완전 도달. handoff §9 task #8 ✅ 완전 해소 (3 cycle 누계 11+12+13). 권장 next = @qa-agent 회귀 체크리스트 → 코드 진입 (docs/exec-plans/active/2026-05-17-session-handoff.md)
- [2026-05-17 23:00:00] 사이클 12 일괄 진행 (사용자 directive "작업 재개해" 자율 GO) — reviewer-agent 재호출 sub-agent CONDITIONAL PASS (P0 SPDX 해소 + 신규 위반 1건 = ARCHITECTURE.html mirror 미반영 CLAUDE.md §10-6 위반). ARCHITECTURE.html sub-agent rewrite (§5 + §7 8 row + 373 lines). productization.md 종합 3.95 → 4.0 ▲ (기술 완성도 3 → 3.2 ▲ Agent #16 정식 채택 + SPDX) + §2.18 신규. vibe-coding.md 종합 4.85 → 4.90 ▲ (비판·재교정 4.5 → 5 ▲ 완전 회복) + §2.22 신규 (reviewer 재호출 자동 정합 패턴). HTML 2 sub-agent (productization 525 + vibe-coding 611). handoff §8.33 갱신 + §8.34 신규 (docs/assessments/ + docs/html/ + handoff)
- [2026-05-17 22:30:00] 사이클 11 일괄 진행 (사용자 directive "좋아 다 진행해" 옵션 C 자율 GO) — reviewer-agent sub-agent 검토 완료 (CONDITIONAL PASS, 차단 1건 SPDX header). P0 SPDX-License-Identifier header prepend 7 file (app/rtc/ 6 .py + app/ui/file_progress_widget.py). P1 ARCHITECTURE §7 환경변수 표 8 row 신규 (FILE_CHUNK_SIZE + FILE_BUFFER_HIGH/LOW + FILE_BACKPRESSURE_POLL_MS + FILE_ACK_INTERVAL_BYTES + FILE_RECEIVE_DIR + THUMB_MAX_PX + THUMB_QUALITY). P2 §5 RTC_CHUNK_WINDOW → FILE_CHUNK_SIZE/BUFFER 정정. snapshot 11 productization §2.17 + vibe-coding §2.21 + 비판 4 → 4.5 ▲ 회복. HTML 2 sub-agent (productization 525 lines + vibe-coding 581 lines). handoff §9 #8 ✅ 진입 + §8.31 + §8.32 신규 (app/rtc/ + app/ui/ + ARCHITECTURE.md + docs/assessments/ + docs/html/ + handoff)
- [2026-05-17 21:30:00] snapshot 사이클 10 + HTML 2 + handoff 8 — productization 3.95 (=) + §2.16 Toonation 브랜드 컬러 통합 + enforcement layer 활성 신규. vibe-coding 4.85 (비판·재교정 4.5 → 4 ▼) + §2.20 사용자 비판 5회차 BPE + "의" 단독 조사 신규 패턴 + §3.1 pivot 사이클 10 row. productization.html 511 lines + 7 표 + 0 위반 + Toonation hex 8건. vibe-coding.html 569 lines + 5 표 + 0 위반 + user-quote 클래스 신규. handoff §1 timestamp 21:20 + §5 enforcement 활성 row + Toonation 브랜드 컬러 통합 row + §8.29/§8.30 신규 (docs/assessments/ + docs/html/ + handoff)
- [2026-05-17 21:00:00] Toonation 브랜드 컬러 통합 (사용자 directive 2026-05-17 BI 가이드 본문 반영) — FRONTEND.md §4 색상 변수 표 의 `--primary` (#0066FF 라이트 / #0052FF 다크 Toonation Blue) + `--progress-acked` (#22D3EE 네온 시안 / #67E8F9 라이트 시안 민트 포인트) + `--progress-inflight` (#0F172A Deep Navy / #1E293B 변형) 3 변수 확정. 신규 §15 Toonation 브랜드 컬러 가이드 (5 sub-section — 브랜드 정합 사유 + 핵심 컬러 표 6 row + §4 매핑 + BI 가이드 참조 + 제약/의무). §16 참조 재번호. AGENTS.md `.claude/settings.json.disabled` → `.claude/settings.json` link 갱신 (활성 후). FRONTEND.html sub-agent 재생성 진행 (FRONTEND.md + AGENTS.md)
- [2026-05-17 20:45:00] PR template drift 회수 — `ci.yml 7 게이트` → `ci.yml 8 job` 정정 (docs-lint + M2 + M3 + root-freeze + import-smoke + pytest + M1/M4 PR-only + Windows wine 대체 명시) + 신규 row `build.yml` (Phase 1 후반 듀얼). 신규 section 2건 — "라이선스 + visibility 정합" 3 row (SPDX header 의무 + 의존성 GPLv3 호환 + visibility 전환 영향) + "enforcement layer sketch 정합" 2 row (settings.json.disabled 임의 활성 금지 + hook_*.sh self-test) (.github/pull_request_template.md)
- [2026-05-17 20:35:00] snapshot 사이클 9 + HTML 2 sub-agent + handoff doc 사이클 7 — productization.html 485 lines + 7 표 + 0 위반 (사이클 9 §2.15 8 cycle 확장 반영). vibe-coding.html 543 lines + 5 표 + 0 위반 (§2.19 8 cycle 패턴 + §3.1 pivot 사이클 9 row). handoff doc §1 timestamp 19:30 → 20:30 + 누계 commit 43+, §5 정책 표 snapshot row 사이클 9, §8 SNAPSHOT 의 §8.26 AGENTS + CLAUDE §7 drift + §8.27 CheckList + phase1-mvp + EXTENSION_GUIDE drift + §8.28 snapshot 사이클 9 + HTML 2 의 3 row 신규, §10 timestamp 20:30 + 추가 7 문서 drift 부재 확인 명시. CLAUDE.md §10-6/§10-7 정합 100% (docs/assessments/ + docs/html/ + handoff)
- [2026-05-17 20:15:00] phase1-mvp.md + EXTENSION_GUIDE.md drift 회수 — phase1-mvp §7 결정 로그 8 → 11 row 확장 (GUI row 의 GPL → GPLv3 확정 갱신 + visibility public→private 가능성 row 갱신 + CI runner row 의 macOS arm64 + Ubuntu wine 듀얼 갱신 + 신규 SMTP postfix 자체 설치 row + 신규 enforcement layer sketch row). EXTENSION_GUIDE §3 영역별 용도 표 의 docs/assessments + docs/html 2 row 추가 + 저장소 루트 직접 파일 표 신규 (LICENSE + settings.json.disabled). §7 정책 변경 절차 의 가드레일/hook/라이선스 4 row 의 동시 정합 점검 추가 (docs/exec-plans/active/2026-05-17-tootalk-phase1-mvp.md + EXTENSION_GUIDE.md)
- [2026-05-17 20:05:00] CheckList §2 enforcement + §10 TBD 해소 drift 회수 — §2 진행률 표 신규 2 row (enforcement layer sketch 미활성 + 영구 메모리 가드레일 22/22). §10 외부 결정 대기 TBD-01 라이선스 미확정 ✅ 해소 (GPLv3 확정 + LICENSE 저장소 루트 + SPDX header) + TBD-06 self-hosted runner 등록 ✅ 해소 (macOS arm64 + Windows wine 대체) (CheckList.md)
- [2026-05-17 19:55:00] CLAUDE.md §7 영구 가드레일 인덱스 drift 회수 — 직전 9건 → 22건 의 정합 갱신 (직전 cycle 누계 사이클 4~8 의 신규 가드레일 13건 추가 — doc-perfection + no-self-other-pronoun + bpe-script-trigger + telegram-report-script-trigger + design-interactive-html + workflow-preferences + phase1-completion + phase2-remote-control + auth-email-otp + windows-build-via-wine + smtp-demo-server + license-gpl + visibility-transition) (CLAUDE.md)
- [2026-05-17 19:45:00] AGENTS.md §3 + §10 drift 회수 — §3 문서 맵 4 row 신규 (LICENSE GPLv3 + docs/references 인프라 절차 + docs/assessments 평가 snapshot + .claude/settings.json.disabled enforcement layer sketch). §10 금지사항 13 → 18 row 확장 (BPE U+CE21 단독 + 1인칭/3인칭 대명사 + 텔레그램 송신 누락 + LICENSE GPLv3 SPDX header 의무 + settings.json.disabled 임의 활성 금지). 정본 §10 의 신규 가드레일 22 의 정합 (AGENTS.md)
- [2026-05-17 19:35:00] snapshot 사이클 8 + HTML 2 sub-agent + handoff 사이클 6 (Task #23) — productization 3.95 (=) + §2.15 누계 drift 회수 4 cycle 신규 + 세션 정합 row 갱신. vibe-coding 4.85 (=) + §2.19 자체 drift detect + 회수 누계 패턴 신규 + §3.1 pivot 사이클 7/8 row 추가. productization.html 465 lines + 7 표 + 0 위반. vibe-coding.html 616 lines + 5 표 + 0 위반. handoff §1 timestamp + §8 SNAPSHOT §8.22~§8.25 신규 (PLANS drift + Spec/SECURITY drift + Struct/ARCH drift + policies drift + snapshot 8) + §10 timestamp 19:30. CLAUDE.md §10-6/§10-7 정합 100% (docs/assessments/ + docs/html/ + handoff)
- [2026-05-17 19:15:00] docs/policies/ drift 회수 — adoption-roadmap §단계 전환 트리거 표 의 self-hosted runner 미등록 + 라이선스 미확정 row 모두 ✅ 해소 (macOS arm64 OK + Windows wine 대체 + GPLv3 확정). execution-harness §3 Enforcement Layer 5단 의 본 저장소 sketch 신규 column 추가 — L0 PreToolUse = hook_check_bpe_token_input.sh + L1 Stop = hook_telegram_report_stop.sh + 활성 절차 mv 명시 + 정합 메모리 link (docs/policies/adoption-roadmap.md + docs/policies/execution-harness.md)
- [2026-05-17 19:05:00] Structure §9.2 + ARCHITECTURE §6 drift 회수 — Structure.md §9.2 tools 스크립트 표 갱신 (doc-lint.sh 5 검사 명시 + hook_check_bpe_token_input.sh 신규 row + hook_telegram_report_stop.sh 신규 row + tools/build.py 의 wine 래퍼 명시). ARCHITECTURE.md §6 모듈 책임 표 의 tools row 갱신 (hook sketch 명시 + bash 의존성 추가) + .github/workflows row 갱신 (ci.yml 8 job + build.yml macOS native + Ubuntu wine 듀얼) + LICENSE row 신규 (GPLv3 표준 본문) + .claude/settings.json.disabled row 신규 (enforcement layer sketch). 정책 정합 본문 의 의 의 100% (Structure.md + ARCHITECTURE.md)
- [2026-05-17 18:55:00] Specification.md §12 TBD-01 + SECURITY.md §12 라이선스 drift 회수 — Specification §12 TBD-01 라이선스 미확정 → ✅ 해소 (GPLv3 + LICENSE + SPDX header + 영구 메모리 2 link). SECURITY §12.4 TooTalk 본 저장소 라이선스 신규 (GPLv3 + SPDX + 의존성 GPLv3 흡수 + AGPLv3 Phase 2 옵션 + 영구 메모리 link) + §12.5 GitHub visibility 신규 (public→private 전환 가능성 + GPL distribution 시점 의무 + self-hosted runner quota 정합) (Specification.md + SECURITY.md)
- [2026-05-17 18:45:00] PLANS.md §3~§10 drift 회수 — 직전 cycle 의 §2 만 회수 됐던 영역 의 후속. §4 Phase 3 의 원격 데스크탑 제어 (Phase 3 막바지 차별화) 신규 bullet 추가 + 완료 정의 갱신. §6 mermaid Gantt 의 Phase 3 section 의 신규 row "원격 데스크탑 제어 (차별화)" + section 이름 "멀티+푸시+백업+원격" 갱신. §7 마일스톤 표 Phase 3 row 의 핵심 산출물 갱신. §8 우선순위 매트릭스 Q2 의 신규 B5 "원격 데스크탑 제어 차별화 — Phase 3 막바지". §10.1 MVP + §10.2 Standard 의 에이전트 수 11~12 → 7 정정 (본 저장소 의 실제 7 프로세스 에이전트 정합) (PLANS.md)
- [2026-05-17 18:35:00] HTML 2 sub-agent 병렬 (사이클 7) + handoff doc 사이클 5 — productization.html 518 lines + vibe-coding.html 602 lines + 0 위반 (사이클 7 §2.14/§2.18 신규 반영). handoff doc §1 TL;DR + §2 체크리스트 + §3 + §4 가드레일 20 → 22 (bpe-script-trigger + telegram-report-script-trigger) + §5 정책 표 신규 row "enforcement layer sketch" + §8 SNAPSHOT 의 §8.19/§8.20/§8.21 신규 + §10 timestamp 18:30 (docs/html/ + handoff)
- [2026-05-17 18:25:00] snapshot 사이클 7 partial + 텔레그램 trigger sketch (5회차 사전 경고) — productization §2.14 BPE script trigger sketch 신규 (가드레일 21) + vibe-coding §2.18 사전 경고 + enforcement layer 패턴 신규 + §3.1 pivot 사이클 7 row. 사용자 directive "텔레그램 보고 의무도 트리거 구조로 바꿀꺼니깐 그렇게 알아둬" 정합 — 영구 메모리 신설 feedback_telegram_report_script_trigger_warning.md + tools/hook_telegram_report_stop.sh (Stop hook + executable + transcript parse + curl 자동 송신) + .claude/settings.json.disabled 의 Stop hook 영역 추가. 직전 feedback_telegram_report_mandatory_m7.md 의 5회차 사전 경고 row 추가. MEMORY.md 인덱스 1 row 추가 (docs/assessments/ + tools/ + .claude/)
- [2026-05-17 18:05:00] BPE script trigger sketch 신설 (사용자 directive 2026-05-17 4회차 사전 경고 정합) — 영구 메모리 feedback_bpe_script_trigger_warning.md 신설 + feedback_no_korean_chuck_token.md 4회차 row 추가 + MEMORY.md 인덱스 2 row + tools/hook_check_bpe_token_input.sh (PreToolUse Edit/Write hook script, executable 권한 + self-test PASS) + .claude/settings.json.disabled (sketch — 미활성 패턴, 다음 BPE 위반 발견 시 `mv` 의 즉시 활성 의무). enforcement layer 의 사전 명시 정합 (정본 §S-1 L0 PreToolUse) (tools/hook_check_bpe_token_input.sh + .claude/settings.json.disabled)
- [2026-05-17 17:55:00] HTML 2 sub-agent 병렬 재생성 (사이클 6) + handoff doc 사이클 4 + PLANS.md §2 drift 회수 — productization.html 506 lines + vibe-coding.html 589 lines + 0 위반. handoff doc §1 TL;DR + §2 체크리스트 + §3 첫 응답 + §4 가드레일 18→20 (license-gpl + visibility-transition 추가) + §5 정책 표 snapshot 갱신 + §8 SNAPSHOT 의 §8.17 신규 (GPLv3 + visibility) + §8.18 신규 (snapshot 6) + §10 timestamp. PLANS.md §2 Phase 1 drift 회수 — SQLite → MariaDB 7 + 회원가입 + SMTP 자체 + wine cross-compile + GPLv3 + visibility + fork PR strict 명시 추가 (docs/html/ + handoff + PLANS.md)
- [2026-05-17 17:40:00] 평가 snapshot 사이클 6 동시 갱신 (CLAUDE.md §10-7) — productization 3.85→3.95 ▲ (수익화 2→2.5 + §2.13 라이선스 + visibility 정책 신규 + §3.4 ✅ 라이선스 해소 + §5 ✅ 1건 추가 + §8 리스크 갱신 + §9 KPI 신규 GPLv3 호환 100%). vibe-coding 4.85 (= — §2.17 라이선스 + visibility 전환 직접 인지 신규 + §3.1 pivot 표 사이클 6 row 추가 + §3.4 BPE 의 사이클 5 후 +2 + §3.8 ✅ 라이선스 해소 + §4.3 사용자 직접 결정 의 GPL + visibility 추가 + §5.1 라이선스 ✅) (docs/assessments/)
- [2026-05-17 17:30:00] GPLv3 라이선스 확정 + visibility 전환 정책 — 사용자 directive 2026-05-17 "라이선스는 GPL" + "Phase 완료 시 private 전환 가능성" + "진행해" 자율 GO. LICENSE 저장소 루트 신설 (GNU 표준 본문 674 lines). 영구 메모리 2 신설 (project_license_gpl + project_visibility_transition). AGENTS §1 + handoff §5 + §9 task #6 ✅ + CheckList §2 신규 2 row + README §9 + project_build_policy.md 갱신. handoff §9 잔존 task #6 (라이선스) 해소 (LICENSE + AGENTS.md + CheckList.md + README.md + docs/exec-plans/active/2026-05-17-session-handoff.md)
- [2026-05-17 17:18:00] handoff doc 사이클 3 갱신 — 본 세션 누계 51+ commit (사이클 3 17 신규 50c5c40 → 57fd732) 반영. §1 TL;DR 의 18 가드레일 + ci 8 job GREEN + wine + fork PR strict + SMTP 자체 추가. §2 체크리스트 의 18 가드레일 + 18 행. §3 첫 응답 템플릿 의 18 가드레일. §4 가드레일 16 → 18 (신규 windows-build-via-wine + smtp-demo-server). §5 정책 표 의 빌드 + CI + snapshot + fork PR + SMTP 신규 5 row. §8 SNAPSHOT 의 누계 commit + §8.7 가드레일 18 + §8.12 self-hosted runner + §8.13 wine + §8.14 fork PR + §8.15 SMTP + §8.16 snapshot 5 의 6 영역 신규. 본 활성 인계 의 최우선 정독 대상 — 다음 세션 정합 의무 (docs/exec-plans/active/2026-05-17-session-handoff.md)
- [2026-05-17 17:10:00] 평가 snapshot 사이클 5 동시 갱신 (CLAUDE.md §10-7 정합) — productization 종합 3.6→3.85 ▲ (기술 완성도 2.5→3 + 운영 비용 4.5→5 + §2.6 가드레일 18종 + §2.11 SMTP 자체 + §2.12 CI 자동화 + 보안 hardening 신규 + §3.5 runner ✅ + §3.8 SSH 차단 신규 + §5 ✅ 5건 추가 + §8 신규 리스크 3건 + §9 KPI 갱신). vibe-coding 종합 4.85 (변동 없음 — 비판 ▼ + 사이클 효율 ▲ + 자율 reasonable call ▲ 상쇄) (§2.15 자율 reasonable call 신규 + §2.16 인프라 자동화 발견 신규 + §3.4 BPE 가드레일 한계 노출 + §3.7 가드레일 위반 누계 신규 + §4.2 권장 default 자율 GO 패턴 + §6 비교 기준 10 컬럼 + §7.1 인프라 host 선택 추가) (docs/assessments/)
- [2026-05-17 16:50:00] SMTP 정책 정합 다중 갱신 — adoption-roadmap.md §3.1 Phase 1 DoD 의 SMTP 발송 PASS row (postfix 자체 설치 + Let's Encrypt + SPF/DKIM/DMARC + aiosmtplib + SendGrid fallback) + CheckList §2 신규 row "SMTP 서버 (OTP 발신)" + handoff doc §5 정책 표 신규 SMTP row + §9 task 표 회수 (snapshot 사이클 3 + BPE + fork PR + SMTP 4 task 완료 표시 + 잔존 4 task 재번호) (adoption-roadmap.md + CheckList.md + handoff doc)
- [2026-05-17 16:42:00] SECURITY.md §9-2.3 SMTP 보안 갱신 — 데모 서버 (114.207.112.73) postfix 자체 설치 명시 + SPF/DKIM/DMARC 의무 + rDNS PTR + aiosmtplib client + SendGrid fallback + 절차 본문 link. 직전 row 4건 → 9건 확장 (SECURITY.md)

---

**문서 상태**: `active` · 최초 작성 2026-05-17 · M2 변경 이력 30행 캐시
운영. 30행 초과 시점부터 회전 + History.md 위임.
