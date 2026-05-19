# SPDX-License-Identifier: GPL-3.0-or-later
"""emoji pack DMCA hash check — phash + dhash actual binding (cycle 150).

memory `project_emoji_pack_share.md` 정합. emoji sticker / custom emoji 의
공유 등록 시점 의 DMCA 침해 hash check chain layer.

cycle 133 = skeleton + graceful binding (Pillow + imagehash 부재 시 sha256
fallback).
cycle 150 = Pillow + imagehash 의 실 binding 진입 — phash + dhash + combined
hash + hamming distance + fuzzy match (threshold ≤ 5).

본 module 범위 (cycle 150)
--------------------------
- ``DmcaCheckResult`` frozen dataclass — is_infringement + matched_hash +
  confidence (0.0 ~ 1.0).
- ``compute_sha256_hash`` — SHA-256 64자 hex (exact match base).
- ``compute_phash`` — perceptual hash 실 binding (16자 hex) + graceful
  fallback. ``compute_phash_skeleton`` 은 backward-compat alias.
- ``compute_dhash`` — difference hash 실 binding (16자 hex) + graceful
  fallback.
- ``compute_combined_hash`` — phash + dhash 의 32자 hex 조합.
- ``hamming_distance`` — bit-level XOR popcount.
- ``check_known_infringement`` — exact match (cycle 133).
- ``check_known_infringement_fuzzy`` — hamming ≤ threshold 의 fuzzy match.

본 cycle 의 범위 외 (별개 cycle 151+):
- whash / colorhash 의 multi-hash 조합 + 가중치 score
- known infringement DB persistence (SQLite / MariaDB) + LRU cache
- DMCA takedown 신고 워크플로우 + 작성자 notification + appeal
- 사용자 신고 기반 누적 hash 의 자동 등록 + 가중치 score
"""

from __future__ import annotations

import hashlib
import io
import logging
from dataclasses import dataclass
from typing import Optional, Set

log = logging.getLogger(__name__)

# 한글 주석: hamming distance threshold 의 default — cycle 150 = 5 이하 hit
DEFAULT_FUZZY_THRESHOLD = 5


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
        0.0 ~ 1.0 의 정확도. exact match → 1.0, fuzzy match → hamming
        distance 의 normalize 한 점수 (1.0 = 0 distance, 0.0 = threshold 초과).
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


def compute_phash(image_bytes: bytes) -> str:
    """perceptual hash 실 binding (Pillow + imagehash).

    graceful — PIL + imagehash 부재 시 sha256[:16] fallback.
    실 binding 시점 의 imagehash.phash → 64-bit hash → 16자 hex string.

    Parameters
    ----------
    image_bytes : bytes
        image binary.

    Returns
    -------
    str
        phash 16자 hex string 또는 sha256[:16] fallback.
    """

    # 한글 주석: PIL + imagehash graceful import — 부재 시 sha256[:16] fallback
    try:
        from PIL import Image  # type: ignore[import-not-found]
        import imagehash  # type: ignore[import-not-found]
    except ImportError:
        log.warning("[dmca] PIL + imagehash 부재 — sha256 fallback")
        return compute_sha256_hash(image_bytes)[:16]

    # 한글 주석: image 로드 + phash 계산 — 예외 시 sha256 fallback (corrupt image)
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return str(imagehash.phash(img))
    except Exception as exc:  # noqa: BLE001
        log.warning("[dmca] phash 실패 — %r", exc)
        return compute_sha256_hash(image_bytes)[:16]


# 한글 주석: backward-compat alias — cycle 133 의 compute_phash_skeleton 호출 정합
compute_phash_skeleton = compute_phash


def compute_dhash(image_bytes: bytes) -> str:
    """difference hash 실 binding (Pillow + imagehash).

    graceful — PIL + imagehash 부재 시 sha256[16:32] fallback (phash 와 다른
    영역 sub-string 으로 결정성 유지).
    실 binding 시점 의 imagehash.dhash → 64-bit hash → 16자 hex string.

    Parameters
    ----------
    image_bytes : bytes
        image binary.

    Returns
    -------
    str
        dhash 16자 hex string 또는 sha256[16:32] fallback.
    """

    # 한글 주석: PIL + imagehash graceful import — 부재 시 sha256[16:32] fallback
    try:
        from PIL import Image  # type: ignore[import-not-found]
        import imagehash  # type: ignore[import-not-found]
    except ImportError:
        log.warning("[dmca] PIL + imagehash 부재 — dhash sha256 fallback")
        return compute_sha256_hash(image_bytes)[16:32]

    # 한글 주석: image 로드 + dhash 계산 — 예외 시 sha256 fallback (corrupt image)
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return str(imagehash.dhash(img))
    except Exception as exc:  # noqa: BLE001
        log.warning("[dmca] dhash 실패 — %r", exc)
        return compute_sha256_hash(image_bytes)[16:32]


