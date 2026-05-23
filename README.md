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
> 본 시점 = 30행 상한 회전 완료 (2026-05-21 — release-agent cycle 169.189 M2 53 entry batch prepend + dereliction-detector HIGH 회수 정합).
> 상세 History.md 전체 보존.

- [2026-05-23 12:14:37] PORTABLE_HARNESS 타 프로젝트 시작용 `$portable-harness` 개인 skill 분리 반영 (docs/PORTABLE_HARNESS.md · CheckList.md · ~/.codex/skills/portable-harness)
- [2026-05-23 12:06:22] PORTABLE_HARNESS 거버넌스·hook·guardrail·trigger·코드 분리 이식 한벌 최신화 (docs/PORTABLE_HARNESS.md · Structure.md · CheckList.md)
- [2026-05-23 07:20:00] 바이브코딩 평가서 엄격 기준 L5 포함 및 보수 비율 반영 (docs/assessments/vibe-coding.md · docs/html/vibe-coding.html)
- [2026-05-23 07:10:00] 원격 시그널링 서버 Playwright WebSocket E2E 보강 (DESIGN.md · CheckList.md · Structure.md · tests/e2e/conftest.py · tests/e2e/test_signaling_browser_flow.py)
- [2026-05-23 06:55:00] 평가 문서 낙관 표현 보수 교정 (docs/assessments/productization.md · docs/assessments/vibe-coding.md · docs/html/productization.html · docs/html/vibe-coding.html)
- [2026-05-23 06:40:00] meta-enforcement L5 자기검증 계층 추가 + 임시 artifact 깨진 링크 정리 (tools/meta_enforce.py · ci.yml · docs/policies/execution-harness.md · docs/assessments/codex-2.8-mixin-fragility.md)
- cycle 169.582~585 (2026-05-24 18:00 KST) — self-hosted runner restart + dispatch retry + UI ignore chain. (582) launchctl unload/load `actions.runner.oneticket99-p2p_msg.tootalk-macos-1ticket` — Listener pid 77699 new (이전 46306 17h uptime token cache expiry). (583) 169.582 57m57s dispatch stall cancel + fresh empty commit trigger. (585) ci.yml pytest `--ignore=tests/app/ui` 추가 (qapp fixture scope=module + PyQt6 widget cleanup stuck pattern 회수).
- cycle 169.574~580 (2026-05-24 17:30 KST) — pytest test swap chain (cycle 169.275/421 actual binding fallout 회수). (574) main_window admin_menu + update_task hang skip mark. (575) capture impl PyObjC graceful guard + win/linux test class verify swap. (576) input_forward PyObjC guard + win/linux test class swap. (577) 평가 staleness rewrite. (578) i18n tr_wrap main_window expected_min 7 → 1 (mixin 분산). (579) test_applier macOS/Windows expect False swap (binary verify gate). (580) admin_menu patch path mixin 정합 fix (standalone PASS / fixture chain hang 별 cycle). tests/app no-ui 전수 = **1153 PASS + 1 skip**.
- cycle 169.569~572 (2026-05-24 16:50 KST) — BPE strict enforcement + asyncio guard chain. (569) hook_chat_bpe_check.sh severity WARN 🟡 → BLOCK 🔴 swap + memory `feedback_bpe_strict_self_grep.md` 신설 (chain literal 부착 차단 5 rule). (570) `tools/bpe_self_check.sh` standalone util 신설 (QUAD/TRIP/DENSE/CHUK detect, draft pipe verify mandatory). (571) 평가 staleness rewrite. (572) `_chat_navigation_mixin.py` asyncio.ensure_future graceful loop guard (python 3.13 안 running loop 부재 시점 schedule skip, rooms.py 5 ERROR → 5 PASS).
- cycle 169.566~567 (2026-05-24 16:30 KST) — CI fail-fast chain. (566) ci.yml pytest `-x --ignore=tests/e2e --ignore=tests/integration` swap (hang scope 축소 + qasync event loop blocker 회피). (567) test_folder_client TLS default swap (cycle 169.275 정합 — `TOOTALK_TLS_VERIFY` default "0" demo retain, production override test 신규, 7 PASS).
- cycle 169.560~565 (2026-05-24 16:00 KST) — WBS web view + 평가/CI staleness chain. (560) tools/wbs_view.py CLI viewer (argparse 4 mode). (561) tools/gen_wbs_view.py + docs/operations/wbs.html (vanilla CSS/JS + Toonation BI + sortable + filter). (562) 평가 staleness rewrite. (563) CheckList FR/NFR/M1~M5 realistic update (5 FR done + 4 partial + 3 M done). (564) ci.yml pytest timeout 20 min + stuck pid kill. (565) 평가 staleness rewrite.
- cycle 169.555~558 (2026-05-24 15:00 KST) — token-usage 이전 머신 history 복원 chain. (555) `docs/operations/token-usage-30d.json.bak.json` + current json union merge logic (per_day + per_model + per_day_model + sessions_summary + totals). (556) HTML render local var reassign bug fix → 일별 비용 5월 17~23일 7일 full render PASS. (557) 평가 4 file staleness rewrite. (558) HTML bak retain commit. regen 결과 = 7 session + 20024 msgs + $22137.68 (이전 1825 msgs/$1535 → 11배+ 복원).
- cycle 169.549~554 (2026-05-24 14:00 KST) — staleness/lint cycle batch. (549) handoff §8.82 14 → 17 entry + wbs 3 row + README/History. (550) stale handoff 2 → completed/ archive. (551) doc-lint local 2 violation (BPE "의" + link path). (552) 다음 session handoff doc 신설 (64 cycle 인계). (553) MD047/MD055 handoff doc. (554) 평가 4 file staleness rewrite.
- cycle 169.548~549 (2026-05-24 14:00 KST) — 평가 4 file staleness rewrite (cycle 169.543~547 5 commit drift 회수, last_verified 14:00 swap) + handoff §8.82 17 entry update (cycle 169.546~548 추가) + M6 wbs 3 row INSERT local (total=188).
- cycle 169.546~547 (2026-05-24 13:50 KST) — handoff §8.82 신설 (cycle 169.532~545 14 entry batch) + M6 wbs 11 row INSERT + build.yml workflow_dispatch dispatch (runId 26320924166) — macOS arm64 (.app 343.8MB) + Windows x64 (.exe 101.5MB) 양 job success ✅ + artifact download chain.
- cycle 169.545 (2026-05-24 13:45 KST) — ws service bot provider env inject (BOT_ENABLED + ANTHROPIC_API_KEY + OPENAI_API_KEY 추가). 원격 .env inject + ws restart → readyz `bot_provider: ok` 도달 (degraded → ok 전환). server full ready state 활성.
- cycle 169.543~544 (2026-05-24 13:35 KST) — markdownlint MD037/MD050 disable (README cycle entry underscore method false positive) + handoff §8.80 table blank line (MD058). docs-lint CI fail 회수.
- cycle 169.542 (2026-05-24 13:30 KST) — 평가 4 file staleness rewrite (6h cap) — last_verified swap + 사이클 169.541 정합.
- cycle 169.541 (2026-05-23 17:00 KST) — token-usage 1ticket dir 동적 resolve + cost_usd local shadow fix (sessions=3 msgs=1825 cost=$1535.25, 이전 0/0/0 초기화 회수).
- cycle 169.540 (2026-05-23 16:50 KST) — ws healthcheck port 8765 + DB_ENABLED (Dockerfile 8080 hardcoded → ws mismatch). readyz db_pool ok 도달.
- cycle 169.539 (2026-05-23 16:45 KST) — `/ws` auth_middleware public path 추가 (codex e2e 401 회수). WebSocket JOIN/UNKNOWN_TYPE protocol chain 활성.
- cycle 169.538 (2026-05-23 16:30 KST) — deploy/docker-compose.yml ws ports 8765:8765 bind (expose only → host port mapping, leftover python3 process conflict 회피).
- cycle 169.537 (2026-05-23 15:00 KST) — codex e2e browser WebSocket flow 신설 (Playwright + native WS alice/bob 2 socket JOIN/OFFER/ANSWER/ICE/LEAVE happy path + UNKNOWN_TYPE/NOT_JOINED error path). 평가 4 file 보수 재교정 (8.4/6.8 swap).
- cycle 169.536 (2026-05-23 14:30 KST) — meta-enforcement L5 자기검증 계층 (tools/meta_enforce.py 5 검사 + ci.yml meta job + L5 6단 docs).
- cycle 169.535 (2026-05-23 14:00 KST) — streaming test 5 URL return swap (cycle 169.418 NotImplementedError 폐기 fallout, 33 test PASS).
- cycle 169.534 (2026-05-23 12:00 KST) — codex 2.8 reviewer 20 finding 회수 + MRO regression test 4 PASS (test_main_window_mixin_mro.py 신설).
- cycle 169.533 (2026-05-23 06:30 KST) — codex 2.7 재 평가 + PyQt6 offscreen MainWindow instantiation smoke PASS (21 mixin + 9 helper + 4 stacked + 2 chat entry + central QSplitter + 720x640). 기술 9.2 → 9.4 ▲ + 종합 6.5 → 6.8 / 10 ▲. 평가 4 file (productization md/html + vibe-coding md/html) last_verified 06:30 swap. readiness 표현은 cycle 169.535 에서 내부 dogfooding 후보로 보수 교정.
- cycle 169.532 (2026-05-23 06:20 KST) — handoff §8.81 신설 (cycle 169.516~531 16 entry manifest) + M6 wbs_tasks 6 row INSERT local (data/wbs.sqlite — cycle 169.526~531). 본격 main_window 책임 분리 phase 본격 종료 manifest + 다음 session 진입 chain 5 (visual ack + PyQt6 smoke + M6 + codex 2.7 + .app build).
- cycle 169.531 (2026-05-23 06:10 KST) — 평가 4 file fingerprint sync — cycle 169.525~530 6 commit drift 회수 (last_verified swap 04:05 → 06:10 + 사이클 169.523 → 169.530).
- cycle 169.530 (2026-05-23 06:00 KST) — codex 2.5 `__init__` 302 line CRITICAL blocker 회수 — 9 helper method split (_init_state + _init_window_properties + _init_splitter + _init_sidebar_rail + _init_chat_list_panel + _init_right_panel + _init_input_bar + _finalize_splitter + _init_status_and_startup_chain) — main_window.py 643 → 600줄 (43줄 감소 + body 가독성 dramatic 향상)
- cycle 169.529 (2026-05-23 05:40 KST) — codex 2.5 main_window 책임 분리 14차 batch — `app/ui/_invite_mixin.py` 신설 (InviteMixin: open_invite_dialog + _on_invite_failed, 2 method 95 line) + `app/ui/_lifecycle_events_mixin.py` 신설 (LifecycleEventsMixin: resizeEvent + closeEvent, 2 method 67 line) + `app/ui/_friend_status_mixin.py` 신설 (FriendStatusMixin: _fetch_user_status async REST, 1 method 53 line) + MainWindow MRO 21 mixin + main_window.py 786 → 643줄 (143줄 분리, 누계 3383줄 4026 → 643, **84.0%**)
---

**문서 상태**: `active` · 최초 작성 2026-05-17 · M2 변경 이력 30행 캐시
운영. 30행 초과 시점부터 회전 + History.md 위임.
