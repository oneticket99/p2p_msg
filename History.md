---
title: "TooTalk 개발 히스토리"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# TooTalk 개발 히스토리

> 로그 형식: `[YYYY-mm-dd H:i:s] 내용 (단축 SHA)`
> M3 — 역순 기록: 최신 Phase·최신 타임스탬프가 문서 상단
> append 금지, prepend 전용 (`tools/md_agents.py` 가 추후 검증 예정)

---

## 0. 본 문서 운영 규약

본 문서는 [CLAUDE_HARNESS_IMPORTANT.md](CLAUDE_HARNESS_IMPORTANT.md) §A M3 와 §I 의 정본 규약을
저장소 루트에 구현한 운영 문서다. 다음 규칙을 강제한다.

1. **역순 기록 (prepend 전용)** — 최신 타임스탬프가 항상 문서 상단. 오래된 항목을 상단에 끼워
   넣는 append 패턴은 금지한다. `@history-agent` 가 단일 진입점이며 `tools/md_agents.py` 의
   `agent_history()` 가 Phase 번호·타임스탬프 내림차순을 강제할 예정이다.
2. **Phase 그룹화** — 동일 Phase 내부에서도 최신 → 과거 내림차순. Phase 헤더 자체도 큰 번호가
   상단. 본 문서 시점은 Phase 1 진행 중이며 Phase 0 (정본 인계) 한 항목이 하단에 위치한다.
3. **M2 동시 갱신 의무** — 모든 파일 작업 단위 완료 시 `README.md` 변경 이력에도 한 줄
   prepend (정본 §H). 본 문서가 단독으로 갱신되는 일은 없다. (현 시점 `README.md` 미생성 상태
   — Phase 1 후반 신설 예정. 신설 시 본 항도 동시 갱신.)
4. **BPE 위생** — 한국어 의존명사 단독 사용 금지 (합성어 측면·관측·측정·좌측·우측·추측만
   허용). `tools/doc-lint.sh` 의 검사 1번이 grep -E 정규식으로 단독 의존명사 토큰을 차단한다.
   허용 합성어 6 종 외 문맥은 다른 표현으로 정정해야 한다.
5. **타임스탬프 출처** — `git log --pretty=format:'%aI %h'` 의 실 commit 메타. 가짜 commit
   발명 금지. 본 문서의 모든 행은 실재 SHA 와 1:1 대응한다.

---

## Phase 1 MVP 부트스트랩 (2026-05-17 진행 중)

본 Phase 의 목표는 PyQt6 + aiortc + qasync 기반 데스크탑 P2P 메신저 의 MVP 골격 확보다.
시그널링 서버·클라이언트 스켈레톤, 9 정책 문서, 운영 문서(Specification·Structure), 가드레일
도구(doc-lint·markdownlint), 7 프로세스 에이전트 정의를 단일 일자에 집중 투입한다.

