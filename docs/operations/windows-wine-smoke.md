---
title: Windows wine cross-compile smoke (cycle 132)
status: investigated
phase: Phase 1 — 빌드 인프라
cycle: 132
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

| 항목 | 값 |
| --- | --- |
| run id | 26077734815 |
| trigger event | `workflow_dispatch` (input `tag=cycle132-smoke`) |
| ref | main |
| 시작 | 2026-05-19T05:15:12Z (KST 14:15:12) |
| `build-macos` | PASS — 1m27s, artifact `tootalk-macos-arm64` 30일 retention |
| `build-windows-wine` | FAIL — 27s, exit 1 (Zip artifact step) |

### 3-1. macOS arm64 self-hosted runner — PASS

self-hosted ARM64 runner 의 의 Python 3.13 venv + `app/requirements.txt` (PyQt6·qasync·aiortc·asyncmy·cryptography) + `pyinstaller>=6.0` 설치 + `tools/build.py --target macos` 실행 후 `dist/TooTalk.app` 산출 + zip + upload-artifact PASS. retention 30일.

### 3-2. Windows x64 via wine — FAIL (Zip artifact step)

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

### 4-1. build.yml 의 entrypoint override patch (본 cycle 적용)

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

### 4-2. 다음 cycle 의 회수 검증 의무

1. **재 trigger** — `gh workflow run build.yml --ref main -f tag=cycle133-recovery` + run id capture.
2. **PyInstaller 산출 검증** — `dist-windows/TooTalk/` 또는 `dist-windows/TooTalk.exe` 의 호스트 path 의 존재 확인.
3. **PyQt6 wine 호환성** — wine 의 Python 3 의 PyQt6 binary install 가능 여부 검증. `cdrx/pyinstaller-windows:python3` image 가 PyQt6 native dependency (`Qt6` DLL · `libGL` · `libfontconfig`) 의 wine prefix 의 부재 시 PyInstaller 의 `hidden imports` 추가 또는 PySide6 fallback 검토.
4. **fallback path** — wine 의 PyQt6 install 영구 실패 시 본 job 을 `windows-latest` GitHub-hosted runner 로 마이그레이션 검토 (사용자 visibility public 정합 — quota 무료). cycle 132 의 self-hosted macOS + GitHub-hosted Windows 의 2 runner pattern 의 정합.
5. **build.yml workflow_dispatch input 확장** — `tag` input 외에 `target` (`macos`·`windows`·`both`) input 추가 검토 (단일 platform smoke 회수 효율 향상 목적).

### 4-3. 회수 chain 의무 순서

| 단계 | 책임 | 검증 명령 |
| --- | --- | --- |
| ① patch 적용 | main session (본 cycle) | `git diff .github/workflows/build.yml` |
| ② lint | doc-gardener / markdown lint | `markdownlint docs/operations/windows-wine-smoke.md` |
| ③ commit + push | 사용자 manual ack (본 cycle 의 절대 금지 의 git commit/push 차단 정합) | `SKIP_PREPUSH=1 git push origin main` |
| ④ 재 trigger | 다음 cycle | `gh workflow run build.yml --ref main -f tag=cycle133-recovery` |
| ⑤ 결과 doc 갱신 | 다음 cycle | 본 문서 §3 의 row 추가 (cycle 133 run id + status) |
| ⑥ Phase 1 빌드 인프라 평가 반영 | 다음 cycle | `docs/assessments/productization.md` + `docs/assessments/vibe-coding.md` 전체 rewrite (사용자 directive — 평가 매 cycle 전면 재작성) |

## 5. 사용자 manual commit ack 의무

본 cycle directive §절대 금지 ("git commit / push 차단") 정합 — main session 은 build.yml patch + 본 doc 신설 까지만 수행하며, 다음 commit/push 는 **사용자 manual 승인** 후 진행. 사용자 directive "1 완료 영구승인" (SKIP_PREPUSH) 는 cycle 별 명시 GO 후만 실행한다.

## 6. 참조

- run 26077734815 — https://github.com/oneticket99/p2p_msg/actions/runs/26077734815
- cdrx/pyinstaller-windows GitHub — https://github.com/cdrx/docker-pyinstaller (entrypoint 동작 source)
- PyInstaller spec docs — https://pyinstaller.org/en/stable/spec-files.html
- 정본: `CLAUDE_HARNESS_IMPORTANT.md` §B (5단계 워크플로우) · §S (분류기 hard block)
- 가드레일: `~/.claude/projects/.../memory/feedback_skip_prepush_permanent_approval.md`
