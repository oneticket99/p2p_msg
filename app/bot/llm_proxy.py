# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 bot framework LLM proxy — 사이클 65.

memory `project_bot_framework.md` 의 (A) 투네이션 고객센터 봇 default 배치 의
LLM 연동 인터랙티브 대화형 Q&A 의 핵심 layer. server-side proxy 패턴 = client
의 API key 노출 차단 + rate limit + prompt injection 방어 의 의무.

본 module 범위
-------------
- ``BotMessage`` frozen dataclass — role (user/assistant/system) + content + timestamp_ms
- ``LLMProvider`` Protocol — chat(messages) async + is_available classmethod
- ``MockLLMProvider`` — deterministic echo (test fixture)
- ``AnthropicProvider`` — placeholder (httpx + ANTHROPIC_API_KEY 의 별개 cycle 의 실 binding)
- ``select_llm_provider`` — factory (mock / anthropic / openai / gemini)
- ``RateLimitGate`` — token bucket per user_id (분당 N건)

본 cycle 의 범위 외 (별개 cycle):
- httpx + ANTHROPIC_API_KEY 의 실 binding (Messages API)
- OpenAI / Google Gemini 의 의 실 binding
- RAG context (Toonation FAQ + 정책 문서 의 vector store)
- prompt injection 방어 detector (jailbreak + system prompt leak 차단)
- 대화 history 의 server-side 영속화 (messages table 의 bot_id 의 별개 column 의무)
- streaming 응답 (Server-Sent Events 또는 chunked transfer)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Final, List, Optional, Protocol, Type

# RateLimitGate default — 분당 20건 의 token bucket (사용자 의 abuse 차단)
_DEFAULT_RATE_PER_MINUTE: Final[int] = 20
# 분 단위 = 60초
_SECONDS_PER_MINUTE: Final[int] = 60
# BotMessage content 최대 길이 (prompt injection 방어 의 1차 의 길이 cap)
_MAX_CONTENT_BYTES: Final[int] = 16 * 1024  # 16 KB


