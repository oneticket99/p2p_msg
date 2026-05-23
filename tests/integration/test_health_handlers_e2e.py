# SPDX-License-Identifier: GPL-3.0-or-later
"""health + ready endpoint chain E2E — cycle 169.712 신설.

chain:
1. healthz 200 + status=ok 항상
2. readyz 200 + status=degraded (all absent)
3. readyz 200 + status=ok (all present)
4. readyz checks dict 4 key
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from aiohttp import web

from server.api.health_handlers import handle_healthz, handle_readyz


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(self, app: web.Application) -> None:
        self.app = app
        self.method = "GET"
        self.headers = {}
        self.match_info = {}


class TestHealthz:
    @pytest.mark.asyncio
    async def test_always_ok(self) -> None:
        app = web.Application()
        req = _FakeRequest(app)
        resp = await handle_healthz(req)
        assert resp.status == 200
        assert json.loads(resp.body)["status"] == "ok"


class TestReadyz:
    @pytest.mark.asyncio
    async def test_all_absent_degraded(self) -> None:
        # 한글 주석 — db_pool + provider + activity + config 모두 absent
        app = web.Application()
        req = _FakeRequest(app)
        resp = await handle_readyz(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["status"] == "degraded"
        # 한글 주석 — 4 check key
        assert "db_pool" in data["checks"]
        assert "bot_provider" in data["checks"]
        assert "activity_tracker" in data["checks"]
        assert "config" in data["checks"]

    @pytest.mark.asyncio
    async def test_db_pool_present_partial(self) -> None:
        app = web.Application()
        app["db_pool"] = MagicMock()
        req = _FakeRequest(app)
        resp = await handle_readyz(req)
        data = json.loads(resp.body)
        assert data["checks"]["db_pool"] == "ok"

    @pytest.mark.asyncio
    async def test_all_present_ok(self) -> None:
        from server.api.bot_handlers import APP_KEY_PROVIDER
        from server.middleware.activity import APP_KEY_ACTIVITY

        app = web.Application()
        app["db_pool"] = MagicMock()
        app[APP_KEY_PROVIDER] = MagicMock()
        app[APP_KEY_ACTIVITY] = MagicMock()
        app["config"] = MagicMock()
        req = _FakeRequest(app)
        resp = await handle_readyz(req)
        data = json.loads(resp.body)
        assert data["status"] == "ok"
        assert all(v == "ok" for v in data["checks"].values())
