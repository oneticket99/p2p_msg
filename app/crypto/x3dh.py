# SPDX-License-Identifier: GPL-3.0-or-later
"""X3DH (Extended Triple Diffie-Hellman) initial key agreement.

Signal Protocol 의 첫 메시지 송신 전 의 비대화형 키 교환. 4 ECDH 의 결합:

- ``DH1 = DH(IK_a, SPK_b)`` — Alice identity × Bob signed prekey (서로 인증)
- ``DH2 = DH(EK_a, IK_b)`` — Alice ephemeral × Bob identity (Alice 신선도)
- ``DH3 = DH(EK_a, SPK_b)`` — Alice ephemeral × Bob signed prekey (forward secrecy)
- ``DH4 = DH(EK_a, OPK_b)`` — Alice ephemeral × Bob one-time prekey (optional, post-compromise security)

shared_secret = HKDF(DH1 || DH2 || DH3 || DH4) → 32 byte AES-256 root key.

본 module = `initialize_session_initiator` 의 shared_secret input 의 생성.
완전 Signal X3DH 의 prekey bundle signing (Ed25519) = 별도 cycle (XEd25519 의 위탁).

API:
- ``PreKeyBundle`` — Bob 의 공개 키 bundle (IK_b + SPK_b + OPK_b optional)
- ``x3dh_initiator`` — Alice 단 + Bob bundle → (EK_a public, shared_secret)
- ``x3dh_responder`` — Bob 단 + Alice public + EK_a → shared_secret
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Optional, Tuple

from app.crypto.e2ee import (
    generate_x25519_keypair,
    hkdf_derive,
    x25519_shared_secret,
)


# HKDF info (Signal X3DH spec 정합)
_X3DH_INFO: Final[bytes] = b"tootalk-x3dh-v1"
# Signal 권장 = KDF input prefix 32 byte 0xFF (key agreement domain separation)
_KDF_PREFIX: Final[bytes] = b"\xff" * 32


@dataclass(frozen=True, slots=True)
class PreKeyBundle:
    """Bob 의 공개 X3DH bundle.

    Attributes
    ----------
    identity_public : bytes
        장기 identity key (32 byte X25519). 변경 시 사용자 alert + re-verify.
    signed_prekey_public : bytes
        중기 signed prekey (32 byte). XEd25519 서명 = 별도 cycle.
    one_time_prekey_public : bytes | None
        일회용 prekey (32 byte). 사용 후 폐기 (forward secrecy 강화).
        None = OPK fallback (security 약화).
    """

    identity_public: bytes
    signed_prekey_public: bytes
    one_time_prekey_public: Optional[bytes] = None

    def __post_init__(self) -> None:
        if len(self.identity_public) != 32:
            raise ValueError(f"identity_public 길이 = {len(self.identity_public)} (32 의무)")
        if len(self.signed_prekey_public) != 32:
            raise ValueError("signed_prekey_public 길이 32 의무")
        if self.one_time_prekey_public is not None and len(self.one_time_prekey_public) != 32:
            raise ValueError("one_time_prekey_public 길이 32 의무")


def _kdf_x3dh(dh_concat: bytes) -> bytes:
    """X3DH HKDF — Signal spec 정합. Returns 32 byte root key."""

    salt = b"\x00" * 32
    return hkdf_derive(
        _KDF_PREFIX + dh_concat,
        salt=salt,
        info=_X3DH_INFO,
        length=32,
    )


def x3dh_initiator(
    *,
    my_identity_private: bytes,
    bob_bundle: PreKeyBundle,
) -> Tuple[bytes, bytes, bytes]:
    """Alice 단 X3DH — Bob bundle 의 4 DH 결합 + shared secret 생성.

    Parameters
    ----------
    my_identity_private : bytes
        Alice 의 IK private (32 byte X25519).
    bob_bundle : PreKeyBundle
        Bob 공개 키 bundle.

    Returns
    -------
    tuple[bytes, bytes, bytes]
        (ephemeral_public, ephemeral_private, shared_secret).
        ephemeral_* = Alice 단 의 EK (메시지 헤더 의 첨부 의무).
        shared_secret = ``initialize_session_initiator`` 의 input.

    Raises
    ------
    ValueError
        my_identity_private 길이 불일치.
    """

    if len(my_identity_private) != 32:
        raise ValueError(f"my_identity_private 길이 = {len(my_identity_private)} (32)")

    # Alice ephemeral keypair 생성 (매 X3DH 단발)
    ek_priv, ek_pub = generate_x25519_keypair()

    # 4 DH 계산 (Signal spec 정합 순서)
    dh1 = x25519_shared_secret(my_identity_private, bob_bundle.signed_prekey_public)
    dh2 = x25519_shared_secret(ek_priv, bob_bundle.identity_public)
    dh3 = x25519_shared_secret(ek_priv, bob_bundle.signed_prekey_public)

    dh_concat = dh1 + dh2 + dh3
    if bob_bundle.one_time_prekey_public is not None:
        dh4 = x25519_shared_secret(ek_priv, bob_bundle.one_time_prekey_public)
        dh_concat += dh4

    shared = _kdf_x3dh(dh_concat)
    return (ek_pub, ek_priv, shared)


def x3dh_responder(
    *,
    my_identity_private: bytes,
    my_signed_prekey_private: bytes,
    my_one_time_prekey_private: Optional[bytes],
    alice_identity_public: bytes,
    alice_ephemeral_public: bytes,
) -> bytes:
    """Bob 단 X3DH — Alice 첫 메시지 헤더 의 EK + IK 수신 직후.

    Parameters
    ----------
    my_identity_private : bytes
        Bob IK private.
    my_signed_prekey_private : bytes
        Bob SPK private.
    my_one_time_prekey_private : bytes | None
        Bob OPK private (Alice 가 OPK 사용 시 만 의무, 사용 후 폐기).
    alice_identity_public : bytes
        Alice IK public (사전 알림 또는 메시지 헤더).
    alice_ephemeral_public : bytes
        Alice EK public (메시지 헤더).

    Returns
    -------
    bytes
        shared_secret (32 byte) — Alice 와 동일.

    Raises
    ------
    ValueError
        keypair 길이 불일치.
    """

    for name, raw in [
        ("my_identity_private", my_identity_private),
        ("my_signed_prekey_private", my_signed_prekey_private),
        ("alice_identity_public", alice_identity_public),
        ("alice_ephemeral_public", alice_ephemeral_public),
    ]:
        if len(raw) != 32:
            raise ValueError(f"{name} 길이 = {len(raw)} (32 의무)")
    if my_one_time_prekey_private is not None and len(my_one_time_prekey_private) != 32:
        raise ValueError("my_one_time_prekey_private 길이 32 의무")

    # Alice 4 DH 와 동일 결과 (peer 대칭 ECDH)
    # DH1 = DH(IK_a, SPK_b) — Alice IK pub × Bob SPK priv
    dh1 = x25519_shared_secret(my_signed_prekey_private, alice_identity_public)
    # DH2 = DH(EK_a, IK_b)
    dh2 = x25519_shared_secret(my_identity_private, alice_ephemeral_public)
    # DH3 = DH(EK_a, SPK_b)
    dh3 = x25519_shared_secret(my_signed_prekey_private, alice_ephemeral_public)

    dh_concat = dh1 + dh2 + dh3
    if my_one_time_prekey_private is not None:
        # DH4 = DH(EK_a, OPK_b)
        dh4 = x25519_shared_secret(my_one_time_prekey_private, alice_ephemeral_public)
        dh_concat += dh4

    return _kdf_x3dh(dh_concat)
