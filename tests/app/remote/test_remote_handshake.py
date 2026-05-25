# SPDX-License-Identifier: GPL-3.0-or-later
"""permission on-channel handshake headless test — cycle 169.779 신설.

Exec Plan M3a 검증. control 채널 권한 교환(req/grant/deny/revoke) wire round-trip +
grant_request 생성 + verify_revoke 상수시간 대조 + 잘못된 kind decode 거부.
"""

from __future__ import annotations

import pytest

from app.remote.permission import (
    PermissionMode,
    PermissionRequest,
    check_grant_active,
    derive_revoke_token,
)
from app.remote.remote_handshake import (
    HandshakeKind,
    decode_deny,
    decode_grant,
    decode_kind,
    decode_request,
    decode_revoke,
    encode_deny,
    encode_grant,
    encode_request,
    encode_revoke,
    grant_request,
    verify_revoke,
)

_NOW_MS = 1_700_000_000_000


def _request() -> PermissionRequest:
    return PermissionRequest(
        requester_user_id=11,
        target_user_id=22,
        mode=PermissionMode.HELP,
        duration_seconds=300,
        reason="OBS 설정 도움",
    )


class TestGrantRequest:
    def test_grant_from_request(self) -> None:
        grant = grant_request(_request(), _NOW_MS)
        assert grant.granted_at_ms == _NOW_MS
        assert grant.expires_at_ms == _NOW_MS + 300 * 1000
        assert len(grant.revoke_token) == 32
        assert check_grant_active(grant, _NOW_MS + 1000) is True
        assert check_grant_active(grant, _NOW_MS + 300_001) is False

    def test_grant_explicit_revoke_token(self) -> None:
        token = derive_revoke_token()
        grant = grant_request(_request(), _NOW_MS, revoke_token=token)
        assert grant.revoke_token == token


class TestRequestWire:
    def test_request_round_trip(self) -> None:
        req = _request()
        decoded = decode_request(encode_request(req))
        assert decoded == req

    def test_decode_kind(self) -> None:
        assert decode_kind(encode_request(_request())) is HandshakeKind.REQUEST


class TestGrantWire:
    def test_grant_round_trip(self) -> None:
        grant = grant_request(_request(), _NOW_MS)
        decoded = decode_grant(encode_grant(grant))
        assert decoded == grant
        assert decode_kind(encode_grant(grant)) is HandshakeKind.GRANT


class TestDenyWire:
    def test_deny_round_trip(self) -> None:
        data = encode_deny("사용자 거절")
        assert decode_kind(data) is HandshakeKind.DENY
        assert decode_deny(data) == "사용자 거절"


class TestRevokeWire:
    def test_revoke_round_trip(self) -> None:
        token = derive_revoke_token()
        data = encode_revoke(token)
        assert decode_kind(data) is HandshakeKind.REVOKE
        assert decode_revoke(data) == token

    def test_verify_revoke_match(self) -> None:
        grant = grant_request(_request(), _NOW_MS)
        assert verify_revoke(grant, grant.revoke_token) is True

    def test_verify_revoke_mismatch(self) -> None:
        grant = grant_request(_request(), _NOW_MS)
        assert verify_revoke(grant, derive_revoke_token()) is False


class TestWrongKindRejected:
    def test_decode_grant_on_request_raises(self) -> None:
        with pytest.raises(ValueError):
            decode_grant(encode_request(_request()))

    def test_decode_request_on_deny_raises(self) -> None:
        with pytest.raises(ValueError):
            decode_request(encode_deny("x"))

    def test_decode_revoke_on_grant_raises(self) -> None:
        grant = grant_request(_request(), _NOW_MS)
        with pytest.raises(ValueError):
            decode_revoke(encode_grant(grant))
