# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — Bot LLM proxy (Phase 3 사이클 74).

엔드포인트:
- POST /api/bot/chat — 클라이언트 의 BotMessage chain → 서버 의 AnthropicProvider
  의 forward → 클라이언트 의 ASSISTANT reply 반환

설계 결정
---------
- ANTHROPIC_API_KEY 의 서버 환경 변수 격리 — 클라이언트 의 API key 부재 의 정합
  ([memory feedback `project_bot_framework`](../../memory/project_bot_framework.md)
  의 server-side LLM proxy 패턴 정합).
- auth_middleware 의 Bearer 검증 의무 (PUBLIC_PATHS 외 — TooTalk 사용자 의무).
- RateLimitGate 의 per-user_id token bucket — abuse 차단 (memory M7 의 정합).
- AnthropicProvider 의 app context 의 의 직접 주입 (테스트 의 mock provider 가능).
- 요청 schema = {messages: [{role, content, timestamp_ms}, ...]}.
- 응답 schema = {reply: {role: "assistant", content: ..., timestamp_ms: ...}}.

본 cycle 의 범위 외 (별개 cycle):
- streaming 응답 (SSE 또는 chunked)
- 대화 history 의 server-side 영속화 (별개 messages.bot_id column)
- prompt injection 의 advanced 차단
- 사용 통계 + 비용 추적
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from aiohttp import web

from app.bot.anthropic_client import (
    AnthropicAuthError,
    AnthropicError,
    AnthropicMalformedError,
    AnthropicRateLimitError,
    AnthropicServerError,
)
from app.bot.llm_proxy import BotMessage, BotRole, LLMProvider, RateLimitGate

log = logging.getLogger(__name__)

# app context key — provider + rate gate 의 등록 위치 (aiohttp web.AppKey 의 type-safe)
APP_KEY_PROVIDER: web.AppKey[LLMProvider] = web.AppKey("bot_llm_provider", LLMProvider)
APP_KEY_RATE_GATE: web.AppKey[RateLimitGate] = web.AppKey("bot_rate_gate", RateLimitGate)

# 요청 body 의 message chain 의 한도 — abuse 차단
_MAX_MESSAGES_PER_REQUEST = 32
# 단일 메시지 content 의 한도 (BotMessage 자체 16KB cap 의 정합)
_MAX_CONTENT_BYTES = 16 * 1024


def _parse_role(raw: str) -> BotRole:
    """role 문자열 → BotRole enum.

    Raises
    ------
    web.HTTPBadRequest
        invalid role string.
    """

    raw_l = raw.lower()
    if raw_l == "user":
        return BotRole.USER
    if raw_l == "assistant":
        return BotRole.ASSISTANT
    if raw_l == "system":
        # 클라이언트 의 system role 주입 = 보안 위험 — 차단
        raise web.HTTPBadRequest(
            reason="system role 의 클라이언트 주입 차단 — 서버 의 default prompt 사용"
        )
    raise web.HTTPBadRequest(reason=f"unknown role — {raw}")


def _parse_messages(raw: Any) -> List[BotMessage]:
    """request body 의 messages 배열 → BotMessage list.

    Raises
    ------
    web.HTTPBadRequest
        schema 위반 또는 message 한도 초과.
    """

    if not isinstance(raw, list):
        raise web.HTTPBadRequest(reason="messages 배열 의무")
    if not raw:
        raise web.HTTPBadRequest(reason="messages 빈 list 불가")
    if len(raw) > _MAX_MESSAGES_PER_REQUEST:
        raise web.HTTPBadRequest(
            reason=f"messages 한도 초과 — max {_MAX_MESSAGES_PER_REQUEST}"
        )
    out: List[BotMessage] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise web.HTTPBadRequest(
                reason=f"messages[{idx}] dict 의무"
            )
        role_raw = item.get("role")
        content = item.get("content")
        timestamp_ms = item.get("timestamp_ms")
        if not isinstance(role_raw, str):
            raise web.HTTPBadRequest(
                reason=f"messages[{idx}].role string 의무"
            )
        if not isinstance(content, str) or not content:
            raise web.HTTPBadRequest(
                reason=f"messages[{idx}].content 빈 차단"
            )
        if (
            not isinstance(timestamp_ms, int)
            or isinstance(timestamp_ms, bool)
            or timestamp_ms < 0
        ):
            raise web.HTTPBadRequest(
                reason=f"messages[{idx}].timestamp_ms 음수 차단 + int 의무"
            )
        if len(content.encode("utf-8")) > _MAX_CONTENT_BYTES:
            raise web.HTTPBadRequest(
                reason=(
                    f"messages[{idx}].content 16KB 초과 — "
                    f"실 {len(content.encode('utf-8'))} bytes"
                )
            )
        try:
            role = _parse_role(role_raw)
        except web.HTTPBadRequest as exc:
            # idx context 추가
            raise web.HTTPBadRequest(
                reason=f"messages[{idx}]: {exc.reason}"
            ) from exc
        out.append(
            BotMessage(role=role, content=content, timestamp_ms=timestamp_ms)
        )
    return out


