#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# TooTalk(p2p_msg) PostToolUse Edit/Write/MultiEdit 검수 hook.
#
# 가드레일 [[feedback-post-write-inspection-mandatory]] 정합.
# 5 검사 — syntax + AST + BPE + pronoun + markdownlint.
#
# stdin = Claude Code PostToolUse JSON.
# exit 0 = PASS, exit 2 = BLOCK (변경 reject).

set -e

INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_name",""))' 2>/dev/null || echo "")
FILE=$(echo "$INPUT" | python3 -c 'import json,sys; t=json.load(sys.stdin).get("tool_input",{}); print(t.get("file_path") or t.get("path") or "")' 2>/dev/null || echo "")

case "$TOOL" in
  Edit|Write|MultiEdit|NotebookEdit) ;;
  *) exit 0 ;;
esac

[[ -z "$FILE" || ! -f "$FILE" ]] && exit 0

case "$FILE" in
  /Users/oneticket_toonation/Documents/vscode_work/p2p_msg/*) ;;
  *) exit 0 ;;
esac

# hook 자체 + lint 도구 = skip (regex pattern literal 자기 match 회피)
case "$FILE" in
  */tools/hook_*.sh|*/tools/doc-lint.sh) exit 0 ;;
esac

FAIL=0
MSG=""
ERR=/tmp/_hook_post_$$

# 1. syntax + AST (.py)
case "$FILE" in
  *.py)
    if ! python3 -m py_compile "$FILE" 2>"$ERR"; then
      FAIL=1; MSG+=$'\n[syntax] py_compile FAIL: '"$(cat "$ERR")"
    fi
    if ! python3 -c "import ast; ast.parse(open('$FILE',encoding='utf-8').read())" 2>"$ERR"; then
      FAIL=1; MSG+=$'\n[AST] ast.parse FAIL: '"$(cat "$ERR")"
    fi
    ;;
  *.json)
    if ! python3 -m json.tool "$FILE" >/dev/null 2>"$ERR"; then
      FAIL=1; MSG+=$'\n[syntax] json FAIL: '"$(cat "$ERR")"
    fi
    ;;
esac

# 2. BPE — U+CE21 단독 + "의 의 의" 3회 연속
CHUK=$(printf '\xec\xb8\xa1')
if grep -nE "(^|[^가-힣])${CHUK}([^가-힣]|$)" "$FILE" 2>/dev/null | head -3 > "$ERR"; then
  if [[ -s "$ERR" ]]; then
    FAIL=1; MSG+=$'\n[BPE] U+CE21 단독: '"$(cat "$ERR")"
  fi
fi
if grep -nE "의 의 의" "$FILE" 2>/dev/null | head -3 > "$ERR"; then
  if [[ -s "$ERR" ]]; then
    FAIL=1; MSG+=$'\n[BPE] "의" 3회 반복: '"$(cat "$ERR")"
  fi
fi

# 3. pronoun
if grep -nE "(본인|타인)" "$FILE" 2>/dev/null | head -3 > "$ERR"; then
  if [[ -s "$ERR" ]]; then
    FAIL=1; MSG+=$'\n[pronoun] 본인/타인: '"$(cat "$ERR")"
  fi
fi

# 4. markdownlint (.md)
case "$FILE" in
  *.md)
    if command -v npx >/dev/null 2>&1; then
      if ! npx --no-install markdownlint-cli2 "$FILE" >"$ERR" 2>&1; then
        if grep -qE "[1-9][0-9]* error" "$ERR"; then
          FAIL=1; MSG+=$'\n[markdownlint] '"$(tail -3 "$ERR")"
        fi
      fi
    fi
    ;;
esac

rm -f "$ERR"

if [[ $FAIL -eq 1 ]]; then
  printf "🔴 PostToolUse 검수 FAIL — %s\n%s\n" "$FILE" "$MSG" >&2
  exit 2
fi
exit 0
