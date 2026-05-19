# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.emoji_dmca_check`` cycle 150 actual binding 단위 테스트.

cycle 150 — Phase 5 emoji moderation chain 의 DMCA hash check 실 binding.
Pillow + imagehash 의 graceful import + phash/dhash + hamming distance +
fuzzy match (threshold ≤ 5) + combined hash 검증 8 test.

본 test 의무 (8 test class)
----------------------------
- TestPhashImporting — imagehash binding 시도 + graceful fallback (mock)
- TestPhashDhash — actual binding 시 16자 hex string 정합 (mock 의 phash 강제)
- TestHammingDistance — bit-level XOR popcount (0 / 64 / 32 case)
- TestFuzzyMatchInside — threshold 안 hit detection
- TestFuzzyMatchOutside — threshold 외 miss
- TestCombinedHash — 32자 hex (16 phash + 16 dhash)
- TestEmptyDB — known_db = set() 의 모든 miss
- TestGracefulFallback — ImportError → sha256[:16] fallback

본 cycle 의 범위 외:
- 실 imagehash binary 호출 / 실 Pillow Image.open server file 호출 (mock 의무)
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.bot.emoji_dmca_check import (
    DEFAULT_FUZZY_THRESHOLD,
    DmcaCheckResult,
    check_known_infringement_fuzzy,
    compute_combined_hash,
    compute_dhash,
    compute_phash,
    compute_phash_skeleton,
    compute_sha256_hash,
    hamming_distance,
)


def _block_pillow_imagehash(monkeypatch: pytest.MonkeyPatch) -> None:
    """PIL + imagehash import 차단 — graceful fallback 강제 경로 검증 helper."""

    # 한글 주석: 기본 __import__ reference 보관 (실제 import → graceful pass-through)
    real_import = (
        __builtins__["__import__"]
        if isinstance(__builtins__, dict)
        else __builtins__.__import__
    )

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        # 한글 주석: PIL / imagehash 만 ImportError 강제 — 외 module 그대로 통과
        if name in ("PIL", "imagehash") or name.startswith("PIL."):
            raise ImportError(f"mock 강제 부재 — {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)


def _install_fake_pil_imagehash(
    monkeypatch: pytest.MonkeyPatch,
    phash_hex: str = "0123456789abcdef",
    dhash_hex: str = "fedcba9876543210",
) -> None:
    """PIL + imagehash 의 가짜 module 주입 — actual binding 경로 mock."""

    # 한글 주석: PIL.Image 가짜 module — open() = 더미 image 객체 반환
    fake_pil = ModuleType("PIL")
    fake_image_mod = ModuleType("PIL.Image")

    def fake_open(_fp: object) -> SimpleNamespace:
        return SimpleNamespace(size=(8, 8), mode="L")

    fake_image_mod.open = fake_open  # type: ignore[attr-defined]
    fake_pil.Image = fake_image_mod  # type: ignore[attr-defined]

    # 한글 주석: imagehash 가짜 module — phash + dhash = 결정성 hex 반환
    fake_imagehash = ModuleType("imagehash")

    class FakeHash:
        def __init__(self, hex_value: str) -> None:
            self._hex = hex_value

        def __str__(self) -> str:
            return self._hex

    def fake_phash(_img: object) -> FakeHash:
        return FakeHash(phash_hex)

    def fake_dhash(_img: object) -> FakeHash:
        return FakeHash(dhash_hex)

    fake_imagehash.phash = fake_phash  # type: ignore[attr-defined]
    fake_imagehash.dhash = fake_dhash  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "PIL", fake_pil)
    monkeypatch.setitem(sys.modules, "PIL.Image", fake_image_mod)
    monkeypatch.setitem(sys.modules, "imagehash", fake_imagehash)


