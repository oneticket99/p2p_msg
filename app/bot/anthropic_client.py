# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 bot Anthropic Messages API client — 사이클 70.

memory `project_bot_framework.md` (A) 투네이션 고객센터 봇 의 실 LLM provider
binding. cycle 65 `llm_proxy.AnthropicProvider` placeholder 다음 의 serialization
+ HTTP transport + error mapping layer.

본 module 범위
-------------
- BotMessage chain → Anthropic Messages API payload 직렬화 (system 의 top-level
  추출 + user / assistant 의 messages 배열 변환)
- Messages API 응답 → BotMessage 파싱 (content array 의 text block 합본)
- HTTP transport Protocol 주입 (httpx 미설치 환경 의 test mock 호환)
- 상태코드 → 4 종 예외 매핑 (auth / rate / server / malformed)

본 cycle 의 범위 외 (별개 cycle):
- httpx 의 실 설치 + 의존성 등록 (현 venv 미설치)
- streaming 응답 (SSE)
- retry backoff (429 retry-after 헤더 + exponential)
- 토큰 카운트 + 비용 추적
- tool use / function calling
"""

from __future__ import annotations

import asyncio
import os
import random
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Final, List, Optional, Tuple

from app.bot.llm_proxy import BotMessage, BotRole

# Anthropic Messages API endpoint + 버전 헤더
_API_BASE: Final[str] = "https://api.anthropic.com"
_API_PATH: Final[str] = "/v1/messages"
_API_VERSION: Final[str] = "2023-06-01"
# default model — 클라이언트 caller 의 override 가능
_DEFAULT_MODEL: Final[str] = "claude-3-5-sonnet-latest"
# 응답 토큰 한도 default — caller 가 늘릴 수 있음
_DEFAULT_MAX_TOKENS: Final[int] = 1024
# httpx timeout default — 초 단위
_DEFAULT_TIMEOUT_SECONDS: Final[float] = 30.0
# retry default — 0 = 회수 무 (backwards compat) + caller opt-in 의무
_DEFAULT_MAX_RETRIES: Final[int] = 0
# 지수 backoff base — 초 단위 (1.0 * 2^attempt)
_DEFAULT_BACKOFF_BASE_SECONDS: Final[float] = 1.0
# jitter — backoff delay 의 추가 randomization 의 default 부재 (caller opt-in)
_DEFAULT_JITTER_MAX_SECONDS: Final[float] = 0.0
# retry-after 헤더 의 cap — 비정상 큰 값 차단 (DoS 회피)
_RETRY_AFTER_MAX_SECONDS: Final[float] = 60.0


SleepFn = Callable[[float], Awaitable[None]]
JitterFn = Callable[[], float]


def _parse_retry_after(headers: dict) -> Optional[float]:
    """retry-after 헤더 의 초 단위 float 추출.

    Anthropic API 는 정수 초 단위 의 retry-after 반환 (HTTP date 미지원).
    헤더 키 = 의 대소문자 무시 의 처리 (case-insensitive).

    Returns
    -------
    float | None
        파싱 성공 시 의 양수 + cap 초과 시 cap + 실패 / 음수 / 부재 시 None.
    """

    if not headers:
        return None
    # case-insensitive lookup
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


class AnthropicError(Exception):
    """Anthropic API 호출 실패 공통 base — 구체 예외는 subclass."""


class AnthropicAuthError(AnthropicError):
    """API key 부재 또는 401 / 403 응답."""


class AnthropicRateLimitError(AnthropicError):
    """429 rate limit — retry-after 헤더 처리는 별개 cycle."""


class AnthropicServerError(AnthropicError):
    """5xx 서버 장애 — Anthropic 서비스 응답 실패."""


class AnthropicMalformedError(AnthropicError):
    """응답 schema 위반 — content / role / text 필드 부재."""


def serialize_messages(
    messages: List[BotMessage],
) -> Tuple[str, List[dict]]:
    """BotMessage chain → (system_str, messages_payload).

    Anthropic Messages API 는 system role 을 top-level 의 별개 field 로 분리한다.
    user 와 assistant 만 messages 배열 entry 가 된다.

    Parameters
    ----------
    messages : list[BotMessage]
        system / user / assistant 의 round-trip chain.

    Returns
    -------
    tuple[str, list[dict]]
        (system_str, payload). system_str 은 여러 SYSTEM 메시지가 있을 때 "\\n\\n"
        결합 결과 + 부재 시 빈 문자열.
    """

    system_parts: List[str] = []
    payload: List[dict] = []
    for msg in messages:
        if msg.role == BotRole.SYSTEM:
            system_parts.append(msg.content)
            continue
        role_str = "user" if msg.role == BotRole.USER else "assistant"
        payload.append({"role": role_str, "content": msg.content})
    return ("\n\n".join(system_parts), payload)


def parse_response(body: dict) -> BotMessage:
    """Messages API 응답 dict → BotMessage.

    Anthropic 응답 schema (요약)::

        {
          "id": "msg_...",
          "role": "assistant",
          "content": [{"type": "text", "text": "..."}],
          "stop_reason": "end_turn",
          ...
        }

    Raises
    ------
    AnthropicMalformedError
        content array 부재 + role != assistant + text 필드 부재.
    """

    content = body.get("content")
    if not content or not isinstance(content, list):
        raise AnthropicMalformedError(f"content array 부재 — body={body}")
    text_parts: List[str] = []
    for block in content:
        if not isinstance(block, dict):
            raise AnthropicMalformedError(f"content block dict 아님 — {block}")
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if not isinstance(text, str):
            raise AnthropicMalformedError(f"text 필드 부재 — block={block}")
        text_parts.append(text)
    if not text_parts:
        raise AnthropicMalformedError("text 추출 결과 빈 — 응답 본문 의심")
    role = body.get("role")
    if role != "assistant":
        raise AnthropicMalformedError(f"role=assistant 부재 — role={role}")
    return BotMessage(
        role=BotRole.ASSISTANT,
        content="\n".join(text_parts),
        timestamp_ms=0,
    )


# HTTP transport — caller 가 주입 가능
# (url, headers, json_body) → (status_code, response_headers, response_body_dict)
# cycle 73 — 3-tuple 의 response_headers 추가 (retry-after 헤더 의 honor 용)
HttpTransport = Callable[[str, dict, dict], Awaitable[Tuple[int, dict, dict]]]


async def _placeholder_transport(
    url: str, headers: dict, body: dict
) -> Tuple[int, dict, dict]:
    """미주입 default — httpx_transport() 또는 mock transport 의무."""

    raise NotImplementedError(
        "AnthropicClient transport 미주입 — httpx_transport() 또는 mock 주입 필요"
    )


def httpx_transport(timeout: float = _DEFAULT_TIMEOUT_SECONDS) -> HttpTransport:
    """httpx.AsyncClient 기반 transport factory.

    Notes
    -----
    본 cycle 의 venv 는 httpx 미설치. caller 는 별개 cycle 의 httpx 설치 + 의존성
    파일 갱신 의무. 호출 시 ImportError → AnthropicError 변환.
    """

    async def _send(
        url: str, headers: dict, body: dict
    ) -> Tuple[int, dict, dict]:
        try:
            import httpx  # type: ignore[import]
        except ImportError as exc:
            raise AnthropicError(
                "httpx 미설치 — pip install httpx 필요"
            ) from exc
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=body)
            return (resp.status_code, dict(resp.headers), resp.json())

    return _send


@dataclass(slots=True)
class AnthropicClient:
    """Anthropic Messages API client.

    Attributes
    ----------
    api_key : str
        ANTHROPIC_API_KEY — 빈 차단.
    model : str
        모델 식별자 (default ``claude-3-5-sonnet-latest``).
    max_tokens : int
        응답 토큰 한도 (default 1024).
    base_url : str
        API base URL (테스트 의 override 가능).
    transport : HttpTransport
        HTTP 전송 함수 — default placeholder + caller 의 주입 의무.
    max_retries : int
        429 / 5xx 응답 의 재시도 횟수 (default 0 = 회수 무). 양수 음수 차단.
    backoff_base_seconds : float
        지수 backoff base — 실 delay = base * 2^attempt (default 1.0).
    jitter_max_seconds : float
        backoff delay 의 추가 jitter range — 실 jitter = jitter_fn() * max
        (default 0.0 = jitter 부재). 음수 차단.
    sleep_fn : SleepFn
        async sleep 함수 — 테스트 의 의 mock 주입 가능 (default asyncio.sleep).
    jitter_fn : JitterFn
        [0, 1) range 의 float 의 sync 함수 — default random.random.
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
            raise AnthropicAuthError(
                "api_key 빈 문자열 불가 — ANTHROPIC_API_KEY 주입 의무"
            )
        if not self.model:
            raise ValueError("model 빈 문자열 불가")
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens 양수 의무 — {self.max_tokens}")
        if not self.base_url:
            raise ValueError("base_url 빈 문자열 불가")
        if self.max_retries < 0:
            raise ValueError(
                f"max_retries 음수 차단 — {self.max_retries}"
            )
        if self.backoff_base_seconds <= 0:
            raise ValueError(
                f"backoff_base_seconds 양수 의무 — {self.backoff_base_seconds}"
            )
        if self.jitter_max_seconds < 0:
            raise ValueError(
                f"jitter_max_seconds 음수 차단 — {self.jitter_max_seconds}"
            )

    def build_headers(self) -> dict:
        """API 요청 헤더 — x-api-key + anthropic-version + content-type."""

        return {
            "x-api-key": self.api_key,
            "anthropic-version": _API_VERSION,
            "content-type": "application/json",
        }

    def build_body(self, messages: List[BotMessage]) -> dict:
        """API 요청 body — model + max_tokens + system + messages."""

        system_str, payload = serialize_messages(messages)
        body: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": payload,
        }
        if system_str:
            body["system"] = system_str
        return body

    async def chat(self, messages: List[BotMessage]) -> BotMessage:
        """messages chain → assistant reply.

        Retry 정책 — max_retries > 0 시 429 / 5xx 응답 의 지수 backoff 재시도.
        지수 backoff 의 delay = backoff_base_seconds * 2^attempt (attempt 0~).
        max_retries 초과 시 마지막 status 의 대응 예외 raise.

        Raises
        ------
        ValueError
            messages 빈 list.
        AnthropicAuthError
            401 / 403 (재시도 없음).
        AnthropicRateLimitError
            429 + 재시도 소진.
        AnthropicServerError
            5xx + 재시도 소진.
        AnthropicMalformedError
            응답 schema 위반.
        AnthropicError
            그 외 4xx 또는 transport ImportError (재시도 없음).
        """

        if not messages:
            raise ValueError("messages 빈 list 불가")
        url = f"{self.base_url}{_API_PATH}"
        headers = self.build_headers()
        body = self.build_body(messages)
        attempt = 0
        while True:
            status, resp_headers, resp_body = await self.transport(
                url, headers, body
            )
            if status == 200:
                return parse_response(resp_body)
            if status in (401, 403):
                raise AnthropicAuthError(
                    f"인증 실패 status={status} body={resp_body}"
                )
            retryable = status == 429 or (500 <= status < 600)
            if not retryable:
                raise AnthropicError(
                    f"unexpected status={status} body={resp_body}"
                )
            if attempt >= self.max_retries:
                if status == 429:
                    raise AnthropicRateLimitError(
                        f"rate limit status=429 body={resp_body} "
                        f"(retries={self.max_retries} 소진)"
                    )
                raise AnthropicServerError(
                    f"서버 장애 status={status} body={resp_body} "
                    f"(retries={self.max_retries} 소진)"
                )
            # retry-after 헤더 의 honor (429 우선) — 부재 / 비정상 시 지수 backoff
            retry_after = _parse_retry_after(resp_headers)
            if retry_after is not None:
                delay = retry_after
            else:
                delay = self.backoff_base_seconds * (2 ** attempt)
            # jitter 추가 — jitter_max_seconds > 0 시 jitter_fn() * max 의 추가
            if self.jitter_max_seconds > 0:
                delay += self.jitter_fn() * self.jitter_max_seconds
            await self.sleep_fn(delay)
            attempt += 1


def from_env(transport: Optional[HttpTransport] = None) -> AnthropicClient:
    """환경 변수 ANTHROPIC_API_KEY → AnthropicClient.

    Parameters
    ----------
    transport : HttpTransport | None
        None = httpx_transport() default. caller 가 mock 주입 가능.

    Raises
    ------
    AnthropicAuthError
        ANTHROPIC_API_KEY 환경 변수 부재.
    """

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise AnthropicAuthError("ANTHROPIC_API_KEY 환경 변수 부재")
    return AnthropicClient(
        api_key=api_key,
        transport=transport or httpx_transport(),
    )
