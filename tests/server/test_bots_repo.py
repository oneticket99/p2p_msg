# SPDX-License-Identifier: GPL-3.0-or-later
"""bots + bot_tokens repository unit — cycle 169.754 신설.

token 생성/해시 + insert_bot(validation) + token + lookup + 디렉토리 + 인증/revoke.
mock async pool 로 asyncmy 우회.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_pool(*, fetchone=None, fetchall=None, lastrowid=1, rowcount=1) -> MagicMock:
    # 한글 주석 — acquire + cursor 2단 async context 모킹
    pool = MagicMock()
    cur = MagicMock()
    cur.execute = AsyncMock(return_value=None)
    cur.fetchone = AsyncMock(return_value=fetchone)
    cur.fetchall = AsyncMock(return_value=fetchall or [])
    cur.lastrowid = lastrowid
    cur.rowcount = rowcount
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
# 한글 주석 — bots SELECT 10-tuple
_BOT_ROW = (3, 10, "Toona Bot", "toona", "desc", None, 1, 1, "active", _TS)
# 한글 주석 — authenticate JOIN 11-tuple (+ token_id at [10])
_AUTH_ROW = (3, 10, "Toona Bot", "toona", "desc", None, 1, 1, "active", _TS, 99)


class TestTokenHelpers:
    def test_hash_token_deterministic(self) -> None:
        from server.db.repositories.bots import _hash_token

        h = _hash_token("bot_abc")
        assert h == _hash_token("bot_abc")
        assert len(h) == 64

    def test_generate_bot_token_shape(self) -> None:
        from server.db.repositories.bots import _hash_token, generate_bot_token

        plain, h = generate_bot_token()
        assert plain.startswith("bot_")
        assert h == _hash_token(plain)


class TestInsertBotValidation:
    @pytest.mark.asyncio
    async def test_zero_owner_raises(self) -> None:
        from server.db.repositories.bots import insert_bot

        with pytest.raises(ValueError, match="owner_user_id"):
            await insert_bot(_build_pool(), owner_user_id=0, name="n", username="u")

    @pytest.mark.asyncio
    async def test_empty_name_raises(self) -> None:
        from server.db.repositories.bots import insert_bot

        with pytest.raises(ValueError, match="name"):
            await insert_bot(_build_pool(), owner_user_id=1, name="", username="u")

    @pytest.mark.asyncio
    async def test_long_username_raises(self) -> None:
        from server.db.repositories.bots import insert_bot

        with pytest.raises(ValueError, match="username"):
            await insert_bot(_build_pool(), owner_user_id=1, name="n", username="x" * 33)

    @pytest.mark.asyncio
    async def test_long_description_raises(self) -> None:
        from server.db.repositories.bots import insert_bot

        with pytest.raises(ValueError, match="description"):
            await insert_bot(_build_pool(), owner_user_id=1, name="n", username="u",
                             description="d" * 256)

    @pytest.mark.asyncio
    async def test_long_webhook_raises(self) -> None:
        from server.db.repositories.bots import insert_bot

        with pytest.raises(ValueError, match="webhook_url"):
            await insert_bot(_build_pool(), owner_user_id=1, name="n", username="u",
                             webhook_url="h" * 513)

    @pytest.mark.asyncio
    async def test_valid_returns_id(self) -> None:
        from server.db.repositories.bots import insert_bot

        bot_id = await insert_bot(_build_pool(lastrowid=42), owner_user_id=1,
                                  name="n", username="u", is_public=True, inline_enabled=True)
        assert bot_id == 42


class TestInsertBotToken:
    @pytest.mark.asyncio
    async def test_zero_bot_id_raises(self) -> None:
        from server.db.repositories.bots import insert_bot_token

        with pytest.raises(ValueError, match="bot_id"):
            await insert_bot_token(_build_pool(), bot_id=0)

    @pytest.mark.asyncio
    async def test_returns_plaintext_and_id(self) -> None:
        from server.db.repositories.bots import insert_bot_token

        plain, tid = await insert_bot_token(_build_pool(lastrowid=7), bot_id=3, label="ci")
        assert plain.startswith("bot_")
        assert tid == 7


class TestGetBotByUsername:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        from server.db.repositories.bots import BotRow, get_bot_by_username

        row = await get_bot_by_username(_build_pool(fetchone=_BOT_ROW), "toona")
        assert isinstance(row, BotRow)
        assert row.username == "toona" and row.is_public is True

    @pytest.mark.asyncio
    async def test_missing_returns_none(self) -> None:
        from server.db.repositories.bots import get_bot_by_username

        assert await get_bot_by_username(_build_pool(fetchone=None), "ghost") is None


class TestListPublicBots:
    @pytest.mark.asyncio
    async def test_limit_over_200_raises(self) -> None:
        from server.db.repositories.bots import list_public_bots

        with pytest.raises(ValueError, match="limit"):
            await list_public_bots(_build_pool(), limit=201)

    @pytest.mark.asyncio
    async def test_negative_offset_raises(self) -> None:
        from server.db.repositories.bots import list_public_bots

        with pytest.raises(ValueError, match="offset"):
            await list_public_bots(_build_pool(), offset=-1)

    @pytest.mark.asyncio
    async def test_returns_rows(self) -> None:
        from server.db.repositories.bots import list_public_bots

        rows = await list_public_bots(_build_pool(fetchall=[_BOT_ROW, _BOT_ROW]))
        assert len(rows) == 2


class TestAuthenticateBotToken:
    @pytest.mark.asyncio
    async def test_empty_plaintext_returns_none(self) -> None:
        from server.db.repositories.bots import authenticate_bot_token

        assert await authenticate_bot_token(_build_pool(), "") is None

    @pytest.mark.asyncio
    async def test_found_returns_bot(self) -> None:
        from server.db.repositories.bots import BotRow, authenticate_bot_token

        row = await authenticate_bot_token(_build_pool(fetchone=_AUTH_ROW), "bot_xyz")
        assert isinstance(row, BotRow)
        assert row.id == 3

    @pytest.mark.asyncio
    async def test_unknown_returns_none(self) -> None:
        from server.db.repositories.bots import authenticate_bot_token

        assert await authenticate_bot_token(_build_pool(fetchone=None), "bot_bad") is None


class TestRevokeAndListOwner:
    @pytest.mark.asyncio
    async def test_revoke_zero_raises(self) -> None:
        from server.db.repositories.bots import revoke_bot_token

        with pytest.raises(ValueError, match="token_id"):
            await revoke_bot_token(_build_pool(), token_id=0)

    @pytest.mark.asyncio
    async def test_revoke_success_true(self) -> None:
        from server.db.repositories.bots import revoke_bot_token

        assert await revoke_bot_token(_build_pool(rowcount=1), token_id=5) is True

    @pytest.mark.asyncio
    async def test_revoke_noop_false(self) -> None:
        from server.db.repositories.bots import revoke_bot_token

        assert await revoke_bot_token(_build_pool(rowcount=0), token_id=5) is False

    @pytest.mark.asyncio
    async def test_list_owner_zero_raises(self) -> None:
        from server.db.repositories.bots import list_owner_bots

        with pytest.raises(ValueError, match="owner_user_id"):
            await list_owner_bots(_build_pool(), owner_user_id=0)

    @pytest.mark.asyncio
    async def test_list_owner_returns_rows(self) -> None:
        from server.db.repositories.bots import list_owner_bots

        rows = await list_owner_bots(_build_pool(fetchall=[_BOT_ROW]), owner_user_id=10)
        assert len(rows) == 1
