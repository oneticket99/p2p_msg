# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.backup.encrypted_backup`` 단위 테스트.

master password → HKDF derive backup key → AES-GCM 의 단일 ciphertext blob.
wire format bytes round-trip + wrong password InvalidTag + tampered blob 검증.
"""

from __future__ import annotations

import secrets

import pytest
from cryptography.exceptions import InvalidTag

from app.backup.encrypted_backup import (
    BackupBundle,
    BackupEntry,
    decrypt_backup,
    derive_backup_key,
    deserialize_bundle,
    encrypt_backup,
    serialize_bundle,
)
from app.crypto.e2ee import EncryptedPayload


def _sample_entries() -> list[BackupEntry]:
    """3 entry sample — 한글 + binary + 빈 plaintext."""

    return [
        BackupEntry(
            message_id="msg-1",
            plaintext="안녕하세요".encode("utf-8"),
            timestamp_ms=1_700_000_000_000,
        ),
        BackupEntry(
            message_id="msg-2",
            plaintext=b"\x00\xff\x01\xfe",
            timestamp_ms=1_700_000_001_000,
        ),
        BackupEntry(
            message_id="msg-3",
            plaintext=b"",
            timestamp_ms=1_700_000_002_000,
        ),
    ]


class TestBackupEntryValidation:
    """``BackupEntry`` dataclass 검증."""

    def test_valid_construction(self) -> None:
        entry = BackupEntry(
            message_id="m1", plaintext=b"hello", timestamp_ms=100
        )
        assert entry.message_id == "m1"
        assert entry.plaintext == b"hello"

    def test_empty_message_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="message_id 빈 문자열 불가"):
            BackupEntry(message_id="", plaintext=b"x", timestamp_ms=1)

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timestamp_ms 음수 불가"):
            BackupEntry(message_id="m", plaintext=b"x", timestamp_ms=-1)

    def test_zero_timestamp_ok(self) -> None:
        entry = BackupEntry(message_id="m", plaintext=b"x", timestamp_ms=0)
        assert entry.timestamp_ms == 0


class TestBackupBundleValidation:
    """``BackupBundle`` dataclass 검증."""

    def test_valid_construction(self) -> None:
        payload = EncryptedPayload(nonce=b"\x00" * 12, ciphertext=b"ct")
        bundle = BackupBundle(
            version="1",
            created_at_ms=100,
            salt=secrets.token_bytes(16),
            blob=payload,
        )
        assert bundle.version == "1"

    def test_empty_version_rejected(self) -> None:
        payload = EncryptedPayload(nonce=b"\x00" * 12, ciphertext=b"ct")
        with pytest.raises(ValueError, match="version 빈 문자열 불가"):
            BackupBundle(
                version="",
                created_at_ms=100,
                salt=secrets.token_bytes(16),
                blob=payload,
            )

    def test_negative_created_at_rejected(self) -> None:
        payload = EncryptedPayload(nonce=b"\x00" * 12, ciphertext=b"ct")
        with pytest.raises(ValueError, match="created_at_ms 음수 불가"):
            BackupBundle(
                version="1",
                created_at_ms=-1,
                salt=secrets.token_bytes(16),
                blob=payload,
            )

    def test_salt_length_mismatch(self) -> None:
        payload = EncryptedPayload(nonce=b"\x00" * 12, ciphertext=b"ct")
        with pytest.raises(ValueError, match="salt 길이 불일치"):
            BackupBundle(
                version="1",
                created_at_ms=100,
                salt=b"\x00" * 8,
                blob=payload,
            )


class TestDeriveBackupKey:
    """``derive_backup_key`` PBKDF2-HMAC-SHA256 stretching 검증 (사이클 50)."""

    def test_deterministic(self) -> None:
        salt = secrets.token_bytes(16)
        k1 = derive_backup_key("password", salt)
        k2 = derive_backup_key("password", salt)
        assert k1 == k2
        assert len(k1) == 32

    def test_pbkdf2_iteration_constant(self) -> None:
        """OWASP 2023 권장 의 600 000 iteration 의 정합 검증."""

        from app.backup.encrypted_backup import _PBKDF2_ITERATIONS

        assert _PBKDF2_ITERATIONS == 600_000

    def test_backup_version_is_v2(self) -> None:
        """encrypt_backup 의 BackupBundle 의 version field = v2 (PBKDF2 stretching)."""

        from app.backup.encrypted_backup import _BACKUP_VERSION

        assert _BACKUP_VERSION == "2"

    def test_v1_bundle_rejected_by_decrypt(self) -> None:
        """qa cycle 51 차단 사유 ① 회수 — v1 spoof bundle decrypt 차단 의무."""

        entries = _sample_entries()
        bundle_v2 = encrypt_backup(entries, "secret", created_at_ms=100)
        # v1 spoof = version 만 v1 으로 교체 + salt / blob 동일
        v1_spoof = BackupBundle(
            version="1",
            created_at_ms=bundle_v2.created_at_ms,
            salt=bundle_v2.salt,
            blob=bundle_v2.blob,
        )
        with pytest.raises(ValueError, match="unsupported backup version"):
            decrypt_backup(v1_spoof, "secret")

    def test_different_password_different_key(self) -> None:
        salt = secrets.token_bytes(16)
        k1 = derive_backup_key("password-a", salt)
        k2 = derive_backup_key("password-b", salt)
        assert k1 != k2

    def test_different_salt_different_key(self) -> None:
        k1 = derive_backup_key("password", secrets.token_bytes(16))
        k2 = derive_backup_key("password", secrets.token_bytes(16))
        assert k1 != k2

    def test_empty_password_rejected(self) -> None:
        with pytest.raises(ValueError, match="password 빈 문자열 불가"):
            derive_backup_key("", secrets.token_bytes(16))

    def test_invalid_salt_length(self) -> None:
        with pytest.raises(ValueError, match="salt 길이 불일치"):
            derive_backup_key("password", b"\x00" * 8)


class TestEncryptDecryptRoundTrip:
    """encrypt_backup + decrypt_backup round-trip 검증."""

    def test_basic_round_trip(self) -> None:
        entries = _sample_entries()
        bundle = encrypt_backup(entries, "secret", created_at_ms=12345)
        restored = decrypt_backup(bundle, "secret")
        assert len(restored) == 3
        assert restored[0].message_id == "msg-1"
        assert restored[0].plaintext == "안녕하세요".encode("utf-8")
        assert restored[1].plaintext == b"\x00\xff\x01\xfe"
        assert restored[2].plaintext == b""

    def test_empty_entries(self) -> None:
        bundle = encrypt_backup([], "secret", created_at_ms=0)
        restored = decrypt_backup(bundle, "secret")
        assert restored == []

    def test_wrong_password_invalid_tag(self) -> None:
        entries = _sample_entries()
        bundle = encrypt_backup(entries, "right", created_at_ms=100)
        with pytest.raises(InvalidTag):
            decrypt_backup(bundle, "wrong")

    def test_tampered_blob_invalid_tag(self) -> None:
        entries = _sample_entries()
        bundle = encrypt_backup(entries, "secret", created_at_ms=100)
        tampered = EncryptedPayload(
            nonce=bundle.blob.nonce,
            ciphertext=bundle.blob.ciphertext[:-1] + bytes(
                [(bundle.blob.ciphertext[-1] ^ 0x01)]
            ),
        )
        tampered_bundle = BackupBundle(
            version=bundle.version,
            created_at_ms=bundle.created_at_ms,
            salt=bundle.salt,
            blob=tampered,
        )
        with pytest.raises(InvalidTag):
            decrypt_backup(tampered_bundle, "secret")

    def test_custom_salt_carried(self) -> None:
        salt = secrets.token_bytes(16)
        entries = _sample_entries()
        bundle = encrypt_backup(
            entries, "secret", created_at_ms=100, salt=salt
        )
        assert bundle.salt == salt
        # 동일 password + 동일 salt = 복원 PASS
        restored = decrypt_backup(bundle, "secret")
        assert len(restored) == 3


class TestSerializeBundle:
    """``serialize_bundle`` / ``deserialize_bundle`` wire format 검증."""

    def test_round_trip(self) -> None:
        entries = _sample_entries()
        bundle = encrypt_backup(entries, "secret", created_at_ms=42)
        wire = serialize_bundle(bundle)
        assert isinstance(wire, bytes)
        restored = deserialize_bundle(wire)
        assert restored.version == bundle.version
        assert restored.created_at_ms == bundle.created_at_ms
        assert restored.salt == bundle.salt
        assert restored.blob.nonce == bundle.blob.nonce
        assert restored.blob.ciphertext == bundle.blob.ciphertext

    def test_round_trip_decrypts(self) -> None:
        """wire 의 round-trip 후 decrypt = 원본 동일 검증."""
        entries = _sample_entries()
        bundle = encrypt_backup(entries, "secret", created_at_ms=42)
        wire = serialize_bundle(bundle)
        restored_bundle = deserialize_bundle(wire)
        restored_entries = decrypt_backup(restored_bundle, "secret")
        assert len(restored_entries) == 3
        assert restored_entries[0].message_id == "msg-1"

    def test_missing_field_rejected(self) -> None:
        import json

        partial = json.dumps({"version": "1"}).encode("utf-8")
        with pytest.raises(ValueError, match="필드 누락"):
            deserialize_bundle(partial)

    def test_non_dict_root_rejected(self) -> None:
        import json

        bad = json.dumps([1, 2, 3]).encode("utf-8")
        with pytest.raises(ValueError, match="root dict 의무"):
            deserialize_bundle(bad)