def compute_combined_hash(image_bytes: bytes) -> str:
    """phash + dhash 조합 32자 hex (16 + 16).

    cycle 150 의 multi-hash 조합 — phash 와 dhash 의 독립 특징 결합 의
    false-positive 감소 + DMCA 신뢰도 상승.

    Parameters
    ----------
    image_bytes : bytes
        image binary.

    Returns
    -------
    str
        32자 hex (phash 16자 + dhash 16자).
    """

    # 한글 주석: phash + dhash 의 단순 concat — 검색 시 16자 단위 split 의무
    return compute_phash(image_bytes) + compute_dhash(image_bytes)


def hamming_distance(hash1: str, hash2: str) -> int:
    """bit-level XOR popcount (hex string 동등 길이 의무).

    cycle 150 의 fuzzy match base — 두 hash 의 bit 단위 차이 count.

    Parameters
    ----------
    hash1 : str
        hex string 1.
    hash2 : str
        hex string 2 (동등 길이 의무).

    Returns
    -------
    int
        bit 단위 XOR popcount (0 = 동일, 4*len(hex) = 최대).

    Raises
    ------
    ValueError
        두 hash 의 길이 가 다른 경우 또는 hex 부적합.
    """

    # 한글 주석: 길이 동등성 의무 — phash 16자 vs dhash 16자 비교 차단
    if len(hash1) != len(hash2):
        raise ValueError(
            f"hash length mismatch: {len(hash1)} vs {len(hash2)}"
        )
    # 한글 주석: hex → int 변환 + XOR + bit_count (Python 3.10+ 의무)
    try:
        int1 = int(hash1, 16)
        int2 = int(hash2, 16)
    except ValueError as exc:
        raise ValueError(f"invalid hex string: {exc}") from exc
    return (int1 ^ int2).bit_count()


def check_known_infringement(image_hash: str, known_db: Set[str]) -> DmcaCheckResult:
    """등록된 침해 hash set 의 exact match (cycle 133 정합).

    cycle 150 의 fuzzy match 는 ``check_known_infringement_fuzzy`` 별개 활용.

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

    # 한글 주석: exact match — bit 단위 동일성 의 의무
    if image_hash in known_db:
        return DmcaCheckResult(
            is_infringement=True,
            matched_hash=image_hash,
            confidence=1.0,
        )
    return DmcaCheckResult(is_infringement=False)


def check_known_infringement_fuzzy(
    image_hash: str,
    known_db: Set[str],
    threshold: int = DEFAULT_FUZZY_THRESHOLD,
) -> DmcaCheckResult:
    """hamming distance threshold 의 fuzzy match (cycle 150 신설).

    image_hash 와 known_db 의 모든 hash 사이 hamming distance 계산 →
    threshold 이하 의 최소 distance match 반환. exact match (distance=0)
    포함. confidence = 1.0 - (distance / threshold).

    Parameters
    ----------
    image_hash : str
        검사 대상 hash hex string.
    known_db : Set[str]
        등록된 침해 hash set (동등 길이 의무).
    threshold : int, default 5
        hamming distance threshold (이하 = match).

    Returns
    -------
    DmcaCheckResult
        is_infringement + matched_hash + confidence (0.0 ~ 1.0).
    """

    # 한글 주석: 빈 DB → miss 즉시 반환
    if not known_db:
        return DmcaCheckResult(is_infringement=False)

    # 한글 주석: 최소 distance 의 hash 추적 — match 미발견 시 None
    best_distance: Optional[int] = None
    best_hash: Optional[str] = None
    for candidate in known_db:
        # 한글 주석: 길이 불일치 candidate 는 graceful skip (혼합 DB 의 회피)
        if len(candidate) != len(image_hash):
            continue
        try:
            distance = hamming_distance(image_hash, candidate)
        except ValueError:
            # 한글 주석: hex 부적합 candidate 는 skip
            continue
        if distance > threshold:
            continue
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_hash = candidate
            # 한글 주석: exact match (distance=0) → 추가 탐색 불필요
            if distance == 0:
                break

    if best_hash is None or best_distance is None:
        return DmcaCheckResult(is_infringement=False)

    # 한글 주석: confidence = 1.0 - (distance / threshold) — distance 0 = 1.0
    if threshold == 0:
        confidence = 1.0 if best_distance == 0 else 0.0
    else:
        confidence = max(0.0, 1.0 - (best_distance / threshold))
    return DmcaCheckResult(
        is_infringement=True,
        matched_hash=best_hash,
        confidence=confidence,
    )
