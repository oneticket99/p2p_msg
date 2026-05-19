# SPDX-License-Identifier: GPL-3.0-or-later
"""Toonation REST API client skeleton — Phase 5 Item 4 prerequisite (cycle 140).

memory ``project_bot_framework.md`` (A) 투네이션 고객센터 봇 default 배치 의
bot framework 마무리 chain 의 prerequisite — Toonation REST API client 의
실 base + customer_service_bot 의 RAG source 통합 의 토대.

본 module 범위
-------------
- ``ToonationDonationRecord`` frozen dataclass — donation_id + streamer_id +
  donor_name + amount_krw + message + timestamp_ms
- ``ToonationStreamerProfile`` frozen dataclass — streamer_id + nickname +
  platform + follower_count + total_donations_krw
- ``ToonationClient`` class — 6 method skeleton (Phase 5 본격 cycle 의 actual
  binding 의무):
    - ``get_streamer_profile(streamer_id)``
    - ``list_recent_donations(streamer_id, limit)``
    - ``get_donation_detail(donation_id)``
    - ``search_donations_by_donor(donor_name, limit)``
    - ``get_total_donations_today(streamer_id)``
    - ``post_alert_test(streamer_id, message)``
- ``build_default_client()`` — env ``TOONATION_API_KEY`` + ``TOONATION_BASE_URL``
  의 default factory.

본 cycle 의 범위 외 (별개 cycle):
- 실 Toonation REST endpoint 의 binding — 사용자 의 의 production endpoint
  + 인증 절차 확정 의무 (placeholder ``https://toon.at/api/v1`` 의 actual
  endpoint 부재 graceful)
- OAuth2 + refresh token + 의 인증 flow
- webhook + SSE 의 real-time donation push
- rate limit + retry + circuit breaker
- 캐시 (Redis / pgvector 의 의 statistics cache)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Final, List, Optional

log = logging.getLogger(__name__)

# httpx 의 import graceful — 실 binding cycle 의 의무 의존 + 본 skeleton 의 graceful
try:
    import httpx  # noqa: F401
    _HTTPX_AVAILABLE: Final[bool] = True
except ImportError:
    _HTTPX_AVAILABLE = False  # type: ignore[misc]

# placeholder base URL — 사용자 의 production endpoint 확정 의무 (Phase 5 cycle)
_DEFAULT_BASE_URL: Final[str] = "https://toon.at/api/v1"
# default donation list limit — caller 권장 max
_DEFAULT_DONATION_LIMIT: Final[int] = 20
# search donor limit — default
_DEFAULT_SEARCH_LIMIT: Final[int] = 50


@dataclass(frozen=True, slots=True)
class ToonationDonationRecord:
    """단일 도네이션 기록 — Toonation REST 의 의 donation entity.

    Attributes
    ----------
    donation_id : str
        고유 식별자 (Toonation 발급).
    streamer_id : int
        수신 streamer 의 ID.
    donor_name : str
        후원자 nickname (익명 후원 = "익명" 상수).
    amount_krw : int
        후원 금액 (원 단위, 양수 의무).
    message : str
        후원 메시지 텍스트 (빈 문자열 허용).
    timestamp_ms : int
        후원 시각 (Unix epoch milliseconds, 양수 의무).
    """

    donation_id: str
    streamer_id: int
    donor_name: str
    amount_krw: int
    message: str
    timestamp_ms: int

    def __post_init__(self) -> None:
        if not self.donation_id:
            raise ValueError("donation_id 빈 문자열 불가")
        if self.streamer_id <= 0:
            raise ValueError(f"streamer_id 양수 의무 — {self.streamer_id}")
        if not self.donor_name:
            raise ValueError("donor_name 빈 문자열 불가")
        if self.amount_krw < 0:
            raise ValueError(f"amount_krw 음수 불가 — {self.amount_krw}")
        if self.timestamp_ms <= 0:
            raise ValueError(f"timestamp_ms 양수 의무 — {self.timestamp_ms}")


@dataclass(frozen=True, slots=True)
class ToonationStreamerProfile:
    """streamer profile — Toonation REST 의 의 streamer entity.

    Attributes
    ----------
    streamer_id : int
        streamer ID (양수 의무).
    nickname : str
        UI 표시명.
    platform : str
        송출 platform — "youtube" / "twitch" / "chzzk" / "kick" 의 4 종.
    follower_count : int
        구독자 수 (음수 불가).
    total_donations_krw : int
        누적 후원 총액 (원 단위, 음수 불가).
    """

    streamer_id: int
    nickname: str
    platform: str
    follower_count: int
    total_donations_krw: int

    _ALLOWED_PLATFORMS: Final = ("youtube", "twitch", "chzzk", "kick")

    def __post_init__(self) -> None:
        if self.streamer_id <= 0:
            raise ValueError(f"streamer_id 양수 의무 — {self.streamer_id}")
        if not self.nickname:
            raise ValueError("nickname 빈 문자열 불가")
        if self.platform not in self._ALLOWED_PLATFORMS:
            raise ValueError(
                f"platform 의 4 종 (youtube/twitch/chzzk/kick) 의 하나 의무 — {self.platform}"
            )
        if self.follower_count < 0:
            raise ValueError(f"follower_count 음수 불가 — {self.follower_count}")
        if self.total_donations_krw < 0:
            raise ValueError(
                f"total_donations_krw 음수 불가 — {self.total_donations_krw}"
            )


class ToonationClient:
    """Toonation REST API client skeleton.

    6 method skeleton — Phase 5 본격 cycle 의 actual binding 의무. 현 cycle
    의 graceful — httpx 부재 + api_key 부재 + 실 endpoint 미정 모든 method 의
    None / [] / False / 0 의 안전 반환.

    Parameters
    ----------
    api_key : str
        Toonation REST API key (Phase 5 의 의 사용자 의무 확정). 빈 문자열 =
        graceful (모든 호출 의 None / [] / False / 0).
    base_url : str | None
        REST base URL. None = placeholder ``https://toon.at/api/v1``.
    timeout_seconds : float
        HTTP request timeout (default 10.0, 양수 의무).

    Notes
    -----
    cycle 140 = 의 skeleton — 모든 method 의 actual binding 부재 의 graceful
    return. 본 cycle 의 작업 의무 = customer_service_bot 의 dispatch chain 의
    의 RAG source 등록 + 사용자 manual 의 의 base_url + api_key 의 확정 + Phase
    5 본격 cycle 의 의 actual binding.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: Optional[str] = None,
        *,
        timeout_seconds: float = 10.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds 양수 의무 — {timeout_seconds}")
        self._api_key = api_key
        self._base_url = base_url or _DEFAULT_BASE_URL
        self._timeout_seconds = timeout_seconds

    @property
    def api_key(self) -> str:
        """api_key read-only access (평문 로그 차단 의무 — caller 의무)."""

        return self._api_key

    @property
    def base_url(self) -> str:
        """REST base URL read-only access."""

        return self._base_url

    @property
    def timeout_seconds(self) -> float:
        """HTTP timeout read-only access."""

        return self._timeout_seconds

    def _is_operational(self) -> bool:
        """실 호출 가능 여부 — httpx + api_key 의 동시 존재 의무."""

        return _HTTPX_AVAILABLE and bool(self._api_key)

    async def get_streamer_profile(
        self, streamer_id: int
    ) -> Optional[ToonationStreamerProfile]:
        """streamer_id → ToonationStreamerProfile.

        Returns
        -------
        ToonationStreamerProfile | None
            graceful 환경 (httpx 부재 또는 api_key 부재) = None.
            Phase 5 본격 cycle = 실 REST 호출 의 결과 binding.

        Raises
        ------
        ValueError
            streamer_id 양수 아닌 경우.
        """

        if streamer_id <= 0:
            raise ValueError(f"streamer_id 양수 의무 — {streamer_id}")
        if not self._is_operational():
            log.warning(
                "[toonation] graceful — httpx=%s api_key_set=%s "
                "streamer_id=%d → None",
                _HTTPX_AVAILABLE,
                bool(self._api_key),
                streamer_id,
            )
            return None
        # Phase 5 cycle — 실 GET /streamers/{streamer_id} binding 의무
        return None

    async def list_recent_donations(
        self,
        streamer_id: int,
        limit: int = _DEFAULT_DONATION_LIMIT,
    ) -> List[ToonationDonationRecord]:
        """streamer_id 의 최근 도네이션 list — 시각 DESC 정렬.

        Parameters
        ----------
        streamer_id : int
            streamer ID (양수 의무).
        limit : int
            반환 entry 수 상한 (default 20, 양수 의무).

        Returns
        -------
        list[ToonationDonationRecord]
            graceful = []. Phase 5 cycle = 실 GET /streamers/{id}/donations.
        """

        if streamer_id <= 0:
            raise ValueError(f"streamer_id 양수 의무 — {streamer_id}")
        if limit <= 0:
            raise ValueError(f"limit 양수 의무 — {limit}")
        if not self._is_operational():
            log.warning(
                "[toonation] graceful list_recent_donations streamer_id=%d → []",
                streamer_id,
            )
            return []
        # Phase 5 cycle — 실 binding 의무
        return []

    async def get_donation_detail(
        self, donation_id: str
    ) -> Optional[ToonationDonationRecord]:
        """donation_id → ToonationDonationRecord.

        Returns
        -------
        ToonationDonationRecord | None
            graceful = None. Phase 5 cycle = 실 GET /donations/{donation_id}.
        """

        if not donation_id:
            raise ValueError("donation_id 빈 문자열 불가")
        if not self._is_operational():
            log.warning(
                "[toonation] graceful get_donation_detail id=%s → None",
                donation_id,
            )
            return None
        return None

    async def search_donations_by_donor(
        self,
        donor_name: str,
        limit: int = _DEFAULT_SEARCH_LIMIT,
    ) -> List[ToonationDonationRecord]:
        """donor_name substring → 도네이션 list.

        Returns
        -------
        list[ToonationDonationRecord]
            graceful = []. Phase 5 cycle = 실 GET /donations?donor=...
        """

        if not donor_name:
            raise ValueError("donor_name 빈 문자열 불가")
        if limit <= 0:
            raise ValueError(f"limit 양수 의무 — {limit}")
        if not self._is_operational():
            log.warning(
                "[toonation] graceful search_donations_by_donor donor=%s → []",
                donor_name,
            )
            return []
        return []

    async def get_total_donations_today(self, streamer_id: int) -> int:
        """오늘 (KST 자정 기준) 누적 후원 총액 (원 단위).

        Returns
        -------
        int
            graceful = 0. Phase 5 cycle = 실 GET /streamers/{id}/stats/today.
        """

        if streamer_id <= 0:
            raise ValueError(f"streamer_id 양수 의무 — {streamer_id}")
        if not self._is_operational():
            log.warning(
                "[toonation] graceful get_total_donations_today streamer_id=%d → 0",
                streamer_id,
            )
            return 0
        return 0

    async def post_alert_test(self, streamer_id: int, message: str) -> bool:
        """OBS 위젯 테스트 알림 송신 — Phase 5 cycle 의 실 POST.

        Parameters
        ----------
        streamer_id : int
            대상 streamer ID (양수 의무).
        message : str
            테스트 알림 메시지 (빈 문자열 불가).

        Returns
        -------
        bool
            graceful = False. Phase 5 cycle = 실 POST /streamers/{id}/alerts/test.
        """

        if streamer_id <= 0:
            raise ValueError(f"streamer_id 양수 의무 — {streamer_id}")
        if not message:
            raise ValueError("message 빈 문자열 불가")
        if not self._is_operational():
            log.warning(
                "[toonation] graceful post_alert_test streamer_id=%d → False",
                streamer_id,
            )
            return False
        return False


def build_default_client() -> ToonationClient:
    """env ``TOONATION_API_KEY`` + ``TOONATION_BASE_URL`` 의 default factory.

    Returns
    -------
    ToonationClient
        env 부재 시 = api_key 빈 문자열 + base_url placeholder 의 graceful
        client (모든 method 의 None / [] / False / 0).

    Notes
    -----
    실 환경 (Phase 5 cycle) = systemd unit 의 Environment 또는 .env 파일 의
    경유 의 secret injection. 평문 평탄 차단 의무 — 본 함수 의 log 의 api_key
    출력 차단.
    """

    api_key = os.environ.get("TOONATION_API_KEY", "").strip()
    base_url_env = os.environ.get("TOONATION_BASE_URL", "").strip()
    base_url = base_url_env or None
    return ToonationClient(api_key=api_key, base_url=base_url)