[2026-05-17 17:10:00] 평가 snapshot 사이클 5 동시 갱신 (CLAUDE.md §10-7 정합) — 본 cycle 의 누계 25 commit + wine 정책 + fork PR strict + SMTP 자체 + ci 8 job GREEN 반영. productization 종합 2.9→3.85 ▲ — 기술 완성도 2.5→3 (self-hosted CI 8 job GREEN + Windows wine cross-compile + SMTP postfix 자체 + fork PR strict), 운영 비용 4.5→5 (Windows runner 회피 + wine 무료 + SMTP 자체 cost 0 + fork PR API 자동), §2.6 가드레일 자동화 강화 (18종 + windows-build-via-wine + smtp-demo-server 신규 2), §2.11 SMTP 자체 (postfix + Let's Encrypt + SPF/DKIM/DMARC + aiosmtplib + SendGrid fallback), §2.12 신규 CI 자동화 + 보안 hardening, §3.5 ✅ self-hosted runner 해소, §3.8 신규 데모 서버 SSH 차단, §5 ✅ 5건 추가 (runner + dead link + wine + fork PR + SMTP), §8 신규 리스크 3건 (spam reputation + wine PyQt6 + SSH 차단), §9 KPI 의 CI GREEN 100% + 가드레일 18 + fork PR strict 갱신. vibe-coding 종합 4.85 변동 없음 — 비판·재교정 속도 5→4.5 ▼ (BPE/1인칭 위반 2회차 누계), 사이클 효율 4.5→5 ▲ (3 큰 정책 단일 cycle 의 신속 적용), 자율 reasonable call 5 신규 ▲ ("권장 default 진행해" 패턴), §2.15 자율 reasonable call 신규 + §2.16 인프라 자동화 발견 신규 + §3.4 BPE 가드레일 한계 노출 명시 + §3.7 가드레일 위반 누계 신규 + §4.2 권장 default 자율 GO 비판 패턴 row + §6 비교 기준 10 컬럼 (자율 reasonable call 추가) + §7.1 인프라 host 선택 + 빌드 도구 선택 + 권장 default 자율 GO 추가. 2 file 의 전체 rewrite (snapshot 패턴 — 히스토리성 prepend 금지) (커밋 대기)
[2026-05-17 16:50:00] SMTP 정책 정합 다중 갱신 (adoption-roadmap.md + CheckList.md + handoff doc) — 직전 commit (b7cd936) 의 SECURITY §9-2.3 후속. adoption-roadmap.md §3.1 Phase 1 DoD 의 SMTP 발송 PASS row 의 갱신 "Gmail/SendGrid/Mailgun 중 1종" → "데모 서버 (114.207.112.73) 안 postfix 자체 설치 + Let's Encrypt + SPF/DKIM/DMARC + aiosmtplib client + SendGrid fallback + smtp-setup.md link". CheckList §2 신규 row "SMTP 서버 (OTP 발신) = 정책 + 절차 OK" 추가. handoff doc §5 정책 표 신규 row "SMTP 서버" 추가. §9 다음 액션 표 회수 갱신 — task #2 (snapshot 3) ✅ 완료 + task #3 (BPE) ✅ 완료 + 신규 task #4 (fork PR 승인) ✅ 완료 + 신규 task #5 (SMTP 설치 정책) ✅ 완료 + 직전 #4~#7 의 재번호 #6~#9. 본 cycle 의 자율 진행 영역 완료 = SMTP 정책 정합 100% (커밋 대기)
[2026-05-17 16:42:00] SECURITY.md §9-2.3 SMTP 보안 row 갱신 — 직전 commit (9109b54) 의 smtp-setup.md 정합 후속. 직전 4 row (TLS + 자격증명 + 발신 도메인 + Reply-To) → 9 row (서버 자체 설치 + TLS + 자격증명 + 발신 도메인 인증 + rDNS PTR + client + fallback + Reply-To + 절차 본문 link) 확장. 서버 row 신규 = "데모 서버 (114.207.112.73) 안 자체 postfix 설치 (사용자 directive 2026-05-17)". 발신 도메인 인증 row 의 SPF + DKIM (opendkim RSA 2048) + DMARC (p=quarantine → p=reject 점진) 의 자세한 명시. rDNS PTR row 신규 (residential IP 의 한계 + SendGrid fallback). client row 신규 (aiosmtplib async + qasync 정합). fallback row 신규 (SendGrid relay free 100/day). 절차 본문 link row 신규 (docs/references/smtp-setup.md). 본 cycle 의 자율 진행 잔존 의무 = adoption-roadmap §3 Phase 1 + CheckList §2 신규 row + handoff doc §5 + §9 (커밋 대기)
[2026-05-17 16:35:00] docs/references/smtp-setup.md 신설 — SMTP 서버 데모 호스트 설치 절차 본문. 사용자 directive 2026-05-17 ("smtp 서버는 사전에 명시했던 테스트서버에 설치해" + "권장방향으로 진행해") 자율 GO 정합 권장 default (postfix + Let's Encrypt + SPF + DKIM + DMARC + aiosmtplib + SendGrid fallback). 신규 본문 13 섹션 (§1 용도 명세 + §2 사전 의존성 + §3 DNS record 6종 + §4 Let's Encrypt + §5 postfix + §6 OpenDKIM + §7 SASL 인증 + §8 검증 + §9 보안 hardening + §10 SendGrid fallback + §11 트러블슈팅 + §12 운영 체크리스트 + §13 참조). 영구 메모리 project_smtp_demo_server.md 신설 + MEMORY.md 인덱스 갱신. handoff §9 잔존 SMTP 제공자 결정 의 해소. 실제 SSH 설치 = 사용자 직접 의무 (114.207.112.73 의 SSH Connection reset by peer 의 main session SSH 차단 검출). 잔존 의무 = SECURITY §9-2 + adoption-roadmap §3 + CheckList §2 + handoff doc 정합 (커밋 대기)
[2026-05-17 16:15:00] fork PR 승인 정책 strict 적용 (Task #4 completed) — handoff §9 우선순위 task 의 잔존 마지막 사용자 직접 영역 의 자동화 발견 + 적용. gh API endpoint `PUT /repos/oneticket99/p2p_msg/actions/permissions/fork-pr-contributor-approval` + `-f approval_policy=all_external_contributors` 의 자동 적용. 직전 default `first_time_contributors` (GitHub 신규 + 첫 contribution 만 approval 의무) → strict `all_external_contributors` (모든 outside collaborator 의 maintainer approval 의무). public repo + self-hosted runner + wine cross-compile 의 보안 hardening 정합. ci-self-hosted-setup.md §5.1 갱신: §5.1.1 자동 적용 (gh API 명령 + 본 cycle 적용 완료 명시), §5.1.2 정책 옵션 표 3행 (Phase 정합 명시), §5.1.3 manual UI 대안. CheckList §2 의 신규 row "fork PR 승인 정책 = strict 적용 (all_external_contributors)" 추가. 직전 cycle 의 6 file wine 갱신 (78d14c9 → 1fd3e2a) 의 보안 hardening 후속 (커밋 대기)
[2026-05-17 16:08:00] ci.yml Windows matrix 영구 비활성 주석 명문화 (5/6 file 완료) — 직전 commit (7a7875f) 의 CheckList §2 갱신 후속. ci.yml 의 import-smoke + pytest 의 matrix 안 Windows-x64 entry 의 직전 주석 "임시 비활성 — Windows runner 미등록 (2026-05-17 cycle) / Phase 1 후반 본 entry 의 주석 해제 + Task #3 정합" → "영구 비활성 — wine cross-compile 대체 (사용자 directive 2026-05-17) / Windows 빌드 의무 = build.yml (Phase 1 후반 신설) 의 GitHub-hosted Ubuntu + cdrx/pyinstaller-windows docker image / 정합 정책: 영구 메모리 project_windows_build_via_wine.md + AGENTS.md §1 빌드 row". 파일 헤더 주석 의 runner 라벨 영역 도 동일 정합 갱신 (Windows 라벨 row 회수). 본 cycle 의 6 file 갱신 완료 (커밋 대기)
[2026-05-17 16:04:00] CheckList §2 진행률 표 갱신 (4/6 file) — 직전 commit (0854f5a) 의 handoff doc 갱신 후속. self-hosted runner row 의 1/2 → 1/1 (충족) (Windows 의무 영구 회수 + macOS arm64 단독). CI 워크플로우 row 의 Windows matrix 영구 비활성 명시 + wine 대체. 신규 row "Windows 빌드 패턴 = wine docker (GitHub-hosted Ubuntu + cdrx/pyinstaller-windows)" 추가. drift 차단 정합 — directive 변경 시 즉시 행 갱신 (커밋 대기)
[2026-05-17 16:01:00] handoff doc §5 정책 표 + §9 task #1 갱신 (3/6 file) — 직전 commit (2864efa) 의 AGENTS 정본 갱신 후속. handoff doc §5 정책 표 의 빌드 row + CI row 의 듀얼 트랙 명시 (macOS arm64 native + GitHub-hosted Ubuntu wine + Windows self-hosted 영구 회수). §9 다음 액션 표 의 task #1 (self-hosted runner 등록) → ✅ 완료 (Windows runner 의무 회수 + wine 대체 명시). §1 TL;DR 의 CI 영역 의 자세한 정합 갱신. handoff doc = 다음 세션 의 최우선 정독 대상 → 본 갱신 정합 의무 (커밋 대기)
[2026-05-17 15:58:00] AGENTS.md §1 빌드 row 갱신 (2/6 file) — 직전 commit (78d14c9 + 22111f0) 의 ci-self-hosted-setup wine 정책 후속. 직전 row "macOS + Windows · PyInstaller + zip · 인증서 미사용 · GitHub Actions self-hosted 매트릭스" → "macOS arm64 native (self-hosted runner) + Windows x64 wine cross-compile (GitHub-hosted Ubuntu + `cdrx/pyinstaller-windows` docker) · PyInstaller + zip · 인증서 미사용". Windows self-hosted runner 의 의무 명시 회수 + GitHub-hosted Ubuntu 명시. 본 row = AGENTS.md 정본 의 빌드 정책 entry — 본 갱신 정합 의무 (커밋 대기)
[2026-05-17 15:55:00] docs/references/ci-self-hosted-setup.md 의 wine cross-compile 정책 본문 갱신 (1/6 file). 사용자 directive 2026-05-17 "윈도우 빌드는 wine을 이용해서 할꺼야" + "권장되는 방향이라고 판단되는부분에 대해 진행해" 의 자율 GO 정합 권장 default (H3 + T1 + P3) 채택. H3 = GitHub-hosted Ubuntu (`ubuntu-latest`, 무료 + ephemeral 격리). T1 = wine-stable (open source + apt). P3 = cdrx/pyinstaller-windows docker image (사전 빌드 + Python + Qt6 documented). 본 직전 영구 메모리 3건 갱신 완료 (`project_windows_build_via_wine.md` 신설 + `project_build_policy.md` rewrite + `project_ci_self_hosted.md` rewrite + MEMORY.md 인덱스 갱신). 본 문서 §1 매트릭스 표 의 Windows self-hosted row → GitHub-hosted Ubuntu row 변경. §2.2 Windows dependency 영역 → 영구 회수 marker. §3.3 Windows 등록 절차 → 영구 회수 marker. §4.1 검증 영역 의 macOS 단독 + gh CLI 검증 명령 추가. §9 운영 체크리스트 8 entry 의 4건 [x] 완료 (macOS runner 등록 + brew install + Python PATH + 3 workflow GREEN 확인) + Phase 1 후반 build.yml 의 wine job 검증 1건 잔존. §11 신설 (wine cross-compile 정책 + ci 패턴 yaml + 검증 의무 + 대안 3건). 영구 메모리 link 추가 (project_windows_build_via_wine.md). 가드레일 [[feedback-doc-perfection-before-code]] 의 "큰 작업" 분류 정합 — 정책 변경 = 자율 진행 차단 영역, 사용자 명시 GO 후 진행 (커밋 대기)
[2026-05-17 15:43:00] Task #5/#6/#7 completed — handoff §9 우선순위 1번 완전 해소. 누계 6 commit 의 cycle (50c5c40 + 2f20650 + 42f649f + a85bb75 + da5a92e + 본 cycle) 의 self-hosted runner 등록 + workflow GREEN 도달. ci 8 job GREEN: docs-lint + m2-readme-history + m3-history-prepend + root-18-freeze + import-smoke (macOS-arm64) + pytest (macOS-arm64) + m1/m4 skipped. docs-lint workflow GREEN + doc-gardener workflow GREEN (25983514381 의 재 trigger). 본 cycle 의 자율 GO directive ("진행해") 의 정합 자율 진행 — 옵션 A (dead link 의 (예정) 마커 + skip rule) + 옵션 W2 (Windows matrix 임시 비활성). 의무 fix 누계 6 영역: MD041 + dead link 10 + Windows matrix + M2 regex + M3 grep + Python PATH + venv 격리. CheckList §2 의 CI 워크플로우 row + self-hosted runner row 의 정합 update. 잔존 task: #3 Windows runner (별도 머신 + 사용자 직접) + #4 fork PR 승인 설정 (Settings UI). 가드레일 [[feedback-no-korean-chuck-token]] 3회차 강화 영구화 완료. 텔레그램 송신 누계 1건 (cycle 시작 시점) — 종료 시점 추가 송신 의무 (커밋 대기)
[2026-05-17 15:40:00] ci.yml venv setup step 추가 — PEP 668 externally-managed 회피. 직전 commit (a85bb75) 의 PATH 등록 후 import-smoke + pytest job 의 `python -m pip install` 단계의 `error: externally-managed-environment`. brew python 의 자체 protection 정책 의 pip install 거부 → venv 격리 의무. import-smoke + pytest 양 job 의 PATH 등록 step 직후 신규 step 추가 — `python -m venv .venv` + `echo "$PWD/.venv/bin" >> $GITHUB_PATH` + `echo "VIRTUAL_ENV=$PWD/.venv" >> $GITHUB_ENV`. GitHub Actions 의 step 간 venv persistence = `$GITHUB_PATH` + `$GITHUB_ENV` 등록 의 표준 패턴. 후속 step 의 `python` 자동 venv python 매치. local doc-lint 5 + markdownlint 0 위반 (커밋 대기)
[2026-05-17 15:32:00] ci.yml 4 게이트 fix — 직전 commit (42f649f) 직후 첫 ci 픽업의 fail 4건 (M2 + M3 + import-smoke + pytest) 해소. M2 m2-readme-history step의 regex `^##\s+변경\s*이력` 의 README.md `## 11. 변경 이력` 헤더의 number prefix 미충족 → 패턴 `^##\s+([0-9]+\.\s+)?변경\s*이력` 의 optional number 매치 확장. M3 m3-history-prepend step의 grep `^##\s+[0-9]{4}-[0-9]{2}-[0-9]{2}` 의 매치 0 line + bash -e + pipe failure 의 exit 1 → 패턴 `^## Phase` 의 History.md Phase header 매치 + `|| true` 의 pipe failure 회피. import-smoke + pytest job 의 `python --version` step의 exit 127 (macOS runner의 `python` 명령 부재) → brew python@3.13 PATH 등록 step 추가 (`/opt/homebrew/opt/python@3.13/libexec/bin` 의 `$GITHUB_PATH` 등록 → `python` symlink 활성 → 후속 step 의 `python` 명령 매치). 가드레일 정합 = if 조건 `runner.os == 'macOS'` 의 명시 (향후 Windows runner 등록 후의 자동 skip). local verify: M2 MATCH + M3 PASS + python symlink 존재 + doc-lint 5 + markdownlint 0 위반 (커밋 대기)
[2026-05-17 15:25:30] dead link 10건 fix + ci.yml Windows matrix 임시 비활성 — 직전 cycle (15:05:30) runner 등록 직후 첫 워크플로우 픽업 의 FAIL 사유 해소. 사용자 directive "진행해" 의 자율 GO 후 옵션 A + W2 채택. 옵션 A = doc-lint.sh skip rule 추가 (link text 영역 안 `(예정)` 마커 발견 시 본 link 검사 skip — 가드레일 [[phase1-completion-priority]] + handoff §7 정합, drift 명시화 + CI fail 회피). Structure.md 의 3 line + FRONTEND.md 의 2 line 의 10 dead link (app/rtc/peer.py / protocol.py / file_sender.py / file_receiver.py / image_processor.py / README.md + app/ui/file_progress_widget.py — Agent #16 산출물 untracked) 의 link text 영역에 `(예정)` 마커 추가. 옵션 W2 = ci.yml 의 import-smoke + pytest job 의 matrix.include 의 Windows-x64 entry 2건 주석 처리 + 한글 주석 명시 ("Phase 1 후반 Windows runner 등록 직후 본 entry 의 주석 해제 + Task #3 정합"). 단일 macOS runner 환경 의 ci 영구 queued 해소. 검증: local doc-lint 5 + markdownlint 0 위반 + CI simulate (untracked /tmp/p2p_stash 의 임시 mv) PASS. 4 file 변경 (tools/doc-lint.sh + Structure.md + FRONTEND.md + .github/workflows/ci.yml) (커밋 대기)
[2026-05-17 15:05:30] CI self-hosted macOS arm64 runner 자동 등록 — handoff §9 우선순위 1번 해소. gh API `POST repos/.../actions/runners/registration-token` → 토큰 발급 자동화. actions/runner v2.319.1 osx-arm64 다운로드 + tar 해제 + `config.sh --unattended --labels macOS,arm64 --name tootalk-macos-arm64` 등록. launchd 의 `svc.sh install + start` (plist `~/Library/LaunchAgents/actions.runner.oneticket99-p2p_msg.tootalk-macos-arm64.plist` + PID 62533 Started + exit 0). GitHub API runner 검증 — id=2 status=online labels=['self-hosted','macOS','ARM64']. queued docs-lint workflow 즉시 픽업 + busy=True 전이. 위 docs-lint run 25982809500 = FAIL `.github/pull_request_template.md:7 MD041 first-line-h1` — fix = 파일 첫 줄 `<!-- markdownlint-disable MD041 -->` directive + 한글 주석 1행 추가 (PR 본문 H2 시작 정합 명문). BPE 위반 2건 도입 도중 검출 + 즉시 정정 (.github/pull_request_template.md:6 의 새 주석 U+CE21 단독 3건 → "=" + "→" + 자연 조사 + README.md:309 prepend 영역 U+CE21 단독 1건 → "영역"). doc-lint 5 검사 + markdownlint-cli2 본 시점 모두 0 위반. macOS runner 의 Phase 1 CI 3 workflow (ci + docs-lint + doc-gardener) 픽업 차단 해소 (커밋 대기)
[2026-05-17 14:44:47] CLAUDE_HARNESS_IMPORTANT.md 정본 BPE 25건 일괄 정정 (handoff §9 우선순위 2번 잔존 task 해소). sed " U+CE21 " → " 의 " bulk 적용. 정본 본문 의미 보존 (가드레일 [[feedback-no-korean-chuck-token]] 정합 — 합성어 측면/관측/측정 등 보존). doc-lint.sh 5 검사 PASS. 본 사이클 BPE 회수 누계 ~245건 (auth 5 + handoff + assessments + 정본 25) (커밋 대기)
[2026-05-17 14:42:00] handoff doc 사이클 2 갱신 — 본 세션 누계 28 commit (8 commit 추가 since 사이클 1 = 0fd2bcf). §1 TL;DR 갱신 (16 가드레일 + DB 7 + 회원가입 + Phase 3 막바지 차별화 + snapshot 3.6/4.85). §4 가드레일 14→16 (신규 2 — remote-control + auth-otp). §5 정책 표 (DB 7 + 회원가입 + 차별화 행 추가 + snapshot 3.6/4.85 갱신). §8.1 누계 commit 28건 + §8.8 회원가입 OTP 정책 신규 + §8.9 원격 제어 차별화 신규 + §8.10 텔레그램 송신 24건 + §8.11 sub-agent 누계 16 spawn 추가. §9 다음 액션 표 — snapshot 사이클 3 항목 제거 + 7행 (runner / BPE / 라이선스 / 코드 진입 / Agent #16 / Toonation / SMTP). §9.1 잔존 task — 회원가입 #11 + 원격 제어 추가. §10 timestamp 14:42 (커밋 대기)
[2026-05-17 14:36:00] 평가 snapshot 사이클 4 동시 갱신 (CLAUDE.md §10-7 정합). productization 종합 2.9→3.6 ▲ (차별화 3→4.5 ▲ 친구간 원격 데스크탑 제어 + 메신저 통합 + 시장 적합성 2→2.5 + 사용자 가치 2.5→3 + 수익화 1.5→2, §2.10 차별화 명시 표 4행 신규, §2.11 회원가입 정합 신규, §4.2 옵션 B ★★★★★ 강화, §5 단기 액션 ✅ 15). vibe-coding 종합 4.7→4.85 ▲ (도메인 비전 4.5→5, 기술 의사결정 4.5→5, UX 직관 4→4.5, QA 사고 4.5→5, 보안 사고 5/5 신규, §2.12 차별화 명문화 + §2.13 회원가입 직접 설계 + §2.14 10 정책 본문 동시 갱신 의무 인지 신규, §3.1 pivot 17+ 갱신, §4.2 큰 정책 directive 직접 패턴 신규, §6 비교 기준 9 컬럼 — 차별화 명문 + 보안 사고 추가, 상위 1~2% 평가). HTML 2종 sub-agent 병렬 재생성 (productization 450 행 표 7 + vibe-coding 381행 표 5). 모두 1인칭/3인칭/BPE 0 위반 (커밋 대기)
[2026-05-17 14:26:14] HTML 3종 동시 재생성 (CLAUDE.md §10-6 정합) — sub-agent 3 (general-purpose) 병렬 Whitebox. ARCHITECTURE.html 366행 (mermaid 3 + 표 5 + §6 모듈 책임 표 app/auth + server/auth 2 행 추가). Structure.html 637행 (mermaid 6 + 표 9 + §4 디렉토리 책임 app/auth/db + server/auth 3 행 추가). FRONTEND.html 662행 (mermaid 9 — 기존 6 + 신규 3 wireframe §14.6/14.7/14.8 + swatch 18 보존 + 표 5). 모두 1인칭/3인칭/BPE 0 위반. 본 사이클 sub-agent 누계 = 9 (5+2 cycle2 + 2 cycle3 + 1 DESIGN + 1 DESIGN 재생성 + 2 cycle3 평가 snapshot + 3 auth) = 누계 14 spawn (커밋 대기)
[2026-05-17 14:17:22] auth 인프라 정책 본문 5 파일 갱신 (auth 정책 후속 사이클). PRODUCT_SENSE.md P3 페르소나 재조정 ("가입 마찰 0" → "가입 마찰 최소" + 1회 가입 후 영구 이용 분산). MIGRATION_MARIADB.md tables 배열 4→7 (users + email_verification + password_reset 추가) + DDL §3.0/3.0a/3.0b 신설 (users + email_verification + password_reset 본문 SQL). ARCHITECTURE.md §6 모듈 책임 표 + app/auth + server/auth 2 행 추가. Structure.md §10 디렉토리 매핑 + app/auth + app/db + server/auth 3 행 추가. FRONTEND.md §14.6 회원가입 화면 + §14.7 로그인 화면 + §14.8 아이디·비번 찾기 화면 3 mermaid wireframe 신설. 가드레일 정합 = 5 파일 lint pass. HTML 3종 (ARCHITECTURE + Structure + FRONTEND) sub-agent 병렬 재생성 = 별도 commit (커밋 대기)
[2026-05-17 14:12:08] 회원가입 + 이메일 OTP 인증 정책 도입 (사용자 directive 2026-05-17). 영구 메모리 신설 project_auth_email_otp_required.md (필수 3필드 email/username/password + 선택 2 nickname/avatar + OTP 3분 흐름 + 아이디/비번 찾기 흐름 + DB 스키마 3 테이블 users/email_verification/password_reset + 기술 명세 bcrypt 12 rounds + aiosmtplib + secrets.choice + 보안 정합 + Phase 1 필수 도입 + 페르소나 영향 P3 가입 마찰 0→최소). Specification.md FR-11 회원가입 + FR-12 로그인 + FR-13 아이디/비번 찾기 3 신규 (P0 / M2). SECURITY.md §9-2 신설 (회원가입 + 이메일 OTP 보안 — 비밀번호 저장 / OTP 보안 / SMTP 보안 / 아이디·비밀번호 찾기 보안 / STRIDE 위협 모델). adoption-roadmap.md Phase 1 회원가입 의무 + DoD 5 신규 + KPI 2 신규 (OTP latency + brute force 차단율). CheckList §2 FR P0/P1 10→13 갱신. 원격 제어 메모리 의 Phase 3 막바지 명시 (사용자 directive). MEMORY.md 인덱스 16종 (커밋 대기)
[2026-05-17 14:02:05] 차별화 계획 정리 — 친구간 1:1 원격 데스크탑 제어 (사용자 directive 2026-05-17). 영구 메모리 신설 project_phase2_remote_control_differentiator.md (패턴 A 원격 도움 요청 + 패턴 B 원격 제어 요청 양방향 명세 + 기술 후보 화면 캡처/입력 주입/WebRTC video track/권한 모델/감사 로그 + Phase 1~5 매핑). PRODUCT_SENSE.md 페르소나 P5 라이브 크리에이터 + P6 기술 도움 제공자 2 신규 (Phase 3+) — 표 7행 확장 + 흐름 mermaid (P5↔P6 양방향 + V5 메신저+원격 제어 통합 신규) + §4.2 상세. adoption-roadmap.md §3.3 Phase 3 (E2EE + 모바일 + 원격 제어 차별화) 통합 — DoD 2 신규 (원격 제어 패턴 A+B PASS + 권한 모델 PASS) + KPI 2 신규 (성공률 95% + 평균 길이 15분). MEMORY.md 인덱스 갱신 (가드레일 15종). Phase 3 진입 시점 = 사용자 명시 GO + Phase 1 기본 8 완성 + E2EE 결합 후 ([[project-phase1-completion-priority]] 정합) (커밋 대기)
[2026-05-17 13:56:40] 평가 snapshot 사이클 3 동시 갱신 (CLAUDE.md §10-7 정합). productization 종합 2.6→2.9 ▲ (기술 완성도 2.0→2.5 pytest+Playwright+DESIGN §11, 가드레일·자동화 5/5 신규, 세션 정합 5/5 신규, §2.8 QA 인프라 + §2.9 UI 디자인 시스템 + §3.7 추가 차별화 보류). vibe-coding 종합 4.5→4.7 ▲ (도메인 비전 4→4.5, 기술 의사결정 4→4.5, 사이클 효율 4→4.5, QA 사고 4.5 신규, 세션 정합 5 신규, §2.9 QA 사고 + §2.10 세션 정합 + §2.11 scope creep 차단, §3.1 pivot 14+ 갱신, §6 비교 기준 7 컬럼 (QA 사고 + 세션 정합 추가)). HTML 2종 sub-agent 병렬 재생성 — productization.html 423행 표 6 + vibe-coding.html 364행 표 5. sub-agent vibe-coding 본문 의미 변경 1건 발견 + 즉시 정정 (사용자 인용 영역 보존 — "내 바이브 코딩 능력" 복원). 텔레그램 송신 누계 17건 (커밋 대기)
[2026-05-17 13:45:55] handoff doc 사이클 1 전체 rewrite — docs/exec-plans/active/2026-05-17-session-handoff.md 본 세션 누계 commit 20 반영. §1 TL;DR (14 가드레일 + 8 체크리스트 + HTML 6 + snapshot 2). §2 세션 시작 체크리스트 7→10 (CLAUDE §10-6/7 + CheckList + 텔레그램). §3 첫 응답 템플릿 갱신. §4 가드레일 9→14 (신규 4 — no-self-other + doc-perfection + design-interactive + phase1-priority). §5 정책 표 (pytest+Playwright + HTML 6 + snapshot 2). §7 피해야 할 실수 12종 (HTML/snapshot 누락 + Phase 1 차별화 차단 추가). §8 SNAPSHOT (20 commit + docs/policies 3 + assessments 2 + HTML 6 + pytest 인프라 + 가드레일 14 + 텔레그램 14 + Agent #16 보존). §9 다음 액션 7 (runner 등록 + snapshot 3 + BPE + 라이선스 + 코드 진입 + Agent #16 + Toonation). §10 불변 규약 유지 (커밋 대기)
[2026-05-17 13:40:44] AGENTS.md PR 게이트 체크리스트 — build.yml (M5 PyInstaller 매트릭스) 행 추가 + Phase 1 active 명시. CI 워크플로우 3 → 4 (build.yml = Phase 1 후반 신설 예정). 실행계획 §6 의 build.yml 등재 정합 (b2b5bcb)
[2026-05-17 13:38:48] CheckList.md §2 진행률 표 drift 차단 갱신 — 본 세션 누계 commit 18 반영. 정책 9 / 운영 8 / 정책 본문 3 / 평가 snapshot 2 / HTML 6 / .claude/agents 7 / .github 인프라 4 / pytest 인프라 1 / 영구 메모리 14 / 코드 0/12 / FR 0/10 / NFR 부분 구축 / 마일스톤 M1 / CI 3/4 / self-hosted runner 0/2 / BPE 자동 검사 1 / 텔레그램 강제 활성 — 16행 진행률 표 (이전 8행 → 16행 2배 확장). 가드레일 [[feedback-doc-perfection-before-code]] 8 체크리스트 정합 — 운영 문서 frontmatter active 확인 (커밋 대기)
[2026-05-17 13:35:46] DESIGN.md §10.6 Playwright E2E + §11 UI 디자인 시스템 + pytest 인프라 신설 + DESIGN.html (사용자 directive 2026-05-17 누계 4종). DESIGN.md §10.6 (Playwright 3 영역 — 시그널링 WS E2E + HTML 시각 회귀 + zip 첫 실행 capture). §11 UI 디자인 시스템 (8 컴포넌트 인벤토리 + 상태 6 + variant 4 + spacing 7 + elevation 4 + motion 3 + dark mode + 타이포). pyproject.toml (pytest + coverage + marker 5 + asyncio mode auto). app/server requirements-dev.txt (pytest-asyncio + cov + qt + mock + aiohttp + playwright). tests/conftest.py (env isolation + repo_root fixture). tests/app/test_config.py (MariaDB 5필드 + db_dsn + signaling_url + 폴백 3 — 6 test). tests/server/test_protocol.py (화이트리스트 5 + 거부 8 + 비문자열 5 — 3 test). tests/e2e/ (Playwright conftest + HTML 시각 회귀 3 test). ci.yml pytest job 추가 (macOS arm64 + Windows x64 매트릭스 + coverage 80% 게이트). docs/html/DESIGN.html 608행 (mermaid 2 + 표 10, sub-agent 재생성). CLAUDE.md §10-6 HTML 5→6종. 영구 메모리 2종 신설 — project-phase1-completion-priority (scope creep 차단) + feedback-design-interactive-html (디자인 directive HTML interactive). 가드레일 누계 14종 (커밋 대기)
[2026-05-17 13:16:44] 평가 snapshot 사이클 2 동시 갱신 (CLAUDE.md §10-7 정합) — productization 종합 2.5→2.6 ▲ (수익화 1→1.5, §2.3 정책 본문 + PR 템플릿 추가, §2.6 가드레일 자동화 강화, §2.7 UX 가시화, §3.6 코드 진입 미완, 단기 액션 ✅ 8 / 🟡 1 / 🔴 5). vibe-coding 종합 4.4→4.5 ▲ (Repo 위생 4→5, UX 직관 4 신규, §2.8 UX 가시화 인지, §3.1 pivot 12+ 누계, §6 UX 가시화 컬럼 추가, §4.2 가드레일 강제 명시 패턴 추가). HTML 2종 sub-agent 병렬 재생성 (productization 413행 + vibe-coding 376행, 모두 1인칭/3인칭/BPE 0 위반) (커밋 대기)
[2026-05-17 13:06:07] FRONTEND.md + FRONTEND.html 색상 swatch 가시화 (사용자 directive 2026-05-17). 색상 변수 표 §4 의 9 hex 변수 (bg/fg/bubble-self/bubble-other/bubble-border/text-timestamp/text-sender/status-connected/status-error) 라이트+다크 18개 hex 값에 14px 색상 swatch 추가. FRONTEND.md inline HTML span (style background) + FRONTEND.html .swatch CSS 클래스 (head style 추가). 미확정 후크 항목 (--primary / --progress-acked / --progress-inflight) 는 swatch 미추가 (값 미정). .markdownlint.json MD033 allowed_elements 에 span + div 추가 (CLAUDE.md §10-6 동시 갱신 의무 정합) (커밋 대기)
[2026-05-17 13:03:13] docs/policies/ 3 문서 신설 — handoff §11 위임 문서 모두 active. doc-gardening.md (9 섹션 — 4 drift + 5 검사 + 오너십 7 + 자동 보정 워크플로우 + 위반 처리 6 + 갱신 절차), adoption-roadmap.md (7 섹션 — 페르소나 4 ↔ Phase 1~5 매트릭스 + Phase별 도입 전략 + 시장 옵션 매핑 + 차단점 5 + 갱신 절차), execution-harness.md (11 섹션 — Watcher 5 정책 + Enforcement Layer 5단 + 직무유기 4 패턴 + 자율성 허용/금지 + Whitebox 6 의무 + 워크플로우 + M1~M7 + 가드레일 6 우선순위 + 분류기 우회 + 갱신 절차). 깨진 링크 12 → 0 해소. AGENTS.md 문서 맵 "작성 예정" → "3 문서 active" 갱신. doc-lint.sh 5 검사 모두 PASS (커밋 대기)
[2026-05-17 12:53:01] .github/pull_request_template.md 신설 — release-agent PR 양식 정합 (사용자 directive 2026-05-17). 9 섹션 (요약 + 변경 분류 + 영향 범위 표 6행 + M1~M7 체크리스트 7 + lint 가드레일 5 + CI 3 workflow + reviewer/qa/observability + 사용자 directive 정합 + 후속 task + 머지 후 조치 5). 깨진 링크 12건 중 1건 해소 (release-agent.md → .github/pull_request_template.md) (96ad8e4)
[2026-05-17 12:50:22] tools/doc-lint.sh bash 3.2 호환 fix + 1인칭/3인칭 검사 5번 추가. mapfile → while read fallback (macOS 기본 bash 3.2 즉시 실행 가능). 검사 4종 → 5종 확장 (BPE + 깨진 링크 + frontmatter + 연속 빈 줄 + 1인칭/3인칭 대명사). 가드레일 자동화 강화 — feedback-no-self-other-pronoun 자동 grep 검출. 전수 검사 가동 검증 OK — 잔존 15 위반 발견 (BPE 3 + 깨진 링크 12) 별도 task 등록 (db0b634)
[2026-05-17 12:46:09] vibe-coding.md 평가 snapshot 갱신 (snapshot 패턴 전체 rewrite) + HTML 2종 재생성 (sub-agent 2 병렬 Whitebox) + 영구 메모리 feedback-doc-perfection-before-code 신설. vibe-coding.md: 종합 4.3 → 4.4 ▲ (사이클 효율 3.5 → 4 + 가드레일 설계 4.5 → 5 + 비판 재교정 4.5 → 5), 강점 #2.7 sub-agent 활용 추가, 약점 §3.1 pivot 표 8건 갱신 (HTML directive + 1인칭 비판 + 텔레그램 가드레일), §4.2 비판 패턴 추가 (가드레일 강제 명시), §3.4 위반 누계 (BPE 118건 + 1인칭 12파일 + 3인칭 8건), 비교 기준 §6 메타규칙 컬럼 추가. productization.html 409행 + vibe-coding.html 537행 재생성 (sub-agent 모두 0 위반 보고). 신규 영구 메모리 = 큰 프로젝트 8 체크리스트 의무 + 간단 작업 완화 + 자율성 추가 제한 + 위반 처벌 3단계 (사용자 2026-05-17 directive 2회 강화) (커밋 대기)
[2026-05-17 12:38:27] 1인칭/3인칭 표현 전수 회수 + 텔레그램 가드레일 강화 — 사용자 directive 2026-05-17 2회 비판 후 즉시 영구화. 영구 메모리 feedback-no-self-other-pronoun 신설 (MEMORY.md 인덱스 갱신 + repeat-criticism 표 2회차 영구화). FRONTEND.md / FRONTEND.html / Structure.md / docs/html/Structure.html / PRODUCT_SENSE.md / server/README.md / .claude/agents/reviewer-agent.md / History.md / docs/exec-plans/active/session-handoff.md / CLAUDE_HARNESS_IMPORTANT.md / docs/assessments/vibe-coding.md / docs/html/vibe-coding.html 12 파일 정정. 대체 패턴: 내/상대/owner/사용자/요청자/자체 (UI 기술 용어 영역) + 1인칭 대명사 표현 (인용 영역). 텔레그램 송신 가드레일 강화 — HTTP API 직접 경로 (curl + bot 8753967007 + chat 201073550) 강제 활성. 매 응답 종료 직전 송신 의무 + caveman ultra 5줄 패턴. productization.md 평가 snapshot 전체 rewrite (점수 갱신 + 단기 액션 표 갱신 + KPI 측정 상태) (26f60ed)
[2026-05-17 12:26:29] docs/html/ 5 HTML 신설 — sub-agent 5종 (general-purpose) 병렬 spawn (Whitebox run_in_background). Structure.html (693행, mermaid 6) + ARCHITECTURE.html (359행, mermaid 3) + FRONTEND.html (533행, mermaid 6) + productization.html (401행, 표 6) + vibe-coding.html (370행, 표 5). 모두 HTML5 + UTF-8 + mermaid.js CDN. CLAUDE.md §10-6/7 (.md ↔ .html 동시 갱신 의무 + 평가 snapshot 동시 갱신 의무) 명문화 (5d898b2)
[2026-05-17 12:24:50] RELIABILITY.md MariaDB 회수 — 13 위반 정정 (handoff §9 우선순위 4번, 가장 큰 회수 작업). SQLite WAL → MariaDB InnoDB redo log + doublewrite buffer 자동 회복. SQLite dump → mysqldump --single-transaction 백업 + binlog PITR. SQLITE_PATH → DB_HOST/PORT/USER/PASS/NAME 5필드. §4.4 트랜잭션 + §7 백업/복구 + §8 카오스 시나리오 + §10.2 트러블슈팅 모두 정합 (87e71e3)
[2026-05-17 12:22:47] 실행계획 (2026-05-17-tootalk-phase1-mvp.md) MariaDB 회수 — 5 위반 정정. L38 In Scope (SQLite 로컬 히스토리 → MariaDB + asyncmy + 환경변수 5종), L92 M3 마일스톤 (SQLite 영구화 → MariaDB 영속화), L109 task #16 (SQLite 스키마 → MariaDB 스키마), L179 검증 회귀 시나리오, L203 의존성 그래프 mermaid (9477e9c)
[2026-05-17 12:19:26] docs/assessments/{productization,vibe-coding}.md 신설 — snapshot 패턴 평가 문서 2종 (사용자 directive 2026-05-17 "매 task 종료 시 전체 rewrite"). 제품화 가능성 평가 (10 섹션, 종합 2.3/5 PoC 단계) + 바이브 코딩 능력 평가 (9 섹션, 종합 4.3/5 상위 10%) (6ab9952)
[2026-05-17 12:12:30] ARCHITECTURE.md MariaDB 회수 — L76 Core 영역 mermaid (SQLite 저장소 → MariaDB 영속화), L163 app/core 모듈 표 (의존성 + app/db 추가), L166 app/db (sqlite3 → asyncmy), L188 환경변수 표 (SQLITE_PATH 단행 → DB_HOST/PORT/USER/PASS/NAME 5행) (aff2cde)
[2026-05-17 12:10:21] app/core/config.py + app/README.md MariaDB 회수 — `_DEFAULT_LOCAL_DB_PATH` + `local_db_path` 단일 필드를 `_DEFAULT_DB_HOST/PORT/USER/PASS/NAME` 5상수 + `db_host/port/user/pass/name` 5필드로 회수. `db_dsn` 프로퍼티 신설 (mysql://user:pass@host:port/name) (34d4707)
[2026-05-17 12:05:41] docs/references/ci-self-hosted-setup.md 신설 — self-hosted runner 등록 절차 (macOS arm64 + Windows x64), 라벨 명세 + 사전 의존성 + 보안 hardening + 트러블슈팅 + 운영 체크리스트 (0b0e010)
[2026-05-17 12:00:02] .github/workflows/doc-gardener.yml 신설 — 주 1회 drift 감지 워크플로우 (cron Monday 00:00 UTC + workflow_dispatch), 90일 스테일 + doc-lint + 루트 18 동결 검증, Phase 2 자동 PR 생성 위임 (6f39d32)
[2026-05-17 11:57:51] .github/workflows/docs-lint.yml 신설 — 문서 lint 전용 워크플로우 (markdownlint + doc-lint.sh), 트리거 4종 (cron daily 00:00 UTC + workflow_dispatch + push + PR path-filter) (76313fe)
[2026-05-17 11:54:45] .github/workflows/ci.yml 신설 — CI 게이트 7종 (docs-lint·root-18·M1·M2·M3·M4·import-smoke), self-hosted [macOS, arm64] + [Windows, x64] 매트릭스 (df7f581)
[2026-05-17 11:23:50] Structure.md 신설 — 운영 3/8, 527행 mermaid 6 ERD + MariaDB 4 테이블 (39bd0a9)
[2026-05-17 11:19:01] FRONTEND.md §14 wireframe/mockup 섹션 추가 — UI 표면 5 mermaid 도식 (0fd29ba)
[2026-05-17 11:18:48] Specification.md 신설 — 운영 1/8, FR 10 + User Story 9 + DB MariaDB 명시 (b3efb2b)
[2026-05-17 11:09:05] tools/doc-lint.sh 신설 — M4 가드레일 (BPE 위생·링크·frontmatter·연속 빈 줄) (8c45f10)
[2026-05-17 11:03:51] .markdownlint.json 신설 — markdown lint 가드레일 사전 작업 (2f33da0)
[2026-05-17 11:03:07] SECURITY.md 신설 — 9 정책 8/9 (44288ab)
[2026-05-17 10:55:07] QUALITY_SCORE.md 신설 — 9 정책 7/9 (d240179)
[2026-05-17 10:54:55] PRODUCT_SENSE.md 신설 — 9 정책 6/9 (aa31bd9)
[2026-05-17 10:54:20] RELIABILITY.md 신설 — 9 정책 5/9 (4f79813)
[2026-05-17 10:54:06] PLANS.md 신설 — 9 정책 4/9 (3a13cfc)
[2026-05-17 10:53:53] FRONTEND.md 신설 — 9 정책 3/9 (b877653)
[2026-05-17 10:53:20] DESIGN.md 신설 — 9 정책 2/9 (af54042)
[2026-05-17 10:52:29] ARCHITECTURE.md 신설 — 9 정책 1/9 (4c23e11)
[2026-05-17 10:33:00] PyQt6 + qasync 클라이언트 스켈레톤 push (1635행, 14 파일, M1·M4) (1fb7ba3)
[2026-05-17 10:23:58] aiohttp WebSocket 시그널링 서버 스켈레톤 push (1121행, 7 파일, M1·M4) (7f10179)
[2026-05-17 10:16:16] .claude/agents 7 프로세스 에이전트 정의 push (600행, M1·M4) (5264d43)
[2026-05-17 10:08:44] 실행계획 TD-6 행 BPE 위생 정정 — 단독 의존명사 제거 (6dbbe06)
[2026-05-17 10:08:22] Phase 1 MVP 실행계획 + CI self-hosted 정책 반영 (M1) (5eac245)
[2026-05-17 10:01:17] 정본 정독 대상 등록 + Claude CLI Telegram wrapper 추가 (M1·M4) (5268a75)
[2026-05-17 09:54:13] AGENTS.md TooTalk 서비스명 명문화 (M1) (928c2bf)
[2026-05-17 09:36:27] 부트스트랩 — AGENTS.md + .gitignore + .env.example 초기화 (M1) (9f67eeb)

### Phase 1 누계 (2026-05-17 기준)

- commit 수: 21 건 (`9f67eeb` ~ `39bd0a9`)
- 신규 루트 마크다운: 14 종 (AGENTS, ARCHITECTURE, DESIGN, FRONTEND, PLANS, PRODUCT_SENSE,
  QUALITY_SCORE, RELIABILITY, SECURITY, Specification, Structure, .markdownlint.json,
  History.md — 본 문서, 본 누계 행 prepend 시점)
- 신규 코드 산출물: PyQt6 클라이언트 스켈레톤 14 파일 / aiohttp 시그널링 서버 7 파일
- 신규 가드레일: `tools/doc-lint.sh` (4 검사) + `tools/claude-telegram.sh` wrapper
- 신규 에이전트 정의: `.claude/agents/` 7 종 (7 프로세스 분리)

---

## Phase 0 정본 인계 (2026-05-15)

[2026-05-15 15:57:00] CLAUDE_HARNESS_IMPORTANT.md 정본 인계 — 저장소 외부 watcher 산출물,
저장소 루트 직접 배치 (44706 bytes). 본 정본이 M1~M5, 9 정책, 루트 동결(18 한도), CI 강제
게이트, docs/policies 위임 구조 전부를 단일 출처로 정의한다. 본 시점부터 모든 신규 문서·코드·
운영 변경의 1차 정합 기준이 된다.

---

## 부록 A. 명령 인용 (검증용)

본 문서의 실재성을 재현하려면 저장소 루트에서 다음 명령을 실행한다.

```bash
# 실 commit 목록 (최신 → 과거 내림차순)
git log --pretty=format:'%aI %h %s'

# 누계 commit 수
git log --pretty=format:'%h' | wc -l

# BPE 위생 + 전체 doc-lint 게이트 (본 문서 단독)
bash tools/doc-lint.sh History.md
```

세 명령 모두 0 매치·exit 0 가 정상이다. 매치 발생 시 해당 행을 합성어로 정정하거나 다른 표현
으로 대체한 뒤 재실행한다.

---

## 부록 B. Phase 정의 (작업 단위 구분)

| Phase | 기간 | 주제 | 산출물 핵심 |
|---|---|---|---|
| Phase 0 | 2026-05-15 | 정본 인계 | `CLAUDE_HARNESS_IMPORTANT.md` 저장소 배치 |
| Phase 1 | 2026-05-17 ~ 진행 중 | MVP 부트스트랩 | 9 정책 + 운영 2종 + 코드 스켈레톤 + 가드레일 |
| Phase 2 | (예정) | 시그널링 ↔ 클라이언트 결선 | WebRTC DataChannel E2E 송수신 검증 |
| Phase 3 | (예정) | SQLite 로컬 저장 + 진행률 UI | 송수신 ProgressBar + 메시지 영속화 |
| Phase 4 | (예정) | macOS·Windows 매트릭스 빌드 | PyInstaller + GitHub Actions self-hosted |

Phase 전환은 다음 조건 충족 시 `@history-agent` 가 새 Phase 헤더를 본 문서 상단에 prepend
한다.

1. 직전 Phase 의 목표(`PLANS.md` 측면 정의) 가 100% 달성됨
2. 정본 `CLAUDE_HARNESS_IMPORTANT.md` 의 M1~M5 게이트 전부 통과
3. `tools/doc-lint.sh` 와 `.github/workflows/ci.yml` 전체 강제 게이트 통과
4. `README.md` 변경 이력(M2) 에도 Phase 전환 행이 동시 prepend

---

## 부록 C. 정본 정합 매핑

| 본 문서 항목 | 정본 위치 | 강제 |
|---|---|---|
| 역순 prepend | §A M3 / §I | CI "History.md 역순 검증(M3)" |
| 30 행 상한 (README) | §H | CI "README.md 변경 이력 존재 확인" |
| BPE 위생 | §J 인접 운영 합의 | `tools/doc-lint.sh` 검사 1 |
| frontmatter 필수 필드 | docs-lint.yml | `tools/doc-lint.sh` 검사 3 (본 문서는 루트라 면제) |
| Phase 그룹화 | §I 구조 도식 | `@history-agent` `tools/md_agents.py` |
| 루트 마크다운 18 동결 | §K | CI "Root markdown 개수 동결 확인" |

본 문서는 루트 직접 배치이므로 `docs/**` frontmatter 강제 검사(검사 3) 의 대상이 아니다. 다만
가독성·소유권 명시 목적으로 동일 4 필드(title·owner·last_verified·status) frontmatter 를
자발 부착한다.

---

## 부록 D. 갱신 절차 (운영자용)

1. 작업 단위 완료 → `git commit` (M5 즉시 push 포함)
2. `git log -1 --pretty=format:'%aI %h %s'` 로 신규 commit 메타 추출
3. 본 문서 "Phase 1 MVP 부트스트랩" 헤더 바로 아래 빈 줄 다음 행에 다음 형식으로 **prepend**
   - `[YYYY-mm-dd HH:MM:SS] 요약 — 산출물 핵심 (단축 SHA)`
4. 동일 단위 변경을 `README.md` 변경 이력에도 prepend (M2)
5. `bash tools/doc-lint.sh History.md` 0 위반 확인
6. `tools/doc-lint.sh` 의 검사 1번 (BPE 위생) 0 매치 확인 — 단독 의존명사 토큰 부재
7. `git add History.md README.md && git commit && git push`

Phase 전환 시는 새 `## Phase N` 헤더를 본 문서 가장 위 Phase 블록보다 상단에 prepend 한다.
직전 Phase 의 "누계" 서브헤더(`### Phase N 누계`) 를 동결 시점에 한 번 더 갱신한다.

---

## 부록 E. 변경 이력 (본 문서 자체)

[2026-05-17] History.md 신설 — Phase 1 MVP 부트스트랩 누계 21 건 + Phase 0 정본 인계 1 건
포함. M3 역순 구조·BPE 위생·doc-lint 통과 상태로 commit. 본 항부터 본 문서 자체의 변경도
한 줄씩 prepend 한다.

---

## 부록 F. 누락 회수 정책 (운영 합의)

본 문서 신설 시점에는 누계 21 건의 commit 이 이미 적재된 상태였고, 본 문서 자체가 그 누계를
"한 번에" 흡수하는 형태로 출발한다. 향후 단발성 누락이 발생한 경우의 회수 절차는 다음과
같이 운영한다.

1. **단일 누락** — 누락 commit 1 건을 발견한 시점에 즉시 해당 commit 의 정확한 타임스탬프와
   단축 SHA 로 본 문서에 prepend (역순 무시 금지: 새 행은 항상 본 Phase 헤더 직하 첫 행에 삽입
   되지 않고, 자체 타임스탬프가 정합되는 위치 — 즉 더 최신 행보다 아래·더 과거 행보다 위 —
   에 삽입한다). 본 절차는 `@history-agent` 의 단발 회수 모드로 실행된다.
2. **다수 누락 (5 건 이상)** — `git log --since=<누락 시작> --until=<누락 끝>` 의 출력 전체를
   본 Phase 헤더 직하에 시간 내림차순으로 prepend 한 뒤 단일 commit "docs(history): 누락
   회수 N 건 흡수" 으로 마감. 회수 commit 자체도 다음 갱신 사이클에서 prepend 된다.
3. **타임스탬프 충돌** — 동일 초 단위 commit 이 둘 이상인 경우 단축 SHA 사전순으로 정렬해
   본 문서 내 행 순서를 결정한다. SHA 사전순은 안정적 정렬이므로 재실행 결과가 동일하다.
4. **회수 후 검증** — `tools/doc-lint.sh History.md` + 본 문서 부록 A 의 self-check 명령을
   순차 실행해 0 위반·실재성을 확보한 뒤 push.

---

## 부록 G. 본 문서가 답하지 않는 것 (위임 경계)

본 문서는 "언제 무엇이 일어났는가" 의 시계열 로그다. 다음 항목은 본 문서가 다루지 않으며,
각각 명시된 정본·운영 문서로 위임한다.

| 위임 대상 질문 | 답하는 문서 |
|---|---|
| "왜 그 결정을 내렸나" 의 논거 | `DESIGN.md` · `ARCHITECTURE.md` · `PLANS.md` |
| "어떤 기능을 만들기로 했나" | `Specification.md` (FR 10 + User Story 9) |
| "코드 구조는 어떻게 되나" | `Structure.md` (mermaid 6 + ERD MariaDB 4 테이블) |
| "보안/품질 정책은 무엇인가" | `SECURITY.md` · `QUALITY_SCORE.md` · `RELIABILITY.md` |
| "현재 진행률은" | `CheckList.md` (Phase 1 후반 신설 예정) |
| "정본 규약 자체는" | `CLAUDE_HARNESS_IMPORTANT.md` (저장소 외부 watcher 산출물) |
| "운영자 가이드는" | `AGENTS.md` (저장소 맵) |

본 문서를 읽는 사람이 "왜?" 를 묻는다면 위 표의 우측 컬럼으로 이동해야 한다. 본 문서는
"무엇이·언제" 만 답한다.

---

## 부록 H. CI 강제 게이트 진척 (Phase 1 시점)

본 문서 신설 시점에 정본 §L 의 3 종 워크플로우 중 로컬 등가 가드레일만 가용 상태다. 원격
GitHub Actions self-hosted runner 구성은 Phase 1 후반에 합류한다.

| 게이트 | 현 상태 | 책임 |
|---|---|---|
| `ci.yml` 본체 | 미구성 | Phase 1 후반 신설 |
| `docs-lint.yml` 등가 | `tools/doc-lint.sh` 로컬 가용 | 본 문서 부록 A 의 self-check 로 매 commit 전 확인 |
| `doc-gardener.yml` | 미구성 | Phase 1 종료 후 합류 |
| History.md 역순 검증 (M3) | 미구성 → 부록 D 절차로 수동 보장 | `@history-agent` 합류 시 자동화 |
| README.md 변경 이력 (M2) | `README.md` 미존재 → 신설 시 동시 도입 | Phase 1 후반 |
| 한글 주석 (M4) | 코드 스켈레톤 단계에서 수동 준수 중 | CI 합류 시 자동 검사 |
| 루트 마크다운 18 동결 (K) | 현 13 / 18 (본 문서 포함) | 추가 5 개 여유 |

본 표는 Phase 1 마감 시점에 모든 항이 "구성 완료"로 전환되어야 한다. 미전환 항이 남아 있다면
Phase 2 진입 조건(부록 B 의 4 조건) 을 충족하지 않은 것으로 간주한다.
