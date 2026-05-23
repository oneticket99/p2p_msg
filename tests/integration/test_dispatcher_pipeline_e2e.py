# SPDX-License-Identifier: GPL-3.0-or-later
"""EmojiModerationDispatcher 4-stage pipeline chain E2E — cycle 169.699 신설.

chain:
1. empty image → HOLD_FOR_REVIEW
2. OCR JAILBREAK_TEXT → REJECTED
3. OCR BLOCKED → REJECTED
4. OCR SUSPICIOUS → HOLD_FOR_REVIEW
5. OCR NONE + no DMCA db → APPROVED
6. DMCA match (fuzzy) → DMCA_TAKEDOWN
7. DMCA exception graceful → HOLD_FOR_REVIEW (admin 위탁)
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.bot.emoji_moderation_dispatcher import (
    EmojiModerationDispatcher, ModerationDecision,
)


pytestmark = pytest.mark.integration


def _ocr_result(signal_name: str, patterns=()):
    from app.bot.jailbreak_detector_ocr import OcrModerationSignal

    signal = getattr(OcrModerationSignal, signal_name)
    return SimpleNamespace(
        signal=signal, reasons=[], matched_patterns=tuple(patterns),
    )


class TestEmptyImage:
    def test_empty_holds_for_review(self) -> None:
        d = EmojiModerationDispatcher()
        outcome = d.evaluate(b"")
        assert outcome.decision == ModerationDecision.HOLD_FOR_REVIEW
        assert "empty" in outcome.reasons[0]


class TestOcrSignalReject:
    def test_jailbreak_text_rejected(self) -> None:
        d = EmojiModerationDispatcher()
        with patch(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            return_value=_ocr_result("JAILBREAK_TEXT"),
        ):
            outcome = d.evaluate(b"\x89PNG\r\n\x1a\n")
        assert outcome.decision == ModerationDecision.REJECTED
        assert any("jailbreak" in r.lower() for r in outcome.reasons)

    def test_blocked_signal_rejected(self) -> None:
        d = EmojiModerationDispatcher()
        with patch(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            return_value=_ocr_result("BLOCKED"),
        ):
            outcome = d.evaluate(b"\x89PNG\r\n\x1a\n")
        assert outcome.decision == ModerationDecision.REJECTED


class TestOcrSuspicious:
    def test_suspicious_holds(self) -> None:
        d = EmojiModerationDispatcher()
        with patch(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            return_value=_ocr_result("SUSPICIOUS"),
        ):
            outcome = d.evaluate(b"\x89PNG\r\n\x1a\n")
        assert outcome.decision == ModerationDecision.HOLD_FOR_REVIEW


class TestOcrCleanNoDmca:
    def test_clean_approves(self) -> None:
        d = EmojiModerationDispatcher()
        with patch(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            return_value=_ocr_result("NONE"),
        ):
            outcome = d.evaluate(b"\x89PNG\r\n\x1a\n")
        assert outcome.decision == ModerationDecision.APPROVED
        assert any("clean" in r.lower() for r in outcome.reasons)


class TestDmcaChain:
    def test_dmca_match_takedown(self) -> None:
        d = EmojiModerationDispatcher(known_dmca_hashes={"a" * 32})
        dmca_result = SimpleNamespace(
            is_infringement=True, confidence=0.95, matched_hash="a" * 32,
        )
        with patch(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            return_value=_ocr_result("NONE"),
        ), patch(
            "app.bot.emoji_moderation_dispatcher.compute_combined_hash",
            return_value="b" * 32,
        ), patch(
            "app.bot.emoji_moderation_dispatcher.check_known_infringement_fuzzy",
            return_value=dmca_result,
        ):
            outcome = d.evaluate(b"\x89PNG\r\n\x1a\n")
        assert outcome.decision == ModerationDecision.DMCA_TAKEDOWN

    def test_dmca_exception_graceful_approve(self) -> None:
        # 한글 주석 — DMCA chain 예외 → graceful + OCR clean = APPROVED
        d = EmojiModerationDispatcher(known_dmca_hashes={"a" * 32})
        with patch(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            return_value=_ocr_result("NONE"),
        ), patch(
            "app.bot.emoji_moderation_dispatcher.compute_combined_hash",
            side_effect=RuntimeError("PIL missing"),
        ):
            outcome = d.evaluate(b"\x89PNG\r\n\x1a\n")
        assert outcome.decision == ModerationDecision.APPROVED
        assert any("DMCA chain 예외" in r for r in outcome.reasons)


class TestKnownHashesNormalization:
    def test_none_defaults_empty(self) -> None:
        d = EmojiModerationDispatcher(known_dmca_hashes=None)
        assert d._known_dmca_hashes == set()

    def test_fuzzy_threshold_stored(self) -> None:
        d = EmojiModerationDispatcher(fuzzy_threshold=10)
        assert d._fuzzy_threshold == 10
