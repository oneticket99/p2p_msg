# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.toonation_client`` 단위 테스트 — cycle 140.

8 test — ToonationClient graceful (httpx 부재 + api_key 부재) + env factory +
dataclass slots + validation 검증.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest

from app.bot.toonation_client import (
    ToonationClient,
    ToonationDonationRecord,
    ToonationStreamerProfile,
    build_default_client,
)


class TestToonationClientGraceful:
    """``ToonationClient`` graceful 검증 — httpx 부재 또는 api_key 부재 시."""

    @pytest.mark.asyncio
    async def test_get_streamer_profile_graceful(self) -> None:
        # 한글 주석 — api_key 빈 문자열 의 graceful None 반환
        client = ToonationClient(api_key="")
        result = await client.get_streamer_profile(streamer_id=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_recent_donations_graceful(self) -> None:
        client = ToonationClient(api_key="")
        result = await client.list_recent_donations(streamer_id=1, limit=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_donation_detail_graceful(self) -> None:
        client = ToonationClient(api_key="")
        result = await client.get_donation_detail(donation_id="d-001")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_donations_by_donor_graceful(self) -> None:
        client = ToonationClient(api_key="")
        result = await client.search_donations_by_donor(donor_name="alice")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_total_donations_today_graceful(self) -> None:
        client = ToonationClient(api_key="")
        result = await client.get_total_donations_today(streamer_id=1)
        assert result == 0

    @pytest.mark.asyncio
    async def test_post_alert_test_graceful(self) -> None:
        client = ToonationClient(api_key="")
        result = await client.post_alert_test(streamer_id=1, message="테스트")
        assert result is False

    @pytest.mark.asyncio
    async def test_invalid_streamer_id_rejected(self) -> None:
        # 한글 주석 — streamer_id 양수 의무 violation 검증
        client = ToonationClient(api_key="")
        with pytest.raises(ValueError, match="streamer_id"):
            await client.get_streamer_profile(streamer_id=0)
        with pytest.raises(ValueError, match="streamer_id"):
            await client.list_recent_donations(streamer_id=-1)

    @pytest.mark.asyncio
    async def test_invalid_limit_rejected(self) -> None:
        client = ToonationClient(api_key="")
        with pytest.raises(ValueError, match="limit"):
            await client.list_recent_donations(streamer_id=1, limit=0)
        with pytest.raises(ValueError, match="limit"):
            await client.search_donations_by_donor(donor_name="x", limit=-5)

    @pytest.mark.asyncio
    async def test_empty_donation_id_rejected(self) -> None:
        client = ToonationClient(api_key="")
        with pytest.raises(ValueError, match="donation_id"):
            await client.get_donation_detail(donation_id="")

    @pytest.mark.asyncio
    async def test_empty_donor_name_rejected(self) -> None:
        client = ToonationClient(api_key="")
        with pytest.raises(ValueError, match="donor_name"):
            await client.search_donations_by_donor(donor_name="")

    @pytest.mark.asyncio
    async def test_empty_alert_message_rejected(self) -> None:
        client = ToonationClient(api_key="")
        with pytest.raises(ValueError, match="message"):
            await client.post_alert_test(streamer_id=1, message="")


class TestEnvFactory:
    """``build_default_client`` env 기반 factory 검증."""

    def test_env_api_key_picked(self) -> None:
        # 한글 주석 — TOONATION_API_KEY env 의 의 client api_key 의 binding
        with mock.patch.dict(
            os.environ,
            {"TOONATION_API_KEY": "test-key-abc", "TOONATION_BASE_URL": ""},
            clear=False,
        ):
            client = build_default_client()
            assert client.api_key == "test-key-abc"

    def test_env_base_url_picked(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "TOONATION_API_KEY": "k",
                "TOONATION_BASE_URL": "https://custom.example.com/v2",
            },
            clear=False,
        ):
            client = build_default_client()
            assert client.base_url == "https://custom.example.com/v2"

    def test_env_absent_graceful(self) -> None:
        # 한글 주석 — env 부재 시 빈 api_key + placeholder base_url
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in ("TOONATION_API_KEY", "TOONATION_BASE_URL")
        }
        with mock.patch.dict(os.environ, env_clean, clear=True):
            client = build_default_client()
            assert client.api_key == ""
            assert "toon" in client.base_url.lower()

    def test_env_whitespace_stripped(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"TOONATION_API_KEY": "  trimmed  ", "TOONATION_BASE_URL": ""},
            clear=False,
        ):
            client = build_default_client()
            assert client.api_key == "trimmed"


