# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.crypto.e2ee`` Phase 2 E2EE helper 단위 테스트."""

from __future__ import annotations

import pytest
from cryptography.exceptions import InvalidTag

from app.crypto.e2ee import (
    EncryptedPayload,
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    ecdh_derive_aes_key,
    generate_aes_key,
    generate_x25519_keypair,
    hkdf_derive,
    x25519_shared_secret,
)


# ---------------------------------------------------------------------------
# 1. AES-256-GCM
# ---------------------------------------------------------------------------


class TestAesGcm:
    def test_key_is_32_bytes(self) -> None:
        key = generate_aes_key()
        assert len(key) == 32
        assert isinstance(key, bytes)

    def test_key_uniqueness(self) -> None:
        keys = {generate_aes_key() for _ in range(50)}
        assert len(keys) == 50

    def test_round_trip(self) -> None:
        key = generate_aes_key()
        plaintext = b"hello tootalk E2EE"
        payload = aes_gcm_encrypt(key, plaintext)
        decoded = aes_gcm_decrypt(key, payload)
        assert decoded == plaintext

    def test_round_trip_korean_utf8(self) -> None:
        # 한글 UTF-8 byte-safe
        key = generate_aes_key()
        plaintext = "안녕하세요 TooTalk 종단간 암호화".encode("utf-8")
        payload = aes_gcm_encrypt(key, plaintext)
        assert aes_gcm_decrypt(key, payload) == plaintext

    def test_round_trip_with_aad(self) -> None:
        key = generate_aes_key()
        plaintext = b"secret body"
        aad = b"public header v1"
        payload = aes_gcm_encrypt(key, plaintext, associated_data=aad)
        assert aes_gcm_decrypt(key, payload, associated_data=aad) == plaintext

    def test_wrong_aad_rejected(self) -> None:
        key = generate_aes_key()
        payload = aes_gcm_encrypt(key, b"body", associated_data=b"aad-v1")
        with pytest.raises(InvalidTag):
            aes_gcm_decrypt(key, payload, associated_data=b"aad-v2")

    def test_wrong_key_rejected(self) -> None:
        key1 = generate_aes_key()
        key2 = generate_aes_key()
        payload = aes_gcm_encrypt(key1, b"secret")
        with pytest.raises(InvalidTag):
            aes_gcm_decrypt(key2, payload)

    def test_tampered_ciphertext_rejected(self) -> None:
        key = generate_aes_key()
        payload = aes_gcm_encrypt(key, b"original")
        # ciphertext 1 byte flip
        tampered = bytearray(payload.ciphertext)
        tampered[0] ^= 0x01
        payload_bad = EncryptedPayload(nonce=payload.nonce, ciphertext=bytes(tampered))
        with pytest.raises(InvalidTag):
            aes_gcm_decrypt(key, payload_bad)

    def test_nonce_uniqueness_per_encrypt(self) -> None:
        # 같은 키 + 같은 평문 의 nonce 매 호출 random
        key = generate_aes_key()
        p1 = aes_gcm_encrypt(key, b"same")
        p2 = aes_gcm_encrypt(key, b"same")
        assert p1.nonce != p2.nonce
        # ciphertext 도 nonce 차이 의 의 다름
        assert p1.ciphertext != p2.ciphertext

    def test_invalid_key_length(self) -> None:
        with pytest.raises(ValueError, match="AES-256 키 길이 불일치"):
            aes_gcm_encrypt(b"short", b"body")
        with pytest.raises(ValueError, match="AES-256 키 길이 불일치"):
            aes_gcm_decrypt(
                b"short",
                EncryptedPayload(nonce=b"\x00" * 12, ciphertext=b"\x00" * 16),
            )


class TestEncryptedPayloadWireFormat:
    def test_to_bytes_round_trip(self) -> None:
        key = generate_aes_key()
        payload = aes_gcm_encrypt(key, b"wire format test")
        wire = payload.to_bytes()
        # nonce(12) + ciphertext (tag 16 포함)
        assert len(wire) >= 12 + 16
        # nonce 추출 검증
        assert wire[:12] == payload.nonce

    def test_from_bytes_round_trip(self) -> None:
        key = generate_aes_key()
        payload = aes_gcm_encrypt(key, b"round")
        wire = payload.to_bytes()
        restored = EncryptedPayload.from_bytes(wire)
        assert restored.nonce == payload.nonce
        assert restored.ciphertext == payload.ciphertext
        assert aes_gcm_decrypt(key, restored) == b"round"

    def test_from_bytes_too_short(self) -> None:
        with pytest.raises(ValueError, match="EncryptedPayload 길이 부족"):
            EncryptedPayload.from_bytes(b"\x00" * 27)


