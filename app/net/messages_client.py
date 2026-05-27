# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk 서버 messages REST API client — Phase 3 사이클 62 + cycle 142 확장.

계층 위치 — app/net 클라이언트 계층(정본 §E). server `messages_handlers` counterpart.
ChatView/main_window 가 호출. 두 client 동거(aiohttp lazy load + httpx CRUD).

본 module 의 2 client 동거:

1. ``MessagesClient`` (aiohttp) — cycle 60 의 lazy load client.
   ``GET /api/messages?room_id&start_ts_ms&end_ts_ms&limit`` 만 wrapping. ChatView
   pre-fill / 구간 lazy load 담당.

2. ``MessagesRestClient`` (httpx) — cycle 142 신설 persistence + CRUD wrapper.
   cycle 141 의 server endpoint 4종 binding — POST / GET (paginated) / GET single /
   DELETE. main_window 의 message_send_requested handler 가 의존.

httpx 부재 graceful — ``MessagesRestClient`` 인스턴스화 시점 RuntimeError. module
import 자체 는 차단 부재 (test collection 호환).

본 module 범위
-------------
- ``MessagePayload`` frozen dataclass — 단일 message 의 JSON wire 의 client-side repr
- ``MessageFetchResult`` frozen dataclass — list_messages_in_range 응답 list
- ``MessagesPageResult`` frozen dataclass — list_messages (paginated) 응답 list + total
- ``MessagesClient`` — aiohttp session wrapper (cycle 60 그대로 보존)
- ``MessagesRestClient`` — httpx.AsyncClient wrapper (cycle 142 신설 — 4 method)
- ``MessagesClientError`` 계열 — 인증 실패 / BadRequest / Forbidden / NotFound /
  서버 오류 / 네트워크 의 6 종

본 cycle 의 범위 외 (별개 cycle):
- WebRTC mesh broadcast 의 client 영역 ack 대기 (GroupMessageClient 별개)
- 응답 cache 의 LRU + TTL (별개 cycle)
- E2EE decrypt 통합 (받은 ciphertext 의 client 단 decrypt — 별개 cycle)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import aiohttp

# httpx graceful — 미설치 환경(test collection 등)에서 import 시점 차단 회피.
try:
    import httpx  # type: ignore[import-not-found]

    _HTTPX_AVAILABLE = True
except ImportError:  # pragma: no cover — httpx 미설치 환경 폴백
    _HTTPX_AVAILABLE = False

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


class MessagesForbiddenError(MessagesClientError):
    """403 Forbidden — sender/owner 아닌 권한 부재 (cycle 142 신설)."""


class MessagesNotFoundError(MessagesClientError):
    """404 Not Found — room 또는 message 부재 (cycle 142 신설)."""


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


# ----------------------------------------------------------------------
# cycle 142 신설 — httpx 기반 persistence + CRUD client
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MessagesPageResult:
    """``list_messages`` (paginated) 의 응답.

    Attributes
    ----------
    messages : list[MessagePayload]
        결과 list — 서버 의 created_at DESC + id DESC 순서.
    count : int
        본 응답 의 row 수.
    total : int
        룸 전체 row 수 (offset 계산용).
    limit : int
        적용된 page size.
    offset : int
        적용된 page offset.
    """

    messages: List[MessagePayload] = field(default_factory=list)
    count: int = 0
    total: int = 0
    limit: int = 0
    offset: int = 0


