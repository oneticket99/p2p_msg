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

- [2026-05-27 03:50:00] cycle 169.853 — **한글 주석 페이즈 M2 batch-7 (T-3) — email_verification + bots**. `email_verification.py`(OTP 평문 비저장 code_hash + 활성 조건 consumed/expires/attempt<5 brute-force 차단 + 1020 retry helper invariant + OtpRow + "부재 의 의무" awkward 정정) + `bots.py`(토큰 평문 비저장 + 인증 revoked/active chain + soft revoke 멱등 + BotRow + bare 함수 5 docstring + 대명사 정정). diff-0 PASS + otp/bot/verif 154 passed 무변경 + BPE/대명사 0. M2 15/21. (server/db/repositories)
- [2026-05-27 03:25:00] cycle 169.853 — **한글 주석 페이즈 M2 batch-6 (T-3) — messages + folders**. `messages.py`(계층 §E + 입력 fail-fast + unbounded SELECT 차단 invariant + soft delete body NULL tombstone + 실 11 함수 카탈로그 + MessageRow invariant + list_recent/list_messages_in_range docstring, ValueError 런타임 string 미변경) + `folders.py`(folder⊃folder_chats include/exclude 2-mode + batch 단일 transaction invariant + FolderRow + bare 함수 5 docstring + "의 의" 이중조사 + 대명사 정정). diff-0 PASS + message/folder 94 passed 무변경 + BPE/대명사 0. M2 13/21. (server/db/repositories)
- [2026-05-27 03:05:00] cycle 169.853 — **한글 주석 페이즈 M2 batch-5 (T-3) — rooms.py(코어)**. module docstring 카탈로그 정정(부정확 "10 SQL" 약칭 → 실 심볼명 15 공개 함수, find_or_create 3종·close_room·list_active_peers 누락 보강 — 카탈로그 컨벤션 정합) + deterministic room_code 멱등 invariant + soft-leave 활성 filter + RoomRow/PeerRow invariant + find_or_create_dm_room/count_active_peers/get_peer/list_active_peers docstring + "의 의" 1건 정정. diff-0 PASS + room/peer 86 passed 무변경 + BPE 0. M2 11/21 repository. (server/db/repositories)
- [2026-05-27 02:45:00] cycle 169.853 — **한글 주석 페이즈 M2 batch-4 (T-3) — users.py(코어)**. module docstring(계층 §E + invariant — email 소문자 normalize/동시성 1020 retry·graceful/미검증 reclaim user_id 보존/avatar_ref backward compat) + UserRow invariant(password_hash 민감·email_verified 의미) + get_user_by_username_excluding 의도(reclaim self-conflict 오판 회피) 보강 + "의 의" 2건 정정. diff-0 PASS + user/auth 104 passed 무변경 + BPE 0. M2 10/21 repository. (server/db/repositories)
- [2026-05-27 02:25:00] cycle 169.853 — **한글 주석 페이즈 M2 batch-3 (T-3) — avatars + streaming_oauth_tokens**. `avatars.py`(파일시스템 backend 계층 위치 + 동기 함수 + 부작용 분리 보강, 이미 모범) + `streaming_oauth_tokens.py`(4 platform OAuth 토큰 보안 invariant — access/refresh 민감 redact + (user,platform) UNIQUE + revoke 후 delete 순서 + refresh chain). diff-0 게이트가 ValueError 메시지 문자열 변경(런타임 AST)을 검출 → 원복(주석 전용 정합 확인). 기능 diff 0 PASS + server 642 무변경 + BPE 0. M2 9/21 repository. (server/db/repositories)
- [2026-05-27 02:05:00] cycle 169.853 — **한글 주석 페이즈 M2 batch-2 (T-3) — server repository 3종**. `file_meta.py`(uploading→completed/failed 상태 머신 invariant + mark_completed status 가드) + `device_tokens.py`(multi-device FCM token + soft revoke is_active + 6 platform ENUM fail-fast) + `user_contacts.py`(E.164 정규화 + 양방향 reverse match 모델 + line 73 "의 의" 이중조사 정정). module/class/함수 docstring(의도/Param/Return/Raises/부작용) + inline "왜". 기능 diff 0(verify_comment_only 3 PASS) + server 642 passed 무변경 + BPE 0. M2 7/21 repository. (server/db/repositories)
- [2026-05-27 01:45:00] cycle 169.853 — **평가 2종 sweep(avatar M7+주석 페이즈 반영) + dereliction MEDIUM 2 회수**. productization/vibe-coding md+html 4종 sweep(last_verified 01:30, §3.1 avatar M1~M7 코드+문서 완결 + 주석 페이즈 row 신설, 종합 근거 갱신, 주석 페이즈 process 강점=AST diff-0 도구화+표준 reviewer 검증 후 전파). WBS cycle 169.853 row 4건 등록 + Exec Plan T-1/T-2 ✅·T-3 in-progress(4/21) 전이. 본 페이즈 기능 diff 0 라 점수 7.6/8.4 무변동. (docs/assessments · html · data · exec-plans)
- [2026-05-27 01:25:00] cycle 169.853 — **한글 주석 페이즈 M2 batch-1 (T-3) — server repository 3종**. `peers.py`(soft-leave 모델 invariant + left_at IS NULL 활성) + `read_states.py`(GREATEST 단조 증가 역행 차단 + unread COALESCE 산출 + "의 의" 이중조사 정정) + `password_reset.py`(token_hash 평문 비저장 + 만료/1회 소진 보안 invariant) 표준 적용(module/class/함수 docstring + inline "왜"). 기능 diff 0(verify_comment_only 3 PASS) + server 642 passed 무변경 + BPE 0. M2 4/21 repo(friends 본보기 포함). (server/db/repositories)
- [2026-05-27 01:00:00] cycle 169.853 — **한글 주석 페이즈 M1 본보기 (T-2) — friends.py 표준 full 적용**. `server/db/repositories/friends.py` module docstring(역할/계층 위치 정본 §E/의존성 DI/invariant 단방향 row/부작용 commit) + 클래스 docstring(FriendRow/FriendWithProfile 책임·불변식·협력) + 8 함수 docstring(의도/Parameters/Returns/Raises/부작용) + inline "왜"(SQL injection 차단·ENUM fail-fast·회귀 근거) 보강. 기능 diff 0(verify_comment_only PASS — docstring 제거 후 AST 동일) + friend test 53 passed 무변경 + BPE 0. M2 잔여 20 repo 의 살아있는 reference exemplar. (server/db/repositories)
- [2026-05-27 00:40:00] cycle 169.853 — **한글 주석 상세화 페이즈 GO + e2e test scope 편입**. Exec Plan status draft→active (사용자 directive "e2e 테스트 파일까지 모두 보강") + M7(tests/app·server·**e2e**) in-scope 편입(D-7/TD-1 해소 + T-10/T-11). `tools/verify_comment_only.py` 신설 — 기능 diff 0 검증(docstring 재귀 제거 후 AST 비교 = 주석/docstring 외 동작 라인 변경 0 검출, grep noise 면역). 자가 테스트 PASS(comment-only→AST 동일, logic 변경→차이). (docs/exec-plans · tools)
- [2026-05-27 00:15:00] cycle 169.852 — avatar picker **M7 문서 동기 (T-18)**. Structure.md(신규 _avatar_cache/_avatar_picker_button/_camera_capture_dialog 파일) + FRONTEND.md §16.4(picker + CameraCaptureDialog + AvatarCache + make_avatar_pixmap 6 site) + ARCHITECTURE.md §6(app/ui avatar 파이프라인 + server avatars_handlers/repo + 0018/0019 migration) + CheckList.md(avatar CODE 완결 + MEDIUM-A 백로그) + 평가 2종 M6 sweep + HTML mirror 4종(Structure/FRONTEND/ARCHITECTURE + 평가 2) 동시. doc-lint + html_mirror hook 전건 PASS. **avatar M1~M7 문서 완결** — G-final(실 webcam visual ack, 사용자 직접) 잔존. (docs · *.md/html)
- [2026-05-26 23:40:00] cycle 169.852 — avatar picker **M6 T-17 완결 (표시 전파 6 site)**. drawer header(HamburgerDrawer `set_avatar_ref` + `make_avatar_pixmap` + update_user_info latent NameError 회수) + profile(MyAccountDialog `avatar_ref` param + my_profile picker) 결선. `_drawer_mixin._on_profile_avatar_changed` 업로드 PASS 시 cache `seed_image`(round-trip 없이 즉시 표시) + `_my_avatar_ref` retain + 열린 drawer/생성 시 `set_avatar_ref` 전파. chat sender=이름 label(avatar pixmap 아님, telegram grouped 정합 N/A). propagation test 7 + 전체 2605 passed 회귀 0. **M6 완결** — M7 문서/G-final(실 webcam visual ack) 잔존. (app/ui · tests)
- [2026-05-26 23:15:00] cycle 169.852 — avatar picker **M6 T-17 표시 전파 (3/6 site)**. ChatListEntry/MemberItem `avatar_ref` 필드 + ① chat-list delegate(group/channel — hit 시 원형 이미지 drawPixmap, miss/부재 시 이니셜 fallback 무손상 + async fetch trigger) + ② member_list `_MemberRow`(make_avatar_pixmap + `avatar_ready` ref-match 재렌더) + ChatListPanel `avatar_ready` viewport repaint 구독. negative-cache(reviewer MEDIUM-1 — disk-miss set 으로 반복 stat 차단). propagation test 5 + 전체 2603 passed 회귀 0. 잔존 site = chat 버블 sender/drawer header/profile. (app/ui · tests)
- [2026-05-26 22:50:00] cycle 169.852 — avatar picker **M6 표시 전파 T-16**(인프라). `_avatar_cache.py` 신설 — AvatarCache 싱글톤(mem+disk `media_cache_dir/avatars/` 2단 캐시 + AvatarFetchWorker async fetch dedup + `avatar_ready(str)` signal + content-addressed 불변 키 + path traversal 방어 + worker retain/deleteLater + seed_image). `_avatar_helper.make_avatar_pixmap(name, avatar_ref, size)` 신설(캐시 위임 thin API, avatar_ref 부재/miss → 이니셜 fallback 무손상). test 8 PASS. T-17 6곳 전파(모델 avatar_ref plumbing) 잔존. (app/ui · tests)
- [2026-05-26 22:20:00] cycle 169.852 — avatar picker **M5 카메라**(T-14/T-15). `CameraCaptureDialog`(QtMultimedia QCamera/QImageCapture/QVideoWidget in-app 모달, FRONTEND §16 exec_modal) live preview + 촬영 → QImage, 권한 거부/카메라 부재 graceful + 자원 해제(stop+setActive(False)+deleteLater, objc-release 정합). picker "카메라에서" → `_on_camera` 연결. camera test 5 + 회귀 fix(기존 action test hang stub). 전체 2590 passed 회귀 0, reviewer 차단 0. M6 표시/M7 문서 잔존. (app/ui · tests)
- [2026-05-26 21:40:00] cycle 169.852 — avatar picker **M4 완결**(T-11/T-12 group/channel 서버 room 승격). camera_btn → AvatarPickerButton 3 dialog + _drawer_mixin 음수 gid placeholder → 실 RoomsClient.create_room(kind,avatar_ref)+invite_user(qasync) + migration 0019 rooms.kind channel 추가 + channel icon 오용 시정. e2e 19 + 전체 2585 passed 회귀 0, reviewer 차단 0. M5 카메라/M6 표시/M7 잔존. (server/db · server/api · app/ui · app/net)
- [2026-05-26 21:05:00] cycle 169.852 — avatar picker **M4 T-13** 개인 프로필 dialog 통합. my_profile_dialog avatar → AvatarPickerButton + `_drawer_mixin._on_profile_avatar_changed`(AvatarUploadWorker → AvatarPatchMeWorker PATCH /api/me/avatar). 3 PASS, 전체 2584 passed 회귀 0, reviewer 차단 0. M4 group/channel(T-11/12) 잔존. (app/ui)
- [2026-05-26 20:40:00] cycle 169.852 — 다음 session 인계 자료 갱신(사용자 directive). handoff cycle169.852 = avatar M1~M3 + M4 서버측 완결 반영, 다음 1번 = M4 클라 dialog 통합(group/channel 서버 room 생성 결선 + profile PATCH). 하드코딩 수렴/주석 plan/Codex 취합 + 부수 잔존 정리. (docs/exec-plans/active)
- [2026-05-26 20:25:00] cycle 169.852 — codex §4.6 하드코딩 수렴 — demo IP api_base routing literal `"http://114.207.112.73:8765"` 8 파일 중복을 `config.DEMO_FALLBACK_API_BASE` 단일 상수로 수렴 + `test_no_443_hardcode` scan gate(config 외 0 lock). 값 동일성 + 회귀 0 + reviewer 차단 0. (app/core · app/ui · tests)
- [2026-05-26 20:30:00] cycle 169.852 — 한글 주석 보강 별도 페이즈 Exec Plan 신설(planning-agent) — `docs/exec-plans/active/2026-05-26-korean-comment-enrichment-phase.md`(M1 표준~M6 영역별 + G-final 기능 diff 0). status draft, 사용자 승인 후 active. (docs/exec-plans/active)
- [2026-05-26 20:10:00] cycle 169.852 — token-usage 5/24~5/26 git 등록 자료만 병합. `token-usage-30d.json.bak.json` 에 2026-05-24~26 행만 추가하고, 산출기 totals/per_model 중복 합산을 날짜×모델 union 재계산으로 보정했다. 보고서 총합은 일별 합계와 일치하도록 10,266,725,019 tokens / $22,855.96 로 정규화. (docs/operations · tools)
- [2026-05-26 20:05:00] cycle 169.852 — avatar picker **M3 AvatarPickerButton + avatars_client** (Exec Plan ② 개발). 원형 picker button(드롭다운 파일/카메라/클립보드, 이모지 제외 + 원형 preview + 이니셜/camera fallback) + QThread worker 3종(upload multipart/fetch/patch_me) + camera/image SVG. test 17 PASS, 전체 2578 passed 회귀 0, reviewer 차단 0. M4~M7 잔존. (app/ui · app/net · app/assets)
- [2026-05-26 19:50:00] cycle 169.852 — Codex 전면평가 보정: `current-project-review.md` 에 실사용 데모 readiness 8.4/10 산정 기준 추가 + 사용자 직접 빌드 산출물 dogfooding 을 데모 QA 핵심 경로로 재분류 + 하드코딩 fallback 개선 큐 유지. (docs/assessments)
- [2026-05-26 19:45:00] cycle 169.852 — Codex 전면평가 보정: `current-project-review.md` 최신 HEAD `ac54cf8` marker 반영 + 하드코딩 fallback 개선 큐 추가(REST api_base/update URL/STUN/OAuth redirect/bot sender id single source 수렴 + literal scan CI gate 제안). (docs/assessments)
- [2026-05-26 19:40:00] cycle 169.852 — 다음 session 인계 자료 작성 (사용자 directive). `docs/exec-plans/active/2026-05-26-session-handoff-cycle169.852.md` — avatar 이미지 picker M1+M2 서버 영속 완결 + 클라 M3~M7 진입 manifest(Exec Plan T-8~T-18 정본 참조). 평가 sweep(avatar M1/M2, 8 commit 회수) 동반. (docs/exec-plans/active)
- [2026-05-26 19:25:00] cycle 169.852 — avatar picker **M2 업로드/조회/PATCH endpoint** (Exec Plan ② 개발). `avatars_handlers.py`(POST multipart+Pillow 정사각512 crop+EXIF strip / GET traversal 방어 / PATCH me) + rooms create payload avatar_ref + main route 등록. e2e 17 PASS, EXIF strip 실측 검증, 전체 2561 passed 회귀 0, reviewer 차단 0. M3~M7 잔존. (server/api · server/db · tests/integration)
- [2026-05-26 18:58:00] cycle 169.852 — avatar picker **M1 서버 영속 foundation** (Exec Plan ② 개발). migration 0018 `users.avatar_ref`(5요소 comment) + `users.py` UserRow/update_avatar_ref/get_avatar_ref + `avatars.py`(content-addressed 디스크 저장 + sha256 dedup + \A..\Z path traversal 방어). test 18 PASS, 전체 2560 passed 회귀 0, reviewer 차단 0. M2~M7 잔존. (server/db · tests/server)
- [2026-05-26 18:40:00] cycle 169.852 — 아바타 이미지 picker Exec Plan 신설 (사용자 directive — 그룹/채널/프로필 3곳 아바타 이미지 picker 파일/카메라/클립보드 + 서버 영속). planning-agent Whitebox spawn → `docs/exec-plans/active/2026-05-26-avatar-image-picker-upload.md` 14 섹션(M1~M7+G-final, T-1~T-18, 결정 D-1~D-8). M1 문서 선행 — 사용자 승인 후 ② 개발 진입. (docs/exec-plans/active)
- [2026-05-26 17:50:00] cycle 169.851 — coverage omit 축소 2차 (사용자 "재개해"). `app/updater`(version_check/downloader/applier) 단위 test 분기 확장 — prerelease/semver ValueError + httpx ImportError/non-dict/예외 + content-length/empty chunk/callback 예외/cleanup + zip 유효성/platform/macOS·Windows swap·rollback. coverage 68→97%, 31 PASS, reviewer 차단 0, 회귀 0(2543 passed). (tests/app/updater)
- [2026-05-26 17:35:00] cycle 169.851 — 잔존작업 batch (사용자 "잔존작업 진행해"). codex §8-5 i18n labels dangling 회수(삭제된 `group_chat_view.py` 출처 주석 → live source `_chat_header_mixin.py:240`/`main_window.py:367` + orphan key `메시지를_입력하세요` 4 dict drop, i18n test 81 PASS, reviewer 차단 0) + token-usage-30d 재산출(sessions=5/$42562.61) + active-plan archive(완료 handoff 4종 completed/ 이동 + 상대링크 정합 broken 0). 회귀 0(2521 passed). (app/i18n · docs/operations · docs/exec-plans)
---

**문서 상태**: `active` · 최초 작성 2026-05-17 · M2 변경 이력 30행 캐시
운영. 30행 초과 시점부터 회전 + History.md 위임.
