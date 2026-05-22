# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk 메인 윈도우 — QMainWindow 상속 (cycle 139 그룹 채팅 통합).

레이아웃 (cycle 139 갱신):

```
+--------------------------------------------------------------+
| 메뉴바: 설정 · 계정 · 도움말                                  |
+-------------+------------------------------------------------+
| RoomList    | QStackedWidget                                 |
| (sidebar)   |  ├─ [tab idx=0] 1:1 ChatView (직접 메시지)     |
|             |  ├─ [tab idx=1] GroupChatView (현재 방)        |
|             |  └─ [tab idx=2] MemberList (멤버 panel)        |
+-------------+------------------------------------------------+
| StatusBar: 연결 상태 · peer 수                                 |
+--------------------------------------------------------------+
```

cycle 139 변경 요점:

- RoomListWidget 을 좌측 sidebar (QSplitter) 에 배치 + ``room_entered``
  시그널 을 ``_on_room_entered(room_id)`` 슬롯 으로 연결.
- 기존 ChatView (1:1) 는 QStackedWidget 의 첫 페이지 로 보존 — 사용자 가
  "직접 메시지" 액션 으로 회귀 가능 (backward compat).
- GroupChatView 는 ``room_entered`` 시 lazy create + StackedWidget 의
  swap. ``message_send_requested`` 시그널 은 REST POST `/api/rooms/{id}/messages`
  (cycle 141 ``MessagesRestClient``) + WebRTC mesh broadcast (cycle 138
  ``GroupMessageClient.send_message``) 의 dual chain (cycle 142 의 actual
  binding 도달).
- ``members_panel_requested`` 시그널 은 MemberListWidget toggle 진입점.
- RoomsClient (``app.net.rooms_client``) 의 ``list_rooms`` / ``get_room`` 의
  의 호출 wrapper 보유 — main entry 점 에서 주입 (test 의 mock 호환).

본 cycle 의 범위 외 (별개 cycle):

- 실 WebRTC mesh peer connection 의 PeerConnection 의 setup (MeshManager)
- 친구 목록 dropdown 의 InviteDialog 의 main_window 통합
- 메시지 history lazy load (cycle 60 messages_client wrapper) 의 GroupChatView
  pre-fill
- REST POST 의 ack 대기 + retry chain (cycle 142 는 fire-and-forget background
  task 만 — ack chain 은 별개 cycle 의 책임)
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QCoreApplication, Qt, pyqtSlot
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.app_state import AppState
from app.core.config import Config
from app.net.auth_client import AuthClient
from app.ui.add_friend_dialog import AddFriendDialog
from app.ui.chat_view import ChatView
from app.ui.friend_list import FriendListWidget
from app.ui.group_chat_view import GroupChatView
from app.ui.login_dialog import LoginDialog
from app.ui.member_list import MemberListWidget
from app.ui.password_reset_dialog import PasswordResetDialog
from app.ui.room_list import RoomListWidget
from app.ui.settings_dialog import SettingsDialog
from app.ui.signup_dialog import SignupDialog
from app.ui.sound_player import SoundPlayer
from app.ui.status_bar import StatusBar
from app.ui.update_checker import periodic_check
from app.ui.update_dialog import UpdateDialog
from app.updater.version_check import CURRENT_VERSION

# RoomsClient 는 httpx 의존 — 본 module import 차단 회피 의무로 lazy import
# (test collection 환경 의 httpx 부재 graceful — main 진입점 에서 주입)

log = logging.getLogger(__name__)

# 한글 주석: 업데이트 서버 base URL — `.env` 의 `UPDATE_SERVER_URL` override 가능.
# 부재 시 데모 서버 (114.207.112.73:8080) 폴백 — cycle 132 server skeleton 정합.
_DEFAULT_UPDATE_SERVER_URL = "http://114.207.112.73:8080"


# 한글 주석 — cycle 144 i18n production binding helper.
# MainWindow context 의 20 .ts entry 와 정합 의무. 본 module 의 5 file 가
# 동일 helper 패턴 의 의 QCoreApplication.translate 호출.
_tr = lambda src: QCoreApplication.translate("MainWindow", src)


