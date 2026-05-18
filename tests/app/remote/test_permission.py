# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.remote.permission`` 단위 테스트.

Pattern A (도움-mode) + Pattern B (제어-mode) 의 permission grant model 검증.
expiry + revoke_token + scope 정합 + 음수/0/상한 ValueError.
"""

from __future__ import annotations

import pytest

from app.remote.permission import (
    PermissionGrant,
    PermissionMode,
    PermissionRequest,
    check_grant_active,
    derive_revoke_token,
)


def _valid_request() -> PermissionRequest:
    """기본 valid HELP request."""

    return PermissionRequest(
        requester_user_id=1,
        target_user_id=2,
        mode=PermissionMode.HELP,
        duration_seconds=300,
        reason="OBS 설정 도움",
    )


def _valid_grant(request: PermissionRequest | None = None) -> PermissionGrant:
    """기본 valid grant — 1700000000000 시점 의 300초 활성."""

    req = request or _valid_request()
    return PermissionGrant(
        request=req,
        granted_at_ms=1_700_000_000_000,
        expires_at_ms=1_700_000_000_000 + req.duration_seconds * 1000,
        revoke_token=derive_revoke_token(),
        scope="screen+input",
    )


class TestPermissionRequestValidation:
    """``PermissionRequest`` dataclass 검증."""

    def test_valid_help_construction(self) -> None:
        req = _valid_request()
        assert req.mode == PermissionMode.HELP
        assert req.duration_seconds == 300

    def test_valid_control_construction(self) -> None:
        req = PermissionRequest(
            requester_user_id=1,
            target_user_id=2,
            mode=PermissionMode.CONTROL,
            duration_seconds=3600,
            reason="unattended access",
        )
        assert req.mode == PermissionMode.CONTROL

    def test_zero_requester_rejected(self) -> None:
        with pytest.raises(ValueError, match="requester_user_id 양수 의무"):
            PermissionRequest(
                requester_user_id=0,
                target_user_id=2,
                mode=PermissionMode.HELP,
                duration_seconds=300,
                reason="x",
            )

    def test_negative_target_rejected(self) -> None:
        with pytest.raises(ValueError, match="target_user_id 양수 의무"):
            PermissionRequest(
                requester_user_id=1,
                target_user_id=-1,
                mode=PermissionMode.HELP,
                duration_seconds=300,
                reason="x",
            )

    def test_self_requester_target_rejected(self) -> None:
        with pytest.raises(ValueError, match="requester \\+ target 동일"):
            PermissionRequest(
                requester_user_id=1,
                target_user_id=1,
                mode=PermissionMode.HELP,
                duration_seconds=300,
                reason="x",
            )

    def test_zero_duration_rejected(self) -> None:
        with pytest.raises(ValueError, match="duration_seconds 양수 의무"):
            PermissionRequest(
                requester_user_id=1,
                target_user_id=2,
                mode=PermissionMode.HELP,
                duration_seconds=0,
                reason="x",
            )

    def test_duration_exceeds_max_rejected(self) -> None:
        with pytest.raises(ValueError, match="duration_seconds 상한 초과"):
            PermissionRequest(
                requester_user_id=1,
                target_user_id=2,
                mode=PermissionMode.HELP,
                duration_seconds=86_401,
                reason="x",
            )

    def test_empty_reason_rejected(self) -> None:
        with pytest.raises(ValueError, match="reason 빈 문자열 불가"):
            PermissionRequest(
                requester_user_id=1,
                target_user_id=2,
                mode=PermissionMode.HELP,
                duration_seconds=300,
                reason="",
            )


class TestPermissionGrantValidation:
    """``PermissionGrant`` dataclass 검증."""

    def test_valid_construction(self) -> None:
        grant = _valid_grant()
        assert grant.scope == "screen+input"
        assert len(grant.revoke_token) == 32

    def test_negative_granted_at_rejected(self) -> None:
        with pytest.raises(ValueError, match="granted_at_ms 음수 불가"):
            PermissionGrant(
                request=_valid_request(),
                granted_at_ms=-1,
                expires_at_ms=100,
                revoke_token=derive_revoke_token(),
                scope="x",
            )

    def test_expires_before_granted_rejected(self) -> None:
        with pytest.raises(ValueError, match="expires_at_ms 의 granted_at_ms 초과 의무"):
            PermissionGrant(
                request=_valid_request(),
                granted_at_ms=100,
                expires_at_ms=50,
                revoke_token=derive_revoke_token(),
                scope="x",
            )

    def test_invalid_revoke_token_length(self) -> None:
        with pytest.raises(ValueError, match="revoke_token 길이 불일치"):
            PermissionGrant(
                request=_valid_request(),
                granted_at_ms=100,
                expires_at_ms=200,
                revoke_token=b"short",
                scope="x",
            )

    def test_empty_scope_rejected(self) -> None:
        with pytest.raises(ValueError, match="scope 빈 문자열 불가"):
            PermissionGrant(
                request=_valid_request(),
                granted_at_ms=100,
                expires_at_ms=200,
                revoke_token=derive_revoke_token(),
                scope="",
            )


class TestDeriveRevokeToken:
    """``derive_revoke_token`` CSPRNG 검증."""

    def test_token_length(self) -> None:
        token = derive_revoke_token()
        assert len(token) == 32

    def test_tokens_are_distinct(self) -> None:
        t1 = derive_revoke_token()
        t2 = derive_revoke_token()
        assert t1 != t2


class TestCheckGrantActive:
    """``check_grant_active`` expiry 검증."""

    def test_active_within_window(self) -> None:
        grant = _valid_grant()
        # granted = 1_700_000_000_000, expires = + 300_000
        assert check_grant_active(grant, 1_700_000_001_000) is True

    def test_inactive_after_expiry(self) -> None:
        grant = _valid_grant()
        # 300 초 후 + 1 초
        assert check_grant_active(grant, 1_700_000_301_000) is False

    def test_inactive_before_grant(self) -> None:
        grant = _valid_grant()
        assert check_grant_active(grant, 1_600_000_000_000) is False

    def test_active_at_granted_boundary(self) -> None:
        grant = _valid_grant()
        # 정확 시작 시점 = 활성
        assert check_grant_active(grant, grant.granted_at_ms) is True

    def test_inactive_at_expires_boundary(self) -> None:
        grant = _valid_grant()
        # 정확 expires 시점 = 비활성 (< expires)
        assert check_grant_active(grant, grant.expires_at_ms) is False