def _reply_to_wire(reply: BotMessage) -> Dict[str, Any]:
    """BotMessage reply → JSON wire dict.

    BotMessage.role 은 BotRole enum 의 보장 (BotMessage 의 dataclass validation).
    Enum.value 의 직접 access — hasattr fallback 부재 (cycle 78 hardening).
    """

    return {
        "role": reply.role.value,
        "content": reply.content,
        "timestamp_ms": reply.timestamp_ms,
    }


async def handle_bot_chat(request: web.Request) -> web.Response:
    """POST /api/bot/chat — 클라이언트 → 서버 LLM proxy → 클라이언트.

    요청 schema:
        {"messages": [{"role": "user", "content": "...", "timestamp_ms": 0}, ...]}

    응답 schema:
        {"reply": {"role": "assistant", "content": "...", "timestamp_ms": 0}}

    상태 매핑:
    - 200 → 성공
    - 401 → Bearer 인증 부재 (auth_middleware)
    - 400 → schema 위반 또는 limit 초과
    - 429 → per-user rate limit 차단
    - 502 → Anthropic 5xx + 재시도 소진 (server-side 의 외부 의존 실패)
    - 503 → Anthropic 429 + 재시도 소진 (upstream rate limit)
    - 500 → 그 외 AnthropicError 또는 unexpected
    """

    user_id = request.get("user_id")
    if user_id is None:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    # bool 의 isinstance(int) is True 의 edge case 명시 차단 (cycle 78 hardening)
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="user_id 양수 int 의무")

    # rate limit gate — per-user_id 의 abuse 차단
    gate: Optional[RateLimitGate] = request.app.get(APP_KEY_RATE_GATE)
    if gate is not None and not gate.allow(user_id):
        raise web.HTTPTooManyRequests(
            reason=f"분당 호출 한도 초과 — user_id={user_id}"
        )

    # body parse
    try:
        body = await request.json()
    except ValueError as exc:
        raise web.HTTPBadRequest(reason="JSON body 의무") from exc
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(reason="body object 의무")

    messages = _parse_messages(body.get("messages"))

    # provider lookup — app context 의 의 등록 의무
    provider: Optional[LLMProvider] = request.app.get(APP_KEY_PROVIDER)
    if provider is None:
        raise web.HTTPServiceUnavailable(
            reason="LLM provider 미등록 — 서버 영역 의 ANTHROPIC_API_KEY 의무"
        )

    # LLM 호출 + 예외 매핑
    try:
        reply = await provider.chat(messages)
    except AnthropicAuthError as exc:
        log.error("Anthropic auth 실패 — server config 점검 의무", exc_info=exc)
        raise web.HTTPInternalServerError(
            reason="LLM provider 인증 실패 — 서버 설정 의무"
        ) from exc
    except AnthropicRateLimitError as exc:
        raise web.HTTPServiceUnavailable(
            reason="upstream rate limit — retry 후 재시도"
        ) from exc
    except AnthropicServerError as exc:
        raise web.HTTPBadGateway(
            reason="upstream 서버 장애"
        ) from exc
    except AnthropicMalformedError as exc:
        log.error("Anthropic 응답 schema 위반", exc_info=exc)
        raise web.HTTPBadGateway(
            reason="upstream 응답 schema 위반"
        ) from exc
    except AnthropicError as exc:
        log.error("Anthropic error", exc_info=exc)
        raise web.HTTPInternalServerError(
            reason="LLM provider 호출 실패"
        ) from exc

    return web.json_response({"reply": _reply_to_wire(reply)})


def register_bot_routes(app: web.Application) -> None:
    """``server.main`` 의 register entry — /api/bot/chat POST 등록."""

    app.router.add_post("/api/bot/chat", handle_bot_chat)
