# SPDX-License-Identifier: GPL-3.0-or-later
"""MessagesClient + MessagesRestClient unit test — cycle 169.664 omit 제거."""

from __future__ import annotations

import pytest


class TestMessagesClientInit:
    def test_trims_trailing_slash(self) -> None:
        from app.net.messages_client import MessagesClient

        c = MessagesClient("https://api.local/", token="t")
        assert c._base_url == "https://api.local"
        assert c._token == "t"
        assert c._owns_session is True

    def test_empty_base_url_raises(self) -> None:
        from app.net.messages_client import MessagesClient

        with pytest.raises(ValueError, match="base_url"):
            MessagesClient("", token="t")

    def test_empty_token_raises(self) -> None:
        from app.net.messages_client import MessagesClient

        with pytest.raises(ValueError, match="token"):
            MessagesClient("https://api.local", token="")


class TestMessagesRestClientInit:
    def test_trims_trailing_slash(self) -> None:
        from app.net.messages_client import MessagesRestClient

        c = MessagesRestClient("https://api.local/", token="t")
        assert c._base_url == "https://api.local"
        assert c._owns_client is True

    def test_empty_base_url_raises(self) -> None:
        from app.net.messages_client import MessagesRestClient

        with pytest.raises(ValueError, match="base_url"):
            MessagesRestClient("", token="t")

    def test_empty_token_raises(self) -> None:
        from app.net.messages_client import MessagesRestClient

        with pytest.raises(ValueError, match="token"):
            MessagesRestClient("https://api.local", token="")


class TestMessagesErrorHierarchy:
    def test_all_subclass_base(self) -> None:
        from app.net.messages_client import (
            MessagesAuthError, MessagesBadRequestError, MessagesClientError,
            MessagesForbiddenError, MessagesNetworkError, MessagesNotFoundError,
            MessagesServerError,
        )

        for cls in (
            MessagesAuthError, MessagesBadRequestError, MessagesForbiddenError,
            MessagesNotFoundError, MessagesServerError, MessagesNetworkError,
        ):
            assert issubclass(cls, MessagesClientError)
