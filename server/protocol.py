"""시그널링 프로토콜 메시지 모델 정의 (Model 계층).

JSON envelope 5 + 4 종 메시지 — 클라이언트 → 서버 5종, 서버 → 클라이언트 4종.
실 데이터(텍스트·이미지·파일)는 본 envelope 안에 포함되지 않으며, WebRTC
DataChannel 직결로 운반된다. 본 모듈은 ``TypedDict`` 기반 구조 선언과
런타임 검증 보조 함수만 노출한다.

본 모듈은 외부 IO 를 수행하지 않는다 — 순수 데이터 모델이며 ``signaling.py``
(Router) 와 ``room.py`` (Service) 양쪽에서 import 한다.
"""

from __future__ import annotations

from typing import Any, Final, Literal, TypedDict


# 클라이언트 → 서버 메시지 타입 식별자 (5종)
MSG_JOIN: Final[str] = "JOIN"
MSG_LEAVE: Final[str] = "LEAVE"
MSG_OFFER: Final[str] = "OFFER"
MSG_ANSWER: Final[str] = "ANSWER"
MSG_ICE: Final[str] = "ICE"

# 서버 → 클라이언트 메시지 타입 식별자 (4종)
MSG_PEERS: Final[str] = "PEERS"
MSG_PEER_JOINED: Final[str] = "PEER_JOINED"
MSG_PEER_LEFT: Final[str] = "PEER_LEFT"
MSG_ERROR: Final[str] = "ERROR"

# 클라이언트 → 서버 허용 타입 집합 (라우터 화이트리스트)
CLIENT_MSG_TYPES: Final[frozenset[str]] = frozenset(
    {MSG_JOIN, MSG_LEAVE, MSG_OFFER, MSG_ANSWER, MSG_ICE}
)


# ---------------------------------------------------------------------------
# 클라이언트 → 서버 envelope (5종)
# ---------------------------------------------------------------------------


class JoinMessage(TypedDict):
    """클라이언트가 특정 방에 합류할 때 전송하는 메시지.

    서버는 동일 ``room`` 안의 기존 peer 목록을 ``PEERS`` 응답으로 회신하고,
    기존 peer 들에게는 ``PEER_JOINED`` 알림을 브로드캐스트한다.
    """

    type: Literal["JOIN"]
    room: str
    peer_id: str


class LeaveMessage(TypedDict):
    """클라이언트가 명시적으로 방을 떠날 때 전송하는 메시지.

    소켓 연결 종료로도 동일한 효과를 얻을 수 있으나, 명시 LEAVE 는 정상
    종료 의도를 서버에 알린다.
    """

    type: Literal["LEAVE"]
    room: str
    peer_id: str


class OfferMessage(TypedDict):
    """A → B WebRTC SDP Offer (서버 경유 단순 중계).

    서버는 ``sdp`` 본문을 검증하지 않고 ``to`` 대상 peer 에게 그대로 전달한다.
    """

    type: Literal["OFFER"]
    # 송신 peer 식별자
    from_: str
    # 수신 peer 식별자 — 동일 방 안에 존재해야 함
    to: str
    sdp: str


class AnswerMessage(TypedDict):
    """B → A WebRTC SDP Answer (서버 경유 단순 중계)."""

    type: Literal["ANSWER"]
    from_: str
    to: str
    sdp: str


class IceMessage(TypedDict):
    """양방향 ICE candidate 교환 (서버 경유 단순 중계).

    ``candidate`` 는 RFC 8839 형식 dict — sdpMid/sdpMLineIndex/candidate 등을
    포함한다. 서버는 본문을 파싱하지 않고 통과만 시킨다.
    """

    type: Literal["ICE"]
    from_: str
    to: str
    candidate: dict[str, Any]


# ---------------------------------------------------------------------------
# 서버 → 클라이언트 envelope (4종)
# ---------------------------------------------------------------------------


class PeersMessage(TypedDict):
    """JOIN 응답 — 동일 방 안의 기존 peer 목록.

    합류한 본인은 목록에서 제외된다.
    """

    type: Literal["PEERS"]
    room: str
    peers: list[str]


class PeerJoinedMessage(TypedDict):
    """동일 방의 신규 peer 합류 알림 (기존 peer 들 대상 브로드캐스트)."""

    type: Literal["PEER_JOINED"]
    peer_id: str


class PeerLeftMessage(TypedDict):
    """동일 방의 peer 이탈 알림 (LEAVE 또는 연결 종료 시)."""

    type: Literal["PEER_LEFT"]
    peer_id: str


class ErrorMessage(TypedDict):
    """프로토콜 위반·라우팅 실패 등 오류 응답.

    ``code`` 는 안정적 식별자 (예: ``BAD_JSON``, ``UNKNOWN_TYPE``,
    ``PEER_NOT_FOUND``), ``message`` 는 사람이 읽는 보조 설명.
    """

    type: Literal["ERROR"]
    code: str
    message: str


# ---------------------------------------------------------------------------
# 오류 코드 상수 — Router 안쪽 일관성 유지를 위해 한 곳에 모음
# ---------------------------------------------------------------------------

ERR_BAD_JSON: Final[str] = "BAD_JSON"
ERR_UNKNOWN_TYPE: Final[str] = "UNKNOWN_TYPE"
ERR_MISSING_FIELD: Final[str] = "MISSING_FIELD"
ERR_NOT_JOINED: Final[str] = "NOT_JOINED"
ERR_PEER_NOT_FOUND: Final[str] = "PEER_NOT_FOUND"
ERR_ROOM_NOT_FOUND: Final[str] = "ROOM_NOT_FOUND"


# ---------------------------------------------------------------------------
# 직렬화 헬퍼 — TypedDict 의 ``from_`` 키를 wire format ``from`` 으로 매핑
# ---------------------------------------------------------------------------
#
# 파이썬 예약어 ``from`` 충돌을 피하기 위해 TypedDict 안에서는 ``from_`` 으로
# 선언하지만, 실제 와이어 포맷은 클라이언트와의 호환을 위해 ``from`` 키를
# 사용한다. 본 헬퍼가 그 변환을 흡수한다.


def wire_to_internal(payload: dict[str, Any]) -> dict[str, Any]:
    """와이어 포맷 dict 에서 내부 표현으로 변환 (``from`` → ``from_``)."""
    if "from" in payload and "from_" not in payload:
        converted = dict(payload)
        converted["from_"] = converted.pop("from")
        return converted
    return payload


def internal_to_wire(payload: dict[str, Any]) -> dict[str, Any]:
    """내부 표현 dict 에서 와이어 포맷으로 변환 (``from_`` → ``from``)."""
    if "from_" in payload:
        converted = dict(payload)
        converted["from"] = converted.pop("from_")
        return converted
    return payload


def is_valid_client_type(type_value: Any) -> bool:
    """클라이언트 → 서버 허용 메시지 타입인지 검증.

    Router 안에서 외부 입력 검증용으로 호출된다.
    """
    return isinstance(type_value, str) and type_value in CLIENT_MSG_TYPES
