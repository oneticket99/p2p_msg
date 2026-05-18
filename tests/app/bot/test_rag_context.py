# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.rag_context`` 단위 테스트.

FAQEntry 검증 + KeywordRAGStore (substring + token overlap) + ranking +
EmbeddingRAGStore placeholder + build_default_toonation_faq 10 entry +
compose_rag_context markdown 산출.
"""

from __future__ import annotations

import pytest

from app.bot.rag_context import (
    EmbeddingRAGStore,
    FAQEntry,
    KeywordRAGStore,
    build_default_toonation_faq,
    compose_rag_context,
)


def _entry(
    *,
    id: str = "test-001",
    topic: str = "donation",
    question: str = "테스트 질문?",
    answer: str = "테스트 답변.",
    tags: tuple = (),
) -> FAQEntry:
    return FAQEntry(
        id=id, topic=topic, question=question, answer=answer, tags=tags
    )


class TestFAQEntryValidation:
    """``FAQEntry`` dataclass 검증."""

    def test_valid_construction(self) -> None:
        entry = _entry()
        assert entry.id == "test-001"
        assert entry.tags == ()

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="id 빈 문자열 불가"):
            _entry(id="")

    def test_empty_topic_rejected(self) -> None:
        with pytest.raises(ValueError, match="topic 빈 문자열 불가"):
            _entry(topic="")

    def test_empty_question_rejected(self) -> None:
        with pytest.raises(ValueError, match="question 빈 문자열 불가"):
            _entry(question="")

    def test_empty_answer_rejected(self) -> None:
        with pytest.raises(ValueError, match="answer 빈 문자열 불가"):
            _entry(answer="")

    def test_with_tags(self) -> None:
        entry = _entry(tags=("후원", "결제"))
        assert "후원" in entry.tags


class TestKeywordRAGStore:
    """``KeywordRAGStore`` substring + token overlap 검증."""

    def test_empty_store(self) -> None:
        store = KeywordRAGStore()
        assert store.size() == 0
        assert store.search("test") == []

    def test_add_size(self) -> None:
        store = KeywordRAGStore()
        store.add(_entry(id="a"))
        store.add(_entry(id="b"))
        assert store.size() == 2

    def test_add_duplicate_rejected(self) -> None:
        store = KeywordRAGStore()
        store.add(_entry(id="x"))
        with pytest.raises(ValueError, match="id 중복"):
            store.add(_entry(id="x"))

    def test_init_with_entries(self) -> None:
        entries = [_entry(id="a"), _entry(id="b")]
        store = KeywordRAGStore(entries)
        assert store.size() == 2

    def test_search_empty_query(self) -> None:
        store = KeywordRAGStore([_entry()])
        assert store.search("") == []

    def test_search_substring_match(self) -> None:
        store = KeywordRAGStore(
            [
                _entry(id="a", question="후원 결제 방법?"),
                _entry(id="b", question="환불 처리 방법?"),
            ]
        )
        results = store.search("후원")
        assert len(results) == 1
        assert results[0].id == "a"

    def test_search_token_overlap_ranks(self) -> None:
        store = KeywordRAGStore(
            [
                _entry(id="a", question="후원 결제 정책"),
                _entry(id="b", question="환불 처리 절차"),
                _entry(id="c", question="후원 환불 의 차이"),
            ]
        )
        # "후원 환불" 의 token overlap = c 가 가장 높음
        results = store.search("후원 환불")
        assert results[0].id == "c"

    def test_search_top_k_limit(self) -> None:
        store = KeywordRAGStore(
            [
                _entry(id=f"e{i}", question=f"후원 질문 {i}")
                for i in range(5)
            ]
        )
        results = store.search("후원", top_k=2)
        assert len(results) == 2

    def test_search_zero_top_k_rejected(self) -> None:
        store = KeywordRAGStore([_entry()])
        with pytest.raises(ValueError, match="top_k 양수 의무"):
            store.search("query", top_k=0)

    def test_search_no_match_returns_empty(self) -> None:
        store = KeywordRAGStore([_entry(question="후원 정책")])
        results = store.search("관련없는키워드")
        assert results == []

    def test_search_tags_matched(self) -> None:
        store = KeywordRAGStore(
            [_entry(id="a", question="질문", tags=("후원", "결제"))]
        )
        results = store.search("후원")
        assert len(results) == 1


class TestEmbeddingRAGStore:
    """``EmbeddingRAGStore`` Embedder backend + cosine sim ranking 검증 (cycle 75)."""

    def _store(self, entries=None):
        from app.bot.rag_context import MockEmbedder

        embedder = MockEmbedder(dim_value=32)
        return EmbeddingRAGStore(embedder=embedder, entries=entries)

    def test_add_size(self) -> None:
        store = self._store()
        store.add(_entry())
        assert store.size() == 1

    def test_duplicate_id_rejected(self) -> None:
        store = self._store([_entry()])
        with pytest.raises(ValueError, match="중복"):
            store.add(_entry())

    def test_search_top_k_zero_rejected(self) -> None:
        store = self._store([_entry()])
        with pytest.raises(ValueError, match="top_k"):
            store.search("query", top_k=0)

    def test_search_empty_query(self) -> None:
        store = self._store([_entry()])
        assert store.search("") == []

    def test_search_empty_store(self) -> None:
        store = self._store()
        assert store.search("query") == []

    def test_search_ranks_by_similarity(self) -> None:
        from app.bot.rag_context import FAQEntry

        store = self._store(
            [
                FAQEntry(
                    id="a",
                    topic="t",
                    question="후원 결제 수단",
                    answer="ans-a",
                    tags=("후원", "결제"),
                ),
                FAQEntry(
                    id="b",
                    topic="t",
                    question="환불 정책 일자",
                    answer="ans-b",
                    tags=("환불",),
                ),
            ]
        )
        result = store.search("후원 결제", top_k=2)
        assert result
        # 후원 결제 query → 후원 결제 entry 가 첫 매치
        assert result[0].id == "a"

    def test_search_top_k_cap(self) -> None:
        from app.bot.rag_context import FAQEntry

        entries = [
            FAQEntry(
                id=f"x-{i}",
                topic="t",
                question=f"후원 결제 {i}",
                answer=f"a-{i}",
                tags=("후원",),
            )
            for i in range(5)
        ]
        store = self._store(entries)
        result = store.search("후원", top_k=2)
        assert len(result) <= 2


class TestMockEmbedder:
    """``MockEmbedder`` deterministic hash 기반 embedder 검증."""

    def test_dim_value_validation(self) -> None:
        from app.bot.rag_context import MockEmbedder

        with pytest.raises(ValueError, match="dim_value"):
            MockEmbedder(dim_value=0)

    def test_dim_returns_value(self) -> None:
        from app.bot.rag_context import MockEmbedder

        assert MockEmbedder(dim_value=8).dim() == 8

    def test_empty_text_zero_vector(self) -> None:
        from app.bot.rag_context import MockEmbedder

        vec = MockEmbedder(dim_value=4).embed("")
        assert vec == [0.0, 0.0, 0.0, 0.0]

    def test_non_empty_text_normalized(self) -> None:
        from app.bot.rag_context import MockEmbedder

        vec = MockEmbedder(dim_value=8).embed("후원 결제 수단")
        # L2 norm ≈ 1.0
        import math

        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 1e-9

    def test_deterministic(self) -> None:
        from app.bot.rag_context import MockEmbedder

        e = MockEmbedder(dim_value=16)
        assert e.embed("query text") == e.embed("query text")


class TestCachedEmbedder:
    """``CachedEmbedder`` LRU cache decorator 검증 (cycle 79)."""

    def test_max_cache_zero_rejected(self) -> None:
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        with pytest.raises(ValueError, match="max_cache"):
            CachedEmbedder(MockEmbedder(dim_value=4), max_cache=0)

    def test_max_cache_negative_rejected(self) -> None:
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        with pytest.raises(ValueError, match="max_cache"):
            CachedEmbedder(MockEmbedder(dim_value=4), max_cache=-1)

    def test_first_call_miss_second_call_hit(self) -> None:
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        c = CachedEmbedder(MockEmbedder(dim_value=8), max_cache=4)
        v1 = c.embed("query")
        v2 = c.embed("query")
        assert v1 == v2
        assert c.hits == 1
        assert c.misses == 1

    def test_different_text_separate_miss(self) -> None:
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        c = CachedEmbedder(MockEmbedder(dim_value=8), max_cache=4)
        c.embed("query a")
        c.embed("query b")
        assert c.hits == 0
        assert c.misses == 2
        assert c.size() == 2

    def test_lru_eviction_at_capacity(self) -> None:
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        c = CachedEmbedder(MockEmbedder(dim_value=8), max_cache=2)
        c.embed("a")
        c.embed("b")
        c.embed("c")  # "a" evicted
        # "a" 의 재호출 = miss (cache 부재)
        c.embed("a")
        assert c.misses == 4  # a + b + c + a (재호출)
        assert c.size() == 2  # b + c 의 evict 후 의 b + a 또는 c + a

    def test_lru_move_to_end_on_hit(self) -> None:
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        c = CachedEmbedder(MockEmbedder(dim_value=8), max_cache=2)
        c.embed("a")
        c.embed("b")
        c.embed("a")  # "a" hit + LRU 의 의 끝 이동
        c.embed("c")  # "b" evict (a 의 최근)
        # "a" 의 재호출 = hit (still cached)
        c.embed("a")
        assert c.hits == 2  # 2번째 a + 4번째 a
        assert c.misses == 3  # a + b + c

    def test_dim_delegates(self) -> None:
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        c = CachedEmbedder(MockEmbedder(dim_value=12))
        assert c.dim() == 12

    def test_reset_stats(self) -> None:
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        c = CachedEmbedder(MockEmbedder(dim_value=4), max_cache=4)
        c.embed("q")
        c.embed("q")
        c.reset_stats()
        assert c.hits == 0
        assert c.misses == 0
        # cache 는 보존
        assert c.size() == 1

    def test_clear_resets_cache_and_stats(self) -> None:
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        c = CachedEmbedder(MockEmbedder(dim_value=4), max_cache=4)
        c.embed("q")
        c.clear()
        assert c.size() == 0
        assert c.hits == 0
        assert c.misses == 0

    def test_works_with_embedding_rag_store(self) -> None:
        from app.bot.rag_context import (
            CachedEmbedder,
            EmbeddingRAGStore,
            FAQEntry,
            MockEmbedder,
        )

        cached = CachedEmbedder(MockEmbedder(dim_value=16), max_cache=8)
        store = EmbeddingRAGStore(
            embedder=cached,
            entries=[
                FAQEntry(
                    id="x",
                    topic="t",
                    question="후원 결제",
                    answer="ans",
                    tags=("후원",),
                )
            ],
        )
        # add 시 1 miss + search 시 query embed 1 miss
        store.search("후원")
        store.search("후원")
        # 2번째 search = query hit
        assert cached.hits >= 1


class TestCachedEmbedderConcurrency:
    """cycle 94 — `threading.RLock` 기반 multi-thread 안전성 회귀 검증.

    ThreadPoolExecutor 로 동시 embed 호출 후 cache + counter 무결성 확인.
    reviewer P1-2 회수 — async sentence-transformers 전환 prerequisite.
    """

    def test_concurrent_same_text_no_corruption(self) -> None:
        """동일 text 동시 embed 호출 시 cache size + hits+misses 합산 무결성.

        50 thread 가 동일 text 호출 → cache size 1 + 합산 = 50.
        race condition 부재 시 sum(hits, misses) = 호출 횟수.
        """

        from concurrent.futures import ThreadPoolExecutor
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        cached = CachedEmbedder(MockEmbedder(dim_value=8), max_cache=16)

        def _call() -> int:
            return len(cached.embed("동일-텍스트"))

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: _call(), range(50)))

        # 50 호출 모두 동일 dim
        assert all(r == 8 for r in results)
        # cache size = 1 (동일 text)
        assert cached.size() == 1
        # hits + misses 합산 = 50 (counter increment race 차단)
        assert cached.hits + cached.misses == 50
        # 최소 1 miss (첫 호출) + 나머지 hit
        assert cached.misses >= 1

    def test_concurrent_distinct_text_under_capacity(self) -> None:
        """서로 다른 text 동시 embed → cache 에 모두 등록 + 합산 무결성."""

        from concurrent.futures import ThreadPoolExecutor
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        cached = CachedEmbedder(MockEmbedder(dim_value=4), max_cache=64)
        texts = [f"text-{i}" for i in range(32)]

        def _call(t: str) -> int:
            return len(cached.embed(t))

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(_call, texts))

        assert all(r == 4 for r in results)
        # 32 distinct text 모두 cache 등록
        assert cached.size() == 32
        # 각 text 1회씩 호출 = 모두 miss
        assert cached.misses == 32
        assert cached.hits == 0

    def test_concurrent_lru_eviction_size_bounded(self) -> None:
        """동시 embed 가 max_cache 초과 시 size <= max_cache 보장."""

        from concurrent.futures import ThreadPoolExecutor
        from app.bot.rag_context import CachedEmbedder, MockEmbedder

        cached = CachedEmbedder(MockEmbedder(dim_value=4), max_cache=8)

        def _call(i: int) -> int:
            return len(cached.embed(f"text-{i}"))

        # max_cache=8, 100 distinct text — eviction race 발생
        with ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(_call, range(100)))

        # size 가 max_cache 초과 금지
        assert cached.size() <= 8
        # 모든 호출이 counter 에 반영
        assert cached.hits + cached.misses == 100


class TestCosineSimilarity:
    """``cosine_similarity`` 벡터 유사도 검증."""

    def test_dim_mismatch_rejected(self) -> None:
        from app.bot.rag_context import cosine_similarity

        with pytest.raises(ValueError, match="차원"):
            cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])

    def test_empty_vector_rejected(self) -> None:
        from app.bot.rag_context import cosine_similarity

        with pytest.raises(ValueError, match="빈"):
            cosine_similarity([], [])

    def test_identical_vectors_one(self) -> None:
        from app.bot.rag_context import cosine_similarity

        assert abs(cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9

    def test_orthogonal_vectors_zero(self) -> None:
        from app.bot.rag_context import cosine_similarity

        assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-9

    def test_zero_norm_returns_zero(self) -> None:
        from app.bot.rag_context import cosine_similarity

        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


class TestBuildDefaultToonationFAQ:
    """``build_default_toonation_faq`` 10 entry + 5 영역 검증."""

    def test_returns_10_entries(self) -> None:
        faq = build_default_toonation_faq()
        assert len(faq) == 10

    def test_5_topics_covered(self) -> None:
        faq = build_default_toonation_faq()
        topics = {e.topic for e in faq}
        assert topics == {"donation", "payout", "obs", "fraud", "refund"}

    def test_all_have_tags(self) -> None:
        faq = build_default_toonation_faq()
        for e in faq:
            assert len(e.tags) > 0

    def test_ids_unique(self) -> None:
        faq = build_default_toonation_faq()
        ids = [e.id for e in faq]
        assert len(ids) == len(set(ids))


class TestComposeRagContext:
    """``compose_rag_context`` markdown 산출."""

    def test_empty_store_returns_empty(self) -> None:
        store = KeywordRAGStore()
        assert compose_rag_context("query", store) == ""

    def test_no_match_returns_empty(self) -> None:
        store = KeywordRAGStore([_entry(question="다른 주제")])
        assert compose_rag_context("관련없음", store) == ""

    def test_match_returns_markdown(self) -> None:
        store = KeywordRAGStore(
            [_entry(id="a", question="후원 결제?", answer="카드/토스")]
        )
        ctx = compose_rag_context("후원", store)
        assert "# 참고 FAQ" in ctx
        assert "Q: 후원 결제?" in ctx
        assert "A: 카드/토스" in ctx

    def test_default_faq_donation_query(self) -> None:
        store = KeywordRAGStore(build_default_toonation_faq())
        ctx = compose_rag_context("후원 결제 수단", store, top_k=3)
        assert "# 참고 FAQ" in ctx
        # 후원 관련 entry top 포함 검증
        assert "후원" in ctx
