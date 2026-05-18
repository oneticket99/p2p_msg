# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 bot LLM 사용 통계 추적 — 사이클 85.

memory `project_bot_framework.md` (사용자 directive) + bot-framework.md §10 의
"사용 통계 + 비용 추적" 의 별개 cycle 의 entry. Anthropic + OpenAI 의 usage
응답 의 통일 추출 + per-user + per-provider + per-period 집계.

본 module 범위
-------------
- ``UsageRecord`` frozen dataclass — user_id + provider + model + input_tokens
  + output_tokens + timestamp_ms
- ``UsageSummary`` frozen dataclass — count + input_tokens + output_tokens 합산
- ``UsageTracker`` class — record + summarize_by_user + summarize_by_provider +
  summarize_by_period (분 / 시 / 일)
- ``extract_anthropic_usage(body)`` helper — Messages API 응답 의 usage 필드
- ``extract_openai_usage(body)`` helper — Chat Completions 응답 의 usage 필드

본 cycle 의 범위 외 (별개 cycle):
- DB 영속화 (현 in-memory only — server restart 의 의 손실)
- 실 비용 계산 (model 별 $ per 1M token 의 의 price book)
- billing alert (한도 도달 시 의 notify)
- export (Prometheus / OpenTelemetry / Grafana)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Final, List, Optional, Tuple


@dataclass(frozen=True, slots=True)
class UsageRecord:
    """단일 LLM 호출 의 usage 의 entry.

    Attributes
    ----------
    user_id : int
        호출 사용자 (per-user 집계 의 key).
    provider : str
        "anthropic" / "openai" / "mock" 등.
    model : str
        모델 식별자 (예: "claude-3-5-sonnet-latest").
    input_tokens : int
        프롬프트 token 수 (음수 차단).
    output_tokens : int
        응답 token 수 (음수 차단).
    timestamp_ms : int
        호출 시점 UNIX epoch ms (음수 차단).
    """

    user_id: int
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    timestamp_ms: int

    def __post_init__(self) -> None:
        if self.user_id <= 0:
            raise ValueError(f"user_id 양수 의무 — {self.user_id}")
        if not self.provider:
            raise ValueError("provider 빈 문자열 불가")
        if not self.model:
            raise ValueError("model 빈 문자열 불가")
        if self.input_tokens < 0:
            raise ValueError(f"input_tokens 음수 차단 — {self.input_tokens}")
        if self.output_tokens < 0:
            raise ValueError(f"output_tokens 음수 차단 — {self.output_tokens}")
        if self.timestamp_ms < 0:
            raise ValueError(f"timestamp_ms 음수 차단 — {self.timestamp_ms}")

    @property
    def total_tokens(self) -> int:
        """입력 + 출력 token 합산."""

        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class UsageSummary:
    """집계 결과 — count + input + output + total tokens."""

    count: int
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# period bucket — 분 / 시 / 일 의 ms 환산
_MS_PER_MINUTE: Final[int] = 60_000
_MS_PER_HOUR: Final[int] = 60 * _MS_PER_MINUTE
_MS_PER_DAY: Final[int] = 24 * _MS_PER_HOUR

_PERIOD_BUCKET_MS: Final[Dict[str, int]] = {
    "minute": _MS_PER_MINUTE,
    "hour": _MS_PER_HOUR,
    "day": _MS_PER_DAY,
}


