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


# ─── cycle 141 — message persistence + MESSAGE_SEND audit chain ─────────────


from contextlib import asynccontextmanager  # noqa: E402

from server.api.messages_handlers import (  # noqa: E402
    handle_delete_message,
    handle_get_message,
    handle_list_room_messages,
    handle_post_message,
)
from server.db.repositories.rooms import PeerRow, RoomRow  # noqa: E402
from server.db.repositories.user_activity import ActivityAction  # noqa: E402


def _mock_pool() -> tuple[Any, Any]:
    """asyncmy pool + cursor mock — audit INSERT capture 표준 builder."""

    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = 1
    cursor.rowcount = 1

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


def _make_room(
    *,
    room_id: int = 7,
    owner_id: int = 42,
    kind: str = "group",
    status: str = "active",
) -> RoomRow:
    return RoomRow(
        id=room_id,
        room_code="abcd1234",
        owner_id=owner_id,
        kind=kind,
        status=status,
        created_at=datetime(2026, 5, 20, 12, 0, 0),
        closed_at=None,
    )


def _make_peer(
    *,
    peer_id: int = 1,
    room_id: int = 7,
    user_id: int = 42,
    role: str = "member",
) -> PeerRow:
    return PeerRow(
        id=peer_id,
        room_id=room_id,
        user_id=user_id,
        role=role,
        joined_at=datetime(2026, 5, 20, 12, 0, 0),
        left_at=None,
    )


def _make_msg_request(
    *,
    db_pool: Any = None,
    user_id: int = 42,
    body: dict | None = None,
    match_info: dict | None = None,
    query: dict | None = None,
) -> MagicMock:
    """aiohttp.web.Request mock — middleware user_id 주입 + db_pool + audit graceful."""

    req = MagicMock()
    req.__getitem__.side_effect = lambda k: {"user_id": user_id}[k]
    body_str = json.dumps(body) if body is not None else ""
    req.content_length = len(body_str) if body else 0
    req.json = AsyncMock(return_value=body or {})
    req.match_info = match_info or {}
    req.query = query or {}
    req.app = MagicMock()
    req.app.__getitem__.side_effect = lambda k: {"db_pool": db_pool}[k]
    req.app.get = lambda k, default=None: db_pool if k == "db_pool" else default
    req.headers = MagicMock()
    req.headers.get = lambda k, default="": (
        "TooTalk/0.4.0" if k == "User-Agent" else default
    )
    req.remote = "10.0.0.1"
    return req


class TestPostMessage:
    """POST /api/rooms/{room_id}/messages — INSERT + MESSAGE_SEND audit + 권한."""

    @pytest.mark.asyncio
    async def test_post_message_success_audit_message_send(
        self, monkeypatch
    ) -> None:
        # 한글 주석: MESSAGE_SEND audit row INSERT 정합 검증.
        pool, cursor = _mock_pool()
        req = _make_msg_request(
            db_pool=pool,
            user_id=99,
            match_info={"room_id": "7"},
            body={"body": "hello"},
        )

        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=_make_peer(user_id=99, role="member")),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.insert_message",
            AsyncMock(return_value=123),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.get_by_id",
            AsyncMock(
                return_value=_make_row(
                    msg_id=123,
                    room_id=7,
                    sender_id=99,
                    body="hello",
                )
            ),
        )

        resp = await handle_post_message(req)
        assert resp.status == 201
        body = json.loads(resp.body.decode("utf-8"))
        assert body["ok"] is True
        assert body["message_id"] == 123
        assert body["room_id"] == 7
        assert body["sender_id"] == 99
        assert body["kind"] == "text"
        assert body["created_at"].startswith("2026-05-20")

        # MESSAGE_SEND audit INSERT 검증
        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 99  # user_id
        assert params[1] == ActivityAction.MESSAGE_SEND.value
        assert params[2] == 123  # target_id = message_id

    @pytest.mark.asyncio
    async def test_post_message_non_member_forbidden_403(
        self, monkeypatch
    ) -> None:
        # 한글 주석: 활성 peer 부재 + owner 아님 = 403.
        pool, _ = _mock_pool()
        req = _make_msg_request(
            db_pool=pool,
            user_id=999,
            match_info={"room_id": "7"},
            body={"body": "intruder"},
        )

        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=None),
        )

        resp = await handle_post_message(req)
        assert resp.status == 403
        body = json.loads(resp.body.decode("utf-8"))
        assert body["error"] == "forbidden_not_member"

    @pytest.mark.asyncio
    async def test_post_message_room_not_found_404(self, monkeypatch) -> None:
        # 한글 주석: room 부재 = 404.
        pool, _ = _mock_pool()
        req = _make_msg_request(
            db_pool=pool,
            user_id=42,
            match_info={"room_id": "9999"},
            body={"body": "x"},
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=None),
        )

        resp = await handle_post_message(req)
        assert resp.status == 404
        body = json.loads(resp.body.decode("utf-8"))
        assert body["error"] == "room_not_found"

    @pytest.mark.asyncio
    async def test_post_message_empty_body_400(self, monkeypatch) -> None:
        # 한글 주석: kind=text + body 빈 문자열 = 400.
        pool, _ = _mock_pool()
        req = _make_msg_request(
            db_pool=pool,
            user_id=42,
            match_info={"room_id": "7"},
            body={"body": "   "},
        )

        with pytest.raises(web.HTTPBadRequest, match="body"):
            await handle_post_message(req)


