# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.middleware.activity`` 의 단위 테스트.

ActivityTracker throttle + extract_client_ip + middleware integration.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from server.middleware.activity import (
    APP_KEY_ACTIVITY,
    ActivityTracker,
    activity_middleware,
    extract_client_ip,
)


class TestActivityTrackerValidation:
    def test_default_throttle_60_seconds(self) -> None:
        tracker = ActivityTracker()
        assert tracker.throttle_seconds == 60

    def test_custom_throttle_seconds(self) -> None:
        tracker = ActivityTracker(throttle_seconds=300)
        assert tracker.throttle_seconds == 300

    def test_zero_throttle_rejected(self) -> None:
        with pytest.raises(ValueError, match="양수 의무"):
            ActivityTracker(throttle_seconds=0)

    def test_negative_throttle_rejected(self) -> None:
        with pytest.raises(ValueError, match="양수 의무"):
            ActivityTracker(throttle_seconds=-1)


class TestActivityTrackerThrottle:
    def test_first_call_updates(self) -> None:
        tracker = ActivityTracker(throttle_seconds=60)
        assert tracker.should_update(user_id=1, now_seconds=1000.0) is True

    def test_within_throttle_skip(self) -> None:
        tracker = ActivityTracker(throttle_seconds=60)
        tracker.should_update(user_id=1, now_seconds=1000.0)
        # 한글 주석: 30초 후 — throttle 안 → False
        assert tracker.should_update(user_id=1, now_seconds=1030.0) is False

    def test_after_throttle_updates(self) -> None:
        tracker = ActivityTracker(throttle_seconds=60)
        tracker.should_update(user_id=1, now_seconds=1000.0)
        # 한글 주석: 60초 정확 cutoff = 갱신 허용 (>= cutoff)
        assert tracker.should_update(user_id=1, now_seconds=1060.0) is True

    def test_distinct_users_independent(self) -> None:
        tracker = ActivityTracker(throttle_seconds=60)
        assert tracker.should_update(user_id=1, now_seconds=1000.0) is True
        assert tracker.should_update(user_id=2, now_seconds=1000.0) is True
        # 1번 사용자 = throttle 안
        assert tracker.should_update(user_id=1, now_seconds=1010.0) is False

    def test_invalid_user_id_zero_skipped(self) -> None:
        tracker = ActivityTracker(throttle_seconds=60)
        assert tracker.should_update(user_id=0) is False
        assert tracker.size() == 0

    def test_invalid_user_id_negative_skipped(self) -> None:
        tracker = ActivityTracker(throttle_seconds=60)
        assert tracker.should_update(user_id=-5) is False


class TestActivityTrackerPrune:
    def test_prune_stale_removes_old(self) -> None:
        tracker = ActivityTracker(throttle_seconds=60)
        tracker.should_update(user_id=1, now_seconds=1000.0)
        tracker.should_update(user_id=2, now_seconds=2000.0)
        tracker.should_update(user_id=3, now_seconds=3000.0)
        # 한글 주석: cutoff 2500 → user 1+2 evict, user 3 유지
        removed = tracker.prune_stale(cutoff_seconds=2500.0)
        assert removed == 2
        assert tracker.size() == 1

    def test_prune_empty_no_removal(self) -> None:
        tracker = ActivityTracker()
        removed = tracker.prune_stale(cutoff_seconds=9999.0)
        assert removed == 0


class TestExtractClientIP:
    def _request(self, *, xff: str = "", remote: str = "") -> Any:
        # 한글 주석: minimal aiohttp.Request mock
        req = MagicMock()
        req.headers = {"X-Forwarded-For": xff} if xff else {}
        # headers.get fallback
        req.headers = {"X-Forwarded-For": xff}
        req.remote = remote
        # MagicMock 의 dict-like 의 headers.get 의 정합
        req.headers = MagicMock()
        req.headers.get = lambda key, default="": {"X-Forwarded-For": xff}.get(
            key, default
        )
        return req

    def test_xff_single_ip(self) -> None:
        req = self._request(xff="1.2.3.4", remote="10.0.0.1")
        assert extract_client_ip(req) == "1.2.3.4"

    def test_xff_multi_proxy_chain_picks_first(self) -> None:
        req = self._request(xff="203.0.113.5, 172.16.0.1, 10.0.0.1")
        assert extract_client_ip(req) == "203.0.113.5"

    def test_xff_empty_fallback_to_remote(self) -> None:
        req = self._request(xff="", remote="192.0.2.10")
        assert extract_client_ip(req) == "192.0.2.10"

    def test_both_empty_returns_empty(self) -> None:
        req = self._request(xff="", remote="")
        assert extract_client_ip(req) == ""

    def test_xff_with_spaces_stripped(self) -> None:
        req = self._request(xff="   203.0.113.5  ,   10.0.0.1  ")
        assert extract_client_ip(req) == "203.0.113.5"


class TestActivityMiddleware:
    @pytest.mark.asyncio
    async def test_no_user_id_skips_update(self) -> None:
        tracker = ActivityTracker(throttle_seconds=60)

        async def handler(req: Any) -> Any:
            return MagicMock(status=200)

        req = MagicMock()
        req.app = MagicMock()
        req.app.get = lambda k: tracker if k == APP_KEY_ACTIVITY else None
        req.get = lambda k, *args: None
        req.headers = MagicMock()
        req.headers.get = lambda k, default="": default
        req.path = "/api/test"
        req.remote = "10.0.0.1"

        await activity_middleware(req, handler)
        # 한글 주석: user_id 부재 → tracker 갱신 부재
        assert tracker.size() == 0

    @pytest.mark.asyncio
    async def test_valid_user_id_updates_once(self) -> None:
        tracker = ActivityTracker(throttle_seconds=60)

        async def handler(req: Any) -> Any:
            return MagicMock(status=200)

        req = MagicMock()
        req.app = MagicMock()
        req.app.get = lambda k: tracker if k == APP_KEY_ACTIVITY else None
        req.get = lambda k, *args: 42 if k == "user_id" else None
        req.headers = MagicMock()
        req.headers.get = lambda k, default="": "1.2.3.4" if k == "X-Forwarded-For" else default
        req.path = "/api/test"
        req.remote = "10.0.0.1"

        await activity_middleware(req, handler)
        assert tracker.size() == 1

    @pytest.mark.asyncio
    async def test_no_tracker_skips_gracefully(self) -> None:
        async def handler(req: Any) -> Any:
            return MagicMock(status=200)

        req = MagicMock()
        req.app = MagicMock()
        req.app.get = lambda k: None
        req.get = lambda k, *args: 42 if k == "user_id" else None
        req.headers = MagicMock()
        req.headers.get = lambda k, default="": default
        req.path = "/api/test"
        req.remote = ""

        # 한글 주석: tracker 부재 — raise 부재, response 정상 반환
        response = await activity_middleware(req, handler)
        assert response is not None
