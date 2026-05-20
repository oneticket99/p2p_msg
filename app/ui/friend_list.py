# SPDX-License-Identifier: GPL-3.0-or-later
"""FriendListWidget — 친구 목록 + status badge + 액션 버튼 (cycle 144).

QListWidget 기반. Phase 1 친구 관리 chain 의 UI skeleton — REST /api/friends
응답 의 시각화 + 액션 (수락 / 거절 / 차단 / 삭제) wire.

주요 동작
---------
- ``set_friends(friends, viewer_id)`` — 친구 리스트 + viewer PK 주입.
  pending (수신) 행 = 수락/거절 버튼 + pending (발신) 행 = "요청 중" 표기
  + accepted 행 = 채팅 + 삭제 버튼 + blocked 행 = 차단 해제 버튼.
- Signals — friend_accepted / friend_rejected / friend_removed / friend_chat_clicked
  의 4 시그널 (user_id payload).

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
class FriendItem:
    """FriendListWidget 의 단일 행 데이터.

    Parameters
    ----------
    user_id : int
        관계 owner 의 PK (friends.user_id).
    friend_user_id : int
        관계 peer 의 PK (friends.friend_user_id). 액션 payload.
    friend_username : str
        peer 의 표시명 (users.username).
    status : str
        관계 상태 — pending / accepted / blocked. removed = 본 list 부재.
    nickname : Optional[str]
        owner 의 friend 별명. None = friend_username 폴백.
    is_incoming : bool
        본 row 의 user_id != viewer_id 일 때 True — 수신 pending 요청 (수락/거절 버튼).
    """

    user_id: int
    friend_user_id: int
    friend_username: str
    status: str = "pending"
    nickname: Optional[str] = None
    is_incoming: bool = False


# ─── status badge label helper ──────────────────────────────────────────────


def _status_badge_text(status: str, is_incoming: bool) -> str:
    """status + incoming 의 사용자 가시 라벨 산출."""

    if status == "pending":
        return "[수신 요청]" if is_incoming else "[요청 대기]"
    if status == "accepted":
        return "[친구]"
    if status == "blocked":
        return "[차단]"
    return f"[{status}]"


# ─── Graceful 폴백 ──────────────────────────────────────────────────────────


if not _PYQT_AVAILABLE:  # pragma: no cover

    class FriendListWidget:  # type: ignore[no-redef]
        """PyQt6 부재 시 의 stub."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("PyQt6 미설치 — FriendListWidget 사용 불가")

