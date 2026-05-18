# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk 서버 messages REST API client — Phase 3 사이클 62.

ChatView lazy load 의 client-side wrapper. cycle 60 의 `server/api/messages_handlers`
의 GET /api/messages 의 aiohttp + qasync 정합 호출.

본 module 범위
-------------
- ``MessagePayload`` frozen dataclass — 단일 message 의 JSON wire 의 client-side repr
- ``MessageFetchResult`` frozen dataclass — 응답 의 messages list + count + limit
- ``MessagesClient`` — aiohttp session wrapper + Bearer 인증 + 401/400/5xx 매핑
- ``MessagesClientError`` 계열 — 인증 실패 / BadRequest / 서버 오류 / 네트워크 의 4 종

본 cycle 의 범위 외 (별개 cycle):
- ChatView 의 scroll signal hook 통합 (QApplication 의무)
- 별개 thread 의 background fetch (asyncio.Task + qasync)
- 응답 cache 의 LRU + TTL (별개 cycle)
- E2EE decrypt 통합 (받은 ciphertext 의 client 단 decrypt — 별개 cycle)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import aiohttp

log = logging.getLogger(__name__)


class MessagesClientError(Exception):
    """messages REST client 의 base exception."""


class MessagesAuthError(MessagesClientError):
    """401 Unauthorized — Bearer 토큰 무효 또는 만료."""


class MessagesBadRequestError(MessagesClientError):
    """400 BadRequest — query string 검증 실패."""


class MessagesServerError(MessagesClientError):
    """5xx — 서버 의 내부 오류."""


class MessagesNetworkError(MessagesClientError):
    """aiohttp.ClientError — 네트워크 실패."""


@dataclass(frozen=True, slots=True)
class MessagePayload:
    """단일 message 의 client-side wire repr.

    Attributes
    ----------
    id : int
        server-side message id.
    room_id : int
        대상 room.
    sender_id : int
        발신자 user_id.
    kind : str
        text / file / system 의 3 종.
    body : str | None
        text 또는 system 의 본문. file = None.
    file_id : str | None
        file kind 의 file_meta 참조. text / system = None.
    created_at_iso : str
        created_at 의 ISO 8601 string (server 의 datetime.isoformat()).
    """

    id: int
    room_id: int
    sender_id: int
    kind: str
    body: Optional[str]
    file_id: Optional[str]
    created_at_iso: str

    @classmethod
    def from_wire(cls, wire: dict) -> "MessagePayload":
        """server JSON wire dict → MessagePayload.

        Notes
        -----
        필수 key 누락 시 KeyError raise — caller 의 wrap 의무.
        """

        return cls(
            id=int(wire["id"]),
            room_id=int(wire["room_id"]),
            sender_id=int(wire["sender_id"]),
            kind=str(wire["kind"]),
            body=wire.get("body"),
            file_id=wire.get("file_id"),
            created_at_iso=str(wire["created_at"]),
        )


@dataclass(frozen=True, slots=True)
class MessageFetchResult:
    """list_messages_in_range 응답 결과.

    Attributes
    ----------
    messages : list[MessagePayload]
        messages 의 created_at DESC + id DESC 순서. caller 의 reverse 의무 (UI 단 ASC 의무).
    count : int
        server 의 응답 count (의 messages 의 len 의 정합 검증 의무).
    limit : int
        server 의 응답 limit (의 적용된 page size).
    """

    messages: List[MessagePayload] = field(default_factory=list)
    count: int = 0
    limit: int = 0


class MessagesClient:
    """messages REST client.

    Parameters
    ----------
    base_url : str
        서버 base URL.
    token : str
        Bearer 인증 토큰 (auth_client.login 의 결과 의 token).
    session : aiohttp.ClientSession | None
        외부 주입 가능 — None 이면 내부 생성.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url 빈 문자열 불가")
        if not token:
            raise ValueError("token 빈 문자열 불가")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._session = session
        self._owns_session = session is None

    async def close(self) -> None:
        """내부 ClientSession close."""

        if self._owns_session and self._session is not None:
            await self._session.close()

    async def list_messages_in_range(
        self,
        *,
        room_id: int,
        start_ts_ms: int,
        end_ts_ms: int,
        limit: int = 1000,
    ) -> MessageFetchResult:
        """GET /api/messages?room_id&start_ts_ms&end_ts_ms&limit.

        Parameters
        ----------
        room_id : int
            대상 room.
        start_ts_ms : int
            구간 시작 (UNIX epoch ms, inclusive).
        end_ts_ms : int
            구간 끝 (UNIX epoch ms, exclusive).
        limit : int, default 1000
            page size.

        Returns
        -------
        MessageFetchResult
            응답 의 messages + count + limit.

        Raises
        ------
        MessagesAuthError, MessagesBadRequestError, MessagesServerError, MessagesNetworkError
        """

        if room_id <= 0:
            raise ValueError(f"room_id 양수 의무 — {room_id}")
        if start_ts_ms < 0 or end_ts_ms < 0:
            raise ValueError(
                f"timestamp 음수 불가 — start={start_ts_ms} end={end_ts_ms}"
            )
        if end_ts_ms <= start_ts_ms:
            raise ValueError(
                f"end_ts_ms 의 start_ts_ms 초과 의무 — start={start_ts_ms} end={end_ts_ms}"
            )
        if limit <= 0:
            raise ValueError(f"limit 양수 의무 — {limit}")

        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True

        url = f"{self._base_url}/api/messages"
        params = {
            "room_id": str(room_id),
            "start_ts_ms": str(start_ts_ms),
            "end_ts_ms": str(end_ts_ms),
            "limit": str(limit),
        }
        headers = {"Authorization": f"Bearer {self._token}"}

        try:
            async with self._session.get(url, params=params, headers=headers) as resp:
                if resp.status == 401:
                    raise MessagesAuthError(
                        f"Unauthorized — Bearer 토큰 의 갱신 의무"
                    )
                if resp.status == 400:
                    text = await resp.text()
                    raise MessagesBadRequestError(f"BadRequest — {text[:200]}")
                if 500 <= resp.status < 600:
                    raise MessagesServerError(
                        f"ServerError HTTP {resp.status}"
                    )
                if resp.status != 200:
                    raise MessagesClientError(
                        f"unexpected HTTP {resp.status}"
                    )
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as exc:
            log.error("[messages_client] network err url=%s err=%r", url, exc)
            raise MessagesNetworkError(f"네트워크 오류: {exc}") from exc

        raw_messages = data.get("messages", [])
        payloads = [MessagePayload.from_wire(m) for m in raw_messages]
        return MessageFetchResult(
            messages=payloads,
            count=int(data.get("count", len(payloads))),
            limit=int(data.get("limit", limit)),
        )
