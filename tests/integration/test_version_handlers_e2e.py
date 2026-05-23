# SPDX-License-Identifier: GPL-3.0-or-later
"""version handlers chain E2E — cycle 169.695 신설.

chain:
1. get_latest 400 — platform invalid
2. get_latest 503 — pool 부재
3. get_latest 404 — no version
4. get_latest 200 — row return
5. get_latest 500 — internal exception
6. post_release 401 — admin token unset
7. post_release 401 — Bearer missing
8. post_release 401 — token mismatch
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.version_handlers import handle_get_latest, handle_post_release


pytestmark = pytest.mark.integration

ADMIN_TOKEN = "v-admin-1234"


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        method: str = "GET",
        query: dict | None = None,
        token: str | None = None,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = method
        self.headers = {}
        if token is not None:
            self.headers["Authorization"] = f"Bearer {token}"
        self.match_info = {}
        self.query = query or {}
        self._body = body

    async def json(self) -> dict:
        if self._body is None:
            raise ValueError("body 부재")
        return self._body


class TestGetLatest:
    @pytest.mark.asyncio
    async def test_invalid_platform_400(self) -> None:
        app = web.Application()
        req = _FakeRequest(app, query={"platform": "freebsd"})
        resp = await handle_get_latest(req)
        assert resp.status == 400
        assert "platform invalid" in json.loads(resp.body)["error"]

    @pytest.mark.asyncio
    async def test_pool_absent_503(self) -> None:
        app = web.Application()
        req = _FakeRequest(app, query={"platform": "macos-arm64"})
        resp = await handle_get_latest(req)
        assert resp.status == 503

    @pytest.mark.asyncio
    async def test_no_version_404(self, monkeypatch) -> None:
        app = web.Application()
        app["db_pool"] = MagicMock()
        monkeypatch.setattr(
            "server.api.version_handlers.get_latest_by_platform",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest(app, query={"platform": "macos-arm64"})
        resp = await handle_get_latest(req)
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_version_returned(self, monkeypatch) -> None:
        app = web.Application()
        app["db_pool"] = MagicMock()
        row = SimpleNamespace(
            version="1.2.3", platform=SimpleNamespace(value="macos-arm64"),
            zip_url="https://x/y.zip", sha256="a" * 64, file_size=12345,
            min_compatible_version="1.0.0",
            released_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
            release_notes="notes", is_latest=True,
        )
        monkeypatch.setattr(
            "server.api.version_handlers.get_latest_by_platform",
            AsyncMock(return_value=row),
        )
        req = _FakeRequest(app, query={"platform": "macos-arm64"})
        resp = await handle_get_latest(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["version"] == "1.2.3"
        assert data["sha256"] == "a" * 64

    @pytest.mark.asyncio
    async def test_internal_exception_500(self, monkeypatch) -> None:
        app = web.Application()
        app["db_pool"] = MagicMock()
        monkeypatch.setattr(
            "server.api.version_handlers.get_latest_by_platform",
            AsyncMock(side_effect=RuntimeError("db boom")),
        )
        req = _FakeRequest(app, query={"platform": "macos-arm64"})
        resp = await handle_get_latest(req)
        assert resp.status == 500


class TestPostRelease:
    @pytest.mark.asyncio
    async def test_unset_admin_token_401(self, monkeypatch) -> None:
        app = web.Application()
        monkeypatch.delenv("VERSION_ADMIN_TOKEN", raising=False)
        req = _FakeRequest(app, method="POST", token=ADMIN_TOKEN, body={})
        resp = await handle_post_release(req)
        assert resp.status == 401
        assert "VERSION_ADMIN_TOKEN unset" in json.loads(resp.body)["reason"]

    @pytest.mark.asyncio
    async def test_bearer_missing_401(self, monkeypatch) -> None:
        app = web.Application()
        monkeypatch.setenv("VERSION_ADMIN_TOKEN", ADMIN_TOKEN)
        req = _FakeRequest(app, method="POST", body={})
        resp = await handle_post_release(req)
        assert resp.status == 401
        assert "Bearer header missing" in json.loads(resp.body)["reason"]

    @pytest.mark.asyncio
    async def test_token_mismatch_401(self, monkeypatch) -> None:
        app = web.Application()
        monkeypatch.setenv("VERSION_ADMIN_TOKEN", ADMIN_TOKEN)
        req = _FakeRequest(app, method="POST", token="wrong-token", body={})
        resp = await handle_post_release(req)
        assert resp.status == 401
        assert "token mismatch" in json.loads(resp.body)["reason"]
