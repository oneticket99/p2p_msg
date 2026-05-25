# SPDX-License-Identifier: GPL-3.0-or-later
"""원격 데스크탑 permission on-channel handshake — control 채널 protocol.

cycle 169.779 신설 — Exec Plan `docs/exec-plans/active/2026-05-25-remote-desktop-real-binding.md`
M3a. RemoteSessionRunner 의 grant 게이트가 사용할 ``PermissionGrant`` 를 살아있는 control
채널 위에서 교환하는 wire layer.

흐름(Pattern A — HELP):

1. controller(요청자) → target(피제어): ``REQUEST`` (PermissionRequest) 송신.
2. target 사용자가 승인 → ``grant_request`` 로 ``PermissionGrant`` 생성 → ``GRANT`` 송신.
   거절 → ``DENY`` (사유) 송신.
3. controller 가 GRANT 수신 → grant 보관(이후 RemoteSessionRunner 에 주입).
4. 어느 쪽이든 ``REVOKE`` (revoke_token) 송신 → 세션 즉시 종료. ``verify_revoke`` 로 token 대조.

control 채널은 input/frame 과 별도 label(`tootalk-remote-control`, ordered=true) 전제.
본 모듈은 채널 객체를 직접 알지 않고 bytes 직렬화 + 검증 함수만 제공한다(DI 정합).
"""

from __future__ import annotations

import hmac
import json
from enum import Enum
from typing import Any, Optional

from app.remote.permission import (
    PermissionGrant,
    PermissionMode,
    PermissionRequest,
    derive_revoke_token,
)

# control 채널 메시지 최상위 key
_KIND = "kind"


class HandshakeKind(str, Enum):
    """control 채널 메시지 종류."""

    REQUEST = "request"  # controller → target : 원격 권한 요청
    GRANT = "grant"  # target → controller : 승인 + grant
    DENY = "deny"  # target → controller : 거절 + 사유
    REVOKE = "revoke"  # 양쪽 : 세션 즉시 종료 (revoke_token 대조)


# ----------------------------------------------------------------------
# granter 측 결정 — request → grant 생성
# ----------------------------------------------------------------------

def grant_request(
    request: PermissionRequest,
    now_ms: int,
    *,
    scope: str = "screen+input",
    revoke_token: Optional[bytes] = None,
) -> PermissionGrant:
    """target 사용자 승인 시 ``PermissionRequest`` → ``PermissionGrant`` 생성.

    만료 = now_ms + duration_seconds * 1000. revoke_token 미지정 시 CSPRNG 생성.
    """

    token = revoke_token if revoke_token is not None else derive_revoke_token()
    return PermissionGrant(
        request=request,
        granted_at_ms=now_ms,
        expires_at_ms=now_ms + request.duration_seconds * 1000,
        revoke_token=token,
        scope=scope,
    )


def verify_revoke(grant: PermissionGrant, revoke_token: bytes) -> bool:
    """REVOKE 메시지의 token 이 grant 의 revoke_token 과 일치하는지 상수시간 대조."""

    return hmac.compare_digest(grant.revoke_token, revoke_token)


# ----------------------------------------------------------------------
# 와이어 직렬화 — control 채널 JSON (revoke_token 은 hex)
# ----------------------------------------------------------------------

def _request_to_obj(req: PermissionRequest) -> dict[str, Any]:
    return {
        "requester_user_id": req.requester_user_id,
        "target_user_id": req.target_user_id,
        "mode": req.mode.value,
        "duration_seconds": req.duration_seconds,
        "reason": req.reason,
    }


def _obj_to_request(obj: dict[str, Any]) -> PermissionRequest:
    return PermissionRequest(
        requester_user_id=int(obj["requester_user_id"]),
        target_user_id=int(obj["target_user_id"]),
        mode=PermissionMode(obj["mode"]),
        duration_seconds=int(obj["duration_seconds"]),
        reason=str(obj.get("reason") or ""),
    )


def encode_request(req: PermissionRequest) -> bytes:
    """``REQUEST`` 메시지 직렬화."""

    return json.dumps(
        {_KIND: HandshakeKind.REQUEST.value, "request": _request_to_obj(req)},
        ensure_ascii=False,
    ).encode("utf-8")


def encode_grant(grant: PermissionGrant) -> bytes:
    """``GRANT`` 메시지 직렬화 (revoke_token hex 인코딩)."""

    return json.dumps(
        {
            _KIND: HandshakeKind.GRANT.value,
            "request": _request_to_obj(grant.request),
            "granted_at_ms": grant.granted_at_ms,
            "expires_at_ms": grant.expires_at_ms,
            "revoke_token": grant.revoke_token.hex(),
            "scope": grant.scope,
        },
        ensure_ascii=False,
    ).encode("utf-8")


def encode_deny(reason: str) -> bytes:
    """``DENY`` 메시지 직렬화."""

    return json.dumps(
        {_KIND: HandshakeKind.DENY.value, "reason": reason}, ensure_ascii=False
    ).encode("utf-8")


def encode_revoke(revoke_token: bytes) -> bytes:
    """``REVOKE`` 메시지 직렬화 (revoke_token hex)."""

    return json.dumps(
        {_KIND: HandshakeKind.REVOKE.value, "revoke_token": revoke_token.hex()},
        ensure_ascii=False,
    ).encode("utf-8")


def decode_kind(data: bytes) -> HandshakeKind:
    """control 메시지의 kind 만 우선 추출 (dispatch 분기용)."""

    obj = json.loads(data.decode("utf-8"))
    return HandshakeKind(obj[_KIND])


def decode_request(data: bytes) -> PermissionRequest:
    obj = json.loads(data.decode("utf-8"))
    if obj.get(_KIND) != HandshakeKind.REQUEST.value:
        raise ValueError(f"REQUEST 아님 — kind={obj.get(_KIND)}")
    return _obj_to_request(obj["request"])


def decode_grant(data: bytes) -> PermissionGrant:
    obj = json.loads(data.decode("utf-8"))
    if obj.get(_KIND) != HandshakeKind.GRANT.value:
        raise ValueError(f"GRANT 아님 — kind={obj.get(_KIND)}")
    return PermissionGrant(
        request=_obj_to_request(obj["request"]),
        granted_at_ms=int(obj["granted_at_ms"]),
        expires_at_ms=int(obj["expires_at_ms"]),
        revoke_token=bytes.fromhex(obj["revoke_token"]),
        scope=str(obj["scope"]),
    )


def decode_deny(data: bytes) -> str:
    obj = json.loads(data.decode("utf-8"))
    if obj.get(_KIND) != HandshakeKind.DENY.value:
        raise ValueError(f"DENY 아님 — kind={obj.get(_KIND)}")
    return str(obj.get("reason") or "")


def decode_revoke(data: bytes) -> bytes:
    obj = json.loads(data.decode("utf-8"))
    if obj.get(_KIND) != HandshakeKind.REVOKE.value:
        raise ValueError(f"REVOKE 아님 — kind={obj.get(_KIND)}")
    return bytes.fromhex(obj["revoke_token"])
