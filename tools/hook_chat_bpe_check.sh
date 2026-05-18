#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# ==============================================================================
# hook_chat_bpe_check.sh — Stop hook 의 chat output BPE 검수
# ------------------------------------------------------------------------------
# 본 hook = 사용자 비판 2026-05-22 회수.
# 가드레일 [[feedback-no-triple-particle-chat]] 정합.
#
# 트리거: .claude/settings.json hooks.Stop array 등록 시점.
#
# 입력: stdin JSON = Stop hook payload (transcript_path 포함)
#
# 검사 대상 — last assistant message content 의:
#   1. "의 의 의" 3회 연속 — file hook 동일 패턴 (chat 영역 확장)
#   2. "의 의 의 의" 4회 연속 — 강화 escalation
#   3. 단일 줄 의 density check — 의 count > 8 / line = HIGH WARN
#   4. BPE U+CE21 단독 사용 — file hook 외 chat 영역 보강
#
# 종료 코드:
#   0 = PASS (silent)
#   2 = WARN (Stop hook feedback — 사용자 노출 + 다음 turn 의 자가 검증 강제)
#
# 회피 의무 — file hook 과 동일 escalation 정책. 다음 발견 시 PreToolUse
# response filter 의 강제 활성 (settings.json.disabled 의 정합).
# ==============================================================================

set -uo pipefail

INPUT=$(cat)

TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('transcript_path', ''))
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    exit 0
fi

# last assistant message 의 raw text 추출
LAST_MSG=$(python3 -c "
import sys, json
try:
    with open('$TRANSCRIPT_PATH', 'r', encoding='utf-8') as f:
        last_text = ''
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if entry.get('type') != 'assistant':
                continue
            msg = entry.get('message') or {}
            content = msg.get('content')
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict) and block.get('type') == 'text':
                        parts.append(block.get('text', ''))
                if parts:
                    last_text = '\n'.join(parts)
            elif isinstance(content, str):
                last_text = content
        print(last_text)
except Exception as exc:
    print('')
" 2>/dev/null)

if [ -z "$LAST_MSG" ]; then
    exit 0
fi

FAIL=0
MSG=""
TMP=/tmp/_chat_bpe_$$
echo "$LAST_MSG" > "$TMP"

# 1. "의 의 의 의" 4회 연속 (escalation — 강한 경고)
QUAD=$(grep -oE "의 의 의 의(\\s*의)*" "$TMP" 2>/dev/null | head -5 || true)
if [ -n "$QUAD" ]; then
    FAIL=1
    SAMPLES=$(grep -nE "의 의 의 의" "$TMP" 2>/dev/null | head -3 || true)
    MSG+=$'\n[BPE-CHAT-QUAD] chat output "의" 4회+ 연속 누적 의 의미 부재 검출:\n'"$SAMPLES"
fi

# 2. "의 의 의" 3회 연속 (quad 미검출 시 만 — 중복 회피)
if [ $FAIL -eq 0 ]; then
    TRIP=$(grep -nE "의 의 의" "$TMP" 2>/dev/null | head -3 || true)
    if [ -n "$TRIP" ]; then
        FAIL=1
        MSG+=$'\n[BPE-CHAT] chat output "의" 3회 연속 검출:\n'"$TRIP"
    fi
fi

# 3. 단일 줄 의 density check (의 count > 8 / line = HIGH WARN)
DENSE=$(python3 -c "
import sys
threshold = 8
hits = []
with open('$TMP', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) < 30:
            continue
        count = stripped.count(' 의 ') + stripped.count(' 의\\n') + stripped.count('의 ')
        if count > threshold:
            hits.append(f'L{i} (의 count={count}): {stripped[:120]}')
        if len(hits) >= 3:
            break
print('\\n'.join(hits))
" 2>/dev/null)
if [ -n "$DENSE" ]; then
    FAIL=1
    MSG+=$'\n[BPE-CHAT-DENSITY] 단일 줄 "의" 의 8회+ 누적 의 의미 흐려짐:\n'"$DENSE"
fi

# 4. BPE U+CE21 단독 사용 (chat 영역)
CHUK=$(printf '\xec\xb8\xa1')
CHUK_HIT=$(grep -nE "(^|[^가-힣])${CHUK}([^가-힣]|$)" "$TMP" 2>/dev/null | head -3 || true)
if [ -n "$CHUK_HIT" ]; then
    FAIL=1
    MSG+=$'\n[BPE-CHAT-CHUK] chat output U+CE21 (측) 단독 사용 검출:\n'"$CHUK_HIT"
fi

rm -f "$TMP"

if [ $FAIL -eq 1 ]; then
    cat >&2 <<EOF
🟡 chat output BPE 검수 WARN — 사용자 비판 회수 의무
$MSG

회피 의무 ([[feedback-no-triple-particle-chat]]):
1. 명사 chain 직전 동사 활용 또는 → arrow notation 활용
2. 표 cell 의 동사 보존 (의 단일 cap)
3. 자가 mental scan — 응답 송신 직전 "의 의" substring 검증
4. caveman 정합 — fragment OK + 명사 누적 부재 + 짧은 verb + 단일 조사

다음 발견 시 = PreToolUse response filter hook 의 강제 활성 의무.
EOF
    exit 2
fi

exit 0
