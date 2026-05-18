# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 2 encrypted backup / restore — 사이클 48.

대화 history 영속화 backup 정합. master password → HKDF derive backup key →
AES-256-GCM 의 단일 ciphertext blob 의무. 복원 = password + salt 의 동일 derive
후 decrypt.

설계 결정
---------
- master password = 사용자 직접 입력 (PBKDF2 의 stretching = 별개 cycle 의무).
  현 cycle = HKDF-SHA256 직접 derive (간단 의 KDF + Phase 2 minimal skeleton).
- entries = JSON 의 plaintext serialization → AES-GCM encrypt 의 단일 blob.
  per-entry encrypt 패턴 = 별개 cycle (수십만 entry 의 효율 의 별개 task).
- salt = 매 backup 의 randomly 생성 (HKDF rotation 정합).
- version field = backward compatibility 의 schema 변경 detect.
- wire format = bytes (`to_bytes` / `from_bytes`) — 디스크 영속화 / 외부 송신 의 동일 의무.

본 module 범위
-------------
- ``BackupEntry`` frozen dataclass — message_id + plaintext + timestamp_ms
- ``BackupBundle`` frozen dataclass — version + created_at_ms + salt + EncryptedPayload
- ``derive_backup_key`` — PBKDF2-HMAC-SHA256 600K iter password + salt → 32-byte AES-256 key
- ``encrypt_backup`` — entries list → JSON → AES-GCM → BackupBundle
- ``decrypt_backup`` — BackupBundle + password → entries list (InvalidTag = wrong pwd)
- ``serialize_bundle`` / ``deserialize_bundle`` — wire format bytes ↔ BackupBundle

본 cycle 의 범위 외 (별개 cycle):
- per-entry encrypt (대용량 backup 의 streaming 패턴)
- 차분 backup (incremental — directives + multi-cycle 의 streaming history)
- cloud upload (S3 / Google Drive — 외부 storage 의 별개 cycle)
- restore conflict resolution (기존 history + backup merge 정책)
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from typing import Final, List

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.crypto.e2ee import (
    EncryptedPayload,
    aes_gcm_decrypt,
    aes_gcm_encrypt,
)

# backup wire format 의 version — schema 변경 시 bump 의무.
# v1 = HKDF-SHA256 직접 derive (cycle 48 skeleton, brute-force 방어 부재).
# v2 = PBKDF2-HMAC-SHA256 600000 iteration stretching (cycle 50 P1 hotfix).
_BACKUP_VERSION: Final[str] = "2"
# PBKDF2 iteration 횟수 — OWASP 2023 권장값 SHA-256 의 600 000 의 정합.
# memory project_smtp_demo_server + bcrypt 12 rounds 의 등가 안전 margin.
_PBKDF2_ITERATIONS: Final[int] = 600_000
# salt 길이 = 16 byte (PBKDF2 권장 의 의무).
_SALT_BYTES: Final[int] = 16
# backup key 길이 = 32 byte (AES-256).
_KEY_BYTES: Final[int] = 32


@dataclass(frozen=True, slots=True)
class BackupEntry:
    """단일 message entry 의 plaintext + metadata.

    Attributes
    ----------
    message_id : str
        message 고유 식별자 (server-side msg id 또는 local UUID).
    plaintext : bytes
        decrypted 메시지 본문. JSON safe 의무 의 UTF-8 의무 (caller responsibility).
    timestamp_ms : int
        UNIX epoch millisecond. 정렬 + 시점 기록 의무.
    """

    message_id: str
    plaintext: bytes
    timestamp_ms: int

    def __post_init__(self) -> None:
        if not self.message_id:
            raise ValueError("message_id 빈 문자열 불가")
        if self.timestamp_ms < 0:
            raise ValueError(f"timestamp_ms 음수 불가 — {self.timestamp_ms}")


@dataclass(frozen=True, slots=True)
class BackupBundle:
    """encrypted backup 의 단일 결과.

    Attributes
    ----------
    version : str
        wire format version. schema 변경 시 bump.
    created_at_ms : int
        backup 생성 시점 (UNIX epoch ms).
    salt : bytes
        HKDF derive 의 salt (16 byte 의무).
    blob : EncryptedPayload
        entries JSON 의 AES-GCM ciphertext + nonce.
    """

    version: str
    created_at_ms: int
    salt: bytes
    blob: EncryptedPayload

    def __post_init__(self) -> None:
        if not self.version:
            raise ValueError("version 빈 문자열 불가")
        if self.created_at_ms < 0:
            raise ValueError(
                f"created_at_ms 음수 불가 — {self.created_at_ms}"
            )
        if len(self.salt) != _SALT_BYTES:
            raise ValueError(
                f"salt 길이 불일치 — len={len(self.salt)} (기대 {_SALT_BYTES})"
            )


