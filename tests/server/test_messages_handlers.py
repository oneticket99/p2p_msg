# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.api.messages_handlers`` 단위 테스트.

ChatView lazy load 의 server-side handler — query string parsing +
ms→datetime 변환 + MessageRow → wire format + pool query 호출 검증.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.messages_handlers import (
    _message_row_to_wire,
    _ms_to_datetime,
    _parse_int_query,
    handle_list_messages_in_range,
)
from server.db.repositories.messages import MessageRow


def _make_row(
    *,
    msg_id: int = 1,
    room_id: int = 42,
    sender_id: int = 7,
    kind: str = "text",
    body: str | None = "안녕",
    file_id: str | None = None,
    created_at: datetime | None = None,
) -> MessageRow:
    return MessageRow(
        id=msg_id,
        room_id=room_id,
        sender_id=sender_id,
        kind=kind,
        body=body,
        file_id=file_id,
        created_at=created_at or datetime(2026, 5, 20, 12, 0, 0, tzinfo=timezone.utc),
    )


def _make_request(
    *,
    user_id: int | None = 7,
    query: dict | None = None,
    pool_rows: list | None = None,
) -> MagicMock:
    """aiohttp.web.Request mock — user_id 주입 + db_pool + query string."""

    req = MagicMock()
    req.get = MagicMock(return_value=user_id)
    req.query = query or {}
    pool = MagicMock()
    req.app = MagicMock()
    req.app.__getitem__.side_effect = lambda k: {"db_pool": pool}[k]
    if pool_rows is not None:
        from server.db.repositories import messages as repo

        async def _fake_query(*args, **kwargs):
            return pool_rows

        repo.list_messages_in_range = _fake_query  # type: ignore[assignment]
    return req


class TestParseIntQuery:
    """``_parse_int_query`` 검증."""

    def test_valid_int(self) -> None:
        req = MagicMock()
        req.query = {"room_id": "42"}
        assert _parse_int_query(req, "room_id") == 42

    def test_missing_required_raises(self) -> None:
        req = MagicMock()
        req.query = {}
        with pytest.raises(web.HTTPBadRequest):
            _parse_int_query(req, "room_id")

    def test_missing_optional_returns_zero(self) -> None:
        req = MagicMock()
        req.query = {}
        assert _parse_int_query(req, "room_id", required=False) == 0

    def test_invalid_int_raises(self) -> None:
        req = MagicMock()
        req.query = {"room_id": "abc"}
        with pytest.raises(web.HTTPBadRequest):
            _parse_int_query(req, "room_id")


class TestMsToDatetime:
    """``_ms_to_datetime`` 변환 검증."""

    def test_basic_conversion(self) -> None:
        dt = _ms_to_datetime(1_700_000_000_000)
        assert dt.tzinfo == timezone.utc
        assert dt.timestamp() == 1_700_000_000.0

    def test_zero_epoch(self) -> None:
        dt = _ms_to_datetime(0)
        assert dt == datetime(1970, 1, 1, tzinfo=timezone.utc)

    def test_negative_ms_rejected(self) -> None:
        with pytest.raises(web.HTTPBadRequest):
            _ms_to_datetime(-1)


class TestMessageRowToWire:
    """``_message_row_to_wire`` 변환 검증."""

    def test_text_message(self) -> None:
        row = _make_row(kind="text", body="hello")
        wire = _message_row_to_wire(row)
        assert wire["kind"] == "text"
        assert wire["body"] == "hello"
        assert wire["file_id"] is None
        assert wire["created_at"].startswith("2026-05-20")

    def test_file_message(self) -> None:
        row = _make_row(kind="file", body=None, file_id="file-abc")
        wire = _message_row_to_wire(row)
        assert wire["kind"] == "file"
        assert wire["body"] is None
        assert wire["file_id"] == "file-abc"

    def test_korean_body_preserved(self) -> None:
        row = _make_row(body="한글 메시지")
        wire = _message_row_to_wire(row)
        assert wire["body"] == "한글 메시지"
        # JSON serialize 의 한글 보존 검증
        text = json.dumps(wire, ensure_ascii=False)
        assert "한글" in text


class TestHandleListMessagesInRange:
    """``handle_list_messages_in_range`` 검증."""

    @pytest.mark.asyncio
    async def test_missing_user_id_unauthorized(self) -> None:
        req = _make_request(user_id=None)
        with pytest.raises(web.HTTPUnauthorized):
            await handle_list_messages_in_range(req)

    @pytest.mark.asyncio
    async def test_missing_room_id_bad_request(self) -> None:
        req = _make_request(query={"start_ts_ms": "100", "end_ts_ms": "200"})
        with pytest.raises(web.HTTPBadRequest):
            await handle_list_messages_in_range(req)

    @pytest.mark.asyncio
    async def test_end_ts_before_start_rejected(self) -> None:
        req = _make_request(
            query={"room_id": "42", "start_ts_ms": "200", "end_ts_ms": "100"}
        )
        with pytest.raises(web.HTTPBadRequest):
            await handle_list_messages_in_range(req)

    @pytest.mark.asyncio
    async def test_limit_zero_rejected(self) -> None:
        req = _make_request(
            query={
                "room_id": "42",
                "start_ts_ms": "100",
                "end_ts_ms": "200",
                "limit": "0",
            }
        )
        with pytest.raises(web.HTTPBadRequest):
            await handle_list_messages_in_range(req)

    @pytest.mark.asyncio
    async def test_limit_exceeds_max_rejected(self) -> None:
        req = _make_request(
            query={
                "room_id": "42",
                "start_ts_ms": "100",
                "end_ts_ms": "200",
                "limit": "10000",
            }
        )
        with pytest.raises(web.HTTPBadRequest):
            await handle_list_messages_in_range(req)

    @pytest.mark.asyncio
    async def test_invalid_limit_string_rejected(self) -> None:
        req = _make_request(
            query={
                "room_id": "42",
                "start_ts_ms": "100",
                "end_ts_ms": "200",
                "limit": "abc",
            }
        )
        with pytest.raises(web.HTTPBadRequest):
            await handle_list_messages_in_range(req)

    @pytest.mark.asyncio
    async def test_valid_request_returns_messages(self) -> None:
        rows = [
            _make_row(msg_id=1, body="first"),
            _make_row(msg_id=2, body="second"),
        ]
        req = _make_request(
            query={
                "room_id": "42",
                "start_ts_ms": "1700000000000",
                "end_ts_ms": "1700001000000",
            },
            pool_rows=rows,
        )
        resp = await handle_list_messages_in_range(req)
        assert resp.status == 200
        body = json.loads(resp.body.decode("utf-8"))
        assert body["count"] == 2
        assert body["limit"] == 1000
        assert len(body["messages"]) == 2
        assert body["messages"][0]["body"] == "first"

    @pytest.mark.asyncio
    async def test_empty_result_returns_zero_count(self) -> None:
        req = _make_request(
            query={
                "room_id": "42",
                "start_ts_ms": "100",
                "end_ts_ms": "200",
            },
            pool_rows=[],
        )
        resp = await handle_list_messages_in_range(req)
        body = json.loads(resp.body.decode("utf-8"))
        assert body["count"] == 0
        assert body["messages"] == []
