#!/usr/bin/env bash
# ==============================================================================
# hook_telegram_report_stop.sh — Stop hook 의 텔레그램 자동 송신 sketch
# ------------------------------------------------------------------------------
# 본 스크립트 = 사용자 directive 2026-05-17 사전 경고 의 enforcement layer.
# 가드레일 [[feedback-telegram-report-script-trigger-warning]] 정합.
#
# 트리거: .claude/settings.json 의 hooks.Stop 의 활성 시점 (사용자 GO 의 의무).
#
# 입력: stdin JSON = Claude Code 의 Stop hook payload
#   - session_id
#   - transcript_path = 의 의 JSONL 본문 경로
#   - cwd = 작업 디렉토리
#
# 동작:
#   1. transcript 의 last assistant message content 추출
#   2. 5줄 caveman ultra 의 추출 (앞 500자)
#   3. .env.telegram 의 TELEGRAM_BOT_TOKEN + CHAT_ID 의 load
#   4. curl 의 sendMessage API 호출
#   5. 송신 실패 시 = exit 0 (silent — Claude Code 의 응답 차단 회피)
#
# 종료 코드: 항상 0 (Stop hook 의 의 응답 차단 의 회피 의무)
# ==============================================================================

set -uo pipefail

# stdin 의 의 JSON 의 input
INPUT=$(cat)

# transcript path 의 추출 (python json parse)
TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('transcript_path', ''))
except Exception:
    print('')
" 2>/dev/null)

# transcript 부재 = silent skip
if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    exit 0
fi

# transcript 의 last assistant message 의 content 추출
SUMMARY=$(python3 -c "
import sys, json
try:
    with open('$TRANSCRIPT_PATH', 'r') as f:
        last = None
        for line in f:
            try:
                d = json.loads(line)
                if d.get('type') == 'assistant':
                    last = d
            except Exception:
                pass
        if last:
            content = last.get('message', {}).get('content', [])
            if isinstance(content, list):
                texts = [c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') == 'text']
                print('\n'.join(texts)[:500])
            else:
                print(str(content)[:500])
except Exception:
    pass
" 2>/dev/null)

# 송신 본문 부재 = silent skip
if [ -z "$SUMMARY" ]; then
    exit 0
fi

# .env.telegram 의 자격 로딩
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$REPO_ROOT/.env.telegram" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO_ROOT/.env.telegram"
    set +a
fi

# token 부재 = silent skip
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
    exit 0
fi

# curl 의 sendMessage 호출 (실패 = silent)
curl -s --max-time 10 "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=[Auto-Stop] ${SUMMARY}" > /dev/null 2>&1 || true

exit 0
