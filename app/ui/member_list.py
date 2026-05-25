# SPDX-License-Identifier: GPL-3.0-or-later
"""MemberListWidget — 그룹 채팅 방 구성원 목록 + role + online 표시.

QListWidget 기반. 본 cycle 136 의 group chat UI skeleton 4 widget 중 3번째.

주요 동작:

- ``set_members(members, viewer_role)`` — 멤버 리스트 + viewer 자기 자신 의
  role (owner/member) 주입. owner 일 경우 각 member 행 의 우측 "추방"
  버튼 활성.
- ``member_kicked`` 시그널 — 추방 버튼 클릭 시 user_id payload emit.
- ``viewer_role()`` — 현재 viewer 의 role getter.

PyQt6 graceful (ImportError + stub) — 정본 §E 정합.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

# PyQt6 graceful — headless 환경 의 ImportError 차단
try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QPushButton,
        QSizePolicy,
        QWidget,
    )

    _PYQT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYQT_AVAILABLE = False

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MemberItem:
    """MemberListWidget 의 단일 행 데이터.

    Parameters
    ----------
    user_id : int
        users.id (PK). 추방/멘션 등 작업 의 식별자.
    username : str
        표시명 (users.username 또는 닉네임).
    role : str
        "owner" / "member" — 방 안 의 역할.
    is_online : bool
        signaling 의 현재 접속 상태 (online/offline).
    """

    user_id: int
    username: str
    role: str = "member"
    is_online: bool = False


# ----------------------------------------------------------------------
# Graceful 폴백
# ----------------------------------------------------------------------

if not _PYQT_AVAILABLE:  # pragma: no cover

    class MemberListWidget:  # type: ignore[no-redef]
        """PyQt6 부재 시 의 stub."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("PyQt6 미설치 — MemberListWidget 사용 불가")

else:

    class _MemberRow(QWidget):
        """단일 멤버 행 위젯 — username + status dot + (조건부) 추방 버튼.

        본 클래스는 MemberListWidget 안 의 setItemWidget 으로 주입된다.
        """

        def __init__(
            self,
            member: MemberItem,
            *,
            viewer_is_owner: bool,
            kick_callback,
            parent: Optional[QWidget] = None,
        ) -> None:
            super().__init__(parent)
            self._member = member

            layout = QHBoxLayout(self)
            layout.setContentsMargins(10, 6, 10, 6)
            layout.setSpacing(10)

            # cycle 169.837 — 멤버 행 = 친구 검색/초대 행과 동일한 원형 아바타 디자인으로 통합
            # (사용자 directive: 멤버 보기·친구 초대 검색 전부 같은 아바타-행). 기존 "●" 텍스트
            # dot → make_initial_pixmap 원형 아바타(이니셜 + deterministic palette).
            from app.ui._avatar_helper import make_initial_pixmap
            self._avatar = QLabel(self)
            self._avatar.setFixedSize(36, 36)
            self._avatar.setPixmap(make_initial_pixmap(member.username, size=36))
            self._avatar.setStyleSheet("background: transparent;")

            # username + role tag (owner 만 표시)
            display = member.username
            if member.role == "owner":
                display = f"{member.username} (방장)"
            self._name_label = QLabel(display, self)
            self._name_label.setStyleSheet(
                "color: #f3f4f6; font-size: 14px; font-weight: 600; background: transparent;"
            )
            self._name_label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )

            layout.addWidget(self._avatar)
            layout.addWidget(self._name_label, stretch=1)

            # 추방 버튼 — viewer 가 owner 이고 대상이 member 일 때만 표시
            self.kick_button: Optional[QPushButton] = None
            if viewer_is_owner and member.role != "owner":
                self.kick_button = QPushButton("추방", self)
                self.kick_button.setFixedWidth(56)
                self.kick_button.clicked.connect(
                    lambda _checked=False, uid=member.user_id: kick_callback(uid)
                )
                layout.addWidget(self.kick_button)

    class MemberListWidget(QListWidget):  # type: ignore[no-redef]
        """그룹 멤버 목록 — owner 의 추방 권한 분기.

        Signals
        -------
        member_kicked : pyqtSignal(int)
            owner 의 추방 버튼 클릭 시 user_id payload emit.
        """

        member_kicked = pyqtSignal(int)

        def __init__(self, parent: Optional[QWidget] = None) -> None:
            super().__init__(parent)
            self._members: List[MemberItem] = []
            self._viewer_role: str = "member"

            self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        # --------------------------------------------------------------
        # public API
        # --------------------------------------------------------------

        def set_members(
            self, members: List[MemberItem], *, viewer_role: str = "member"
        ) -> None:
            """전체 멤버 목록 갱신.

            Parameters
            ----------
            members : List[MemberItem]
                표시할 멤버 리스트.
            viewer_role : str
                현재 viewer 의 본 방 role ("owner" / "member"). owner 일 때
                각 member 행 의 추방 버튼 표시.
            """

            self.clear()
            self._members = list(members)
            self._viewer_role = viewer_role
            viewer_is_owner = viewer_role == "owner"

            for member in self._members:
                row_widget = _MemberRow(
                    member,
                    viewer_is_owner=viewer_is_owner,
                    kick_callback=self._emit_kick,
                )
                item = QListWidgetItem(self)
                # row widget 의 sizeHint 자동 적용
                item.setSizeHint(row_widget.sizeHint())
                item.setData(Qt.ItemDataRole.UserRole, member.user_id)
                self.addItem(item)
                self.setItemWidget(item, row_widget)

        def viewer_role(self) -> str:
            """현재 viewer 의 role getter."""

            return self._viewer_role

        def member_count(self) -> int:
            """현재 표시 중인 멤버 수 getter."""

            return len(self._members)

        # --------------------------------------------------------------
        # 내부 헬퍼
        # --------------------------------------------------------------

        def _emit_kick(self, user_id: int) -> None:
            """추방 버튼 콜백 — member_kicked emit."""

            log.info("[member_list] kick request user_id=%s", user_id)
            self.member_kicked.emit(int(user_id))
