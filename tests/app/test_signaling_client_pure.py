# SPDX-License-Identifier: GPL-3.0-or-later
"""SignalingClient pure transform unit test — cycle 169.677 omit 제거 path.

순수 helper (Qt 의존 부재) 만 test — PyQt6 QObject 인스턴스화 회피.
"""

from __future__ import annotations


class TestWireToInternalTransform:
    def test_from_key_renamed_to_from_underscore(self) -> None:
        from app.net.signaling_client import _wire_to_internal

        result = _wire_to_internal({"type": "OFFER", "from": "alice", "sdp": "x"})
        assert "from_" in result
        assert "from" not in result
        assert result["from_"] == "alice"

    def test_no_from_key_passthrough(self) -> None:
        from app.net.signaling_client import _wire_to_internal

        payload = {"type": "PEERS", "peers": []}
        result = _wire_to_internal(payload)
        assert result == payload

    def test_existing_from_underscore_preserved(self) -> None:
        # 한글 주석 — from_ 가 이미 존재 시 변환 차단 (idempotent)
        from app.net.signaling_client import _wire_to_internal

        payload = {"from_": "bob", "from": "alice"}
        result = _wire_to_internal(payload)
        # from_ 가 이미 있으니 from → from_ 치환 차단
        assert result == payload


class TestInternalToWireTransform:
    def test_from_underscore_renamed_to_from(self) -> None:
        from app.net.signaling_client import _internal_to_wire

        result = _internal_to_wire({"type": "OFFER", "from_": "alice", "sdp": "x"})
        assert "from" in result
        assert "from_" not in result
        assert result["from"] == "alice"

    def test_no_from_underscore_passthrough(self) -> None:
        from app.net.signaling_client import _internal_to_wire

        payload = {"type": "JOIN", "room": "r"}
        result = _internal_to_wire(payload)
        assert result == payload


class TestRoundTrip:
    def test_internal_wire_internal_idempotent(self) -> None:
        # 한글 주석 — internal → wire → internal round-trip 정합
        from app.net.signaling_client import (
            _internal_to_wire, _wire_to_internal,
        )

        original = {"type": "ANSWER", "from_": "bob", "sdp": "data"}
        wire = _internal_to_wire(original)
        recovered = _wire_to_internal(wire)
        assert recovered == original
