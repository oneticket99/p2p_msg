---
title: Windows wine cross-compile smoke (cycle 132 → 141)
owner: oneticket99
last_verified: 2026-05-19T15:55:00+09:00
status: active
phase: Phase 1 — 빌드 인프라
cycle: 141
date: 2026-05-19
artifact_target: dist-windows/TooTalk-windows-x64.zip
related:
  - .github/workflows/build.yml
  - build/tootalk.spec
  - app/requirements.txt
---

# Windows wine cross-compile smoke 회수 보고서

## 1. 개요

cycle 132 directive 가 지정한 `.github/workflows/build.yml` 안 `build-windows-wine` job (ubuntu-latest GitHub-hosted runner + `cdrx/pyinstaller-windows:python3` docker image) 에 대한 actual `workflow_dispatch` 실행 smoke 검증.

본 cycle 이전 까지 build workflow 는 **tag push (`v*`) trigger 만 활성** 상태로 3 회 실패 누적 (run id 26041524530 · 26036513764 · 26017115282). 본 cycle 에서 workflow_dispatch trigger 명령 + run id capture + 실패 원인 정밀 분석 + build.yml 회수 patch 적용 까지 수행한다.

- runner: `ubuntu-24.04` GitHub-hosted (quota 회피 정합, 사용자 visibility public directive)
- image: `cdrx/pyinstaller-windows:python3` (digest `sha256:7d7bcb510a2e785f4936a2a61989fa93ff1eeba3b80571fbba919c23e52a0a63`)
- 빌드 entry: `app/main.py` → `build/tootalk.spec` → `dist-windows/TooTalk/` 산출 목표

## 2. workflow_dispatch trigger 명령

`workflow_dispatch` 의 의 `on:` block 의 이미 정의되어 있어 build.yml 추가 변경 불요.

```bash
# main 브랜치 기준 manual trigger
gh workflow run build.yml --ref main -f tag=cycle132-smoke

# trigger 결과 capture
gh run list --workflow build.yml --limit 3

# 실시간 watch
gh run watch <run-id> --exit-status

# 실패 log capture
gh run view <run-id> --log-failed
```

