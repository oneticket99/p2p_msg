#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk PyInstaller build wrapper — cycle 169.94 신설.
#
# 사용자 directive 2026-05-20 — "빌드 스크립트 만들어놔".
#
# chain:
#   1. .venv 존재 검증 + 의무 의 부재 시 생성
#   2. requirements + pyinstaller install
#   3. tools/build.py --target {macos|windows} run
#   4. dist/TooTalk.app zip 패키징 (macOS)
#   5. SHA-256 산출 + 결과 log
#
# 사용:
#   scripts/build.sh              # macOS native (default)
#   scripts/build.sh windows      # Windows cross-compile (wine 폐기 — windows-latest CI)
#   scripts/build.sh clean        # dist/build cache 삭제

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# 한글 주석 — color output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[build.sh]${NC} $*"; }
warn() { echo -e "${YELLOW}[build.sh][WARN]${NC} $*"; }
fail() { echo -e "${RED}[build.sh][FAIL]${NC} $*" >&2; exit 1; }

TARGET="${1:-macos}"

# clean 분기
if [[ "$TARGET" == "clean" ]]; then
    log "dist/ + build/work/ 삭제"
    rm -rf dist/ build/work/
    log "PASS — clean complete"
    exit 0
fi

# venv 검증
if [[ ! -d ".venv" ]]; then
    warn ".venv 부재 → python3 -m venv .venv 생성"
    python3 -m venv .venv
fi

VENV_PY=".venv/bin/python"
[[ -x "$VENV_PY" ]] || fail ".venv/bin/python 부재"

log "Python = $($VENV_PY --version)"

# requirements install (idempotent)
log "requirements install"
$VENV_PY -m pip install --quiet --upgrade pip
$VENV_PY -m pip install --quiet -r app/requirements.txt
$VENV_PY -m pip install --quiet -r app/requirements-dev.txt

# PyInstaller 존재 검증
if ! $VENV_PY -c "import PyInstaller" 2>/dev/null; then
    fail "PyInstaller install fail — pip log 확인 의무"
fi

# target 분기
case "$TARGET" in
    macos|mac|darwin)
        log "target = macOS arm64 native build"
        $VENV_PY tools/build.py --target macos
        APP_PATH="dist/TooTalk.app"
        if [[ ! -d "$APP_PATH" ]]; then
            fail "build fail — $APP_PATH 부재"
        fi
        log "build PASS — $APP_PATH"
        # 한글 주석 — zip 패키징 + SHA-256
        ZIP_PATH="dist/TooTalk-macos-arm64.zip"
        log "zip 패키징 → $ZIP_PATH"
        (cd dist && ditto -c -k --sequesterRsrc --keepParent TooTalk.app TooTalk-macos-arm64.zip)
        ZIP_SIZE=$(du -h "$ZIP_PATH" | cut -f1)
        SHA256=$(shasum -a 256 "$ZIP_PATH" | cut -d' ' -f1)
        log "PASS — size=$ZIP_SIZE  sha256=$SHA256"
        ;;
    windows|win)
        log "target = Windows x64"
        warn "wine cross-compile 폐기 (cycle 142 영구화) — GitHub Actions windows-latest runner 의무"
        warn "local Windows build 경로 부재 → .github/workflows/release.yml chain 사용"
        exit 2
        ;;
    *)
        fail "지원 target = macos | windows | clean (현재 '$TARGET')"
        ;;
esac
