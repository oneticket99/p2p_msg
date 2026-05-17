#!/usr/bin/env bash
# ==============================================================================
# doc-lint.sh — TooTalk 문서 lint (정본 §L docs-lint.yml 로컬 등가)
# ------------------------------------------------------------------------------
# 검증 항목 (5종):
#   1. BPE 위생 — 한국어 의존명사 U+CE21 단독 사용 금지
#   2. 깨진 상대 markdown 링크
#   3. docs/** frontmatter 필수 필드 (title · owner · last_verified · status)
#   4. 연속 빈 줄 (3 줄 이상 연속 공백 줄 차단)
#   5. 1인칭/3인칭 대명사 — 1인칭 + 3인칭 대명사 단독 사용 금지
#                          (사용자 가드레일 feedback-no-self-other-pronoun 정합)
#
# 사용:
#   bash tools/doc-lint.sh          # 전체 저장소 검사
#   bash tools/doc-lint.sh <file>   # 단일 파일 검사
#
# 종료 코드:
#   0 = 통과
#   1 = 위반 발견 (commit 차단)
#
# 사용자 directive 2026-05-17: lint 가드레일 — 파일 수정 후 본 스크립트 통과 시
#                              git push 진행. 한 단계 실패 시 push 차단 + 정정.
#
# 호환성: macOS 기본 bash 3.2 호환 (mapfile 미사용 — while read fallback)
# ==============================================================================

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-}"

# ANSI 색상 (가독성)
RED='\033[0;31m'
YEL='\033[0;33m'
GRN='\033[0;32m'
NC='\033[0m'

ERRORS=0

err()  { echo -e "${RED}[ERR]${NC}  $1" >&2; ERRORS=$((ERRORS+1)); }
warn() { echo -e "${YEL}[WARN]${NC} $1" >&2; }
ok()   { echo -e "${GRN}[OK]${NC}   $1"; }

# ── 검사 대상 파일 수집 (bash 3.2 호환 — mapfile 미사용) ────────────────────
FILES=()
if [ -n "$TARGET" ]; then
    if [ ! -f "$REPO_ROOT/$TARGET" ] && [ ! -f "$TARGET" ]; then
        err "대상 파일 미존재: $TARGET"
        exit 1
    fi
    if [ -f "$REPO_ROOT/$TARGET" ]; then
        FILES+=("$REPO_ROOT/$TARGET")
    else
        FILES+=("$TARGET")
    fi
else
    # 저장소 전체 .md 파일 — node_modules / .venv / dist 제외
    # bash 3.2 호환 — mapfile 대신 while read 사용
    while IFS= read -r line; do
        FILES+=("$line")
    done < <(find "$REPO_ROOT" \
        -type f -name "*.md" \
        ! -path "*/node_modules/*" \
        ! -path "*/.venv/*" \
        ! -path "*/dist/*" \
        ! -path "*/build/*" \
        ! -path "*/.git/*")
    # 본 스크립트 자체는 lint 대상 외 (BPE 검사 메타 인용 자체 검출 회피)
    # 단 .md 만 검사 대상이므로 .sh 인 본 스크립트는 자동 제외됨 — self-exclude 라인 명시
fi

echo "──────────────────────────────────────────────────────────────"
echo " doc-lint.sh — 검사 대상 ${#FILES[@]} 개 .md 파일"
echo "──────────────────────────────────────────────────────────────"

# ── 검사 1: BPE 위생 — 한국어 의존명사 U+CE21 단독 사용 ───────────────────────
echo ""
echo "[1/5] BPE 위생 검사 (한국어 의존명사 U+CE21 단독 사용 금지)"
for f in "${FILES[@]}"; do
    # 단독 의존명사 매치 — 합성어 (측면 / 관측 / 측정 / 좌측 / 우측 / 추측) 제외
    HITS=$(grep -nE "(^|[^가-힣])측($|[^가-힣면관추좌우정])" "$f" 2>/dev/null || true)
    if [ -n "$HITS" ]; then
        err "BPE 위생 위반 ($f):"
        echo "$HITS" | sed 's/^/        /' >&2
    fi
done