본 cycle 의 trigger 결과 run id = **26077734815** (URL https://github.com/oneticket99/p2p_msg/actions/runs/26077734815).

## 3. 결과 capture

### 3-0. cycle 별 누계 (최신 상단)

| cycle | run id | 시작 (KST) | macOS | Windows wine | 실패 단계 | 실패 root cause |
| :---: | --- | --- | :---: | :---: | --- | --- |
| 141 | 26081251136 | 2026-05-19 15:50:52 | PASS (1m15s) | **FAIL** (29s) | PyInstaller wine cross-compile | cycle 140 동일 — `UnicodeDecodeError 'charmap' byte 0x90 @ pos 123` 재현. **트리거 시점 origin/main = 회수 patch 부재** (사용자 manual commit/push ack 대기 의무). 로컬 stage = `app/requirements.txt` ASCII 변환 + `build.yml` `PYTHONIOENCODING=utf-8 + PYTHONUTF8=1 + LANG=C.UTF-8 + LC_ALL=C.UTF-8` env 4종 정합. push 후 cycle 142 재 trigger 의무 |
| 140 | 26081012261 | 2026-05-19 15:44:57 | PASS (1m29s) | **FAIL** (37s) | PyInstaller wine cross-compile | wine image Python 3.7 + pip 19.3.1 → `requirements.txt` UTF-8 한글 주석 `cp1252` codec decode 실패 (byte 0x90 @ pos 123) |
| 132 | 26077734815 | 2026-05-19 14:15:12 | PASS (1m27s) | FAIL (27s) | Zip artifact step (silent PyInstaller skip) | docker `cdrx/pyinstaller-windows:python3` default entrypoint `/entrypoint.sh` → CMD arg 무시 → `dist-windows/` 디렉토리 생성 부재 |

### 3-1a. cycle 141 — ASCII 변환 + UTF-8 env 회수 patch 적용 (push 대기 상태 trigger FAIL)

cycle 140 root cause 회수 chain 의 1차 적용. 본 cycle 변경:

1. `app/requirements.txt` 의 한글 주석 2종 → ASCII 영문 paraphrase 변환:
   - `# MariaDB driver (사용자 directive 2026-05-17 — 영속화 DB)` → `# MariaDB driver (user directive 2026-05-17 - persistence DB)`
   - `# Phase 2 E2EE — AES-256-GCM + X25519 ECDH + HKDF (PyCA cryptography)` → `# Phase 2 E2EE - AES-256-GCM + X25519 ECDH + HKDF (PyCA cryptography)`
   - 한글 + em-dash (U+2014) 24 byte 전량 제거 → wine cp1252 decode 실패 직접 회수.
2. `.github/workflows/build.yml` `docker run` env 4종 추가 (defensive in-depth):
   - `-e PYTHONIOENCODING=utf-8`
   - `-e PYTHONUTF8=1`
   - `-e LANG=C.UTF-8`
   - `-e LC_ALL=C.UTF-8`

| 항목 | 값 |
| --- | --- |
| run id | 26081251136 |
| trigger event | `workflow_dispatch` (input `tag=cycle141-wine-recovery2`) |
| ref | main (origin 회수 patch 부재 상태) |
| 시작 | 2026-05-19T06:50:52Z (KST 15:50:52) |
| 종료 | 2026-05-19T06:52:12Z |
| `build-macos` | PASS — 1m15s |
| `build-windows-wine` | **FAIL — 29s, exit 2** (cycle 140 의 와 동일 root cause 재현) |

**FAIL 원인 분석**: 본 cycle directive `절대 금지` 의 "git commit/push 차단" 정합 → 로컬 stage 의 회수 patch (requirements.txt ASCII + build.yml UTF-8 env) 가 origin/main 에 반영되지 않은 상태 의 trigger. `gh workflow run --ref main` 은 origin/main HEAD checkout 의무 → 기존 broken `requirements.txt` (한글 주석 24 byte) 재 사용 → `UnicodeDecodeError 'charmap' codec byte 0x90 @ pos 123` 동일 실패 재현.

**log 증거** (run 26081251136):

```
2026-05-19T06:51:23.5583154Z ERROR: Exception:
2026-05-19T06:51:23.5598622Z   File "c:\Python37\lib\encodings\cp1252.py", line 15, in decode
2026-05-19T06:51:23.5600346Z UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position 123
2026-05-19T06:51:23.7464572Z WARNING: You are using pip version 19.3.1; however, version 24.0 is available.
2026-05-19T06:51:23.8507907Z ##[error]Process completed with exit code 2.
```

**다음 cycle (142) 후속 의무**:

1. 사용자 manual ack 의 `SKIP_PREPUSH=1 git push origin main` (현 branch `main` 이 origin 보다 2 commit ahead + 본 cycle stage 7 file 추가 → 본 cycle ack 대기).
2. push 완료 직후 `gh workflow run build.yml --ref main -f tag=cycle142-wine-recovery3` 재 trigger.
3. PASS 시 → §3-0 cycle 142 row prepend + 산출 artifact `tootalk-windows-x64.zip` SHA-256 + size capture.
4. FAIL 지속 시 → cycle 140 §4-0 결론 (cdrx wine image 영구 폐기 + `windows-latest` 마이그레이션) 즉시 진입 의무.

### 3-1. cycle 140 — entrypoint patch 정합 PASS + 새 layer FAIL

cycle 132 의 `--entrypoint /bin/sh` override patch **정합 확인**. docker `pip install -r app/requirements.txt` 명령이 실제 실행됨 (cycle 132 silent skip 회수 성공). 단, 새 실패 layer 발견.

| 항목 | 값 |
| --- | --- |
| run id | 26081012261 |
| trigger event | `workflow_dispatch` (input `tag=cycle140-wine-recovery`) |
| ref | main |
| 시작 | 2026-05-19T06:44:57Z (KST 15:44:57) |
| 종료 | 2026-05-19T06:46:31Z |
| `build-macos` | PASS — 1m29s, artifact `tootalk-macos-arm64` 30일 retention |
| `build-windows-wine` | FAIL — 37s, exit 2 (PyInstaller wine cross-compile step) |

**증상**: docker run + cdrx image pull (29초) PASS → wine 안 `pip install -r app/requirements.txt` 실행 → `UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position 123: character maps to <undefined>` → exit 2.

**root cause 정밀 분석** (3 layer):

1. **wine image Python 버전 = 3.7** — cdrx/pyinstaller-windows:python3 의 wine prefix 안 `c:\Python37\` (log line `File "c:\Python37\lib\site-packages\pip\_internal\cli\base_command.py"`). pip 19.3.1 (2019년 릴리즈 — 7년 stale).
2. **requirements.txt UTF-8 한글 주석 24바이트** — `app/requirements.txt` 안 `# MariaDB driver (사용자 directive 2026-05-17 — 영속화 DB)` + `# Phase 2 E2EE — AES-256-GCM + X25519 ECDH + HKDF (PyCA cryptography)` 한글/em-dash 24 byte 가 non-ASCII. wine 안 default locale `cp1252` 코덱이 byte `0x90` (한글 EUC 영역) decode 불가.
3. **PyQt6 wine 호환 부재 (잠재)** — 본 cycle 안 UnicodeDecodeError 가 먼저 발생하여 PyQt6 install 단계까지 도달하지 못함. 단, PyQt6 6.7+ 요구 Python ≥ 3.9 + Windows native Qt6 DLL → wine 안 호환 검증 부재 → cycle 132 doc §4-2.3 의 잠재 risk 유효.

**log 증거** (run 26081012261, Windows job):

```
2026-05-19T06:45:37.7090354Z ERROR: Exception:
2026-05-19T06:45:37.7104085Z   File "c:\Python37\lib\encodings\cp1252.py", line 15, in decode
2026-05-19T06:45:37.7105112Z UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position 123: character maps to <undefined>
2026-05-19T06:45:37.8994229Z WARNING: You are using pip version 19.3.1; however, version 24.0 is available.
2026-05-19T06:45:38.0058383Z ##[error]Process completed with exit code 2.
```

### 3-2. cycle 132 — entrypoint silent skip FAIL (기존 row 보존)

| 항목 | 값 |
| --- | --- |
| run id | 26077734815 |
| trigger event | `workflow_dispatch` (input `tag=cycle132-smoke`) |
| ref | main |
| 시작 | 2026-05-19T05:15:12Z (KST 14:15:12) |
| `build-macos` | PASS — 1m27s, artifact `tootalk-macos-arm64` 30일 retention |
| `build-windows-wine` | FAIL — 27s, exit 1 (Zip artifact step) |

### 3-3. macOS arm64 self-hosted runner — PASS (cycle 132 + 140 동일)

self-hosted ARM64 runner 안 Python 3.13 venv + `app/requirements.txt` (PyQt6·qasync·aiortc·asyncmy·cryptography) + `pyinstaller>=6.0` 설치 + `tools/build.py --target macos` 실행 후 `dist/TooTalk.app` 산출 + zip + upload-artifact PASS. retention 30일. cycle 140 run 26081012261 에서도 1m29s PASS 재현.

### 3-4. cycle 132 Windows x64 via wine — FAIL (Zip artifact step)

**증상**: `Zip artifact` step 의 `cd dist-windows` 실행 → `bash: line 1: cd: dist-windows: No such file or directory` → exit 1.

**원인 정밀 분석**: `cdrx/pyinstaller-windows:python3` image 안 default `ENTRYPOINT` → `/entrypoint.sh` 자체 wrap script 로 정의되어 있어 docker `CMD` arg `/bin/sh -c "pip install ... && pyinstaller ..."` 가 entrypoint script 의 argument 로 전달되고 무시된다. 결과적으로 `pip install` + `pyinstaller` 명령 자체가 실행되지 않으며 호스트 mount path 안 `dist-windows/` 디렉토리 생성 부재.

**log 증거** (run 26077734815, Windows job):

```
2026-05-19T05:15:42.0999344Z /bin/sh -c pip install -r app/requirements.txt && pyinstaller build/tootalk.spec --clean --noconfirm --distpath dist-windows --workpath build/work-win
2026-05-19T05:15:42.1739099Z /home/runner/work/_temp/0221ef3d-8895-4c98-b0b4-c75cdc215fec.sh: line 1: cd: dist-windows: No such file or directory
2026-05-19T05:15:42.1750548Z ##[error]Process completed with exit code 1.
```

마지막 PyInstaller log line timestamp `05:15:42.0999` 와 Zip artifact step 시작 `05:15:42.1652` 간격 0.07초 → 실제 pip install + PyInstaller 가 요구하는 수 분 단위 작업 부재 = entrypoint 가 echo 후 즉시 0 exit 확정.

## 4. 회수 chain

### 4-0. cycle 140 회수 결론 — cdrx wine image 영구 폐기 + `windows-latest` 마이그레이션 의무

cycle 140 결과 → 실패 layer 가 3 종으로 확정된다:

1. **cdrx/pyinstaller-windows:python3 = Python 3.7 stale image** — pip 19.3.1 (2019년 릴리즈) + PyQt6 가 Python ≥ 3.9 요구 → 호환 부재. image 자체가 6+ 년 유지보수 부재.
2. **wine prefix `cp1252` locale fixed** — UTF-8 한글 주석을 포함한 requirements.txt → cycle 132 doc §4-2.3 의 risk 가 cycle 140 에서 실 재현. requirements.txt ASCII 제한 또는 wine LC_ALL 설정 회피 가능 → 양쪽 다 fragile.
3. **PyQt6 wine native binary 호환 risk 잠재** — UnicodeDecodeError 가 이전 단계 stop → PyQt6 install 단계 도달 부재. cdrx wine image 자체가 Qt6 DLL 패키징 부재 (image 가 2019년 PyQt5 기준).

**결론**: cdrx wine image cross-compile 경로를 **영구 폐기**한다. 다음 cycle (141 이후) `windows-latest` GitHub-hosted runner → native Windows Python 3.13 + PyInstaller → 마이그레이션 필수. 본 저장소 visibility = public ([reference_github_remote.md](../../README.md)) → `windows-latest` quota 무료 정합 + 사용자 memory `project_windows_build_via_wine.md` (wine cross-compile 가정) → 회수 의무.

### 4-1. cycle 132 entrypoint override patch (정합 PASS — 유지)

```yaml
- name: PyInstaller wine cross-compile
  run: |
    docker run --rm \
      --entrypoint /bin/sh \
      -v "$PWD:/src" \
      -w /src \
      cdrx/pyinstaller-windows:python3 \
      -c "pip install -r app/requirements.txt && pyinstaller build/tootalk.spec --clean --noconfirm --distpath dist-windows --workpath build/work-win && ls -la dist-windows"
- name: Zip artifact
  run: |
    ls -la dist-windows || (echo "dist-windows 부재 — PyInstaller 산출 실패" && exit 1)
    cd dist-windows && zip -r "TooTalk-windows-x64.zip" .
```

핵심 변경: `--entrypoint /bin/sh` 로 default entrypoint override + `-c` flag 의 단일 shell command 직접 전달. Zip artifact step 의 `ls -la dist-windows` 의 의 fail-fast 로 silent failure 회피.

### 4-2. cycle 141 회수 검증 의무 — `windows-latest` 마이그레이션 patch sketch

cycle 140 결과를 반영한 build.yml patch 후보:

```yaml
build-windows-native:
  name: Windows x64 native (.exe)
  runs-on: windows-latest
  steps:
    - uses: actions/checkout@v4
    - name: Python 3.13 setup
      uses: actions/setup-python@v5
      with:
        python-version: '3.13'
    - name: deps + PyInstaller
      shell: pwsh
      run: |
        python -m pip install --upgrade pip
        python -m pip install -r app/requirements.txt pyinstaller>=6.0
    - name: PyInstaller build
      shell: pwsh
      run: pyinstaller build/tootalk.spec --clean --noconfirm --distpath dist-windows --workpath build/work-win
    - name: Zip artifact
      shell: pwsh
      run: Compress-Archive -Path dist-windows/* -DestinationPath dist-windows/TooTalk-windows-x64.zip
    - name: Upload artifact
      uses: actions/upload-artifact@v4
      with:
        name: tootalk-windows-x64
        path: dist-windows/TooTalk-windows-x64.zip
        retention-days: 30
```

**검증 절차**:

1. **재 trigger** — `gh workflow run build.yml --ref main -f tag=cycle141-windows-native` + run id capture.
2. **PyInstaller 산출 검증** — `dist-windows/TooTalk/` 또는 `dist-windows/TooTalk.exe` 호스트 path 존재 확인 + size > 1MB.
3. **PyQt6 Windows native 호환성** — windows-latest 안 Python 3.13 + PyQt6 6.7+ wheel binary 의 정상 install 검증 (pip 의 manylinux/win_amd64 wheel 자동 선택).
4. **memory 가드레일 갱신** — `project_windows_build_via_wine.md` → `project_windows_build_native.md` rename + content 회수 (사용자 directive 확정 의무).
5. **build.yml workflow_dispatch input 확장** — `tag` input 외에 `target` (`macos`·`windows`·`both`) input 추가 검토 (단일 platform smoke 회수 효율 향상 목적).

### 4-3. 회수 chain 의무 순서 (cycle 141 기준)

| 단계 | 책임 | 검증 명령 |
| --- | --- | --- |
| ① cycle 140 doc 갱신 | main session (본 cycle) | `git diff docs/operations/windows-wine-smoke.md` |
| ② lint | doc-gardener / markdown lint | `markdownlint docs/operations/windows-wine-smoke.md` |
| ③ commit + push | 사용자 manual ack (본 cycle directive §절대 금지 — git commit/push 차단 정합) | `SKIP_PREPUSH=1 git push origin main` |
| ④ build.yml 재 patch | cycle 141 | wine job 폐기 + `build-windows-native` job 신설 (§4-2 sketch) |
| ⑤ 재 trigger | cycle 141 | `gh workflow run build.yml --ref main -f tag=cycle141-windows-native` |
| ⑥ memory 가드레일 회수 | cycle 141 | `project_windows_build_via_wine.md` 회수 + native patch 의무 신규 메모리 |
| ⑦ 결과 doc 갱신 | cycle 141 | 본 문서 §3-0 표 row 추가 (cycle 141 run id + status) |
| ⑧ Phase 1 빌드 인프라 평가 반영 | cycle 141 | `docs/assessments/productization.md` + `docs/assessments/vibe-coding.md` 전체 rewrite (사용자 directive — 평가 매 cycle 전면 재작성) |

## 5. 사용자 manual commit ack 의무

본 cycle directive §절대 금지 ("git commit / push 차단") 정합 — main session 은 build.yml patch + 본 doc 신설 까지만 수행하며, 다음 commit/push 는 **사용자 manual 승인** 후 진행. 사용자 directive "1 완료 영구승인" (SKIP_PREPUSH) 는 cycle 별 명시 GO 후만 실행한다.

## 6. 참조

- run 26081012261 (cycle 140) — https://github.com/oneticket99/p2p_msg/actions/runs/26081012261
- run 26077734815 (cycle 132) — https://github.com/oneticket99/p2p_msg/actions/runs/26077734815
- cdrx/pyinstaller-windows GitHub — https://github.com/cdrx/docker-pyinstaller (entrypoint 동작 source + 2019년 이후 stale)
- PyInstaller spec docs — https://pyinstaller.org/en/stable/spec-files.html
- GitHub Actions windows-latest runner spec — https://github.com/actions/runner-images (Windows Server 2022 + Python 3.13)
- 정본: `CLAUDE_HARNESS_IMPORTANT.md` §B (5단계 워크플로우) · §S (분류기 hard block)
- 가드레일: `~/.claude/projects/.../memory/feedback_skip_prepush_permanent_approval.md` · `project_windows_build_via_wine.md` (cycle 141 회수 의무)
