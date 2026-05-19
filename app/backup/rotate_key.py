# SPDX-License-Identifier: GPL-3.0-or-later
"""encrypted backup master key rotation — PBKDF2 + AES-GCM (사이클 132 skeleton).

Phase 2 사이클 24~32 chain 의 encrypted_backup (PBKDF2 600K iteration + AES-GCM +
X25519) 의 master key rotation 자동화 prerequisite. master key 6개월 권장 rotation
+ 기존 backup 재암호화 + 사용자 manual 트리거 진입점.

본 module 범위 (사이클 132 skeleton)
-----------------------------------
- ``needs_rotation`` — 마지막 rotation timestamp 기준 만료 검증
- ``generate_new_master_key`` — secrets.token_bytes 의 AES-256 32 byte 생성
- ``rotation_log_entry`` — audit log dict 빌더 (DB user_activity_log 정합)
- ``export_rotation_command`` — 사용자 manual rotation 명령 안내 string

본 cycle 범위 외 (별개 cycle 의무):
- 실 key file 생성 + 디스크 write (사용자 manual 의무)
- 실 backup 재암호화 chain (encrypt_backup 의 batch re-run)
- DB user_activity_log INSERT (별개 schema migration cycle)
- /etc/tootalk/keys/ 의 active.key + archive/ 디렉토리 운영
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)

# 한글 주석 — KST = UTC+9 timezone 고정 (모든 timestamp KST 의무, MEMORY #25 정합)
_KST = timezone(timedelta(hours=9))

# 한글 주석 — master key rotation 정책 6개월 = 180 일 default
DEFAULT_ROTATION_DAYS: int = 180

# 한글 주석 — AES-256 의 최소 32 byte 의무, 16 byte 미만 차단
MIN_KEY_BYTES: int = 16


def needs_rotation(last_rotated_iso: str, rotation_days: int = DEFAULT_ROTATION_DAYS) -> bool:
    """마지막 rotation 시점에서 rotation_days 경과 검증.

    Parameters
    ----------
    last_rotated_iso : str
        ISO 8601 형식 timestamp (예: ``2025-11-19T04:00:00+09:00``).
        timezone 부재 시 KST 가정.
    rotation_days : int
        rotation 주기 일수 (default 180 = 6개월).

    Returns
    -------
    bool
        True = rotation 의무 (경과 또는 invalid timestamp).
        False = rotation 불필요 (주기 내).
    """
    # 한글 주석 — invalid ISO timestamp 시 안전쪽 (rotation 의무) 처리
    try:
        last = datetime.fromisoformat(last_rotated_iso)
    except (ValueError, TypeError):
        log.warning("invalid last_rotated_iso=%r → rotation 의무 처리", last_rotated_iso)
        return True
    # 한글 주석 — naive datetime 시 KST 가정 (정본 timezone 정책 정합)
    if last.tzinfo is None:
        last = last.replace(tzinfo=_KST)
    delta = datetime.now(_KST) - last
    return delta.days >= rotation_days


def generate_new_master_key(byte_length: int = 32) -> bytes:
    """AES-256 의무 32 byte secrets cryptographically secure 생성.

    Parameters
    ----------
    byte_length : int
        생성할 key byte 길이. AES-128 의무 = 16 byte 이상, default 32 (AES-256).

    Returns
    -------
    bytes
        ``secrets.token_bytes(byte_length)`` 결과.

    Raises
    ------
    ValueError
        ``byte_length < MIN_KEY_BYTES`` 시.
    """
    # 한글 주석 — AES-128 미만 byte 차단 (NIST SP 800-38D minimum)
    if byte_length < MIN_KEY_BYTES:
        raise ValueError(
            f"byte_length >= {MIN_KEY_BYTES} 의무 (AES-128 이상), 현재={byte_length}"
        )
    return secrets.token_bytes(byte_length)


def rotation_log_entry(
    *,
    old_key_id: str,
    new_key_id: str,
    reason: str = "scheduled",
) -> dict:
    """rotation audit log entry 생성 (DB user_activity_log 정합).

    Parameters
    ----------
    old_key_id : str
        rotation 이전 key 식별자 (예: SHA256 prefix 8 char).
    new_key_id : str
        rotation 이후 key 식별자.
    reason : str
        rotation 사유 (``scheduled`` / ``manual`` / ``compromised`` / ``audit``).

    Returns
    -------
    dict
        ``ts_kst`` + ``old_key_id`` + ``new_key_id`` + ``reason`` + ``policy`` 5 키.
    """
    # 한글 주석 — KST ISO + 정책 metadata 포함 (audit log INSERT row 의무)
    return {
        "ts_kst": datetime.now(_KST).isoformat(),
        "old_key_id": old_key_id,
        "new_key_id": new_key_id,
        "reason": reason,
        "policy": f"rotation_days={DEFAULT_ROTATION_DAYS}",
    }


def export_rotation_command(backup_dir: Path, new_key_path: Path) -> str:
    """사용자 manual rotation 명령 안내 string 생성.

    Phase 2 본격 cycle 시 actual binding (encrypt_backup batch + DB INSERT) 진입점.
    현 사이클 132 = skeleton 안내 4 단계 chain 명문화.

    Parameters
    ----------
    backup_dir : Path
        기존 backup blob 디렉토리 (재암호화 대상).
    new_key_path : Path
        새 master key 영속화 경로.

    Returns
    -------
    str
        4 단계 사용자 manual 명령 안내 multi-line text.
    """
    # 한글 주석 — 4 단계 chain: key 백업 + 재암호화 + active 갱신 + DB log INSERT
    return (
        "# 사용자 manual rotation chain (사이클 132 skeleton):\n"
        f"# 1. {new_key_path} 백업 (생성 직후 안전 매체 보관)\n"
        f"# 2. {backup_dir} chain 의 모든 backup blob → 새 key 재암호화 batch\n"
        "# 3. /etc/tootalk/keys/active.key 갱신 + 이전 key /etc/tootalk/keys/archive/ 이동\n"
        "# 4. DB user_activity_log 의 rotation 기록 INSERT (audit 의무)\n"
    )
