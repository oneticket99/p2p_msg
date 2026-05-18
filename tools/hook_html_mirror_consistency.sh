#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk(p2p_msg) Stop hook — HTML mirror 동시 갱신 의무 강제 검사.
#
# 사용자 directive 2026-05-21 — "평가문서를 마크다운만 만들면 안되는거잖아?
# 이것도 훅에 넣어줄까?". CLAUDE.md §10-6 의 HTML 동시 유지 의무 6 pair 의
# Stop hook 강제 차단.
#
# 검사 6 pair (CLAUDE.md §10-6 정합):
#   - Structure.md ↔ docs/html/Structure.html
#   - ARCHITECTURE.md ↔ docs/html/ARCHITECTURE.html
#   - FRONTEND.md ↔ docs/html/FRONTEND.html
#   - DESIGN.md ↔ docs/html/DESIGN.html
#   - docs/assessments/productization.md ↔ docs/html/productization.html
#   - docs/assessments/vibe-coding.md ↔ docs/html/vibe-coding.html
#
# 검사 로직:
#   .md = working tree dirty (M / A) + 대응 .html = clean → BLOCK
#   양쪽 동시 dirty 또는 양쪽 동시 clean → PASS
#
# exit 0 = PASS, exit 2 = BLOCK
#
# 정합 가드레일: [[feedback-doc-consistency-mandatory]]

set -e

ROOT="${CLAUDE_PROJECT_DIR:-/Users/oneticket_toonation/Documents/vscode_work/p2p_msg}"
cd "$ROOT" || exit 0

# 6 pair 정의 — md_path|html_path
PAIRS=(
  "Structure.md|docs/html/Structure.html"
  "ARCHITECTURE.md|docs/html/ARCHITECTURE.html"
  "FRONTEND.md|docs/html/FRONTEND.html"
  "DESIGN.md|docs/html/DESIGN.html"
  "docs/assessments/productization.md|docs/html/productization.html"
  "docs/assessments/vibe-coding.md|docs/html/vibe-coding.html"
)

# git status --porcelain — working tree + staged 양쪽
STATUS=$(git status --porcelain 2>/dev/null || echo "")

DRIFT=""
for pair in "${PAIRS[@]}"; do
  md="${pair%|*}"
  html="${pair#*|}"
  # md 변경 여부 (M / A / R / ?? 매치)
  md_dirty=$(echo "$STATUS" | grep -E "^[ MARC?]?[MARC?] $md\$" || echo "")
  html_dirty=$(echo "$STATUS" | grep -E "^[ MARC?]?[MARC?] $html\$" || echo "")

  if [[ -n "$md_dirty" && -z "$html_dirty" ]]; then
    DRIFT+="\n  - .md 변경 단 .html 미갱신 — $md / $html"
  fi
  if [[ -z "$md_dirty" && -n "$html_dirty" ]]; then
    DRIFT+="\n  - .html 변경 단 .md 미갱신 — $html / $md"
  fi
done

if [[ -n "$DRIFT" ]]; then
  cat >&2 <<EOF
🔴 HTML mirror 동시 갱신 의무 위반 — CLAUDE.md §10-6 차단
$(printf "%b" "$DRIFT")

조치:
1. 6 pair 의 .md / .html 양쪽 동시 갱신 의무
2. 부재 의 mirror 의 추가 또는 .md 변경 revert
3. commit + push
EOF
  exit 2
fi

exit 0