class TestDataclassSlots:
    """``ToonationDonationRecord`` + ``ToonationStreamerProfile`` slots + frozen."""

    def test_donation_record_construction(self) -> None:
        rec = ToonationDonationRecord(
            donation_id="d-001",
            streamer_id=1,
            donor_name="alice",
            amount_krw=5000,
            message="화이팅",
            timestamp_ms=1_700_000_000_000,
        )
        assert rec.donation_id == "d-001"
        assert rec.amount_krw == 5000

    def test_donation_record_frozen(self) -> None:
        rec = ToonationDonationRecord(
            donation_id="d-001",
            streamer_id=1,
            donor_name="alice",
            amount_krw=5000,
            message="",
            timestamp_ms=1_700_000_000_000,
        )
        with pytest.raises((AttributeError, Exception)):
            rec.amount_krw = 9999  # type: ignore[misc]

    def test_donation_record_slots(self) -> None:
        # 한글 주석 — slots=True 의 __dict__ 부재 검증
        rec = ToonationDonationRecord(
            donation_id="d-001",
            streamer_id=1,
            donor_name="alice",
            amount_krw=5000,
            message="",
            timestamp_ms=1_700_000_000_000,
        )
        assert not hasattr(rec, "__dict__")

    def test_donation_record_validation_empty_id(self) -> None:
        with pytest.raises(ValueError, match="donation_id"):
            ToonationDonationRecord(
                donation_id="",
                streamer_id=1,
                donor_name="alice",
                amount_krw=5000,
                message="",
                timestamp_ms=1_700_000_000_000,
            )

    def test_donation_record_negative_amount(self) -> None:
        with pytest.raises(ValueError, match="amount_krw"):
            ToonationDonationRecord(
                donation_id="d-001",
                streamer_id=1,
                donor_name="alice",
                amount_krw=-1,
                message="",
                timestamp_ms=1_700_000_000_000,
            )

    def test_streamer_profile_construction(self) -> None:
        prof = ToonationStreamerProfile(
            streamer_id=1,
            nickname="streamer-a",
            platform="youtube",
            follower_count=1234,
            total_donations_krw=99_999,
        )
        assert prof.platform == "youtube"
        assert prof.follower_count == 1234

    def test_streamer_profile_invalid_platform(self) -> None:
        with pytest.raises(ValueError, match="platform"):
            ToonationStreamerProfile(
                streamer_id=1,
                nickname="x",
                platform="afreeca",
                follower_count=0,
                total_donations_krw=0,
            )

    def test_streamer_profile_slots(self) -> None:
        prof = ToonationStreamerProfile(
            streamer_id=1,
            nickname="x",
            platform="twitch",
            follower_count=0,
            total_donations_krw=0,
        )
        assert not hasattr(prof, "__dict__")


class TestApiKeyAbsentGraceful:
    """empty api_key 의 의 모든 method 의 graceful return."""

    def test_default_construction_no_key(self) -> None:
        # 한글 주석 — default 생성 시 api_key 빈 문자열 + placeholder base_url
        client = ToonationClient()
        assert client.api_key == ""
        assert client.base_url
        assert client.timeout_seconds == 10.0

    def test_invalid_timeout_rejected(self) -> None:
        with pytest.raises(ValueError, match="timeout_seconds"):
            ToonationClient(api_key="k", timeout_seconds=0)
        with pytest.raises(ValueError, match="timeout_seconds"):
            ToonationClient(api_key="k", timeout_seconds=-1.5)

    def test_custom_base_url(self) -> None:
        client = ToonationClient(
            api_key="k", base_url="https://staging.toon.at/api/v2"
        )
        assert client.base_url == "https://staging.toon.at/api/v2"

    @pytest.mark.asyncio
    async def test_all_methods_graceful_chain(self) -> None:
        # 한글 주석 — empty api_key 의 6 method 모두 graceful chain
        client = ToonationClient(api_key="")
        assert await client.get_streamer_profile(streamer_id=1) is None
        assert await client.list_recent_donations(streamer_id=1) == []
        assert await client.get_donation_detail(donation_id="d-001") is None
        assert await client.search_donations_by_donor(donor_name="x") == []
        assert await client.get_total_donations_today(streamer_id=1) == 0
        assert (
            await client.post_alert_test(streamer_id=1, message="t") is False
        )
