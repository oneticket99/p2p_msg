# SPDX-License-Identifier: GPL-3.0-or-later
"""InviteDialog — 친구 목록 dropdown 으로 그룹 방 초대 송신.

본 cycle 147 갱신 — cycle 136 skeleton 의 placeholder dropdown 을 cycle 144
FriendsClient REST chain 으로 교체. ``FriendsClient.list_friends(status="accepted")``
호출 + 응답 의 ``FriendProfilePayload`` list → dropdown populate. 사용자 선택 +
"초대" 버튼 클릭 시 ``invite_requested(room_id, friend_user_id)`` 시그널 emit.
caller (MainWindow) 가 본 시그널 을 받아 ``RoomsClient.invite_user`` REST 호출.

흐름:

1. caller (MainWindow) 가 ``InviteDialog(room_id, friends_client=..., ...)`` 인스턴스화.
2. ``populate_friends_async`` async helper 가 FriendsClient 호출 + dropdown 채움.
   (or caller 가 ``set_friends`` 로 사전 fetch 한 list 주입 가능 — test mock 호환)
3. 사용자가 friend dropdown 선택 + "초대" 버튼 클릭.
4. 다이얼로그가 ``invite_requested`` 시그널 (room_id, friend_user_id) emit.
5. caller 가 REST ``POST /api/rooms/{id}/invite`` 호출 + 결과 통보.

PyQt6 graceful (ImportError + stub) — 정본 §E 정합.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List, Optional

# 한글 주석 — cycle 169.834 — user-facing 문구 i18n 바인딩 (5언어 labels)
from app.i18n import labels as _i18n_labels

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


def _friends_to_options(friends: List[Any]) -> List[FriendOption]:
    """FriendsClient.list_friends 응답 → FriendOption list 변환.

    ``FriendProfilePayload`` 또는 ``FriendOption`` 둘 다 허용 — duck typing 의무.
    payload 의 ``friend_user_id`` + ``friend_username`` 우선 + 미보유 시
    ``user_id`` + ``username`` 폴백. nickname 가용 시 라벨 prefix.
    """

    options: List[FriendOption] = []
    for friend in friends:
        if isinstance(friend, FriendOption):
            options.append(friend)
            continue
        # 한글 주석: FriendProfilePayload duck typing — friend_user_id + friend_username.
        uid = getattr(friend, "friend_user_id", None)
        if uid is None:
            uid = getattr(friend, "user_id", None)
        username = getattr(friend, "friend_username", None) or getattr(
            friend, "username", None
        )
        if uid is None or not username:
            log.warning("[invite_dialog] friend payload 무효 skip — %r", friend)
            continue
        nickname = getattr(friend, "nickname", None)
        display = f"{nickname} ({username})" if nickname else str(username)
        options.append(FriendOption(user_id=int(uid), username=display))
    return options


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
        invite_failed : pyqtSignal(str)
            populate 또는 invite 단계 의 오류 메시지 — caller 의 status feedback.
        """

        invite_requested = pyqtSignal(int, int)
        invite_failed = pyqtSignal(str)

        def __init__(
            self,
            *,
            room_id: int,
            friends: Optional[List[FriendOption]] = None,
            friends_client: Optional[Any] = None,
            room_title: str = "",
            parent: Optional[QWidget] = None,
        ) -> None:
            """다이얼로그 위젯 트리 구성.

            Parameters
            ----------
            room_id : int
                초대 대상 방 의 식별자.
            friends : List[FriendOption] | None
                사전 fetch 한 친구 목록 — dropdown 항목 으로 즉시 표시.
                None / 빈 list = caller 의 ``populate_friends_async`` 호출 의무
                (또는 friends_client 주입 시 manual fetch).
            friends_client : FriendsClient | None
                cycle 147 신설 — ``app.net.friends_client.FriendsClient`` 의 주입.
                ``populate_friends_async`` 호출 시 의 ``list_friends`` source.
                None = manual ``set_friends`` 의 의무 (test 격리 mock 호환).
            room_title : str
                헤더 표기 — 부재 시 "Room #<id>" 폴백.
            """

            super().__init__(parent)
            self._room_id = room_id
            self._friends: List[FriendOption] = list(friends or [])
            self._friends_client = friends_client

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
            root.addWidget(self._combo)
            self._rebuild_combo()

            # ── 상태 라벨 (populate / 오류 표기) ──────────
            self._status_label = QLabel("", self)
            self._status_label.setWordWrap(True)
            root.addWidget(self._status_label)

            # ── 버튼 줄 ───────────────────────────────────
            btn_row = QHBoxLayout()
            self._cancel_btn = QPushButton("취소", self)
            self._cancel_btn.clicked.connect(self.reject)

            self._invite_btn = QPushButton("초대", self)
            self._invite_btn.setDefault(True)
            self._invite_btn.clicked.connect(self._on_invite_clicked)
            self._refresh_invite_button_state()

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

        def set_friends(self, friends: List[Any]) -> None:
            """dropdown 의 friends list 갱신 — caller 의 외부 fetch 의무 entry.

            ``FriendOption`` 또는 ``FriendProfilePayload`` 호환 (duck typing).
            cycle 147 의 main_window 통합 = ``FriendsClient.list_friends`` 응답
            그대로 본 메서드 의 인자 주입 의 의무.
            """

            self._friends = _friends_to_options(friends)
            self._rebuild_combo()
            self._refresh_invite_button_state()
            log.debug(
                "[invite_dialog] set_friends 갱신 — count=%d", len(self._friends)
            )

        async def populate_friends_async(self) -> None:
            """``FriendsClient.list_friends(status="accepted")`` 호출 + dropdown 갱신.

            friends_client 주입 부재 시 noop + warning. graceful — 예외 발생
            시 ``invite_failed`` 시그널 emit + status 라벨 표기 + dropdown
            현 상태 보존.
            """

            if self._friends_client is None:
                log.warning(
                    "[invite_dialog] friends_client 미주입 — populate skip"
                )
                self._status_label.setText(
                    _i18n_labels.tr("msg_invite_client_unavailable")
                )
                return

            try:
                friends = await self._friends_client.list_friends(
                    status="accepted"
                )
            except Exception as exc:  # noqa: BLE001
                msg = f"친구 목록 조회 실패 — {exc}"
                log.warning("[invite_dialog] %s", msg)
                self._status_label.setText(msg)
                self.invite_failed.emit(msg)
                return

            self.set_friends(friends)
            self._status_label.setText(
                f"친구 {len(self._friends)}명 — 초대할 친구 선택"
            )

        # --------------------------------------------------------------
        # 내부 헬퍼
        # --------------------------------------------------------------

        def _rebuild_combo(self) -> None:
            """현재 ``self._friends`` 기반 dropdown 재구성."""

            self._combo.clear()
            if self._friends:
                for friend in self._friends:
                    # data role 에 user_id 보관 — currentData() 로 조회
                    self._combo.addItem(friend.username, friend.user_id)
                self._combo.setEnabled(True)
            else:
                self._combo.addItem("초대 가능한 친구 없음", None)
                self._combo.setEnabled(False)

        def _refresh_invite_button_state(self) -> None:
            """초대 버튼 활성 토글 — 친구 부재 시 비활성."""

            self._invite_btn.setEnabled(bool(self._friends))

        def _on_invite_clicked(self) -> None:
            """초대 버튼 슬롯 — 선택 검증 + 시그널 emit + accept().

            REST binding (``POST /api/rooms/{id}/invite``) 은 caller 가 본
            시그널 을 받아 처리. cycle 147 의 main_window 통합 = MainWindow
            가 ``rooms_client.invite_user(room_id, friend_user_id)`` 호출.
            """

            friend_id = self.selected_friend_id()
            if friend_id is None:
                from app.ui.confirm_dialog import ConfirmDialog
                ConfirmDialog.show_warning(
                    self, "TooTalk", _i18n_labels.tr("msg_invite_select_friend")
                )
                return

            log.info(
                "[invite_dialog] invite_requested emit room_id=%s friend_id=%s",
                self._room_id,
                friend_id,
            )
            self.invite_requested.emit(int(self._room_id), int(friend_id))
            self.accept()
