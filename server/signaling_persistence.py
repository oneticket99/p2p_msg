# SPDX-License-Identifier: GPL-3.0-or-later
"""시그널링 영속화 helper — rooms/peers/messages DB 동기.

기존 server/signaling.py 의 in-memory RoomRegistry 와 DB 의 분리 layer.
signaling.py 의 함수 호출 (dependency injection) — DB 미연결 시 silent skip.

함수:
- persist_room_create — rooms row 생성 (owner_id 첫 peer)
- persist_peer_join — peers row 생성
- persist_peer_leave — peers.left_at 갱신
- persist_text_message — messages row 생성 (kind=text)
- persist_system_event — messages row 생성 (kind=system, 예: join/leave 알림)

모든 함수 = pool=None 허용 (DB 비활성 시 silent skip).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from server.db.repositories import messages as msg_repo
from server.db.repositories import peers as peers_repo
from server.db.repositories import rooms as rooms_repo

log = logging.getLogger(__name__)


async def persist_room_create(
    pool: Optional[Any],
    *,
    room_code: str,
    owner_id: int,
    kind: str = "direct",
) -> Optional[int]:
    """룸 영속화 — DB 비활성 시 None 반환 + skip.

    Returns
    -------
    int | None
        rooms.id 또는 None.
    """

    if pool is None:
        return None
    try:
        room_id = await rooms_repo.insert_room(
            pool, room_code=room_code, owner_id=owner_id, kind=kind
        )
        log.info("[persist] room_create id=%d code=%s owner=%d", room_id, room_code, owner_id)
        return room_id
    except Exception as exc:  # noqa: BLE001 - DB 오류 = 비차단
        log.warning("[persist] room_create FAIL — %r", exc)
        return None


async def persist_peer_join(
    pool: Optional[Any],
    *,
    room_id: int,
    user_id: int,
    role: str = "member",
) -> Optional[int]:
    """참여자 영속화."""

    if pool is None or room_id is None:
        return None
    try:
        peer_id = await peers_repo.insert_peer(
            pool, room_id=room_id, user_id=user_id, role=role
        )
        log.info("[persist] peer_join room=%d user=%d role=%s", room_id, user_id, role)
        return peer_id
    except Exception as exc:  # noqa: BLE001
        log.warning("[persist] peer_join FAIL — %r", exc)
        return None


async def persist_peer_leave(
    pool: Optional[Any],
    *,
    room_id: int,
    user_id: int,
) -> None:
    """leave 시각 갱신 — 영속화 비활성 시 silent skip."""

    if pool is None or room_id is None:
        return
    try:
        await peers_repo.mark_peer_left(pool, room_id=room_id, user_id=user_id)
        log.info("[persist] peer_leave room=%d user=%d", room_id, user_id)
    except Exception as exc:  # noqa: BLE001
        log.warning("[persist] peer_leave FAIL — %r", exc)


async def persist_text_message(
    pool: Optional[Any],
    *,
    room_id: int,
    sender_id: int,
    body: str,
) -> Optional[int]:
    """텍스트 메시지 history 기록."""

    if pool is None or room_id is None:
        return None
    try:
        msg_id = await msg_repo.insert_text_message(
            pool, room_id=room_id, sender_id=sender_id, body=body
        )
        return msg_id
    except Exception as exc:  # noqa: BLE001
        log.warning("[persist] text_message FAIL — %r", exc)
        return None


async def persist_system_event(
    pool: Optional[Any],
    *,
    room_id: int,
    sender_id: int,
    body: str,
) -> Optional[int]:
    """시스템 알림 (join/leave/owner change) 영속화."""

    if pool is None or room_id is None:
        return None
    try:
        msg_id = await msg_repo.insert_system_message(
            pool, room_id=room_id, sender_id=sender_id, body=body
        )
        return msg_id
    except Exception as exc:  # noqa: BLE001
        log.warning("[persist] system_event FAIL — %r", exc)
        return None
