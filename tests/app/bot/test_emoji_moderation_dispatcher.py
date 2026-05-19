# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.emoji_moderation_dispatcher`` 단위 테스트 — cycle 151.

cycle 132 (skeleton) + cycle 133 (OCR + DMCA) + cycle 141 (OCR binding) +
cycle 144 (dispatcher 4 stage) + cycle 150 (DMCA combined hash + fuzzy) +
cycle 151 (dispatcher 의 cycle 150 actual binding) chain 검증.

10 test:
- TestEmptyInput.test_empty_bytes_returns_hold
- TestOcrJailbreakReject.test_jailbreak_text_signal_returns_reject
- TestOcrBlockedReject.test_blocked_signal_returns_reject
- TestDmcaTakedown.test_dmca_match_returns_takedown
- TestSuspiciousHold.test_suspicious_returns_hold_for_review
- TestAutoApprove.test_clean_returns_approved + map_to_moderation_status
- TestDmcaFuzzyMatch.test_fuzzy_match_within_threshold_returns_takedown  (신규)
- TestDmcaFuzzyMatch.test_fuzzy_miss_outside_threshold_returns_approved  (신규)
- TestDmcaCombinedHash.test_combined_hash_invoked_in_dispatcher          (신규)
- TestDmcaThresholdOverride.test_strict_threshold_zero_exact_only        (신규)
"""

from __future__ import annotations

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


# 한글 주석: known DMCA hash database = placeholder 32자 hex (phash 16자 + dhash 16자)
# 한글 주석: 실 등록 = 사용자 manual 의무 (cycle 151 절대 금지 — placeholder set 만)
PLACEHOLDER_KNOWN_HASH_A = "ffeeddccbbaa99887766554433221100"  # 32자 hex
PLACEHOLDER_KNOWN_HASH_B = "0011223344556677889900aabbccddee"  # 32자 hex


def _ocr_clean() -> OcrModerationResult:
    """OCR clean (NONE) 의 helper — 다수 test 의 공용 mock."""

    return OcrModerationResult(
        signal=OcrModerationSignal.NONE,
        extracted_text="clean text",
        matched_patterns=(),
        reasons=["OCR clean"],
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
    """OCR NONE + DMCA combined hash exact match → DMCA_TAKEDOWN."""

    def test_dmca_match_returns_takedown(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """compute_combined_hash mock + known_db 의 exact match → DMCA_TAKEDOWN."""

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            lambda image_bytes: _ocr_clean(),
        )

        # 한글 주석: compute_combined_hash mock — known hash 반환 (exact match)
        def fake_combined(image_bytes: bytes) -> str:
            return PLACEHOLDER_KNOWN_HASH_A

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.compute_combined_hash",
            fake_combined,
        )
        dispatcher = EmojiModerationDispatcher(
            known_dmca_hashes={PLACEHOLDER_KNOWN_HASH_A, PLACEHOLDER_KNOWN_HASH_B}
        )
        outcome = dispatcher.evaluate(b"fake bytes")
        assert outcome.decision is ModerationDecision.DMCA_TAKEDOWN
        # 한글 주석: dmca_check 의 confidence 1.0 의무 (exact match — distance=0)
        assert outcome.dmca_check is not None
        assert outcome.dmca_check.is_infringement is True
        assert outcome.dmca_check.confidence == 1.0
        assert outcome.dmca_check.matched_hash == PLACEHOLDER_KNOWN_HASH_A
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

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            lambda image_bytes: _ocr_clean(),
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


class TestDmcaFuzzyMatch:
    """cycle 151 신규 — DMCA fuzzy match (hamming distance threshold) 검증."""

    def test_fuzzy_match_within_threshold_returns_takedown(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_known_infringement_fuzzy 의 fuzzy hit → DMCA_TAKEDOWN + confidence < 1.0."""

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            lambda image_bytes: _ocr_clean(),
        )

        # 한글 주석: compute_combined_hash mock — 32자 hex (실 binding 회피)
        def fake_combined(image_bytes: bytes) -> str:
            return "aaaaaaaaaaaaaaaabbbbbbbbbbbbbbbb"

        # 한글 주석: check_known_infringement_fuzzy mock — fuzzy hit (distance=3, threshold=5)
        def fake_fuzzy(
            image_hash: str, known_db: set, threshold: int = 5
        ) -> DmcaCheckResult:
            assert threshold == 5  # default
            assert image_hash == "aaaaaaaaaaaaaaaabbbbbbbbbbbbbbbb"
            return DmcaCheckResult(
                is_infringement=True,
                matched_hash="aaaaaaaaaaaaaaaabbbbbbbbbbbbbbbc",  # 3 bit 차이
                confidence=1.0 - (3 / 5),  # 0.4
            )

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.compute_combined_hash",
            fake_combined,
        )
        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.check_known_infringement_fuzzy",
            fake_fuzzy,
        )
        dispatcher = EmojiModerationDispatcher(
            known_dmca_hashes={"aaaaaaaaaaaaaaaabbbbbbbbbbbbbbbc"}
        )
        outcome = dispatcher.evaluate(b"fake bytes")
        assert outcome.decision is ModerationDecision.DMCA_TAKEDOWN
        assert outcome.dmca_check is not None
        assert outcome.dmca_check.is_infringement is True
        # 한글 주석: fuzzy match 의 confidence < 1.0 의무 (distance > 0)
        assert outcome.dmca_check.confidence == pytest.approx(0.4)
        assert any("DMCA hash match" in r for r in outcome.reasons)
        # 한글 주석: reasons 안 threshold 표기 의무 (audit log 정합)
        assert any("threshold=5" in r for r in outcome.reasons)

    def test_fuzzy_miss_outside_threshold_returns_approved(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """check_known_infringement_fuzzy 의 miss → DMCA chain pass → APPROVED."""

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            lambda image_bytes: _ocr_clean(),
        )
        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.compute_combined_hash",
            lambda image_bytes: "00000000000000000000000000000000",
        )

        # 한글 주석: fuzzy miss — distance > threshold (5) → is_infringement=False
        def fake_fuzzy(
            image_hash: str, known_db: set, threshold: int = 5
        ) -> DmcaCheckResult:
            return DmcaCheckResult(is_infringement=False)

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.check_known_infringement_fuzzy",
            fake_fuzzy,
        )
        dispatcher = EmojiModerationDispatcher(
            known_dmca_hashes={PLACEHOLDER_KNOWN_HASH_A}
        )
        outcome = dispatcher.evaluate(b"fake bytes")
        # 한글 주석: miss 의 결과 = APPROVED (OCR clean + DMCA clean)
        assert outcome.decision is ModerationDecision.APPROVED
        assert outcome.dmca_check is not None
        assert outcome.dmca_check.is_infringement is False
        assert any("auto approve" in r for r in outcome.reasons)