def derive_backup_key(password: str, salt: bytes) -> bytes:
    """master password + salt → 32 byte AES-256 backup key (PBKDF2 stretching).

    Notes
    -----
    PBKDF2-HMAC-SHA256 with 600 000 iterations (OWASP 2023 권장). brute-force
    공격 방어 의 의무 (memory project_smtp_demo_server bcrypt 12 rounds 의
    등가 안전 margin). cycle 48 의 HKDF 직접 derive (v1) → cycle 50 의 PBKDF2
    stretching (v2) 의 backward incompatible bump.

    Raises
    ------
    ValueError
        password 빈 문자열 또는 salt 길이 불일치.
    """

    if not password:
        raise ValueError("password 빈 문자열 불가")
    if len(salt) != _SALT_BYTES:
        raise ValueError(
            f"salt 길이 불일치 — len={len(salt)} (기대 {_SALT_BYTES})"
        )
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_BYTES,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def _entries_to_json(entries: List[BackupEntry]) -> bytes:
    """entries → JSON bytes (한글 UTF-8 보존)."""

    payload = [
        {
            "message_id": e.message_id,
            "plaintext_b64": _bytes_to_b64(e.plaintext),
            "timestamp_ms": e.timestamp_ms,
        }
        for e in entries
    ]
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _json_to_entries(raw: bytes) -> List[BackupEntry]:
    """JSON bytes → entries list."""

    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("backup JSON root list 의무")
    out: List[BackupEntry] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("backup entry dict 의무")
        out.append(
            BackupEntry(
                message_id=item["message_id"],
                plaintext=_b64_to_bytes(item["plaintext_b64"]),
                timestamp_ms=int(item["timestamp_ms"]),
            )
        )
    return out


def _bytes_to_b64(data: bytes) -> str:
    """bytes → base64 str (JSON safe)."""

    from base64 import b64encode

    return b64encode(data).decode("ascii")


def _b64_to_bytes(s: str) -> bytes:
    """base64 str → bytes."""

    from base64 import b64decode

    return b64decode(s.encode("ascii"))


def encrypt_backup(
    entries: List[BackupEntry],
    password: str,
    *,
    created_at_ms: int,
    salt: bytes | None = None,
) -> BackupBundle:
    """entries list → BackupBundle (AES-GCM ciphertext).

    Parameters
    ----------
    entries : list[BackupEntry]
        backup 대상 message entries. 빈 list = 허용 (empty backup).
    password : str
        master password (HKDF input).
    created_at_ms : int
        backup 생성 시점 (UNIX epoch ms). caller responsibility.
    salt : bytes | None
        HKDF salt. None = secrets.token_bytes(16) 자동 생성.

    Returns
    -------
    BackupBundle
        version + created_at_ms + salt + AES-GCM 의 ciphertext blob.
    """

    used_salt = salt if salt is not None else secrets.token_bytes(_SALT_BYTES)
    key = derive_backup_key(password, used_salt)
    raw_json = _entries_to_json(entries)
    blob = aes_gcm_encrypt(key, raw_json)
    return BackupBundle(
        version=_BACKUP_VERSION,
        created_at_ms=created_at_ms,
        salt=used_salt,
        blob=blob,
    )


def decrypt_backup(bundle: BackupBundle, password: str) -> List[BackupEntry]:
    """BackupBundle + password → entries list.

    Notes
    -----
    잘못된 password 또는 tampered blob = AES-GCM InvalidTag exception raise.
    caller 의 wrap 의무.
    """

    key = derive_backup_key(password, bundle.salt)
    raw_json = aes_gcm_decrypt(key, bundle.blob)
    return _json_to_entries(raw_json)


def serialize_bundle(bundle: BackupBundle) -> bytes:
    """BackupBundle → wire format bytes (디스크 영속화 의 동일 의무).

    JSON envelope: version + created_at_ms + salt_b64 + blob_b64.
    """

    payload = {
        "version": bundle.version,
        "created_at_ms": bundle.created_at_ms,
        "salt_b64": _bytes_to_b64(bundle.salt),
        "blob_b64": _bytes_to_b64(bundle.blob.to_bytes()),
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def deserialize_bundle(raw: bytes) -> BackupBundle:
    """wire format bytes → BackupBundle."""

    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("backup wire format root dict 의무")
    required = ("version", "created_at_ms", "salt_b64", "blob_b64")
    missing = [k for k in required if k not in payload]
    if missing:
        raise ValueError(f"backup wire format 의 필드 누락 — {missing}")
    return BackupBundle(
        version=str(payload["version"]),
        created_at_ms=int(payload["created_at_ms"]),
        salt=_b64_to_bytes(payload["salt_b64"]),
        blob=EncryptedPayload.from_bytes(_b64_to_bytes(payload["blob_b64"])),
    )
