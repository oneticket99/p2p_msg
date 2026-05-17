# SPDX-License-Identifier: GPL-3.0-or-later
"""Double Ratchet session state — root key + sending/receiving chain.

본 module = Signal Double Ratchet session 의 state holder + initialize helper.
DH ratchet step (X25519 keypair 매 turn 갱신) + skipped message keys = 별도 cycle.

State 구성:
- ``root_key`` (32 byte) — DH ratchet 의 master key
- ``sending_chain`` (ChainKey) — 송신 chain
- ``receiving_chain`` (ChainKey) — 수신 chain
- ``my_dh_keypair`` (sk, pk) — 본인 X25519
- ``peer_dh_public`` — 상대 X25519 public

초기화:
- ``initialize_session_initiator`` — Alice (먼저 메시지 송신) 측
- ``initialize_session_responder`` — Bob (수신 후 응답) 측
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

from app.crypto.double_ratchet import ChainKey
from app.crypto.e2ee import (
    generate_x25519_keypair,
    hkdf_derive,
    x25519_shared_secret,
)


# HKDF info string — domain separation (Signal Protocol 정합)
_ROOT_KEY_INFO: bytes = b"tootalk-ratchet-root-v1"
_CHAIN_KEY_INFO: bytes = b"tootalk-ratchet-chain-v1"


@dataclass(slots=True)
class SessionState:
    """Double Ratchet session 의 mutable state.

    Attributes
    ----------
    root_key : bytes
        32 byte master key — DH ratchet step 의 input.
    sending_chain : ChainKey | None
        송신 chain (counter 0~). None = 아직 송신 안 함.
    receiving_chain : ChainKey | None
        수신 chain. None = 아직 수신 안 함.
    my_dh_private : bytes
        본인 X25519 private (32 byte).
    my_dh_public : bytes
        본인 X25519 public (32 byte).
    peer_dh_public : bytes | None
        상대 X25519 public. None = 아직 수신 안 함.
    """

    root_key: bytes
    my_dh_private: bytes
    my_dh_public: bytes
    sending_chain: Optional[ChainKey] = None
    receiving_chain: Optional[ChainKey] = None
    peer_dh_public: Optional[bytes] = None

    def __post_init__(self) -> None:
        if len(self.root_key) != 32:
            raise ValueError(f"root_key 길이 불일치 — {len(self.root_key)} (32 의무)")
        if len(self.my_dh_private) != 32:
            raise ValueError("my_dh_private 길이 = 32 의무")
        if len(self.my_dh_public) != 32:
            raise ValueError("my_dh_public 길이 = 32 의무")
        if self.peer_dh_public is not None and len(self.peer_dh_public) != 32:
            raise ValueError("peer_dh_public 길이 = 32 의무")


def _derive_root_and_chain(shared_secret: bytes, current_root: bytes) -> Tuple[bytes, bytes]:
    """DH output + current root → next root + new chain key.

    Signal Protocol = HKDF(salt=root, ikm=DH_output, info=...) → 64 byte → split.

    Returns
    -------
    tuple[bytes, bytes]
        (next_root_key, new_chain_key).
    """

    # 64 byte = root(32) + chain(32) — Signal 정합
    kdf_out = hkdf_derive(
        shared_secret,
        salt=current_root,
        info=_ROOT_KEY_INFO,
        length=64,
    )
    return (kdf_out[:32], kdf_out[32:])


def initialize_session_initiator(
    *,
    shared_secret: bytes,
    peer_dh_public: bytes,
) -> SessionState:
    """Alice 측 session 초기화 — 첫 메시지 송신 직전.

    Parameters
    ----------
    shared_secret : bytes
        초기 X3DH 또는 pre-shared key (32 byte). Phase 1 = root key seed.
    peer_dh_public : bytes
        Bob 의 X25519 public key (32 byte). Phase 1 = 시그널링 경유 전달.

    Returns
    -------
    SessionState
        sending_chain 활성 (DH ratchet step 1 수행).
    """

    if len(shared_secret) != 32:
        raise ValueError("shared_secret 32 byte 의무")
    if len(peer_dh_public) != 32:
        raise ValueError("peer_dh_public 32 byte 의무")

    my_sk, my_pk = generate_x25519_keypair()

    # Alice 의 첫 DH ratchet step — DH(Alice_new, Bob_pre) → sending chain
    dh_out = x25519_shared_secret(my_sk, peer_dh_public)
    next_root, sending_chain_key = _derive_root_and_chain(dh_out, shared_secret)

    return SessionState(
        root_key=next_root,
        my_dh_private=my_sk,
        my_dh_public=my_pk,
        peer_dh_public=peer_dh_public,
        sending_chain=ChainKey(key=sending_chain_key, counter=0),
        receiving_chain=None,
    )


def initialize_session_responder(
    *,
    shared_secret: bytes,
) -> SessionState:
    """Bob 측 session 초기화 — Alice 첫 메시지 수신 직전.

    Notes
    -----
    Bob 은 Alice DH public 을 첫 메시지 헤더 의 의 수신. 본 함수 = pre-receive 상태.
    실 수신 시점에 ``advance_dh_ratchet`` (별도 cycle) 호출.
    """

    if len(shared_secret) != 32:
        raise ValueError("shared_secret 32 byte 의무")

    my_sk, my_pk = generate_x25519_keypair()

    return SessionState(
        root_key=shared_secret,  # 첫 DH ratchet 전 = shared_secret 자체
        my_dh_private=my_sk,
        my_dh_public=my_pk,
        peer_dh_public=None,
        sending_chain=None,
        receiving_chain=None,
    )
