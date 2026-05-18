# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 원격 데스크탑 권한 model — 사이클 55.

memory `project_phase2_remote_control_differentiator.md` 정합. 친구간 1:1 원격
데스크탑 control 의 2 pattern 의무:

- **Pattern A (도움-mode)** — 상대 화면 view + 마우스 / 키보드 input forward.
  Toonation OBS 설정 도움 의 시나리오 (사용자 directive). 의무 = 사용자 명시 동의 +
  expiry + 1 click revoke.
- **Pattern B (제어-mode)** — full RDP 등가 의 unattended access. 의무 = 강한
  password + 추가 2FA + 항상 visible indicator (Apple Accessibility 정합).

본 module 범위
-------------
- ``PermissionMode`` Enum — 2 mode 식별
- ``PermissionRequest`` frozen dataclass — requester + target + mode + duration + reason
- ``PermissionGrant`` frozen dataclass — accepted + expires_at_ms + revoke_token + scope
- ``check_grant_active`` — grant expiry + mode 정합 검증
- ``derive_revoke_token`` — random 32 byte revoke token (1회용 revoke 인증)

본 cycle 의 범위 외 (별개 cycle):
- screen capture 의 platform-specific (Quartz / Win32 / X11)
- input event forward 의 platform-specific (CGEvent / SendInput / XTestFakeKey)
- accessibility permission 의 OS 권한 grant flow (macOS Privacy 의 Screen Recording + Accessibility)
- 항상 visible indicator widget (Pattern B 의 의무 UI)
- bandwidth estimation + ABR encoding (h264 / vp9 / raw RGB diff)
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import Enum
from typing import Final

# revoke token 길이 = 32 byte (CSPRNG)
_REVOKE_TOKEN_BYTES: Final[int] = 32
# 최대 grant 시간 = 24 시간 (안전 상한, Pattern B 도 24h 한도)
_MAX_DURATION_SECONDS: Final[int] = 24 * 60 * 60


class PermissionMode(str, Enum):
    """원격 데스크탑 권한 mode."""

    # Pattern A — view + input forward, expiry + revoke 의무
    HELP = "help"
    # Pattern B — unattended control, 2FA + visible indicator 의무
    CONTROL = "control"


@dataclass(frozen=True, slots=True)
class PermissionRequest:
    """원격 데스크탑 권한 의 요청 envelope.

    Attributes
    ----------
    requester_user_id : int
        요청자 식별자 (도움 요청 또는 control 요청 의 의무).
    target_user_id : int
        대상 사용자 식별자 (screen 공유 + input 수신 의무).
    mode : PermissionMode
        HELP 또는 CONTROL 의 2 mode.
    duration_seconds : int
        grant 유효 시간 (초). 0 < duration <= 86 400 의무.
    reason : str
        요청 사유 (UI 표시 의무, 사용자 의 grant 결정 의 의무).
    """

    requester_user_id: int
    target_user_id: int
    mode: PermissionMode
    duration_seconds: int
    reason: str

    def __post_init__(self) -> None:
        if self.requester_user_id <= 0:
            raise ValueError(
                f"requester_user_id 양수 의무 — {self.requester_user_id}"
            )
        if self.target_user_id <= 0:
            raise ValueError(
                f"target_user_id 양수 의무 — {self.target_user_id}"
            )
        if self.requester_user_id == self.target_user_id:
            raise ValueError("requester + target 동일 user_id 불가")
        if self.duration_seconds <= 0:
            raise ValueError(
                f"duration_seconds 양수 의무 — {self.duration_seconds}"
            )
        if self.duration_seconds > _MAX_DURATION_SECONDS:
            raise ValueError(
                f"duration_seconds 상한 초과 — {self.duration_seconds} "
                f"(최대 {_MAX_DURATION_SECONDS})"
            )
        if not self.reason:
            raise ValueError("reason 빈 문자열 불가 — 사용자 grant 의무 정합")


@dataclass(frozen=True, slots=True)
class PermissionGrant:
    """원격 데스크탑 권한 의 승인 결과.

    Attributes
    ----------
    request : PermissionRequest
        원본 요청 (불변 binding).
    granted_at_ms : int
        승인 시점 (UNIX epoch ms).
    expires_at_ms : int
        만료 시점 (granted_at_ms + duration_seconds * 1000).
    revoke_token : bytes
        revoke 의 1회용 인증 token (32 byte, CSPRNG).
    scope : str
        승인 범위 (예: "screen+input" / "screen_only"). 의무 = mode 정합.
    """

    request: PermissionRequest
    granted_at_ms: int
    expires_at_ms: int
    revoke_token: bytes
    scope: str

    def __post_init__(self) -> None:
        if self.granted_at_ms < 0:
            raise ValueError(
                f"granted_at_ms 음수 불가 — {self.granted_at_ms}"
            )
        if self.expires_at_ms <= self.granted_at_ms:
            raise ValueError(
                f"expires_at_ms 의 granted_at_ms 초과 의무 — "
                f"granted={self.granted_at_ms} expires={self.expires_at_ms}"
            )
        if len(self.revoke_token) != _REVOKE_TOKEN_BYTES:
            raise ValueError(
                f"revoke_token 길이 불일치 — "
                f"len={len(self.revoke_token)} (기대 {_REVOKE_TOKEN_BYTES})"
            )
        if not self.scope:
            raise ValueError("scope 빈 문자열 불가")


def derive_revoke_token() -> bytes:
    """1회용 revoke token 생성 — 32 byte CSPRNG."""

    return secrets.token_bytes(_REVOKE_TOKEN_BYTES)


def check_grant_active(grant: PermissionGrant, now_ms: int) -> bool:
    """grant 의 현재 시점 활성 여부 검증.

    Parameters
    ----------
    grant : PermissionGrant
        검증 대상 권한.
    now_ms : int
        현재 시점 (UNIX epoch ms, caller responsibility).

    Returns
    -------
    bool
        granted_at_ms <= now_ms < expires_at_ms = True. 그 외 = False.
    """

    return grant.granted_at_ms <= now_ms < grant.expires_at_ms
