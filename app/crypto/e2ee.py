# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk Phase 2 E2EE — AES-256-GCM + X25519 ECDH + HKDF.

본 module = Phase 2 E2EE 의 첫 단계 = symmetric 암호화 + ephemeral 키 교환.
완전 Signal Protocol (Double Ratchet + 3-DH + Sender Keys) 통합 = 별도 cycle.

함수:
- ``generate_aes_key`` — AES-256 (32 byte) 키 생성 (`secrets.token_bytes`)
- ``aes_gcm_encrypt`` — AES-256-GCM 암호화 (nonce + ciphertext + tag)
- ``aes_gcm_decrypt`` — 복호화 + tag 검증
- ``generate_x25519_keypair`` — Curve25519 ECDH keypair 생성
- ``x25519_shared_secret`` — DH shared secret 계산
- ``hkdf_derive`` — HKDF-SHA256 키 유도 (shared secret → AES key)

모든 함수 = stateless. 키 저장 = caller 책임.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from typing import Final, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# AES-256 키 길이
_AES_KEY_BYTES: Final[int] = 32
# AES-GCM nonce 길이 — NIST SP 800-38D 권장 96-bit
_GCM_NONCE_BYTES: Final[int] = 12


@dataclass(frozen=True, slots=True)
class EncryptedPayload:
    """AES-GCM 출력 통합 dataclass.

    Attributes
    ----------
    nonce : bytes
        12 byte random nonce (재사용 절대 금지).
    ciphertext : bytes
        AES-GCM 암호문 + 16 byte auth tag 의 결합.
    """

    nonce: bytes
    ciphertext: bytes

    def to_bytes(self) -> bytes:
        """wire format: ``nonce || ciphertext`` (caller 측 분리)."""

        return self.nonce + self.ciphertext

    @classmethod
    def from_bytes(cls, raw: bytes) -> "EncryptedPayload":
        """``to_bytes`` 의 역변환. 최소 길이 = nonce(12) + tag(16) = 28 byte."""

        if len(raw) < _GCM_NONCE_BYTES + 16:
            raise ValueError(
                f"EncryptedPayload 길이 부족 — len={len(raw)} (최소 28 필요)"
            )
        return cls(nonce=raw[:_GCM_NONCE_BYTES], ciphertext=raw[_GCM_NONCE_BYTES:])


# ---------------------------------------------------------------------------
# AES-256-GCM symmetric 암호화
# ---------------------------------------------------------------------------


def generate_aes_key() -> bytes:
    """AES-256 키 32 byte 생성 — `secrets.token_bytes`.

    Returns
    -------
    bytes
        32 byte random key. 캐싱 + 보관 = caller 책임.
    """

    return secrets.token_bytes(_AES_KEY_BYTES)


def aes_gcm_encrypt(
    key: bytes,
    plaintext: bytes,
    *,
    associated_data: bytes | None = None,
) -> EncryptedPayload:
    """AES-256-GCM 암호화.

    Parameters
    ----------
    key : bytes
        32 byte AES-256 키.
    plaintext : bytes
        암호화 대상.
    associated_data : bytes | None
        AAD — 인증만 (암호화 안 됨). 헤더 metadata 용도.

    Returns
    -------
    EncryptedPayload
        nonce + ciphertext (auth tag 포함).

    Raises
    ------
    ValueError
        key 길이가 32 byte 가 아닌 경우.
    """

    if len(key) != _AES_KEY_BYTES:
        raise ValueError(f"AES-256 키 길이 불일치 — got={len(key)} (기대 32)")

    aesgcm = AESGCM(key)
    nonce = os.urandom(_GCM_NONCE_BYTES)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
    return EncryptedPayload(nonce=nonce, ciphertext=ciphertext)


def aes_gcm_decrypt(
    key: bytes,
    payload: EncryptedPayload,
    *,
    associated_data: bytes | None = None,
) -> bytes:
    """AES-256-GCM 복호화 + tag 검증.

    Raises
    ------
    ValueError
        key 길이 불일치.
    cryptography.exceptions.InvalidTag
        auth tag 검증 실패 (tampering 또는 잘못된 키).
    """

    if len(key) != _AES_KEY_BYTES:
        raise ValueError(f"AES-256 키 길이 불일치 — got={len(key)} (기대 32)")

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(payload.nonce, payload.ciphertext, associated_data)


# ---------------------------------------------------------------------------
# X25519 ECDH keypair + shared secret
# ---------------------------------------------------------------------------


def generate_x25519_keypair() -> Tuple[bytes, bytes]:
    """X25519 keypair 생성.

    Returns
    -------
    tuple[bytes, bytes]
        (private_key_raw, public_key_raw). 각 32 byte.
    """

    sk = X25519PrivateKey.generate()
    sk_raw = sk.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pk_raw = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return (sk_raw, pk_raw)


def x25519_shared_secret(private_key_raw: bytes, peer_public_key_raw: bytes) -> bytes:
    """X25519 ECDH — shared secret 32 byte 계산.

    Returns
    -------
    bytes
        32 byte shared secret. HKDF 의 input 으로 사용 권장 (직접 키 사용 금지).
    """

    if len(private_key_raw) != 32 or len(peer_public_key_raw) != 32:
        raise ValueError(
            "X25519 키 길이 불일치 — private/public 32 byte 의무"
        )
    sk = X25519PrivateKey.from_private_bytes(private_key_raw)
    pk = X25519PublicKey.from_public_bytes(peer_public_key_raw)
    return sk.exchange(pk)


# ---------------------------------------------------------------------------
# HKDF-SHA256 키 유도
# ---------------------------------------------------------------------------


def hkdf_derive(
    shared_secret: bytes,
    *,
    salt: bytes | None = None,
    info: bytes = b"tootalk-e2ee-v1",
    length: int = 32,
) -> bytes:
    """HKDF-SHA256 — shared secret → 대칭 키.

    Parameters
    ----------
    shared_secret : bytes
        ``x25519_shared_secret`` 결과.
    salt : bytes | None
        non-secret random salt (None 이면 zero bytes).
    info : bytes
        application-specific context — domain separation.
    length : int
        출력 키 길이 (default 32 = AES-256).

    Returns
    -------
    bytes
        파생 키.
    """

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
    )
    return hkdf.derive(shared_secret)


def ecdh_derive_aes_key(
    my_private_raw: bytes,
    peer_public_raw: bytes,
    *,
    salt: bytes | None = None,
    info: bytes = b"tootalk-e2ee-v1",
) -> bytes:
    """X25519 ECDH + HKDF 통합 — 단일 호출 의 AES-256 키 유도.

    Returns
    -------
    bytes
        32 byte AES-256 키 — `aes_gcm_encrypt` 의 input.
    """

    shared = x25519_shared_secret(my_private_raw, peer_public_raw)
    return hkdf_derive(shared, salt=salt, info=info, length=_AES_KEY_BYTES)
