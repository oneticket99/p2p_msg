# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.net.messages_client`` 단위 테스트.

MessagePayload 의 wire → dataclass 변환 + MessagesClient 의 query string +
Bearer 헤더 + 401/400/5xx/network 의 4 종 exception 매핑 + valid 응답 파싱.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from app.net.messages_client import (
    MessageFetchResult,
    MessagePayload,
    MessagesAuthError,
    MessagesBadRequestError,
    MessagesClient,
    MessagesClientError,
    MessagesNetworkError,
    MessagesServerError,
)


def _wire_message(
    *,
    msg_id: int = 1,
    room_id: int = 42,
    sender_id: int = 7,
    kind: str = "text",
    body: str | None = "안녕",
    file_id: str | None = None,
    created_at: str = "2026-05-21T03:30:00+00:00",
) -> dict:
    return {
        "id": msg_id,
        "room_id": room_id,
        "sender_id": sender_id,
        "kind": kind,
        "body": body,
        "file_id": file_id,
        "created_at": created_at,
    }


def _mock_session(
    *,
    status: int,
    json_data: dict | None = None,
    text_data: str = "",
    raise_client_error: bool = False,
) -> MagicMock:
    """aiohttp.ClientSession mock — get() context manager."""

    session = MagicMock(spec=aiohttp.ClientSession)
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.text = AsyncMock(return_value=text_data)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=None)

    if raise_client_error:
        session.get = MagicMock(side_effect=aiohttp.ClientError("mock"))
    else:
        session.get = MagicMock(return_value=cm)
    session.close = AsyncMock()
    return session


class TestMessagePayloadFromWire:
    """``MessagePayload.from_wire`` 변환 검증."""

    def test_text_message(self) -> None:
        wire = _wire_message(kind="text", body="hello")
        payload = MessagePayload.from_wire(wire)
        assert payload.id == 1
        assert payload.kind == "text"
        assert payload.body == "hello"
        assert payload.file_id is None

    def test_file_message(self) -> None:
        wire = _wire_message(kind="file", body=None, file_id="file-abc")
        payload = MessagePayload.from_wire(wire)
        assert payload.kind == "file"
        assert payload.body is None
        assert payload.file_id == "file-abc"

    def test_korean_body(self) -> None:
        wire = _wire_message(body="한글 메시지")
        payload = MessagePayload.from_wire(wire)
        assert payload.body == "한글 메시지"

    def test_missing_required_raises(self) -> None:
        wire = {"id": 1, "room_id": 42}
        with pytest.raises(KeyError):
            MessagePayload.from_wire(wire)


class TestMessagesClientValidation:
    """``MessagesClient.__init__`` 검증."""

    def test_valid_construction(self) -> None:
        client = MessagesClient("http://api.example.com/", token="tok")
        assert client._base_url == "http://api.example.com"

    def test_empty_base_url_rejected(self) -> None:
        with pytest.raises(ValueError, match="base_url 빈 문자열 불가"):
            MessagesClient("", token="tok")

    def test_empty_token_rejected(self) -> None:
        with pytest.raises(ValueError, match="token 빈 문자열 불가"):
            MessagesClient("http://api.example.com", token="")


class TestListMessagesInRangeValidation:
    """``list_messages_in_range`` 의 input 검증."""

    @pytest.mark.asyncio
    async def test_zero_room_id_rejected(self) -> None:
        client = MessagesClient("http://x", token="t")
        with pytest.raises(ValueError, match="room_id 양수 의무"):
            await client.list_messages_in_range(
                room_id=0, start_ts_ms=100, end_ts_ms=200
            )

    @pytest.mark.asyncio
    async def test_negative_ts_rejected(self) -> None:
        client = MessagesClient("http://x", token="t")
        with pytest.raises(ValueError, match="timestamp 음수 불가"):
            await client.list_messages_in_range(
                room_id=1, start_ts_ms=-1, end_ts_ms=100
            )

    @pytest.mark.asyncio
    async def test_end_before_start_rejected(self) -> None:
        client = MessagesClient("http://x", token="t")
        with pytest.raises(ValueError, match="end_ts_ms 의 start_ts_ms 초과 의무"):
            await client.list_messages_in_range(
                room_id=1, start_ts_ms=200, end_ts_ms=100
            )

    @pytest.mark.asyncio
    async def test_zero_limit_rejected(self) -> None:
        client = MessagesClient("http://x", token="t")
        with pytest.raises(ValueError, match="limit 양수 의무"):
            await client.list_messages_in_range(
                room_id=1, start_ts_ms=100, end_ts_ms=200, limit=0
            )


