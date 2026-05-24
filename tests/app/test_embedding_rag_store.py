# SPDX-License-Identifier: GPL-3.0-or-later
"""bot EmbeddingRAGStore unit — cycle 169.733 신설."""

from __future__ import annotations

import pytest


def _entry(eid: str, question: str, tags=()):
    from app.bot.rag_context import FAQEntry

    return FAQEntry(id=eid, topic="t", question=question, answer="a", tags=tags)


class TestEmbeddingRAGStoreInit:
    def test_empty_store(self) -> None:
        from app.bot.rag_context import EmbeddingRAGStore, MockEmbedder

        s = EmbeddingRAGStore(MockEmbedder(dim_value=8))
        assert s.size() == 0

    def test_init_with_entries(self) -> None:
        from app.bot.rag_context import EmbeddingRAGStore, MockEmbedder

        s = EmbeddingRAGStore(
            MockEmbedder(dim_value=8),
            entries=[_entry("1", "how to donate"), _entry("2", "payout schedule")],
        )
        assert s.size() == 2


class TestEmbeddingRAGStoreAdd:
    def test_add_increments(self) -> None:
        from app.bot.rag_context import EmbeddingRAGStore, MockEmbedder

        s = EmbeddingRAGStore(MockEmbedder(dim_value=8))
        s.add(_entry("1", "q1"))
        assert s.size() == 1

    def test_duplicate_id_raises(self) -> None:
        from app.bot.rag_context import EmbeddingRAGStore, MockEmbedder

        s = EmbeddingRAGStore(MockEmbedder(dim_value=8))
        s.add(_entry("1", "q1"))
        with pytest.raises(ValueError, match="중복"):
            s.add(_entry("1", "q2"))

    def test_tags_concat_for_embed(self) -> None:
        # 한글 주석 — tags 결합 embed → recall 향상 path verify (예외 부재)
        from app.bot.rag_context import EmbeddingRAGStore, MockEmbedder

        s = EmbeddingRAGStore(MockEmbedder(dim_value=8))
        s.add(_entry("1", "donate", tags=("payment", "krw")))
        assert s.size() == 1


class TestEmbeddingRAGStoreSearch:
    def test_top_k_invalid_raises(self) -> None:
        from app.bot.rag_context import EmbeddingRAGStore, MockEmbedder

        s = EmbeddingRAGStore(MockEmbedder(dim_value=8))
        with pytest.raises(ValueError, match="top_k"):
            s.search("query", top_k=0)

    def test_empty_query_returns_empty(self) -> None:
        from app.bot.rag_context import EmbeddingRAGStore, MockEmbedder

        s = EmbeddingRAGStore(
            MockEmbedder(dim_value=8), entries=[_entry("1", "donate")],
        )
        assert s.search("", top_k=3) == []

    def test_empty_store_returns_empty(self) -> None:
        from app.bot.rag_context import EmbeddingRAGStore, MockEmbedder

        s = EmbeddingRAGStore(MockEmbedder(dim_value=8))
        assert s.search("donate", top_k=3) == []

    def test_search_returns_relevant(self) -> None:
        # 한글 주석 — donate query → donate entry 가장 상위 (cosine sim)
        from app.bot.rag_context import EmbeddingRAGStore, MockEmbedder

        s = EmbeddingRAGStore(
            MockEmbedder(dim_value=16),
            entries=[
                _entry("a", "totally unrelated random text here"),
                _entry("b", "donate payment krw amount", tags=("donate",)),
            ],
        )
        results = s.search("donate payment", top_k=2)
        # 한글 주석 — donate entry retain (sim > 0)
        assert len(results) >= 1
        assert any(e.id == "b" for e in results)
