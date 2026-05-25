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
- [2026-05-25 18:30:00] cycle 169.800 — 평가 2종 staleness refresh (hook_assessment_freshness — 792 이후 5+ commit) + SFU 진척 backfill. productization.md + vibe-coding.md + docs/html 2 mirror 를 사이클 169.800 marker + last_verified 18:30 동기 + 최근 갱신 note 에 cycle 169.793~799 진척 반영: P2 MIGRATION strict CI gate(doc 25=SQL 25) + Structure §11 ERD drift 회수(4→25 도메인 인벤토리) + **음성·영상 SFU 확장(9 peer+) 본격 착수** (cycle 796 Exec Plan + M3a protocol SFU 타입 + M3b sfu_room.py MediaRelay 1→2 forward loopback 3 PASS, 각 reviewer-agent 게이트 PASS, feature/sfu-group-call PR #12 WIP). 중요 발견: productization "mesh ≤ 8 ✅" 부정확 — group 음성·영상 = SFU greenfield 첫 결선. 점수 7.6/10 · 8.4/10 변동 부재 (docs/assessments · docs/html)
- [2026-05-25 18:25:00] cycle 169.797 — 평가 문서 반복 작업 방지 가드레일 추가. `tools/check_assessment_consistency.py` 신설 — HEAD cycle marker 누락, WBS 최신 row completed 와 M6 잔존 큐 충돌, MIGRATION strict PASS 와 DB strict 잔존 큐 충돌을 차단. `doc-gardener.yml` 에 평가 문서 consistency step 연결 + `tools/meta_enforce.py` 자기검증 등록 + `docs/policies/doc-gardening.md` 정책 반영. `current-project-review.md` 를 7.8/10, M6 ACTIVE, MIGRATION IMPLEMENTED, 반복 방지 ACTIVE 기준으로 갱신 (tools · .github/workflows · docs/policies · docs/assessments)
- [2026-05-25 18:20:00] cycle 169.796 — 음성·영상 SFU 확장(9 peer+) Exec Plan 초안 작성. planning-agent 산출물을 `docs/exec-plans/active/2026-05-25-voice-video-sfu-expansion.md` 로 등록해 Phase 6+ 확장 방향을 문서화 (docs/exec-plans/active)
- [2026-05-25 18:10:00] cycle 169.794 — Codex §4.2 Structure.md DB drift 회수. `Structure.md` + `docs/html/Structure.html` §11 ERD = cycle 138 P2P 시절 "4 테이블"(rooms/peers/file_meta/messages) 고착 → 실 schema 25 테이블 미반영 drift. chat-core 4 mermaid 필드 상세 retain + §11.3 "전체 25 테이블 도메인 인벤토리" 신설(auth 3·chat-core 4·device 4·emoji 2·bot 3·social 6·misc 3, 각 migration file 정본 ref). intro/§11.2/footer "4 테이블"→"25 테이블" 정정 + DDL SSoT = server/db/migrations + MIGRATION_MARIADB(--strict). HTML mirror 동시 갱신(§10-6). 음성·영상 SFU 확장(9 peer+) Exec Plan = planning-agent 별도 진행 (Structure · docs/html)
- [2026-05-25 17:55:00] cycle 169.793 — Codex P2 MIGRATION strict CI gate 승격 (사용자 directive "p2 진행 가능한 부분 진행" — codesign 은 프로젝트 최종 마감 시 결정 = 데몬스트레이션용 영구 제외, memory 강화). `MIGRATION_MARIADB.md` §3.5 신설 — 18 확장 테이블(devices/user_sessions/user_activity_log/emoji_packs+items/bot_escalations/app_versions/friends/message_reactions/folders+chats+invites/bots+tokens/device_tokens/read_states/user_contacts/streaming_oauth_tokens) `CREATE TABLE` 등재(DDL+필드 COMMENT 정본=migration 0002~0016 ref). `check_migration_tables.py --strict` doc 25=SQL 25 통과 → `doc-gardener.yml` MIGRATION step forward-only→`--strict` CI gate 승격(actionlint 0). codesign = P2 잔존에서 영구 제외(최종 마감 시점만 재활성) (MIGRATION_MARIADB · .github/workflows)
- [2026-05-25 17:45:00] cycle 169.792 — 평가 2종 staleness refresh (Stop hook hook_assessment_freshness — vibe 169.785 이후 6 commit, prod 787 이후 4). productization.md + vibe-coding.md + docs/html 2 mirror 를 cycle 169.792 marker(사이클 169 + last_verified 17:45) 동기 + 최근 갱신 note 에 cycle 169.787~791 진척(Codex P0/P1 auto-completable 소진 + M6 post-commit hook + doc-lint gate 교훈) 반영. 점수 productization 7.6/10 · vibe-coding 8.4/10 변동 부재 (docs/assessments · docs/html)
- [2026-05-25 17:40:00] cycle 169.791 — cycle 169.790 변경이력 entry 의 인용 literal 재-위반 회수 (changelog 본문이 위반 문자열을 그대로 인용해 BPE 재발 → 인용 제거 rephrase). doc-lint EXIT=0 gate 확인 후 commit (이번엔 push 전 검증). 교훈 = 위반 문자열 인용 금지 (README · History)
- [2026-05-25 17:35:00] cycle 169.790 — BPE 측단독 회수 (cycle 169.789 MANUAL_TESTS §2.9 의 capture/dispatch 측단독(U+CE21) 표기 2건 → "쪽", doc-lint EXIT=1 push 후 즉시 정정). doc-lint PASS 재확인 (docs/exec-plans/active)
- [2026-05-25 17:30:00] cycle 169.789 — Codex P1 원격 데스크탑 M4 수동 검증 절차 문서화 (사용자 directive "잔존작업 다 진행", Codex P1 #5). `docs/exec-plans/active/MANUAL_TESTS.md` §2.9 신설 — 원격 M4 의 실 OS + 물리 2 장비 사용자 직접 ack 항목(macOS Screen Recording/Accessibility 권한 + friend P2P 세션 + `_remote_data_channel` 실 결선 + HOST grant 주입 + controller 화면 표시/클릭 실 적용 visual ack + revoke). 자동 검증 완료분(G2 headless loopback) 과 분리. M4 = G3 사용자 게이트 — 실 OS/물리 장비 의존이라 Claude 자동 불가, 본 문서가 수동 절차 정본 (docs/exec-plans/active)
- [2026-05-25 17:15:00] cycle 169.788 — Codex P1 NFR-04 실 server chaos test (사용자 directive "잔존작업 다 진행"). `tests/integration/test_signaling_chaos_reconnect.py` 신설 1 PASS — 실 aiohttp WebSocket server(동적 port) 1회차 연결 강제 close(1011) → SignalingClient 비정상 drop 감지 → RECONNECTING 상태 → backoff 재연결 → 2회차 연결 + 마지막 JOIN 식별자 reJOIN(server 가 room-chaos/peer-X 재수신) 검증. 기존 test_signaling_reconnect(FSM mock 격리)와 달리 실 WS 왕복 chaos. StatusBar ERROR 미오표시(RECONNECTING 정상 경로) 정합. test-only(signaling_client = cycle 169.775 reviewer PASS분 무변경) (tests/integration)
- [2026-05-25 17:00:00] cycle 169.787 — Codex P0 마감 잔존 batch (사용자 directive "잔존작업 다 진행"). (1) **M6 enforcement 완결** — `tools/wbs_post_commit.py`(post-commit hook: commit subject cycle169.N → wbs_tasks 1행 자동 INSERT, 멱등) + `tools/install_wbs_hook.sh`(.git/hooks/post-commit 설치) 신설 + 설치. wbs cycle 745~786 누락 backfill + status `done`→`completed` 통일(278 row 전부 completed) + finished_at NULL 42 row 보정(wbs_view 정합). reviewer-agent 게이트 PASS(F1 finished_at fix 반영). (2) **productization 본문 freshness** — §2 강점 bullet 의 stale metric(2280/2408 PASS·80.75/87.76% cov) → 현 ≈2490 PASS·90.45% 정정 + historical 표기. md/html pair 동기. `data/` gitignored = wbs local only (app/tools · docs/assessments · docs/html)
- [2026-05-25 16:40:00] cycle 169.786 — 다음 세션 인계 자료 갱신 (사용자 directive "다음 세션에 인계할 내용 정리"). `docs/exec-plans/active/2026-05-17-session-handoff.md` §1.1 을 cycle 169.768~785 세션 요약으로 rewrite + intro 시점 169.785(`438d520`) 갱신. 핵심 성과((a) DI refactor 무효 확정+skip 38→24 / Codex P0 signaling 재연결 / (c) 원격 M3+G2 완결 PR #10 / reviewer 게이트 정책 / M6 활성 / Codex 7.6 환류) + 다음 세션 Codex 작업 큐(P0 M6 hook + productization 본문 / P1 원격 M4 G3 게이트 + NFR-04 chaos / P2 DB·배포) + 병렬 Codex 주의 명시 (docs/exec-plans/active)
- [2026-05-25 16:25:00] cycle 169.785 — vibe-coding 평가 staleness refresh (Stop hook hook_assessment_freshness, 132cb2b 이후 6 commit). `docs/assessments/vibe-coding.md` + `docs/html/vibe-coding.html` 를 cycle 169.785 marker 로 갱신 — 직전 169.779~784 진척(원격 M3 완결 + reviewer-agent 게이트 모든 feat 의무 정책 확립 + reviewer F1 회귀 회수 + M6 활성 + Codex 7.6/10 외부평가 환류) 관측 반영. 점수 8.4/10 변동 부재(process 성숙). 약 2490 PASS (docs/assessments · docs/html)
- [2026-05-25 16:20:00] cycle 169.784 — Codex 전면평가(7.6/10) P0 doc-freshness 반영 (사용자 directive "codex 평가문서 정독해서 반영해"). (1) Specification.md FR-10 trace row 정정 — `app/net/signaling_client.py (예정)` → 구현 완료(signaling_client + app_state + status_bar + test_signaling_reconnect, cycle 169.775 IMPLEMENTED). (2) README 과거 표현 정정 — L52 "시그널링 자동 연결 수행하지 않는다"(거짓, 자동 재연결 구현됨) + L220 rtc "(예정)"(app/rtc 존재) + 운영 8 문서 "(작성 예정)" 5건(CheckList/History/EXTENSION_GUIDE/MIGRATION/CLAUDE 전부 존재) 링크화. (3) productization.md/html 평가 pair fingerprint 동기 — md H1 + 사이클 169.783 Korean marker + html title/last_verified 169.783/16:05 (Codex 783 갱신 후 html 미동기 + 본문 역사적 "사이클 6" false-match 해소). 잔존 = productization 장문 본문 전수 783 rewrite + MIGRATION/Structure DB strict (Codex P1/P2) (README · Specification · docs/assessments · docs/html)
- [2026-05-25 16:05:00] cycle 169.783 — 평가 문서 freshness 회수 (사용자 directive "평가문서 업데이트 해줘 claude 가 바로 작업 할 수 있게"). `docs/assessments/current-project-review.md` 전면 갱신 — 7.6/10, cycle 169.782 main 기준, SignalingClient 재연결 구현/StatusBar 회귀 회수/원격 데스크탑 M3+실 aiortc loopback/M6 backfill 반영 + Claude 즉시 작업 큐(P0 문서 freshness, M6 enforcement, 원격 M4, NFR-04 실 서버 chaos) 명시. `docs/assessments/productization.md` 상단 snapshot + 종합 row 7.6/10 동기 (docs/assessments)
- [2026-05-25 15:50:00] cycle 169.782 — (c) M3 잔존 완결: G2 aiortc 실 DataChannel loopback + M3c UI accept 결선 (사용자 directive "m3 잔존 진행해"). G2 = `tests/integration/test_remote_session_loopback.py` — 실 RTCPeerConnection 2 peer + DataChannel 위 RemoteSessionRunner host capture→frame 채널→controller on_frame + controller send_input→input 채널→host grant 게이트→apply 검증(1 PASS, mock backend). M3c = `app/ui/_chat_header_mixin.py` `_start_remote_session(role, peer)` 신설 + `_on_remote_request`(controller)/`_on_remote_connect`(host) 의 RemoteCallDialog accepted_signal→runner 기동 결선 + mock isolation test 4 PASS(role 매핑 + 채널 no-op/결선). reviewer-agent 게이트 선행(정책) → feature branch + PR(직접 main 미머지). remote 회귀 150 PASS. 잔존=M4 실 OS capture/dispatch 수동 ack(G3 게이트 후) (app/ui · tests/integration · tests/app/ui)
- [2026-05-25 15:35:00] cycle 169.781 — M6 WBS backfill (사용자 directive "활성 — 누락 backfill", dereliction-detector MEDIUM 회수). `data/wbs.sqlite` `wbs_tasks` 가 cycle 169.744 이후 등록 중단 → cycle 169.745~781 누락 37 row INSERT (directive=commit subject, status=completed, commit_sha=cycle 매핑 sha). M6 활성 확정(CLAUDE.md §8 단서 해제). 236→273 row (data)
- [2026-05-25 15:30:00] cycle 169.780 — reviewer-agent F1(MED) 회귀 회수 (사용자 directive "자동 구간도 reviewer-agent 가 리뷰를 해야해" → feat 775/777/779 사후 일괄 reviewer 게이트 PASS, F1 1건 fix). cycle 169.775 가 `app/core/app_state.py` 에 RECONNECTING 추가했으나 `app/ui/status_bar.py` `_VALID_STATES` 미동기 → 재연결 중 RECONNECTING emit 시 "ERROR" 오표시 회귀. status_bar `_VALID_STATES` 에 RECONNECTING 추가 + docstring 동기. 회귀 test `tests/app/ui/test_status_bar_states.py` 3 PASS (widget 미인스턴스화 — hang 회피, app_state 정본 집합 정합 검증). reviewer 종합 PASS(M1~M7 0위반, 금지패턴 0). F2/F3 LOW backlog (app/ui · tests/app/ui)
- [2026-05-25 15:10:00] cycle 169.779 — (c) M3a+M3b 진행: permission on-channel handshake + coord_transform 결선. `app/remote/remote_handshake.py` 신설 — control 채널 권한 protocol(REQUEST/GRANT/DENY/REVOKE wire JSON) + `grant_request`(request→grant, expiry=now+duration) + `verify_revoke`(hmac.compare_digest 상수시간 대조). `app/remote/session_runner.py` host input dispatch 에 `transform_coordinates` 결선 — controller 화면 좌표 → host 화면 좌표 보정(DPI/Retina backing scale) 후 apply. test `test_remote_handshake.py` 12 PASS + `test_session_runner.py` coord 2 PASS 추가 = remote 146 PASS. 잔존 M3=UI accept 결선(`_on_remote_request` accept→runner.start, mock isolation) + aiortc 실 DataChannel loopback(G2) (app/remote · tests/app/remote)
- [2026-05-25 14:55:00] cycle 169.778 — 평가 6 file staleness refresh (Stop hook hook_assessment_freshness, af09733 이후 6 commit). productization.md + vibe-coding.md + docs/html 2 mirror 를 cycle 169.774~777 진척 반영 갱신 — (a) DI refactor 무효 확정+skip 14건 은퇴(38→24) + Codex P0 SignalingClient 재연결(test 9 PASS, FR-10 [x]) 가용성 진척 + (c) RemoteSessionRunner orchestration core(headless 13 PASS) Phase 5 차별화 1차 진입. 약 2485 PASS. 종합 6.7/10(productization) + 8.4/10(vibe-coding) 유지 (docs/assessments · docs/html)
- [2026-05-25 14:50:00] cycle 169.777 — (c) M2 RemoteSessionRunner 신설 — 원격 데스크탑 orchestration core. `app/remote/session_runner.py` — host(capture loop→RemoteFrame encode→frame 채널 송신 + input 수신→grant 게이트(check_grant_active)→apply_events)/controller(frame 수신→decode→on_frame 콜백 + send_local_input→encode→input 채널) loop + frame/input 와이어 직렬화(struct 헤더 frame + JSON input) + capture/input backend DI + send callable 추상화(실 DataChannel/Mock 양쪽 결선). headless test `tests/app/remote/test_session_runner.py` 13 PASS(round-trip/capture loop/frame recv/grant 게이트/input 거부/host↔controller mock loopback). remote 영역 회귀 132 PASS. 잔존=aiortc 실 DataChannel loopback test(G2) + permission on-channel handshake(M3) + UI accept 결선(M3) (app/remote · tests/app/remote)
- [2026-05-25 14:35:00] cycle 169.776 — (c) Phase 5 원격 데스크탑 실 binding Exec Plan 신설 (사용자 directive "원격 데스크탑 실 binding 진입"). `docs/exec-plans/active/2026-05-25-remote-desktop-real-binding.md` (planning-agent 산출, status draft) — 핵심 발견: 빌딩블록 절반만 사실(capture.py/input_forward.py 실 OS binding 구현 단 Mock-test 만, screen_capture.py/input_dispatch.py skeleton 중복=deprecate 대상), 진짜 부재=RemoteSessionRunner orchestrator(dialog signal slot 미연결 + permission 채널 교환 코드 부재), e2e 8 PASS=mock orchestration(실 binding 아님). 자동(M1~M3 aiortc loopback+Mock+offscreen headless) vs 수동(M4 macOS 권한+PyObjC+실 장비 사람 눈) 분리 + G3 사용자 게이트. frame/input 2 채널 + Pattern A(HELP) 만 + file_sender backpressure 재사용. BPE 측단독 5건 쪽 정정 후 doc-lint PASS (docs/exec-plans/active)
- [2026-05-25 14:20:00] cycle 169.775 — Codex P0 회수: SignalingClient 실 자동 재연결(backoff + reJOIN) 구현 (사용자 directive "codex의 P0 진행"). `connect()` 단발 + recv loop 종료=DISCONNECTED 한계를 해소 — 비정상 drop 감지 시 지수 backoff(base 0.5s ×2, cap 30s, 무한/max_attempts) 재연결 + 마지막 JOIN 식별자로 reJOIN 복구 + RECONNECTING 상태 신설. disconnect() 가 진행 중 재연결 취소(의도적 종료 구분). `app/net/signaling_client.py` + `app/core/app_state.py`(RECONNECTING valid state) + 통합 test `tests/app/net/test_signaling_reconnect.py` 9 PASS + CheckList FR-10 `[~]→[x]`. net+core 회귀 87 PASS (app · tests · CheckList)
---

**문서 상태**: `active` · 최초 작성 2026-05-17 · M2 변경 이력 30행 캐시
운영. 30행 초과 시점부터 회전 + History.md 위임.
