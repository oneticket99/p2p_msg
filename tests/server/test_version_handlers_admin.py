# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 cycle 134 — POST /api/version/release admin Bearer + INSERT SQL 검증.

cycle 132 의 base test (`test_version_handlers.py`) 의 401/200 분기 보강 — Bearer
부재 / 잘못된 token / 정합 token + INSERT SQL call_args 의 정밀 검증.

4 test (TestPostReleaseAuth 3 + TestPostReleaseInsertSQL 1):
- TestPostReleaseAuth.test_returns_401_when_bearer_absent — Bearer 헤더 누락 401
- TestPostReleaseAuth.test_returns_401_when_token_mismatch — 잘못된 token 401
- TestPostReleaseAuth.test_returns_200_when_token_matches — 정합 token 200
- TestPostReleaseInsertSQL.test_insert_sql_call_args_match_payload — INSERT call_args 정합
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from server.api.version_handlers import register_version_routes


def _mock_pool_capture_insert() -> tuple[Any, MagicMock]:
    """한글 주석 — INSERT execute 의 call_args capture 가능한 mock pool + cursor 반환."""

    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = 42
    cursor.rowcount = 1
    cursor.fetchone = AsyncMock(return_value=None)

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
    return pool, cursor


async def _make_client(app: web.Application) -> TestClient:
    """한글 주석 — aiohttp TestServer + TestClient builder (cycle 132 정합)."""

    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    return client


class TestPostReleaseAuth:
    """POST /api/version/release admin Bearer 3 분기 검증."""

    @pytest.mark.asyncio
    async def test_returns_401_when_bearer_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석: VERSION_ADMIN_TOKEN env 정합 + Bearer 헤더 부재 → 401
        monkeypatch.setenv("VERSION_ADMIN_TOKEN", "secret-admin-xyz")

        pool, _cursor = _mock_pool_capture_insert()
        app = web.Application()
        register_version_routes(app)
        app["db_pool"] = pool

        client = await _make_client(app)
        try:
            resp = await client.post(
                "/api/version/release",
                json={
                    "version": "v0.5.0-phase5",
                    "platform": "macos-arm64",
                    "zip_url": "https://example.com/a.zip",
                    "sha256": "a" * 64,
                },
            )
            assert resp.status == 401
            body = await resp.json()
            assert body["error"] == "admin only"
            assert "Bearer header missing" in body.get("reason", "")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_returns_401_when_token_mismatch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석: VERSION_ADMIN_TOKEN env 정합 + Bearer 헤더 잘못된 token → 401
        monkeypatch.setenv("VERSION_ADMIN_TOKEN", "secret-admin-xyz")

        pool, _cursor = _mock_pool_capture_insert()
        app = web.Application()
        register_version_routes(app)
        app["db_pool"] = pool

        client = await _make_client(app)
        try:
            resp = await client.post(
                "/api/version/release",
                headers={"Authorization": "Bearer WRONG-TOKEN-VALUE"},
                json={
                    "version": "v0.5.0-phase5",
                    "platform": "macos-arm64",
                    "zip_url": "https://example.com/a.zip",
                    "sha256": "b" * 64,
                },
            )
            assert resp.status == 401
            body = await resp.json()
            assert body["error"] == "admin only"
            assert "token mismatch" in body.get("reason", "")
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_returns_200_when_token_matches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석: VERSION_ADMIN_TOKEN env 정합 + Bearer 헤더 정합 token → 200 + lastrowid
        monkeypatch.setenv("VERSION_ADMIN_TOKEN", "secret-admin-xyz")

        pool, _cursor = _mock_pool_capture_insert()
        app = web.Application()
        register_version_routes(app)
        app["db_pool"] = pool

        client = await _make_client(app)
        try:
            resp = await client.post(
                "/api/version/release",
                headers={"Authorization": "Bearer secret-admin-xyz"},
                json={
                    "version": "v0.5.0-phase5",
                    "platform": "macos-arm64",
                    "zip_url": "https://github.com/oneticket99/p2p_msg/releases/download/v0.5.0-phase5/TooTalk-macos-arm64.zip",
                    "sha256": "c" * 64,
                    "file_size": 12345678,
                    "is_latest": True,
                },
            )
            assert resp.status == 200
            body = await resp.json()
            assert body["ok"] is True
            assert body["id"] == 42  # mock lastrowid 정합
        finally:
            await client.close()


class TestPostReleaseInsertSQL:
    """INSERT SQL 의 call_args 정밀 검증 (payload 의 정합 + parameterized 차단)."""

    @pytest.mark.asyncio
    async def test_insert_sql_call_args_match_payload(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석: POST payload 의 각 field → INSERT SQL 의 params tuple 정합
        monkeypatch.setenv("VERSION_ADMIN_TOKEN", "secret-admin-xyz")

        pool, cursor = _mock_pool_capture_insert()
        app = web.Application()
        register_version_routes(app)
        app["db_pool"] = pool

        client = await _make_client(app)
        try:
            payload = {
                "version": "v0.5.0-phase5",
                "platform": "macos-arm64",
                "zip_url": "https://example.com/TooTalk-macos-arm64.zip",
                "sha256": "d" * 64,
                "file_size": 9876543,
                "min_compatible_version": "0.4.0",
                "release_notes": "자동 업데이트 신설",
                "is_latest": True,
            }
            resp = await client.post(
                "/api/version/release",
                headers={"Authorization": "Bearer secret-admin-xyz"},
                json=payload,
            )
            assert resp.status == 200

            # 한글 주석: cursor.execute 의 last call 의 SQL + params tuple 검증
            assert cursor.execute.await_count >= 1
            call_args = cursor.execute.await_args
            sql = call_args.args[0]
            params = call_args.args[1]

            # parameterized SQL 의 placeholder 의무 (injection 차단)
            assert "INSERT INTO app_versions" in sql
            assert "%s" in sql

            # params tuple 의 순서 정합 — repository.insert_version 정합
            # (version, platform, zip_url, sha256, file_size, min_compat, release_notes, is_latest)
            assert params[0] == "v0.5.0-phase5"
            assert params[1] == "macos-arm64"
            assert params[2] == payload["zip_url"]
            assert params[3] == ("d" * 64)
            assert params[4] == 9876543
            assert params[5] == "0.4.0"
            assert params[6] == "자동 업데이트 신설"
            assert params[7] == 1  # is_latest True → 1
        finally:
            await client.close()
