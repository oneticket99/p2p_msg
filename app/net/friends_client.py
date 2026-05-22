# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk 서버 friends REST API client — `/api/friends` 8 method wrapper (cycle 147).

본 module 은 cycle 144 의 ``server/api/friends_handlers`` (GET/POST/ACCEPT/REJECT/
BLOCK/REMOVE/PENDING/SEARCH 8 endpoint) 의 client-side wrapper. cycle 147 의
invite_dialog FriendList dropdown populate + main_window 통합 chain 의 의무
의존성. RoomsClient + MessagesRestClient 의 동일 graceful 패턴 의무.

본 module 의 범위
-----------------
- ``FriendProfilePayload`` frozen dataclass — wire dict → Python obj
- ``UserSearchResult`` frozen dataclass — search endpoint 응답 row
- ``FriendsClient`` — httpx.AsyncClient wrapper + Bearer 인증 + 8 method
- ``FriendsClientError`` 계열 — Auth / BadRequest / Forbidden / NotFound /
  Conflict / Server / Network 7 종 매핑

graceful 의무 — httpx ImportError 환경 (테스트 collection / headless) 시
``FriendsClient`` 인스턴스화 시점 RuntimeError. client 모듈 import 자체는 통과.

호출 형식 (모두 async)
---------------------
- ``list_friends(status: str | None = None) -> List[FriendProfilePayload]``
- ``list_pending() -> List[FriendProfilePayload]``
- ``search_users(keyword: str, limit: int = 20) -> List[UserSearchResult]``
- ``request_friend(user_id: int, nickname: str | None = None) -> int``
- ``accept_friend(user_id: int) -> None``
- ``reject_friend(user_id: int) -> None``
- ``block_friend(user_id: int) -> None``
- ``remove_friend(user_id: int) -> None``

본 module 은 wire layer 의 의무. UI binding (FriendListWidget / InviteDialog) 은
별개 cycle. cycle 147 의 invite_dialog 통합 = ``list_friends(status="accepted")``
호출 + dropdown populate 의 main_window 책임.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

# httpx graceful — headless / test collection 시 import 시점 미차단
try:
    import httpx

    _HTTPX_AVAILABLE = True
except ImportError:  # pragma: no cover — httpx 미설치 환경 폴백
    _HTTPX_AVAILABLE = False

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Exception hierarchy
# ----------------------------------------------------------------------


class FriendsClientError(Exception):
    """friends REST client 의 base exception — 모든 하위 분기 의 root."""


class FriendsAuthError(FriendsClientError):
    """401 Unauthorized — Bearer 토큰 무효 또는 만료."""


class FriendsBadRequestError(FriendsClientError):
    """400 BadRequest — body / path / query 검증 실패."""


class FriendsForbiddenError(FriendsClientError):
    """403 Forbidden — 권한 부재 (self-add 등)."""


class FriendsNotFoundError(FriendsClientError):
    """404 Not Found — 친구 관계 row 부재."""


class FriendsConflictError(FriendsClientError):
    """409 Conflict — 이미 친구 / 차단 등 의 상태 충돌."""


class FriendsServerError(FriendsClientError):
    """5xx — 서버 의 내부 오류."""


class FriendsNetworkError(FriendsClientError):
    """httpx 네트워크 실패 — connection / timeout / DNS."""


# ----------------------------------------------------------------------
# Wire payload dataclass
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FriendProfilePayload:
    """단일 친구 관계 의 client-side wire repr — server _friend_with_profile_to_wire 정합.

    Attributes
    ----------
    id : int
        friends.id (PK).
    user_id : int
        관계 owner PK (friends.user_id).
    friend_user_id : int
        관계 peer PK (friends.friend_user_id) — invite_dialog dropdown 의 payload.
    friend_username : str
        peer 의 표시명 (users.username) — dropdown 가시 라벨.
    status : str
        pending / accepted / blocked / removed 의 4 종.
    nickname : str | None
        owner 의 friend 별명 (선택).
    requested_at_iso : str | None
        요청 시점 ISO 8601 (서버 fill).
    accepted_at_iso : str | None
        수락 시점 ISO 8601 (서버 fill).
    friend_email_verified : bool
        peer 의 OTP 인증 완료 여부 (UI badge 의무).
    """

    id: int
    user_id: int
    friend_user_id: int
    friend_username: str
    status: str = "pending"
    nickname: Optional[str] = None
    requested_at_iso: Optional[str] = None
    accepted_at_iso: Optional[str] = None
    friend_email_verified: bool = False

    @classmethod
    def from_wire(cls, wire: dict) -> "FriendProfilePayload":
        """server JSON dict → FriendProfilePayload — 필수 key 누락 시 KeyError."""

        return cls(
            id=int(wire["id"]),
            user_id=int(wire["user_id"]),
            friend_user_id=int(wire["friend_user_id"]),
            friend_username=str(wire.get("friend_username", "")),
            status=str(wire.get("status", "pending")),
            nickname=wire.get("nickname"),
            requested_at_iso=wire.get("requested_at"),
            accepted_at_iso=wire.get("accepted_at"),
            friend_email_verified=bool(wire.get("friend_email_verified", False)),
        )