class TestListMessages:
    """GET /api/rooms/{room_id}/messages — paginated + 권한."""

    @pytest.mark.asyncio
    async def test_list_messages_paginated(self, monkeypatch) -> None:
        # 한글 주석: limit + offset + total + count 응답 정합.
        pool, _ = _mock_pool()
        req = _make_msg_request(
            db_pool=pool,
            user_id=42,
            match_info={"room_id": "7"},
            query={"limit": "10", "offset": "5"},
        )

        rows = [
            _make_row(msg_id=11, body="m1"),
            _make_row(msg_id=10, body="m2"),
        ]
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=_make_peer(user_id=42, role="owner")),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.list_by_room",
            AsyncMock(return_value=rows),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.count_by_room",
            AsyncMock(return_value=42),
        )

        resp = await handle_list_room_messages(req)
        assert resp.status == 200
        body = json.loads(resp.body.decode("utf-8"))
        assert body["count"] == 2
        assert body["total"] == 42
        assert body["limit"] == 10
        assert body["offset"] == 5
        assert body["messages"][0]["body"] == "m1"

    @pytest.mark.asyncio
    async def test_list_messages_empty(self, monkeypatch) -> None:
        # 한글 주석: 비빈 룸 = count 0.
        pool, _ = _mock_pool()
        req = _make_msg_request(
            db_pool=pool, user_id=42, match_info={"room_id": "7"}
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=_make_peer(user_id=42, role="owner")),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.list_by_room",
            AsyncMock(return_value=[]),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.count_by_room",
            AsyncMock(return_value=0),
        )

        resp = await handle_list_room_messages(req)
        body = json.loads(resp.body.decode("utf-8"))
        assert body["count"] == 0
        assert body["total"] == 0

    @pytest.mark.asyncio
    async def test_list_messages_limit_overflow_400(self, monkeypatch) -> None:
        # 한글 주석: limit > 500 = 400.
        pool, _ = _mock_pool()
        req = _make_msg_request(
            db_pool=pool,
            user_id=42,
            match_info={"room_id": "7"},
            query={"limit": "9999"},
        )

        with pytest.raises(web.HTTPBadRequest, match="limit"):
            await handle_list_room_messages(req)


class TestDeleteMessage:
    """DELETE /api/messages/{message_id} — sender / owner 권한 + 부재."""

    @pytest.mark.asyncio
    async def test_delete_message_by_sender_success(self, monkeypatch) -> None:
        # 한글 주석: sender 자신 의 soft delete PASS.
        pool, _ = _mock_pool()
        req = _make_msg_request(
            db_pool=pool, user_id=99, match_info={"message_id": "55"}
        )

        msg = _make_row(msg_id=55, sender_id=99, room_id=7, body="del me")
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.get_by_id",
            AsyncMock(return_value=msg),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )
        mock_soft = AsyncMock(return_value=1)
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.soft_delete", mock_soft
        )

        resp = await handle_delete_message(req)
        assert resp.status == 200
        body = json.loads(resp.body.decode("utf-8"))
        assert body["ok"] is True
        assert body["deleted"] is True
        assert body["message_id"] == 55
        mock_soft.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_message_by_other_user_403(self, monkeypatch) -> None:
        # 한글 주석: sender 아님 + owner 아님 = 403.
        pool, _ = _mock_pool()
        req = _make_msg_request(
            db_pool=pool, user_id=999, match_info={"message_id": "55"}
        )

        msg = _make_row(msg_id=55, sender_id=99, room_id=7)
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.get_by_id",
            AsyncMock(return_value=msg),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )

        resp = await handle_delete_message(req)
        assert resp.status == 403
        body = json.loads(resp.body.decode("utf-8"))
        assert body["error"] == "forbidden_sender_or_owner_only"

    @pytest.mark.asyncio
    async def test_delete_message_not_found_404(self, monkeypatch) -> None:
        # 한글 주석: message 부재 = 404.
        pool, _ = _mock_pool()
        req = _make_msg_request(
            db_pool=pool, user_id=42, match_info={"message_id": "9999"}
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.get_by_id",
            AsyncMock(return_value=None),
        )

        resp = await handle_delete_message(req)
        assert resp.status == 404
        body = json.loads(resp.body.decode("utf-8"))
        assert body["error"] == "message_not_found"