class TestListMessagesInRangeResponse:
    """``list_messages_in_range`` 의 HTTP 응답 매핑."""

    @pytest.mark.asyncio
    async def test_200_returns_messages(self) -> None:
        wire = {
            "messages": [
                _wire_message(msg_id=1, body="first"),
                _wire_message(msg_id=2, body="second"),
            ],
            "count": 2,
            "limit": 1000,
        }
        session = _mock_session(status=200, json_data=wire)
        client = MessagesClient("http://x", token="tok", session=session)
        result = await client.list_messages_in_range(
            room_id=42, start_ts_ms=100, end_ts_ms=200
        )
        assert isinstance(result, MessageFetchResult)
        assert result.count == 2
        assert len(result.messages) == 2
        assert result.messages[0].body == "first"

    @pytest.mark.asyncio
    async def test_200_empty_messages(self) -> None:
        wire = {"messages": [], "count": 0, "limit": 1000}
        session = _mock_session(status=200, json_data=wire)
        client = MessagesClient("http://x", token="tok", session=session)
        result = await client.list_messages_in_range(
            room_id=42, start_ts_ms=100, end_ts_ms=200
        )
        assert result.count == 0
        assert result.messages == []

    @pytest.mark.asyncio
    async def test_401_raises_auth_error(self) -> None:
        session = _mock_session(status=401)
        client = MessagesClient("http://x", token="tok", session=session)
        with pytest.raises(MessagesAuthError, match="Bearer 토큰"):
            await client.list_messages_in_range(
                room_id=42, start_ts_ms=100, end_ts_ms=200
            )

    @pytest.mark.asyncio
    async def test_400_raises_bad_request(self) -> None:
        session = _mock_session(status=400, text_data="invalid query")
        client = MessagesClient("http://x", token="tok", session=session)
        with pytest.raises(MessagesBadRequestError, match="BadRequest"):
            await client.list_messages_in_range(
                room_id=42, start_ts_ms=100, end_ts_ms=200
            )

    @pytest.mark.asyncio
    async def test_500_raises_server_error(self) -> None:
        session = _mock_session(status=500)
        client = MessagesClient("http://x", token="tok", session=session)
        with pytest.raises(MessagesServerError, match="ServerError HTTP 500"):
            await client.list_messages_in_range(
                room_id=42, start_ts_ms=100, end_ts_ms=200
            )

    @pytest.mark.asyncio
    async def test_unexpected_status_raises_client_error(self) -> None:
        session = _mock_session(status=302)
        client = MessagesClient("http://x", token="tok", session=session)
        with pytest.raises(MessagesClientError, match="unexpected HTTP 302"):
            await client.list_messages_in_range(
                room_id=42, start_ts_ms=100, end_ts_ms=200
            )

    @pytest.mark.asyncio
    async def test_network_error_raises_network_error(self) -> None:
        session = _mock_session(status=200, raise_client_error=True)
        client = MessagesClient("http://x", token="tok", session=session)
        with pytest.raises(MessagesNetworkError, match="네트워크 오류"):
            await client.list_messages_in_range(
                room_id=42, start_ts_ms=100, end_ts_ms=200
            )

    @pytest.mark.asyncio
    async def test_bearer_header_attached(self) -> None:
        wire = {"messages": [], "count": 0, "limit": 1000}
        session = _mock_session(status=200, json_data=wire)
        client = MessagesClient("http://x", token="MyToken", session=session)
        await client.list_messages_in_range(
            room_id=42, start_ts_ms=100, end_ts_ms=200
        )
        call_args = session.get.call_args
        assert call_args.kwargs["headers"]["Authorization"] == "Bearer MyToken"

    @pytest.mark.asyncio
    async def test_query_string_attached(self) -> None:
        wire = {"messages": [], "count": 0, "limit": 500}
        session = _mock_session(status=200, json_data=wire)
        client = MessagesClient("http://x", token="tok", session=session)
        await client.list_messages_in_range(
            room_id=42, start_ts_ms=100, end_ts_ms=200, limit=500
        )
        call_args = session.get.call_args
        params = call_args.kwargs["params"]
        assert params["room_id"] == "42"
        assert params["start_ts_ms"] == "100"
        assert params["end_ts_ms"] == "200"
        assert params["limit"] == "500"
