#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk(p2p_msg) Stop hook — 평가 문서 staleness 검출 + 차단.
#
# [[feedback-assessment-freshness-trigger]] 정합.
# productization.md + vibe-coding.md 의 commit 차이 5+ = stale 판정 → exit 2 BLOCK.
# 사용자 directive 2026-05-17 — code 작업 + git 반영 후 평가 문서 갱신 의무.

set -e

ROOT="${CLAUDE_PROJECT_DIR:-/Users/oneticket_toonation/Documents/vscode_work/p2p_msg}"
cd "$ROOT" || exit 0

# 마지막 productization 갱신 commit
LAST_PROD=$(git log -1 --pretty=format:%h -- docs/assessments/productization.md 2>/dev/null)
LAST_VIBE=$(git log -1 --pretty=format:%h -- docs/assessments/vibe-coding.md 2>/dev/null)
HEAD_SHA=$(git rev-parse --short HEAD 2>/dev/null)

[[ -z "$LAST_PROD" || -z "$LAST_VIBE" || -z "$HEAD_SHA" ]] && exit 0

# productization 갱신 후 누적 commit 수
COMMITS_SINCE_PROD=$(git rev-list --count "${LAST_PROD}..HEAD" 2>/dev/null || echo 0)
COMMITS_SINCE_VIBE=$(git rev-list --count "${LAST_VIBE}..HEAD" 2>/dev/null || echo 0)

# 5+ commit 누적 = stale
STALE_THRESHOLD=5

if [[ $COMMITS_SINCE_PROD -ge $STALE_THRESHOLD || $COMMITS_SINCE_VIBE -ge $STALE_THRESHOLD ]]; then
  cat >&2 <<EOF
🔴 평가 문서 staleness 검출 — 직무유기 차단 ([[feedback-assessment-freshness-trigger]])

- productization.md 마지막 갱신: $LAST_PROD (이후 $COMMITS_SINCE_PROD commit)
- vibe-coding.md 마지막 갱신: $LAST_VIBE (이후 $COMMITS_SINCE_VIBE commit)
- 임계: $STALE_THRESHOLD commit 누적 시 stale 판정
- 현재 HEAD: $HEAD_SHA

조치:
1. docs/assessments/productization.md + vibe-coding.md 의무 갱신 (사이클 row + 종합 점수)
2. HTML mirror (docs/html/) 동시 rewrite (CLAUDE §10-6)
3. handoff §8 신규 row 추가
4. commit + push

가드레일 정합: [[feedback-code-qa-review-gate-mandatory]] + [[feedback-no-autonomy-dereliction-prevention]].
EOF
  exit 2
fi

exit 0
