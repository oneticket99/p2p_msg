# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk 서버 reactions REST API client — `/api/messages/{id}/reactions` 3 method wrapper (cycle 156 신설).

server/api/reactions_handlers.py (cycle 155 신설) 의 client-side wrapper.
MessageBubble.add_reaction (cycle 153.6 신설) 의 server persist binding chain.

호출 형식 (모두 async):
    add_reaction(message_id, emoji) -> int (total_count)
    list_reactions(message_id) -> List[ReactionEntry]
    remove_reaction(message_id, emoji) -> None

graceful = httpx ImportError 시 RuntimeError + log + UI 차단 부재.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:  # pragma: no cover — headless / test env
    _HTTPX_AVAILABLE = False

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReactionEntry:
    """단일 reaction view model — emoji + count."""
    emoji: str
    count: int


class ReactionsClientError(Exception):
    """reactions client base exception."""


class ReactionsAuthError(ReactionsClientError):
    """401 Authorization 부재."""


class ReactionsNetworkError(ReactionsClientError):
    """httpx network 실패."""


class ReactionsClient:
    """async httpx wrapper — Bearer 인증 + 3 method."""

    def __init__(self, base_url: str, token: Optional[str] = None) -> None:
        if not _HTTPX_AVAILABLE:
            raise RuntimeError("httpx 미설치 — ReactionsClient 생성 불가")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client: Optional[httpx.AsyncClient] = None

    def set_token(self, token: str) -> None:
        """세션 토큰 갱신 — login 직후 호출 의무."""
        self._token = token

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _ensure_client(self) -> "httpx.AsyncClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def add_reaction(self, message_id: int, emoji: str) -> int:
        """POST /api/messages/{message_id}/reactions — emoji 추가 + total count 반환."""
        client = await self._ensure_client()
        url = f"{self._base_url}/api/messages/{message_id}/reactions"
        try:
            resp = await client.post(url, json={"emoji": emoji}, headers=self._headers())
        except httpx.HTTPError as exc:
            log.warning("[reactions] add network 실패 — %r", exc)
            raise ReactionsNetworkError(str(exc)) from exc
        if resp.status_code == 401:
            raise ReactionsAuthError("Bearer 부재 또는 만료")
        if resp.status_code >= 400:
            raise ReactionsClientError(f"HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        return int(data.get("total_count", 0))

    async def list_reactions(self, message_id: int) -> List[ReactionEntry]:
        """GET /api/messages/{message_id}/reactions — emoji + count list."""
        client = await self._ensure_client()
        url = f"{self._base_url}/api/messages/{message_id}/reactions"
        try:
            resp = await client.get(url, headers=self._headers())
        except httpx.HTTPError as exc:
            log.warning("[reactions] list network 실패 — %r", exc)
            raise ReactionsNetworkError(str(exc)) from exc
        if resp.status_code >= 400:
            raise ReactionsClientError(f"HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        return [
            ReactionEntry(emoji=str(r["emoji"]), count=int(r["count"]))
            for r in data.get("reactions", [])
        ]

    async def remove_reaction(self, message_id: int, emoji: str) -> None:
        """DELETE /api/messages/{message_id}/reactions/{emoji} — emoji 제거."""
        client = await self._ensure_client()
        url = f"{self._base_url}/api/messages/{message_id}/reactions/{emoji}"
        try:
            resp = await client.delete(url, headers=self._headers())
        except httpx.HTTPError as exc:
            log.warning("[reactions] remove network 실패 — %r", exc)
            raise ReactionsNetworkError(str(exc)) from exc
        if resp.status_code == 401:
            raise ReactionsAuthError("Bearer 부재 또는 만료")
        if resp.status_code >= 400:
            raise ReactionsClientError(f"HTTP {resp.status_code}: {resp.text}")
