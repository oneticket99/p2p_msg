# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk 서버 rooms REST API client — `/api/rooms` 7 method wrapper (cycle 139).

본 module 은 cycle 135 의 ``server/api/rooms_handlers`` (POST/GET/JOIN/LEAVE/
INVITE/KICK 7 endpoint) 의 client-side wrapper. cycle 139 의 main_window 통합
시점 의 의무 의존성 — RoomList sidebar 의 list_rooms / GroupChatView 의
WebRTC mesh 진입 의 join_room / 헤더 추방 의 kick_user 등.

본 module 의 범위
-----------------
- ``RoomPayload`` frozen dataclass — wire dict → Python obj
- ``RoomMemberPayload`` frozen dataclass — peers row wire repr
- ``RoomsClient`` — httpx.AsyncClient wrapper + Bearer 인증 + 7 method
- ``RoomsClientError`` 계열 — Auth / BadRequest / Forbidden / NotFound /
  Conflict / Server / Network 7 종 매핑

graceful 의무 — httpx ImportError 환경 (테스트 collection / headless) 시
``RoomsClient`` 인스턴스화 시점 RuntimeError. client 모듈 import 자체는 통과.

호출 형식 (모두 async)
---------------------
- ``create_room(name: str, kind: str = "group") -> RoomPayload``
- ``list_rooms(scope: str = "all") -> List[RoomPayload]``
- ``get_room(room_id: int) -> Tuple[RoomPayload, List[RoomMemberPayload]]``
- ``join_room(room_id: int) -> int``  # peer_id 반환
- ``leave_room(room_id: int) -> None``
- ``invite_user(room_id: int, user_id: int) -> int``  # 신규 peer_id
- ``kick_user(room_id: int, user_id: int) -> None``

본 module 은 wire layer 의 의무. UI binding (MainWindow / RoomList) 은
별개 cycle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

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


class RoomsClientError(Exception):
    """rooms REST client 의 base exception — 모든 하위 분기 의 root."""


class RoomsAuthError(RoomsClientError):
    """401 Unauthorized — Bearer 토큰 무효 또는 만료."""


class RoomsBadRequestError(RoomsClientError):
    """400 BadRequest — body / path / query 검증 실패."""


class RoomsForbiddenError(RoomsClientError):
    """403 Forbidden — owner 만 허용 등 의 권한 부재."""


class RoomsNotFoundError(RoomsClientError):
    """404 Not Found — room 또는 peer 부재."""


class RoomsConflictError(RoomsClientError):
    """409 Conflict — already_member / room_closed 등 의 상태 충돌."""


class RoomsServerError(RoomsClientError):
    """5xx — 서버 의 내부 오류."""


class RoomsNetworkError(RoomsClientError):
    """httpx 네트워크 실패 — connection / timeout / DNS."""


# ----------------------------------------------------------------------
# Wire payload dataclass
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RoomPayload:
    """단일 room 의 client-side wire repr.

    Attributes
    ----------
    id : int
        rooms.id (PK).
    room_code : str
        rooms.room_code (CHAR(16) 의 선두 8자 hex).
    owner_id : int
        owner users.id.
    kind : str
        "direct" / "group".
    status : str
        "active" / "closed" 등.
    created_at_iso : str | None
        rooms.created_at 의 ISO 8601 string (서버 가 fill).
    """

    id: int
    room_code: str
    owner_id: int
    kind: str = "group"
    status: str = "active"
    created_at_iso: Optional[str] = None

    @classmethod
    def from_wire(cls, wire: dict) -> "RoomPayload":
        """server JSON dict → RoomPayload — 한글 주석: 필수 key 누락 시 KeyError."""

        return cls(
            id=int(wire["id"]),
            room_code=str(wire["room_code"]),
            owner_id=int(wire["owner_id"]),
            kind=str(wire.get("kind", "group")),
            status=str(wire.get("status", "active")),
            created_at_iso=wire.get("created_at"),
        )


@dataclass(frozen=True, slots=True)
class RoomMemberPayload:
    """단일 peers row 의 client-side wire repr — GET /api/rooms/{id} 의 members."""

    id: int
    room_id: int
    user_id: int
    role: str = "member"
    joined_at_iso: Optional[str] = None
    left_at_iso: Optional[str] = None

    @classmethod
    def from_wire(cls, wire: dict) -> "RoomMemberPayload":
        """server JSON dict → RoomMemberPayload."""

        return cls(
            id=int(wire["id"]),
            room_id=int(wire["room_id"]),
            user_id=int(wire["user_id"]),
            role=str(wire.get("role", "member")),
            joined_at_iso=wire.get("joined_at"),
            left_at_iso=wire.get("left_at"),
        )


# ----------------------------------------------------------------------
# RoomsClient
# ----------------------------------------------------------------------


