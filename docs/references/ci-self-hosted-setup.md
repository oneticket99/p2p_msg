---
title: "CI self-hosted runner 등록 절차"
owner: oneticket99
last_verified: 2026-05-17
status: active
---

# CI self-hosted runner 등록 절차

> 본 문서는 사용자 directive 2026-05-17 ("CI 는 self-hosted 환경으로 구축해") 에 따라
> TooTalk(p2p_msg) 의 self-hosted runner 등록 단계별 안내를 제공한다. GitHub-hosted
> runner 는 미사용 (비용 0 · 보안 통제 우위 정합).
>
> 관련 워크플로우:
> [.github/workflows/ci.yml](../../.github/workflows/ci.yml) ·
> [.github/workflows/docs-lint.yml](../../.github/workflows/docs-lint.yml) ·
> [.github/workflows/doc-gardener.yml](../../.github/workflows/doc-gardener.yml)

---

## 1. 매트릭스 + 라벨 명세

| Runner | 라벨 (정확히 일치) | 빌드 산출물 | 호스트 |
|---|---|---|---|
| **macOS arm64 self-hosted** | `[self-hosted, macOS, arm64]` | TooTalk.app + macOS zip + ci/docs-lint/doc-gardener 게이트 | 사용자 본 Mac (id=2, launchd PID 62533, online) |
| **GitHub-hosted Ubuntu** | `ubuntu-latest` | TooTalk Windows zip (wine cross-compile, Phase 1 후반 build.yml) | GitHub 무료 (public repo) |

> **Windows self-hosted runner 의 의무 = 영구 회수** (사용자 directive 2026-05-17
> "윈도우 빌드는 wine을 이용해서 할꺼야"). Windows 빌드 = GitHub-hosted Ubuntu 의
> wine cross-compile (docker `cdrx/pyinstaller-windows`) — 영구 메모리
> [[project-windows-build-via-wine]] 정합.
>
> Linux self-hosted runner 후보 (`114.207.112.73` Ubuntu) 는 Phase 2+ 검토 —
> 사용자 directive 2026-05-17 macOS arm64 단독 + GitHub-hosted Ubuntu 듀얼.

라벨 배열 매칭 = AND. GitHub Actions 매트릭스 job 은 모든 라벨 충족 runner 를 선택. 라벨 1개라도
어긋나면 workflow 는 `queued` 상태로 무한 대기한다.

---

## 2. 사전 의존성 (runner OS 별)

### 2.1 macOS arm64 (필수)

