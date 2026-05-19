# SPDX-License-Identifier: GPL-3.0-or-later
"""RoomListWidget — 사용자 가 소유 또는 참여 중인 그룹 채팅 방 목록.

QListWidget 기반 + 더블 클릭 진입 신호 (room_id payload). 본 cycle 136 의
group chat UI skeleton 4 widget 중 1번째. PyQt6 graceful (ImportError 시
조용히 stub 반환) — 정본 §E 정합.

주요 동작:

- ``set_rooms(rooms)`` — 외부에서 RoomItem 리스트 주입 + 목록 갱신.
- ``room_entered`` 시그널 — itemDoubleClicked 슬롯이 room_id 를 emit.
- ``current_room_id()`` — 현재 선택 행 의 room_id (없을 시 None).

본 widget 은 View 만 담당. REST 조회 + WebRTC binding 은 외부 caller 의
별도 cycle 책임 (cycle 137+ main_window 통합).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

# PyQt6 graceful — headless 환경 (테스트 collection 등) 의 ImportError 차단
try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QWidget

    _PYQT_AVAILABLE = True
except ImportError:  # pragma: no cover — PyQt6 없는 환경 의 폴백
    _PYQT_AVAILABLE = False

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RoomItem:
    """RoomListWidget 의 단일 행 데이터 컨테이너.

    Parameters
    ----------
    room_id : int
        rooms.id (PK). DataChannel join 대상 식별자.
    room_code : str
        rooms.room_code (사용자 표시용 5~12 자 코드).
    title : str
        UI 표기명 (방장이 지정한 친근한 이름). 부재 시 room_code 폴백.
    role : str
        "owner" / "member" — 사용자 의 본 방 안 역할.
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


# ----------------------------------------------------------------------
# Graceful 폴백 — PyQt6 부재 시 stub 클래스 (테스트 collection 통과)
# ----------------------------------------------------------------------

if not _PYQT_AVAILABLE:  # pragma: no cover

    class RoomListWidget:  # type: ignore[no-redef]
        """PyQt6 부재 시 의 stub — 인스턴스화 시 RuntimeError."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("PyQt6 미설치 — RoomListWidget 사용 불가")

else:

    class RoomListWidget(QListWidget):  # type: ignore[no-redef]
        """그룹 채팅 방 목록 — QListWidget 상속.

        Signals
        -------
        room_entered : pyqtSignal(int)
            행 더블 클릭 시 room_id payload emit.

        Notes
        -----
        - 내부 데이터: ``_rooms`` (List[RoomItem]) — index 가 QListWidgetItem
          row 와 1:1 정렬.
        - 표기 형식: ``[role 약자] title (member_count) · unread``.
        """

        room_entered = pyqtSignal(int)

        def __init__(self, parent: Optional[QWidget] = None) -> None:
            """초기 빈 목록 + 시그널 wire."""

            super().__init__(parent)
            self._rooms: List[RoomItem] = []

            # 단일 선택 + 더블 클릭 진입 trigger
            self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
            self.itemDoubleClicked.connect(self._on_item_double_clicked)

            # 빈 상태 표기 (rooms 부재 시 사용자 안내)
            self._placeholder_text = "참여 중인 방이 없습니다"

        # --------------------------------------------------------------
        # public API
        # --------------------------------------------------------------

        def set_rooms(self, rooms: List[RoomItem]) -> None:
            """전체 방 목록 갱신 — 기존 행 제거 + 신규 일괄 삽입.

            Parameters
            ----------
            rooms : List[RoomItem]
                신규 표시할 방 목록. 빈 리스트 시 placeholder 행 1개 표시.
            """

            self.clear()
            self._rooms = list(rooms)

            if not self._rooms:
                placeholder = QListWidgetItem(self._placeholder_text)
                # 비활성 행 — 클릭 불가
                placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
                self.addItem(placeholder)
                return

            for room in self._rooms:
                label = self._format_row(room)
                item = QListWidgetItem(label)
                # role payload 보관 — 추후 컨텍스트 메뉴 의 분기 근거
                item.setData(Qt.ItemDataRole.UserRole, room.room_id)
                self.addItem(item)

        def current_room_id(self) -> Optional[int]:
            """현재 선택된 행 의 room_id (선택 없으면 None)."""

            row = self.currentRow()
            if row < 0 or row >= len(self._rooms):
                return None
            return self._rooms[row].room_id

        # --------------------------------------------------------------
        # 내부 헬퍼
        # --------------------------------------------------------------

        @staticmethod
        def _format_row(room: RoomItem) -> str:
            """행 표시 문자열 — role 약자 + title + member_count + unread."""

            role_tag = "★" if room.role == "owner" else "·"
            title = room.title or room.room_code
            unread_suffix = f"  ({room.unread} 신규)" if room.unread > 0 else ""
            return f"{role_tag} {title} [{room.member_count}]{unread_suffix}"

        def _on_item_double_clicked(self, item) -> None:
            """더블 클릭 슬롯 — room_id payload 와 함께 room_entered emit."""

            room_id = item.data(Qt.ItemDataRole.UserRole)
            if room_id is None:
                # placeholder 등 의 비유효 행 (방어적 가드)
                return
            log.debug("[room_list] room_entered emit room_id=%s", room_id)
            self.room_entered.emit(int(room_id))
