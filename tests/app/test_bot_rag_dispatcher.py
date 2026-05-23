# SPDX-License-Identifier: GPL-3.0-or-later
"""bot rag_context + emoji_moderation_dispatcher unit test — cycle 169.689 신설."""

from __future__ import annotations

import pytest


class TestFAQEntry:
    def test_valid_construct(self) -> None:
        from app.bot.rag_context import FAQEntry

        e = FAQEntry(
            id="d-1", topic="donation", question="Q?", answer="A!",
            tags=("donation", "payout"),
        )
        assert e.id == "d-1"
        assert e.topic == "donation"
        assert "donation" in e.tags

    def test_empty_id_raises(self) -> None:
        from app.bot.rag_context import FAQEntry

        with pytest.raises(ValueError, match="id"):
            FAQEntry(id="", topic="x", question="q", answer="a")

    def test_empty_topic_raises(self) -> None:
        from app.bot.rag_context import FAQEntry

        with pytest.raises(ValueError, match="topic"):
            FAQEntry(id="x", topic="", question="q", answer="a")

    def test_empty_question_raises(self) -> None:
        from app.bot.rag_context import FAQEntry

        with pytest.raises(ValueError, match="question"):
            FAQEntry(id="x", topic="x", question="", answer="a")

    def test_empty_answer_raises(self) -> None:
        from app.bot.rag_context import FAQEntry

        with pytest.raises(ValueError, match="answer"):
            FAQEntry(id="x", topic="x", question="q", answer="")


class TestKeywordRAGStore:
    def test_empty_store_size_zero(self) -> None:
        from app.bot.rag_context import KeywordRAGStore

        s = KeywordRAGStore()
        assert s.size() == 0

    def test_add_entry(self) -> None:
        from app.bot.rag_context import FAQEntry, KeywordRAGStore

        s = KeywordRAGStore()
        s.add(FAQEntry(id="1", topic="t", question="q", answer="a"))
        assert s.size() == 1

    def test_add_duplicate_id_raises(self) -> None:
        from app.bot.rag_context import FAQEntry, KeywordRAGStore

        s = KeywordRAGStore()
        e1 = FAQEntry(id="1", topic="t", question="q", answer="a")
        s.add(e1)
        with pytest.raises(ValueError, match="중복"):
            s.add(FAQEntry(id="1", topic="t2", question="q2", answer="a2"))

    def test_search_returns_relevant(self) -> None:
        # 한글 주석 — token overlap + substring 매칭 verify
        from app.bot.rag_context import FAQEntry, KeywordRAGStore

        s = KeywordRAGStore([
            FAQEntry(id="d1", topic="donation",
                     question="how to donate", answer="...",
                     tags=("donate", "payment")),
            FAQEntry(id="p1", topic="payout",
                     question="when do I get paid", answer="...",
                     tags=("payout",)),
        ])
        results = s.search("donate now", top_k=2)
        assert len(results) >= 1
        # 한글 주석 — search 반환 = List[FAQEntry]
        assert results[0].id == "d1"


class TestModerationDecision:
    def test_map_approved(self) -> None:
        from app.bot.emoji_moderation_dispatcher import (
            ModerationDecision, map_to_moderation_status,
        )

        assert map_to_moderation_status(ModerationDecision.APPROVED) == "approved"

    def test_map_rejected(self) -> None:
        from app.bot.emoji_moderation_dispatcher import (
            ModerationDecision, map_to_moderation_status,
        )

        assert map_to_moderation_status(ModerationDecision.REJECTED) == "rejected"

    def test_map_dmca_takedown(self) -> None:
        from app.bot.emoji_moderation_dispatcher import (
            ModerationDecision, map_to_moderation_status,
        )

        assert map_to_moderation_status(ModerationDecision.DMCA_TAKEDOWN) == "dmca_takedown"

    def test_map_hold_for_review_returns_pending(self) -> None:
        # 한글 주석 — HOLD_FOR_REVIEW → admin queue 진입 = pending 정합
        from app.bot.emoji_moderation_dispatcher import (
            ModerationDecision, map_to_moderation_status,
        )

        assert map_to_moderation_status(ModerationDecision.HOLD_FOR_REVIEW) == "pending"


class TestModerationOutcome:
    def test_default_fields(self) -> None:
        from app.bot.emoji_moderation_dispatcher import (
            ModerationDecision, ModerationOutcome,
        )

        o = ModerationOutcome(decision=ModerationDecision.APPROVED)
        assert o.decision == ModerationDecision.APPROVED
        assert o.reasons == []
        assert o.matched_patterns == ()
