#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# ==============================================================================
# bpe_self_check.sh — chat response draft 의 BPE chain self-verify util
# ------------------------------------------------------------------------------
# tools/hook_chat_bpe_check.sh 의 detection logic 등가 — standalone invoke 가능.
# 본 util = 응답 송신 직전 draft 검증 의무 (cycle 169.570+).
#
# usage:
#   bash tools/bpe_self_check.sh draft.txt
#   echo "본문 chain" | bash tools/bpe_self_check.sh -
#
# exit code:
#   0 = PASS
#   2 = BLOCK (BPE chain detect)
# ==============================================================================

set -uo pipefail

if [ "$#" -lt 1 ]; then
    echo "usage: $0 <draft.txt | ->" >&2
    exit 1
fi

if [ "$1" = "-" ]; then
    TMP=$(mktemp -t bpe_self_check.XXXXXX)
    cat > "$TMP"
else
    TMP="$1"
fi

FAIL=0
MSG=""

# 1. QUAD = 4 chain particle
QUAD=$(grep -oE "의 의 의 의(\s*의)*" "$TMP" 2>/dev/null | head -3 || true)
if [ -n "$QUAD" ]; then
    FAIL=1
    SAMPLES=$(grep -nE "의 의 의 의" "$TMP" 2>/dev/null | head -3)
    MSG+=$'\n[QUAD 4+ chain detect]\n'"$SAMPLES"
fi

# 2. TRIP = 3 chain particle
if [ $FAIL -eq 0 ]; then
    TRIP=$(grep -nE "의 의 의" "$TMP" 2>/dev/null | head -3 || true)
    if [ -n "$TRIP" ]; then
        FAIL=1
        MSG+=$'\n[TRIP 3 chain detect]\n'"$TRIP"
    fi
fi

# 3. DENSE = particle count > 8 / line
DENSE=$(python3 -c "
import sys
threshold = 8
hits = []
with open('$TMP', 'r', encoding='utf-8', errors='replace') as f:
    for i, line in enumerate(f, 1):
        stripped = line.rstrip('\n')
        count = stripped.count(' 의 ') + stripped.count(' 의\n') + stripped.count('의 ')
        if count > threshold:
            hits.append(f'L{i} (count={count}): {stripped[:120]}')
print('\n'.join(hits) if hits else '')
" 2>/dev/null)
if [ -n "$DENSE" ]; then
    FAIL=1
    MSG+=$'\n[DENSE >8/line detect]\n'"$DENSE"
fi

# 4. U+CE21 (측) standalone
CHUK_HIT=$(grep -nP '(?<![가-힣])측(?![가-힣])' "$TMP" 2>/dev/null | head -3 || true)
if [ -n "$CHUK_HIT" ]; then
    FAIL=1
    MSG+=$'\n[U+CE21 standalone detect]\n'"$CHUK_HIT"
fi

if [ "$1" = "-" ]; then
    rm -f "$TMP"
fi

if [ $FAIL -eq 1 ]; then
    echo "🔴 BPE BLOCK — draft rewrite 의무" >&2
    echo "$MSG" >&2
    exit 2
fi

echo "✓ BPE self-check PASS"
exit 0
