# SPDX-License-Identifier: GPL-3.0-or-later
"""FriendsClient unit test — cycle 169.663 omit 제거 path 4th."""

from __future__ import annotations

import pytest


class TestFriendsClientInit:
    def test_init_trims_trailing_slash(self) -> None:
        from app.net.friends_client import FriendsClient

        client = FriendsClient("https://api.local/", token="t")
        assert client._base_url == "https://api.local"
        assert client._token == "t"

    def test_empty_base_url_raises(self) -> None:
        from app.net.friends_client import FriendsClient

        with pytest.raises(ValueError, match="base_url"):
            FriendsClient("", token="t")

    def test_empty_token_raises(self) -> None:
        from app.net.friends_client import FriendsClient

        with pytest.raises(ValueError, match="token"):
            FriendsClient("https://api.local", token="")

    def test_owns_client_flag(self) -> None:
        from app.net.friends_client import FriendsClient

        client = FriendsClient("https://api.local", token="t")
        assert client._owns_client is True
        assert client._client is None


class TestFriendsErrorHierarchy:
    """Exception 계층 verify — base + 7 subclasses."""

    def test_subclass_chain(self) -> None:
        from app.net.friends_client import (
            FriendsAuthError, FriendsBadRequestError, FriendsClientError,
            FriendsConflictError, FriendsForbiddenError, FriendsNetworkError,
            FriendsNotFoundError, FriendsServerError,
        )

        assert issubclass(FriendsAuthError, FriendsClientError)
        assert issubclass(FriendsBadRequestError, FriendsClientError)
        assert issubclass(FriendsForbiddenError, FriendsClientError)
        assert issubclass(FriendsNotFoundError, FriendsClientError)
        assert issubclass(FriendsConflictError, FriendsClientError)
        assert issubclass(FriendsServerError, FriendsClientError)
        assert issubclass(FriendsNetworkError, FriendsClientError)
