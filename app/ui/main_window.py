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


class MainWindow(TrayMixin, FriendSearchMixin, BotChatMixin, DrawerMixin, ChatHelperMixin, MenuBarMixin, SignalingMixin, RoomGroupChatMixin, RestPostMixin, FolderMixin, ChatHeaderMixin, QMainWindow):
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

        # 0) 외부 의존 보관
        self._config: Config = config
        self._state: AppState = AppState.instance()
        self._auth_client: Optional[AuthClient] = auth_client
        self._rooms_client = rooms_client  # cycle 139 RoomsClient (lazy 의존)
        # cycle 142 — messages REST + WebRTC mesh 의 dual chain 의무 의존성
        self._messages_client = messages_client
        self._group_message_client = group_message_client
        # cycle 147 — friends REST client (InviteDialog dropdown populate source)
        self._friends_client = friends_client
        # cycle 159 — reactions_client (app.net.reactions_client) 주입 — graceful 부재 None
        self._reactions_client = reactions_client
        # cycle 164 — ReactionsPoller (30s interval polling fallback)
        self._reactions_poller = None
        self._session_token: Optional[str] = None
        self._current_user_id: Optional[int] = None
        self._auth_token: Optional[str] = None
        # 한글 주석 — cycle 169.59 — 현 active chat 의 peer_id (signaling 의 의 SDP exchange 의 target)
        self._active_peer_id: Optional[str] = None
        # cycle 148 — 현재 user 의 service-wide role (admin / owner / member).
        # admin / owner 만 "관리자" 메뉴 가시 + emoji moderation dialog 진입 path.
        # 로그인 응답 의 role 의 caller 의 set_user_role 갱신 의무 (별개 cycle 의 chain).
        self._current_user_role: str = "member"
        # cycle 139 — 현재 활성 그룹 채팅 방 의 GroupChatView (방 전환 시 swap)
        self._group_chat_view: Optional[GroupChatView] = None
        self._current_room_id: Optional[int] = None
        # cycle 142 — 가장 최근 REST POST 응답 의 message_id capture (UI / 추후 ack chain)
        self._last_message_id: Optional[int] = None
        # cycle 169.157 — friend/bot DM history client cache (kind, target_id) → list[(sender, text, ts, is_self)]
        # chat_selected 시점 replay → chat_view re-populate. server REST fetch chain = 별 cycle 169.158+
        self._dm_history: dict[tuple[str, int], list[tuple[str, str, "datetime", bool]]] = {}
        self._active_chat_kind: Optional[str] = None
        self._active_chat_target_id: Optional[int] = None

        # 0-1) 시그니처 사운드 player — Config 의 sound_* 3 필드 기반 init
        self._sound_player: SoundPlayer = SoundPlayer(config)

        # 1) 윈도우 기본 속성
        self.setWindowTitle("TooTalk")
        self.setMinimumSize(720, 640)  # cycle 139 sidebar 추가로 가로 확장

        # 2) 중앙 위젯 — QSplitter 3 column (rail | room_list | right_panel)
        # cycle 153.4 phase 3 통합 — SidebarRail (64px) + RoomListWidget (220~320px) + ChatHeader + stacked
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setContentsMargins(0, 0, 0, 0)
        # 한글 주석 — cycle 169.52 회수 — splitter handle visible (사용자 directive "구분선 안보여")
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(
            "QSplitter::handle { background-color: #1F2937; }"
            " QSplitter::handle:hover { background-color: #374151; }"
        )

        # 3-1) 좌측 rail — SidebarRail (cycle 153 phase 3 신설)
        # 한글 주석 — 4 tab (👥 친구 + 🏠 방 + 🤖 봇 + ⚙️ 설정) + tab_clicked signal
        from app.ui.sidebar_rail import SidebarRail
        self._sidebar_rail = SidebarRail(parent=splitter)
        self._sidebar_rail.tab_clicked.connect(self._on_sidebar_tab_clicked)  # type: ignore[arg-type]
        # 한글 주석 — cycle 169.56 회수 — 햄버거 menu drawer signal
        self._sidebar_rail.hamburger_clicked.connect(self._on_hamburger_clicked)  # type: ignore[arg-type]

        # 한글 주석 — cycle 169.74 회수 — sidebar_rail + FolderList 통합 single column.
        # 사용자 verbatim "같은 레이아웃에 있어야 하는데 그냥 목업 레이아웃을 새로 붙인걸로밖에".
        # FolderList legacy 보존 (signal backward compat) + splitter 안 hide.
        from app.ui.folder_list import FolderList
        self._folder_list = FolderList(parent=self)
        self._folder_list.setVisible(False)
        self._folder_list.folder_selected.connect(self._on_folder_selected)  # type: ignore[arg-type]
        # sidebar_rail 내부 folder 통합 chain — folder_selected signal direct binding
        self._sidebar_rail.folder_selected.connect(self._on_folder_selected)  # type: ignore[arg-type]

        # 3-2) 중앙 chat list — ChatListPanel (cycle 169.62 신설, telegram desktop align)
        # RoomListWidget legacy 보존 — group chat 진입 chain (room_id) backward compat.
        from app.ui.chat_list_panel import ChatListPanel, ChatListEntry
        self._chat_list_panel = ChatListPanel(parent=splitter)
        self._chat_list_panel.chat_selected.connect(self._on_chat_selected)  # type: ignore[arg-type]
        self._sidebar_rail.tab_clicked.connect(self._chat_list_panel.set_active_tab)  # type: ignore[arg-type]

        # 한글 주석 — cycle 169.99 회수 — 투네이션 고객센터 봇 default seed (사용자 directive)
        # chatlist = 친구 + 그룹톡 + 봇톡 통합 — 기본 entry = 투네이션 고객센터 봇 (LLM 연동)
        from datetime import datetime
        default_entries = [
            ChatListEntry(
                kind="bot",
                target_id=1,
                name="투네이션 고객센터",
                last_message="안녕하세요. 무엇을 도와드릴까요? 24시간 LLM 상담 chain.",
                last_ts=datetime.now(),
                unread_count=0,
                is_pinned=True,
                is_online=True,
            ),
            # cycle 169.323 — 사용자 directive image #86 — "저장한 메시지" 친구 list entry (telegram saved messages 정합)
            ChatListEntry(
                kind="saved",
                target_id=0,
                name="저장한 메시지",
                last_message="나에게 메모 + 파일 보관",
                last_ts=datetime.now(),
                unread_count=0,
                is_pinned=True,
                is_online=True,
            ),
        ]
        self._chat_list_panel.set_entries(default_entries)
        # cycle 169.136 — 채팅 통합 (telegram align) — default tab "friends" = 채팅
        self._chat_list_panel.set_active_tab("friends")
        # cycle 169.182 — startup 시점 default chat 진입 (사용자 critique image #16)
        # 투네이션 고객센터 bot default selected → chat_header name 즉시 출력
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._on_chat_selected("bot", 1))

        # RoomListWidget — 의 의 hide (group chat 진입 시 _on_room_entered 호출 chain backward compat)
        self._room_list = RoomListWidget(parent=self)
        self._room_list.setVisible(False)
        self._room_list.room_entered.connect(self._on_room_entered)
        self._room_list.set_rooms([])

        # 4) 우측 — ChatHeader + QStackedWidget + 입력 영역
        # 한글 주석 — cycle 169.52 회수 — right panel 배경 sidebar 보다 밝게 (사용자 directive)
        right_panel = QWidget(splitter)
        right_panel.setObjectName("rightPanel")
        right_panel.setStyleSheet(
            "QWidget#rightPanel { background-color: #1a2335; }"
        )
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 4-0) ChatHeader top bar (56px) — cycle 153 phase 3 신설
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

        # 4-1) ChatView (1:1) — index 0 (기존 호환 유지)
        self._chat_view = ChatView(
            parent=self._stacked,
            sound_player=self._sound_player,
            reactions_client=self._reactions_client,
        )
        # cycle 169.444 — scroll-up lazy load signal subscribe (사용자 directive)
        self._chat_view.lazy_load_requested.connect(self._on_lazy_load_requested)  # type: ignore[arg-type]
        # cycle 164 — ReactionsPoller 인스턴스 + 시작 (client 부재 시 graceful skip)
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
        self._stacked.addWidget(self._chat_view)  # idx 0
        # cycle 154 — reply_to_message signal → InputBar reply mode chain
        try:
            self._chat_view.reply_to_message.connect(self._on_chat_reply_requested)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("reply_to_message binding 실패 — %r", exc)

        # 4-2) GroupChatView placeholder (lazy) — index 1 의 자리 holder
        # 실제 GroupChatView 는 _on_room_entered 시 신설 + 교체.
        self._group_placeholder = QWidget(self._stacked)
        self._stacked.addWidget(self._group_placeholder)  # idx 1

        # 4-3) MemberListWidget — index 2
        self._member_list = MemberListWidget(parent=self._stacked)
        self._stacked.addWidget(self._member_list)  # idx 2

        # 4-4) FriendListWidget — index 3 (cycle 144 신설)
        # 한글 주석: 메뉴 "계정 → 친구 목록" 진입점 + 친구 추가 dialog 의 host.
        self._friend_list = FriendListWidget(parent=self._stacked)
        self._friend_list.set_friends([], viewer_id=0)  # 빈 placeholder
        # cycle 153.7 — friend chat click → ProfileView modal open chain
        try:
            self._friend_list.friend_chat_clicked.connect(self._on_friend_profile_open)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("friend_chat_clicked binding 실패 — %r", exc)
        self._stacked.addWidget(self._friend_list)  # idx 3

        # 초기 페이지 = 1:1 직접 메시지 (기존 호환)
        self._stacked.setCurrentIndex(self._STACK_DIRECT_CHAT)

        # 5) 입력 영역 — cycle 153.7 본격 InputBar 마이그레이션
        # 한글 주석 — 기존 QLineEdit + 보내기 button row → InputBar widget 교체
        # InputBar = 첨부 + emoji + multi-line + voice + drag&drop 통합 (phase 6 신설)
        from app.ui.input_bar import InputBar
        # 한글 주석 — cycle 169.71 회수 — i18n tr() literal 의 의 input bar 의 tooltip 정합
        _ = QCoreApplication.translate("MainWindow", "보내기")
        self._input_bar = InputBar(parent=right_panel)
        self._input_bar.message_sent.connect(self._on_input_message_sent)  # type: ignore[arg-type]
        self._input_bar.file_attached.connect(self._on_input_file_attached)  # type: ignore[arg-type]
        right_layout.addWidget(self._input_bar, stretch=0)

        # 한글 주석 — 기존 호환 binding (QLineEdit attribute 보존 legacy code path)
        self._input_edit = self._input_bar._text_edit
        self._send_button = self._input_bar._send_btn
        self._attach_button = self._input_bar._attach_btn
        self._input_container = self._input_bar

        # 6) Splitter 3 column 위젯 추가 + 비율 설정
        # 한글 주석 — index 0 rail (fixed) + 1 room_list (resize) + 2 right_panel (flex)
        # cycle 169.100 회수 — telegram desktop align column order
        # leftmost = sidebar_rail (folder + icon + label) + middle = chat_list_panel + right = chat area
        # room_list = hidden sibling (group chat 진입 chain backward compat)
        splitter.addWidget(self._sidebar_rail)
        splitter.addWidget(self._chat_list_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)  # rail fixed narrow
        splitter.setStretchFactor(1, 0)  # chat list panel resizable
        splitter.setStretchFactor(2, 1)  # right_panel flex
        # room_list = parent=self (별도 — hidden + signal chain retain)
        self._room_list.setParent(self)
        self._room_list.setVisible(False)

        self.setCentralWidget(splitter)

        # 7) StatusBar
        self._status_bar = StatusBar(parent=self)
        self.setStatusBar(self._status_bar)
        # cycle 169.100 회수 — production status bar hide (telegram align 정합)
        self._status_bar.setVisible(False)
        self._status_bar.set_connection_state("DISCONNECTED")
        self._status_bar.set_peer_count(0)

        # 8) 메뉴바 (설정 / 계정 / 도움말)
        self._build_menu_bar()

        # 9) 초기 안내 메시지 한 줄 (1:1 ChatView)
        self._chat_view.add_message(
            sender="system",
            text=f"TooTalk 클라이언트 준비 완료 — 닉네임: {config.user_nickname}",
            ts=datetime.now(),
            is_self=False,
        )

        # 10) auto-update periodic_check 백그라운드 task 등록 (cycle 139)
        # cycle 132 (server) + cycle 133 (UpdateDialog) + cycle 134 (release CI)
        # chain 의 startup integration — 시작 시 1회 + 24시간 polling. 신 버전
        # 검출 시 _on_new_version slot 호출 + UpdateDialog instantiation.
        # asyncio loop 부재 환경 (일반 unittest 등) 의 graceful skip.
        self._update_task: Optional[asyncio.Task] = None
        self._current_update_dialog: Optional[UpdateDialog] = None
        # cycle 148 — emoji moderation admin dialog 참조 보관 (gc 회피 + 테스트 가시성)
        self._current_moderation_dialog: Optional[object] = None
        self._start_update_check_task()
        # cycle 169.498 — system tray icon + context menu (사용자 directive 영구).
        # close event override → hide + tray retain. tray RMB → 로그아웃 + TooTalk 종료.
        self._tray_icon = None
        self._tray_quit_requested = False
        self._setup_tray_icon()

    # ------------------------------------------------------------------
    # auto-update 백그라운드 task — cycle 139 startup integration
    # ------------------------------------------------------------------

    def _start_update_check_task(self) -> None:
        """``periodic_check`` 코루틴 의 asyncio task 등록.

        qasync 통합 환경 의 정상 경로 — 시작 시 1회 + 매 24시간 polling.
        running loop 부재 환경 (pytest QApplication only / 순수 unittest) 의
        graceful skip + log.debug. 정상 환경 에서는 task 가 background 살아 있다.
        """

        # 한글 주석: 환경변수 override — Phase 5 productization 시 .env 정합
        server_url = (
            os.environ.get("UPDATE_SERVER_URL", "").strip()
            or _DEFAULT_UPDATE_SERVER_URL
        )

        # 한글 주석: running loop 우선 — qasync 통합 환경 의 정상 경로.
        # 부재 시 graceful skip (running loop 부재 = pytest unittest 환경).
        loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            log.debug(
                "[main_window] asyncio running loop 부재 — auto-update task skip"
            )
            self._update_task = None
            return

        try:
            self._update_task = asyncio.ensure_future(
                periodic_check(server_url, self._on_new_version),
                loop=loop,
            )
            log.info(
                "[main_window] auto-update periodic_check task 등록 — server=%s",
                server_url,
            )
        except RuntimeError as exc:
            # 한글 주석: loop closed 등 의 graceful catch
            log.warning(
                "[main_window] auto-update task 등록 실패 — skip (%r)", exc
            )
            self._update_task = None

    def _on_new_version(self, latest_info: dict) -> None:
        """신 버전 검출 시 ``UpdateDialog`` instantiation + 사용자 GO 대기.

        ``periodic_check`` callback 진입점. UpdateDialog 의 modal 호출 +
        사용자 GO 시 download chain trigger (실 download = Phase 5 본격
        cycle 위탁 — 본 cycle 의 skeleton dialog 표시 까지).

        Parameters
        ----------
        latest_info : dict
            ``check_latest_version`` 응답 — ``{"version": ..., "download_url":
            ..., "sha256": ..., "release_notes": ...}`` 형태.
        """

        latest_version = latest_info.get("version", "(unknown)")
        log.info(
            "[main_window] 신 버전 검출 — current=%s latest=%s",
            CURRENT_VERSION,
            latest_version,
        )
        try:
            dialog = UpdateDialog(
                current_version=CURRENT_VERSION,
                latest_info=latest_info,
                parent=self,
                on_user_go=None,  # 한글 주석: 실 download chain = Phase 5 본격 cycle
            )
            # 한글 주석: dialog 참조 보관 — gc 회피 + 테스트 가시성
            self._current_update_dialog = dialog
            dialog.exec()
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[main_window] UpdateDialog instantiation 실패 — graceful skip (%r)",
                exc,
            )

    def _cancel_update_task(self) -> None:
        """shutdown chain 의 update task cancel + cleanup.

        ``closeEvent`` 진입 시 호출. task 부재 / 이미 종료 시 noop.
        CancelledError 는 정상 종료 신호이므로 swallow.
        """

        if self._update_task is None:
            return
        if self._update_task.done():
            self._update_task = None
            return
        try:
            self._update_task.cancel()
            log.info("[main_window] auto-update task cancel 송신")
        except Exception as exc:  # noqa: BLE001
            log.warning("[main_window] auto-update task cancel 실패 — %r", exc)
        self._update_task = None

    # ------------------------------------------------------------------
    # cycle 169.520 — 메뉴 구성 + admin moderation chain → app/ui/_menu_bar_mixin.py 분리
    # (MenuBarMixin mixin 상속, 7 method retain)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 계정 슬롯
    # ------------------------------------------------------------------

    def _require_auth_client(self) -> Optional[AuthClient]:
        """AuthClient 미주입 시 경고."""

        if self._auth_client is None:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(self, "TooTalk", "AuthClient 미초기화 — main 진입점 의무")
            return None
        return self._auth_client

    @pyqtSlot()
    def _on_open_signup(self) -> None:
        """회원가입 다이얼로그."""

        client = self._require_auth_client()
        if client is None:
            return
        dialog = SignupDialog(client, self)
        dialog.exec()

    @pyqtSlot()
    def _on_open_login(self) -> None:
        """로그인 다이얼로그 — PASS 시 세션 토큰 보관."""

        client = self._require_auth_client()
        if client is None:
            return
        dialog = LoginDialog(client, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._session_token = dialog.token
            self._current_user_id = dialog.user_id
            # cycle 169.271 — 사용자 critique bot 401 root cause trace
            log.warning(
                "[main_window] _session_token set token_present=%s token_len=%d user_id=%s",
                bool(self._session_token), len(self._session_token or ""), self._current_user_id,
            )
            log.info("[main_window] 로그인 PASS user_id=%s", self._current_user_id)
            # cycle 169.107 회수 — login PASS 직후 friend/room server fetch chain
            self._post_login_refresh()
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_info(
                self, "TooTalk", f"로그인 완료. user_id={self._current_user_id}"
            )

    # ------------------------------------------------------------------
    # cycle 169.519 — _fetch_unread_counts → app/ui/_chat_helper_mixin.py 분리
    # ------------------------------------------------------------------

    def _post_login_refresh(self) -> None:
        """login PASS 직후 friend + room server fetch + chat_list_panel populate (cycle 169.107).

        FriendsClient.list_friends + RoomsClient.list_rooms 호출 (async).
        graceful — client 부재 시 default seed 만 표시.
        """
        import asyncio

        async def _fetch_chain() -> None:
            try:
                fc = getattr(self, "_friends_client", None)
                if fc is not None and self._session_token:
                    try:
                        friends = await fc.list_friends(self._session_token, status="accepted")  # type: ignore[attr-defined]
                        self._friend_list.set_friends(friends, viewer_id=self._current_user_id or 0)
                        log.info("[post_login] friends fetch — count=%d", len(friends))
                    except Exception as exc:  # noqa: BLE001
                        log.warning("[post_login] friends fetch fail — %r", exc)
                rc = getattr(self, "_rooms_client", None)
                if rc is not None and self._session_token:
                    try:
                        rooms = await rc.list_rooms(self._session_token)  # type: ignore[attr-defined]
                        if hasattr(self, "_room_list"):
                            self._room_list.set_rooms(rooms)
                        log.info("[post_login] rooms fetch — count=%d", len(rooms))
                    except Exception as exc:  # noqa: BLE001
                        log.warning("[post_login] rooms fetch fail — %r", exc)
            finally:
                self._refresh_chat_list_panel()
                # cycle 169.469 — startup 시점 unread batch fetch fire
                asyncio.ensure_future(self._fetch_unread_counts())
                # cycle 169.500 — startup 시점 pending request count badge 갱신
                asyncio.ensure_future(self._refresh_pending_badge())

        try:
            asyncio.ensure_future(_fetch_chain())
        except Exception as exc:  # noqa: BLE001
            log.warning("[post_login] _fetch_chain spawn fail — %r", exc)
            self._refresh_chat_list_panel()

    @pyqtSlot()
    def _on_open_reset(self) -> None:
        """비밀번호 재설정."""

        client = self._require_auth_client()
        if client is None:
            return
        PasswordResetDialog(client, self).exec()

    @pyqtSlot()
    def _on_logout(self) -> None:
        """세션 토큰 폐기 + LoginDialog re-spawn (cycle 169.498)."""

        from app.ui.confirm_dialog import ConfirmDialog
        if self._session_token is None:
            ConfirmDialog.show_info(self, "TooTalk", "로그인 상태 아님")
            return
        # 한글 주석 — tray menu logout chain 동일 활용
        self._perform_logout_and_relogin()

    # ------------------------------------------------------------------
    # cycle 144 — 친구 관리 슬롯
    # ------------------------------------------------------------------

    def _on_open_friend_list(self) -> None:
        """"친구 목록" 메뉴 슬롯 — FriendListWidget page 활성.

        REST 호출 chain (GET /api/friends) 의 actual binding = 별개 cycle 의 의무.
        본 슬롯 = stacked page 의 토글 + viewer_id 갱신 만.
        """

        viewer_id = self._current_user_id or 0
        self._friend_list.set_friends(
            self._friend_list._friends, viewer_id=viewer_id
        )
        # cycle 169.106 회수 — friend_list 갱신 직후 chat_list_panel populate chain
        self._refresh_chat_list_panel()
        self._stacked.setCurrentIndex(self._STACK_FRIENDS)
        log.info(
            "[main_window] friend_list page 활성 viewer_id=%d", viewer_id
        )

    def _refresh_chat_list_panel(self) -> None:
        """친구 + 방 + 봇 data 의 ChatListEntry 변환 + chat_list_panel populate (cycle 169.106).

        사용자 directive — "chatlist 는 추가된 친구 + 단톡방 + 봇톡 출력".
        default seed (투네이션 고객센터 봇) retain + friend/room 실 data 추가.
        """
        from datetime import datetime
        from app.ui.chat_list_panel import ChatListEntry

        entries: list[ChatListEntry] = []

        # 한글 주석 — 투네이션 고객센터 봇 default (pinned + online)
        entries.append(
            ChatListEntry(
                kind="bot",
                target_id=1,
                name="투네이션 고객센터",
                last_message="안녕하세요. 무엇을 도와드릴까요? 24시간 LLM 상담 chain.",
                last_ts=datetime.now(),
                unread_count=0,
                is_pinned=True,
                is_online=True,
            )
        )

        # 한글 주석 — friend_list 안 friends → ChatListEntry kind=friend 변환
        friends = getattr(self._friend_list, "_friends", [])
        for fr in friends:
            uid = getattr(fr, "user_id", None) or getattr(fr, "id", None) or 0
            name = getattr(fr, "username", None) or getattr(fr, "display_name", None) or f"friend_{uid}"
            online = bool(getattr(fr, "is_online", False) or getattr(fr, "online", False))
            entries.append(
                ChatListEntry(
                    kind="friend",
                    target_id=int(uid),
                    name=str(name),
                    last_message="",
                    last_ts=None,
                    unread_count=0,
                    is_pinned=False,
                    is_online=online,
                )
            )

        # 한글 주석 — room_list 안 rooms → ChatListEntry kind=room 변환
        rooms = getattr(self._room_list, "_rooms", []) if hasattr(self, "_room_list") else []
        for rm in rooms:
            rid = getattr(rm, "room_id", None) or getattr(rm, "id", None) or 0
            rname = getattr(rm, "name", None) or getattr(rm, "title", None) or f"room_{rid}"
            entries.append(
                ChatListEntry(
                    kind="room",
                    target_id=int(rid),
                    name=str(rname),
                    last_message="",
                    last_ts=None,
                    unread_count=0,
                    is_pinned=False,
                    is_online=False,
                )
            )

        self._chat_list_panel.set_entries(entries)
        log.info(
            "[main_window] chat_list_panel refresh — bot=1 friend=%d room=%d",
            len(friends), len(rooms),
        )
        # cycle 169.202 — re-populate 후 active chat retain 또는 default 진입 (사용자 critique image #28)
        if self._active_chat_kind and self._active_chat_target_id is not None:
            try:
                self._chat_list_panel.set_current_chat(
                    self._active_chat_kind, self._active_chat_target_id,
                )
            except Exception:
                pass
        else:
            # 빈 chat default 회피 — 투네이션 고객센터 bot 진입
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._on_chat_selected("bot", 1))

    # ------------------------------------------------------------------
    # cycle 169.511 — friend search + pending requests chain → _friend_search_mixin.py 분리
    # (FriendSearchMixin mixin 상속, codex 2.5 책임 분리 2차)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # 채팅 슬롯 — 1:1 + 그룹 (cycle 139 추가) + SidebarRail / ChatHeader (cycle 153.4 신설)
    # ------------------------------------------------------------------

    @pyqtSlot(str)
    def _on_sidebar_tab_clicked(self, tab_key: str) -> None:
        """SidebarRail tab 변경 — stacked widget index 매핑.

        tab_key ∈ {"friends", "rooms", "bots", "settings"} (telegram align label = 채팅/연락처/통화/설정)
        cycle 169.136 — bot_panel 폐기 + chat_list 통합 (사용자 ack)
        - friends("채팅") = chat_list 통합 view (이미 friend + room + bot entry populate chain — cycle 169.106)
        - rooms("연락처") = friends widget (연락처 list)
        - bots("통화") = call placeholder (Phase 5 actual binding)
        - settings = SettingsDialog modal
        """
        if tab_key == "friends":
            # cycle 169.185 — "모든 대화방" 통합 view (default — chat_list 친구+방+봇 통합)
            # cycle 169.283 — 사용자 critique image #55/56/57 회수 — chat_header clear 폐기 (active chat retain)
            self._stacked.setCurrentIndex(self._STACK_DIRECT_CHAT)
        elif tab_key == "settings":
            # cycle 169.193 — 편집 tab = FolderManageDialog modal (telegram 폴더 편집 — 사용자 directive 회수)
            # cycle 169.230 — dialog main 안 centered + height clamp
            try:
                from app.ui.folder_manage_dialog import FolderManageDialog
                user_folders = getattr(self, "_user_folders", [])
                dialog = FolderManageDialog(user_folders=user_folders, parent=self)
                # cycle 169.369 — folder_create_requested connect chain (사용자 critique image #123/124 '+ 새 폴더 만들기' 무반응 회수)
                dialog.folder_create_requested.connect(self._on_folder_create_requested)  # type: ignore[arg-type]
                dialog.folder_delete_requested.connect(self._on_folder_delete_requested)  # type: ignore[arg-type]
                # cycle 169.381 — folder_edit_requested chain (사용자 critique image #139/140 수정 button)
                dialog.folder_edit_requested.connect(self._on_folder_edit_requested)  # type: ignore[arg-type]
                # cycle 169.373 — active dialog reference retain (만들기 완료 시점 close chain)
                self._active_folder_dialog = dialog
                self._exec_dialog_centered(dialog)
                self._active_folder_dialog = None
            except Exception as exc:  # pragma: no cover - graceful
                log.debug("FolderManageDialog open 실패 graceful — %r", exc)
            self._sidebar_rail.set_active_tab("friends")
            self._on_sidebar_tab_clicked("friends")
            # cycle 169.305 — 사용자 critique image #74/75 — dialog close 後 chat_list_panel 의 visibility 강제 retain
            if hasattr(self, "_chat_list_panel"):
                self._chat_list_panel.show()
                self._chat_list_panel.update()

    @pyqtSlot(str)
    def _on_input_message_sent(self, text: str) -> None:
        """InputBar message_sent → 기존 _on_send_clicked chain dispatch."""
        # 한글 주석 — InputBar 의 QTextEdit 안 text 이미 clear 됨. 기존 logic 호환 의무
        if hasattr(self, "_input_edit"):
            self._input_edit.setPlainText(text)
        self._on_send_clicked()
        if hasattr(self, "_input_edit"):
            self._input_edit.clear()

    @pyqtSlot(list)
    def _on_input_file_attached(self, paths: list) -> None:
        """InputBar file_attached → DataChannel chunk transfer chain (cycle 154.2 actual)."""
        log.info("input file attached — %d file", len(paths))
        # 한글 주석 — cycle 154.2 file_sender 의존 graceful binding
        try:
            file_sender = getattr(self, "_file_sender", None)
            if file_sender is None:
                # 한글 주석 — placeholder ChatView 안 system message render
                from datetime import datetime
                for path in paths:
                    self._chat_view.add_message(
                        sender="system",
                        text=f"📎 첨부 (송신 대기): {path}",
                        ts=datetime.now(),
                        is_self=True,
                    )
                return
            # 한글 주석 — file_sender.send(path) async coroutine chain (cycle 119+ FileSender 정합)
            import asyncio
            for path in paths:
                asyncio.ensure_future(file_sender.send(path))
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("file attached chain 실패 — %r", exc)

    # ------------------------------------------------------------------
    # cycle 169.522 — _post_and_resolve → app/ui/_rest_post_mixin.py 분리
    # ------------------------------------------------------------------

    @pyqtSlot(str, str)
    def _on_chat_reply_requested(self, sender: str, text: str) -> None:
        """ChatView reply_to_message signal → InputBar reply mode set."""
        if hasattr(self, "_input_bar"):
            self._input_bar.set_reply_to(sender, text)

    @pyqtSlot(int)
    def _on_friend_profile_open(self, friend_id: int) -> None:
        """friend chat click → ProfileView modal open (cycle 153.7 신설)."""
        try:
            from app.ui.profile_view import ProfileData, ProfileView
            from PyQt6.QtWidgets import QDialog, QVBoxLayout
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("ProfileView import 실패 — %r", exc)
            return

        # 한글 주석 — friend_list 안 row data 조회 (cycle 144 정의 정합)
        friend_data = next(
            (f for f in getattr(self._friend_list, "_friends", []) if getattr(f, "user_id", None) == friend_id),
            None,
        )
        if friend_data is None:
            log.debug("friend_id %d data 부재 — graceful skip", friend_id)
            return

        # ProfileData mapping (cycle 144 friend dataclass → ProfileData)
        profile = ProfileData(
            user_id=friend_id,
            email=getattr(friend_data, "email", ""),
            username=getattr(friend_data, "username", ""),
            bio=getattr(friend_data, "bio", ""),
            avatar_emoji="👤",
            is_online=getattr(friend_data, "is_online", False),
        )

        modal = QDialog(self)
        modal.setWindowTitle(f"TooTalk · {_tr('프로필')}")
        modal.setMinimumSize(440, 560)
        layout = QVBoxLayout(modal)
        layout.setContentsMargins(0, 0, 0, 0)
        view = ProfileView(parent=modal)
        view.set_profile(profile)
        # cycle 154.2 — 4 button actual binding chain
        view.message_clicked.connect(lambda _uid=friend_id: self._profile_message_clicked(modal, friend_id))  # type: ignore[arg-type]
        view.call_clicked.connect(lambda _uid=friend_id: self._profile_call_clicked(friend_id))  # type: ignore[arg-type]
        view.mute_clicked.connect(lambda _uid=friend_id: self._profile_mute_clicked(friend_id))  # type: ignore[arg-type]
        view.block_clicked.connect(lambda _uid=friend_id: self._profile_block_clicked(modal, friend_id))  # type: ignore[arg-type]
        layout.addWidget(view)
        modal.exec()

    def _profile_message_clicked(self, modal, friend_id: int) -> None:
        """profile 메시지 button → modal close + chat 진입 (cycle 154.2).

        cycle 169.166 — _on_chat_selected redirect (single source chain).
        chat_header set_chat + chat_view clear + DM cache replay + scroll bottom 일괄 처리.
        """
        modal.accept()
        self._on_chat_selected("friend", friend_id)

    def _append_dm_message(
        self,
        kind: str,
        target_id: int,
        sender: str,
        text: str,
        ts: "datetime",
        is_self: bool,
        reply_to: Optional[object] = None,
    ) -> None:
        """cycle 169.160 — DM cache append + active chat 시점 chat_view render single source.

        send chain + receive callback (future cycle) 동일 helper 호출 → cache 정합.
        cycle 169.163 — 1:1 chat (kind="friend" or "bot") sender label suppress (telegram align).
        """
        key = (kind, target_id)
        self._dm_history.setdefault(key, []).append((sender, text, ts, is_self))
        # cycle 169.440 — local SQLite cache write-through (사용자 directive MariaDB 부하 분담)
        # room_id mapping = bot/saved/friend kind 별 별 chain (server REST POST 의 응답 안 msg_id retain 별 cycle)
        # 본 cycle = client-only insert (msg_id 부재 시점 0 — uuid-only retain)
        try:
            from app.db import messages_cache as _mc
            # 한글 주석 — room_id derive: bot=1*10+kind_offset, friend=target_id*100, saved=self_id*100
            self_id = getattr(self, "_current_user_id", None) or 0
            sender_id = self_id if is_self else target_id
            # 한글 주석 — cycle 169.497 — _kind_room_local helper 사용 (공식 통일).
            # 이전 cycle 169.440 의 bot 공식 = target_id * 10 + 2 → cycle 169.444 안 self_id * 10 + 2 swap.
            # _load_local_history 와 read 공식 불일치 회수.
            room_id_local = self._kind_room_local(kind, target_id)
            ts_ms = int(ts.timestamp() * 1000) if ts else 0
            _mc.insert_message(
                msg_id=0,  # server msg_id 부재 — uuid-only path retain
                room_id=room_id_local,
                sender_id=int(sender_id) if sender_id else 1,
                kind="text",
                body=text,
                ts_ms=ts_ms,
                is_self=is_self,
            )
        except Exception as exc:
            log.debug("[append_dm_message] local cache 실패 — %r", exc)
        # cycle 169.174~436 — chat_list entry preview + ts bump (sort + render + unread)
        try:
            active_match = (
                self._active_chat_kind == kind and self._active_chat_target_id == target_id
            )
            log.warning(
                "[append_dm_message] bump fire — kind=%s tid=%s active_kind=%s active_tid=%s match=%s is_self=%s text=%r",
                kind, target_id, self._active_chat_kind, self._active_chat_target_id,
                active_match, is_self, text[:40],
            )
            self._chat_list_panel.bump_entry(
                kind=kind, target_id=target_id,
                last_message=text, last_ts=ts,
                last_sender=sender if not is_self else "나",
                is_self=is_self,
                active_chat_match=active_match,
            )
        except Exception as exc:
            log.warning("[append_dm_message] bump_entry 실패 — %r", exc)
        # cycle 169.437 — peer 수신 시점 sound 실시간 (사용자 directive — 포커싱 무관 의무)
        # active chat 부재 시점도 sound trigger — 메신저 기본 의무
        if not is_self and kind != "saved":
            try:
                sp = getattr(self._chat_view, "_sound_player", None)
                if sp is not None:
                    sp.play_signature()
            except Exception as exc:
                log.debug("[append_dm_message] sound trigger 실패 — %r", exc)
        # active chat 이면 chat_view render
        if self._active_chat_kind == kind and self._active_chat_target_id == target_id:
            try:
                # 1:1 chat = friend/bot/saved kind → sender label suppress (room = retain)
                hide_sender = kind in ("friend", "bot", "saved")
                # cycle 169.430 — saved kind = self DM 의 모든 msg 의 is_self=True 강제 (사용자 critique 회수)
                effective_is_self = True if kind == "saved" else is_self
                self._chat_view.add_message(
                    sender=sender, text=text, ts=ts, is_self=effective_is_self,
                    reply_to=reply_to, hide_sender=hide_sender,
                )
                # cycle 169.165 — send/receive 직후 scroll bottom 자동 (telegram align)
                self._chat_view.scroll_to_bottom()
            except Exception as exc:  # pragma: no cover - graceful
                log.debug("chat_view add_message 실패 — %r", exc)

    # ------------------------------------------------------------------
    # cycle 169.519 — _fetch_dm_history → app/ui/_chat_helper_mixin.py 분리
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.522 — _send_saved_message_rest → app/ui/_rest_post_mixin.py 분리
    # ------------------------------------------------------------------

    async def _fetch_user_status(self, user_id: int) -> None:
        """cycle 169.221 — friend last_seen REST fetch (cycle 169.216 endpoint).

        GET /api/auth/users/{user_id}/status → chat_header status 갱신.
        graceful exception (server 부재 시 기존 fallback retain).
        """
        import aiohttp
        try:
            api_base = getattr(self._config, "api_base", None) or "https://114.207.112.73"
            token = getattr(self, "_session_token", None) or ""
            if not token:
                return
            headers = {"Authorization": f"Bearer {token}"}
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    f"{api_base}/api/auth/users/{user_id}/status",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return
                    data = await resp.json()
                    online = data.get("online", False)
                    last_active = data.get("last_active_at")
            # active chat 의 의 retain 시점만 갱신
            if self._active_chat_kind == "friend" and self._active_chat_target_id == user_id:
                if online:
                    status = "온라인"
                elif last_active:
                    status = f"마지막 접속: {last_active[:16]}"
                else:
                    status = "최근에 접속함"
                name = self._lookup_friend_name(user_id)
                self._chat_header.set_chat(name, status=status)
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("[user_status] fetch 실패 — %r", exc)

    # ------------------------------------------------------------------
    # cycle 169.513 — _send_bot_message → app/ui/_bot_chat_mixin.py 분리
    # (BotChatMixin mixin 상속, codex 2.5 책임 분리 3차)
    # ------------------------------------------------------------------

    def _lookup_friend_name(self, friend_id: int) -> str:
        """cycle 169.154 — friend_id → nickname lookup (friend_list 안 cache 조회).

        nickname > friend_username > "friend #{id}" 폴백 chain.
        """
        try:
            friend = next(
                (f for f in getattr(self._friend_list, "_friends", []) if getattr(f, "user_id", None) == friend_id),
                None,
            )
            if friend:
                return getattr(friend, "nickname", None) or getattr(friend, "friend_username", None) or f"friend #{friend_id}"
        except Exception:  # pragma: no cover - graceful
            pass
        return f"friend #{friend_id}"

    def _profile_call_clicked(self, friend_id: int) -> None:
        """profile 통화 button — cycle 200+ WebRTC SDP entry."""
        log.info("profile call clicked — friend_id=%d cycle 200+ entry", friend_id)

    def _profile_mute_clicked(self, friend_id: int) -> None:
        """profile 음소거 토글 (cycle 154.2)."""
        muted = getattr(self, "_muted_friends", set())
        if friend_id in muted:
            muted.discard(friend_id)
        else:
            muted.add(friend_id)
        self._muted_friends = muted
        log.info("profile mute toggle — friend_id=%d muted=%s", friend_id, friend_id in muted)

    def _profile_block_clicked(self, modal, friend_id: int) -> None:
        """profile 차단 button → friends_client.block endpoint (cycle 154.2)."""
        from app.ui.confirm_dialog import ConfirmDialog
        if ConfirmDialog.ask(self, "TooTalk", f"friend #{friend_id} 차단?"):
            client = getattr(self, "_friends_client", None)
            if client is not None:
                import asyncio
                try:
                    asyncio.ensure_future(client.block(friend_id))  # type: ignore[attr-defined]
                except Exception as exc:  # pragma: no cover - graceful
                    log.debug("block chain 실패 — %r", exc)
            modal.accept()

    @pyqtSlot(str)
    # ------------------------------------------------------------------
    # cycle 169.523 — folder CRUD 7 method → app/ui/_folder_mixin.py 분리
    # (FolderMixin mixin 상속, codex 2.5 책임 분리 9차)
    # ------------------------------------------------------------------

    @pyqtSlot(str, int)
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

    def _on_chat_selected(self, kind: str, target_id: int) -> None:
        """ChatListPanel.chat_selected → group room 진입 또는 friend/bot chat 진입 (cycle 169.62)."""
        log.info("[main_window] chat_selected kind=%s target_id=%d", kind, target_id)
        if kind == "room":
            self._on_room_entered(target_id)
            return
        # 한글 주석 — cycle 169.107 회수 — entry 안 name + status lookup chain
        # cycle 169.159 — telegram align fallback "최근에 접속함" (actual last_seen REST = 별 cycle)
        chat_panel = getattr(self, "_chat_list_panel", None)
        name = f"{kind}:{target_id}"
        status = "최근에 접속함"
        if chat_panel is not None:
            for entry in getattr(chat_panel, "_entries", []):
                if entry.kind == kind and entry.target_id == target_id:
                    name = entry.name
                    status = "온라인" if entry.is_online else "최근에 접속함"
                    break
        self._chat_header.set_chat(name, status=status)
        # cycle 169.221 — friend kind 시점 last_seen REST fetch (cycle 169.216 endpoint 연동)
        # cycle 169.225 — DM history fetch (cycle 169.222 DM room resolve + list_messages)
        if kind == "friend" and target_id > 0:
            import asyncio
            asyncio.ensure_future(self._fetch_user_status(target_id))
            asyncio.ensure_future(self._fetch_dm_history(target_id))
        # cycle 169.411 — saved messages history fetch chain (self DM room resolve server-side)
        if kind == "saved":
            import asyncio
            self_id = getattr(self, "_current_user_id", None)
            if isinstance(self_id, int) and self_id > 0:
                asyncio.ensure_future(self._fetch_dm_history(self_id))
        # cycle 169.454 — bot kind history fetch chain (bot DM room resolve actual binding)
        if kind == "bot":
            import asyncio
            asyncio.ensure_future(self._fetch_bot_history())
        # cycle 169.156~157 — chat 전환 + DM cache replay (image #12 telegram 동작성)
        try:
            # cycle 169.176 — prev active chat 의 scroll offset save (전환 직전)
            self._chat_view.save_scroll_offset()
            self._chat_view.clear_messages()
            self._active_chat_kind = kind
            self._active_chat_target_id = target_id
            # cycle 169.157 — cache replay (server REST fetch = 별 cycle 169.158+)
            # cycle 169.163 — 1:1 chat (friend/bot) sender label suppress propagate
            # cycle 169.441 — local SQLite 우선 replay (in-memory cache 부재 시점 fallback)
            hide_sender = kind in ("friend", "bot", "saved")
            cached = self._dm_history.get((kind, target_id), [])
            if cached:
                for sender, text, ts, is_self in cached:
                    # cycle 169.462 — history replay 시점 sound 차단 (사용자 critique)
                    self._chat_view.add_message(
                        sender, text, ts, is_self=is_self, hide_sender=hide_sender,
                        play_sound=False,
                    )
            else:
                # 한글 주석 — in-memory cache miss → local SQLite history replay (사용자 directive 영속)
                self._load_local_history(kind, target_id)
            # cycle 169.444 — chat_view active room_id 갱신 (lazy load cursor base)
            self._chat_view.set_active_room(self._kind_room_local(kind, target_id))
            # cycle 169.457 — chat focus 시점 모든 peer bubble 자동 읽음 처리 (사용자 directive 정합)
            try:
                self._chat_view.mark_all_bubbles_read()
            except Exception as exc:
                log.debug("[chat_focus] mark_read 실패 — %r", exc)
            # cycle 169.176 — prev offset restore 시도 + 부재 시 bottom fallback
            restored = self._chat_view.restore_scroll_offset(kind, target_id)
            if not restored:
                self._chat_view.scroll_to_bottom()
            # cycle 169.167 — chat_list selected row sync (programmatic 진입 path 정합)
            try:
                self._chat_list_panel.set_current_chat(kind, target_id)
            except Exception:  # pragma: no cover - graceful
                pass
            log.info("[main_window] chat switched — kind=%s target=%d replay=%d restored=%s",
                     kind, target_id, len(cached), restored)
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("chat_view switch 실패 — %r", exc)
        self._stacked.setCurrentIndex(self._STACK_DIRECT_CHAT)
        self._input_container.setVisible(True)

    @pyqtSlot()
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

    def _exec_dialog_centered(self, dialog) -> int:
        """cycle 169.267 — child overlay + backdrop dim + manual modal event loop.

        사용자 directive image #25/27/31 회수 — backdrop rgba(0,0,0,0.5) 의 main rect
        의 dimming layer 추가. dialog 의 z-order 위 backdrop. close 직후 backdrop hide.
        """
        # cycle 169.287 — hide/setParent/setWindowFlags(Widget)/show strict chain (Qt internal cache reset)
        from PyQt6.QtCore import Qt as _Qt, QEventLoop, QEvent
        from PyQt6.QtGui import QKeyEvent, QMouseEvent
        from PyQt6.QtWidgets import QFrame, QSplitter as _QSplitter
        # cycle 169.312 — splitter sizes snapshot (dialog open 시점 chat_list panel collapse 회피)
        _central = self.centralWidget()
        _splitter_sizes: list[int] = []
        if isinstance(_central, _QSplitter):
            _splitter_sizes = _central.sizes()
            log.warning("[dialog_open] splitter sizes captured=%s", _splitter_sizes)
        # cycle 169.314 — active_tab snapshot (folder dialog 후 tab 의 entries filter mismatch → 빈 list 회피)
        _clp_pre = getattr(self, "_chat_list_panel", None)
        _active_tab_pre = getattr(_clp_pre, "_active_tab", "chats") if _clp_pre else "chats"
        log.warning("[dialog_open] active_tab captured=%s", _active_tab_pre)
        # cycle 169.307 — main_window child overlay (centralWidget = splitter, child 시점 panel add 깨짐 회수)
        backdrop = QFrame(self)
        backdrop.setObjectName("dialogBackdrop")
        backdrop.setAutoFillBackground(True)
        backdrop.setStyleSheet(
            "QFrame#dialogBackdrop { background-color: rgba(0, 0, 0, 160); }"
        )
        backdrop.setGeometry(self.rect())
        backdrop.show()
        backdrop.raise_()
        # cycle 169.321 — backdrop click reject chain (사용자 directive image #85 — close button 부재 시 fallback)
        def _backdrop_click(event):
            if event.button() == _Qt.MouseButton.LeftButton:
                if hasattr(dialog, "reject"):
                    dialog.reject()
        backdrop.mousePressEvent = _backdrop_click  # type: ignore[assignment]
        dialog.hide()
        dialog.setParent(self)
        dialog.setWindowFlags(_Qt.WindowType.Widget)
        parent_for_dialog = self
        # cycle 169.299 — debug log 추가 (사용자 critique 의 실 size capture)
        parent_rect = parent_for_dialog.rect()
        log.warning(
            "[dialog_centered] parent_rect=%dx%d dialog initial=%dx%d cls=%s",
            parent_rect.width(), parent_rect.height(),
            dialog.width(), dialog.height(), dialog.__class__.__name__,
        )
        max_w = max(parent_rect.width() - 40, 360)
        max_h = max(parent_rect.height() - 40, 400)
        dlg_w = min(dialog.width(), max_w)
        dlg_h = min(dialog.height(), max_h)
        dialog.setFixedSize(dlg_w, dlg_h)
        dw, dh = dialog.width(), dialog.height()
        log.warning("[dialog_centered] after setFixedSize=%dx%d", dw, dh)
        x = (parent_rect.width() - dw) // 2
        y = (parent_rect.height() - dh) // 2
        dialog.move(x, y)
        # cycle 169.302 — signal connect chain (bound method override snapshot 회피)
        loop = QEventLoop()
        dialog._embed_result = 0
        accepted_sig = getattr(dialog, "accepted", None)
        rejected_sig = getattr(dialog, "rejected", None)
        def _on_accepted():
            dialog._embed_result = 1
            loop.quit()
        def _on_rejected():
            dialog._embed_result = 0
            loop.quit()
        if accepted_sig is not None and hasattr(accepted_sig, "connect"):
            accepted_sig.connect(_on_accepted)
        if rejected_sig is not None and hasattr(rejected_sig, "connect"):
            rejected_sig.connect(_on_rejected)
        # 한글 주석 — QDialog fallback (signal 부재 시 method override)
        if accepted_sig is None:
            orig_accept = dialog.accept
            def _accept():
                dialog._embed_result = 1
                try:
                    orig_accept()
                except Exception:
                    pass
                loop.quit()
            dialog.accept = _accept
        if rejected_sig is None:
            orig_reject = dialog.reject
            def _reject():
                dialog._embed_result = 0
                try:
                    orig_reject()
                except Exception:
                    pass
                loop.quit()
            dialog.reject = _reject
        # cycle 169.321 — ESC key handler (FramelessWindowHint 시점 의 QDialog 기본 ESC 회복)
        _orig_keyPress = getattr(dialog, "keyPressEvent", None)
        def _key_press(event):
            if event.key() == _Qt.Key.Key_Escape:
                if hasattr(dialog, "reject"):
                    dialog.reject()
                return
            if _orig_keyPress is not None:
                _orig_keyPress(event)
        dialog.keyPressEvent = _key_press  # type: ignore[assignment]
        dialog.show()
        dialog.raise_()
        dialog.setFocus()
        # cycle 169.351 — child widget visible 강제 (QStackedWidget 등 nested widget 시점 obscure 차단)
        log.warning("[dialog_centered] dialog.isVisible=%s size=%dx%d pos=(%d,%d) children=%d",
                    dialog.isVisible(), dialog.width(), dialog.height(),
                    dialog.x(), dialog.y(), len(dialog.findChildren(QWidget)))
        for child in dialog.findChildren(QWidget):
            child.show()
        dialog.update()
        dialog.repaint()
        loop.exec()
        dialog.hide()
        dialog.setParent(None)  # cycle 169.307 — dialog widget tree 분리 (close 後 main_window layout 회복)
        result = dialog._embed_result
        backdrop.hide()
        backdrop.deleteLater()
        # cycle 169.311 — close 後 strict restore + debug log
        clp = getattr(self, "_chat_list_panel", None)
        if clp is not None:
            entries_count = len(getattr(clp, "_entries", []))
            log.warning(
                "[dialog_close] chat_list_panel entries=%d visible=%s parent=%s",
                entries_count, clp.isVisible(), clp.parent().__class__.__name__ if clp.parent() else None,
            )
            clp.show()
            inner_list = getattr(clp, "_list", None)
            if inner_list is not None:
                inner_list.show()
                inner_list.setVisible(True)
            empty_label = getattr(clp, "_empty_label", None)
            # cycle 169.314 — active_tab restore (dialog open 직전 snapshot) + _render() 재호출
            if hasattr(clp, "set_active_tab"):
                try:
                    clp.set_active_tab(_active_tab_pre)
                    log.warning("[dialog_close] active_tab restored=%s actual=%s",
                                _active_tab_pre, getattr(clp, "_active_tab", "?"))
                except Exception:
                    pass
            if hasattr(clp, "_render"):
                try:
                    clp._render()
                except Exception:
                    pass
            clp.update()
            clp.repaint()
        # cycle 169.312 — splitter sizes restore (chat_list panel width 0 collapse 차단)
        if _splitter_sizes:
            _central2 = self.centralWidget()
            if isinstance(_central2, _QSplitter):
                _central2.setSizes(_splitter_sizes)
                log.warning("[dialog_close] splitter sizes restored=%s actual=%s",
                            _splitter_sizes, _central2.sizes())
        if self.centralWidget():
            self.centralWidget().update()
            self.centralWidget().repaint()
        self.update()
        return result

    # ------------------------------------------------------------------
    # cycle 169.514 — drawer slot 11종 → app/ui/_drawer_mixin.py 분리
    # ------------------------------------------------------------------

    @pyqtSlot()
    @pyqtSlot()
    # ------------------------------------------------------------------
    # cycle 169.525 — ChatHeader + remote dropdown 7 method → _chat_header_mixin
    # ------------------------------------------------------------------

    @pyqtSlot()
    # ------------------------------------------------------------------
    # cycle 169.521 — _on_group_info + _on_chat_clear + _on_chat_leave →
    # app/ui/_room_group_chat_mixin.py 분리
    # ------------------------------------------------------------------

    @pyqtSlot()
    def _on_send_clicked(self) -> None:
        """보내기 버튼 / Enter 키 슬롯 — 1:1 ChatView 의 의무.

        그룹 채팅 모드 (StackedWidget idx == GROUP) 일 때는 GroupChatView 의
        내부 입력창 의 책임 — 본 슬롯 은 echo 차단.
        """

        # cycle 139 — 그룹 모드 active 시 1:1 입력 차단
        if self._stacked.currentIndex() != self._STACK_DIRECT_CHAT:
            return

        # 한글 주석 — cycle 153.7 InputBar 마이그레이션 — QTextEdit `toPlainText()` 우선
        # legacy QLineEdit `text()` fallback graceful
        try:
            text = self._input_edit.toPlainText().strip()
        except AttributeError:
            text = self._input_edit.text().strip()
        if not text:
            return

        # cycle 154.3 — reply context snapshot + InputBar clear
        reply_ctx = None
        if hasattr(self, "_input_bar"):
            ctx = self._input_bar.reply_context()
            if ctx is not None:
                # 한글 주석 — ReplyContext dataclass (message_bubble) 의 instance 생성
                from app.ui.message_bubble import ReplyContext
                reply_ctx = ReplyContext(original_sender=ctx[0], original_text=ctx[1])
            self._input_bar.clear_reply_to()

        ts_now = datetime.now()
        # cycle 169.160 — single source helper _append_dm_message 호출 (active 시점 chat_view 동시 render)
        if self._active_chat_kind and self._active_chat_target_id is not None:
            self._append_dm_message(
                self._active_chat_kind,
                self._active_chat_target_id,
                self._config.user_nickname,
                text,
                ts_now,
                True,
                reply_to=reply_ctx,
            )
            # cycle 169.203 — bot kind 의 LLM 응답 chain (사용자 critique image #29)
            if self._active_chat_kind == "bot":
                import asyncio
                asyncio.ensure_future(self._send_bot_message(text))
        else:
            # active chat 부재 fallback — 기존 chat_view direct render
            self._chat_view.add_message(
                sender=self._config.user_nickname,
                text=text,
                ts=ts_now,
                is_self=True,
                reply_to=reply_ctx,
            )
        self._input_edit.clear()

        # cycle 161~163 — mesh_manager broadcast + server REST POST chain
        # MessagePayload v1.0 + ReplyToField + uuid → bubble mapping + server message_id resolve
        try:
            from app.net.message_protocol import ReplyToField, build_text_payload
            proto_reply = None
            if reply_ctx is not None:
                proto_reply = ReplyToField(
                    message_id="",
                    sender=reply_ctx.original_sender,
                    preview=reply_ctx.original_text[:60],
                )
            payload = build_text_payload(
                sender=self._config.user_nickname,
                text=text,
                reply_to=proto_reply,
            )

            # cycle 163 — client uuid → bubble mapping 등록
            try:
                self._chat_view.register_pending_bubble(payload.id)
            except Exception:  # pragma: no cover - graceful
                pass

            import asyncio
            # cycle 169.411 — saved kind 의 의 mesh skip + self DM REST POST chain
            if self._active_chat_kind == "saved":
                asyncio.ensure_future(self._send_saved_message_rest(text, payload.id))
            else:
                # 한글 주석 — mesh broadcast (DataChannel fan-out, ≤ 8 peer)
                mesh = getattr(self, "_mesh_manager", None)
                if mesh is not None:
                    asyncio.ensure_future(mesh.broadcast_payload(payload))

                # cycle 163 — server REST POST + message_id resolve chain
                msg_client = getattr(self, "_messages_client", None)
                current_room = getattr(self, "_current_room_id", None)
                if msg_client is not None and current_room:
                    asyncio.ensure_future(
                        self._post_and_resolve(msg_client, current_room, text, payload.id)
                    )
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("send chain 실패 graceful — %r", exc)

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

    def open_invite_dialog(self, room_id: Optional[int] = None) -> Optional[object]:
        """InviteDialog 의 instantiation + friends_client populate chain.

        Parameters
        ----------
        room_id : int | None
            초대 대상 room. None = ``self._current_room_id`` 폴백. 부재 시 noop.

        Returns
        -------
        InviteDialog | None
            인스턴스 (caller 의 exec 의무 — test 가시성 확보).
            ``self._current_room_id`` 부재 시 None.

        Notes
        -----
        - friends_client 주입 부재 시 = dialog instantiation 만 (빈 dropdown).
        - rooms_client 부재 시 = invite_requested 시그널 발생 후 graceful skip.
        - 실 exec() 은 caller 책임 — test 의 modal 차단 회피.
        """

        from app.ui.invite_dialog import InviteDialog  # 한글 주석: lazy import (graceful)

        target_room_id = room_id if room_id is not None else self._current_room_id
        if target_room_id is None or target_room_id <= 0:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(self, "TooTalk", "초대 = 그룹 방 진입 의무")
            return None

        dialog = InviteDialog(
            room_id=target_room_id,
            friends_client=self._friends_client,
            room_title=f"Room #{target_room_id}",
            parent=self,
        )
        # 한글 주석: invite_requested → rooms_client.invite_user REST chain
        dialog.invite_requested.connect(self._on_invite_requested)
        dialog.invite_failed.connect(self._on_invite_failed)

        # 한글 주석: friends_client 가용 시 async populate task 등록 (graceful skip)
        if self._friends_client is not None:
            loop: Optional[asyncio.AbstractEventLoop] = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None:
                asyncio.ensure_future(
                    dialog.populate_friends_async(), loop=loop
                )
            else:
                log.debug(
                    "[main_window] asyncio running loop 부재 — populate skip"
                )

        log.info(
            "[main_window] invite_dialog 인스턴스화 room_id=%s friends_client=%s",
            target_room_id,
            bool(self._friends_client),
        )
        return dialog

    # ------------------------------------------------------------------
    # cycle 169.522 — _on_invite_requested + _dispatch_invite_chain →
    # app/ui/_rest_post_mixin.py 분리
    # ------------------------------------------------------------------

    @pyqtSlot(str)
    def _on_invite_failed(self, message: str) -> None:
        """InviteDialog 의 invite_failed 시그널 핸들러 — status bar feedback.

        populate 단계 (friends_client.list_friends FAIL) 의 message 전달.
        """

        log.warning("[main_window] invite_failed — %s", message)
        self._status_bar.showMessage(message, 4000)

    @pyqtSlot()
    def _on_open_direct_chat(self) -> None:
        """1:1 직접 메시지 페이지 회귀 (cycle 139 신설)."""

        self._stacked.setCurrentIndex(self._STACK_DIRECT_CHAT)
        self._input_container.setVisible(True)
        log.debug("[main_window] direct chat 페이지 진입")

    # ------------------------------------------------------------------
    # 설정/방 다이얼로그
    # ------------------------------------------------------------------

    @pyqtSlot()
    def _on_open_settings_dialog(self) -> None:
        """환경설정 다이얼로그 — 시그니처 사운드 음소거/볼륨 즉시 반영.

        cycle 169.250 — _exec_dialog_centered apply (main embed center + 사용자 critique image #10 회수).
        """

        dialog = SettingsDialog(sound_player=self._sound_player, parent=self)
        result = self._exec_dialog_centered(dialog)
        log.debug("SettingsDialog 종료 — result=%s", result)

    @pyqtSlot()
    def _on_open_room_dialog(self) -> None:
        """"방 입장" 다이얼로그 — room_id + peer_id 입력 (기존 호환)."""

        room_id, ok1 = QInputDialog.getText(
            self,
            "방 입장",
            "Room ID 를 입력하세요:",
            QLineEdit.EchoMode.Normal,
            self._state.room_id or "demo",
        )
        if not ok1 or not room_id.strip():
            return

        peer_id, ok2 = QInputDialog.getText(
            self,
            "방 입장",
            "Peer ID (self 식별자) 를 입력하세요:",
            QLineEdit.EchoMode.Normal,
            self._state.peer_id or self._config.user_nickname,
        )
        if not ok2 or not peer_id.strip():
            return

        self._state.set_identity(room_id=room_id.strip(), peer_id=peer_id.strip())
        log.info(
            "방 입장 의도 등록 — room=%s peer=%s (실 연결은 Task #16 에서)",
            room_id,
            peer_id,
        )
        self._chat_view.add_message(
            sender="system",
            text=f"방 입장 의도 등록: room={room_id} · peer={peer_id}",
            ts=datetime.now(),
            is_self=False,
        )

    @pyqtSlot()
    def _on_show_about(self) -> None:
        """About 다이얼로그 — 서비스명·버전·라이선스 안내."""

        from app import __version__ as app_version
        from app.ui.confirm_dialog import ConfirmDialog

        ConfirmDialog.show_info(
            self,
            "TooTalk 정보",
            (
                f"TooTalk\n버전: {app_version}\n\n"
                "PyQt6 기반 데스크탑 P2P 메신저 (WebRTC DataChannel 직결).\n"
                "코드명: p2p_msg · Phase 1 MVP"
            ),
        )

    # ------------------------------------------------------------------
    # 윈도우 종료 훅
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # cycle 169.509 — tray icon + logout chain → app/ui/_tray_mixin.py 분리
    # (TrayMixin mixin 상속, codex review 2.5 책임 분리 진입)
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802 — Qt 규약
        """윈도우 resize 시점 훅 — drawer geometry 동기 (사용자 directive image #26).

        cycle 169.500 — main window resize → active drawer height 동시 갱신 의무.
        drawer setGeometry 가 init 1 회만 — resize 시점 stale.
        """
        super().resizeEvent(event)
        try:
            drawer = getattr(self, "_active_drawer", None)
            if drawer is not None and hasattr(drawer, "isVisible") and drawer.isVisible():
                sidebar_w = self._sidebar_rail.width() if hasattr(self, "_sidebar_rail") else 96
                # 한글 주석 — cycle 169.501 — self.height() (full client area) 사용 — central.height() cut 회수
                drawer.setGeometry(sidebar_w, 0, drawer.width(), self.height())
        except Exception as exc:  # noqa: BLE001
            log.debug("[resize] drawer 동기 실패 — %r", exc)

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt 규약
        """윈도우 종료 시점 훅.

        cycle 139 — auto-update background task 의 cancel + cleanup.
        cycle 169.498 — close button = hide + tray retain (사용자 directive).
        tray menu "TooTalk 종료" 만 본격 quit chain.
        """
        # 한글 주석 — tray 가용 + quit 명시 부재 시점 hide + ignore (tray retain)
        if (
            not self._tray_quit_requested
            and self._tray_icon is not None
            and self._tray_icon.isVisible()
        ):
            event.ignore()
            self.hide()
            try:
                # 한글 주석 — 첫 hide 시점 사용자 안내 balloon (1회만)
                if not getattr(self, "_tray_hint_shown", False):
                    from PyQt6.QtWidgets import QSystemTrayIcon
                    self._tray_icon.showMessage(
                        "TooTalk",
                        "트레이 안 retain 됐다. RMB 클릭 → 로그아웃/종료.",
                        QSystemTrayIcon.MessageIcon.Information,
                        3000,
                    )
                    self._tray_hint_shown = True
            except Exception:
                pass
            return
        log.info("MainWindow 종료 — Qt 이벤트 루프 정리 단계 진입")
        # 한글 주석: auto-update background task 정상 cancel (cycle 139)
        self._cancel_update_task()
        super().closeEvent(event)
