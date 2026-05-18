# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.middleware.request_id`` 의 단위 테스트.

contextvar isolation + nginx X-Request-ID propagation + uuid4 fallback +
response header echo.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any
from unittest.mock import MagicMock

import pytest

from server.middleware.request_id import (
    current_request_id,
    get_request_id,
    request_id_middleware,
)


_UUID_HEX_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class _FakeRequest:
    """aiohttp.web.Request minimal dict-like fake — req[k] = v + req.headers.get."""

    def __init__(self, *, request_id_header: str = "") -> None:
        self.scope: dict[str, Any] = {}
        self._headers = {"X-Request-ID": request_id_header}

    @property
    def headers(self) -> Any:
        class _H:
            def __init__(self, data: dict[str, str]) -> None:
                self._data = data

            def get(self, key: str, default: str = "") -> str:
                return self._data.get(key, default)

        return _H(self._headers)

    def __setitem__(self, key: str, value: Any) -> None:
        self.scope[key] = value

    def __getitem__(self, key: str) -> Any:
        return self.scope[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.scope.get(key, default)


def _make_request(*, request_id_header: str = "") -> Any:
    return _FakeRequest(request_id_header=request_id_header)


def _make_response() -> Any:
    response = MagicMock()
    response.headers = {}
    return response


class TestRequestIDGeneration:
    """nginx 의 X-Request-ID 의 propagation + fallback uuid4."""

    @pytest.mark.asyncio
    async def test_incoming_header_used(self) -> None:
        captured: dict[str, str] = {}

        async def handler(req: Any) -> Any:
            captured["request_id"] = get_request_id() or ""
            captured["scope"] = req.scope.get("request_id", "")
            return _make_response()

        req = _make_request(request_id_header="trace-abc-123")
        await request_id_middleware(req, handler)
        assert captured["request_id"] == "trace-abc-123"
        assert captured["scope"] == "trace-abc-123"

    @pytest.mark.asyncio
    async def test_missing_header_generates_uuid(self) -> None:
        captured: dict[str, str] = {}

        async def handler(req: Any) -> Any:
            captured["request_id"] = get_request_id() or ""
            return _make_response()

        req = _make_request(request_id_header="")
        await request_id_middleware(req, handler)
        # 한글 주석: uuid4 hex 32자 + 0-9a-f
        assert _UUID_HEX_PATTERN.match(captured["request_id"])

    @pytest.mark.asyncio
    async def test_whitespace_header_treated_as_missing(self) -> None:
        captured: dict[str, str] = {}

        async def handler(req: Any) -> Any:
            captured["request_id"] = get_request_id() or ""
            return _make_response()

        req = _make_request(request_id_header="   ")
        await request_id_middleware(req, handler)
        assert _UUID_HEX_PATTERN.match(captured["request_id"])


class TestResponseHeaderEcho:
    """response 의 X-Request-ID echo back — 클라이언트 trace 가능."""

    @pytest.mark.asyncio
    async def test_response_header_echoed(self) -> None:
        response = _make_response()

        async def handler(req: Any) -> Any:
            return response

        req = _make_request(request_id_header="echo-id-456")
        result = await request_id_middleware(req, handler)
        assert result.headers["X-Request-ID"] == "echo-id-456"

    @pytest.mark.asyncio
    async def test_generated_id_echoed(self) -> None:
        response = _make_response()

        async def handler(req: Any) -> Any:
            return response

        req = _make_request()
        result = await request_id_middleware(req, handler)
        assert _UUID_HEX_PATTERN.match(result.headers["X-Request-ID"])


class TestContextVarIsolation:
    """async task 별 contextvar 의 격리 의무."""

    @pytest.mark.asyncio
    async def test_concurrent_tasks_isolated(self) -> None:
        # 한글 주석: 2 task 의 동시 middleware 실행 — 각자 의 request_id 의 격리.
        captured: dict[str, str] = {}

        async def handler(req: Any) -> Any:
            # delay 의 inter-task race 의 노출
            await asyncio.sleep(0.001)
            tag = req.scope["tag"]
            captured[tag] = get_request_id() or ""
            return _make_response()

        async def run(tag: str, header: str) -> None:
            req = _make_request(request_id_header=header)
            req.scope["tag"] = tag
            await request_id_middleware(req, handler)

        await asyncio.gather(
            run("task-A", "id-aaa"),
            run("task-B", "id-bbb"),
        )
        assert captured["task-A"] == "id-aaa"
        assert captured["task-B"] == "id-bbb"

    @pytest.mark.asyncio
    async def test_after_middleware_context_cleared(self) -> None:
        async def handler(req: Any) -> Any:
            return _make_response()

        req = _make_request(request_id_header="cleanup-test")
        await request_id_middleware(req, handler)
        # 한글 주석: middleware 종료 후 contextvar reset 검증 (finally block)
        assert get_request_id() is None


class TestGetRequestIDOutsideMiddleware:
    def test_outside_returns_none(self) -> None:
        # 한글 주석: middleware 외 호출 = default None
        assert current_request_id.get() is None
        assert get_request_id() is None
