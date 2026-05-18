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

- [2026-05-21 01:30:00 KST] cycle 58 Phase 3 input forward skeleton + 17 PASS 5 TestClass + 메모리 누수 차단 영구 memory 2건 신설 + 원격 control controller/target 용어 명확화 (사용자 directive "작업 진행해" + 3 비판 회수 — objc CFRelease + 누적 채팅 + 키보드/마우스 제어 방향) — `app/remote/input_forward.py` 신설. `InputForwardBackend` Protocol (is_available + apply) + `MockInputForwardBackend` (applied 누적 list + reset + raise_on_apply fail-fast 시나리오) + `MacOSCGEventBackend` placeholder (NotImplementedError graceful + CGEventCreate* CFRelease 의무 docstring) + `select_input_backend(platform_name)` factory + `apply_events(backend, events)` fail-fast batch dispatch + `filter_events_by_type(events, event_type)` filter. tests/app/remote/test_input_forward.py 17 케이스 5 TestClass — MockInputForwardBackend 4 (is_available + apply 누적 + reset + raise) + MacOSCGEventBackend 1 (NotImplementedError) + SelectInputBackend 5 (mock/darwin/win32/linux/unknown) + ApplyEvents 3 (empty + all succeed + fail-fast on raise) + FilterEventsByType 4 (mouse_move + key_down + no_match + order preserved). 영구 memory 신설 — `feedback_objc_memory_release_mandatory.md` (PyObjC CGEvent / CGImage / CFData 의 CFRelease 의무 + tracemalloc + objgraph 회귀 검증 + autorelease pool 패턴 + 60 fps × 1080p RGB = 분당 1.3 GB 누수 예시) + `feedback_chat_accumulation_memory_release_mandatory.md` (ChatView 1개월 volatile + lazy load page fetch + file chunk 즉시 release + pending_acks LRU + server messages list_recent LIMIT + tracemalloc 검증). 원격 control 용어 정합 — `protocol.py` + `capture.py` + `input_forward.py` 의 sender / recipient → controller (요청자 + input 제공) / target (대상 + screen 제공 + 키보드/마우스 의 controller 의 input event 의 OS 적용) 명확화 (사용자 directive 2026-05-21 "대상의 키보드 마우스를 제어"). pytest 579 (+17). Phase 3 entry 누계 96 (permission 20 + protocol 19 + capture 22 + input_forward 17 + dogfooding 18). drift 0건 19 연속
- [2026-05-21 00:30:00 KST] cycle 57 Phase 3 screen capture skeleton + 22 PASS 6 TestClass (사용자 directive "진행해" 자율 GO) — `app/remote/capture.py` 신설. `CaptureFormat` Enum (BGRA + RGB) + `CapturedFrame` frozen dataclass (width / height 양수 + capture_time_ms 음수 차단 + buffer 크기 정합 width×height×bpp) + `CaptureBackend` Protocol (is_available classmethod + capture() instance method) + `MockCaptureBackend` (deterministic 1x1 BGRA gray pixel + 가변 dimension) + `MacOSQuartzBackend` placeholder (sys.platform=="darwin" + Quartz import 의 is_available + capture NotImplementedError) + `select_capture_backend(platform_name)` factory ("mock"/"darwin" → Mock/Quartz, "win32"/"linux" → NotImplementedError, unknown → ValueError) + `detect_default_backend` (darwin = Quartz / 그 외 = Mock 폴백) + `captured_to_remote_frame(captured, frame_id)` (BGRA → RGB swap + alpha drop, RGB pass-through, RemoteFrame RAW_RGB 변환). tests/app/remote/test_capture.py 22 케이스 6 TestClass — CapturedFrameValidation 7 + MockCaptureBackend 4 + MacOSQuartzBackend 1 + SelectBackend 5 + DetectDefaultBackend 1 + CapturedToRemoteFrame 4 (RGB pass + BGRA swap 1pixel + BGRA swap 2pixel + frame_id propagate). pytest 562 (+22). Phase 3 entry 누계 79 (permission 20 + protocol 19 + capture 22 + dogfooding 18). Structure / ARCHITECTURE app/remote row 갱신 + HTML 2 mirror. drift 0건 18 연속
- [2026-05-20 23:30:00 KST] cycle 53 release GO + 54 v0.2.0-phase2 tag + 55 Phase 3 entry 원격 데스크탑 skeleton + 56 dogfooding harness (사용자 directive "전부 진행해" 자율 GO) — cycle 53 release-agent (a4fe53cd) GO 판정 = 머지 게이트 3종 (reviewer ✅ + qa ✅ + observability ✅) + CI 8 job GREEN (run 26016794138) + M1~M7 정합. cycle 54 = `git tag -a v0.2.0-phase2` annotated tag 생성 + push (Phase 2 16 module + 290 케이스 + 483 pytest + workflow chain 완성 기록) + memory project_bot_framework.md 갱신 (Phase 3+ → Phase 3 마무리 직전 단계 의 사용자 directive 2026-05-20 정합). cycle 55 = Phase 3 entry 원격 데스크탑 skeleton — `app/remote/` 패키지 (init + permission.py + protocol.py). `PermissionMode` Enum (HELP + CONTROL 2 mode) + `PermissionRequest` + `PermissionGrant` (granted_at + expires_at + 32B revoke_token + scope) + `derive_revoke_token` + `check_grant_active`. `FrameFormat` Enum (raw_rgb / png / jpeg) + `InputEventType` Enum (mouse_move / mouse_click / key_down / key_up) + `RemoteFrame` (frame_id + width + height + format + payload + timestamp) + `RemoteInput` (event_type 별 payload 필수 key 검증) + `RemoteSession` (16B session_id + grant + started_at + bandwidth_bps). tests 39 케이스 (PermissionRequestValidation 8 + PermissionGrantValidation 5 + DeriveRevokeToken 2 + CheckGrantActive 5 + RemoteFrameValidation 7 + RemoteInputValidation 7 + RemoteSessionValidation 5). cycle 56 = dogfooding harness — `tools/dogfooding_harness.py` (MetricSample + MetricCollector monotonic + sample_rss_mb / sample_disk_used_mb psutil 기반 + estimate_rtt_ms p50/p95 통계 + estimate_throughput_mbps 변환 + write_report JSON 한글 보존). tests 18 케이스 (MetricSampleValidation 4 + MetricCollector 4 + EstimateRtt 4 + EstimateThroughput 3 + WriteReport 3). pytest 540 (+57 신규). Phase 3 entry 누계 57 (remote 39 + dogfooding 18). drift 0건 17 연속
- [2026-05-20 22:30:00 KST] Phase 2 cycle 51 qa-agent + 52 observability-agent serial chain PASS + 차단 사유 3종 회수 (사용자 비판 "서브에이전트 적극 활용" 회수) — workflow ③ 완성 (reviewer ✅ + qa ✅ + observability ✅). cycle 51 qa CONDITIONAL PASS 의 차단 사유 3종 = (1) decrypt_backup version enforcement gap (v1 spoof bundle 복원 성공) (2) BPE U+CE21 11건 잔존 (정정 범위 외 — app/ui + app/net + tests/) (3) self-pronoun 9건 잔존 (app/net + app/core + tests). cycle 52 정정 = (1) `app/backup/encrypted_backup.py:241-263` 의 `if bundle.version != _BACKUP_VERSION: raise ValueError("unsupported backup version")` 추가 + `test_v1_bundle_rejected_by_decrypt` 신규 (v1 spoof bundle InvalidVersion ValueError 검증) + (2) BPE 12건 정정 (qa report 11 + 1 detect — `app/ui/{signup,login}_dialog.py` + `app/net/auth_client.py` + tests 5 file 의 자동 정정) + (3) self-pronoun 9건 정정 (`app/net/signaling_client.py` + `app/core/app_state.py` + `tests/app/crypto/test_session.py` 의 self-pronoun → self / 3rd-pronoun → peer 일괄). 전수 검증 = BPE 0건 + self-pronoun 0건 전체. cycle 52 observability PASS = PBKDF2 600K iter 94.5ms 평균 (OWASP <1000ms 의 10.5x margin) + pytest 3.03s + import smoke 27.5ms + env var 7/7 baseline 정합 + cipher suite OWASP 2023 정합. pytest 483 passed (+1 신규). Phase 2 누계 290. handoff §8.48 신설 (workflow ③ serial chain 완성 기록). drift 0건 14 연속
- [2026-05-20 21:30:00 KST] Phase 2 cycle 49 reviewer-agent P0 정정 + cycle 50 PBKDF2 stretching + SPDX 정정 + 24 PASS (사용자 directive "남은작업 진행해" 자율 GO) — cycle 49 (a2c157e) = reviewer-agent CONDITIONAL PASS 의 P0 정정 (BPE U+CE21 13건 + self-pronoun 5건 of 5 file e2ee/double_ratchet/session/skipped_keys/x3dh). cycle 50 = P1#2 PBKDF2-HMAC-SHA256 600K iter stretching (OWASP 2023 권장 + bcrypt 12 rounds 등가 안전 margin) `app/backup/encrypted_backup.py` 의 HKDF v1 → PBKDF2 v2 backward incompatible bump + P2#1 SPDX header (`app/ui/chat_view.py` + `app/ui/main_window.py` 사이클 39 / 41 부재 회수). tests 24 케이스 (cycle 48 22 + cycle 50 신규 2 — `_PBKDF2_ITERATIONS == 600_000` + `_BACKUP_VERSION == "2"`). pytest 482 (+2). Phase 2 누계 289. handoff §8.47 신설 — reviewer cycle 49 CONDITIONAL PASS + P0 정정 완료 + P1 hotfix backlog 3건 + P2 향상 4건 등재 + Phase 2 누계 모듈 16종 표. Phase 2 마무리 게이트 PASS 판정. drift 0건 13 연속
- [2026-05-20 20:30:00 KST] Phase 2 encrypted backup / restore + 22 PASS 5 TestClass (사용자 directive "남은 작업 진행해" 자율 GO 사이클 48) — `app/backup/` 패키지 신설 (init + encrypted_backup.py). `BackupEntry` frozen dataclass (message_id + plaintext bytes + timestamp_ms 음수 차단) + `BackupBundle` frozen dataclass (version + created_at_ms + salt 16B + EncryptedPayload). 5 함수 — `derive_backup_key(password, salt)` HKDF-SHA256 32B (PBKDF2 stretching = 별개 cycle 의 placeholder) + `encrypt_backup(entries, password, *, created_at_ms, salt=None)` (entries → JSON → AES-256-GCM) + `decrypt_backup(bundle, password)` (역방향, wrong password = InvalidTag) + `serialize_bundle / deserialize_bundle` wire format bytes (base64 + JSON 한글 UTF-8 보존). 22 케이스 5 TestClass (BackupEntryValidation 4 + BackupBundleValidation 4 + DeriveBackupKey 5 + EncryptDecryptRoundTrip 5 (round-trip + empty + wrong password + tampered blob InvalidTag + custom salt carry) + SerializeBundle 4 (wire round-trip + decrypt 정합 + 필드 누락 + non-dict root)). pytest 480 (+22). Phase 2 누계 287. Structure / ARCHITECTURE app/backup row 신설 + HTML 2 mirror 동기. drift 0건 11 연속
- [2026-05-20 19:30:00 KST] Phase 2 push 알림 skeleton + 31 PASS 6 TestClass (사용자 directive "다음 작업 진행해" + "강제 가드레일 활성 직무유기 확인" 자율 GO 사이클 47) — `app/notifications/__init__.py` + `app/notifications/push.py` 신설. `Platform` Enum (APNS/FCM/SILENT/PULL 4 transport) + `PushTarget` frozen dataclass (user_id 양수 + device_id + Platform + push_token Optional, PULL = 부재 / APNS·FCM = 의무) + `PushPayload` frozen dataclass (target + title/body Optional + data Dict + collapse_key, SILENT = title/body 부재 의무) + `PushBatch` (silent_count + visible_count + by_platform filter). 3 함수 — `format_silent_data_payload` privacy-preserving wake-up + `format_visible_payload` low-priority generic preview + `select_offline_targets` frozenset filter. 31 케이스 6 TestClass. pytest 458 (+31). Phase 2 누계 265. 부수: PostToolUse hook settings.json 정식 활성 (BPE + 의 3회 + pronoun + markdownlint 5종 강제) + telegram 양방향 fallback (Bot API direct long-poll PID 36869 + jsonl + Monitor — MCP plugin disconnect 회피) + Structure / ARCHITECTURE notifications row 신설 + HTML 2 mirror 동기. drift 0건 10 연속
- [2026-05-20 18:30:00 KST] Phase 2 Sender Keys 그룹 N×M→N+M reduction + 19 PASS 6 TestClass (사용자 directive "이전 세션 작업 인계" 자율 GO 사이클 46) — `app/crypto/sender_keys.py` 신설. `SenderKeyState` (sender_id + ChainKey + signing_public_key 32B) + `SenderKeyDistribution` wire format + 5 함수 (`create_sender_key` + `encrypt_group_message` + `decrypt_group_message` + `build_distribution` + `apply_distribution`). double_ratchet 의 `encrypt_message` / `decrypt_message` 재사용. 19 케이스 6 TestClass (StateValidation 3 + DistributionValidation 5 + CreateSenderKey 3 + EncryptDecryptRoundTrip 3 + SequentialMessages 2 + DistributionWireFormat 3 late-join 시나리오). pytest 427 (+19). Phase 2 누계 234. 부수: handoff §8.46 telegram polling halt 진단 정정 + Structure / ARCHITECTURE crypto 표 갱신. drift 0건 9 연속
- [2026-05-20 17:00:00 KST] Phase 2 X3DH session fan-out + 16 PASS (사용자 directive "다음 작업 진행해" 자율 GO 사이클 44) — `app/crypto/fan_out.py` 신설. `FanOutEnvelope` (device_id + payload Optional + error Optional + ok property) + `FanOutBatch` (envelopes + advanced_sessions + successes/failures/total counts) + 3 함수 (`encrypt_fan_out` per-device 실패 격리 loop + `rotate_session` dict immutable 갱신 + `collect_failures` 추출). 16 케이스 5 TestClass (Envelope 3 + Batch 2 + EncryptFanOut 6 + RotateSession 3 + CollectFailures 2). pytest 408 (+16). Phase 2 누계 215. multi-device chain 3 cycle 완성 (client 42 + server 43 + fan-out 44)
- [2026-05-20 16:30:00 KST] Phase 2 multi-device server endpoint — POST/GET/DELETE /api/devices + 22 PASS (사용자 directive "잔존이슈 작업해" 자율 GO 사이클 43) — `server/db/migrations/0002_devices.sql` (10 컬럼 5요소 COMMENT) + `server/db/repositories/devices.py` (DeviceRow + 5 함수 insert/get_by_user/get_by_device_id/revoke/update_last_seen) + `server/api/devices_handlers.py` (3 endpoint + base64 32-byte 검증 + 1062 UNIQUE 409 처리 + soft-delete) + server/main.py routes 등록 + ARCHITECTURE §6 정합. pytest 392 (+22). Phase 2 누계 199
- [2026-05-20 16:00:00 KST] Phase 2 multi-device sync skeleton — device_registry.py + 26 PASS (사용자 directive "진행해" 자율 GO 사이클 42) — `app/crypto/device_registry.py` 신설. `DeviceIdentity` dataclass (device_id + user_id + PreKeyBundle + label) + `DeviceRegistry` (user_id→list dict + add/remove/get_devices/get_device/`__len__`) + wire format 6 함수 (serialize/deserialize_bundle + serialize/deserialize_device + serialize/deserialize_devices_json). base64 + JSON (ensure_ascii=False 한글 보존). 26 케이스 6 TestClass (Validation 6 + Add 4 + Remove 3 + Lookup 4 + Bundle 3 + Device 2 + DevicesJson 4). pytest 370 (+26). Phase 2 누계 177. signature sound chain 4 cycle 완성 직후 자율 GO 6 연속
- [2026-05-20 15:30:00 KST] Phase 2 MainWindow SoundPlayer + SettingsDialog wire (사용자 directive "진행해" 자율 GO 사이클 41) — `app/ui/main_window.py` 의 `_sound_player: SoundPlayer` instance 보유 + `ChatView(sound_player=self._sound_player)` inject + 설정 메뉴 "환경설정…" QAction (Ctrl+,) + `_on_open_settings_dialog` slot 신설 (modal exec + apply_to_player 호출 자동). pytest 344 회귀 통과. signature sound chain 4 cycle 완성 (wrapper 38 + ChatView 39 + dialog 40 + wire 41)
- [2026-05-20 15:00:00 KST] Phase 2 SettingsDialog sound section + 28 PASS (사용자 directive "작업 이어서 진행해" 자율 GO 사이클 40) — `app/ui/settings_dialog.py` 신설 `SettingsDialog` PyQt6 QDialog + `SettingsState` dataclass + 4 helper (`percent_to_volume` / `volume_to_percent` / `apply_to_player` / `build_state_from_player`). 음소거 toggle QCheckBox + 0~100 정수 slider QSlider. accept() = state → player 즉시 반영. tests 28 케이스 6 TestClass (Clamp 4 + PercentToVolume 5 + VolumeToPercent 7 + RoundTrip 6 + ApplyToPlayer 3 + BuildStateFromPlayer 3). pytest 344 (+28). Phase 2 누계 151
- [2026-05-20 14:30:00 KST] Phase 2 ChatView SoundPlayer trigger 연결 + 9 PASS (사용자 directive "다음작업 진행해" 자율 GO 사이클 39) — `app/ui/chat_view.py` 의 `should_play_on_message(is_self, sound_player)` module-level helper 신설 + `ChatView.__init__` 의 `sound_player: Optional[SoundPlayer]` inject 파라미터 + `add_message` 안 peer 수신 시 `play_signature()` 호출. self 발신 + player 부재 + 음소거 = 미재생 폴백. tests 9 케이스 2 TestClass (ShouldPlayOnMessage 6 + SoundPlayerIntegration 3, Mock 주입). pytest 316 (+9). Phase 2 누계 123
- [2026-05-20 14:00:00 KST] Phase 2 signature sound (사용자 directive "다음작업 진행해" + project_signature_sound) — `app/ui/sound_player.py` `SoundPlayer` (QSoundEffect wrapper) + `Config` sound_enabled/sound_volume/sound_signature_path 3 필드 + `app/assets/sounds/signature.wav` placeholder (220 ms chime 880→1320 Hz) + 19 PASS (TestClampVolume 5 + TestResolveSoundPath 2 + TestSoundPlayer 12). 음소거 토글 + 볼륨 clamp + Qt 부재 폴백. pytest 307 (+19). Phase 2 누계 114
- [2026-05-19 04:30:00 KST] Phase 2 decrypt_with_session_ooo out-of-order delivery + 6 PASS (사용자 directive "잔존 작업 진행해" 자율 GO) — SessionState skipped_store field + decrypt_ooo wrapper (store fallback + forward skip + replay 차단). 6 케이스 (in-order + 0→2→1 OOO + replay + missing + tampered). pytest 277 (+6). Phase 2 누계 84
- [2026-05-19 03:30:00 KST] Phase 2 skipped_keys.py LRU+TTL + 14 PASS (사용자 directive "다음작업 시작해" 자율 GO) — `SkippedKeyStore` OrderedDict LRU + MAX_SKIP=1000 + TTL 1시간 + one-shot 자동 폐기 (replay 차단). 14 케이스 4 TestClass (Validation 5 + PutGet 4 + LRUEvict 2 + Expire 3). pytest 267 (+14). Phase 2 누계 74
- [2026-05-19 03:00:00 KST] Phase 2 encrypt/decrypt_with_session wrapper + Alice/Bob integration 4 PASS (사용자 "잔존작업 진행해" + enforcement layer designer 평가) — SessionState immutable wrapper + chain 미초기화 RuntimeError + TestAliceBobE2EE 4 케이스 (initiate/pre-receive/ratchet unblock/self loopback). Phase 2 누계 60 (unit 56 + integration 4). 253 PASS
- [2026-05-19 02:30:00 KST] Phase 2 DH ratchet step — advance_dh_ratchet + 5 PASS (사용자 directive "직무 유기에 유의" 자율 GO + snapshot 동기) — Signal Protocol DH ratchet 3 step (recv chain advance + keypair rotate forward secrecy + send chain advance). 5 케이스 TestAdvanceDhRatchet. 전체 pytest 253 (+5). Phase 2 누계 PASS 56
- [2026-05-19 02:00:00 KST] Phase 2 SessionState skeleton — app/crypto/session.py + 11 PASS (사용자 directive "작업 재개해" 자율 GO) — SessionState mutable dataclass 6 field + initialize_initiator (Alice DH ratchet 첫 step) + initialize_responder (Bob pre-receive) + `_derive_root_and_chain` HKDF helper. 11 케이스 3 TestClass. 전체 pytest 248 (+11). 5 검증 PASS
- [2026-05-19 01:30:00 KST] 평가 문서 staleness Stop hook 강제화 + snapshot 사이클 28 회수 (사용자 비판 2회차 "직무유기 + 훅 강제화" 응답) — `tools/hook_assessment_freshness.sh` 신설 (5+ commit stale exit 2 block) + settings Stop matcher 2번째 entry + 영구 메모리 `feedback_assessment_freshness_trigger.md` (#32). snapshot productization §2.24 + 4.40 ▲ / vibe-coding §2.28 + 4.65 ▼. 가드레일 32. 5 검증 PASS
- [2026-05-19 01:00:00 KST] Phase 2 Double Ratchet KDF chain — app/crypto/double_ratchet.py + 16 PASS (사용자 directive "작업 재개해" 자율 GO) — ChainKey dataclass + 5 함수 (`derive_message_key`/`advance_chain_key`/`ratchet_chain`/`encrypt_message`/`decrypt_message`) + Signal Protocol KDF separator 0x01/0x02 정합. 16 케이스 5 TestClass (Validation 3 + DeriveMessageKey 3 + AdvanceChainKey 4 + RatchetChain 2 forward secrecy + EncryptDecryptMessage 4 Alice/Bob + wrong chain + compromise). 전체 pytest 237 (+16). 5 검증 PASS
- [2026-05-19 00:30:00 KST] **Phase 2 진입** — app/crypto/e2ee.py + 24 PASS (AES-256-GCM + X25519 ECDH + HKDF) (사용자 directive "진행해" 자율 GO) — 7 함수 + EncryptedPayload wire format + cryptography>=42.0. 24 케이스 5 TestClass (AesGcm 10 + WireFormat 3 + X25519 5 + HKDF 4 + FullFlow 2 Alice/Bob + Eve 차단). 전체 pytest 221 (+24). 5 검증 PASS
- [2026-05-19 00:00:00 KST] server/signaling.py DB 영속화 통합 + 가드레일 31 (사용자 directive "다음작업 + 페이즈 2 후 reviewer + handoff" 자율 GO) — `_handle_join` 의 user_id 파싱 + Peer set + persist_peer_join (단계별 + 매 Edit AST). `_handle_leave` 의 persist_peer_leave. 영구 메모리 `feedback_phase2_completion_review_handoff.md` (Phase 2 마무리 후 reviewer + handoff doc 의무). 5 검증 PASS
- [2026-05-18 23:30:00 KST] server/room.py Peer dataclass user_id + db_room_id field 추가 (사용자 directive "잔존작업 진행해" 자율 GO) — minimal 확장 (`user_id: int | None` + `db_room_id: int | None`) — signaling 통합 사전 보장. 5 검증 PASS — AST + dataclass 인스턴스 + pytest 197 + doc-lint 0 + BPE 0
- [2026-05-18 23:00:00 KST] server/signaling_persistence.py 신설 — DB 영속화 helper (사용자 directive "검증하면서 작업" 자율 GO) — 5 async 함수 (room_create/peer_join/peer_leave/text_message/system_event) + pool=None silent skip + 예외 비차단. 5 검증 PASS — AST + import + pytest 197 + doc-lint 0 + BPE 0. 기존 signaling.py 미수정 (보수적 분리)
- [2026-05-18 22:30:00 KST] build.yml 신설 + snapshot 사이클 23 + handoff §8.41 (사용자 directive "잔존이슈 다 진행해" 자율 GO) — `.github/workflows/build.yml` heredoc 신설 (macOS arm64 + wine cross-compile + tag push v* + dispatch + artifact 30일). productization §2.23 + 4.25 ▲ + vibe-coding §2.27 + 4.80 ▼ (사이클 22 사고 반영). handoff §8.41 + 마지막 갱신 사이클 23. doc-lint 0 + BPE 0
- [2026-05-18 22:00:00 KST] app/ui/main_window.py 계정 메뉴 + 4 slot + 검증 의무 적용 (사용자 directive "검증 진행하면서 작업해" + "KST timezone" 자율 GO) — 단계별 Edit + 매 Edit 직후 AST 검증. 5 검증 PASS — AST + import + pytest 197 + doc-lint 0 + BPE 0. 직전 perl bulk 손상 회수 + post-write hook 정합
- [2026-05-18 06:00:00] server/main.py + app/main.py 확장 (DB pool + auth middleware + AuthClient) (사용자 directive "잔존작업 다 진행해" 자율 GO) — build_app() 비동기 변환 + auth_middleware + register_auth_routes + session_store dict + DB_ENABLED=1 시 create_pool + on_cleanup close_pool. AuthClient base URL normalize + graceful close. 전체 pytest 197 passed + import OK
- [2026-05-18 05:30:00] server/api REST 5 endpoint + app/net/auth_client.py + UI 3 dialog (signup + login + reset) (사용자 directive "다음작업 이어서 진행해" 자율 GO) — server/api/auth_handlers.py 5 POST handler (register/verify/login/reset/request/consume) + AuthError → HTTP status 매핑. AuthClient class (aiohttp + network err 폴백) + 5 method. signup/login/password_reset dialog (PyQt6 QStackedWidget 2단계 + asyncio.ensure_future + silent success enumeration 방어). 전체 pytest 197 passed

---

**문서 상태**: `active` · 최초 작성 2026-05-17 · M2 변경 이력 30행 캐시
운영. 30행 초과 시점부터 회전 + History.md 위임.