class MessagesRestClient:
    """messages REST CRUD client (cycle 142 신설 — httpx 기반).

    cycle 141 의 server endpoint 4종 binding:

    - ``post_message(room_id, body, kind="text", file_id=None)`` →
      POST /api/rooms/{room_id}/messages
    - ``list_messages(room_id, limit=50, offset=0)`` →
      GET /api/rooms/{room_id}/messages
    - ``get_message(message_id)`` → GET /api/messages/{message_id}
    - ``delete_message(message_id)`` → DELETE /api/messages/{message_id}

    Parameters
    ----------
    base_url : str
        서버 base URL.
    token : str
        Bearer 인증 토큰 (auth_client.login 응답 의 ``token``).
    client : httpx.AsyncClient | None
        외부 주입 (test mock 의무). None 일 시 인스턴스 내부 생성 + close 책임.

    Notes
    -----
    - httpx 미설치 환경 인스턴스화 시 ``RuntimeError`` — graceful 의무.
    - HTTP status → 7 분기 exception 매핑 (401/400/403/404/409/5xx/network).
    - 모든 method = async. ``async with MessagesRestClient(...) as c:`` 권장.
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        client: Optional["httpx.AsyncClient"] = None,
    ) -> None:
        if not _HTTPX_AVAILABLE:
            raise RuntimeError(
                "httpx 미설치 — MessagesRestClient 사용 불가. pip install httpx 의무."
            )
        if not base_url:
            raise ValueError("base_url 빈 문자열 불가")
        if not token:
            raise ValueError("token 빈 문자열 불가")
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "MessagesRestClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def close(self) -> None:
        """내부 httpx.AsyncClient 의 close (소유 시 만)."""

        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> "httpx.AsyncClient":
        """httpx.AsyncClient lazy init — Bearer header default."""

        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=httpx.Timeout(10.0),
            )
        return self._client

    @staticmethod
    def _raise_for_status(status: int, payload: dict) -> None:
        """HTTP status → exception 분기 — payload error 메시지 보존."""

        if 200 <= status < 300:
            return
        message = (
            payload.get("error") or payload.get("message") or f"HTTP {status}"
        )
        if status == 401:
            raise MessagesAuthError(message)
        if status == 400:
            raise MessagesBadRequestError(message)
        if status == 403:
            raise MessagesForbiddenError(message)
        if status == 404:
            raise MessagesNotFoundError(message)
        if 500 <= status < 600:
            raise MessagesServerError(f"ServerError HTTP {status}")
        raise MessagesClientError(f"unexpected HTTP {status}: {message}")

    async def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """공통 request wrapper — Bearer header + network 예외 mapping."""

        client = self._ensure_client()
        url = f"{self._base_url}{path}"
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            log.error("[messages_rest] network err %s %s: %r", method, url, exc)
            raise MessagesNetworkError(f"{method} {url}: {exc}") from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {"error": "invalid_json", "message": response.text[:200]}
        if not isinstance(payload, dict):
            payload = {"error": "unexpected_payload", "raw": payload}

        self._raise_for_status(response.status_code, payload)
        return payload

    # ------------------------------------------------------------------
    # 4 public method
    # ------------------------------------------------------------------

    async def post_message(
        self,
        room_id: int,
        body: str,
        *,
        kind: str = "text",
        file_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /api/rooms/{room_id}/messages — text/file/system INSERT.

        Returns
        -------
        dict
            ``{ok, message_id, room_id, sender_id, kind, created_at}`` — server
            응답 그대로. caller 의 message_id capture 의무.
        """

        if room_id <= 0:
            raise ValueError(f"room_id 양수 의무 — {room_id}")
        if kind == "text" and (not isinstance(body, str) or not body.strip()):
            raise ValueError("text body 비빈 문자열 의무")
        payload_body: Dict[str, Any] = {"kind": kind}
        if body:
            payload_body["body"] = body
        if file_id:
            payload_body["file_id"] = file_id
        return await self._request(
            "POST", f"/api/rooms/{room_id}/messages", json=payload_body
        )

    async def list_messages(
        self, room_id: int, *, limit: int = 50, offset: int = 0
    ) -> MessagesPageResult:
        """GET /api/rooms/{room_id}/messages?limit=&offset= — paginated list."""

        if room_id <= 0:
            raise ValueError(f"room_id 양수 의무 — {room_id}")
        if limit <= 0:
            raise ValueError(f"limit 양수 의무 — {limit}")
        if offset < 0:
            raise ValueError(f"offset 음수 불가 — {offset}")

        params = {"limit": str(limit), "offset": str(offset)}
        payload = await self._request(
            "GET", f"/api/rooms/{room_id}/messages", params=params
        )
        raw_messages = payload.get("messages", [])
        payloads = [MessagePayload.from_wire(m) for m in raw_messages]
        return MessagesPageResult(
            messages=payloads,
            count=int(payload.get("count", len(payloads))),
            total=int(payload.get("total", 0)),
            limit=int(payload.get("limit", limit)),
            offset=int(payload.get("offset", offset)),
        )

    async def get_message(self, message_id: int) -> MessagePayload:
        """GET /api/messages/{message_id} — single message detail."""

        if message_id <= 0:
            raise ValueError(f"message_id 양수 의무 — {message_id}")
        payload = await self._request("GET", f"/api/messages/{message_id}")
        wire = payload.get("message")
        if not isinstance(wire, dict):
            raise MessagesClientError("응답 의 message 필드 부재")
        return MessagePayload.from_wire(wire)

    async def delete_message(self, message_id: int) -> Dict[str, Any]:
        """DELETE /api/messages/{message_id} — soft delete (sender/owner 만).

        Returns
        -------
        dict
            ``{ok, message_id, deleted}`` — server 응답 그대로.
        """

        if message_id <= 0:
            raise ValueError(f"message_id 양수 의무 — {message_id}")
        return await self._request("DELETE", f"/api/messages/{message_id}")
