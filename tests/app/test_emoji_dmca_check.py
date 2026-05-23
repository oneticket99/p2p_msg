# SPDX-License-Identifier: GPL-3.0-or-later
"""bot emoji_dmca_check unit — cycle 169.722 신설.

hamming_distance + check_known_infringement (exact + fuzzy) + sha256 helper.
"""

from __future__ import annotations

import pytest


class TestComputeSha256:
    def test_returns_64_hex(self) -> None:
        from app.bot.emoji_dmca_check import compute_sha256_hash

        h = compute_sha256_hash(b"hello world")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self) -> None:
        from app.bot.emoji_dmca_check import compute_sha256_hash

        h1 = compute_sha256_hash(b"same")
        h2 = compute_sha256_hash(b"same")
        assert h1 == h2

    def test_different_input_different_hash(self) -> None:
        from app.bot.emoji_dmca_check import compute_sha256_hash

        assert compute_sha256_hash(b"a") != compute_sha256_hash(b"b")


class TestHammingDistance:
    def test_identical_zero(self) -> None:
        from app.bot.emoji_dmca_check import hamming_distance

        assert hamming_distance("abcd", "abcd") == 0

    def test_all_different(self) -> None:
        # 한글 주석 — 0x0 = 0000 vs 0xF = 1111 → 4 bit diff
        from app.bot.emoji_dmca_check import hamming_distance

        assert hamming_distance("0", "f") == 4

    def test_length_mismatch_raises(self) -> None:
        from app.bot.emoji_dmca_check import hamming_distance

        with pytest.raises(ValueError, match="length"):
            hamming_distance("abc", "abcd")

    def test_invalid_hex_raises(self) -> None:
        from app.bot.emoji_dmca_check import hamming_distance

        with pytest.raises(ValueError, match="hex"):
            hamming_distance("zzzz", "0000")


class TestCheckKnownInfringement:
    def test_exact_match(self) -> None:
        from app.bot.emoji_dmca_check import check_known_infringement

        result = check_known_infringement("abc123", {"abc123", "def456"})
        assert result.is_infringement is True
        assert result.matched_hash == "abc123"
        assert result.confidence == 1.0

    def test_no_match(self) -> None:
        from app.bot.emoji_dmca_check import check_known_infringement

        result = check_known_infringement("ghost", {"abc123", "def456"})
        assert result.is_infringement is False
        assert result.matched_hash is None
        assert result.confidence == 0.0

    def test_empty_db_no_match(self) -> None:
        from app.bot.emoji_dmca_check import check_known_infringement

        result = check_known_infringement("abc123", set())
        assert result.is_infringement is False


class TestCheckKnownInfringementFuzzy:
    def test_fuzzy_within_threshold(self) -> None:
        # 한글 주석 — 1 bit diff = match (threshold 5 안)
        from app.bot.emoji_dmca_check import check_known_infringement_fuzzy

        result = check_known_infringement_fuzzy(
            "0", {"1"}, threshold=5,
        )
        assert result.is_infringement is True
        assert 0.0 < result.confidence <= 1.0

    def test_fuzzy_beyond_threshold(self) -> None:
        # 한글 주석 — 4 bit diff > threshold 2 → match 차단
        from app.bot.emoji_dmca_check import check_known_infringement_fuzzy

        result = check_known_infringement_fuzzy(
            "0", {"f"}, threshold=2,
        )
        assert result.is_infringement is False

    def test_empty_db(self) -> None:
        from app.bot.emoji_dmca_check import check_known_infringement_fuzzy

        result = check_known_infringement_fuzzy("0000", set())
        assert result.is_infringement is False


class TestDmcaCheckResult:
    def test_default_construct(self) -> None:
        from app.bot.emoji_dmca_check import DmcaCheckResult

        r = DmcaCheckResult(is_infringement=False)
        assert r.matched_hash is None
        assert r.confidence == 0.0