# ── 검사 2: 깨진 상대 링크 ───────────────────────────────────────────────────
echo ""
echo "[2/5] 깨진 상대 markdown 링크 검사"
for f in "${FILES[@]}"; do
    BASE_DIR=$(dirname "$f")
    # `[text](relative/path.md)` 또는 `[text](relative/path)` 패턴 추출
    # 절대 URL (http://, https://, mailto:) 제외
    LINKS=$(grep -oE '\]\(([^)]+)\)' "$f" 2>/dev/null \
        | sed -E 's/^\]\(//;s/\)$//' \
        | grep -vE '^(https?://|mailto:|#)' \
        | grep -vE '^[a-z]+:' \
        | awk -F'#' '{print $1}' \
        || true)

    while IFS= read -r LINK; do
        [ -z "$LINK" ] && continue
        # 빈 fragment-only 제외
        [ "$LINK" = "" ] && continue
        # 절대 경로 → REPO_ROOT 기준
        if [[ "$LINK" = /* ]]; then
            TARGET_PATH="$REPO_ROOT$LINK"
        else
            TARGET_PATH="$BASE_DIR/$LINK"
        fi
        if [ ! -e "$TARGET_PATH" ]; then
            err "깨진 링크 ($f → $LINK): 대상 미존재 $TARGET_PATH"
        fi
    done <<< "$LINKS"
done

# ── 검사 3: docs/** frontmatter 필수 필드 ────────────────────────────────────
echo ""
echo "[3/5] docs/** frontmatter 필수 필드 검사 (title · owner · last_verified · status)"
for f in "${FILES[@]}"; do
    # docs/ 하위 파일만 대상
    if [[ "$f" != *"/docs/"* ]]; then
        continue
    fi
    # README.md 는 frontmatter 면제 — 표준 디렉토리 안내 문서
    if [[ "$(basename "$f")" = "README.md" ]]; then
        continue
    fi

    # 첫 4 줄에 YAML frontmatter 시작 `---` 확인
    HEAD=$(head -n 1 "$f")
    if [ "$HEAD" != "---" ]; then
        err "frontmatter 미존재 ($f): 첫 줄 '---' 필요"
        continue
    fi

    # 필수 필드 검사
    for FIELD in "title" "owner" "last_verified" "status"; do
        if ! grep -qE "^${FIELD}[[:space:]]*:" "$f" 2>/dev/null; then
            err "frontmatter 필수 필드 누락 ($f): $FIELD"
        fi
    done
done

# ── 검사 4: 연속 빈 줄 (3 줄 이상) ───────────────────────────────────────────
echo ""
echo "[4/5] 연속 빈 줄 검사 (3 줄 이상 공백 줄 차단)"
for f in "${FILES[@]}"; do
    # awk 로 연속 빈 줄 카운트 — 3 이상 발견 시 출력
    HITS=$(awk '
        /^[[:space:]]*$/ { count++; if (count >= 3) { print NR ": " count " consecutive blank lines"; exit_code=1; count=0 } next }
        { count=0 }
        END { exit (exit_code ? 1 : 0) }
    ' "$f" 2>/dev/null || true)
    if [ -n "$HITS" ]; then
        err "연속 빈 줄 ($f): $HITS"
    fi
done

# ── 검사 5: 1인칭/3인칭 대명사 사용 금지 (사용자 가드레일 2026-05-17) ────────
echo ""
echo "[5/5] 1인칭/3인칭 대명사 사용 검사"
for f in "${FILES[@]}"; do
    # 단독 의존명사 매치 — 한글 음절 앞뒤 없는 경우만 (예: "X 본인 Y", "본인 발신" 등)
    # 사용자 발언 인용은 자체 마스킹 의무 (인용 영역 그대로 보존 = 위반)
    HITS=$(grep -nE "(^|[^가-힣])(본인|타인)([^가-힣]|$)" "$f" 2>/dev/null || true)
    if [ -n "$HITS" ]; then
        err "1인칭/3인칭 대명사 위반 ($f):"
        echo "$HITS" | sed 's/^/        /' >&2
    fi
done

# ── 최종 결과 ────────────────────────────────────────────────────────────────
echo ""
echo "──────────────────────────────────────────────────────────────"
if [ "$ERRORS" -eq 0 ]; then
    ok "doc-lint 통과 (검사 대상 ${#FILES[@]} 파일, 위반 0건)"
    exit 0
else
    err "doc-lint 실패 — 총 $ERRORS 건 위반"
    err "정정 후 다시 실행 필요. push 차단."
    exit 1
fi
