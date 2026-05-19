# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 cycle 132 — version_handlers 의 GET latest + POST release 검증.

엔드포인트 5 test:
- TestGetLatest — 200 success / 404 platform 의 부재 / pool None graceful 503
- TestPostRelease — 401 admin token 부재 / 200 admin token 정합

본 test = unit-level aiohttp TestServer + asyncmy mock pool. 실 DB / GitHub
Release 연동 = 별개 cycle 의 integration test.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from server.api.version_handlers import register_version_routes
from server.db.repositories.app_versions import AppVersionRow, Platform


def _mock_pool_with_latest_row(row: AppVersionRow | None) -> Any:
    """한글 주석 — get_latest_by_platform 의 SELECT fetchone mock pool."""

    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = 99
    cursor.rowcount = 1

    if row is None:
        cursor.fetchone = AsyncMock(return_value=None)
    else:
        cursor.fetchone = AsyncMock(
            return_value=(
                row.id,
                row.version,
                row.platform.value,
                row.zip_url,
                row.sha256,
                row.file_size,
                row.min_compatible_version,
                row.released_at,
                row.release_notes,
                1 if row.is_latest else 0,
            )
        )

    @asynccontextmanager
    async def cursor_cm() -> Any:
        yield cursor

    conn = MagicMock()
    conn.cursor = lambda: cursor_cm()
    conn.commit = AsyncMock()

    @asynccontextmanager
    async def acquire_cm() -> Any:
        yield conn

    pool = MagicMock()
    pool.acquire = lambda: acquire_cm()
    return pool


async def _make_client(app: web.Application) -> TestClient:
    """한글 주석 — aiohttp TestServer + TestClient builder."""

    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    return client


class TestGetLatest:
    """GET /api/version/latest 의 3 분기 검증."""

    @pytest.mark.asyncio
    async def test_returns_200_with_latest_row(self) -> None:
        # 한글 주석: pool 가용 + latest row 의 200 응답 + JSON 정합
        from datetime import datetime

        row = AppVersionRow(
            id=1,
            version="0.5.0-phase5",
            platform=Platform.MACOS_ARM64,
            zip_url="https://github.com/oneticket99/p2p_msg/releases/download/v0.5.0/TooTalk-macos-arm64.zip",
            sha256="a" * 64,
            file_size=12345678,
            min_compatible_version="0.4.0",
            released_at=datetime(2026, 5, 19, 12, 0, 0),
            release_notes="자동 업데이트 신설",
            is_latest=True,
        )
        app = web.Application()
        register_version_routes(app)
        app["db_pool"] = _mock_pool_with_latest_row(row)

        client = await _make_client(app)
        try:
            resp = await client.get("/api/version/latest?platform=macos-arm64")
            assert resp.status == 200
            body = await resp.json()
            assert body["version"] == "0.5.0-phase5"
            assert body["platform"] == "macos-arm64"
            assert body["sha256"] == "a" * 64
            assert body["zip_url"].startswith("https://")
            assert body["release_notes"] == "자동 업데이트 신설"
            assert body["is_latest"] is True
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_returns_404_when_platform_not_found(self) -> None:
        # 한글 주석: pool 가용 + row 부재 의 404
        app = web.Application()
        register_version_routes(app)
        app["db_pool"] = _mock_pool_with_latest_row(None)

        client = await _make_client(app)
        try:
            resp = await client.get("/api/version/latest?platform=linux-x64")
            assert resp.status == 404
            body = await resp.json()
            assert body["error"] == "no version"
            assert body["platform"] == "linux-x64"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_returns_503_when_pool_none_graceful(self) -> None:
        # 한글 주석: pool None — DB_ENABLED=0 dev 의 graceful 503
        app = web.Application()
        register_version_routes(app)
        # db_pool 미설정 = None 등가

        client = await _make_client(app)
        try:
            resp = await client.get("/api/version/latest?platform=windows-x64")
            assert resp.status == 503
            body = await resp.json()
            assert body["error"] == "db unavailable"
        finally:
            await client.close()


class TestPostRelease:
    """POST /api/version/release 의 admin Bearer 검증."""

    @pytest.mark.asyncio
    async def test_returns_401_when_admin_token_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석: VERSION_ADMIN_TOKEN env 부재 — 401 fallback
        monkeypatch.delenv("VERSION_ADMIN_TOKEN", raising=False)

        app = web.Application()
        register_version_routes(app)
        app["db_pool"] = _mock_pool_with_latest_row(None)

        client = await _make_client(app)
        try:
            resp = await client.post(
                "/api/version/release",
                json={
                    "version": "0.5.1",
                    "platform": "macos-arm64",
                    "zip_url": "https://example.com/a.zip",
                    "sha256": "b" * 64,
                },
            )
            assert resp.status == 401
            body = await resp.json()
            assert body["error"] == "admin only"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_returns_200_when_admin_token_matches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석: VERSION_ADMIN_TOKEN env + Bearer 일치 — 200 INSERT
        monkeypatch.setenv("VERSION_ADMIN_TOKEN", "secret-admin-xyz")

        app = web.Application()
        register_version_routes(app)
        app["db_pool"] = _mock_pool_with_latest_row(None)

        client = await _make_client(app)
        try:
            resp = await client.post(
                "/api/version/release",
                headers={"Authorization": "Bearer secret-admin-xyz"},
                json={
                    "version": "0.5.1",
                    "platform": "macos-arm64",
                    "zip_url": "https://example.com/a.zip",
                    "sha256": "c" * 64,
                    "file_size": 1024,
                    "release_notes": "패치 1",
                    "is_latest": True,
                },
            )
            assert resp.status == 200
            body = await resp.json()
            assert body["ok"] is True
            assert body["id"] == 99  # mock lastrowid
        finally:
            await client.close()
