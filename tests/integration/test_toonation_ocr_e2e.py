# SPDX-License-Identifier: GPL-3.0-or-later
"""toonation_client + jailbreak_detector_ocr chain E2E — cycle 169.704 신설."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


class TestOcrDetectImage:
    def test_empty_bytes_none(self) -> None:
        from app.bot.jailbreak_detector_ocr import (
            OcrModerationSignal, detect_image,
        )

        result = detect_image(b"")
        assert result.signal == OcrModerationSignal.NONE
        assert "empty" in result.reasons[0]

    def test_pillow_absent_graceful(self, monkeypatch) -> None:
        # 한글 주석 — Pillow + pytesseract import 부재 → NONE graceful
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name in ("PIL", "pytesseract"):
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        from app.bot.jailbreak_detector_ocr import (
            OcrModerationSignal, detect_image,
        )

        result = detect_image(b"\x89PNG\r\n")
        assert result.signal == OcrModerationSignal.NONE
        assert any("Pillow" in r for r in result.reasons)


class TestOcrModerationResult:
    def test_default_construct(self) -> None:
        from app.bot.jailbreak_detector_ocr import (
            OcrModerationResult, OcrModerationSignal,
        )

        r = OcrModerationResult()
        assert r.signal == OcrModerationSignal.NONE
        assert r.extracted_text == ""
        assert r.matched_patterns == ()


class TestOcrSignalEnum:
    def test_4_values(self) -> None:
        from app.bot.jailbreak_detector_ocr import OcrModerationSignal

        assert OcrModerationSignal.NONE.value == "none"
        assert OcrModerationSignal.SUSPICIOUS.value == "suspicious"
        assert OcrModerationSignal.BLOCKED.value == "blocked"
        assert OcrModerationSignal.JAILBREAK_TEXT.value == "jailbreak_text"


class TestToonationDonationRecord:
    def test_valid_construct(self) -> None:
        from app.bot.toonation_client import ToonationDonationRecord

        r = ToonationDonationRecord(
            donation_id="d1", streamer_id=10, donor_name="익명",
            amount_krw=5000, message="응원합니다", timestamp_ms=1000,
        )
        assert r.donation_id == "d1"

    def test_empty_donation_id_raises(self) -> None:
        from app.bot.toonation_client import ToonationDonationRecord

        with pytest.raises(ValueError, match="donation_id"):
            ToonationDonationRecord(
                donation_id="", streamer_id=10, donor_name="x",
                amount_krw=100, message="", timestamp_ms=1,
            )

    def test_zero_streamer_id_raises(self) -> None:
        from app.bot.toonation_client import ToonationDonationRecord

        with pytest.raises(ValueError, match="streamer_id"):
            ToonationDonationRecord(
                donation_id="d1", streamer_id=0, donor_name="x",
                amount_krw=100, message="", timestamp_ms=1,
            )

    def test_negative_amount_raises(self) -> None:
        from app.bot.toonation_client import ToonationDonationRecord

        with pytest.raises(ValueError, match="amount_krw"):
            ToonationDonationRecord(
                donation_id="d1", streamer_id=10, donor_name="x",
                amount_krw=-1, message="", timestamp_ms=1,
            )

    def test_zero_timestamp_raises(self) -> None:
        from app.bot.toonation_client import ToonationDonationRecord

        with pytest.raises(ValueError, match="timestamp_ms"):
            ToonationDonationRecord(
                donation_id="d1", streamer_id=10, donor_name="x",
                amount_krw=100, message="", timestamp_ms=0,
            )


class TestToonationStreamerProfile:
    def test_valid_construct(self) -> None:
        from app.bot.toonation_client import ToonationStreamerProfile

        p = ToonationStreamerProfile(
            streamer_id=10, nickname="alice", platform="chzzk",
            follower_count=100, total_donations_krw=5000,
        )
        assert p.platform == "chzzk"

    def test_unsupported_platform_raises(self) -> None:
        from app.bot.toonation_client import ToonationStreamerProfile

        with pytest.raises(ValueError, match="platform"):
            ToonationStreamerProfile(
                streamer_id=10, nickname="x", platform="afreeca",
                follower_count=0, total_donations_krw=0,
            )

    def test_empty_nickname_raises(self) -> None:
        from app.bot.toonation_client import ToonationStreamerProfile

        with pytest.raises(ValueError, match="nickname"):
            ToonationStreamerProfile(
                streamer_id=10, nickname="", platform="chzzk",
                follower_count=0, total_donations_krw=0,
            )

    def test_negative_follower_raises(self) -> None:
        from app.bot.toonation_client import ToonationStreamerProfile

        with pytest.raises(ValueError, match="follower_count"):
            ToonationStreamerProfile(
                streamer_id=10, nickname="x", platform="chzzk",
                follower_count=-1, total_donations_krw=0,
            )


class TestToonationClient:
    def test_default_base_url(self) -> None:
        from app.bot.toonation_client import ToonationClient

        c = ToonationClient()
        assert "toon" in c.base_url
        assert c.timeout_seconds == 10.0
        assert c.api_key == ""

    def test_zero_timeout_raises(self) -> None:
        from app.bot.toonation_client import ToonationClient

        with pytest.raises(ValueError, match="timeout_seconds"):
            ToonationClient(timeout_seconds=0)

    def test_not_operational_no_key(self) -> None:
        # 한글 주석 — api_key 빈 → _is_operational False
        from app.bot.toonation_client import ToonationClient

        c = ToonationClient(api_key="")
        assert c._is_operational() is False

    @pytest.mark.asyncio
    async def test_get_streamer_graceful_none(self) -> None:
        # 한글 주석 — graceful 환경 → None
        from app.bot.toonation_client import ToonationClient

        c = ToonationClient(api_key="")
        result = await c.get_streamer_profile(streamer_id=10)
        assert result is None


class TestBuildDefaultClient:
    def test_returns_client(self) -> None:
        from app.bot.toonation_client import (
            ToonationClient, build_default_client,
        )

        c = build_default_client()
        assert isinstance(c, ToonationClient)
