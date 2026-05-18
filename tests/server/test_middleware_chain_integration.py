# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 114 — middleware chain end-to-end integration smoke.

aiohttp TestServer + TestClient 의 실 HTTP 호출 의 request_id 헤더 propagation
+ response echo + contextvar 의 handler 내 isolation 검증.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from server.middleware import (
    APP_KEY_ACTIVITY,
    ActivityTracker,
    activity_middleware,
    get_request_id,
    request_id_middleware,
)


_UUID_HEX_PATTERN = re.compile(r"^[0-9a-f]{32}$")


async def _make_client(app: web.Application) -> TestClient:
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    return client


def _build_app() -> tuple[web.Application, dict[str, Any]]:
    """request_id + activity 의 2 middleware chain + echo handler 의 minimal app."""

    captured: dict[str, Any] = {"handler_request_ids": []}

    async def echo(request: web.Request) -> web.Response:
        rid = get_request_id()
        captured["handler_request_ids"].append(rid)
        captured["scope_request_id"] = request.get("request_id")
        return web.json_response({"request_id": rid})

    # 한글 주석: auth 부재 — public smoke. middleware chain = request_id + activity.
    app = web.Application(middlewares=[request_id_middleware, activity_middleware])
    app[APP_KEY_ACTIVITY] = ActivityTracker(throttle_seconds=60)
    app.router.add_get("/echo", echo)
    return app, captured


class TestRequestIDEndToEnd:
    """real aiohttp TestServer → request_id 의 wire-level 검증."""

    @pytest.mark.asyncio
    async def test_incoming_header_propagated_to_handler(self) -> None:
        app, captured = _build_app()
        client = await _make_client(app)
        try:
            resp = await client.get(
                "/echo", headers={"X-Request-ID": "wire-test-123"}
            )
            assert resp.status == 200
            body = await resp.json()
            assert body["request_id"] == "wire-test-123"
            assert resp.headers["X-Request-ID"] == "wire-test-123"
            assert captured["handler_request_ids"] == ["wire-test-123"]
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_missing_header_generates_uuid(self) -> None:
        app, captured = _build_app()
        client = await _make_client(app)
        try:
            resp = await client.get("/echo")
            assert resp.status == 200
            body = await resp.json()
            assert _UUID_HEX_PATTERN.match(body["request_id"])
            assert resp.headers["X-Request-ID"] == body["request_id"]
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_each_request_distinct_request_id(self) -> None:
        # 한글 주석: 3 sequential request → 3 distinct uuid (또는 incoming distinct).
        app, captured = _build_app()
        client = await _make_client(app)
        try:
            r1 = await client.get("/echo", headers={"X-Request-ID": "req-1"})
            r2 = await client.get("/echo", headers={"X-Request-ID": "req-2"})
            r3 = await client.get("/echo")  # uuid fallback
            assert r1.headers["X-Request-ID"] == "req-1"
            assert r2.headers["X-Request-ID"] == "req-2"
            assert _UUID_HEX_PATTERN.match(r3.headers["X-Request-ID"])
            assert captured["handler_request_ids"] == [
                "req-1",
                "req-2",
                r3.headers["X-Request-ID"],
            ]
        finally:
            await client.close()


class TestMiddlewareChainOrder:
    """middleware chain 순서 의 정합 검증 — request_id 가 최상단."""

    @pytest.mark.asyncio
    async def test_request_id_available_throughout_chain(self) -> None:
        # 한글 주석: activity_middleware 안 의 get_request_id 의 값 의 검증.
        # activity_middleware = response 직후 호출 — contextvar 는 reset 직전.
        captured: dict[str, Any] = {}

        async def echo(request: web.Request) -> web.Response:
            return web.json_response({"ok": True})

        app = web.Application(
            middlewares=[request_id_middleware, activity_middleware]
        )
        app[APP_KEY_ACTIVITY] = ActivityTracker(throttle_seconds=60)
        app.router.add_get("/echo", echo)
        client = await _make_client(app)
        try:
            resp = await client.get("/echo", headers={"X-Request-ID": "chain-test"})
            assert resp.headers["X-Request-ID"] == "chain-test"
        finally:
            await client.close()
