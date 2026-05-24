#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Stop hook — push 완료 직후 self-hosted CI 활성 검증 + 미실행 시 사용자 안내.
# 사용자 directive 2026-05-19 cycle 131 — "파일 쓰기와 검수작업이 완료되면 반드시 self-hosted ci 돌리도록 훅 등록해".
#
# 동작:
# 1. 로컬 HEAD = remote main 정합 → 최근 CI run status 검증 (gh API read-only).
# 2. 최근 5 run 의 모든 fail → 🔴 alert (사용자 즉시 회수 의무).
# 3. 최근 5 run 의 1건 이상 success → ✅ OK.
# 4. CI run 부재 또는 stale → ⚠️ warning (push 부재 가능).
#
# 본 hook = read-only 진단 만 (CI workflow trigger 부재 — push 시 GitHub 자동 fire 정합).
# exit 0 = silent PASS, exit 0 + stdout msg = warning (Stop hook block 부재).

set -uo pipefail

# 한글 주석: gh CLI + main branch 정합 의무
if ! command -v gh &>/dev/null ; then
  echo "[ci-hook] gh CLI 부재 — self-hosted CI 검증 skip"
  exit 0
fi

# 한글 주석: 로컬 git repo 정합 검증
cd "${CLAUDE_PROJECT_DIR:-$(pwd)}" || exit 0
if ! git rev-parse --git-dir &>/dev/null ; then
  exit 0
fi

# 한글 주석: 로컬 HEAD vs remote main 정합 검증 — push 부재 시 안내
LOCAL=$(git rev-parse HEAD 2>/dev/null || echo "")
REMOTE=$(git ls-remote origin main 2>/dev/null | awk '{print $1}')
if [ -z "$LOCAL" ] || [ -z "$REMOTE" ] ; then
  exit 0
fi
if [ "$LOCAL" != "$REMOTE" ] ; then
  echo "[ci-hook] 🟡 로컬 HEAD ≠ remote main — feature branch push + PR merge 후 CI 검증 의무"
  exit 0
fi

# 한글 주석: 최근 5 CI run status 검증 (gh API read-only)
runs_json=$(gh run list --limit 5 --json status,conclusion,workflowName,createdAt 2>/dev/null || echo "[]")
if [ "$runs_json" = "[]" ] || [ -z "$runs_json" ] ; then
  echo "[ci-hook] ⚠️ recent CI run 부재 — gh 인증 또는 workflow 등록 검증 의무"
  exit 0
fi

# 한글 주석: failure 누계 검증 — 5건 모두 fail = self-hosted runner 또는 코드 회귀
failures=$(echo "$runs_json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
fails = [r for r in data if r.get('conclusion') == 'failure']
print(len(fails))
" 2>/dev/null || echo "0")

total=$(echo "$runs_json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(len(data))
" 2>/dev/null || echo "0")

# 한글 주석: 활성 CI runner online 검증 — self-hosted runner status=online 필수
runners_json=$(gh api /repos/oneticket99/p2p_msg/actions/runners 2>/dev/null || echo "{}")
online_count=$(echo "$runners_json" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    runners = data.get('runners', [])
    online = [r for r in runners if r.get('status') == 'online']
    print(len(online))
except Exception:
    print(0)
" 2>/dev/null || echo "0")

# 한글 주석: 결과 보고 분기
if [ "$online_count" -eq 0 ] ; then
  echo "[ci-hook] 🔴 self-hosted runner 의 online 0 — actions-runner-tootalk launchd 활성 검증 의무"
  exit 0
fi

if [ "$failures" -ge 5 ] ; then
  echo "[ci-hook] 🔴 최근 5 CI run 모두 failure — 즉시 회수 의무 (\`gh run view <id> --log-failed\`)"
  exit 0
fi

# 한글 주석: PASS 정합 — silent (Stop hook output 최소화)
echo "[ci-hook] ✅ self-hosted runner online=${online_count} + 최근 ${total} run 중 ${failures} fail"
exit 0