class BotRole(str, Enum):
    """BotMessage 의 role 식별."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class BotMessage:
    """단일 conversation turn 의 message.

    Attributes
    ----------
    role : BotRole
        user / assistant / system 의 3 종.
    content : str
        텍스트 본문 (UTF-8 한글 정합).
    timestamp_ms : int
        message 시점 (UNIX epoch ms).
    """

    role: BotRole
    content: str
    timestamp_ms: int

    def __post_init__(self) -> None:
        if not self.content:
            raise ValueError("content 빈 문자열 불가")
        if len(self.content.encode("utf-8")) > _MAX_CONTENT_BYTES:
            raise ValueError(
                f"content 길이 초과 — {_MAX_CONTENT_BYTES} byte 한도"
            )
        if self.timestamp_ms < 0:
            raise ValueError(f"timestamp_ms 음수 불가 — {self.timestamp_ms}")


class LLMProvider(Protocol):
    """LLM provider 의 interface.

    구현 의무:
    - ``is_available`` classmethod — runtime API key + framework 의 가용성
    - ``chat`` async method — N message 의 context → 1 assistant reply

    본 Protocol = duck typing 의 인터페이스 통일.
    """

    @classmethod
    def is_available(cls) -> bool:
        """현 환경 의 provider 의 가용성 (API key 의 존재 + framework import)."""
        ...

    async def chat(self, messages: List[BotMessage]) -> BotMessage:
        """N message context → 1 assistant reply."""
        ...


@dataclass(slots=True)
class MockLLMProvider:
    """test fixture — deterministic echo.

    실 LLM API 의존 부재. 입력 last user message 의 content 의 echo +
    "[mock] " prefix 의 의 assistant reply 반환.
    """

    @classmethod
    def is_available(cls) -> bool:
        return True

    async def chat(self, messages: List[BotMessage]) -> BotMessage:
        """last user message 의 echo + [mock] prefix."""

        if not messages:
            raise ValueError("messages 빈 list 불가")
        last_user = next(
            (m for m in reversed(messages) if m.role == BotRole.USER), None
        )
        if last_user is None:
            raise ValueError("user role message 부재")
        return BotMessage(
            role=BotRole.ASSISTANT,
            content=f"[mock] {last_user.content}",
            timestamp_ms=int(time.time() * 1000),
        )


class AnthropicProvider:
    """Anthropic Claude Messages API provider.

    cycle 70 의 ``app.bot.anthropic_client.AnthropicClient`` 를 LLMProvider
    Protocol 의 의 adapter 로 wrapping. caller 는 client 를 명시 주입 가능 +
    부재 시 ``from_env()`` 의 lazy 생성 (chat 호출 시점 의 환경 변수 + httpx
    transport 의 의 활성).

    Notes
    -----
    is_available classmethod = 환경 변수 + httpx import 의 가용성 prefetch.
    chat = AnthropicClient.chat 의 delegate + 동일 예외 (Auth/RateLimit/Server/
    Malformed/AnthropicError) 의 그대로 propagation.
    """

    def __init__(self, client: Optional[object] = None) -> None:
        # client 는 AnthropicClient 또는 None — None 일 시 chat 호출 시 lazy 생성
        self._client = client

    @classmethod
    def is_available(cls) -> bool:
        """ANTHROPIC_API_KEY env + httpx import 가능 여부."""

        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import httpx  # type: ignore[import]  # noqa: F401
        except ImportError:
            return False
        return True

    async def chat(self, messages: List[BotMessage]) -> BotMessage:
        """messages → assistant reply via AnthropicClient delegate.

        client 미주입 시 ``from_env()`` 의 lazy 생성 (ANTHROPIC_API_KEY 환경
        변수 + httpx_transport default). 후속 호출 의 동일 client 재사용.

        Raises
        ------
        AnthropicAuthError, AnthropicRateLimitError, AnthropicServerError,
        AnthropicMalformedError, AnthropicError
            (``app.bot.anthropic_client`` 의 예외 propagation)
        ValueError
            messages 빈 list.
        """

        if self._client is None:
            # 순환 import 회피 — chat 호출 시점 의 lazy import
            from app.bot.anthropic_client import from_env

            self._client = from_env()
        return await self._client.chat(messages)  # type: ignore[union-attr]


class OpenAIProvider:
    """OpenAI Chat Completions API provider — 사이클 84.

    `app.bot.openai_client.OpenAIClient` 의 LLMProvider Protocol adapter +
    AnthropicProvider 와 동일 의 dependency injection 패턴.

    Notes
    -----
    is_available classmethod = OPENAI_API_KEY env + httpx import 의 가용성 prefetch.
    chat = OpenAIClient.chat 의 delegate + 동일 예외 propagation.
    """

    def __init__(self, client: Optional[object] = None) -> None:
        self._client = client

    @classmethod
    def is_available(cls) -> bool:
        """OPENAI_API_KEY env + httpx import 가능 여부."""

        if not os.environ.get("OPENAI_API_KEY"):
            return False
        try:
            import httpx  # type: ignore[import]  # noqa: F401
        except ImportError:
            return False
        return True

    async def chat(self, messages: List[BotMessage]) -> BotMessage:
        """messages → assistant reply via OpenAIClient delegate."""

        if self._client is None:
            from app.bot.openai_client import from_env

            self._client = from_env()
        return await self._client.chat(messages)  # type: ignore[union-attr]


def select_llm_provider(name: Optional[str] = None) -> Type[LLMProvider]:
    """LLM provider 의 factory.

    Parameters
    ----------
    name : str | None
        "mock" / "anthropic" / "openai" / "gemini". None = 자동 detect
        (가용 의 first match + fallback 의 의무 = mock).

    Returns
    -------
    Type[LLMProvider]
        provider class. caller 의 instantiate 의무.

    Raises
    ------
    ValueError
        unknown name.
    NotImplementedError
        gemini 의 별개 cycle 의무.
    """

    if name is None:
        # auto detect — anthropic 우선 + openai fallback + mock 최종
        if AnthropicProvider.is_available():
            return AnthropicProvider  # type: ignore[return-value]
        if OpenAIProvider.is_available():
            return OpenAIProvider  # type: ignore[return-value]
        return MockLLMProvider  # type: ignore[return-value]
    name_l = name.lower()
    if name_l == "mock":
        return MockLLMProvider  # type: ignore[return-value]
    if name_l == "anthropic":
        return AnthropicProvider  # type: ignore[return-value]
    if name_l == "openai":
        return OpenAIProvider  # type: ignore[return-value]
    if name_l == "gemini":
        raise NotImplementedError(
            "gemini provider 별개 cycle 의무 — google-generativeai + GOOGLE_API_KEY"
        )
    raise ValueError(f"unknown provider name — {name}")


@dataclass(slots=True)
class RateLimitGate:
    """token bucket per user_id — 분당 N건 의 abuse 차단.

    Attributes
    ----------
    rate_per_minute : int
        분당 허용 건 (default 20).
    _buckets : dict[int, list[float]]
        user_id → 호출 timestamp (epoch seconds) list. 1분 이전 의 자동 prune.
    """

    rate_per_minute: int = _DEFAULT_RATE_PER_MINUTE
    _buckets: Dict[int, List[float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.rate_per_minute <= 0:
            raise ValueError(
                f"rate_per_minute 양수 의무 — {self.rate_per_minute}"
            )

    def allow(self, user_id: int, *, now_seconds: Optional[float] = None) -> bool:
        """1 호출 허용 여부 + bucket 에 timestamp 누적.

        Parameters
        ----------
        user_id : int
            대상 사용자.
        now_seconds : float | None
            현재 시점 (test injection 가능). None = time.time().

        Returns
        -------
        bool
            허용 = True (bucket 에 추가). reject = False (bucket 불변).
        """

        if user_id <= 0:
            raise ValueError(f"user_id 양수 의무 — {user_id}")
        now = now_seconds if now_seconds is not None else time.time()
        cutoff = now - _SECONDS_PER_MINUTE
        bucket = self._buckets.setdefault(user_id, [])
        # 1분 이전 prune
        self._buckets[user_id] = [t for t in bucket if t >= cutoff]
        bucket = self._buckets[user_id]
        if len(bucket) >= self.rate_per_minute:
            return False
        bucket.append(now)
        return True

    def remaining(self, user_id: int, *, now_seconds: Optional[float] = None) -> int:
        """현 시점 의 잔여 호출 수."""

        if user_id <= 0:
            raise ValueError(f"user_id 양수 의무 — {user_id}")
        now = now_seconds if now_seconds is not None else time.time()
        cutoff = now - _SECONDS_PER_MINUTE
        bucket = self._buckets.get(user_id, [])
        active = sum(1 for t in bucket if t >= cutoff)
        return max(0, self.rate_per_minute - active)
