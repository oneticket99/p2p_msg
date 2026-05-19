# SPDX-License-Identifier: GPL-3.0-or-later
"""MessagePayload + ReplyToField + json roundtrip 검증 — cycle 156 신설.

10 case:
- payload default factory uuid4 + ts auto-set
- type 무효 → text fallback
- to_json/from_json roundtrip
- reply_to None default
- reply_to populated + preview 60자 cap
- reactions dict serialize
- schema field 의무 포함
- invalid json → system payload fallback
- build_text_payload helper
- SCHEMA_VERSION 상수 정합
"""

from __future__ import annotations

import json

import pytest

from app.net.message_protocol import (
    SCHEMA_VERSION,
    MessagePayload,
    ReplyToField,
    build_text_payload,
)


class TestMessagePayloadDefaults:
    """default factory + auto-set 검증 — 3 case."""

    def test_uuid4_default(self) -> None:
        # 한글 주석 — id default = uuid4 의 36자 hex+dash 패턴
        p = MessagePayload(sender="user", text="hi")
        assert len(p.id) == 36
        assert p.id.count("-") == 4

    def test_ts_auto_set(self) -> None:
        # 한글 주석 — ts 부재 시 epoch millis 자동 세팅
        p = MessagePayload(sender="user", text="hi")
        assert p.ts > 1_700_000_000_000

    def test_type_invalid_fallback(self) -> None:
        # 한글 주석 — 무효 type → text 폴백
        p = MessagePayload(type="invalid", sender="user", text="hi")
        assert p.type == "text"


class TestMessagePayloadJsonRoundtrip:
    """to_json + from_json roundtrip 검증 — 4 case."""

    def test_text_roundtrip(self) -> None:
        p = MessagePayload(type="text", sender="alice", text="안녕")
        raw = p.to_json()
        parsed = MessagePayload.from_json(raw)
        assert parsed.type == "text"
        assert parsed.sender == "alice"
        assert parsed.text == "안녕"
        assert parsed.schema == SCHEMA_VERSION

    def test_reply_to_populated(self) -> None:
        reply = ReplyToField(message_id="uuid-1", sender="bob", preview="원본 텍스트")
        p = MessagePayload(type="text", sender="alice", text="답장", reply_to=reply)
        raw = p.to_json()
        parsed = MessagePayload.from_json(raw)
        assert parsed.reply_to is not None
        assert parsed.reply_to.message_id == "uuid-1"
        assert parsed.reply_to.sender == "bob"

    def test_reply_to_none_default(self) -> None:
        p = MessagePayload(type="text", sender="alice", text="hi")
        raw = p.to_json()
        d = json.loads(raw)
        assert d["reply_to"] is None
        parsed = MessagePayload.from_json(raw)
        assert parsed.reply_to is None

    def test_reactions_serialize(self) -> None:
        p = MessagePayload(type="text", sender="alice", text="hi", reactions={"👍": 3, "❤️": 1})
        raw = p.to_json()
        parsed = MessagePayload.from_json(raw)
        assert parsed.reactions == {"👍": 3, "❤️": 1}


class TestReplyToFieldCap:
    """preview 60자 cap 검증 — 1 case."""

    def test_preview_60_char_cap(self) -> None:
        long_text = "가" * 100
        raw = json.dumps({"reply_to": {"message_id": "u", "sender": "s", "preview": long_text}})
        parsed = MessagePayload.from_json(raw)
        assert parsed.reply_to is not None
        assert len(parsed.reply_to.preview) == 60


class TestInvalidJsonFallback:
    """invalid json + 미지 schema graceful — 1 case."""

    def test_invalid_json_fallback(self) -> None:
        parsed = MessagePayload.from_json("not json")
        assert parsed.type == "system"
        assert "invalid payload" in parsed.text


class TestBuildTextPayloadHelper:
    """build_text_payload 편의 함수 — 1 case."""

    def test_helper_basic(self) -> None:
        p = build_text_payload(sender="alice", text="hi")
        assert p.type == "text"
        assert p.sender == "alice"
        assert p.text == "hi"
        assert p.reply_to is None
