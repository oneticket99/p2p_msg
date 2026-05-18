# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 bot OpenAI Chat Completions API client — 사이클 84.

memory `project_bot_framework.md` 의 provider plug-in 패턴 의 정합 — Anthropic
client (cycle 70~73) 와 동일 의 abstraction layer 의 OpenAI 등가 구현.

OpenAI vs Anthropic 의 schema 차이
---------------------------------
- endpoint: ``/v1/chat/completions`` (Anthropic = ``/v1/messages``)
- system role: messages array 의 entry (Anthropic = top-level ``system`` field 분리)
- Authorization: ``Bearer <key>`` (Anthropic = ``x-api-key`` header)
- API version header: 부재 (Anthropic = ``anthropic-version`` header)
- response: ``choices[0].message.{role,content}`` (Anthropic = ``content[].text``)

본 module 범위
-------------
- BotMessage chain → OpenAI messages payload 직렬화 (system 의 inline 유지)
- Chat Completions 응답 → BotMessage 파싱
- HTTP transport Protocol 주입 (httpx 미설치 환경 의 test mock 호환)
- 상태코드 → 4 종 예외 매핑 (auth / rate / server / malformed)
- retry/backoff + retry-after + jitter (Anthropic 과 동일 의 정책)

본 cycle 의 범위 외 (별개 cycle):
- OpenAI 의 streaming response (SSE delta)
- function calling / tools
- assistant API (vs chat completions)
- 토큰 카운트 + 비용 추적
- model 별 의 context window 의 의 검증
"""

from __future__ import annotations

import asyncio
import os
import random
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Final, List, Optional, Tuple

from app.bot.llm_proxy import BotMessage, BotRole

# OpenAI Chat Completions API endpoint
_API_BASE: Final[str] = "https://api.openai.com"
_API_PATH: Final[str] = "/v1/chat/completions"
# default model — caller 가 override 가능 (4o-mini 의 cost 효율 우선)
_DEFAULT_MODEL: Final[str] = "gpt-4o-mini"
_DEFAULT_MAX_TOKENS: Final[int] = 1024
_DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
_DEFAULT_MAX_RETRIES: Final[int] = 0
_DEFAULT_BACKOFF_BASE_SECONDS: Final[float] = 1.0
_DEFAULT_JITTER_MAX_SECONDS: Final[float] = 0.0
_RETRY_AFTER_MAX_SECONDS: Final[float] = 60.0


SleepFn = Callable[[float], Awaitable[None]]
JitterFn = Callable[[], float]


class OpenAIError(Exception):
    """OpenAI API 호출 실패 공통 base — 구체 예외는 subclass."""


class OpenAIAuthError(OpenAIError):
    """API key 부재 또는 401 / 403 응답."""


class OpenAIRateLimitError(OpenAIError):
    """429 rate limit — retry-after 헤더 처리는 본 cycle 정합."""


class OpenAIServerError(OpenAIError):
    """5xx 서버 장애 — OpenAI 서비스 응답 실패."""


class OpenAIMalformedError(OpenAIError):
    """응답 schema 위반 — choices / message / content 필드 부재."""


def serialize_messages(messages: List[BotMessage]) -> List[dict]:
    """BotMessage chain → OpenAI messages payload.

    Anthropic 과 달리 system role 의 분리 부재 — messages array 의 entry 의 유지.

    Returns
    -------
    list[dict]
        ``[{"role": "system|user|assistant", "content": str}, ...]``.
    """

    payload: List[dict] = []
    for msg in messages:
        if msg.role == BotRole.SYSTEM:
            role_str = "system"
        elif msg.role == BotRole.USER:
            role_str = "user"
        else:
            role_str = "assistant"
        payload.append({"role": role_str, "content": msg.content})
    return payload


def parse_response(body: dict) -> BotMessage:
    """Chat Completions 응답 dict → BotMessage.

    OpenAI 응답 schema (요약)::

        {
          "id": "chatcmpl-...",
          "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "..."}}
          ],
          ...
        }

    Raises
    ------
    OpenAIMalformedError
        choices array 부재 / message 부재 / role/content 부재.
    """

    choices = body.get("choices")
    if not choices or not isinstance(choices, list):
        raise OpenAIMalformedError(f"choices array 부재 — body={body}")
    first = choices[0]
    if not isinstance(first, dict):
        raise OpenAIMalformedError(f"choices[0] dict 아님 — {first}")
    message = first.get("message")
    if not isinstance(message, dict):
        raise OpenAIMalformedError(f"message dict 부재 — {first}")
    role = message.get("role")
    if role != "assistant":
        raise OpenAIMalformedError(f"role=assistant 부재 — role={role}")
    content = message.get("content")
    if not isinstance(content, str) or not content:
        raise OpenAIMalformedError(f"content string 부재 — {message}")
    return BotMessage(
        role=BotRole.ASSISTANT, content=content, timestamp_ms=0
    )


HttpTransport = Callable[[str, dict, dict], Awaitable[Tuple[int, dict, dict]]]


async def _placeholder_transport(
    url: str, headers: dict, body: dict
) -> Tuple[int, dict, dict]:
    """미주입 default — httpx_transport() 또는 mock transport 의무."""

    raise NotImplementedError(
        "OpenAIClient transport 미주입 — httpx_transport() 또는 mock 주입 필요"
    )


def httpx_transport(timeout: float = _DEFAULT_TIMEOUT_SECONDS) -> HttpTransport:
    """httpx.AsyncClient 기반 transport factory.

    Notes
    -----
    본 cycle 의 venv 는 httpx 미설치. caller 는 별개 cycle 의 httpx 설치 의무.
    """

    async def _send(
        url: str, headers: dict, body: dict
    ) -> Tuple[int, dict, dict]:
        try:
            import httpx  # type: ignore[import]
        except ImportError as exc:
            raise OpenAIError(
                "httpx 미설치 — pip install httpx 필요"
            ) from exc
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            return (resp.status_code, dict(resp.headers), resp.json())

    return _send


def _parse_retry_after(headers: dict) -> Optional[float]:
    """retry-after 헤더 의 초 단위 float 추출 (case-insensitive).

    Returns
    -------
    float | None
        파싱 성공 + 양수 + cap 의 의 적용. 부재 / 비숫자 / 음수 / 빈 = None.
    """

    if not headers:
        return None
    raw: Optional[str] = None
    for key, value in headers.items():
        if isinstance(key, str) and key.lower() == "retry-after":
            raw = str(value) if value is not None else None
            break
    if raw is None or not raw.strip():
        return None
    try:
        seconds = float(raw.strip())
    except (TypeError, ValueError):
        return None
    if seconds <= 0:
        return None
    return min(seconds, _RETRY_AFTER_MAX_SECONDS)


@dataclass(slots=True)
class OpenAIClient:
    """OpenAI Chat Completions API client.

    Attributes
    ----------
    api_key : str
        OPENAI_API_KEY — 빈 차단.
    model : str
        모델 식별자 (default ``gpt-4o-mini``).
    max_tokens : int
        응답 토큰 한도 (default 1024).
    base_url : str
        API base URL (테스트 의 override 가능).
    transport : HttpTransport
        HTTP 전송 함수 — default placeholder + caller 의 주입 의무.
    max_retries : int
        429 / 5xx 응답 의 재시도 횟수 (default 0).
    backoff_base_seconds : float
        지수 backoff base (default 1.0).
    jitter_max_seconds : float
        backoff delay 의 추가 jitter range (default 0.0).
    sleep_fn : SleepFn
        async sleep 함수 (default asyncio.sleep).
    jitter_fn : JitterFn
        [0, 1) range 의 float sync 함수 (default random.random).
    """

    api_key: str
    model: str = _DEFAULT_MODEL
    max_tokens: int = _DEFAULT_MAX_TOKENS
    base_url: str = _API_BASE
    transport: HttpTransport = field(default=_placeholder_transport)
    max_retries: int = _DEFAULT_MAX_RETRIES
    backoff_base_seconds: float = _DEFAULT_BACKOFF_BASE_SECONDS
    jitter_max_seconds: float = _DEFAULT_JITTER_MAX_SECONDS
    sleep_fn: SleepFn = field(default=asyncio.sleep)
    jitter_fn: JitterFn = field(default=random.random)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise OpenAIAuthError(
                "api_key 빈 문자열 불가 — OPENAI_API_KEY 주입 의무"
            )
        if not self.model:
            raise ValueError("model 빈 문자열 불가")
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens 양수 의무 — {self.max_tokens}")
        if not self.base_url:
            raise ValueError("base_url 빈 문자열 불가")
        if self.max_retries < 0:
            raise ValueError(f"max_retries 음수 차단 — {self.max_retries}")
        if self.backoff_base_seconds <= 0:
            raise ValueError(
                f"backoff_base_seconds 양수 의무 — {self.backoff_base_seconds}"
            )
        if self.jitter_max_seconds < 0:
            raise ValueError(
                f"jitter_max_seconds 음수 차단 — {self.jitter_max_seconds}"
            )

    def build_headers(self) -> dict:
        """API 요청 헤더 — Authorization Bearer + content-type."""

        return {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }

    def build_body(self, messages: List[BotMessage]) -> dict:
        """API 요청 body — model + max_tokens + messages."""

        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": serialize_messages(messages),
        }

    async def chat(self, messages: List[BotMessage]) -> BotMessage:
        """messages chain → assistant reply.

        Raises
        ------
        ValueError
            messages 빈 list.
        OpenAIAuthError, OpenAIRateLimitError, OpenAIServerError,
        OpenAIMalformedError, OpenAIError
            HTTP status / 응답 schema 위반 의 매핑.
        """

        if not messages:
            raise ValueError("messages 빈 list 불가")
        url = f"{self.base_url}{_API_PATH}"
        headers = self.build_headers()
        body = self.build_body(messages)
        attempt = 0
        while True:
            try:
                status, resp_headers, resp_body = await self.transport(
                    url, headers, body
                )
            except (ConnectionError, OSError, TimeoutError) as exc:
                if attempt >= self.max_retries:
                    raise OpenAIServerError(
                        f"network 장애 (retries={self.max_retries} 소진) — {exc}"
                    ) from exc
                delay = self.backoff_base_seconds * (2 ** attempt)
                if self.jitter_max_seconds > 0:
                    delay += self.jitter_fn() * self.jitter_max_seconds
                await self.sleep_fn(delay)
                attempt += 1
                continue
            if status == 200:
                return parse_response(resp_body)
            if status in (401, 403):
                raise OpenAIAuthError(
                    f"인증 실패 status={status} body={resp_body}"
                )
            retryable = status == 429 or (500 <= status < 600)
            if not retryable:
                raise OpenAIError(
                    f"unexpected status={status} body={resp_body}"
                )
            if attempt >= self.max_retries:
                if status == 429:
                    raise OpenAIRateLimitError(
                        f"rate limit status=429 body={resp_body} "
                        f"(retries={self.max_retries} 소진)"
                    )
                raise OpenAIServerError(
                    f"서버 장애 status={status} body={resp_body} "
                    f"(retries={self.max_retries} 소진)"
                )
            retry_after = _parse_retry_after(resp_headers)
            if retry_after is not None:
                delay = retry_after
            else:
                delay = self.backoff_base_seconds * (2 ** attempt)
            if self.jitter_max_seconds > 0:
                delay += self.jitter_fn() * self.jitter_max_seconds
            await self.sleep_fn(delay)
            attempt += 1


def from_env(transport: Optional[HttpTransport] = None) -> OpenAIClient:
    """환경 변수 OPENAI_API_KEY → OpenAIClient.

    Raises
    ------
    OpenAIAuthError
        OPENAI_API_KEY 환경 변수 부재.
    """

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise OpenAIAuthError("OPENAI_API_KEY 환경 변수 부재")
    return OpenAIClient(
        api_key=api_key,
        transport=transport or httpx_transport(),
    )
