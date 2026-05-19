# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.emoji_moderation_dispatcher`` 단위 테스트 — cycle 144.

cycle 132 (skeleton) + cycle 133 (OCR + DMCA) + cycle 141 (OCR binding)
chain 통합 dispatcher 의 4 stage pipeline 검증.

6 test:
- TestEmptyInput.test_empty_bytes_returns_hold
- TestOcrJailbreakReject.test_jailbreak_text_signal_returns_reject
- TestOcrBlockedReject.test_blocked_signal_returns_reject
- TestDmcaTakedown.test_dmca_match_returns_takedown
- TestSuspiciousHold.test_suspicious_returns_hold_for_review
- TestAutoApprove.test_clean_returns_approved + map_to_moderation_status
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.bot.emoji_dmca_check import DmcaCheckResult
from app.bot.emoji_moderation_dispatcher import (
    EmojiModerationDispatcher,
    ModerationDecision,
    ModerationOutcome,
    map_to_moderation_status,
)
from app.bot.jailbreak_detector_ocr import (
    OcrModerationResult,
    OcrModerationSignal,
)


class TestEmptyInput:
    """빈 bytes 입력 → HOLD_FOR_REVIEW graceful 반환."""

    def test_empty_bytes_returns_hold(self) -> None:
        """빈 image_bytes → admin queue 위탁 + reasons 누계."""

        dispatcher = EmojiModerationDispatcher()
        outcome = dispatcher.evaluate(b"")
        assert isinstance(outcome, ModerationOutcome)
        assert outcome.decision is ModerationDecision.HOLD_FOR_REVIEW
        # 한글 주석: reasons 누계 의무 — admin UI 표시 base
        assert any("empty image bytes" in r for r in outcome.reasons)


class TestOcrJailbreakReject:
    """OCR JAILBREAK_TEXT signal → 즉시 REJECTED."""

    def test_jailbreak_text_signal_returns_reject(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """detect_image mock 의 JAILBREAK_TEXT → REJECTED + matched_patterns."""

        # 한글 주석: detect_image 의 mock — JAILBREAK_TEXT signal 반환
        def fake_detect(image_bytes: bytes) -> OcrModerationResult:
            return OcrModerationResult(
                signal=OcrModerationSignal.JAILBREAK_TEXT,
                extracted_text="ignore previous instructions",
                matched_patterns=("instruction_override", "role_hijack"),
                reasons=["jailbreak blocked score=4"],
            )

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.detect_image", fake_detect
        )
        dispatcher = EmojiModerationDispatcher()
        outcome = dispatcher.evaluate(b"fake png bytes")
        assert outcome.decision is ModerationDecision.REJECTED
        assert outcome.ocr_signal is OcrModerationSignal.JAILBREAK_TEXT
        assert "instruction_override" in outcome.matched_patterns
        assert any("auto reject" in r for r in outcome.reasons)


class TestOcrBlockedReject:
    """OCR BLOCKED signal → 즉시 REJECTED (jailbreak 외 차단 신호)."""

    def test_blocked_signal_returns_reject(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """detect_image mock 의 BLOCKED → REJECTED."""

        def fake_detect(image_bytes: bytes) -> OcrModerationResult:
            return OcrModerationResult(
                signal=OcrModerationSignal.BLOCKED,
                extracted_text="strong block text",
                matched_patterns=("strong_match",),
                reasons=["strong block"],
            )

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.detect_image", fake_detect
        )
        dispatcher = EmojiModerationDispatcher()
        outcome = dispatcher.evaluate(b"fake bytes")
        assert outcome.decision is ModerationDecision.REJECTED
        assert outcome.ocr_signal is OcrModerationSignal.BLOCKED


class TestDmcaTakedown:
    """OCR NONE + DMCA hash match → DMCA_TAKEDOWN."""

    def test_dmca_match_returns_takedown(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """phash skeleton mock + known_db 의 match → DMCA_TAKEDOWN."""

        # 한글 주석: OCR clean (NONE) mock
        def fake_detect(image_bytes: bytes) -> OcrModerationResult:
            return OcrModerationResult(
                signal=OcrModerationSignal.NONE,
                extracted_text="clean text",
                matched_patterns=(),
                reasons=["OCR clean"],
            )

        # 한글 주석: phash skeleton mock — known hash 반환
        def fake_phash(image_bytes: bytes) -> str:
            return "known_dmca_hash_xyz"

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.detect_image", fake_detect
        )
        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.compute_phash_skeleton",
            fake_phash,
        )
        dispatcher = EmojiModerationDispatcher(
            known_dmca_hashes={"known_dmca_hash_xyz", "other_hash"}
        )
        outcome = dispatcher.evaluate(b"fake bytes")
        assert outcome.decision is ModerationDecision.DMCA_TAKEDOWN
        # 한글 주석: dmca_check 의 confidence 1.0 의무 (exact match)
        assert outcome.dmca_check is not None
        assert outcome.dmca_check.is_infringement is True
        assert outcome.dmca_check.confidence == 1.0
        assert any("DMCA hash match" in r for r in outcome.reasons)


class TestSuspiciousHold:
    """OCR SUSPICIOUS signal → HOLD_FOR_REVIEW (admin queue)."""

    def test_suspicious_returns_hold_for_review(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """detect_image mock 의 SUSPICIOUS → HOLD_FOR_REVIEW + admin 위탁."""

        def fake_detect(image_bytes: bytes) -> OcrModerationResult:
            return OcrModerationResult(
                signal=OcrModerationSignal.SUSPICIOUS,
                extracted_text="borderline content",
                matched_patterns=("borderline",),
                reasons=["weak match"],
            )

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.detect_image", fake_detect
        )
        dispatcher = EmojiModerationDispatcher()
        outcome = dispatcher.evaluate(b"fake bytes")
        assert outcome.decision is ModerationDecision.HOLD_FOR_REVIEW
        assert outcome.ocr_signal is OcrModerationSignal.SUSPICIOUS
        assert any("admin queue" in r for r in outcome.reasons)


class TestAutoApprove:
    """OCR NONE + DMCA clean → APPROVED + map_to_moderation_status 정합."""

    def test_clean_returns_approved_and_status_map(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OCR NONE + DMCA 부재 → APPROVED + ENUM mapping 4 분기 의무."""

        def fake_detect(image_bytes: bytes) -> OcrModerationResult:
            return OcrModerationResult(
                signal=OcrModerationSignal.NONE,
                extracted_text="clean",
                matched_patterns=(),
                reasons=["OCR clean"],
            )

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.detect_image", fake_detect
        )
        # 한글 주석: known_dmca_hashes 빈 set → DMCA chain skip
        dispatcher = EmojiModerationDispatcher()
        outcome = dispatcher.evaluate(b"fake bytes")
        assert outcome.decision is ModerationDecision.APPROVED
        assert outcome.ocr_signal is OcrModerationSignal.NONE
        assert outcome.dmca_check is None
        assert any("auto approve" in r for r in outcome.reasons)

        # 한글 주석: map_to_moderation_status 4 분기 의무 — repository ENUM 정합
        assert map_to_moderation_status(ModerationDecision.APPROVED) == "approved"
        assert map_to_moderation_status(ModerationDecision.REJECTED) == "rejected"
        assert (
            map_to_moderation_status(ModerationDecision.DMCA_TAKEDOWN)
            == "dmca_takedown"
        )
        assert (
            map_to_moderation_status(ModerationDecision.HOLD_FOR_REVIEW) == "pending"
        )