class RoomsClient:
    """REST `/api/rooms` 7 method wrapper.

    Parameters
    ----------
    base_url : str
        서버 base URL (예: `http://114.207.112.73:8765`).
    token : str
        Bearer 인증 토큰 — 로그인 응답 의 ``token`` 필드.
    client : httpx.AsyncClient | None
        외부 주입 (test mock 용). None 일 시 인스턴스 내부 생성 + close 책임.

    Notes
    -----
    - httpx 미설치 환경 인스턴스화 시 ``RuntimeError`` — graceful 의무.
    - 모든 method 는 async. ``async with RoomsClient(...) as c:`` 패턴 권장.
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
                "httpx 미설치 — RoomsClient 사용 불가. pip install httpx 의무."
            )
        if not base_url:
            raise ValueError("base_url 필수")
        if not token:
            raise ValueError("token 필수 (Bearer 인증)")

        self._base_url = base_url.rstrip("/")
        self._token = token
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "RoomsClient":
        """async context — 본 cycle 의 mock 친화 entry."""

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
        """httpx.AsyncClient lazy init — Bearer header default."""

        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=httpx.Timeout(10.0),
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
            raise RoomsAuthError(message)
        if status == 400:
            raise RoomsBadRequestError(message)
        if status == 403:
            raise RoomsForbiddenError(message)
        if status == 404:
            raise RoomsNotFoundError(message)
        if status == 409:
            raise RoomsConflictError(message)
        if 500 <= status < 600:
            raise RoomsServerError(message)
        raise RoomsClientError(f"unexpected status {status}: {message}")

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """공통 request wrapper — Bearer header + network 예외 mapping."""

        client = self._ensure_client()
        url = f"{self._base_url}{path}"
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            log.error("[rooms_client] network err %s %s: %r", method, url, exc)
            raise RoomsNetworkError(f"{method} {url}: {exc}") from exc

        try:
            payload = response.json()
        except ValueError:
            payload = {"error": "invalid_json", "message": response.text[:200]}

        self._raise_for_status(response.status_code, payload)
        return payload

    # ------------------------------------------------------------------
    # 7 public method
    # ------------------------------------------------------------------

    async def create_room(
        self,
        name: str = "",
        kind: str = "group",
        avatar_ref: str = "",
        description: str = "",
    ) -> RoomPayload:
        """POST /api/rooms — 룸 생성 + owner 자동 peers row 등록.

        Parameters
        ----------
        name : str
            그룹/채널 표기명 — 서버 rooms.name(0017) 영속.
        kind : str
            "direct" / "group" / "channel"(0019). default = group.
        avatar_ref : str
            cycle 169.852 — POST /api/avatars 업로드 회신 키(`avatars/<sha>.<ext>`).
            빈값 = avatar 없음(이니셜 fallback). 서버가 실재 검증 후 rooms.avatar_ref 영속.
        description : str
            채널 설명 — 서버 rooms.description(0017) 영속. 빈값 허용.

        Returns
        -------
        RoomPayload
            id + room_code + owner_id + kind 채워진 신규 row.
        """

        body = {"kind": kind}
        if name:
            body["name"] = name
        if avatar_ref:
            body["avatar_ref"] = avatar_ref
        if description:
            body["description"] = description
        payload = await self._request("POST", "/api/rooms", json=body)
        return RoomPayload.from_wire(payload)

    async def list_rooms(self, scope: str = "all") -> List[RoomPayload]:
        """GET /api/rooms — owner + member 룸 list 조회.

        Parameters
        ----------
        scope : str
            "owner" / "member" / "all". default all (서버 default 와 정합).

        Returns
        -------
        List[RoomPayload]
            중복 제거된 룸 목록 (서버 가 set 으로 정리).
        """

        params = {"scope": scope}
        payload = await self._request("GET", "/api/rooms", params=params)
        rooms_wire = payload.get("rooms", [])
        return [RoomPayload.from_wire(r) for r in rooms_wire]

    async def get_room(
        self, room_id: int
    ) -> Tuple[RoomPayload, List[RoomMemberPayload]]:
        """GET /api/rooms/{room_id} — 룸 detail + 활성 멤버 list.

        Returns
        -------
        Tuple[RoomPayload, List[RoomMemberPayload]]
            (룸 정보, 활성 peers list). 비참여자 = 403 → RoomsForbiddenError.
        """

        payload = await self._request("GET", f"/api/rooms/{room_id}")
        room = RoomPayload.from_wire(payload["room"])
        members = [
            RoomMemberPayload.from_wire(m) for m in payload.get("members", [])
        ]
        return room, members

    async def join_room(self, room_id: int) -> int:
        """POST /api/rooms/{room_id}/join — 룸 가입.

        Returns
        -------
        int
            신규 peers.id (PK). 이미 참여 중 = 409 → RoomsConflictError.
        """

        payload = await self._request("POST", f"/api/rooms/{room_id}/join")
        return int(payload["peer_id"])

    async def leave_room(self, room_id: int) -> None:
        """POST /api/rooms/{room_id}/leave — 룸 탈퇴 (peers.left_at UPDATE).

        활성 참여 부재 = 404 → RoomsNotFoundError.
        """

        await self._request("POST", f"/api/rooms/{room_id}/leave")

    async def invite_user(self, room_id: int, user_id: int) -> int:
        """POST /api/rooms/{room_id}/invite — owner 의 초대.

        Parameters
        ----------
        user_id : int
            초대할 대상 users.id. 자기 자신 = 400. 이미 참여 = 409.

        Returns
        -------
        int
            신규 peers.id.
        """

        if user_id <= 0:
            raise RoomsBadRequestError("user_id 양수 정수 의무")
        body = {"user_id": user_id}
        payload = await self._request(
            "POST", f"/api/rooms/{room_id}/invite", json=body
        )
        return int(payload["peer_id"])

    async def kick_user(self, room_id: int, user_id: int) -> None:
        """POST /api/rooms/{room_id}/kick — owner 의 추방.

        owner 부재 + 자기 자신 추방 = 400. target 미참여 = 404.
        """

        if user_id <= 0:
            raise RoomsBadRequestError("user_id 양수 정수 의무")
        body = {"user_id": user_id}
        await self._request(
            "POST", f"/api/rooms/{room_id}/kick", json=body
        )
