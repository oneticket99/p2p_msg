# SPDX-License-Identifier: GPL-3.0-or-later
"""RoomItem — 그룹 채팅 방 행 데이터 컨테이너 (dataclass).

cycle 169.848 M5b — 구 ``RoomListWidget`` (방번호 입력 sidebar)은 room broadcast
→ 통합 ChatView 마이그레이션으로 물리 회수. room 적재는 ``_rooms_cache`` +
``ChatListPanel`` 통합 entry 로 수렴 (``_refresh_chat_list_panel``). 본 모듈은
``app/main.py`` 의 room 적재 chain 이 사용하는 ``RoomItem`` dataclass 만 보존한다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoomItem:
    """room 적재 chain (``app/main.py``)의 단일 방 데이터 컨테이너.

    Parameters
    ----------
    room_id : int
        rooms.id (PK). DataChannel join 대상 식별자.
    room_code : str
        rooms.room_code (사용자 표시용 5~12 자 코드).
    title : str
        UI 표기명 (방장이 지정한 친근한 이름). 부재 시 room_code 폴백.
    role : str
        "owner" / "member" — 사용자의 본 방 안 역할.
    member_count : int
        현재 방 구성원 수 (online + offline 합산).
    unread : int
        미확인 메시지 수. 0 이상 (기본 0).
    """

    room_id: int
    room_code: str
    title: str = ""
    role: str = "member"
    member_count: int = 0
    unread: int = 0