- **Python 3.13** (`brew install python@3.13` 또는 [python.org](https://www.python.org) 공식 인스톨러)
- **bash 4 이상** (`brew install bash`) — `tools/doc-lint.sh` 의 `mapfile` builtin 의존.
  macOS 기본 bash 3.2 는 `mapfile` 미지원. Homebrew GNU bash 5.x 권장.
- **node + npx** (`brew install node`) — `markdownlint-cli2` 의 `npx --yes` 실행 의존
- **git 2.30 이상** (Xcode CLT 동봉본 또는 `brew install git`)

### 2.2 ~~Windows x64 self-hosted runner~~ (영구 회수)

본 영역 의 의무 = 2026-05-17 사용자 directive 정합 영구 회수. Windows 빌드 의
host = GitHub-hosted Ubuntu (`ubuntu-latest`) + docker `cdrx/pyinstaller-windows`
의 wine cross-compile. 사용자 Windows 머신 + VM + dependency 설치 의무 = 모두 회피.

자세한 정합 정책 = 영구 메모리 [[project-windows-build-via-wine]] + 본 문서 §11
(신규 wine cross-compile 영역).

### 2.3 공통 권장

- self-hosted runner 용 dedicated 사용자 계정 (시스템 권한 분리)
- runner work 디렉토리 = SSD (PyInstaller 빌드 IO 큼)
- 디스크 여유 ≥ 20GB (Python venv + node_modules + PyInstaller dist)

---

## 3. runner 등록 절차

### 3.1 GitHub 토큰 발급

1. <https://github.com/oneticket99/p2p_msg/settings/actions/runners> 로 이동
2. **New self-hosted runner** 버튼 클릭
3. OS 선택 (macOS / Windows) → 등록 토큰 (`A` 로 시작하는 토큰) 표시
4. 토큰은 1시간 한도 — 즉시 사용

### 3.2 macOS arm64 등록 단계

```bash
# 사용자 Mac 의 dedicated 디렉토리
mkdir -p ~/actions-runner-tootalk && cd ~/actions-runner-tootalk

# 최신 runner 다운로드 (버전은 GitHub 안내 사용)
curl -o actions-runner.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.319.1/actions-runner-osx-arm64-2.319.1.tar.gz
tar xzf ./actions-runner.tar.gz

# 라벨 정확히 일치 — macOS, arm64 (대소문자 보존)
./config.sh \
  --url https://github.com/oneticket99/p2p_msg \
  --token <발급_토큰> \
  --name tootalk-macos-arm64 \
  --labels macOS,arm64 \
  --work _work

# 데몬 등록 (재부팅 시 자동 시작)
./svc.sh install
./svc.sh start
```

> `self-hosted` 라벨은 GitHub 가 자동 부여. 사용자 라벨 = `macOS,arm64` 만 지정.
> 매트릭스 `[self-hosted, macOS, arm64]` 3개 라벨 AND 매칭.

### 3.3 ~~Windows x64 등록 단계~~ (영구 회수 — §11 wine cross-compile 정합)

본 영역 의 의무 = 영구 회수. Windows 빌드 = §11 의 wine cross-compile 패턴 정합.

---

## 4. 등록 검증

### 4.1 GitHub runner 상태 확인

<https://github.com/oneticket99/p2p_msg/settings/actions/runners> 에 macOS arm64
runner 단독 `Idle` 또는 `Active` 상태 = 정상. Windows runner 없음 = 정합.

```bash
# gh CLI 검증 명령
gh api repos/oneticket99/p2p_msg/actions/runners | \
  python3 -c "import sys,json;d=json.load(sys.stdin);[print(r['name'],r['status'],r['labels']) for r in d['runners']]"
```

### 4.2 워크플로우 수동 실행

```bash
# docs-lint 수동 trigger
gh workflow run docs-lint.yml

# doc-gardener 수동 trigger
gh workflow run doc-gardener.yml

# ci.yml 은 push/PR trigger — 더미 commit 으로 검증
```

실행 결과 = `gh run list` + `gh run watch <run-id>` 으로 추적.

---

## 5. public repo + self-hosted runner 보안 hardening

GitHub 공식 가이드 [GitHub Actions Security
hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
정합. public repo 에서 self-hosted runner 사용 시 외부 contributor fork PR 의 악성 코드
실행 위험 존재.

### 5.1 fork PR workflow 승인 설정 (✅ 2026-05-17 적용 완료)

#### 5.1.1 자동 적용 (gh API)

```bash
# 현재 정책 조회
gh api repos/oneticket99/p2p_msg/actions/permissions/fork-pr-contributor-approval

# Phase 1 strict 적용 (모든 외부 contributor 의 approval 의무)
gh api -X PUT repos/oneticket99/p2p_msg/actions/permissions/fork-pr-contributor-approval \
  -f approval_policy=all_external_contributors
```

본 패턴 = 2026-05-17 cycle 적용 완료. 현재 정책 = `all_external_contributors`.

#### 5.1.2 정책 옵션

| `approval_policy` 값 | 의미 | Phase 정합 |
|---|---|---|
| `first_time_contributors_new_to_github` | GitHub 신규 + 첫 contribution 만 | Phase 3+ |
| `first_time_contributors` | 본 repo 첫 contribution 만 (GitHub default) | Phase 2 |
| `all_external_contributors` | 모든 outside collaborator (maintainer 외) | **Phase 1 권장 (적용 완료)** |

#### 5.1.3 manual UI 설정 (대안)

1. <https://github.com/oneticket99/p2p_msg/settings/actions> 이동
2. **Fork pull request workflows from outside collaborators** 섹션
3. `Require approval for all outside collaborators` 선택 + **Save**

### 5.2 secrets 노출 차단

- runner 환경변수에 비밀 (DB credentials, telegram bot token) **저장 금지**
- GitHub Actions secrets 는 fork PR 에 자동 노출 차단 됨 (GitHub 기본)
- self-hosted runner 의 별도 secret store (예: macOS Keychain, Windows DPAPI) 별도 검토

### 5.3 runner 환경 격리

- dedicated 사용자 계정으로 runner 실행 (root/admin 권한 금지)
- 작업 디렉토리 (`_work/`) 권한 700 (해당 사용자만)
- 빌드 산출물 외 영역 (사용자 home, 시스템 디렉토리) 에 접근 차단

### 5.4 한계 (Phase 1 deprioritized)

사용자 directive 2026-05-17 — "데모 단계 보안 deprioritized". 본 §5 의 hardening 은 Phase 2
정식 단계 진입 직전 강제. 외부 contributor 0 상태 = 즉각 위험 낮음.

---

## 6. 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| Workflow 가 `queued` 로 무한 대기 | 라벨 미일치 또는 runner offline | `gh run view <run-id>` + GitHub runner page 확인. 라벨 정확히 일치 검증. |
| `mapfile: command not found` (macOS) | bash 3.2 기본 사용 | `brew install bash` + runner PATH 의 `/opt/homebrew/bin` 우선 |
| `npx: command not found` | node 미설치 | `brew install node` (macOS) / nodejs.org 인스톨러 (Windows) |
| `python: command not found` (Windows) | PATH 미등록 | Python 인스톨러 "Add to PATH" 재실행 또는 `setx PATH` 수동 추가 |
| import-smoke 의 PyQt6 빌드 실패 | Xcode CLT 또는 VC++ Build Tools 미설치 | macOS = `xcode-select --install` / Windows = Visual Studio Build Tools 의 C++ 워크로드 |
| import-smoke 의 aiortc 빌드 실패 | system libsrtp/libopus 미설치 | macOS = `brew install srtp opus` / Windows = 사전 빌드 wheel (pip --only-binary=:all:) |
| runner disk full | _work/ 누계 산출물 잔존 | `./run.sh --once` 종료 후 `_work/` 수동 정리 |

---

## 7. runner 제거 절차

```bash
# 1. GitHub 에서 토큰 발급 (제거용)
#    Settings → Actions → Runners → 대상 runner → Remove
#    "Remove runner" 의 발급 토큰 복사

# 2. macOS / Windows runner 데몬 정지 + config 제거
cd ~/actions-runner-tootalk           # 또는 C:\actions-runner-tootalk
./svc.sh stop && ./svc.sh uninstall   # macOS
# .\svc.cmd stop; .\svc.cmd uninstall # Windows

./config.sh remove --token <제거_토큰>  # macOS
# .\config.cmd remove --token <제거_토큰> # Windows

# 3. 디렉토리 삭제
cd .. && rm -rf actions-runner-tootalk
```

---

## 8. 비용·운영 함의

| 항목 | self-hosted | GitHub-hosted (참고) |
|---|---|---|
| 비용 | 사용자 머신 전력/시간 (변동) | macOS public repo 무료 (10x 멀티플라이어) |
| 실행 환경 | 사용자 직접 통제 (Python 3.13, brew, etc.) | GitHub 표준 image (변경 빈도 큼) |
| 캐시 | 사용자 디스크 (영구) | actions/cache (10GB 한도, repo 단위) |
| 보안 | 사용자 책임 (fork PR hardening 필수) | GitHub 격리 (ephemeral VM) |
| 가용성 | 사용자 머신 온/오프 의존 | 99.9% SLA |
| 빌드 속도 | 캐시 누계 활용 + 사용자 HW 의존 | 표준 (4-core) |

---

## 9. 운영 체크리스트

- [x] macOS runner 등록 + `online` 상태 확인 (2026-05-17 id=2 launchd PID 62533)
- [x] `brew install bash node python@3.13` (macOS) 완료
- [x] Python 3.13 PATH 등록 (`/opt/homebrew/opt/python@3.13/libexec/bin`)
- [ ] fork PR workflow 승인 설정 적용 (Settings UI — Task #4)
- [x] `gh workflow run docs-lint.yml` 수동 trigger 의 GREEN 확인
- [x] `gh workflow run doc-gardener.yml` 수동 trigger 의 GREEN 확인
- [x] push trigger 의 `ci.yml` 8 job GREEN 확인 (2026-05-17 commit e68f818)
- [ ] Phase 1 후반 `build.yml` 신설 + Windows wine cross-compile job 동작 검증 (§11)

---

## 10. 참조

- [정본 §L](../../CLAUDE_HARNESS_IMPORTANT.md) — CI 강제 게이트
- `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_ci_self_hosted.md` — 사용자 directive 본문
- `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_windows_build_via_wine.md` — Windows 빌드 wine 정책
- [GitHub Docs — Adding self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners)
- [GitHub Docs — Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [cdrx/pyinstaller-windows](https://github.com/cdrx/docker-pyinstaller) — docker image (wine + Python + PyInstaller)
- 본 문서 owner: oneticket99 · last_verified: 2026-05-17 · status: active

---

## 11. Windows 빌드 — wine cross-compile (사용자 directive 2026-05-17)

### 11.1 정책 확정

- Windows self-hosted runner 의 의무 = **영구 회수**
- Windows 빌드 host = **GitHub-hosted Ubuntu** (`ubuntu-latest`) + docker `cdrx/pyinstaller-windows` 의 wine 실행
- 사유: 사용자 Windows 머신 + VM + dependency 설치 의무 회피 + GitHub-hosted Ubuntu 의 무료 + ephemeral 격리 + matrix scale

### 11.2 패턴

```yaml
build-windows:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: PyInstaller wine cross-compile
      uses: cdrx/pyinstaller-windows@master
      with:
        spec: tools/build.spec
        requirements: app/requirements.txt
    - name: zip 패키징
      run: |
        cd dist/windows
        zip -r ../TooTalk-${{ github.ref_name }}-windows-x64.zip .
    - uses: actions/upload-artifact@v4
      with:
        name: TooTalk-windows-x64
        path: dist/*.zip
```

### 11.3 검증 의무 (Phase 1 후반)

- hello-world PyQt6 빌드 의 wine 안 수행 + Windows native 머신 실행 검증 (사용자 직접)
- aiortc 의 native 모듈 (`av` + `cffi`) 의 Windows wheel `pip --only-binary=:all:` 자동 fetch 검증
- PyQt6 Qt6 dlls 의 wine 안 PyInstaller 자동 수집 검증

### 11.4 대안 (cdrx 의 한계 시)

- alternative A: ubuntu-latest 직접 setup — `apt install wine winetricks` + native PyInstaller
- alternative B: 자체 docker image (Python 3.13 의무 시)
- alternative C: macOS runner 안 wine-stable (apple silicon native 9.x) — fallback

- [정본 §L](../../CLAUDE_HARNESS_IMPORTANT.md) — CI 강제 게이트
- `~/.claude/projects/-Users-oneticket-toonation-Documents-vscode-work-p2p-msg/memory/project_ci_self_hosted.md` — 사용자 directive 본문 (저장소 외부 영구 메모리)
- [GitHub Docs — Adding self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners)
- [GitHub Docs — Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- 본 문서 owner: oneticket99 · last_verified: 2026-05-17 · status: active
