#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk(p2p_msg) Stop hook — 문서 정합 강제 검사.
#
# [[feedback-doc-consistency-mandatory]] 정합.
# 사용자 directive 2026-05-18 — 작업 완료 시 문서 정합도 강제.
#
# 검사:
# 1. ARCHITECTURE.md §6 모듈 책임 표 의 app/<dir>/ + server/<dir>/ 명시 = 실 디렉토리 정합
# 2. ARCHITECTURE.md §6 의 의 존재 path 의 ls 검증 — 부재 path 명시 = drift block

set -e

ROOT="${CLAUDE_PROJECT_DIR:-/Users/oneticket_toonation/Documents/vscode_work/p2p_msg}"
cd "$ROOT" || exit 0

ARCH="$ROOT/ARCHITECTURE.md"
[[ ! -f "$ARCH" ]] && exit 0

DRIFT=""

# 역방향 — app/<dir> + server/<dir> 실 존재 단 ARCHITECTURE 미명시
# regex 정밀화 — `server/api/`, `server/api/auth_handlers.py`, `server/api` 모두 매치
for d in app/crypto server/api server/auth server/db server/mail server/signaling_persistence.py; do
  if [[ -e "$ROOT/$d" ]]; then
    escaped="${d//\//\\/}"
    if ! grep -qE "\`${escaped}/?(/[a-z_.]+)?\`" "$ARCH" 2>/dev/null; then
      DRIFT+="\n  - 실 path 존재 단 ARCHITECTURE.md §6 미명시: $d"
    fi
  fi
done

# Phase 2+ 의 예고 path = ARCHITECTURE §8 진화 경로 영역 — false positive 회피
# §6 안 의 backtick path 만 검사 (forward direction).
SECTION6=$(awk '/^## 6\. / {flag=1; next} /^## 7\./ {flag=0} flag' "$ARCH" 2>/dev/null)
PATHS=$(echo "$SECTION6" | grep -oE '`(app|server)/[a-z_]+(/[a-z_.]+)*/?`' | tr -d '`' | sort -u)
DRIFT_FWD=""
while IFS= read -r p; do
  [[ -z "$p" ]] && continue
  clean="${p%/}"
  if [[ ! -e "$ROOT/$clean" ]]; then
    DRIFT_FWD+="\n  - ARCHITECTURE.md §6 명시 path 부재: $p"
  fi
done <<< "$PATHS"
DRIFT="$DRIFT_FWD$DRIFT"

if [[ -n "$DRIFT" ]]; then
  cat >&2 <<EOF
🔴 문서 정합 drift 검출 — ARCHITECTURE.md §6 module 표 차단 ([[feedback-doc-consistency-mandatory]])
$(printf "%b" "$DRIFT")

조치:
1. ARCHITECTURE.md §6 모듈 책임 표 갱신 — 실 디렉토리/모듈 정합
2. Structure.md 동기 (트리 갱신)
3. commit + push
EOF
  exit 2
fi

exit 0
