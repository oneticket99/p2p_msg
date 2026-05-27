# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 124 — health + readiness handler 검증.

handle_healthz (liveness) + handle_readyz (readiness + dependency check) +
PUBLIC_PATHS 정합 + aiohttp TestServer wire-level smoke.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from server.api.bot_handlers import APP_KEY_PROVIDER
from server.api.health_handlers import (
    handle_healthz,
    handle_readyz,
    register_health_routes,
)
from server.middleware.activity import APP_KEY_ACTIVITY, ActivityTracker


async def _make_client(app: web.Application) -> TestClient:
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    return client


class TestHealthz:
    @pytest.mark.asyncio
    async def test_returns_200_ok(self) -> None:
        app = web.Application()
        register_health_routes(app)
        client = await _make_client(app)
        try:
            resp = await client.get("/healthz")
            assert resp.status == 200
            body = await resp.json()
            assert body["status"] == "ok"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_no_dependency_check(self) -> None:
        # liveness = DB / 외부 의존성 검증 부재. 빈 app 도 200 OK.
        app = web.Application()
        register_health_routes(app)
        client = await _make_client(app)
        try:
            resp = await client.get("/healthz")
            assert resp.status == 200
        finally:
            await client.close()


class TestReadyz:
    @pytest.mark.asyncio
    async def test_all_dependencies_present(self) -> None:
        app = web.Application()
        register_health_routes(app)
        app["db_pool"] = object()  # not None
        app[APP_KEY_PROVIDER] = object()
        app[APP_KEY_ACTIVITY] = ActivityTracker(throttle_seconds=60)
        app["config"] = object()

        client = await _make_client(app)
        try:
            resp = await client.get("/readyz")
            assert resp.status == 200
            body = await resp.json()
            assert body["status"] == "ok"
            assert body["checks"]["db_pool"] == "ok"
            assert body["checks"]["bot_provider"] == "ok"
            assert body["checks"]["activity_tracker"] == "ok"
            assert body["checks"]["config"] == "ok"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_db_pool_absent_degraded(self) -> None:
        app = web.Application()
        register_health_routes(app)
        app[APP_KEY_ACTIVITY] = ActivityTracker(throttle_seconds=60)
        app["config"] = object()

        client = await _make_client(app)
        try:
            resp = await client.get("/readyz")
            assert resp.status == 200
            body = await resp.json()
            assert body["status"] == "degraded"
            assert body["checks"]["db_pool"] == "absent"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_all_absent_degraded(self) -> None:
        app = web.Application()
        register_health_routes(app)
        client = await _make_client(app)
        try:
            resp = await client.get("/readyz")
            assert resp.status == 200
            body = await resp.json()
            assert body["status"] == "degraded"
            assert body["checks"]["db_pool"] == "absent"
            assert body["checks"]["bot_provider"] == "absent"
            assert body["checks"]["activity_tracker"] == "absent"
            assert body["checks"]["config"] == "absent"
        finally:
            await client.close()


class TestRouteRegistration:
    def test_register_health_routes_adds_both(self) -> None:
        app = web.Application()
        register_health_routes(app)
        paths = {
            getattr(route.resource, "canonical", "") for route in app.router.routes()
        }
        assert "/healthz" in paths
        assert "/readyz" in paths


class TestPublicPathsBypass:
    """auth_middleware PUBLIC_PATHS bypass 정합."""

    def test_healthz_in_public_paths(self) -> None:
        from server.auth.middleware import _PUBLIC_PATHS

        assert "/healthz" in _PUBLIC_PATHS
        assert "/readyz" in _PUBLIC_PATHS
