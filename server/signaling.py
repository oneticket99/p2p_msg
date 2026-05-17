"""WebSocket 시그널링 핸들러 (Router 계층).

aiohttp ``WebSocketResponse`` 한 개당 한 클라이언트가 매핑된다. 본 모듈은
다음만 책임진다.

- WebSocket upgrade 처리 (``handle_ws``)
- 수신 프레임 JSON 디코드 + 타입 화이트리스트 검증
- 5종 클라이언트 메시지 (JOIN/LEAVE/OFFER/ANSWER/ICE) 를 ``RoomRegistry``
  Service 계층에 위임
- 오류 응답 (``ERROR``) 송신
- 연결 종료 시 ``RoomRegistry.cleanup_peer`` 호출

비즈니스 로직 (peer 라우팅·방 GC·브로드캐스트) 은 본 모듈에 두지 않는다.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import WSMsgType, web

from .protocol import (
    ERR_BAD_JSON,
    ERR_MISSING_FIELD,
    ERR_NOT_JOINED,
    ERR_PEER_NOT_FOUND,
    ERR_ROOM_NOT_FOUND,
    ERR_UNKNOWN_TYPE,
    MSG_ANSWER,
    MSG_ERROR,
    MSG_ICE,
    MSG_JOIN,
    MSG_LEAVE,
    MSG_OFFER,
    is_valid_client_type,
    wire_to_internal,
)
from .room import Peer, RoomRegistry


logger = logging.getLogger(__name__)

# aiohttp app 안에서 RoomRegistry 를 꺼내올 때 사용하는 키
APP_KEY_REGISTRY: str = "room_registry"


async def handle_ws(request: web.Request) -> web.WebSocketResponse:
    """WebSocket 엔드포인트 진입점 — ``/ws`` 라우트에 바인딩된다.

    하나의 연결이 유지되는 동안 본 코루틴이 message loop 를 돈다. 연결이
    종료되면 ``RoomRegistry.cleanup_peer`` 가 호출되어 잔존 상태를 청소한다.
    """
    ws = web.WebSocketResponse(heartbeat=30.0)
    await ws.prepare(request)

    registry: RoomRegistry = request.app[APP_KEY_REGISTRY]

    # peer_id 는 JOIN 메시지 수신 시점에 확정되므로 일단 임시 Peer 컨테이너만
    # 보유. JOIN 이전 송수신은 ``room_id is None`` 으로 가드된다.
    peer: Peer | None = None
    remote = request.remote or "unknown"
    logger.info("새 WebSocket 연결 remote=%s", remote)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                peer = await _dispatch_text(ws, peer, msg.data, registry)
            elif msg.type == WSMsgType.BINARY:
                # 바이너리 프레임은 본 프로토콜에서 정의되지 않음 — ERROR 응답
                await _send_error(
                    ws,
                    ERR_UNKNOWN_TYPE,
                    "바이너리 프레임은 지원하지 않습니다.",
                )
            elif msg.type == WSMsgType.ERROR:
                logger.warning(
                    "WebSocket 오류 remote=%s err=%s", remote, ws.exception()
                )
                break
            # CLOSE/CLOSED/CLOSING 은 루프가 자연 종료
    finally:
        if peer is not None:
            await registry.cleanup_peer(peer)
        if not ws.closed:
            await ws.close()
        logger.info("WebSocket 연결 종료 remote=%s", remote)

    return ws


async def _dispatch_text(
    ws: web.WebSocketResponse,
    peer: Peer | None,
    raw: str,
    registry: RoomRegistry,
) -> Peer | None:
    """텍스트 프레임 한 건을 디코드·검증·라우팅한다.

    Returns:
        업데이트된 Peer (JOIN 직후 새로 생성된 경우) 또는 기존 Peer.
    """
    # ---- 1) JSON 파싱 ----------------------------------------------------
    try:
        payload_raw: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        await _send_error(ws, ERR_BAD_JSON, f"JSON 디코드 실패: {exc.msg}")
        return peer

    if not isinstance(payload_raw, dict):
        await _send_error(ws, ERR_BAD_JSON, "envelope 는 JSON object 여야 합니다.")
        return peer

    # 와이어 포맷 ``from`` → 내부 표현 ``from_`` 변환
    payload: dict[str, Any] = wire_to_internal(payload_raw)

    # ---- 2) 타입 화이트리스트 검증 --------------------------------------
    msg_type = payload.get("type")
    if not is_valid_client_type(msg_type):
        await _send_error(
            ws,
            ERR_UNKNOWN_TYPE,
            f"허용되지 않은 메시지 타입: {msg_type!r}",
        )
        return peer

    # ---- 3) 타입별 라우팅 ------------------------------------------------
    if msg_type == MSG_JOIN:
        return await _handle_join(ws, peer, payload, registry)
    if msg_type == MSG_LEAVE:
        await _handle_leave(ws, peer, payload, registry)
        return peer
    if msg_type in (MSG_OFFER, MSG_ANSWER, MSG_ICE):
        await _handle_relay(ws, peer, payload, registry)
        return peer

    # 위 화이트리스트 검증에서 걸러져야 하지만 방어적으로 한번 더 처리
    await _send_error(ws, ERR_UNKNOWN_TYPE, f"라우팅 불가 타입: {msg_type!r}")
    return peer


async def _handle_join(
    ws: web.WebSocketResponse,
    peer: Peer | None,
    payload: dict[str, Any],
    registry: RoomRegistry,
) -> Peer | None:
    """JOIN 메시지 처리 — Peer 객체 신규 생성 + RoomRegistry 합류."""
    room_id = payload.get("room")
    peer_id = payload.get("peer_id")
    if not isinstance(room_id, str) or not room_id:
        await _send_error(ws, ERR_MISSING_FIELD, "JOIN: room 필드 누락 또는 무효.")
        return peer
    if not isinstance(peer_id, str) or not peer_id:
        await _send_error(
            ws, ERR_MISSING_FIELD, "JOIN: peer_id 필드 누락 또는 무효."
        )
        return peer

    # 동일 소켓이 두 번 JOIN 하면 이전 방에서 먼저 이탈시킨다 (재합류 허용)
    if peer is not None and peer.room_id is not None:
        await registry.leave(peer.room_id, peer.peer_id)

    new_peer = peer if peer is not None else Peer(peer_id=peer_id, ws=ws)
    # 동일 소켓이 다른 peer_id 로 재JOIN 하는 경우 — 식별자 갱신
    new_peer.peer_id = peer_id
    new_peer.ws = ws

    await registry.join(room_id, new_peer)
    return new_peer


async def _handle_leave(
    ws: web.WebSocketResponse,
    peer: Peer | None,
    payload: dict[str, Any],
    registry: RoomRegistry,
) -> None:
    """LEAVE 메시지 처리 — RoomRegistry 이탈."""
    if peer is None or peer.room_id is None:
        await _send_error(ws, ERR_NOT_JOINED, "LEAVE 이전에 JOIN 필요.")
        return

    room_id = payload.get("room") or peer.room_id
    peer_id = payload.get("peer_id") or peer.peer_id
    if not isinstance(room_id, str) or not isinstance(peer_id, str):
        await _send_error(ws, ERR_MISSING_FIELD, "LEAVE: room/peer_id 무효.")
        return

    await registry.leave(room_id, peer_id)
    # 핸들러 안에서 peer 객체의 room_id 도 None 으로 되돌려 둠
    peer.room_id = None


async def _handle_relay(
    ws: web.WebSocketResponse,
    peer: Peer | None,
    payload: dict[str, Any],
    registry: RoomRegistry,
) -> None:
    """OFFER/ANSWER/ICE 단순 중계 처리.

    서버는 ``sdp`` · ``candidate`` 본문을 파싱하지 않는다 — 화이트리스트 검증된
    타입과 ``to`` 대상 peer 존재 여부만 확인하고 통과시킨다.
    """
    if peer is None or peer.room_id is None:
        await _send_error(ws, ERR_NOT_JOINED, "중계 메시지 이전에 JOIN 필요.")
        return

    to_peer_id = payload.get("to")
    if not isinstance(to_peer_id, str) or not to_peer_id:
        await _send_error(ws, ERR_MISSING_FIELD, "to 필드 누락 또는 무효.")
        return

    msg_type = payload["type"]
    if msg_type in (MSG_OFFER, MSG_ANSWER):
        if not isinstance(payload.get("sdp"), str):
            await _send_error(
                ws, ERR_MISSING_FIELD, f"{msg_type}: sdp 필드 누락 또는 무효."
            )
            return
    elif msg_type == MSG_ICE:
        if not isinstance(payload.get("candidate"), dict):
            await _send_error(
                ws, ERR_MISSING_FIELD, "ICE: candidate 객체 누락 또는 무효."
            )
            return

    ok, err_code = await registry.relay(
        room_id=peer.room_id,
        from_peer_id=peer.peer_id,
        to_peer_id=to_peer_id,
        payload=payload,
    )
    if not ok:
        # registry 에서 받은 코드를 protocol 상수와 매핑
        code = {
            "NOT_JOINED": ERR_NOT_JOINED,
            "PEER_NOT_FOUND": ERR_PEER_NOT_FOUND,
            "ROOM_NOT_FOUND": ERR_ROOM_NOT_FOUND,
        }.get(err_code or "", ERR_PEER_NOT_FOUND)
        await _send_error(ws, code, f"중계 실패: to={to_peer_id}")


async def _send_error(
    ws: web.WebSocketResponse, code: str, message: str
) -> None:
    """ERROR envelope 송신 헬퍼 — 송신 실패는 조용히 무시 (이미 끊긴 소켓)."""
    if ws.closed:
        return
    err_payload: dict[str, Any] = {
        "type": MSG_ERROR,
        "code": code,
        "message": message,
    }
    try:
        await ws.send_str(json.dumps(err_payload, ensure_ascii=False))
    except (ConnectionResetError, RuntimeError) as exc:
        logger.warning("ERROR 응답 송신 실패 code=%s err=%s", code, exc)


def build_routes(app: web.Application, registry: RoomRegistry) -> None:
    """aiohttp app 에 라우트와 RoomRegistry 참조를 바인딩한다.

    ``main.py`` 가 호출하는 진입점.
    """
    app[APP_KEY_REGISTRY] = registry
    app.router.add_get("/ws", handle_ws)
    app.router.add_get("/health", _handle_health)


async def _handle_health(request: web.Request) -> web.Response:
    """단순 health-check 엔드포인트 — 데모 서버 watchdog 용.

    인증 없음, 200 OK + JSON 한 줄. Phase 2 에서 인증·rate limit 도입 시 본
    엔드포인트도 동일 정책으로 hardening 한다 (현재는 TD-1 보류).
    """
    registry: RoomRegistry = request.app[APP_KEY_REGISTRY]
    # 내부 상태 노출은 최소화 — 방 개수만 공개
    # noinspection PyProtectedMember
    room_count = len(registry._rooms)  # type: ignore[attr-defined]
    body = {"status": "ok", "rooms": room_count}
    return web.json_response(body)