else:

    class _FriendRow(QWidget):
        """단일 친구 행 위젯 — badge + username + status-specific 액션 버튼."""

        def __init__(
            self,
            friend: FriendItem,
            *,
            accept_callback,
            reject_callback,
            remove_callback,
            chat_callback,
            parent: Optional[QWidget] = None,
        ) -> None:
            super().__init__(parent)
            self._friend = friend

            layout = QHBoxLayout(self)
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(6)

            # 한글 주석: status badge + 이름 영역 — Expanding policy.
            badge_text = _status_badge_text(friend.status, friend.is_incoming)
            self._badge_label = QLabel(badge_text, self)
            self._badge_label.setFixedWidth(80)

            display = friend.nickname or friend.friend_username
            if friend.nickname:
                display = f"{friend.nickname} ({friend.friend_username})"
            self._name_label = QLabel(display, self)
            self._name_label.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )

            layout.addWidget(self._badge_label)
            layout.addWidget(self._name_label, stretch=1)

            # 한글 주석: status 별 액션 버튼 분기.
            target_id = friend.friend_user_id if not friend.is_incoming else friend.user_id

            self.accept_button: Optional[QPushButton] = None
            self.reject_button: Optional[QPushButton] = None
            self.remove_button: Optional[QPushButton] = None
            self.chat_button: Optional[QPushButton] = None

            if friend.status == "pending" and friend.is_incoming:
                # 수신 pending — 수락 / 거절 버튼
                self.accept_button = QPushButton("수락", self)
                self.accept_button.setFixedWidth(54)
                self.accept_button.clicked.connect(
                    lambda _checked=False, uid=target_id: accept_callback(uid)
                )
                self.reject_button = QPushButton("거절", self)
                self.reject_button.setFixedWidth(54)
                self.reject_button.clicked.connect(
                    lambda _checked=False, uid=target_id: reject_callback(uid)
                )
                layout.addWidget(self.accept_button)
                layout.addWidget(self.reject_button)
            elif friend.status == "accepted":
                # accepted — 채팅 + 삭제 버튼
                self.chat_button = QPushButton("채팅", self)
                self.chat_button.setFixedWidth(54)
                self.chat_button.clicked.connect(
                    lambda _checked=False, uid=target_id: chat_callback(uid)
                )
                self.remove_button = QPushButton("삭제", self)
                self.remove_button.setFixedWidth(54)
                self.remove_button.clicked.connect(
                    lambda _checked=False, uid=target_id: remove_callback(uid)
                )
                layout.addWidget(self.chat_button)
                layout.addWidget(self.remove_button)
            elif friend.status == "blocked":
                # blocked — 차단 해제 = 삭제 (status=removed) 의 재사용
                self.remove_button = QPushButton("차단 해제", self)
                self.remove_button.setFixedWidth(74)
                self.remove_button.clicked.connect(
                    lambda _checked=False, uid=target_id: remove_callback(uid)
                )
                layout.addWidget(self.remove_button)
            # pending + 발신 (is_incoming=False) — 액션 부재 (대기 표기 만)

    class FriendListWidget(QListWidget):  # type: ignore[no-redef]
        """친구 목록 + status badge + 액션 wire.

        Signals
        -------
        friend_accepted : pyqtSignal(int)
            수락 버튼 클릭 — sender_user_id (발신자 PK) payload.
        friend_rejected : pyqtSignal(int)
            거절 버튼 클릭 — sender_user_id payload.
        friend_removed : pyqtSignal(int)
            삭제 / 차단 해제 버튼 — peer_user_id payload.
        friend_chat_clicked : pyqtSignal(int)
            채팅 버튼 — peer_user_id payload.
        """

        friend_accepted = pyqtSignal(int)
        friend_rejected = pyqtSignal(int)
        friend_removed = pyqtSignal(int)
        friend_chat_clicked = pyqtSignal(int)

        def __init__(self, parent: Optional[QWidget] = None) -> None:
            super().__init__(parent)
            self._friends: List[FriendItem] = []
            self._viewer_id: int = 0

            self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        # ----------------------------------------------------------------
        # public API
        # ----------------------------------------------------------------

        def set_friends(
            self,
            friends: List[FriendItem],
            *,
            viewer_id: int = 0,
        ) -> None:
            """전체 친구 목록 갱신.

            Parameters
            ----------
            friends : List[FriendItem]
                표시 할 친구 리스트. status + is_incoming 의 caller 결정.
            viewer_id : int
                viewer PK — pending 의 발신/수신 방향 결정 의 caller hint.
            """

            self.clear()
            self._friends = list(friends)
            self._viewer_id = viewer_id

            # cycle 169.100 회수 — placeholder text 부재 (사용자 directive — 플레이스홀더 없이 전부 구현)
            if not self._friends:
                return

            for friend in self._friends:
                row_widget = _FriendRow(
                    friend,
                    accept_callback=self._emit_accept,
                    reject_callback=self._emit_reject,
                    remove_callback=self._emit_remove,
                    chat_callback=self._emit_chat,
                )
                item = QListWidgetItem(self)
                item.setSizeHint(row_widget.sizeHint())
                item.setData(
                    Qt.ItemDataRole.UserRole, friend.friend_user_id
                )
                self.addItem(item)
                self.setItemWidget(item, row_widget)

        def viewer_id(self) -> int:
            """viewer PK getter."""

            return self._viewer_id

        def friend_count(self) -> int:
            """현재 표시 친구 수 getter."""

            return len(self._friends)

        # ----------------------------------------------------------------
        # 내부 헬퍼
        # ----------------------------------------------------------------

        def _emit_accept(self, user_id: int) -> None:
            log.info("[friend_list] accept request user_id=%s", user_id)
            self.friend_accepted.emit(int(user_id))

        def _emit_reject(self, user_id: int) -> None:
            log.info("[friend_list] reject request user_id=%s", user_id)
            self.friend_rejected.emit(int(user_id))

        def _emit_remove(self, user_id: int) -> None:
            log.info("[friend_list] remove request user_id=%s", user_id)
            self.friend_removed.emit(int(user_id))

        def _emit_chat(self, user_id: int) -> None:
            log.info("[friend_list] chat request user_id=%s", user_id)
            self.friend_chat_clicked.emit(int(user_id))
