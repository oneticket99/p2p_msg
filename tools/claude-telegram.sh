#!/usr/bin/env bash
# ==============================================================================
# claude-telegram.sh — TooTalk 개발용 Claude CLI 실행 wrapper
# ------------------------------------------------------------------------------
# 목적: Claude CLI 를 Telegram plugin 강제 로드 상태로 실행
#       양방향 송수신 (reply, react, edit_message, download_attachment) 활성
#
# 사용:
#   ./tools/claude-telegram.sh             # 기본 실행
#   ./tools/claude-telegram.sh --resume    # 직전 세션 이어 받기
#   ./tools/claude-telegram.sh --bare      # 최소 환경 (plugin 로드는 강제 유지)
#
# 전제:
#   - Bun 설치 (bun.sh)
#   - Telegram plugin 설치: ~/.claude/plugins/cache/claude-plugins-official/telegram/0.0.6/
#   - Bot token 설정: /telegram:configure <token> 사전 실행 권장
#
# 사용자 directive (2026-05-17): "claude cli 의 텔레그램 양방향 송수신이 가능한
#                                  옵션을 붙여서 간단하게 실행 할 수 있도록"
# ==============================================================================

set -euo pipefail

# ── 경로 상수 (하드코딩 금지 원칙 예외: 시스템 경로) ──────────────────────────
PROJECT_DIR="/Users/oneticket_toonation/Documents/vscode_work/p2p_msg"
CLAUDE_CHANNELS_DIR="$HOME/.claude/channels/telegram"
TELEGRAM_PLUGIN_DIR="$HOME/.claude/plugins/cache/claude-plugins-official/telegram/0.0.6"
TELEGRAM_ENV="$CLAUDE_CHANNELS_DIR/.env"
TELEGRAM_ACCESS="$CLAUDE_CHANNELS_DIR/access.json"
BOT_PID_FILE="$CLAUDE_CHANNELS_DIR/bot.pid"

# ── 색상 출력 (가독성용 ANSI) ─────────────────────────────────────────────────
RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[0;33m'
CYA='\033[0;36m'
NC='\033[0m'

err()  { echo -e "${RED}[ERR]${NC}  $1" >&2; }
ok()   { echo -e "${GRN}[OK]${NC}   $1"; }
warn() { echo -e "${YEL}[WARN]${NC} $1"; }
info() { echo -e "${CYA}[INFO]${NC} $1"; }

# ── 1. 사전 환경 검증 ────────────────────────────────────────────────────────
info "사전 환경 검증 시작"

command -v bun >/dev/null 2>&1 || { err "Bun 미설치 — https://bun.sh/install 안내 참조"; exit 1; }
command -v claude >/dev/null 2>&1 || { err "Claude CLI 미설치 — npm i -g @anthropic-ai/claude-code"; exit 1; }
[ -d "$TELEGRAM_PLUGIN_DIR" ] || { err "Telegram plugin 미설치 — Claude CLI 내부에서 /plugin install telegram@claude-plugins-official 실행 필요"; exit 1; }

ok "bun + claude + plugin 디렉토리 모두 존재"

# ── 2. 토큰 검증 ──────────────────────────────────────────────────────────────
if [ ! -f "$TELEGRAM_ENV" ] || ! grep -q "^TELEGRAM_BOT_TOKEN=" "$TELEGRAM_ENV" 2>/dev/null; then
    warn "Telegram bot token 미설정 — Claude CLI 세션 내 /telegram:configure <token> 으로 등록 필요"
    warn "BotFather 에서 발급받은 토큰 형식: 123456789:AAHfiqksKZ8..."
else
    TOKEN_MASKED=$(grep "^TELEGRAM_BOT_TOKEN=" "$TELEGRAM_ENV" | cut -d= -f2 | head -c 12)
    ok "토큰 설정 확인: ${TOKEN_MASKED}..."
fi

# ── 3. access.json 검증 ──────────────────────────────────────────────────────
if [ -f "$TELEGRAM_ACCESS" ]; then
    POLICY=$(grep -o '"dmPolicy"[[:space:]]*:[[:space:]]*"[^"]*"' "$TELEGRAM_ACCESS" 2>/dev/null | sed 's/.*"\([^"]*\)"$/\1/' || echo "unknown")
    ALLOW_COUNT=$(grep -o '"allowFrom"[[:space:]]*:[[:space:]]*\[[^]]*\]' "$TELEGRAM_ACCESS" 2>/dev/null | grep -oE '"[0-9]+"' | wc -l | tr -d ' ' || echo "0")
    ok "access.json: dmPolicy=${POLICY}, allowFrom=${ALLOW_COUNT} 명"

    if [ "$POLICY" != "allowlist" ]; then
        warn "권장 정책 allowlist 아님 — /telegram:access policy allowlist 로 lockdown 권장"
    fi
else
    warn "access.json 미존재 — 첫 DM 시 pairing 모드 동작"
fi

# ── 4. Bot 프로세스 상태 점검 (stale PID 정리) ────────────────────────────────
if [ -f "$BOT_PID_FILE" ]; then
    BOT_PID=$(cat "$BOT_PID_FILE" 2>/dev/null || echo "")
    if [ -n "$BOT_PID" ] && ps -p "$BOT_PID" > /dev/null 2>&1; then
        ok "Telegram bot 프로세스 running (PID $BOT_PID)"
    else
        warn "Stale PID 파일 정리"
        rm -f "$BOT_PID_FILE"
    fi
fi

# ── 5. Claude CLI 실행 ───────────────────────────────────────────────────────
cd "$PROJECT_DIR"
ok "TooTalk 프로젝트 디렉토리 진입: $PROJECT_DIR"
info "Claude CLI 시작 — Telegram plugin 강제 로드 (--plugin-dir)"
echo "──────────────────────────────────────────────────────────────"

# 양방향 송수신 활성 핵심 옵션:
#   --plugin-dir : telegram plugin 명시 로드 (자동 검색 실패 회피)
#   "$@"         : 사용자가 추가로 넘긴 인자 (--resume, --continue, --bare 등) 전달
exec claude --plugin-dir "$TELEGRAM_PLUGIN_DIR" "$@"
