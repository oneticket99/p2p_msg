#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Stop hook 8 번째 entry — dereliction-detector-agent 자동 trigger (cycle 168.3 신설).
# 사용자 directive 2026-05-20 — "각 작업이 마무리 될때마다 직무유기 분석 에이전트는 ... 체크하면서 지시해".
#
# 본 hook = 매 작업 commit 직후 fire — 7 영역 자동 detect + WARN report.
# 회수 chain 본격 = main session 안 dereliction-detector-agent spawn 의무.

set +u  # 한글 주석 — CLAUDE_PROJECT_DIR 부재 graceful path (terminal 직접 fire)
CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$CLAUDE_PROJECT_DIR" || exit 0

# 한글 주석 — 최근 N commit 범위 (default 5)
N_RECENT="${DERELICTION_RECENT_COMMITS:-5}"
HEAD_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

VIOLATIONS=()
WARN_COUNT=0

# 1. M2 README.md 변경 이력 prepend 검증
README_EDITS=$(git log --oneline -n "$N_RECENT" -- README.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$README_EDITS" -eq 0 ]; then
  VIOLATIONS+=("[M2 README] 최근 $N_RECENT commit 안 README.md prepend 부재")
  WARN_COUNT=$((WARN_COUNT + 1))
fi

# 2. M3 History.md 역순 prepend 검증
HISTORY_EDITS=$(git log --oneline -n "$N_RECENT" -- History.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$HISTORY_EDITS" -eq 0 ]; then
  VIOLATIONS+=("[M3 History] 최근 $N_RECENT commit 안 History.md prepend 부재")
  WARN_COUNT=$((WARN_COUNT + 1))
fi

# 3. M7 텔레그램 송신 hook fire 검증 (graceful 부재 시 skip)
TG_LOG="${CLAUDE_PROJECT_DIR}/.claude/hook_telegram_log.txt"
if [ -f "$TG_LOG" ]; then
  TG_RECENT=$(tail -n 50 "$TG_LOG" 2>/dev/null | grep -c "$HEAD_SHA" || true)
  if [ "$TG_RECENT" -eq 0 ]; then
    VIOLATIONS+=("[M7 telegram] 현 HEAD $HEAD_SHA 의 텔레그램 송신 history 부재")
    WARN_COUNT=$((WARN_COUNT + 1))
  fi
fi

# 4. 사용자 manual test trigger 부재 detect (handoff 안 "사용자 test 진입" 키워드 후 N cycle 추가)
HANDOFF="${CLAUDE_PROJECT_DIR}/docs/exec-plans/active/2026-05-17-session-handoff.md"
if [ -f "$HANDOFF" ]; then
  TEST_TRIGGER_LINE=$(grep -n "사용자 manual test\|test 진입 시점" "$HANDOFF" 2>/dev/null | head -1 | cut -d: -f1 || echo 0)
  if [ "${TEST_TRIGGER_LINE:-0}" -gt 0 ]; then
    # 한글 주석 — 평가 manifest 안 test trigger 명시 — 추가 cycle 진행 detect (heuristic)
    RECENT_FEAT_COMMITS=$(git log --oneline -n "$N_RECENT" --grep="feat(cycle1" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$RECENT_FEAT_COMMITS" -ge 3 ]; then
      VIOLATIONS+=("[manual test trigger] test 진입 시점 명시 후 $RECENT_FEAT_COMMITS feat cycle 추가 진행 — 사용자 ack 부재 blind work 가능성")
      WARN_COUNT=$((WARN_COUNT + 1))
    fi
  fi
fi

# report 출력 — cycle 169.212 — stderr redirect (claude session Stop hook stderr capture 정합)
if [ "$WARN_COUNT" -gt 0 ]; then
  {
    echo "🔴 dereliction-detector 자동 check BLOCK — ${WARN_COUNT}건 detect (HEAD=$HEAD_SHA)"
    echo ""
    for v in "${VIOLATIONS[@]}"; do
      echo "  - $v"
    done
    echo ""
    echo "회수 chain ([[feedback-no-autonomy-dereliction-prevention]] + [[feedback-dereliction-auto-spawn-mandatory]] 정합):"
    echo "  1. main session 안 dereliction-detector-agent 즉시 spawn (run_in_background=true)"
    echo "  2. background 결과 wait + 회수 chain dispatch"
    echo "  3. 사용자 ack 의무 항목 분리 + verbatim trigger"
    echo ""
    echo "사용자 directive 2026-05-21 — 매 작업 완료 보고마다 dereliction-detector spawn 의무."
    echo "cycle 168.3 + cycle 169.189 + cycle 169.212 강화."
  } 1>&2
  # cycle 169.189 — exit 2 block 강화 (사용자 directive — Stop hook 의 main session 의 spawn 강제)
  exit 2
fi

exit 0
