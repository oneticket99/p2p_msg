#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk Phase 5 cycle 133 — i18n .ts → .qm compile script
# 한글 주석 — Qt Linguist 의 lrelease 실행 wrapper. binary 부재 시 graceful skip.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TS_DIR="${ROOT_DIR}/app/i18n/translations"

# 한글 주석 — lrelease binary 자동 detect (pyside6-lrelease / lrelease6 / lrelease 순서)
LRELEASE_BIN=""
for candidate in pyside6-lrelease lrelease6 lrelease; do
    if command -v "${candidate}" >/dev/null 2>&1; then
        LRELEASE_BIN="${candidate}"
        break
    fi
done

if [[ -z "${LRELEASE_BIN}" ]]; then
    echo "[i18n-compile] lrelease binary 부재 — 안내 명령:" >&2
    echo "    macOS  : brew install qt && export PATH=\"\$(brew --prefix qt)/bin:\$PATH\"" >&2
    echo "    Ubuntu : sudo apt install qttools5-dev-tools" >&2
    echo "    pip    : pip install pyside6 (pyside6-lrelease 동봉)" >&2
    exit 0
fi

echo "[i18n-compile] lrelease=${LRELEASE_BIN} TS_DIR=${TS_DIR}"

shopt -s nullglob
TS_FILES=("${TS_DIR}"/tootalk_*.ts)
if [[ ${#TS_FILES[@]} -eq 0 ]]; then
    echo "[i18n-compile] ts 파일 부재 — ${TS_DIR}/tootalk_*.ts" >&2
    exit 1
fi

# 한글 주석 — 각 .ts 파일 단위 compile + .qm 생성 로그
for ts in "${TS_FILES[@]}"; do
    qm="${ts%.ts}.qm"
    echo "[i18n-compile] ${ts} → ${qm}"
    "${LRELEASE_BIN}" "${ts}" -qm "${qm}"
done

echo "[i18n-compile] 완료 — $(ls -1 "${TS_DIR}"/*.qm 2>/dev/null | wc -l | tr -d ' ') qm 파일 생성"