class UsageTracker:
    """in-memory usage record 의 누적 + 집계.

    Notes
    -----
    thread-safety 미보장 — async single event loop 의 가정. DB 영속화 부재 —
    server restart 시 의 손실 (별개 cycle 의 messages table 의 bot_id column 의
    의 영속 layer).
    """

    def __init__(self) -> None:
        self._records: List[UsageRecord] = []

    def record(self, entry: UsageRecord) -> None:
        """단일 호출 의 entry 추가."""

        self._records.append(entry)

    def size(self) -> int:
        """누적 record 수."""

        return len(self._records)

    def clear(self) -> None:
        """전수 reset."""

        self._records.clear()

    def all_records(self) -> List[UsageRecord]:
        """누적 record 의 copy 반환 (caller 의 mutation 차단)."""

        return list(self._records)

    def summarize_by_user(self) -> Dict[int, UsageSummary]:
        """user_id 별 집계 — {user_id: UsageSummary}."""

        per: Dict[int, Tuple[int, int, int]] = {}
        for r in self._records:
            count, inp, out = per.get(r.user_id, (0, 0, 0))
            per[r.user_id] = (count + 1, inp + r.input_tokens, out + r.output_tokens)
        return {
            uid: UsageSummary(count=c, input_tokens=i, output_tokens=o)
            for uid, (c, i, o) in per.items()
        }

    def summarize_by_provider(self) -> Dict[str, UsageSummary]:
        """provider 별 집계 — {provider: UsageSummary}."""

        per: Dict[str, Tuple[int, int, int]] = {}
        for r in self._records:
            count, inp, out = per.get(r.provider, (0, 0, 0))
            per[r.provider] = (count + 1, inp + r.input_tokens, out + r.output_tokens)
        return {
            p: UsageSummary(count=c, input_tokens=i, output_tokens=o)
            for p, (c, i, o) in per.items()
        }

    def summarize_by_period(
        self, period: str
    ) -> Dict[int, UsageSummary]:
        """period bucket 별 집계 — {bucket_start_ms: UsageSummary}.

        Parameters
        ----------
        period : str
            "minute" / "hour" / "day".

        Returns
        -------
        dict[int, UsageSummary]
            bucket_start_ms (= timestamp_ms // bucket_ms × bucket_ms) key.
        """

        if period not in _PERIOD_BUCKET_MS:
            raise ValueError(
                f"period 의 minute/hour/day 의무 — 실 {period}"
            )
        bucket_ms = _PERIOD_BUCKET_MS[period]
        per: Dict[int, Tuple[int, int, int]] = {}
        for r in self._records:
            bucket = (r.timestamp_ms // bucket_ms) * bucket_ms
            count, inp, out = per.get(bucket, (0, 0, 0))
            per[bucket] = (count + 1, inp + r.input_tokens, out + r.output_tokens)
        return {
            b: UsageSummary(count=c, input_tokens=i, output_tokens=o)
            for b, (c, i, o) in per.items()
        }

    def total(self) -> UsageSummary:
        """전체 누적 합산."""

        if not self._records:
            return UsageSummary(count=0, input_tokens=0, output_tokens=0)
        c = len(self._records)
        i = sum(r.input_tokens for r in self._records)
        o = sum(r.output_tokens for r in self._records)
        return UsageSummary(count=c, input_tokens=i, output_tokens=o)


def extract_anthropic_usage(body: dict) -> Tuple[int, int]:
    """Anthropic Messages API 응답 → (input_tokens, output_tokens).

    응답 schema — ``{"usage": {"input_tokens": N, "output_tokens": M}}``.
    부재 / 비숫자 = (0, 0) 의 graceful fallback.
    """

    usage = body.get("usage") if isinstance(body, dict) else None
    if not isinstance(usage, dict):
        return (0, 0)
    inp_raw = usage.get("input_tokens")
    out_raw = usage.get("output_tokens")
    inp = inp_raw if isinstance(inp_raw, int) and not isinstance(inp_raw, bool) else 0
    out = out_raw if isinstance(out_raw, int) and not isinstance(out_raw, bool) else 0
    return (max(0, inp), max(0, out))


def extract_openai_usage(body: dict) -> Tuple[int, int]:
    """OpenAI Chat Completions 응답 → (input_tokens, output_tokens).

    응답 schema — ``{"usage": {"prompt_tokens": N, "completion_tokens": M}}``.
    부재 / 비숫자 = (0, 0) 의 graceful fallback.
    """

    usage = body.get("usage") if isinstance(body, dict) else None
    if not isinstance(usage, dict):
        return (0, 0)
    inp_raw = usage.get("prompt_tokens")
    out_raw = usage.get("completion_tokens")
    inp = inp_raw if isinstance(inp_raw, int) and not isinstance(inp_raw, bool) else 0
    out = out_raw if isinstance(out_raw, int) and not isinstance(out_raw, bool) else 0
    return (max(0, inp), max(0, out))