from app.ui._tray_mixin import TrayMixin
from app.ui._friend_search_mixin import FriendSearchMixin
from app.ui._bot_chat_mixin import BotChatMixin
from app.ui._drawer_mixin import DrawerMixin
from app.ui._chat_helper_mixin import ChatHelperMixin
from app.ui._menu_bar_mixin import MenuBarMixin
from app.ui._signaling_mixin import SignalingMixin
from app.ui._room_group_chat_mixin import RoomGroupChatMixin
from app.ui._rest_post_mixin import RestPostMixin
from app.ui._folder_mixin import FolderMixin
from app.ui._chat_header_mixin import ChatHeaderMixin
from app.ui._update_lifecycle_mixin import UpdateLifecycleMixin
from app.ui._auth_chain_mixin import AuthChainMixin
from app.ui._chat_navigation_mixin import ChatNavigationMixin
from app.ui._friend_profile_mixin import FriendProfileMixin
from app.ui._chat_send_mixin import ChatSendMixin
from app.ui._dialog_center_mixin import DialogCenterMixin
from app.ui._menu_actions_mixin import MenuActionsMixin
from app.ui._invite_mixin import InviteMixin
from app.ui._lifecycle_events_mixin import LifecycleEventsMixin
from app.ui._friend_status_mixin import FriendStatusMixin


