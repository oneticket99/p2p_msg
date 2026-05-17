# SPDX-License-Identifier: GPL-3.0-or-later
"""Double Ratchet minimal — chain key + message key derive (Signal Protocol 정합).

본 module = Signal Double Ratchet (Open Whisper Systems) 의 KDF chain layer.
완전 ratchet (DH ratchet step + skipped message keys + header encryption) = 별도 cycle.

본 cycle 의 범위:
- ``ChainKey`` dataclass — current chain key + counter
- ``derive_message_key`` — HMAC-SHA256 (chain_key, b"\\x01") → message key (forward secrecy)
- ``advance_chain_key`` — HMAC-SHA256 (chain_key, b"\\x02") → next chain key
- ``ratchet_chain`` — message key + next chain key 동시 산출

KDF constants = Signal Protocol spec 정합:
- 0x01 = message key derive
- 0x02 = chain key advance
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from hashlib import sha256
from typing import Final, Tuple

from app.crypto.e2ee import EncryptedPayload, aes_gcm_decrypt, aes_gcm_encrypt

# Signal Protocol KDF separators (RFC-defined byte values)
_MESSAGE_KEY_SEED: Final[bytes] = b"\x01"
_CHAIN_KEY_SEED: Final[bytes] = b"\x02"

# chain key + message key 길이 = 32 byte (AES-256 + HMAC-SHA256)
_KEY_BYTES: Final[int] = 32


@dataclass(frozen=True, slots=True)
class ChainKey:
    """Sending 또는 receiving chain 의 현재 상태.

    Attributes
    ----------
    key : bytes
        32 byte chain key (HMAC-SHA256 input).
    counter : int
        0부터 증가하는 메시지 번호 — replay 검출 + 순서 보장.
    """

    key: bytes
    counter: int = 0

    def __post_init__(self) -> None:
        if len(self.key) != _KEY_BYTES:
            raise ValueError(f"chain_key 길이 불일치 — len={len(self.key)} (기대 {_KEY_BYTES})")
        if self.counter < 0:
            raise ValueError(f"counter 음수 불가 — {self.counter}")


def _hmac_sha256(key: bytes, data: bytes) -> bytes:
    """HMAC-SHA256 wrapper — 32 byte 출력 의무."""

    return hmac.new(key, data, sha256).digest()


def derive_message_key(chain: ChainKey) -> bytes:
    """현재 chain key → 메시지 키 (32 byte AES-256 key).

    Notes
    -----
    Signal Protocol = `MK = HMAC-SHA256(CK, 0x01)`.
    """

    return _hmac_sha256(chain.key, _MESSAGE_KEY_SEED)


def advance_chain_key(chain: ChainKey) -> ChainKey:
    """chain key advance — `CK_next = HMAC-SHA256(CK, 0x02)`.

    counter +1 — forward secrecy 보장.
    """

    next_key = _hmac_sha256(chain.key, _CHAIN_KEY_SEED)
    return ChainKey(key=next_key, counter=chain.counter + 1)


def ratchet_chain(chain: ChainKey) -> Tuple[bytes, ChainKey]:
    """message key 산출 + chain key advance — 1회 호출 의 atomic step.

    Returns
    -------
    tuple[bytes, ChainKey]
        (message_key, next_chain_key).
    """

    mk = derive_message_key(chain)
    next_chain = advance_chain_key(chain)
    return (mk, next_chain)


# ---------------------------------------------------------------------------
# 메시지 단위 암호화 — ChainKey + plaintext → EncryptedPayload + advance
# ---------------------------------------------------------------------------


def encrypt_message(
    chain: ChainKey,
    plaintext: bytes,
    *,
    associated_data: bytes | None = None,
) -> Tuple[EncryptedPayload, ChainKey]:
    """Double Ratchet step — chain → message key derive + AES-GCM 암호화.

    Returns
    -------
    tuple[EncryptedPayload, ChainKey]
        (ciphertext, advanced chain). caller 는 advanced chain 의 의무 저장.
    """

    mk, next_chain = ratchet_chain(chain)
    payload = aes_gcm_encrypt(mk, plaintext, associated_data=associated_data)
    return (payload, next_chain)


def decrypt_message(
    chain: ChainKey,
    payload: EncryptedPayload,
    *,
    associated_data: bytes | None = None,
) -> Tuple[bytes, ChainKey]:
    """수신 측 Double Ratchet step — chain → message key + AES-GCM 복호화.

    Notes
    -----
    동일 counter 의 chain key 가 양측 = 동일 message key 보장 (Signal symmetric ratchet).
    skipped key 처리 (재정렬) = 별도 cycle.
    """

    mk, next_chain = ratchet_chain(chain)
    plaintext = aes_gcm_decrypt(mk, payload, associated_data=associated_data)
    return (plaintext, next_chain)
