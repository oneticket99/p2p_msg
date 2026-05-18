# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 113 — X-Request-ID propagation middleware.

nginx 의 `proxy_set_header X-Request-ID $request_id` 의 backend 전파 정합.
contextvar 의 request-scoped 의 request_id 의 logger correlation base
(cycle 116~117 의 JSON structured logging 의 prerequisite).

설계 결정
---------
- contextvar 의 `current_request_id` — async context 의 isolation 의무 (aiohttp
  의 multi-request concurrent 의무).
- nginx 의 X-Request-ID header 가용 시 본 값 사용 + 부재 시 uuid4 hex 32자
  자체 생성 (graceful fallback).
- response header X-Request-ID 의 echo back (클라이언트 의 trace 가능).
- log 의 추가 layer = 별개 cycle 의 logging Item 4 의 의무 (Phase 4 cycle 116~117).

본 module 범위 외
----------------
- JSON formatter 의 request_id field 의 자동 injection — cycle 116~117 의무.
- distributed trace context (W3C traceparent) — Phase 5+ 의무.
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from typing import Any, Callable, Optional

from aiohttp import web

log = logging.getLogger(__name__)


_HEADER_REQUEST_ID = "X-Request-ID"

# contextvar — async task 별 request_id 의 격리 의무
current_request_id: ContextVar[Optional[str]] = ContextVar(
    "current_request_id", default=None
)


def get_request_id() -> Optional[str]:
    """현재 async context 의 request_id 반환. middleware 외 호출 시 None."""

    return current_request_id.get()


def _generate_request_id() -> str:
    """nginx X-Request-ID 부재 시 fallback — uuid4 hex 32자."""

    return uuid.uuid4().hex


@web.middleware
async def request_id_middleware(
    request: web.Request,
    handler: Callable[[web.Request], Any],
) -> web.StreamResponse:
    """X-Request-ID header → contextvar + response echo back.

    chain 위치 = auth_middleware 의 직전 (모든 request 의 trace 의무).
    """

    incoming = request.headers.get(_HEADER_REQUEST_ID, "").strip()
    request_id = incoming if incoming else _generate_request_id()
    # 한글 주석: request scope 의 attribute + contextvar 양쪽 등록
    request["request_id"] = request_id
    token = current_request_id.set(request_id)
    try:
        response = await handler(request)
        # response header echo — 클라이언트 의 trace 가능
        response.headers[_HEADER_REQUEST_ID] = request_id
        return response
    finally:
        current_request_id.reset(token)
