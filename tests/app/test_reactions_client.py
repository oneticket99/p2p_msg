# SPDX-License-Identifier: GPL-3.0-or-later
"""ReactionsClient unit test — cycle 169.654 omit 제거 path 3rd."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestReactionsClientInit:
    def test_init_trims_trailing_slash(self) -> None:
        from app.net.reactions_client import ReactionsClient

        client = ReactionsClient("https://api.local/", token="t")
        assert client._base_url == "https://api.local"
        assert client._token == "t"

    def test_set_token_replaces(self) -> None:
        from app.net.reactions_client import ReactionsClient

        client = ReactionsClient("https://api.local")
        assert client._token is None
        client.set_token("new")
        assert client._token == "new"

    def test_headers_with_token(self) -> None:
        from app.net.reactions_client import ReactionsClient

        client = ReactionsClient("https://api.local", token="abc")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer abc"
        assert headers["Content-Type"] == "application/json"

    def test_headers_without_token(self) -> None:
        from app.net.reactions_client import ReactionsClient

        client = ReactionsClient("https://api.local")
        headers = client._headers()
        assert "Authorization" not in headers


class TestReactionsClientAddSuccess:
    @pytest.mark.asyncio
    async def test_add_reaction_returns_count(self) -> None:
        from app.net.reactions_client import ReactionsClient

        client = ReactionsClient("https://api.local", token="t")
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"total_count": 5}
        fake_client = MagicMock()
        fake_client.post = AsyncMock(return_value=fake_resp)
        client._client = fake_client
        total = await client.add_reaction(42, "👍")
        assert total == 5

    @pytest.mark.asyncio
    async def test_add_reaction_401_raises_auth(self) -> None:
        from app.net.reactions_client import ReactionsClient, ReactionsAuthError

        client = ReactionsClient("https://api.local", token="t")
        fake_resp = MagicMock()
        fake_resp.status_code = 401
        fake_client = MagicMock()
        fake_client.post = AsyncMock(return_value=fake_resp)
        client._client = fake_client
        with pytest.raises(ReactionsAuthError):
            await client.add_reaction(42, "👍")


class TestReactionsClientListSuccess:
    @pytest.mark.asyncio
    async def test_list_reactions_parses_entries(self) -> None:
        from app.net.reactions_client import ReactionsClient

        client = ReactionsClient("https://api.local", token="t")
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            "reactions": [
                {"emoji": "👍", "count": 3},
                {"emoji": "❤️", "count": 1},
            ]
        }
        fake_client = MagicMock()
        fake_client.get = AsyncMock(return_value=fake_resp)
        client._client = fake_client
        result = await client.list_reactions(42)
        assert len(result) == 2
        assert result[0].emoji == "👍"
        assert result[0].count == 3