@dataclass(frozen=True, slots=True)
class UserSearchResult:
    """search endpoint 응답 의 단일 user row.

    Attributes
    ----------
    id : int
        users.id (PK) — 친구 요청 시 target.
    username : str
        users.username — 로그인 식별자 (영문).
    display_name : str
        users.display_name — 표시 이름 (한글 가능). cycle 169.491 신설.
    nickname : str
        users.nickname — 닉네임 (한글 가능). cycle 169.491 신설.
    email_verified : bool
        OTP 인증 완료 여부 — UI badge 의무.
    """

    id: int
    username: str
    display_name: str = ""
    nickname: str = ""
    email_verified: bool = False

    @classmethod
    def from_wire(cls, wire: dict) -> "UserSearchResult":
        """server JSON dict → UserSearchResult — id/username 필수."""

        return cls(
            id=int(wire["id"]),
            username=str(wire.get("username", "")),
            display_name=str(wire.get("display_name") or ""),
            nickname=str(wire.get("nickname") or ""),
            email_verified=bool(wire.get("email_verified", False)),
        )


# ----------------------------------------------------------------------
# FriendsClient
# ----------------------------------------------------------------------


class FriendsClient:
    """REST `/api/friends` 8 method wrapper (cycle 147 신설).

    Parameters
    ----------
    base_url : str
        서버 base URL (예: ``http://114.207.112.73:8765``).
    token : str
        Bearer 인증 토큰 — 로그인 응답 의 ``token`` 필드.
    client : httpx.AsyncClient | None
        외부 주입 (test mock 용). None 일 시 인스턴스 내부 생성 + close 책임.

    Notes
    -----
    - httpx 미설치 환경 인스턴스화 시 ``RuntimeError`` — graceful 의무.
    - 모든 method 는 async. ``async with FriendsClient(...) as c:`` 패턴 권장.
    - HTTP status → 7 분기 exception 매핑 의 의무 (401/400/403/404/409/5xx/network).
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        client: Optional["httpx.AsyncClient"] = None,
    ) -> None:
        """초기화 — base_url 정규화 + Bearer header 준비."""

        if not _HTTPX_AVAILABLE:
            raise RuntimeError(
                "httpx 미설치 — FriendsClient 사용 불가. pip install httpx 의무."
            )
        if not base_url:
            raise ValueError("base_url 필수")
        if not token:
            raise ValueError("token 필수 (Bearer 인증)")

        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "FriendsClient":
        """async context — mock 친화 entry."""

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """async context exit — 내부 생성 client 의 close 책임."""

        await self.close()

    async def close(self) -> None:
        """내부 httpx.AsyncClient 의 close (소유 시 만)."""

        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> "httpx.AsyncClient":
        """httpx.AsyncClient lazy init — Bearer header default.

        cycle 169.494 — TLS verify TOOTALK_TLS_VERIFY env 정합. demo self-signed cert
        verify=False fallback. AuthClient aiohttp ssl.CERT_NONE 패턴 등가.
        """

        if self._client is None:
            # 한글 주석 — TOOTALK_TLS_VERIFY=0 시점 verify=False (self-signed cert 정합).
            # default "0" — 다른 client (_ssl_util.build_ssl_context) 동기. production = TOOTALK_TLS_VERIFY=1 명시 의무.
            import os
            tls_verify = os.environ.get("TOOTALK_TLS_VERIFY", "0") != "0"
            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=httpx.Timeout(10.0),
                verify=tls_verify,
            )
        return self._client

    # ------------------------------------------------------------------
    # 내부 헬퍼 — HTTP status → exception 매핑
    # ------------------------------------------------------------------

    @staticmethod
    def _raise_for_status(status: int, payload: dict) -> None:
        """HTTP status 기반 exception 분기 — payload 의 error 메시지 보존."""

        if 200 <= status < 300:
            return
        message = payload.get("error") or payload.get("message") or f"HTTP {status}"
        if status == 401:
            raise FriendsAuthError(message)
        if status == 400:
            raise FriendsBadRequestError(message)
        if status == 403:
            raise FriendsForbiddenError(message)
        if status == 404:
            raise FriendsNotFoundError(message)
        if status == 409:
            raise FriendsConflictError(message)
        if 500 <= status < 600:
            raise FriendsServerError(message)
        raise FriendsClientError(f"unexpected status {status}: {message}")

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """공통 request wrapper — Bearer header + network 예외 mapping."""

        client = self._ensure_client()
        url = f"{self._base_url}{path}"
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            log.error("[friends_client] network err %s %s: %r", method, url, exc)
            raise FriendsNetworkError(f"{method} {url}: {exc}") from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {"error": "invalid_json", "message": response.text[:200]}
        if not isinstance(payload, dict):
            payload = {"error": "unexpected_payload", "raw": payload}

        self._raise_for_status(response.status_code, payload)
        return payload

    # ------------------------------------------------------------------
    # 8 public method
    # ------------------------------------------------------------------

    async def list_friends(
        self, status: Optional[str] = None
    ) -> List[FriendProfilePayload]:
        """GET /api/friends — 친구 list (pending + accepted + blocked).

        Parameters
        ----------
        status : str | None
            client-side 필터 — "accepted" / "pending" / "blocked" 의 부분 집합 만 반환.
            None = 전체 (서버 응답 그대로). 본 cycle 147 의 invite_dialog dropdown =
            ``status="accepted"`` 호출 의무.

        Returns
        -------
        List[FriendProfilePayload]
            친구 list — server 의 created DESC 정렬 보존.
        """

        payload = await self._request("GET", "/api/friends")
        friends_wire = payload.get("friends", [])
        items = [FriendProfilePayload.from_wire(r) for r in friends_wire]
        if status:
            items = [f for f in items if f.status == status]
        return items

    async def list_pending(self) -> List[FriendProfilePayload]:
        """GET /api/friends/pending — 수신 pending 요청 list (받은 요청 만)."""

        payload = await self._request("GET", "/api/friends/pending")
        pending_wire = payload.get("pending", [])
        return [FriendProfilePayload.from_wire(r) for r in pending_wire]

    async def search_users(
        self, keyword: str, limit: int = 20
    ) -> List[UserSearchResult]:
        """GET /api/friends/search?q=&limit= — username 부분 매칭 검색.

        Parameters
        ----------
        keyword : str
            검색어 — server 2자 이상 의무. 미달 시 400 → FriendsBadRequestError.
        limit : int
            결과 cap (server 50 max).

        Returns
        -------
        List[UserSearchResult]
            검색 결과 — 자기 PK 제외 의 server-side 사전 필터.
        """

        if not isinstance(keyword, str) or not keyword.strip():
            raise FriendsBadRequestError("keyword 빈 문자열 차단")
        if limit <= 0:
            raise FriendsBadRequestError("limit 양수 의무")
        params = {"q": keyword.strip(), "limit": str(limit)}
        payload = await self._request("GET", "/api/friends/search", params=params)
        results_wire = payload.get("results", [])
        return [UserSearchResult.from_wire(r) for r in results_wire]

    async def request_friend(
        self, user_id: int, nickname: Optional[str] = None
    ) -> int:
        """POST /api/friends — 친구 요청 발신.

        Parameters
        ----------
        user_id : int
            요청 대상 users.id. 자기 자신 = 400 → FriendsBadRequestError.
        nickname : str | None
            owner 가 friend 에게 부여하는 별명 (선택).

        Returns
        -------
        int
            신규 friends.id.
        """

        if user_id <= 0:
            raise FriendsBadRequestError("user_id 양수 정수 의무")
        body: dict = {"user_id": user_id}
        if nickname is not None:
            if not isinstance(nickname, str):
                raise FriendsBadRequestError("nickname 문자열 의무")
            stripped = nickname.strip()[:64]
            if stripped:
                body["nickname"] = stripped
        payload = await self._request("POST", "/api/friends", json=body)
        return int(payload["id"])

    async def accept_friend(self, user_id: int) -> None:
        """POST /api/friends/{user_id}/accept — pending → accepted 수락.

        Parameters
        ----------
        user_id : int
            발신자 PK (수락 대상). pending row 부재 = 404.
        """

        if user_id <= 0:
            raise FriendsBadRequestError("user_id 양수 정수 의무")
        await self._request("POST", f"/api/friends/{user_id}/accept")

    async def reject_friend(self, user_id: int) -> None:
        """POST /api/friends/{user_id}/reject — pending → removed 거절."""

        if user_id <= 0:
            raise FriendsBadRequestError("user_id 양수 정수 의무")
        await self._request("POST", f"/api/friends/{user_id}/reject")

    async def block_friend(self, user_id: int) -> None:
        """POST /api/friends/{user_id}/block — 차단 (status=blocked).

        기존 관계 부재 시 = 신규 blocked row INSERT (server-side).
        """

        if user_id <= 0:
            raise FriendsBadRequestError("user_id 양수 정수 의무")
        await self._request("POST", f"/api/friends/{user_id}/block")

    async def remove_friend(self, user_id: int) -> None:
        """DELETE /api/friends/{user_id} — 친구 관계 제거 (status=removed).

        soft delete — history 보존. 양방향 row 동시 갱신.
        """

        if user_id <= 0:
            raise FriendsBadRequestError("user_id 양수 정수 의무")
        await self._request("DELETE", f"/api/friends/{user_id}")
