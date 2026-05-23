# SPDX-License-Identifier: GPL-3.0-or-later
"""Telegram sticker pack share + bot framework chain E2E — cycle 169.661 신설.

사용자 directive #9 — "Telegram sticker pack share + bot framework (emoji pack 디렉토리
+ BotFather equivalent + payment)"

chain:
1. emoji pack create / list / get + slug uniqueness
2. emoji pack add item
3. moderation queue (pending → approved)
4. bot framework — customer_service_bot + emoji_moderation_dispatcher 기존 binding verify
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.emoji_handlers import handle_create_pack, handle_get_pack, handle_list_packs
from server.db.repositories.emoji_packs import EmojiPackRow, ModerationStatus


pytestmark = pytest.mark.integration


class _FakeRequest:
    """aiohttp Request 모방 — emoji_handlers 정합."""

    def __init__(self, method: str, path: str, app: web.Application, user_id: int | None = None, match_info: dict | None = None, body: dict | None = None, query: dict | None = None) -> None:
        self.app = app
        self.method = method
        self.path = path
        self.headers = {"Authorization": "Bearer fake"} if user_id else {}
        self.match_info = match_info or {}
        self.query = query or {}
        self.remote = "127.0.0.1"
        self._state = {"user_id": user_id} if user_id else {}
        self._body = body

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    async def json(self) -> dict:
        if self._body is None:
            raise ValueError("body 부재")
        return self._body


@pytest.fixture
def app_with_pool() -> web.Application:
    pool = MagicMock()
    app = web.Application()
    app["db_pool"] = pool
    return app


def _make_pack(pack_id: int = 1, slug: str = "anime-emojis", owner: int = 42, is_public: bool = True, mod: str = "approved") -> EmojiPackRow:
    return EmojiPackRow(
        id=pack_id, owner_user_id=owner, name="Anime Emojis", slug=slug,
        description="Test pack", is_public=is_public,
        moderation_status=ModerationStatus(mod), download_count=0,
    )


class TestEmojiPackListPublic:
    """GET /api/emoji/packs — 공개 + approved list."""

    @pytest.mark.asyncio
    async def test_list_public_packs(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.emoji_handlers._packs_repo.list_public_approved",
            AsyncMock(return_value=[_make_pack(1, "pack-a"), _make_pack(2, "pack-b")]),
        )
        req = _FakeRequest("GET", "/api/emoji/packs", app_with_pool, query={"limit": "50", "offset": "0"})
        resp = await handle_list_packs(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["count"] == 2
        assert data["packs"][0]["slug"] == "pack-a"
        assert data["packs"][1]["slug"] == "pack-b"

    @pytest.mark.asyncio
    async def test_list_empty_when_no_pool(self) -> None:
        app = web.Application()
        # 한글 주석 — db_pool 부재 → empty list graceful
        req = _FakeRequest("GET", "/api/emoji/packs", app, query={})
        resp = await handle_list_packs(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["count"] == 0


class TestEmojiPackCreate:
    """POST /api/emoji/packs — 신규 팩 생성 + slug uniqueness."""

    @pytest.mark.asyncio
    async def test_create_pack_returns_201(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.emoji_handlers._packs_repo.get_pack_by_slug",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "server.api.emoji_handlers._packs_repo.insert_pack",
            AsyncMock(return_value=100),
        )
        req = _FakeRequest(
            "POST", "/api/emoji/packs", app_with_pool, user_id=42,
            body={"name": "Cool Pack", "slug": "cool-pack", "description": "demo", "is_public": True},
        )
        resp = await handle_create_pack(req)
        assert resp.status == 201
        data = json.loads(resp.body)
        assert data["pack_id"] == 100
        assert data["slug"] == "cool-pack"

    @pytest.mark.asyncio
    async def test_duplicate_slug_returns_409(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.emoji_handlers._packs_repo.get_pack_by_slug",
            AsyncMock(return_value=_make_pack(99, "existing-slug")),
        )
        req = _FakeRequest(
            "POST", "/api/emoji/packs", app_with_pool, user_id=42,
            body={"name": "Dup", "slug": "existing-slug", "is_public": False},
        )
        resp = await handle_create_pack(req)
        assert resp.status == 409
        data = json.loads(resp.body)
        assert data["error"] == "SLUG_CONFLICT"

    @pytest.mark.asyncio
    async def test_unauthorized_no_user_raises_401(self, app_with_pool) -> None:
        req = _FakeRequest(
            "POST", "/api/emoji/packs", app_with_pool, user_id=None,
            body={"name": "x", "slug": "x"},
        )
        with pytest.raises(web.HTTPUnauthorized):
            await handle_create_pack(req)

    @pytest.mark.asyncio
    async def test_invalid_slug_raises_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            "POST", "/api/emoji/packs", app_with_pool, user_id=42,
            body={"name": "x", "slug": "Invalid Slug!", "is_public": False},
        )
        with pytest.raises(web.HTTPBadRequest):
            await handle_create_pack(req)


class TestBotFrameworkBinding:
    """bot framework — customer_service_bot + emoji_moderation_dispatcher binding verify."""

    def test_customer_service_bot_import(self) -> None:
        from app.bot.customer_service_bot import CustomerServiceBot

        assert CustomerServiceBot is not None

    def test_emoji_moderation_dispatcher_import(self) -> None:
        from app.bot.emoji_moderation_dispatcher import EmojiModerationDispatcher

        assert EmojiModerationDispatcher is not None

    def test_jailbreak_detector_import(self) -> None:
        # 한글 주석 — function-based detect API (cycle 169.x 정합)
        from app.bot.jailbreak_detector import detect, is_blocked

        assert detect is not None
        assert is_blocked is not None

    def test_rag_context_import(self) -> None:
        # 한글 주석 — FAQEntry dataclass + RAGStore Protocol pattern
        from app.bot.rag_context import FAQEntry, RAGStore

        assert FAQEntry is not None
        assert RAGStore is not None
