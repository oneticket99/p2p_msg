# SPDX-License-Identifier: GPL-3.0-or-later
"""YouTube Live Chat API v3 chat client — 사이클 146 skeleton.

memory `project_bot_framework.md` (B) 방송 도우미 봇 별개 API 정합 —
YouTube Data API v3 의 ``liveChatMessages.list`` endpoint 의 polling.

Protocol 의 핵심
----------------
- OAuth2 Bearer access_token + ``liveChatId`` (LiveBroadcast resource 의
  ``snippet.liveChatId``) 의 의 ``GET https://www.googleapis.com/youtube/v3/
  liveChat/messages`` polling (3~5초 간격, ``pollingIntervalMillis`` server
  hint 준수).
- response 의 ``items[]`` 안 의 ``snippet.displayMessage`` + ``authorDetails
  .displayName`` + ``snippet.publishedAt`` 추출.
- 본 cycle = httpx 부재 graceful False + skeleton receive_loop.

본 cycle 의 범위 외 (별개 cycle)
-------------------------------
- 실 OAuth2 refresh_token rotation.
- nextPageToken / pollingIntervalMillis 의 의 backpressure 처리.
- Super Chat / Super Sticker / membership event 의 의 별개 dispatch.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional

log = logging.getLogger(__name__)

# 한글 주석 — httpx optional import (graceful False 의무)
try:
    import httpx  # type: ignore[import-not-found]

    _HTTPX_AVAILABLE = True
except ImportError:  # pragma: no cover
    _HTTPX_AVAILABLE = False


# YouTube Data API v3 base endpoint
_API_BASE = "https://www.googleapis.com/youtube/v3"
# default polling interval (server hint 부재 시 fallback) — 4초
_DEFAULT_POLL_INTERVAL_SECONDS = 4.0
# max poll interval 한도 — server hint 의 의 상한 cap
_MAX_POLL_INTERVAL_SECONDS = 30.0
# access_token 최대 길이 — RFC 6749 Bearer token 안전 상한
_MAX_TOKEN_LENGTH = 4096


@dataclass(slots=True)
class YouTubeChatConfig:
    """YouTube Live Chat client 의 연결 설정.

    Attributes
    ----------
    access_token : str
        Google OAuth2 access_token (``youtube.readonly`` scope 의무).
    live_chat_id : str
        대상 방송 의 ``liveChatId``.
    poll_interval_seconds : float
        polling 간격 (server hint 부재 시 fallback).
    """

    access_token: str
    live_chat_id: str
    poll_interval_seconds: float = _DEFAULT_POLL_INTERVAL_SECONDS

    def __post_init__(self) -> None:
        # 한글 주석 — token / chat_id empty + 상한 검증
        if not self.access_token:
            raise ValueError("access_token 빈 문자열 불가")
        if len(self.access_token) > _MAX_TOKEN_LENGTH:
            raise ValueError(
                f"access_token 길이 초과 — {_MAX_TOKEN_LENGTH} 한도"
            )
        if not self.live_chat_id:
            raise ValueError("live_chat_id 빈 문자열 불가")
        if not (0 < self.poll_interval_seconds <= _MAX_POLL_INTERVAL_SECONDS):
            raise ValueError(
                f"poll_interval_seconds 범위 외 — {self.poll_interval_seconds}"
                f" (0~{_MAX_POLL_INTERVAL_SECONDS})"
            )


class YouTubeChatClient:
    """YouTube Live Chat API v3 polling chat client skeleton.

    한글 주석 — 본 cycle 146 = httpx graceful False + skeleton receive_loop.
    실 polling chain + Super Chat dispatch = 별개 cycle.

    Parameters
    ----------
    config : YouTubeChatConfig
        client 설정.
    on_message : Callable[[ChatMessage], Awaitable[None]] | None
        chat message 수신 callback (None = 무동작).
    """

    PLATFORM = "youtube"

    def __init__(
        self,
        config: YouTubeChatConfig,
        on_message: Optional[Callable[[object], Awaitable[None]]] = None,
    ) -> None:
        self._config = config
        self._on_message = on_message
        self._http: Optional[object] = None
        self._connected = False
        self._next_page_token: Optional[str] = None

    @property
    def config(self) -> YouTubeChatConfig:
        return self._config

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """cycle 169.422 — YouTube Data API v3 actual httpx.AsyncClient session 활성.

        Returns
        -------
        bool
            연결 성공 여부. httpx 부재 시 False.
        """
        if not _HTTPX_AVAILABLE:
            log.warning("[youtube] httpx 라이브러리 부재 — graceful False")
            return False
        self._http = httpx.AsyncClient(
            base_url=_API_BASE,
            headers={"Authorization": f"Bearer {self._config.access_token}"},
            timeout=10.0,
        )
        self._connected = True
        log.info("[youtube] connect PASS — chat_id=%s", self._config.live_chat_id)
        return True

    async def disconnect(self) -> None:
        """httpx session close + state reset."""

        if self._http is not None:
            try:
                # 한글 주석 — Phase 5 cycle 의 httpx.AsyncClient.aclose()
                close = getattr(self._http, "aclose", None)
                if close is not None:
                    await close()
            except Exception as exc:  # pragma: no cover
                log.warning("[youtube] disconnect 실패 — %s", exc)
        self._http = None
        self._connected = False
        self._next_page_token = None

    async def receive_loop(self, max_iterations: Optional[int] = None) -> List[object]:
        """cycle 169.422 — liveChatMessages.list actual polling loop.

        Parameters
        ----------
        max_iterations : int | None
            poll iteration 한도 (test injection). None = 무한 loop.

        Returns
        -------
        list[object]
            수신 message dict list (snippet + authorDetails 합산).
        """
        if not self._connected or self._http is None:
            return []
        messages: List[object] = []
        iters = 0
        while True:
            if max_iterations is not None and iters >= max_iterations:
                break
            iters += 1
            params: dict = {
                "liveChatId": self._config.live_chat_id,
                "part": "snippet,authorDetails",
            }
            if self._next_page_token:
                params["pageToken"] = self._next_page_token
            try:
                resp = await self._http.get("/liveChat/messages", params=params)
                if resp.status_code != 200:
                    log.warning("[youtube] poll status=%d", resp.status_code)
                    break
                data = resp.json()
            except Exception as exc:  # pragma: no cover - graceful
                log.warning("[youtube] poll fail — %r", exc)
                break
            self._next_page_token = data.get("nextPageToken")
            poll_ms = data.get("pollingIntervalMillis")
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                author = item.get("authorDetails", {})
                msg = {
                    "platform": self.PLATFORM,
                    "text": snippet.get("displayMessage", ""),
                    "author": author.get("displayName", ""),
                    "author_channel_id": author.get("channelId"),
                    "published_at": snippet.get("publishedAt"),
                    "raw": item,
                }
                messages.append(msg)
                if self._on_message is not None:
                    try:
                        await self._on_message(msg)
                    except Exception as exc:  # pragma: no cover
                        log.warning("[youtube] on_message exc — %r", exc)
            if max_iterations is None:
                interval = (
                    min(_MAX_POLL_INTERVAL_SECONDS, poll_ms / 1000.0)
                    if isinstance(poll_ms, (int, float))
                    else self._config.poll_interval_seconds
                )
                await asyncio.sleep(interval)
        return messages
