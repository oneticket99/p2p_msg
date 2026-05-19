# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 Item 3 emoji pack OCR moderation chain — cycle 133 (actual binding).

memory `project_emoji_pack_share.md` + `project_bot_framework.md` 정합. emoji
sticker / custom emoji 의 image 안 의 jailbreak prompt + 명시 텍스트 detection
의 chain layer.

본 module 범위 (cycle 133 actual binding skeleton)
-------------------------------------------------
- ``OcrModerationSignal`` Enum (NONE / SUSPICIOUS / BLOCKED / JAILBREAK_TEXT)
  — 기존 `jailbreak_detector.JailbreakSignal` 정합 + JAILBREAK_TEXT 추가
  (cycle 133 — OCR 추출 텍스트 안 jailbreak 패턴 match 의 별개 신호).
- ``OcrModerationResult`` frozen dataclass — signal + extracted_text +
  matched_patterns + reasons (backward compat).
- ``detect_image(image_bytes)`` — Pillow + pytesseract graceful binding +
  jailbreak detector chain.

본 cycle 의 범위 외 (별개 cycle 141~150 본격 binding):
- 한국어 traineddata 의 정밀 tune (kor.traineddata + kor_vert.traineddata)
- EasyOCR binding (대안 + ML 기반 + 다국어)
- image preprocessing (resize + binarize + noise reduction)
- DMCA 신고 본문 텍스트 기반 reverse-image-search hint
- adversarial steganography (LSB + EXIF 안 의 숨겨진 instruction)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

# 한글 주석: jailbreak 17 패턴 detector 의 chain 의무 — 본 module 의 핵심 dependency
from app.bot.jailbreak_detector import (
    JailbreakSignal,
    detect,
    summarize_categories,
)

log = logging.getLogger(__name__)


class OcrModerationSignal(Enum):
    """OCR moderation 결과 신호 — 기존 JailbreakSignal 정합 + JAILBREAK_TEXT 추가."""

    NONE = "none"  # OCR 추출 텍스트 부재 또는 normal
    SUSPICIOUS = "suspicious"  # 약 match — log + 진행
    BLOCKED = "blocked"  # 강 match — 즉시 차단
    JAILBREAK_TEXT = "jailbreak_text"  # OCR 안 jailbreak 패턴 match (cycle 133 신설)


@dataclass(frozen=True, slots=True)
class OcrModerationResult:
    """OCR moderation 결과 — signal + 추출 텍스트 + matched_patterns + reasons.

    Attributes
    ----------
    signal : OcrModerationSignal
        최종 신호.
    extracted_text : str
        OCR 추출 본문 (snippet — 첫 500자 cap).
    matched_patterns : Tuple[str, ...]
        match 한 jailbreak category list (cycle 133 신설 — frozen tuple).
    reasons : List[str]
        match 한 카테고리 + 사유 list (cycle 132 backward compat).
    """

    signal: OcrModerationSignal = OcrModerationSignal.NONE
    extracted_text: str = ""
    matched_patterns: Tuple[str, ...] = ()
    reasons: List[str] = field(default_factory=list)


def detect_image(image_bytes: bytes) -> OcrModerationResult:
    """image bytes → OCR moderation 결과 (cycle 133 actual binding).

    Pillow + pytesseract OCR + jailbreak detector 17 패턴 chain. graceful —
    library 부재 시 NONE 반환 + log warning. binary 부재 시 NONE 즉시 반환.

    Parameters
    ----------
    image_bytes : bytes
        image binary (PNG / WEBP / GIF).

    Returns
    -------
    OcrModerationResult
        signal + extracted_text(500자 cap) + matched_patterns(category tuple).
    """

    # 한글 주석: 빈 입력 short circuit — log 의 noise 회피
    if not image_bytes:
        return OcrModerationResult(
            signal=OcrModerationSignal.NONE,
            extracted_text="",
            matched_patterns=(),
            reasons=["empty image bytes"],
        )

    # 한글 주석: Pillow + pytesseract graceful import — 부재 시 NONE 반환
    try:
        from PIL import Image  # type: ignore[import-not-found]
        import pytesseract  # type: ignore[import-not-found]
        import io
    except ImportError:
        log.warning("[ocr] Pillow + pytesseract 부재 — graceful NONE 반환")
        return OcrModerationResult(
            signal=OcrModerationSignal.NONE,
            extracted_text="",
            matched_patterns=(),
            reasons=["Pillow + pytesseract 부재 (graceful)"],
        )

    # 한글 주석: OCR 추출 + jailbreak 17 패턴 chain — 예외 시 graceful NONE
    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang="kor+eng")
        snippet = text[:500]
        # 한글 주석: jailbreak detector 17 패턴 chain — score 합산 후 category 추출
        jb_result = detect(text)
        if jb_result.signal != JailbreakSignal.NONE:
            categories = summarize_categories(jb_result)
            return OcrModerationResult(
                signal=OcrModerationSignal.JAILBREAK_TEXT,
                extracted_text=snippet,
                matched_patterns=tuple(categories),
                reasons=[f"jailbreak {jb_result.signal.value} score={jb_result.score}"],
            )
        return OcrModerationResult(
            signal=OcrModerationSignal.NONE,
            extracted_text=snippet,
            matched_patterns=(),
            reasons=["OCR 추출 + jailbreak match 부재"],
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("[ocr] OCR 실패 — %r", exc)
        return OcrModerationResult(
            signal=OcrModerationSignal.NONE,
            extracted_text="",
            matched_patterns=(),
            reasons=[f"OCR 예외 ({type(exc).__name__})"],
        )