class TestDmcaCombinedHash:
    """cycle 151 신규 — dispatcher 의 compute_combined_hash 호출 chain 의무."""

    def test_combined_hash_invoked_in_dispatcher(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """dispatcher 의 evaluate → compute_combined_hash 호출 의무 검증."""

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            lambda image_bytes: _ocr_clean(),
        )

        # 한글 주석: compute_combined_hash 호출 추적 — 인자 + 호출 횟수 검증
        call_log: list = []

        def fake_combined(image_bytes: bytes) -> str:
            call_log.append(image_bytes)
            return PLACEHOLDER_KNOWN_HASH_A

        # 한글 주석: fuzzy match miss — APPROVED 의 path 강제 (DMCA chain 통과)
        def fake_fuzzy(
            image_hash: str, known_db: set, threshold: int = 5
        ) -> DmcaCheckResult:
            assert image_hash == PLACEHOLDER_KNOWN_HASH_A
            return DmcaCheckResult(is_infringement=False)

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.compute_combined_hash",
            fake_combined,
        )
        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.check_known_infringement_fuzzy",
            fake_fuzzy,
        )
        dispatcher = EmojiModerationDispatcher(
            known_dmca_hashes={PLACEHOLDER_KNOWN_HASH_B}
        )
        outcome = dispatcher.evaluate(b"fake png bytes 12345")
        # 한글 주석: compute_combined_hash 호출 1 회 의무 (DMCA stage chain)
        assert len(call_log) == 1
        assert call_log[0] == b"fake png bytes 12345"
        # 한글 주석: OCR clean + DMCA miss → APPROVED
        assert outcome.decision is ModerationDecision.APPROVED


class TestDmcaThresholdOverride:
    """cycle 151 신규 — fuzzy_threshold 0 (exact match only) override 검증."""

    def test_strict_threshold_zero_exact_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """fuzzy_threshold=0 → exact match 만 인정 (distance>0 = miss)."""

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.detect_image",
            lambda image_bytes: _ocr_clean(),
        )
        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.compute_combined_hash",
            lambda image_bytes: "deadbeefcafebabe1234567890abcdef",
        )

        # 한글 주석: fuzzy threshold=0 의 dispatcher 호출 검증 (strict mode)
        captured_threshold: dict = {}

        def fake_fuzzy(
            image_hash: str, known_db: set, threshold: int = 5
        ) -> DmcaCheckResult:
            captured_threshold["t"] = threshold
            # 한글 주석: threshold=0 + exact 일치 (image_hash == candidate) → match
            return DmcaCheckResult(
                is_infringement=True,
                matched_hash=image_hash,
                confidence=1.0,
            )

        monkeypatch.setattr(
            "app.bot.emoji_moderation_dispatcher.check_known_infringement_fuzzy",
            fake_fuzzy,
        )
        # 한글 주석: fuzzy_threshold=0 override (생성자 인자)
        dispatcher = EmojiModerationDispatcher(
            known_dmca_hashes={"deadbeefcafebabe1234567890abcdef"},
            fuzzy_threshold=0,
        )
        outcome = dispatcher.evaluate(b"fake bytes")
        # 한글 주석: threshold 0 의 dispatcher → check 함수 전달 의무
        assert captured_threshold["t"] == 0
        assert outcome.decision is ModerationDecision.DMCA_TAKEDOWN
        assert outcome.dmca_check is not None
        assert outcome.dmca_check.confidence == 1.0
        # 한글 주석: reasons 안 threshold=0 표기 의무
        assert any("threshold=0" in r for r in outcome.reasons)