class MainWindow(TrayMixin, FriendSearchMixin, BotChatMixin, DrawerMixin, ChatHelperMixin, MenuBarMixin, SignalingMixin, RoomGroupChatMixin, RestPostMixin, FolderMixin, ChatHeaderMixin, UpdateLifecycleMixin, AuthChainMixin, ChatNavigationMixin, FriendProfileMixin, ChatSendMixin, DialogCenterMixin, MenuActionsMixin, InviteMixin, LifecycleEventsMixin, FriendStatusMixin, QMainWindow):
    """TooTalk 최상위 윈도우.

    본 위젯은 ``app.core.AppState`` 인스턴스를 보유하여 현재 room/peer_id/
    연결 상태를 추적하고, ``app.ui.chat_view.ChatView`` (1:1) · ``GroupChatView``
    (그룹) · ``MemberListWidget`` 의 상위 컨테이너 역할을 한다.

    cycle 139 — QStackedWidget 의 3 페이지 토글 패턴 +
    RoomListWidget sidebar (QSplitter 좌측 패널).

    Qt slot 내부 동기 코드만 사용하며, 시그널링 IO 는 ``asyncio.create_task``
    를 통해 ``app.net.signaling_client`` 의 코루틴을 예약한다 (정본 §E).
    """

    # QStackedWidget index — 코드 가독성 목적 상수
    _STACK_DIRECT_CHAT: int = 0  # 1:1 ChatView
    _STACK_GROUP_CHAT: int = 1   # GroupChatView (cycle 139 신설)
    _STACK_MEMBERS: int = 2      # MemberListWidget (cycle 139 신설)
    _STACK_FRIENDS: int = 3      # FriendListWidget (cycle 144 신설)

    def __init__(
        self,
        config: Config,
        parent: Optional[QWidget] = None,
        *,
        auth_client: Optional[AuthClient] = None,
        rooms_client: Optional[object] = None,
        messages_client: Optional[object] = None,
        group_message_client: Optional[object] = None,
        friends_client: Optional[object] = None,
        reactions_client: Optional[object] = None,
    ) -> None:
        """초기 위젯 트리 + sidebar + Stacked + 메뉴/StatusBar 배치.

        Parameters
        ----------
        config : Config
            ``.env`` 로딩 결과. signaling_url/stun_url/user_nickname 등.
        parent : QWidget | None
            상위 위젯 (보통 None).
        auth_client : AuthClient | None
            회원가입/로그인 다이얼로그 의 의존성. 주입 의무 (main 진입점).
        rooms_client : RoomsClient | None
            cycle 139 신설 — ``app.net.rooms_client.RoomsClient`` 의 주입.
            None 일 시 RoomList sidebar 의 list_rooms 호출 skip + 빈 placeholder
            행 만 표시 (test 격리 + 인증 미완료 단계 graceful).
        messages_client : MessagesRestClient | None
            cycle 142 신설 — ``app.net.messages_client.MessagesRestClient`` 의 주입.
            그룹 메시지 송신 시 REST POST `/api/rooms/{room_id}/messages` 호출 +
            server 영속화 + audit log 트리거. None 또는 호출 실패 시 mesh-only
            모드 (graceful) — UI 흐름 차단 없음.
        group_message_client : GroupMessageClient | None
            cycle 142 신설 — ``app.net.group_message_client.GroupMessageClient`` 의
            주입 (WebRTC mesh broadcast fan-out). None 일 시 mesh broadcast skip
            (UI echo 만). 정상 환경 의 main 진입점 의 의무 주입.
        friends_client : FriendsClient | None
            cycle 147 신설 — ``app.net.friends_client.FriendsClient`` 의 주입.
            InviteDialog dropdown populate (``list_friends(status="accepted")``)
            + 향후 friend_list page 의 REST 갱신 source. None = manual
            ``set_friends`` 의무 (test 격리 mock 호환).
        """

        super().__init__(parent)
        # cycle 169.530 — __init__ 9 helper split (302 line CRITICAL blocker 회수)
        self._init_state(config, auth_client, rooms_client, messages_client,
                         group_message_client, friends_client, reactions_client)
        self._init_window_properties()
        splitter = self._init_splitter()
        self._init_sidebar_rail(splitter)
        self._init_chat_list_panel(splitter)
        right_panel, right_layout = self._init_right_panel(splitter)
        self._init_input_bar(right_panel, right_layout)
        self._finalize_splitter(splitter, right_panel)
        self._init_status_and_startup_chain()

    # ------------------------------------------------------------------
    # cycle 169.530 — __init__ 9 helper method split (CRITICAL blocker 회수)
    # ------------------------------------------------------------------

    def _init_state(
        self,
        config: Config,
        auth_client,
        rooms_client,
        messages_client,
        group_message_client,
        friends_client,
        reactions_client,
    ) -> None:
        """0) 외부 의존 보관 + state 초기화 + SoundPlayer."""
        self._config: Config = config
        self._state: AppState = AppState.instance()
        self._auth_client = auth_client
        self._rooms_client = rooms_client
        self._messages_client = messages_client
        self._group_message_client = group_message_client
        self._friends_client = friends_client
        self._reactions_client = reactions_client
        self._reactions_poller = None
        self._session_token: Optional[str] = None
        self._current_user_id: Optional[int] = None
        self._auth_token: Optional[str] = None
        self._active_peer_id: Optional[str] = None
        self._current_user_role: str = "member"
        self._group_chat_view: Optional[GroupChatView] = None
        self._current_room_id: Optional[int] = None
        self._last_message_id: Optional[int] = None
        # cycle 169.157 — friend/bot DM history client cache
        self._dm_history: dict[tuple[str, int], list[tuple[str, str, "datetime", bool]]] = {}
        self._active_chat_kind: Optional[str] = None
        self._active_chat_target_id: Optional[int] = None
        # 0-1) 시그니처 사운드 player
        self._sound_player: SoundPlayer = SoundPlayer(config)

    def _init_window_properties(self) -> None:
        """1) 윈도우 기본 속성."""
        self.setWindowTitle("TooTalk")
        self.setMinimumSize(720, 640)

    def _init_splitter(self) -> QSplitter:
        """2) 중앙 QSplitter 3 column container."""
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(
            "QSplitter::handle { background-color: #1F2937; }"
            " QSplitter::handle:hover { background-color: #374151; }"
        )
        return splitter

    def _init_sidebar_rail(self, splitter: QSplitter) -> None:
        """3-1) SidebarRail + FolderList legacy."""
        from app.ui.sidebar_rail import SidebarRail
        self._sidebar_rail = SidebarRail(parent=splitter)
        self._sidebar_rail.tab_clicked.connect(self._on_sidebar_tab_clicked)  # type: ignore[arg-type]
        self._sidebar_rail.hamburger_clicked.connect(self._on_hamburger_clicked)  # type: ignore[arg-type]
        # 한글 주석 — FolderList legacy 보존 (signal backward compat) + hide
        from app.ui.folder_list import FolderList
        self._folder_list = FolderList(parent=self)
        self._folder_list.setVisible(False)
        self._folder_list.folder_selected.connect(self._on_folder_selected)  # type: ignore[arg-type]
        self._sidebar_rail.folder_selected.connect(self._on_folder_selected)  # type: ignore[arg-type]

    def _init_chat_list_panel(self, splitter: QSplitter) -> None:
        """3-2) ChatListPanel + default seed (bot + saved) + RoomList legacy."""
        from app.ui.chat_list_panel import ChatListPanel, ChatListEntry
        self._chat_list_panel = ChatListPanel(parent=splitter)
        self._chat_list_panel.chat_selected.connect(self._on_chat_selected)  # type: ignore[arg-type]
        self._sidebar_rail.tab_clicked.connect(self._chat_list_panel.set_active_tab)  # type: ignore[arg-type]
        # 한글 주석 — 투네이션 고객센터 봇 default seed (사용자 directive)
        default_entries = [
            ChatListEntry(
                kind="bot", target_id=1, name="투네이션 고객센터",
                last_message="안녕하세요. 무엇을 도와드릴까요? 24시간 LLM 상담 chain.",
                last_ts=datetime.now(), unread_count=0, is_pinned=True, is_online=True,
            ),
            ChatListEntry(
                kind="saved", target_id=0, name="저장한 메시지",
                last_message="나에게 메모 + 파일 보관",
                last_ts=datetime.now(), unread_count=0, is_pinned=True, is_online=True,
            ),
        ]
        self._chat_list_panel.set_entries(default_entries)
        self._chat_list_panel.set_active_tab("friends")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._on_chat_selected("bot", 1))
        # RoomListWidget hidden sibling
        self._room_list = RoomListWidget(parent=self)
        self._room_list.setVisible(False)
        self._room_list.room_entered.connect(self._on_room_entered)
        self._room_list.set_rooms([])

    def _init_right_panel(self, splitter: QSplitter):
        """4) right_panel + ChatHeader + QStackedWidget 4 widget."""
        right_panel = QWidget(splitter)
        right_panel.setObjectName("rightPanel")
        right_panel.setStyleSheet(
            "QWidget#rightPanel { background-color: #1a2335; }"
        )
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        # 4-0) ChatHeader
        from app.ui.chat_header import ChatHeader
        self._chat_header = ChatHeader(parent=right_panel)
        self._chat_header.search_clicked.connect(self._on_header_search)  # type: ignore[arg-type]
        self._chat_header.call_clicked.connect(self._on_header_call)  # type: ignore[arg-type]
        self._chat_header.remote_clicked.connect(self._on_header_remote)  # type: ignore[arg-type]
        self._chat_header.menu_clicked.connect(self._on_header_menu)  # type: ignore[arg-type]
        self._chat_header.sidebar_toggled.connect(self._on_header_sidebar_toggle)  # type: ignore[arg-type]
        right_layout.addWidget(self._chat_header)
        self._stacked = QStackedWidget(right_panel)
        right_layout.addWidget(self._stacked, stretch=1)
        # 4-1) ChatView (1:1) idx 0
        self._chat_view = ChatView(
            parent=self._stacked,
            sound_player=self._sound_player,
            reactions_client=self._reactions_client,
        )
        self._chat_view.lazy_load_requested.connect(self._on_lazy_load_requested)  # type: ignore[arg-type]
        try:
            from app.ui.reactions_poller import ReactionsPoller
            self._reactions_poller = ReactionsPoller(
                chat_view=self._chat_view,
                reactions_client=self._reactions_client,
                parent=self,
            )
            self._reactions_poller.start()
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("ReactionsPoller 초기화 실패 graceful — %r", exc)
        self._stacked.addWidget(self._chat_view)
        try:
            self._chat_view.reply_to_message.connect(self._on_chat_reply_requested)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("reply_to_message binding 실패 — %r", exc)
        # 4-2) GroupChatView placeholder idx 1
        self._group_placeholder = QWidget(self._stacked)
        self._stacked.addWidget(self._group_placeholder)
        # 4-3) MemberListWidget idx 2
        self._member_list = MemberListWidget(parent=self._stacked)
        self._stacked.addWidget(self._member_list)
        # 4-4) FriendListWidget idx 3
        self._friend_list = FriendListWidget(parent=self._stacked)
        self._friend_list.set_friends([], viewer_id=0)
        try:
            self._friend_list.friend_chat_clicked.connect(self._on_friend_profile_open)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("friend_chat_clicked binding 실패 — %r", exc)
        self._stacked.addWidget(self._friend_list)
        self._stacked.setCurrentIndex(self._STACK_DIRECT_CHAT)
        return right_panel, right_layout

    def _init_input_bar(self, right_panel, right_layout) -> None:
        """5) InputBar 마이그레이션."""
        from app.ui.input_bar import InputBar
        _ = QCoreApplication.translate("MainWindow", "보내기")
        self._input_bar = InputBar(parent=right_panel)
        self._input_bar.message_sent.connect(self._on_input_message_sent)  # type: ignore[arg-type]
        self._input_bar.file_attached.connect(self._on_input_file_attached)  # type: ignore[arg-type]
        right_layout.addWidget(self._input_bar, stretch=0)
        # 한글 주석 — 기존 호환 binding (legacy attribute)
        self._input_edit = self._input_bar._text_edit
        self._send_button = self._input_bar._send_btn
        self._attach_button = self._input_bar._attach_btn
        self._input_container = self._input_bar

    def _finalize_splitter(self, splitter: QSplitter, right_panel) -> None:
        """6) splitter assemble + StretchFactor + centralWidget."""
        splitter.addWidget(self._sidebar_rail)
        splitter.addWidget(self._chat_list_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 1)
        self._room_list.setParent(self)
        self._room_list.setVisible(False)
        self.setCentralWidget(splitter)

    def _init_status_and_startup_chain(self) -> None:
        """7~10) StatusBar + menu_bar + 초기 안내 + auto-update + tray."""
        self._status_bar = StatusBar(parent=self)
        self.setStatusBar(self._status_bar)
        self._status_bar.setVisible(False)
        self._status_bar.set_connection_state("DISCONNECTED")
        self._status_bar.set_peer_count(0)
        self._build_menu_bar()
        self._chat_view.add_message(
            sender="system",
            text=f"TooTalk 클라이언트 준비 완료 — 닉네임: {self._config.user_nickname}",
            ts=datetime.now(),
            is_self=False,
        )
        self._update_task: Optional[asyncio.Task] = None
        self._current_update_dialog: Optional[UpdateDialog] = None
        self._current_moderation_dialog: Optional[object] = None
        self._start_update_check_task()
        self._tray_icon = None
        self._tray_quit_requested = False
        self._setup_tray_icon()

    # ------------------------------------------------------------------
    # auto-update 백그라운드 task — cycle 139 startup integration
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.526 — auto-update 3 method → app/ui/_update_lifecycle_mixin.py 분리
    # (UpdateLifecycleMixin 상속, codex 2.5 책임 분리 11차 LOW batch)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.520 — 메뉴 구성 + admin moderation chain → app/ui/_menu_bar_mixin.py 분리
    # (MenuBarMixin mixin 상속, 7 method retain)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 계정 슬롯
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.526 — 회원가입/로그인/재설정/로그아웃 6 method →
    # app/ui/_auth_chain_mixin.py 분리 (AuthChainMixin 상속, codex 2.5 11차)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.519 — _fetch_unread_counts → app/ui/_chat_helper_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 144 — 친구 관리 슬롯
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.528 — _on_open_friend_list → _menu_actions_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.526 — _refresh_chat_list_panel → _chat_navigation_mixin.py 분리
    # (ChatNavigationMixin 상속, codex 2.5 11차)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.511 — friend search + pending requests chain → _friend_search_mixin.py 분리
    # (FriendSearchMixin mixin 상속, codex 2.5 책임 분리 2차)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 채팅 슬롯 — 1:1 + 그룹 (cycle 139 추가) + SidebarRail / ChatHeader (cycle 153.4 신설)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.526 — _on_sidebar_tab_clicked → _chat_navigation_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.527 — InputBar 3 slot + _on_send_clicked + _append_dm_message →
    # app/ui/_chat_send_mixin.py 분리 (ChatSendMixin 상속, codex 2.5 12차)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.522 — _post_and_resolve → app/ui/_rest_post_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.527 — _on_friend_profile_open + 4 profile button slot +
    # _lookup_friend_name → app/ui/_friend_profile_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.527 — _profile_message_clicked → _friend_profile_mixin 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.527 — _append_dm_message → _chat_send_mixin 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.519 — _fetch_dm_history → app/ui/_chat_helper_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.522 — _send_saved_message_rest → app/ui/_rest_post_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.529 — _fetch_user_status → _friend_status_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.513 — _send_bot_message → app/ui/_bot_chat_mixin.py 분리
    # (BotChatMixin mixin 상속, codex 2.5 책임 분리 3차)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.527 — _lookup_friend_name + 3 profile button slot →
    # _friend_profile_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.523 — folder CRUD 7 method → app/ui/_folder_mixin.py 분리
    # (FolderMixin mixin 상속, codex 2.5 책임 분리 9차)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.522 — _mark_room_read + _post_mark_read → _rest_post_mixin 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.519 — _kind_room_local → app/ui/_chat_helper_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.519 — _on_lazy_load_requested + _load_local_history →
    # app/ui/_chat_helper_mixin.py 분리 (cycle 169.466/441 origin)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.526 — _on_chat_selected → _chat_navigation_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.525 — _on_header_sidebar_toggle → _chat_header_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.520 — _on_signaling_* 4 slot → app/ui/_signaling_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.514 — _on_hamburger_clicked → app/ui/_drawer_mixin.py 분리
    # (DrawerMixin mixin 상속, codex 2.5 책임 분리 4차)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.528 — _exec_dialog_centered → _dialog_center_mixin.py 분리 (193 line)
    # ------------------------------------------------------------------


    # ------------------------------------------------------------------
    # cycle 169.514 — drawer slot 11종 → app/ui/_drawer_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.525 — ChatHeader + remote dropdown 7 method → _chat_header_mixin
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.521 — _on_group_info + _on_chat_clear + _on_chat_leave →
    # app/ui/_room_group_chat_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.527 — _on_send_clicked → _chat_send_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.521 — _on_room_entered + _on_group_message_send +
    # _dispatch_message_chain + _on_open_members_panel → _room_group_chat_mixin
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.521 — group message dual chain + members panel →
    # app/ui/_room_group_chat_mixin.py 분리 (cycle 142 origin)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 147 — InviteDialog 의 host + invite_requested signal handler
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.529 — open_invite_dialog + _on_invite_failed →
    # app/ui/_invite_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.522 — _on_invite_requested + _dispatch_invite_chain →
    # app/ui/_rest_post_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.528 — _on_open_direct_chat + _on_open_settings_dialog +
    # _on_open_room_dialog + _on_show_about → _menu_actions_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 윈도우 종료 훅
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.509 — tray icon + logout chain → app/ui/_tray_mixin.py 분리
    # (TrayMixin mixin 상속, codex review 2.5 책임 분리 진입)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.529 — resizeEvent + closeEvent →
    # app/ui/_lifecycle_events_mixin.py 분리
    # ------------------------------------------------------------------