# ---------------------------------------------------------------------------
# 2. X25519 ECDH
# ---------------------------------------------------------------------------


class TestX25519Ecdh:
    def test_keypair_format(self) -> None:
        sk, pk = generate_x25519_keypair()
        assert len(sk) == 32
        assert len(pk) == 32
        assert isinstance(sk, bytes)
        assert isinstance(pk, bytes)
        assert sk != pk  # private + public 별개

    def test_keypair_uniqueness(self) -> None:
        sks = {generate_x25519_keypair()[0] for _ in range(20)}
        assert len(sks) == 20

    def test_shared_secret_symmetric(self) -> None:
        # Alice + Bob 의 keypair 의 ECDH 결과 동일
        sk_a, pk_a = generate_x25519_keypair()
        sk_b, pk_b = generate_x25519_keypair()
        shared_a = x25519_shared_secret(sk_a, pk_b)
        shared_b = x25519_shared_secret(sk_b, pk_a)
        assert shared_a == shared_b
        assert len(shared_a) == 32

    def test_shared_secret_different_pairs(self) -> None:
        # 다른 pair 의 shared secret 별개
        sk_a, _ = generate_x25519_keypair()
        _, pk_b = generate_x25519_keypair()
        _, pk_c = generate_x25519_keypair()
        s_ab = x25519_shared_secret(sk_a, pk_b)
        s_ac = x25519_shared_secret(sk_a, pk_c)
        assert s_ab != s_ac

    def test_invalid_key_length(self) -> None:
        with pytest.raises(ValueError, match="X25519 키 길이 불일치"):
            x25519_shared_secret(b"\x00" * 31, b"\x00" * 32)
        with pytest.raises(ValueError, match="X25519 키 길이 불일치"):
            x25519_shared_secret(b"\x00" * 32, b"\x00" * 33)


# ---------------------------------------------------------------------------
# 3. HKDF
# ---------------------------------------------------------------------------


class TestHkdf:
    def test_deterministic(self) -> None:
        # 같은 input → 같은 output
        ss = b"\x42" * 32
        k1 = hkdf_derive(ss)
        k2 = hkdf_derive(ss)
        assert k1 == k2
        assert len(k1) == 32

    def test_different_salt(self) -> None:
        ss = b"\x42" * 32
        k1 = hkdf_derive(ss, salt=b"salt-a")
        k2 = hkdf_derive(ss, salt=b"salt-b")
        assert k1 != k2

    def test_different_info(self) -> None:
        ss = b"\x42" * 32
        k1 = hkdf_derive(ss, info=b"context-a")
        k2 = hkdf_derive(ss, info=b"context-b")
        assert k1 != k2

    def test_custom_length(self) -> None:
        k = hkdf_derive(b"\x42" * 32, length=64)
        assert len(k) == 64


# ---------------------------------------------------------------------------
# 4. ECDH + HKDF 통합 — 실 E2EE 흐름
# ---------------------------------------------------------------------------


class TestE2EEFullFlow:
    def test_alice_bob_full_round_trip(self) -> None:
        """Alice + Bob 의 ECDH → HKDF AES key → 메시지 송수신 전체 흐름."""

        # 1. keypair 생성 — Alice + Bob
        sk_a, pk_a = generate_x25519_keypair()
        sk_b, pk_b = generate_x25519_keypair()

        # 2. ECDH + HKDF — 양측 동일 AES key 유도
        k_a = ecdh_derive_aes_key(sk_a, pk_b)
        k_b = ecdh_derive_aes_key(sk_b, pk_a)
        assert k_a == k_b

        # 3. Alice → Bob 메시지 암호화
        message = "TooTalk Phase 2 종단간 암호화 첫 메시지".encode("utf-8")
        payload = aes_gcm_encrypt(k_a, message)

        # 4. Bob 복호화
        decoded = aes_gcm_decrypt(k_b, payload)
        assert decoded == message

    def test_third_party_cannot_decrypt(self) -> None:
        """Eve (third party) 의 ECDH 결과 = Alice/Bob shared secret 과 다름."""

        sk_a, pk_a = generate_x25519_keypair()
        sk_b, pk_b = generate_x25519_keypair()
        sk_e, _ = generate_x25519_keypair()

        k_ab = ecdh_derive_aes_key(sk_a, pk_b)
        k_ea = ecdh_derive_aes_key(sk_e, pk_a)
        assert k_ab != k_ea

        payload = aes_gcm_encrypt(k_ab, b"secret")
        with pytest.raises(InvalidTag):
            aes_gcm_decrypt(k_ea, payload)
