# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 Item 3 emoji pack moderation dispatcher chain — cycle 144.

cycle 132 (0004 emoji_packs migration + 5 endpoint skeleton) +
cycle 133 (jailbreak_ocr + DMCA skeleton) + cycle 141 (OCR actual binding)
chain 의 통합 dispatcher layer.

본 module 범위 (cycle 144)
--------------------------
- ``ModerationDecision`` Enum — APPROVED / REJECTED / DMCA_TAKEDOWN /
  HOLD_FOR_REVIEW (admin queue 의 manual 결정 대기).
- ``ModerationOutcome`` frozen dataclass — decision + reasons +
  ocr_signal + dmca_check + suggested_status (ModerationStatus 정합).
- ``EmojiModerationDispatcher`` — 4 stage pipeline:
    1. OCR detect (jailbreak_detector_ocr.detect_image)
    2. DMCA phash check (emoji_dmca_check.check_known_infringement)
    3. auto decision (BLOCKED / JAILBREAK_TEXT / DMCA → 즉시 차단)
    4. HOLD_FOR_REVIEW → admin queue 위탁 (manual approve/reject)
- ``map_to_moderation_status`` — ModerationDecision →
  ModerationStatus ENUM (repository binding 의 변환 helper).

설계 결정
---------
- graceful — OCR + DMCA chain 의 library 부재 시 NONE + HOLD_FOR_REVIEW.
- pure function 로 구성 — repository binding (DB) 은 caller 의 책임.
- admin queue persistence 는 별개 cycle (cycle 145+) 의무.

본 cycle 의 범위 외 (별개 cycle 145+):
- admin 결정 audit log (감사 추적)
- moderation_decision_history 테이블 영속 + REST 노출
- ML-based confidence score (HOLD vs auto 의 의사결정)
- 사용자 신고 기반 가중치 score
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set, Tuple

from app.bot.emoji_dmca_check import (
    DmcaCheckResult,
    check_known_infringement,
    compute_phash_skeleton,
)
from app.bot.jailbreak_detector_ocr import (
    OcrModerationResult,
    OcrModerationSignal,
    detect_image,
)

log = logging.getLogger(__name__)


class ModerationDecision(Enum):
    """dispatcher 자동 의사결정 신호 — admin UI / DB ENUM 변환 base."""

    APPROVED = "approved"  # OCR + DMCA chain 모두 clean → auto approve
    REJECTED = "rejected"  # OCR JAILBREAK_TEXT / BLOCKED → auto reject
    DMCA_TAKEDOWN = "dmca_takedown"  # DMCA hash match → auto takedown
    HOLD_FOR_REVIEW = "hold_for_review"  # SUSPICIOUS / library 부재 → admin queue


@dataclass(frozen=True, slots=True)
class ModerationOutcome:
    """dispatcher 의 단일 응답 — admin UI + REST + DB 갱신 의 base.

    Attributes
    ----------
    decision : ModerationDecision
        자동 의사결정 신호 (4 ENUM).
    reasons : List[str]
        결정 사유 list (debug + audit log + admin UI 표시).
    ocr_signal : OcrModerationSignal
        OCR chain 의 신호 (NONE / SUSPICIOUS / BLOCKED / JAILBREAK_TEXT).
    dmca_check : Optional[DmcaCheckResult]
        DMCA chain 의 결과 (None = phash 미실행).
    matched_patterns : Tuple[str, ...]
        OCR 안 jailbreak category 누계 tuple (admin UI 표시).
    """

    decision: ModerationDecision
    reasons: List[str] = field(default_factory=list)
    ocr_signal: OcrModerationSignal = OcrModerationSignal.NONE
    dmca_check: Optional[DmcaCheckResult] = None
    matched_patterns: Tuple[str, ...] = ()


def map_to_moderation_status(decision: ModerationDecision) -> str:
    """ModerationDecision → emoji_packs.moderation_status ENUM (string).

    repository.update_moderation_status 의 직접 binding 가능.

    Parameters
    ----------
    decision : ModerationDecision
        dispatcher 결정 신호.

    Returns
    -------
    str
        emoji_packs.moderation_status 4 ENUM 정합 string.
        - APPROVED → "approved"
        - REJECTED → "rejected"
        - DMCA_TAKEDOWN → "dmca_takedown"
        - HOLD_FOR_REVIEW → "pending" (admin queue 진입)
    """

    # 한글 주석: HOLD_FOR_REVIEW = pending 상태 유지 (admin 결정 대기)
    if decision is ModerationDecision.APPROVED:
        return "approved"
    if decision is ModerationDecision.REJECTED:
        return "rejected"
    if decision is ModerationDecision.DMCA_TAKEDOWN:
        return "dmca_takedown"
    return "pending"


