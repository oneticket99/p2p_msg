# SPDX-License-Identifier: GPL-3.0-or-later
"""emoji moderation queue chain E2E — cycle 169.670 신설.

사용자 directive — emoji moderation queue (pending → approved/rejected/dmca).

chain:
1. POST moderation 401 — token unset
2. POST moderation 401 — Bearer missing
3. POST moderation 401 — token mismatch
4. POST moderation 400 — invalid status ENUM
5. POST moderation 404 — pack slug 부재
6. POST moderation 200 — approved transition
7. POST moderation 200 — rejected transition
8. POST moderation 200 — dmca_takedown transition
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.emoji_handlers import handle_moderation
from server.db.repositories.emoji_packs import EmojiPackRow, ModerationStatus


pytestmark = pytest.mark.integration

ADMIN_TOKEN = "sekret-admin-1234"


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        slug: str,
        token: str | None = ADMIN_TOKEN,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = "POST"
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.match_info = {"slug": slug}
        self.remote = "127.0.0.1"
        self._body = body or {}

    async def json(self) -> dict:
        return self._body


@pytest.fixture
def app_with_pool() -> web.Application:
    app = web.Application()
    app["db_pool"] = MagicMock()
    return app


@pytest.fixture(autouse=True)
def admin_env(monkeypatch) -> None:
    monkeypatch.setenv("EMOJI_MODERATION_ADMIN_TOKEN", ADMIN_TOKEN)


def _make_pack() -> EmojiPackRow:
    return EmojiPackRow(
        id=42, owner_user_id=10, name="Test", slug="test-pack",
        description="x", is_public=True,
        moderation_status=ModerationStatus("pending"), download_count=0,
    )


class TestModerationAuth:
    @pytest.mark.asyncio
    async def test_unset_admin_token_401(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — admin env 미설정 → 401
        monkeypatch.delenv("EMOJI_MODERATION_ADMIN_TOKEN", raising=False)
        req = _FakeRequest(app_with_pool, slug="test-pack", token=ADMIN_TOKEN,
                           body={"moderation_status": "approved"})
        resp = await handle_moderation(req)
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_bearer_missing_401(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, slug="test-pack", token=None,
                           body={"moderation_status": "approved"})
        resp = await handle_moderation(req)
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_token_mismatch_401(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, slug="test-pack", token="wrong",
                           body={"moderation_status": "approved"})
        resp = await handle_moderation(req)
        assert resp.status == 401


class TestModerationValidation:
    @pytest.mark.asyncio
    async def test_invalid_status_400(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, slug="test-pack",
                           body={"moderation_status": "invalid"})
        with pytest.raises(web.HTTPBadRequest, match="moderation_status"):
            await handle_moderation(req)

    @pytest.mark.asyncio
    async def test_pack_not_found_404(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.emoji_handlers._packs_repo.get_pack_by_slug",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest(app_with_pool, slug="missing",
                           body={"moderation_status": "approved"})
        with pytest.raises(web.HTTPNotFound):
            await handle_moderation(req)


class TestModerationTransitions:
    @pytest.mark.asyncio
    async def test_transition_approved(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.emoji_handlers._packs_repo.get_pack_by_slug",
            AsyncMock(return_value=_make_pack()),
        )
        update_mock = AsyncMock(return_value=1)
        monkeypatch.setattr(
            "server.api.emoji_handlers._packs_repo.update_moderation_status",
            update_mock,
        )

        req = _FakeRequest(app_with_pool, slug="test-pack",
                           body={"moderation_status": "approved"})
        resp = await handle_moderation(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["updated"] is True
        assert data["moderation_status"] == "approved"
        assert update_mock.await_args.kwargs["moderation_status"] == ModerationStatus.APPROVED

    @pytest.mark.asyncio
    async def test_transition_rejected(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.emoji_handlers._packs_repo.get_pack_by_slug",
            AsyncMock(return_value=_make_pack()),
        )
        monkeypatch.setattr(
            "server.api.emoji_handlers._packs_repo.update_moderation_status",
            AsyncMock(return_value=1),
        )

        req = _FakeRequest(app_with_pool, slug="test-pack",
                           body={"moderation_status": "rejected"})
        resp = await handle_moderation(req)
        assert resp.status == 200
        assert json.loads(resp.body)["moderation_status"] == "rejected"

    @pytest.mark.asyncio
    async def test_transition_dmca_takedown(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.emoji_handlers._packs_repo.get_pack_by_slug",
            AsyncMock(return_value=_make_pack()),
        )
        monkeypatch.setattr(
            "server.api.emoji_handlers._packs_repo.update_moderation_status",
            AsyncMock(return_value=1),
        )

        req = _FakeRequest(app_with_pool, slug="test-pack",
                           body={"moderation_status": "dmca_takedown"})
        resp = await handle_moderation(req)
        assert resp.status == 200
        assert json.loads(resp.body)["moderation_status"] == "dmca_takedown"
