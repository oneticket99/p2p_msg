#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# 한글 주석 — M6 post-commit WBS hook 설치 (cycle 169.787 신설, Codex P0 회수).
# .git/hooks/post-commit 가 tools/wbs_post_commit.py 를 호출하도록 결선한다.
# .git/hooks 는 version-control 밖이므로 본 스크립트(version-controlled)로 재현 가능하게 한다.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_PATH="$REPO_ROOT/.git/hooks/post-commit"

# 한글 주석 — 기존 post-commit 이 있으면 보존 안내 후 덮어쓰기 차단
if [ -f "$HOOK_PATH" ] && ! grep -q "wbs_post_commit.py" "$HOOK_PATH" 2>/dev/null; then
  echo "[install-wbs-hook] 기존 post-commit hook 존재 (wbs 아님) — 수동 병합 필요. 중단." >&2
  exit 1
fi

cat > "$HOOK_PATH" <<'HOOK'
#!/usr/bin/env bash
# 한글 주석 — M6 자동 WBS row 등록 (tools/install_wbs_hook.sh 가 생성). commit 차단 금지.
REPO_ROOT="$(git rev-parse --show-toplevel)"
python3 "$REPO_ROOT/tools/wbs_post_commit.py" || true
HOOK

chmod +x "$HOOK_PATH"
echo "[install-wbs-hook] 설치 완료 — $HOOK_PATH"
