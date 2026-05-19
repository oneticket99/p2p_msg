#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Stop hook — 매 작업 마무리 시점 평가 문서 + 토큰 사용량 문서 재 작성 강제 trigger.
# 사용자 directive 2026-05-19 cycle 148 — "각 작업 마무리 시에 반드시 평가문서 + 토큰사용량 문서 재작성 하도록 트리거 만들고 트리거 걸어".
#
# 검사 4 layer:
#   layer 1 — 평가 md 2 pair (productization.md + vibe-coding.md) 마지막 갱신 ↔ 현재 KST 차이 검증 (>6시간 = stale)
#   layer 2 — 평가 md ↔ HTML mirror fingerprint mismatch detect (hook_html_mirror_consistency 의 기존 정합)
#   layer 3 — token-usage-30d.html / .json 마지막 갱신 ↔ 현재 KST 차이 검증 (>24시간 = stale)
#   layer 4 — git working tree 안 평가 / token usage 미커밋 변경 detect → 사용자 manual commit 안내
#
# exit 0 = PASS / exit 2 = BLOCK
#
# 정합 가드레일: [[feedback-assessment-full-rewrite]] + [[feedback-assessment-full-section-sweep]] + [[feedback-assessment-freshness-trigger]]

set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" || exit 0

# 한글 주석 — KST 현재 시각 (timestamp seconds)
NOW_EPOCH=$(date +%s)
WARN_HOURS=${HOOK_ASSESS_STALE_HOURS:-6}
WARN_TOKEN_HOURS=${HOOK_TOKEN_STALE_HOURS:-24}

DRIFT=""

# ─── Layer 1 + 2 — 평가 md staleness ──────────────────
for f in docs/assessments/productization.md docs/assessments/vibe-coding.md ; do
    [ -f "$f" ] || continue
    mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo 0)
    age_hours=$(( (NOW_EPOCH - mtime) / 3600 ))
    if [ "$age_hours" -ge "$WARN_HOURS" ] ; then
        DRIFT+="\n  [layer1 stale] $f 마지막 갱신 ${age_hours}h 경과 (cap ${WARN_HOURS}h) — 전면 rewrite 의무"
    fi
done

# ─── Layer 3 — token-usage staleness ──────────────────
TOKEN_HTML="docs/operations/token-usage-30d.html"
TOKEN_JSON="docs/operations/token-usage-30d.json"

for f in "$TOKEN_HTML" "$TOKEN_JSON" ; do
    [ -f "$f" ] || continue
    mtime=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f" 2>/dev/null || echo 0)
    age_hours=$(( (NOW_EPOCH - mtime) / 3600 ))
    if [ "$age_hours" -ge "$WARN_TOKEN_HOURS" ] ; then
        DRIFT+="\n  [layer3 token-stale] $f 마지막 갱신 ${age_hours}h 경과 (cap ${WARN_TOKEN_HOURS}h) — 재 산출 의무"
    fi
done

# ─── Layer 4 — git uncommitted 평가/token 변경 ──────────────────
STATUS=$(git status --porcelain 2>/dev/null || echo "")
UNCOMMIT_ASSESS=$(echo "$STATUS" | grep -E "docs/(assessments|html/(productization|vibe-coding))|docs/operations/token-usage-30d" | head -5)
if [ -n "$UNCOMMIT_ASSESS" ] ; then
    DRIFT+="\n  [layer4 uncommit] 평가/token usage 미커밋 변경 — commit + push 의무"
fi

# ─── 결과 분기 ──────────────────
if [ -n "$DRIFT" ] ; then
    cat >&2 <<EOF
🔴 평가 + 토큰 사용량 staleness detect — 강제 재작성 의무
$(printf "%b" "$DRIFT")

조치 4단계:
1. productization.md + vibe-coding.md 전면 rewrite (§1+§2+§3+§5+§6+§8 6 영역 sweep)
2. HTML mirror 2종 동시 rewrite (CLAUDE.md §10-6)
3. token-usage-30d.html + .json 재 산출 (sub-agent general-purpose spawn 권장)
4. commit + push (SKIP_PREPUSH=1 git push origin main)

env override — HOOK_ASSESS_STALE_HOURS / HOOK_TOKEN_STALE_HOURS
EOF
    exit 2
fi

exit 0
