# SPDX-License-Identifier: GPL-3.0-or-later
"""InviteDialog — 친구 목록 dropdown 으로 그룹 방 초대 송신.

본 cycle 136 의 group chat UI skeleton 4 widget 중 4번째 (마지막).

흐름:

1. caller (MainWindow) 가 ``InviteDialog(room_id, friends, ...)`` 인스턴스화.
2. 사용자가 friend dropdown 선택 + "초대" 버튼 클릭.
3. 다이얼로그가 ``invite_requested`` 시그널 (room_id, friend_user_id) emit.
4. caller 가 REST ``POST /api/rooms/{id}/invite`` 호출 (binding 부재 시
   skeleton 단계에서는 graceful 무시).

PyQt6 graceful (ImportError + stub) — 정본 §E 정합.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

# PyQt6 graceful — headless 환경 의 ImportError 차단
try:
    from PyQt6.QtCore import pyqtSignal
    from PyQt6.QtWidgets import (
        QComboBox,
        QDialog,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    _PYQT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYQT_AVAILABLE = False

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FriendOption:
    """InviteDialog 의 dropdown 단일 항목 데이터.

    Parameters
    ----------
    user_id : int
        users.id (PK).
    username : str
        표시명. dropdown 의 사용자 가시 라벨.
    """

    user_id: int
    username: str


# ----------------------------------------------------------------------
# Graceful 폴백
# ----------------------------------------------------------------------

if not _PYQT_AVAILABLE:  # pragma: no cover

    class InviteDialog:  # type: ignore[no-redef]
        """PyQt6 부재 시 의 stub."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("PyQt6 미설치 — InviteDialog 사용 불가")

else:

    class InviteDialog(QDialog):  # type: ignore[no-redef]
        """그룹 방 초대 다이얼로그.

        Signals
        -------
        invite_requested : pyqtSignal(int, int)
            (room_id, friend_user_id) payload — caller 가 REST 호출.
        """

        invite_requested = pyqtSignal(int, int)

        def __init__(
            self,
            *,
            room_id: int,
            friends: List[FriendOption],
            room_title: str = "",
            parent: Optional[QWidget] = None,
        ) -> None:
            """다이얼로그 위젯 트리 구성.

            Parameters
            ----------
            room_id : int
                초대 대상 방 의 식별자.
            friends : List[FriendOption]
                현재 user 의 친구 목록 — dropdown 항목 으로 표시.
                빈 리스트 일 경우 "초대 가능한 친구 없음" 안내 + 초대 버튼 비활성.
            room_title : str
                헤더 표기 — 부재 시 "Room #<id>" 폴백.
            """

            super().__init__(parent)
            self._room_id = room_id
            self._friends: List[FriendOption] = list(friends)

            display_title = room_title or f"Room #{room_id}"
            self.setWindowTitle(f"TooTalk · 친구 초대 — {display_title}")
            self.setMinimumWidth(360)

            root = QVBoxLayout(self)

            # ── 안내 라벨 ──────────────────────────────────
            heading = QLabel(f"<b>{display_title}</b> 방 에 초대할 친구를 선택하세요.")
            heading.setWordWrap(True)
            root.addWidget(heading)

            # ── friend dropdown ──────────────────────────
            self._combo = QComboBox(self)
            if self._friends:
                for friend in self._friends:
                    # data role 에 user_id 보관 — currentData() 로 조회
                    self._combo.addItem(friend.username, friend.user_id)
            else:
                self._combo.addItem("초대 가능한 친구 없음", None)
                self._combo.setEnabled(False)
            root.addWidget(self._combo)

            # ── 버튼 줄 ───────────────────────────────────
            btn_row = QHBoxLayout()
            self._cancel_btn = QPushButton("취소", self)
            self._cancel_btn.clicked.connect(self.reject)

            self._invite_btn = QPushButton("초대", self)
            self._invite_btn.setDefault(True)
            self._invite_btn.clicked.connect(self._on_invite_clicked)
            if not self._friends:
                self._invite_btn.setEnabled(False)

            btn_row.addStretch(1)
            btn_row.addWidget(self._cancel_btn)
            btn_row.addWidget(self._invite_btn)
            root.addLayout(btn_row)

        # --------------------------------------------------------------
        # public API
        # --------------------------------------------------------------

        @property
        def room_id(self) -> int:
            """초대 대상 room_id getter."""

            return self._room_id

        def selected_friend_id(self) -> Optional[int]:
            """현재 dropdown 선택 friend user_id getter (없으면 None)."""

            data = self._combo.currentData()
            if data is None:
                return None
            return int(data)

        # --------------------------------------------------------------
        # 내부 헬퍼
        # --------------------------------------------------------------

        def _on_invite_clicked(self) -> None:
            """초대 버튼 슬롯 — 선택 검증 + 시그널 emit + accept().

            REST binding (``POST /api/rooms/{id}/invite``) 은 caller 가 본
            시그널 을 받아 처리 — 본 skeleton 의 actual 호출 차단.
            """

            friend_id = self.selected_friend_id()
            if friend_id is None:
                QMessageBox.warning(self, "TooTalk", "친구 선택 의무")
                return

            log.info(
                "[invite_dialog] invite_requested emit room_id=%s friend_id=%s",
                self._room_id,
                friend_id,
            )
            self.invite_requested.emit(int(self._room_id), int(friend_id))
            self.accept()
