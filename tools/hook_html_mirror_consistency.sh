#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk(p2p_msg) Stop + PostToolUse hook — HTML mirror 동시 갱신 의무 강제 차단 + content fingerprint mismatch detect.
#
# 사용자 directive 2026-05-21 + 2026-05-19 cycle 133 강화 — "훅을 만들어도 왜 강제화가 안될까? 트리거 만들어?".
# CLAUDE.md §10-6 의 HTML 동시 유지 의무 6 pair 강제 차단.
#
# 검사 6 pair (CLAUDE.md §10-6 정합):
#   - Structure.md ↔ docs/html/Structure.html
#   - ARCHITECTURE.md ↔ docs/html/ARCHITECTURE.html
#   - FRONTEND.md ↔ docs/html/FRONTEND.html
#   - DESIGN.md ↔ docs/html/DESIGN.html
#   - docs/assessments/productization.md ↔ docs/html/productization.html
#   - docs/assessments/vibe-coding.md ↔ docs/html/vibe-coding.html
#
# 검사 로직 2 layer (강화 cycle 133):
#   layer 1 — working tree dirty mismatch (.md dirty + .html clean → BLOCK)
#   layer 2 — content fingerprint mismatch (last_verified ISO + 사이클 N 의 .md ↔ .html 일치 검증)
#             commit clean 상태에서도 fire — 평가 md (last_verified + 사이클 N) 의 HTML 정합 의무
#
# exit 0 = PASS, exit 2 = BLOCK
#
# 정합 가드레일: [[feedback-doc-consistency-mandatory]] + [[feedback-assessment-full-rewrite]]

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

# git status — working tree + staged
STATUS=$(git status --porcelain 2>/dev/null || echo "")

DRIFT=""

# ─── Layer 1 — working tree dirty mismatch ──────────────────
for pair in "${PAIRS[@]}"; do
  md="${pair%|*}"
  html="${pair#*|}"
  md_dirty=$(echo "$STATUS" | grep -E "^[ MARC?]?[MARC?] $md\$" || echo "")
  html_dirty=$(echo "$STATUS" | grep -E "^[ MARC?]?[MARC?] $html\$" || echo "")

  if [[ -n "$md_dirty" && -z "$html_dirty" ]]; then
    DRIFT+="\n  [layer1 dirty] .md 변경 단 .html 미갱신 — $md / $html"
  fi
  if [[ -z "$md_dirty" && -n "$html_dirty" ]]; then
    DRIFT+="\n  [layer1 dirty] .html 변경 단 .md 미갱신 — $html / $md"
  fi
done

# ─── Layer 2 — content fingerprint mismatch (평가 md 2 pair 만 — last_verified ISO + 사이클 N) ──────────────────
# 한글 주석: 평가 snapshot 2 pair (productization + vibe-coding) 의 last_verified + 사이클 N 정합 검증.
# 기타 4 pair (Structure / ARCHITECTURE / FRONTEND / DESIGN) = frontmatter 부재 의 fingerprint 검증 skip.

ASSESS_PAIRS=(
  "docs/assessments/productization.md|docs/html/productization.html"
  "docs/assessments/vibe-coding.md|docs/html/vibe-coding.html"
)

for pair in "${ASSESS_PAIRS[@]}"; do
  md="${pair%|*}"
  html="${pair#*|}"
  [ -f "$md" ] || continue
  [ -f "$html" ] || continue

  # 한글 주석: md frontmatter last_verified ISO 추출
  md_lv=$(grep -m1 -E '^last_verified:' "$md" | sed 's/^last_verified:[[:space:]]*//' | tr -d '"' || echo "")
  html_lv=$(grep -m1 -oE 'last_verified[":>[:space:]]+[0-9TZ:+-]+' "$html" | sed -E 's/^last_verified[":>[:space:]]+//' || echo "")

  if [[ -n "$md_lv" && -n "$html_lv" && "$md_lv" != "$html_lv" ]]; then
    DRIFT+="\n  [layer2 fingerprint] last_verified mismatch — $md ($md_lv) ≠ $html ($html_lv)"
  fi

  # 한글 주석: md 최근 갱신 사이클 N 추출 (예 "사이클 132") + html 동일 검증
  md_cycle=$(grep -m1 -oE '사이클 [0-9]+' "$md" | head -1 || echo "")
  html_cycle=$(grep -m1 -oE '사이클 [0-9]+' "$html" | head -1 || echo "")

  if [[ -n "$md_cycle" && -n "$html_cycle" && "$md_cycle" != "$html_cycle" ]]; then
    DRIFT+="\n  [layer2 fingerprint] 사이클 N mismatch — $md ($md_cycle) ≠ $html ($html_cycle)"
  fi
done

if [[ -n "$DRIFT" ]]; then
  cat >&2 <<EOF
🔴 HTML mirror 동시 갱신 의무 위반 — CLAUDE.md §10-6 차단 (2 layer 강화)
$(printf "%b" "$DRIFT")

조치:
1. 6 pair 의 .md / .html 양쪽 동시 갱신 의무
2. 평가 md 2 pair = last_verified + 사이클 N 정합 의무 (commit clean state 도 fire)
3. 부재 mirror 의 추가 또는 .md 변경 revert
4. commit + push
EOF
  exit 2
fi

exit 0
