# SPDX-License-Identifier: GPL-3.0-or-later
"""server protocol envelope unit test — cycle 169.700 신설.

chain:
1. wire_to_internal from → from_ rename
2. wire_to_internal idempotent (from_ 기존 → 변환 skip)
3. internal_to_wire from_ → from rename
4. internal_to_wire passthrough
5. is_valid_client_type 5 type
6. is_valid_client_type unknown reject
7. error code constants
"""

from __future__ import annotations


class TestWireInternal:
    def test_from_to_from_underscore(self) -> None:
        from server.protocol import wire_to_internal

        result = wire_to_internal({"type": "OFFER", "from": "alice", "sdp": "x"})
        assert "from_" in result
        assert result["from_"] == "alice"
        assert "from" not in result

    def test_existing_from_underscore_unchanged(self) -> None:
        # 한글 주석 — from_ 기존 → 변환 차단
        from server.protocol import wire_to_internal

        payload = {"from_": "bob", "from": "alice"}
        result = wire_to_internal(payload)
        assert result == payload

    def test_no_from_passthrough(self) -> None:
        from server.protocol import wire_to_internal

        payload = {"type": "PEERS", "peers": []}
        assert wire_to_internal(payload) == payload


class TestInternalWire:
    def test_from_underscore_to_from(self) -> None:
        from server.protocol import internal_to_wire

        result = internal_to_wire({"type": "OFFER", "from_": "alice", "sdp": "x"})
        assert "from" in result
        assert result["from"] == "alice"
        assert "from_" not in result

    def test_no_from_underscore_passthrough(self) -> None:
        from server.protocol import internal_to_wire

        payload = {"type": "JOIN", "room": "r"}
        assert internal_to_wire(payload) == payload


class TestClientTypeValidation:
    def test_5_valid_types(self) -> None:
        from server.protocol import is_valid_client_type

        for t in ("JOIN", "LEAVE", "OFFER", "ANSWER", "ICE"):
            assert is_valid_client_type(t)

    def test_unknown_rejected(self) -> None:
        from server.protocol import is_valid_client_type

        assert is_valid_client_type("BOGUS") is False
        assert is_valid_client_type("") is False
        # 한글 주석 — server-only type 도 client 의 type 부재
        assert is_valid_client_type("PEERS") is False
        assert is_valid_client_type("ERROR") is False

    def test_non_string_rejected(self) -> None:
        from server.protocol import is_valid_client_type

        assert is_valid_client_type(None) is False
        assert is_valid_client_type(123) is False


class TestErrorCodes:
    def test_constants_defined(self) -> None:
        from server.protocol import (
            ERR_BAD_JSON, ERR_MISSING_FIELD, ERR_NOT_JOINED,
            ERR_PEER_NOT_FOUND, ERR_ROOM_NOT_FOUND, ERR_UNKNOWN_TYPE,
        )

        assert ERR_BAD_JSON == "BAD_JSON"
        assert ERR_UNKNOWN_TYPE == "UNKNOWN_TYPE"
        assert ERR_MISSING_FIELD == "MISSING_FIELD"
        assert ERR_NOT_JOINED == "NOT_JOINED"
        assert ERR_PEER_NOT_FOUND == "PEER_NOT_FOUND"
        assert ERR_ROOM_NOT_FOUND == "ROOM_NOT_FOUND"


class TestRoundTrip:
    def test_internal_wire_internal(self) -> None:
        from server.protocol import internal_to_wire, wire_to_internal

        original = {"type": "ANSWER", "from_": "bob", "sdp": "data"}
        wire = internal_to_wire(original)
        recovered = wire_to_internal(wire)
        assert recovered == original
