#!/usr/bin/env bash
# ==============================================================================
# hook_check_bpe_token_input.sh — PreToolUse Edit/Write hook 의 BPE/대명사 차단
# ------------------------------------------------------------------------------
# 본 스크립트 = 사용자 directive 2026-05-17 4회차 사전 경고 의 enforcement layer.
# 정본 §S-1 의 L0 PreToolUse Edit/Write hook 의 `check_korean_token_input.sh`
# 의 본 저장소 의 실 적용 sketch.
#
# 트리거: .claude/settings.json 의 hooks.PreToolUse.Edit/Write 의 활성 시점
# (사용자 GO 의 직접 활성 의무).
#
# 검사 대상:
#   1. BPE 손상 U+CE21 단독 의존명사 (가드레일 feedback-no-korean-chuck-token)
#   2. 1인칭 / 3인칭 대명사 본인 / 타인 (가드레일 feedback-no-self-other-pronoun)
#
# 입력: stdin 또는 $1 인자 = Edit/Write 의 input 본문
# 종료 코드:
#   0 = 통과 (입력 본문 의 정합)
#   1 = 위반 차단 (Edit/Write 의 자동 거부)
#
# 사용자 directive 2026-05-17 정합:
#   "만약 BPE 토큰 손상이 다음번에 발견되면 스크립트 트리거 구조로
#    강제 검열 진행하는 방식으로 바꿀꺼야"
# ==============================================================================

set -uo pipefail

# 입력 source — stdin 우선 + $1 fallback
if [ ! -t 0 ]; then
    INPUT=$(cat)
else
    INPUT="${1:-}"
fi

# 입력 비어 있음 = 통과
if [ -z "$INPUT" ]; then
    exit 0
fi

# 본 hook 자체 의 본문 의 grep 의 자기 참조 회피 — script 자체 의 quote 영역 의 의무
# (settings.json 의 hook 호출 시점 의 input 만 검사 대상)

ERRORS=0

# 검사 1: BPE U+CE21 단독 의존명사 (합성어 측면/측정/관측/추측/좌측/우측 의 제외)
HITS_BPE=$(echo "$INPUT" | grep -nE '(^|[^가-힣])측($|[^가-힣면관추좌우정])' || true)
if [ -n "$HITS_BPE" ]; then
    echo "==============================================================" >&2
    echo "[BPE HOOK] BPE 손상 U+CE21 단독 의존명사 차단 — Edit/Write 거부" >&2
    echo "위반 위치:" >&2
    echo "$HITS_BPE" | sed 's/^/        /' >&2
    echo "정합: feedback-no-korean-chuck-token (4회차 강화 영구화)" >&2
    echo "대체: 자연 조사 (의/가/은/는) + 화살표 (→) + 공백 + 콤마" >&2
    echo "==============================================================" >&2
    ERRORS=$((ERRORS+1))
fi

# 검사 2: 1인칭 / 3인칭 대명사 본인 / 타인
HITS_PRONOUN=$(echo "$INPUT" | grep -nE '(^|[^가-힣])(본인|타인)([^가-힣]|$)' || true)
if [ -n "$HITS_PRONOUN" ]; then
    echo "==============================================================" >&2
    echo "[PRONOUN HOOK] 1인칭/3인칭 대명사 차단 — Edit/Write 거부" >&2
    echo "위반 위치:" >&2
    echo "$HITS_PRONOUN" | sed 's/^/        /' >&2
    echo "정합: feedback-no-self-other-pronoun (3회차 강화 영구화)" >&2
    echo "대체: 주어 생략 + 명사 직접 + 자체 + 사용자 + 요청자" >&2
    echo "==============================================================" >&2
    ERRORS=$((ERRORS+1))
fi

# 최종 결과
if [ "$ERRORS" -gt 0 ]; then
    echo "[BPE HOOK] 총 $ERRORS 영역 위반 — 정정 후 재시도 의무" >&2
    exit 1
fi

# 통과 시 stderr 의 명시 없음 (Edit/Write 의 정상 진행)
exit 0