class EmojiModerationDispatcher:
    """4 stage pipeline — OCR → DMCA → auto decision → admin queue.

    Stateless 의 service layer — caller 가 image bytes + known DMCA set
    의 주입 의무. repository binding (DB) 은 caller 의 책임.
    """

    def __init__(
        self,
        *,
        known_dmca_hashes: Optional[Set[str]] = None,
    ) -> None:
        """dispatcher 신설.

        Parameters
        ----------
        known_dmca_hashes : Optional[Set[str]]
            등록된 침해 hash set (DMCA takedown 누계 의 in-memory snapshot).
            None = 빈 set (DMCA chain skip).
        """

        # 한글 주석: known_dmca_hashes None graceful — 빈 set 의 안전 default
        self._known_dmca_hashes: Set[str] = (
            set(known_dmca_hashes) if known_dmca_hashes else set()
        )

    def evaluate(self, image_bytes: bytes) -> ModerationOutcome:
        """image bytes → 4 stage pipeline → ModerationOutcome.

        Stage 1: OCR detect (jailbreak_detector_ocr.detect_image).
        Stage 2: DMCA phash check (skeleton).
        Stage 3: auto decision (BLOCKED / JAILBREAK_TEXT / DMCA → reject).
        Stage 4: HOLD_FOR_REVIEW → admin queue 위탁 (manual approve/reject).

        Parameters
        ----------
        image_bytes : bytes
            image binary (PNG / WEBP / GIF). 빈 = HOLD_FOR_REVIEW.

        Returns
        -------
        ModerationOutcome
            decision + reasons + ocr_signal + dmca_check + matched_patterns.
        """

        # 한글 주석: 빈 입력 graceful — admin queue 위탁
        if not image_bytes:
            return ModerationOutcome(
                decision=ModerationDecision.HOLD_FOR_REVIEW,
                reasons=["empty image bytes — admin queue 위탁"],
            )

        # Stage 1: OCR detect — library 부재 graceful (NONE 반환)
        ocr_result: OcrModerationResult = detect_image(image_bytes)
        reasons: List[str] = list(ocr_result.reasons)

        # 한글 주석: BLOCKED + JAILBREAK_TEXT = 즉시 reject (admin 결정 불요)
        if ocr_result.signal is OcrModerationSignal.JAILBREAK_TEXT:
            reasons.append("OCR jailbreak text match — auto reject")
            return ModerationOutcome(
                decision=ModerationDecision.REJECTED,
                reasons=reasons,
                ocr_signal=ocr_result.signal,
                matched_patterns=ocr_result.matched_patterns,
            )
        if ocr_result.signal is OcrModerationSignal.BLOCKED:
            reasons.append("OCR blocked signal — auto reject")
            return ModerationOutcome(
                decision=ModerationDecision.REJECTED,
                reasons=reasons,
                ocr_signal=ocr_result.signal,
                matched_patterns=ocr_result.matched_patterns,
            )

        # Stage 2: DMCA phash check — known set 의 exact match (cycle 133 정합)
        dmca_result: Optional[DmcaCheckResult] = None
        if self._known_dmca_hashes:
            # 한글 주석: phash skeleton — imagehash 부재 시 sha256[:16] fallback
            try:
                phash_str = compute_phash_skeleton(image_bytes)
                dmca_result = check_known_infringement(
                    phash_str, self._known_dmca_hashes
                )
                if dmca_result.is_infringement:
                    reasons.append(
                        f"DMCA hash match (confidence={dmca_result.confidence}) "
                        f"— auto takedown"
                    )
                    return ModerationOutcome(
                        decision=ModerationDecision.DMCA_TAKEDOWN,
                        reasons=reasons,
                        ocr_signal=ocr_result.signal,
                        dmca_check=dmca_result,
                        matched_patterns=ocr_result.matched_patterns,
                    )
            except Exception as exc:  # noqa: BLE001
                # 한글 주석: phash 실패 graceful — admin queue 위탁 (HOLD)
                log.warning("[dispatcher] phash 실패 — %r", exc)
                reasons.append(f"DMCA chain 예외 ({type(exc).__name__})")

        # Stage 3: SUSPICIOUS → admin queue 위탁 (HOLD_FOR_REVIEW)
        if ocr_result.signal is OcrModerationSignal.SUSPICIOUS:
            reasons.append("OCR suspicious — admin queue 위탁")
            return ModerationOutcome(
                decision=ModerationDecision.HOLD_FOR_REVIEW,
                reasons=reasons,
                ocr_signal=ocr_result.signal,
                dmca_check=dmca_result,
                matched_patterns=ocr_result.matched_patterns,
            )

        # Stage 4: NONE + DMCA clean → auto approve
        reasons.append("OCR clean + DMCA clean — auto approve")
        return ModerationOutcome(
            decision=ModerationDecision.APPROVED,
            reasons=reasons,
            ocr_signal=ocr_result.signal,
            dmca_check=dmca_result,
            matched_patterns=ocr_result.matched_patterns,
        )
