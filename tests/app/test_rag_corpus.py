# SPDX-License-Identifier: GPL-3.0-or-later
"""bot rag_corpus snippet unit test — cycle 169.713 신설."""

from __future__ import annotations


class TestRagCorpus:
    def test_get_snippet_returns_string(self) -> None:
        from app.bot.rag_corpus import get_corpus_snippet

        s = get_corpus_snippet()
        assert isinstance(s, str)
        assert len(s) > 0

    def test_snippet_includes_toonation(self) -> None:
        from app.bot.rag_corpus import get_corpus_snippet

        s = get_corpus_snippet()
        assert "Toonation" in s
        assert "투네이션" in s

    def test_corpus_contains_obs_settings(self) -> None:
        # 한글 주석 — OBS 설정 chain 의 corpus 안 등재 verify
        from app.bot.rag_corpus import get_corpus_snippet

        s = get_corpus_snippet()
        assert "OBS" in s
        assert "위젯" in s

    def test_corpus_contains_refund_chain(self) -> None:
        from app.bot.rag_corpus import get_corpus_snippet

        s = get_corpus_snippet()
        assert "사기 신고" in s or "환불" in s

    def test_corpus_lists_5_platforms(self) -> None:
        # 한글 주석 — 5 연동 platform 등재 verify
        from app.bot.rag_corpus import get_corpus_snippet

        s = get_corpus_snippet()
        assert "트위치" in s or "Twitch" in s
        assert "아프리카" in s
        assert "유튜브" in s or "YouTube" in s
        assert "치지직" in s or "CHZZK" in s
