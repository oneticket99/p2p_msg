# SPDX-License-Identifier: GPL-3.0-or-later
"""peers repo + remote_handlers e2e — cycle 169.763 신설.

peers(insert/leave/list) mock pool + remote_handlers(request/grant/revoke +
_audit_remote pool 분기) _FakeRequest. 잔존 cov gap 회수.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_pool(*, fetchall=None, lastrowid=1) -> MagicMock:
    # 한글 주석 — acquire + cursor 2단 async context 모킹
    pool = MagicMock()
    cur = MagicMock()
    cur.execute = AsyncMock(return_value=None)
    cur.fetchall = AsyncMock(return_value=fetchall or [])
    cur.lastrowid = lastrowid
    cur_ctx = MagicMock()
    cur_ctx.__aenter__ = AsyncMock(return_value=cur)
    cur_ctx.__aexit__ = AsyncMock(return_value=None)
    conn = MagicMock()
    conn.cursor = MagicMock(return_value=cur_ctx)
    conn.commit = AsyncMock(return_value=None)
    conn_ctx = MagicMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn)
    conn_ctx.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=conn_ctx)
    return pool


_TS = datetime(2026, 5, 24, tzinfo=timezone.utc)


# ─── peers repo ─────────────────────────────────────────────────────────────

class TestPeersRepo:
    @pytest.mark.asyncio
    async def test_insert_peer_returns_id(self) -> None:
        from server.db.repositories.peers import insert_peer

        assert await insert_peer(_build_pool(lastrowid=5), room_id=100, user_id=10) == 5

    @pytest.mark.asyncio
    async def test_insert_peer_owner_role(self) -> None:
        from server.db.repositories.peers import insert_peer

        assert await insert_peer(_build_pool(lastrowid=6),
                                 room_id=100, user_id=10, role="owner") == 6

    @pytest.mark.asyncio
    async def test_mark_peer_left_commits(self) -> None:
        from server.db.repositories.peers import mark_peer_left

        pool = _build_pool()
        await mark_peer_left(pool, 100, 10)
        conn = await pool.acquire().__aenter__()
        conn.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_list_active_peers(self) -> None:
        from server.db.repositories.peers import PeerRow, list_active_peers

        row = (1, 100, 10, "owner", _TS, None)
        rows = await list_active_peers(_build_pool(fetchall=[row]), 100)
        assert len(rows) == 1 and isinstance(rows[0], PeerRow)
        assert rows[0].role == "owner" and rows[0].left_at is None

    @pytest.mark.asyncio
    async def test_list_active_peers_empty(self) -> None:
        from server.db.repositories.peers import list_active_peers

        assert await list_active_peers(_build_pool(fetchall=[]), 999) == []


# ─── remote_handlers e2e ────────────────────────────────────────────────────

class _FakeRequest:
    """aiohttp Request mock — user_id + json body + db_pool + headers."""

    def __init__(self, *, user_id=7, body=None, pool=None) -> None:
        self._user_id = user_id
        self._body = body if body is not None else {}
        self.content_length = 1 if body else 0
        self.headers = {"User-Agent": "pytest-agent"}
        self.app = {"db_pool": pool} if pool is not None else {}
        # 한글 주석 — extract_client_ip 가 참조하는 속성 graceful
        self.remote = "127.0.0.1"
        self.transport = None

    def get(self, key, default=None):  # noqa: ANN001
        return self._user_id if key == "user_id" else default

    async def json(self):
        return self._body


def _patch_audit(monkeypatch, *, raise_exc=False):
    # 한글 주석 — log_activity + extract_client_ip patch (실 asyncmy 차단)
    import server.api.remote_handlers as rh

    calls = []

    async def _fake_log(*args, **kwargs):
        calls.append(kwargs)
        if raise_exc:
            raise RuntimeError("audit fail mock")

    monkeypatch.setattr(rh, "log_activity", _fake_log)
    monkeypatch.setattr(rh, "extract_client_ip", lambda req: "127.0.0.1")
    return calls


class TestRemoteRequest:
    @pytest.mark.asyncio
    async def test_request_pending_with_pool_audit(self, monkeypatch) -> None:
        import json as _json

        from server.api.remote_handlers import handle_remote_request

        calls = _patch_audit(monkeypatch)
        req = _FakeRequest(body={"target_user_id": 20, "pattern": "control"}, pool=_build_pool())
        resp = await handle_remote_request(req)
        assert resp.status == 200
        body = _json.loads(resp.body.decode())
        assert body == {"ok": True, "status": "pending", "pattern": "control"}
        assert len(calls) == 1  # audit fired (pool present)

    @pytest.mark.asyncio
    async def test_request_pool_none_skips_audit(self, monkeypatch) -> None:
        from server.api.remote_handlers import handle_remote_request

        calls = _patch_audit(monkeypatch)
        req = _FakeRequest(body={"target_user_id": 20}, pool=None)
        resp = await handle_remote_request(req)
        assert resp.status == 200
        assert calls == []  # pool None → early return


class TestRemoteGrant:
    @pytest.mark.asyncio
    async def test_grant_granted(self, monkeypatch) -> None:
        import json as _json

        from server.api.remote_handlers import handle_remote_grant

        _patch_audit(monkeypatch)
        req = _FakeRequest(body={"request_id": 42, "requester_user_id": 5}, pool=_build_pool())
        resp = await handle_remote_grant(req)
        body = _json.loads(resp.body.decode())
        assert body == {"ok": True, "status": "granted", "request_id": 42}


class TestRemoteRevoke:
    @pytest.mark.asyncio
    async def test_revoke_revoked(self, monkeypatch) -> None:
        import json as _json

        from server.api.remote_handlers import handle_remote_revoke

        _patch_audit(monkeypatch)
        req = _FakeRequest(body={"session_id": 99, "target_user_id": 20}, pool=_build_pool())
        resp = await handle_remote_revoke(req)
        body = _json.loads(resp.body.decode())
        assert body == {"ok": True, "status": "revoked", "session_id": 99}

    @pytest.mark.asyncio
    async def test_audit_exception_swallowed(self, monkeypatch) -> None:
        # 한글 주석 — log_activity 예외 → endpoint 200 유지 (graceful swallow)
        from server.api.remote_handlers import handle_remote_revoke

        _patch_audit(monkeypatch, raise_exc=True)
        req = _FakeRequest(body={"session_id": 1}, pool=_build_pool())
        resp = await handle_remote_revoke(req)
        assert resp.status == 200


class TestRegisterRoutes:
    def test_register_remote_routes(self) -> None:
        from aiohttp import web

        from server.api.remote_handlers import register_remote_routes

        app = web.Application()
        register_remote_routes(app)
        paths = {r.resource.canonical for r in app.router.routes()}
        assert "/api/remote/request" in paths
        assert "/api/remote/grant" in paths
        assert "/api/remote/revoke" in paths
