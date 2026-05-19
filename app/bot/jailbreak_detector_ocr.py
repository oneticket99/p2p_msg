# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 Item 3 emoji pack OCR moderation chain — cycle 132 skeleton.

memory `project_emoji_pack_share.md` + `project_bot_framework.md` 정합. emoji
sticker / custom emoji 의 image 안 의 jailbreak prompt + 명시 텍스트 detection
의 chain layer.

본 module 범위 (cycle 132 skeleton)
----------------------------------
- ``OcrModerationSignal`` Enum (NONE / SUSPICIOUS / BLOCKED) — 기존
  `jailbreak_detector.JailbreakSignal` 정합.
- ``OcrModerationResult`` frozen dataclass — signal + extracted_text + reasons.
- ``detect_image(image_bytes)`` 시그너처 정의 + skeleton return (NONE 신호).

본 cycle 의 범위 외 (별개 cycle 141~150 본격 binding):
- Tesseract OCR binding (pytesseract + 한국어 traineddata)
- EasyOCR binding (대안 + ML 기반 + 다국어)
- 추출 텍스트 기반 기존 `jailbreak_detector.detect` 의 합쳐진 chain
- image preprocessing (resize + binarize + noise reduction)
- DMCA 신고 본문 텍스트 기반 reverse-image-search hint
- adversarial steganography (LSB + EXIF 안 의 숨겨진 instruction)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class OcrModerationSignal(Enum):
    """OCR moderation 결과 신호 — 기존 JailbreakSignal 정합."""

    NONE = "none"  # OCR 추출 텍스트 부재 또는 normal
    SUSPICIOUS = "suspicious"  # 약 match — log + 진행
    BLOCKED = "blocked"  # 강 match — 즉시 차단


@dataclass(frozen=True, slots=True)
class OcrModerationResult:
    """OCR moderation 결과 — signal + 추출 텍스트 + reasons.

    Attributes
    ----------
    signal : OcrModerationSignal
        최종 신호.
    extracted_text : str
        OCR 추출 본문 (snippet — 첫 512자 cap).
    reasons : List[str]
        match 한 카테고리 + 사유 list.
    """

    signal: OcrModerationSignal = OcrModerationSignal.NONE
    extracted_text: str = ""
    reasons: List[str] = field(default_factory=list)


def detect_image(image_bytes: bytes) -> OcrModerationResult:
    """image bytes → OCR moderation 결과 (skeleton).

    Phase 5 본격 cycle 141~150 의 실 binding:
    1. PIL.Image.open(BytesIO(image_bytes)) — image load.
    2. preprocessing (RGB → grayscale + 1.5x upscale + binarize).
    3. pytesseract.image_to_string(img, lang='kor+eng') — OCR 추출.
    4. jailbreak_detector.detect(extracted_text) 의 chain — signal 매핑.
    5. EXIF 안 의 metadata scan (별개 cycle).

    Parameters
    ----------
    image_bytes : bytes
        image binary (PNG / WEBP / GIF).

    Returns
    -------
    OcrModerationResult
        skeleton = NONE 신호 + 빈 추출 텍스트.
    """

    # 한글 주석: skeleton — 본격 cycle 진입 시 pytesseract / easyocr binding 의무
    if not image_bytes:
        return OcrModerationResult(
            signal=OcrModerationSignal.NONE,
            extracted_text="",
            reasons=["empty image bytes"],
        )
    # 한글 주석: image_bytes 의 size 만 기록 — 본격 cycle 진입 시 OCR 호출 placeholder
    return OcrModerationResult(
        signal=OcrModerationSignal.NONE,
        extracted_text="",
        reasons=[f"skeleton placeholder (size={len(image_bytes)} bytes)"],
    )
