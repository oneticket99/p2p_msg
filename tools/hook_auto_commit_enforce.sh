#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# 한글 주석 — auto commit+PR 경로 강제 Stop hook (cycle 169.739 정식 연결).
# 사용자 directive — "각 작업 끝나면 무조건 훅 돌리게끔 강제 트리거".
# feedback_auto_commit_push_deploy.md 4회차 강화 정합 — uncommitted code/test file detect 시 block exit 2.
#
# 차단 대상 = tests/ + app/ + server/ 안 uncommitted (staged or unstaged or untracked) 변경.
# 문서 (docs/ + *.md) 단독 변경은 평가 staleness hook 의 영역 — 본 hook 제외.

set -euo pipefail

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}" || exit 0

# 한글 주석 — code/test prefix 의 uncommitted entry 검출 (untracked + modified + staged)
DIRTY=$(git status --porcelain 2>/dev/null | grep -E '^.{2} (tests/|app/|server/)' || true)

if [ -n "$DIRTY" ]; then
  COUNT=$(printf '%s\n' "$DIRTY" | wc -l | tr -d ' ')
  echo "🔴 auto commit 직무유기 차단 — code/test uncommitted ${COUNT}건 detect (feedback_auto_commit_push_deploy 강제)" >&2
  echo "" >&2
  printf '%s\n' "$DIRTY" | head -20 >&2
  echo "" >&2
  echo "조치 의무 (같은 turn 안 완결):" >&2
  echo "  1. git add -A" >&2
  echo "  2. git commit -m '<type>(cycle169.N): <scope>'  (co-authored-by retain)" >&2
  echo "  3. git push origin HEAD:<feature-branch>" >&2
  echo "  4. gh pr create --base main --head <feature-branch> --fill" >&2
  echo "" >&2
  echo "별 turn 미루기 금지 — batch 단위 = 작성→verify→commit→branch push→PR 한 turn 완결." >&2
  exit 2
fi

exit 0
