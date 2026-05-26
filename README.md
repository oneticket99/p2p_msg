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

- [2026-05-26 10:10:00] cycle 169.846 — M5 reviewer 게이트 PASS(차단 0, LOW 1+OBSERVATION 3, 송신 경로 수렴 기능 등가+import 무결성 핵심 PASS) + 다음 session 인계 자료 작성. `docs/exec-plans/active/2026-05-26-session-handoff-cycle169.845.md` 신설(cycle 839~845 + 잔존 M6 통합 room-send coverage/M5b idx 재번호+위젯 파일 삭제+dead attr). room broadcast 마이그레이션 M1~M5 완료 — 통합 ChatView 단일 경로 수렴. (docs/exec-plans/active)
- [2026-05-26 09:55:00] cycle 169.845 — room broadcast 마이그레이션 M5(안전): legacy GroupChatView 경로 물리 회수 + M3+M4 reviewer PASS. 회수: GroupChatView import/`_group_chat_view`/RoomListWidget(`_room_list`)/`room_entered`/`_on_room_entered`/`_on_group_message_send`/`_dispatch_message_chain`/header room_list 토글. 유지: `_group_placeholder`(idx 1 빈 spacer, idx 재번호 회피)·`_member_list`(idx 2, group-management)·멤버 보기 in-app 모달. test 2 삭제(obsolete) + 3 갱신. 전체 2500 passed + BPE PASS. idx 완전 재번호 + 위젯 파일 삭제 = M5b. (app/ui · app · tests · docs)
- [2026-05-26 09:25:00] cycle 169.844 — room broadcast 마이그레이션 M4(kind=room 진입 통합 ChatView 통일, 임계 전환점). `_on_chat_selected` 의 `kind=="room"` → `_on_room_entered` early return 제거 + kind=room 시 `_current_room_id` 설정(송신 REST + 멤버 보기 활성) + `_on_header_menu` group 분기에 "room" 추가(멤버 보기 회귀 차단). 본 cycle 로 GroupChatView 사용자 도달 불가 → G-final 게이트 준비 완료(M5 위젯 회수는 사용자 GO 후). test 2 신설. UI 348 passed(346→348, 회귀 0) + BPE PASS. (app/ui · tests)
- [2026-05-26 09:05:00] cycle 169.843 — room broadcast 마이그레이션 M3(room 적재 source-of-truth `_room_list._rooms` → `_rooms_cache` 직접 cache 이전) + M2 reviewer-agent 게이트 PASS(차단 0). 4 지점 atomic: main_window `_rooms_cache` 신설 + `_auth_chain_mixin`/`app/main.py` writer + `_chat_navigation_mixin._refresh_chat_list_panel` reader 전환. `_room_list.set_rooms` 는 M5(G-final 후) 회수까지 병행 유지. test 2 신설(cache 읽기 증명 + 빈 cache). UI 346 passed(344→346, 회귀 0) + BPE PASS. (app/ui · app · tests)
- [2026-05-26 08:35:00] cycle 169.842 — room broadcast 마이그레이션 M2(송신 echo 통합 ChatView 재배선). `_on_group_message_send` echo 를 legacy `_group_chat_view.append_message` → `_chat_view.add_message(hide_sender=False, play_sound=False)` 재배선, `_dispatch_message_chain`(REST+mesh) 불변. 발견: 통합 송신 경로가 이미 group/room 완전 처리 → legacy 핸들러는 GroupChatView 전용. test 2 신설(echo target spy). UI 344 passed(342→344, 회귀 0) + baseline 무파괴 + BPE PASS. GroupChatView 는 M5(G-final 후) 회수까지 병행. (app/ui · tests)
- [2026-05-26 08:15:00] cycle 169.841 — current-project-review 전면평가 최신화. HEAD cycle169.839 + token usage 산출 cycle169.840 진행 상태 반영, 점수 7.7/10 보수 조정, pytest 2557 PASS + coverage 87.99% + migration strict PASS + assessment stale 원인 기록, legacy room path 전체 마이그레이션을 P0 큐로 승격. (docs/assessments)
- [2026-05-26 08:15:00] cycle 169.840 — token-usage-30d 재산출(사용자 directive — 원격 git `.bak` 이어서). `gen_token_usage_30d.py` 가 원격 pull `token-usage-30d.json.bak.json`(sessions 4·msgs 17954·$20342) 병합 + 현 세션 합산. parsed_messages 24364→37197, 누적 토큰 122.5억→187.4억, cost $26,104→$41,954, cache hit 97.27%→96.79%, sessions 5. json+html mirror rewrite. (docs/operations)
- [2026-05-26 08:10:00] cycle 169.839 — group-flow isolated test 재구성(인계 task 3-1). cycle838 "방 입장"(Room ID) 제거 정합 — `test_main_window_rooms.py` 구 `room_entered.emit(N)`(GroupChatView idx 1) → 그룹 만들기 wizard chain 전면 교체. 사용자 결정=통합 ChatView(idx 0) canonical, 구 GroupChatView+room_entered=legacy 폐기(코드 무변경, test 만). 신 6 PASS(ChatListPanel default·NewGroupDialog 2-step·group_created emit·`_on_group_created` kind=group insert·`_on_drawer_new_group` offscreen 가드·전 wizard chain). UI 342 passed(5→6, 회귀 0) + BPE PASS. (tests)
- [2026-05-26 01:00:00] cycle 169.838 — 전 dialog in-app overlay 모달 변환(별도 OS 윈도우 → 메인 레이아웃 안 모달, 새창=원격제어 창만) + "방 입장"(Room ID) 메뉴 제거(그룹방=그룹만들기+초대) + ChatHeader stale 수정 + GroupChatView 중복 헤더 제거. `_exec_dialog_centered` test 가드 + `_modal_helper`(nested dialog parent-walk) 신설. UI 341 + integration/e2e 327 passed(hang 0). (app/ui)
- [2026-05-26 00:40:00] cycle 169.837 — 그룹 멤버 UX 완성: 멤버 보기 → 모달 + 원형 아바타 행(친구행과 동일 디자인) + 그룹 "..." 메뉴 미구현 stub 전수 제거(알림끄기·그룹정보·그룹관리·설문·채팅정보 → working 항목만). 사용자 directive(미구현 노출 금지). UI 341 passed(hang 해소). (app/ui · tests)
- [2026-05-26 00:10:00] cycle 169.836 — 그룹 "멤버 보기" 헤더 "..." 드롭다운 entry 이동(텔레그램 플로우) + room 진입 시 `_active_chat_kind="group"` 미설정으로 "..." 가 단순 메뉴 표시되던 버그 회수(별도 버튼 제거). + 메시지 수신음 실 파일 교체 정정 — cycle834 가 미사용 시스템 파일(tootalk_ppyong.wav)을 교체해 구버전 소리 잔존 → 실 재생 파일 `app/assets/sounds/signature.wav` 를 ding 으로 교체. UI 341 + sound 45 passed. (app/ui · app/assets)
- [2026-05-25 23:00:00] cycle 169.835 — startup 로그인 경로 계정 메뉴 auth 토글 회수. main window 진입 후에도 회원가입/로그인 메뉴 잔존(재로그인해야 토글) — cycle831 이 `_on_open_login` 만 커버, startup(`main.py`) 경로 누락 → token 주입 직후 `apply_auth_menu_visibility` 재호출. reviewer PASS + menu isolated 4 passed. (app)
- [2026-05-25 22:40:00] cycle 169.834 — dogfooding 버그 6종 + user-facing 문구 i18n 5언어 친절화. (1)채팅 스크롤 중복 dedup+cursor (2)로그인후 메뉴 auth 토글 (3)친구 요청/승인 모델(instant→pending, accept 시 DM room) (4)헤더 멤버수 stub (5)트레이 문구 (6)`labels.py` 5언어 tr 키+11 UI 친절화. i18n16+UI341+friends32 passed, doc-lint 0위반. (app/ui · app/i18n · server/api · tests · docs)
- [2026-05-25 22:10:00] cycle 169.829 — `.markdownlint.json` `$schema` 줄 제거 (VSCode schema-fetch 경고 해소). URL 은 HTTP 200 유효이나 편집기 fetch 실패 경고 — markdownlint-cli2(CI) 는 `$schema` 불요로 lint 무영향(0 error) + JSON 유효 + doc-lint PASS, 편집기 자동완성만 상실. (config)
- [2026-05-25 21:50:00] cycle 169.828 — SFU 서버 재가용: `server/requirements.txt` 에 `aiortc>=1.14` 추가. cycle826 graceful optional import 위에서 데모 서버 SFU 그룹 통화 실 활성화. python:3.13-slim throwaway 검증 — aiortc-1.14.0/av-16.1.0/pylibsrtp-1.0.0 전부 manylinux wheel(native 빌드·Dockerfile 수정 불요) + runtime import OK. redeploy 시 `AIORTC_AVAILABLE=True` → `SFU_PUBLISH` 차단 해제. 평가 marker 828 동기. reviewer PASS. (server · docs)
- [2026-05-25 21:30:00] cycle 169.827 — 평가 marker 169.826 동기(current-project-review/productization/vibe + `docs/html` 2 mirror) + README 30행 trim + meta `latest-cycle-documented` self-reference 회수(History/README 에 169.827 marker). assessment-consistency 2cycle RED 해소. 코드·서버 무관(데모 healthz 200 유지). (docs)
- [2026-05-25 20:58:00] cycle 169.826 — 데모 서버 502 회수: SFU aiortc graceful import. cycle 169.799 SFU 가 `sfu_room.py:36` 에 aiortc module-level hard import(requirements 누락) → 244-commit stale clone redeploy 후 web·ws `ModuleNotFoundError: aiortc` crash loop → nginx 502. aiortc 를 try/except graceful optional(`AIORTC_AVAILABLE`, httpx/firebase 동일 convention)로 전환 → 코어 부팅 + SFU degrade. `SfuRoom` 가드 + `_handle_sfu_publish` 차단. 로컬 차단모사 검증 + reviewer PASS. SFU 재가용은 별 task. (server)
- [2026-05-25 23:55:00] cycle 169.820~823 — 텔레그램 그룹 관리 모델 단계 + 빌드/502 회수. (1) migration 0017 — `peers.role` ENUM owner/admin/member 3-tier + `rooms` name/description/avatar_ref 그룹 메타 (모델→REST→UI 의 모델, isolated 15). (2) Windows/macOS 재빌드 (MemberPanel member_count/viewer_role 위임 CI 회귀 회수). (3) **443 nginx 전수조사** — nginx 443 의 web:8080/ws:8765 upstream 컨테이너 다운 502 근본 식별(8765 직결 UP), 클라이언트 443/8080 하드코딩 전수 제거(10+3 → http 8765 + guard test). reviewer/qa/observability PASS. (server/db · app/ui · tests · deploy)
- [2026-05-25 21:00:00] cycle 169.814 — 협업용 전면평가 stale 재발 방지 강화. `tools/check_assessment_consistency.py` 를 doc-gardener 주간 검사에서 PR/main push `ci.yml` 필수 job 으로 승격하고, `tools/meta_enforce.py` 가 해당 CI job 존재를 자기검증하도록 추가. `docs/policies/doc-gardening.md` + `docs/assessments/current-project-review.md` 에 ci/doc-gardener/meta-enforcement 3중 연결을 명시. README 변경 이력 30행 상한 재정렬 (ci · tools · docs/assessments · docs/policies)
- [2026-05-25 22:30:00] cycle 169.819 — 그룹 멤버 보기 UX 2건 회수(사용자 빌드 테스트 발견). (1) "멤버 보기" 빈 화면: `_on_open_members_panel` cycle 139 stub(set_members([]))를 AppState self peer + known_peers MemberItem 구성으로 회수(빈 방="아직 참여 멤버가 없습니다" 안내). (2) 이전 화면 복귀 채팅리스트 의존: `app/ui/member_panel.py` MemberPanel(헤더 "← 뒤로" + MemberListWidget) 신설 → back_requested→_STACK_GROUP_CHAT 복귀. main.py MemberListWidget→MemberPanel 교체. member_panel isolated 4 PASS. reviewer PASS. + History M3 814 재배치(역순 정합) (app/ui · tests)
- [2026-05-25 22:10:00] cycle 169.818 — 평가 2종 staleness refresh (vibe 813 이후 5 commit). Codex 평가 환류 완료(811~816) + 빌드 테스트 회수(817 로그인 502 + dialog 투명) 반영. productization/vibe-coding + html mirror 2 = 사이클 169.818 + last_verified 22:10. macOS .app 정상 기동 + 502 회수 검증, Windows CI 빌드. 점수 7.6/8.4 변동 부재 (docs/assessments · docs/html)
- [2026-05-25 22:00:00] cycle 169.817 — 빌드 테스트 발견 회수 2건. (1) 로그인 HTTP 502 Bad Gateway 회수: 앱이 https://114.207.112.73(nginx 443, upstream 502) 호출하나 REST 실 동작은 http 8765(signaling 동일 aiohttp). `app/core/config.py` 에 `api_base` 필드 신설(default "", from_env 가 http://{host}:{port} 8765 주입) + `app/main.py` config.api_base single source 정합(7 client + 9 mixin getattr 공통). (2) `app/ui/confirm_dialog.py` title+msg_label `background: transparent;` (사용자 directive). config 52 PASS + confirm_dialog isolated 9 PASS + doc-lint EXIT=0. reviewer PASS (app/core · app · app/ui)
- [2026-05-25 21:20:00] cycle 169.816 — Codex P0 FR 추적표 "코드 위치 (예정)" per-file 감사 완료. Specification.md §8 FR 표 9 FR 코드경로 실재 검증 → 실 트리 노드 링크 갱신 + 경로 이동 반영(transfer.py→file_sender/file_receiver/image_processor · storage.py→db/messages_cache+local_db · db_init→server/db/migrations · onboarding_dialog→welcome_dialog/signup_dialog). CheckList.md "코드 위치 (예정)" 컬럼 헤더/참조 label 4건 정리(데이터는 이미 실 링크). FR 코드경로 "(예정)" 전 저장소 0. markdownlint 0 + doc-lint EXIT=0 (Specification · CheckList)
- [2026-05-25 21:00:00] cycle 169.815 — Codex §4.2 productization 본문 전수 rewrite (general-purpose agent + main session 검수). productization.md 718→508행 + docs/html/productization.html 580→513행 mirror 동시. §2.14~2.40 cycle-by-cycle 역사 로그 graveyard(cycle 169.NNN 348회) 제거 → 현 상태 중심 prose 압축(잔존 2 = 815 marker). SFU 그룹 통화 종단 완결(PR#12/#13) IMPLEMENTED 반영, 점수 7.6/10 유지. 검수: BPE 0 + 의 의 0 + doc-lint EXIT=0 + mirror EXIT=0. cycle 814 Codex(PR#14) 충돌 → 815 정정 (docs/assessments · docs/html)
- [2026-05-25 20:50:00] cycle 169.813 — 평가 2종 staleness refresh (hook_assessment_freshness — 808 이후 5 commit) — SFU 종단 완결(PR#12/#13 merge) + Codex 전면평가 환류(811 review cycle 797→810 + §3.6 SFU + checker PASS, 812 stale sweep) 반영. productization/vibe-coding + html mirror 2 = 사이클 169.813 + last_verified 20:50 동기. 점수 7.6/8.4 변동 부재 (docs/assessments · docs/html)
- [2026-05-25 20:45:00] cycle 169.812 — Codex P0 "과거 표현 sweep" 안전 부분 진행. Specification.md(17) + CheckList.md(4) 의 "작성 예정 — 운영 N/8" stale marker 21건 정정(Structure.md/History.md/README.md/CheckList.md 모두 실재 → "작성 완료"). "작성 예정" 잔존 0. 코드 경로 "(예정)" 열은 per-file 감사 필요 → 후속 위임. doc-lint EXIT=0 (Specification · CheckList)
- [2026-05-25 20:30:00] cycle 169.811 — Codex 전면평가(current-project-review.md) 정독 + 수정반영. check_assessment_consistency FAIL(HEAD cycle 810 marker 부재) 회수: 검토 기준 cycle 797→810 + §3.6 "음성·영상 SFU 그룹 통화" 신설(server/client/UI/배선 종단 IMPLEMENTED, PR#12/#13) + §4.1 회수 2건 추가(Structure ERD drift 794 회수 + mesh≤8 부정확 정정). checker [PASS] 복귀. Codex P0 잔여 = Specification/CheckList 과거 "예정" 표현 sweep(후속) (docs/assessments)
- [2026-05-25 20:00:00] cycle 169.810 — 음성·영상 SFU 그룹 통화 **종단 코드 완결 + PR #13 main merge**. cycle 809 MainWindow 합성(SfuCallMixin bases + _init_sfu_call + "그룹 통화 시작"(Ctrl+Shift+G) 메뉴 entry + _sfu_call_mixin attr 정렬 self._signaling→_signaling_client[807 broken 사전 회수, app/main.py:397 실 attr]) 반영. PR #13(M4a SfuCallClient 804 + M4b-1 dispatch/send 805 + M4b-2a GroupCallDialog 806 + M4b-2b SfuCallMixin 807 + 합성 809) CI 10/10 GREEN merge(60348d2). server(PR#12)+client net+UI+배선+entry 종단 완결. 잔여=visual ack 후반 일괄 (app/ui · README/History)
- [2026-05-25 19:30:00] cycle 169.808 — 평가 2종 staleness refresh (hook_assessment_freshness — 802 이후 6 commit) — 음성·영상 SFU 그룹 통화 전 경로 코드 완결 반영. server(M3a/b/c PR#12 merge) + client net(M4a SfuCallClient 804, M4b-1 SignalingClient SFU dispatch/send 805) + UI(M4b-2a GroupCallDialog 806) + 배선(M4b-2b SfuCallMixin 807, PR#13). reviewer-gate 9 feat 전수 PASS. 잔존=MainWindow 합성+visual ack 큐. 점수 7.6/8.4 변동 부재 (docs/assessments · docs/html)
- [2026-05-25 18:50:00] cycle 169.802 — 평가 2종 staleness refresh (hook_assessment_freshness — 800 이후 5 commit) — 음성·영상 SFU 그룹 통화 server-side 완결 반영. M3a(798 protocol)→M3b(799 sfu_room MediaRelay 코어)→M3c(801 signaling 라우팅+SfuRegistry+main startup), 각 reviewer-agent 게이트 PASS, SFU 17+회귀 36 PASS, PR #12. productization/vibe-coding + html mirror 2 = 사이클 169.802 + last_verified 18:50 동기. 점수 7.6/8.4 변동 부재 (docs/assessments · docs/html)
---

**문서 상태**: `active` · 최초 작성 2026-05-17 · M2 변경 이력 30행 캐시
운영. 30행 초과 시점부터 회전 + History.md 위임.
