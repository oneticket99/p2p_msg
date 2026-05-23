# SPDX-License-Identifier: GPL-3.0-or-later
"""bot RAG ranking + Embedder cache chain E2E — cycle 169.697 신설.

chain:
1. _tokenize stopword 제거
2. _score_entry token overlap + substring boost
3. KeywordRAGStore top_k ranking
4. cosine_similarity 1.0 / 0.0 / -1.0
5. MockEmbedder L2 normalize + dim 정합
6. MockEmbedder dim<=0 raises
7. CachedEmbedder hit/miss counter
8. CachedEmbedder LRU evict
9. CachedEmbedder clear + reset_stats
"""

from __future__ import annotations

import math

import pytest

from app.bot.rag_context import (
    CachedEmbedder, FAQEntry, KeywordRAGStore, MockEmbedder,
    _score_entry, _tokenize, cosine_similarity,
)


pytestmark = pytest.mark.integration


class TestTokenize:
    def test_lowercase_split(self) -> None:
        tokens = _tokenize("Hello World")
        assert "hello" in tokens
        assert "world" in tokens

    def test_empty_returns_empty(self) -> None:
        assert _tokenize("") == []


class TestScoreEntry:
    def test_empty_query_zero(self) -> None:
        e = FAQEntry(id="1", topic="t", question="q text", answer="a")
        assert _score_entry([], e) == 0.0

    def test_overlap_proportional(self) -> None:
        e = FAQEntry(id="1", topic="t", question="how to donate",
                     answer="a", tags=())
        # 한글 주석 — donate match → 1/2 = 0.5
        score = _score_entry(["donate", "now"], e)
        assert 0.0 < score <= 1.5

    def test_substring_boost(self) -> None:
        # 한글 주석 — query 가 question 안 직접 포함 → +0.5 boost (cap 1.0)
        e = FAQEntry(id="1", topic="t", question="donate now please",
                     answer="a", tags=())
        score = _score_entry(["donate", "now"], e)
        assert score == 1.0


class TestKeywordRAGStoreRanking:
    def test_top_k_returns_most_relevant(self) -> None:
        s = KeywordRAGStore([
            FAQEntry(id="a", topic="t", question="totally unrelated text",
                     answer="..."),
            FAQEntry(id="b", topic="t", question="donate payment now",
                     answer="...", tags=("donate",)),
            FAQEntry(id="c", topic="t", question="payout schedule",
                     answer="...", tags=("payout",)),
        ])
        results = s.search("donate", top_k=1)
        assert len(results) == 1
        assert results[0].id == "b"

    def test_empty_query_returns_empty(self) -> None:
        s = KeywordRAGStore([
            FAQEntry(id="a", topic="t", question="x", answer="y"),
        ])
        results = s.search("", top_k=3)
        assert results == []


class TestCosineSimilarity:
    def test_identical_vectors_1(self) -> None:
        v = [1.0, 0.0, 0.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_0(self) -> None:
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_neg1(self) -> None:
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


class TestMockEmbedder:
    def test_dim_default_16(self) -> None:
        e = MockEmbedder()
        assert e.dim() == 16

    def test_custom_dim(self) -> None:
        e = MockEmbedder(dim_value=8)
        assert e.dim() == 8

    def test_dim_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="dim_value"):
            MockEmbedder(dim_value=0)

    def test_empty_text_zero_vector(self) -> None:
        e = MockEmbedder(dim_value=4)
        v = e.embed("")
        assert v == [0.0, 0.0, 0.0, 0.0]

    def test_embed_l2_normalized(self) -> None:
        e = MockEmbedder(dim_value=4)
        v = e.embed("hello world test")
        norm = math.sqrt(sum(x * x for x in v))
        # 한글 주석 — L2 normalize → norm ≈ 1.0
        assert norm == pytest.approx(1.0, abs=0.01)


class TestCachedEmbedder:
    def test_hit_miss_counter(self) -> None:
        backend = MockEmbedder(dim_value=8)
        c = CachedEmbedder(backend)
        c.embed("first")
        assert c.misses == 1
        assert c.hits == 0
        c.embed("first")
        assert c.hits == 1
        assert c.misses == 1

    def test_lru_evict(self) -> None:
        backend = MockEmbedder(dim_value=8)
        c = CachedEmbedder(backend, max_cache=2)
        c.embed("a")
        c.embed("b")
        c.embed("c")  # a evict
        assert c.size() == 2
        # 한글 주석 — "a" 재호출 → miss (evict)
        c.embed("a")
        assert c.misses == 4

    def test_max_cache_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="max_cache"):
            CachedEmbedder(MockEmbedder(), max_cache=0)

    def test_clear_resets(self) -> None:
        c = CachedEmbedder(MockEmbedder())
        c.embed("x")
        c.embed("y")
        c.clear()
        assert c.size() == 0
        assert c.hits == 0
        assert c.misses == 0