class TestPhashImporting:
    """imagehash binding 시도 + graceful fallback (mock 강제 부재)."""

    def test_alias_backward_compat(self) -> None:
        """compute_phash_skeleton = compute_phash alias 의 backward-compat 의무."""

        # 한글 주석: cycle 133 의 dispatcher 호출 정합 — alias 동일 함수 reference
        assert compute_phash_skeleton is compute_phash

    def test_phash_imports_falls_back_when_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PIL / imagehash 부재 시 sha256[:16] fallback — log warning 의무."""

        _block_pillow_imagehash(monkeypatch)
        payload = b"png-like emoji bytes for import test"
        result = compute_phash(payload)
        # 한글 주석: fallback 의 16자 prefix 의무
        assert result == compute_sha256_hash(payload)[:16]
        assert len(result) == 16


class TestPhashDhash:
    """actual binding 시 16자 hex string 정합 (mock 의 phash 강제)."""

    def test_phash_actual_returns_16_hex(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """mock imagehash 의 phash → 16자 hex string 반환 의무."""

        _install_fake_pil_imagehash(
            monkeypatch, phash_hex="0123456789abcdef"
        )
        payload = b"fake png bytes for phash"
        result = compute_phash(payload)
        # 한글 주석: 16자 hex string — imagehash.phash 의 64-bit 정합
        assert result == "0123456789abcdef"
        assert len(result) == 16

    def test_dhash_actual_returns_16_hex(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """mock imagehash 의 dhash → 16자 hex string 반환 의무."""

        _install_fake_pil_imagehash(
            monkeypatch, dhash_hex="fedcba9876543210"
        )
        payload = b"fake png bytes for dhash"
        result = compute_dhash(payload)
        assert result == "fedcba9876543210"
        assert len(result) == 16


class TestHammingDistance:
    """bit-level XOR popcount (0 / 64 / 32 case)."""

    def test_zero_distance_identical(self) -> None:
        """동일 hash → distance = 0."""

        assert hamming_distance("abcdef0123456789", "abcdef0123456789") == 0

    def test_max_distance_inverted(self) -> None:
        """완전 반전 hash → distance = 64 (16자 hex × 4 bit)."""

        # 한글 주석: 0xFF...F XOR 0x00...0 = 64 bit 차이 (16자 hex × 4 bit)
        assert hamming_distance("ffffffffffffffff", "0000000000000000") == 64

    def test_partial_distance_half(self) -> None:
        """half 반전 hash → distance = 32 (alternate nibble)."""

        # 한글 주석: 0xAAAA... XOR 0x5555... = 모든 bit 반전 → 64
        # 한글 주석: 0xFFFF...00000000 (8자 F + 8자 0) XOR 0 → 32 bit 차이
        h1 = "ffffffff00000000"
        h2 = "0000000000000000"
        assert hamming_distance(h1, h2) == 32

    def test_length_mismatch_raises(self) -> None:
        """길이 불일치 → ValueError 의무."""

        with pytest.raises(ValueError, match="length mismatch"):
            hamming_distance("abcd", "abcdef")

    def test_invalid_hex_raises(self) -> None:
        """hex 부적합 → ValueError 의무."""

        with pytest.raises(ValueError):
            hamming_distance("zzzz", "abcd")


class TestFuzzyMatchInside:
    """threshold 안 hit detection — hamming ≤ 5 의 match 의무."""

    def test_exact_match_full_confidence(self) -> None:
        """distance = 0 → confidence 1.0."""

        known = {"abcdef0123456789", "fedcba9876543210"}
        result = check_known_infringement_fuzzy(
            "abcdef0123456789", known, threshold=5
        )
        assert isinstance(result, DmcaCheckResult)
        assert result.is_infringement is True
        assert result.matched_hash == "abcdef0123456789"
        assert result.confidence == 1.0

    def test_within_threshold_partial_confidence(self) -> None:
        """distance 1 (1 bit 차이) → confidence ≈ 0.8 (threshold=5)."""

        # 한글 주석: abcdef0123456788 = ...789 의 마지막 nibble 1 bit 차이
        known = {"abcdef0123456789"}
        result = check_known_infringement_fuzzy(
            "abcdef0123456788", known, threshold=5
        )
        assert result.is_infringement is True
        assert result.matched_hash == "abcdef0123456789"
        # 한글 주석: confidence = 1.0 - (1/5) = 0.8
        assert result.confidence == pytest.approx(0.8)


class TestFuzzyMatchOutside:
    """threshold 외 miss — hamming > 5 의 비 match 의무."""

    def test_outside_threshold_returns_miss(self) -> None:
        """distance 6 이상 → is_infringement=False."""

        # 한글 주석: 0xFFFF... vs 0x0000... = 64 distance — threshold=5 초과
        known = {"ffffffffffffffff"}
        result = check_known_infringement_fuzzy(
            "0000000000000000", known, threshold=5
        )
        assert result.is_infringement is False
        assert result.matched_hash is None
        assert result.confidence == 0.0

    def test_default_threshold_constant(self) -> None:
        """DEFAULT_FUZZY_THRESHOLD = 5 의 정합."""

        # 한글 주석: cycle 150 default threshold 의 calibration 의무
        assert DEFAULT_FUZZY_THRESHOLD == 5


class TestCombinedHash:
    """32자 hex (16 phash + 16 dhash) 정합."""

    def test_combined_hash_length_32(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """phash 16자 + dhash 16자 = 32자 의무 (mock 의 actual binding)."""

        _install_fake_pil_imagehash(
            monkeypatch,
            phash_hex="0123456789abcdef",
            dhash_hex="fedcba9876543210",
        )
        payload = b"fake png bytes for combined"
        result = compute_combined_hash(payload)
        # 한글 주석: 32자 hex string — phash 16자 prefix + dhash 16자 suffix
        assert len(result) == 32
        assert result == "0123456789abcdef" + "fedcba9876543210"

    def test_combined_hash_fallback_length_32(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PIL / imagehash 부재 시 fallback 도 32자 의무 (sha256 의 2 영역)."""

        _block_pillow_imagehash(monkeypatch)
        payload = b"fallback combined bytes"
        result = compute_combined_hash(payload)
        # 한글 주석: phash sha256[:16] + dhash sha256[16:32] = 32자
        assert len(result) == 32
        sha = compute_sha256_hash(payload)
        assert result == sha[:16] + sha[16:32]


class TestEmptyDB:
    """known_db = set() 의 모든 miss 의무 (fuzzy + exact)."""

    def test_empty_db_returns_miss(self) -> None:
        """빈 DB → is_infringement=False 즉시 반환."""

        result = check_known_infringement_fuzzy(
            "abcdef0123456789", set(), threshold=5
        )
        assert result.is_infringement is False
        assert result.matched_hash is None
        assert result.confidence == 0.0


class TestGracefulFallback:
    """ImportError → sha256[:16] fallback (phash + dhash 별개 영역)."""

    def test_phash_dhash_fallback_distinct_regions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """phash sha256[:16] + dhash sha256[16:32] 의 별개 영역 의무."""

        _block_pillow_imagehash(monkeypatch)
        payload = b"fallback distinct bytes"
        sha = compute_sha256_hash(payload)
        # 한글 주석: phash = sha256 의 prefix 16자 / dhash = 의 16:32 영역
        assert compute_phash(payload) == sha[:16]
        assert compute_dhash(payload) == sha[16:32]
        # 한글 주석: 두 영역 의 결정성 — 서로 다른 sub-string 의무 (collision 차단)
        assert compute_phash(payload) != compute_dhash(payload)
