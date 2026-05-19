# SPDX-License-Identifier: GPL-3.0-or-later
"""emoji pack DMCA hash check skeleton — phash + known infringement DB (cycle 133).

memory `project_emoji_pack_share.md` 정합. emoji sticker / custom emoji 의
공유 등록 시점 의 DMCA 침해 hash check chain layer. cycle 133 = skeleton +
graceful binding (Pillow + imagehash 부재 시 sha256 fallback).

본 module 범위 (cycle 133)
--------------------------
- ``DmcaCheckResult`` frozen dataclass — is_infringement + matched_hash +
  confidence (0.0 ~ 1.0).
- ``compute_sha256_hash`` — SHA-256 64자 hex (exact match base).
- ``compute_phash_skeleton`` — perceptual hash placeholder (graceful fallback).
- ``check_known_infringement`` — known set 의 exact match (cycle 141+ 의
  hamming distance threshold + DB persistence).

본 cycle 의 범위 외 (별개 cycle 141~150):
- imagehash library 의 dhash / whash / colorhash 의 multi-hash 조합
- hamming distance threshold (예: 5 이하 = match)
- known infringement DB persistence (SQLite / MariaDB) + LRU cache
- DMCA takedown 신고 워크플로우 + 작성자 notification + appeal
- 사용자 신고 기반 누적 hash 의 자동 등록 + 가중치 score
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional, Set

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DmcaCheckResult:
    """DMCA hash check 결과 — caller 의 차단 의사결정 의 base.

    Attributes
    ----------
    is_infringement : bool
        침해 hash 의 match 여부.
    matched_hash : Optional[str]
        match 한 hash 의 hex string (None = 부재).
    confidence : float
        0.0 ~ 1.0 의 정확도. cycle 133 = exact match 만 → 1.0 또는 0.0.
        cycle 141+ 의 hamming distance threshold 의 점수화.
    """

    is_infringement: bool
    matched_hash: Optional[str] = None
    confidence: float = 0.0


def compute_sha256_hash(image_bytes: bytes) -> str:
    """SHA-256 64자 hex (exact match base).

    Parameters
    ----------
    image_bytes : bytes
        image binary.

    Returns
    -------
    str
        64자 hex (lowercase) SHA-256 digest.
    """

    # 한글 주석: SHA-256 = exact match 의 base — 단 1 bit 의 변경 도 다른 hash
    return hashlib.sha256(image_bytes).hexdigest()


def compute_phash_skeleton(image_bytes: bytes) -> str:
    """perceptual hash placeholder (Phase 5 본격 imagehash library binding).

    graceful — PIL + imagehash 부재 시 sha256[:16] fallback.

    Parameters
    ----------
    image_bytes : bytes
        image binary.

    Returns
    -------
    str
        phash hex string (보통 16자) 또는 sha256[:16] fallback.
    """

    # 한글 주석: PIL + imagehash graceful import — 부재 시 sha256[:16] fallback
    try:
        from PIL import Image  # type: ignore[import-not-found]
        import imagehash  # type: ignore[import-not-found]
        import io
    except ImportError:
        log.warning("[dmca] PIL + imagehash 부재 — sha256 fallback")
        return compute_sha256_hash(image_bytes)[:16]

    # 한글 주석: image 로드 + phash 계산 — 예외 시 sha256 fallback
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return str(imagehash.phash(img))
    except Exception as exc:  # noqa: BLE001
        log.warning("[dmca] phash 실패 — %r", exc)
        return compute_sha256_hash(image_bytes)[:16]


def check_known_infringement(image_hash: str, known_db: Set[str]) -> DmcaCheckResult:
    """등록된 침해 hash set 검사 (cycle 133 = exact match 만).

    Phase 5 본격 cycle 141+ 의 hamming distance threshold 추가 예정.

    Parameters
    ----------
    image_hash : str
        검사 대상 hash hex string.
    known_db : Set[str]
        등록된 침해 hash set (예: DMCA takedown 누계 DB 의 in-memory snapshot).

    Returns
    -------
    DmcaCheckResult
        is_infringement + matched_hash + confidence.
    """

    # 한글 주석: exact match — cycle 133 의 의무, hamming distance 는 별개 cycle
    if image_hash in known_db:
        return DmcaCheckResult(
            is_infringement=True,
            matched_hash=image_hash,
            confidence=1.0,
        )
    return DmcaCheckResult(is_infringement=False)
