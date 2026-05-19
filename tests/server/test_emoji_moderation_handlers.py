# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 cycle 144 — emoji moderation 4 endpoint admin Bearer + UPDATE 검증.

cycle 132 의 emoji_handlers (skeleton 5 endpoint) follow-up — admin
moderation 4 endpoint 의 401 분기 + UPDATE SQL call_args 정밀 검증.

5 test:
- TestQueueAuth.test_queue_returns_401_when_bearer_absent
- TestApproveAuth.test_approve_returns_401_when_token_mismatch
- TestApproveSuccess.test_approve_returns_200_when_token_matches
- TestRejectUpdateSQL.test_reject_invokes_update_with_correct_enum
- TestDmcaInvalidBody.test_dmca_returns_400_when_pack_id_missing
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from server.api.emoji_moderation_handlers import register_emoji_moderation_routes


def _mock_pool_capture_update() -> tuple[Any, MagicMock]:
    """한글 주석 — UPDATE execute call_args capture 가능한 mock pool + cursor 반환."""

    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = 0
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
    """aiohttp TestServer + TestClient builder — cycle 132 / 134 정합."""

    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    return client


class TestQueueAuth:
    """GET /api/emoji/moderation/queue admin Bearer 검증."""

    @pytest.mark.asyncio
    async def test_queue_returns_401_when_bearer_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석: EMOJI_MODERATION_ADMIN_TOKEN env 정합 + Bearer 부재 → 401
        monkeypatch.setenv("EMOJI_MODERATION_ADMIN_TOKEN", "secret-emoji-admin")

        pool, _ = _mock_pool_capture_update()
        app = web.Application()
        register_emoji_moderation_routes(app)
        app["db_pool"] = pool

        client = await _make_client(app)
        try:
            resp = await client.get("/api/emoji/moderation/queue")
            assert resp.status == 401
            body = await resp.json()
            assert body["error"] == "admin only"
            assert "Bearer header missing" in body.get("reason", "")
        finally:
            await client.close()


class TestApproveAuth:
    """POST /api/emoji/moderation/approve 잘못된 token 401."""

    @pytest.mark.asyncio
    async def test_approve_returns_401_when_token_mismatch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석: env 정합 + 잘못된 Bearer → 401 + reason=token mismatch
        monkeypatch.setenv("EMOJI_MODERATION_ADMIN_TOKEN", "secret-emoji-admin")

        pool, _ = _mock_pool_capture_update()
        app = web.Application()
        register_emoji_moderation_routes(app)
        app["db_pool"] = pool

        client = await _make_client(app)
        try:
            resp = await client.post(
                "/api/emoji/moderation/approve",
                headers={"Authorization": "Bearer WRONG-TOKEN"},
                json={"pack_id": 42},
            )
            assert resp.status == 401
            body = await resp.json()
            assert body["error"] == "admin only"
            assert "token mismatch" in body.get("reason", "")
        finally:
            await client.close()


class TestApproveSuccess:
    """POST /api/emoji/moderation/approve 정합 token + pack_id → 200."""

    @pytest.mark.asyncio
    async def test_approve_returns_200_when_token_matches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석: env + Bearer + pack_id 의무 → 200 + rowcount=1
        monkeypatch.setenv("EMOJI_MODERATION_ADMIN_TOKEN", "secret-emoji-admin")

        pool, _cursor = _mock_pool_capture_update()
        app = web.Application()
        register_emoji_moderation_routes(app)
        app["db_pool"] = pool

        client = await _make_client(app)
        try:
            resp = await client.post(
                "/api/emoji/moderation/approve",
                headers={"Authorization": "Bearer secret-emoji-admin"},
                json={"pack_id": 42},
            )
            assert resp.status == 200
            body = await resp.json()
            assert body["ok"] is True
            assert body["pack_id"] == 42
            assert body["moderation_status"] == "approved"
            assert body["rowcount"] == 1
        finally:
            await client.close()


class TestRejectUpdateSQL:
    """POST /api/emoji/moderation/reject — UPDATE call_args 정합 검증."""

    @pytest.mark.asyncio
    async def test_reject_invokes_update_with_correct_enum(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석: reject endpoint → UPDATE 의 params=('rejected', pack_id) 의무
        monkeypatch.setenv("EMOJI_MODERATION_ADMIN_TOKEN", "secret-emoji-admin")

        pool, cursor = _mock_pool_capture_update()
        app = web.Application()
        register_emoji_moderation_routes(app)
        app["db_pool"] = pool

        client = await _make_client(app)
        try:
            resp = await client.post(
                "/api/emoji/moderation/reject",
                headers={"Authorization": "Bearer secret-emoji-admin"},
                json={"pack_id": 7},
            )
            assert resp.status == 200
            body = await resp.json()
            assert body["moderation_status"] == "rejected"

            # 한글 주석: cursor.execute 의 last call SQL + params tuple 검증
            assert cursor.execute.await_count >= 1
            call_args = cursor.execute.await_args
            sql = call_args.args[0]
            params = call_args.args[1]
            # parameterized 의무 (injection 차단)
            assert "UPDATE emoji_packs" in sql
            assert "%s" in sql
            # params 순서 = (moderation_status, pack_id) 정합
            assert params[0] == "rejected"
            assert params[1] == 7
        finally:
            await client.close()


class TestDmcaInvalidBody:
    """POST /api/emoji/moderation/dmca — pack_id 부재 → 400."""

    @pytest.mark.asyncio
    async def test_dmca_returns_400_when_pack_id_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석: pack_id 부재 body → 400 reason="pack_id 양수 정수 의무"
        monkeypatch.setenv("EMOJI_MODERATION_ADMIN_TOKEN", "secret-emoji-admin")

        pool, _ = _mock_pool_capture_update()
        app = web.Application()
        register_emoji_moderation_routes(app)
        app["db_pool"] = pool

        client = await _make_client(app)
        try:
            resp = await client.post(
                "/api/emoji/moderation/dmca",
                headers={"Authorization": "Bearer secret-emoji-admin"},
                json={},  # pack_id 부재
            )
            assert resp.status == 400
            body = await resp.json()
            assert "pack_id" in body["error"]
        finally:
            await client.close()
