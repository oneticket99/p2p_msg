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


class MainWindow(QMainWindow):
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
    # 메뉴 구성
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        """상단 메뉴바 구성 — "설정" + "계정" + "도움말" 3 진입점."""

        menubar = self.menuBar()

        # 한글 주석 — "설정" .ts entry tr() (5 locale: Settings/設定/设置/設定/設定).
        menu_settings = menubar.addMenu(_tr("설정"))

        act_room = QAction("방 입장…", self)
        act_room.setShortcut(QKeySequence("Ctrl+R"))
        act_room.triggered.connect(self._on_open_room_dialog)
        menu_settings.addAction(act_room)

        # cycle 139 — 1:1 직접 메시지 회귀 액션
        # 한글 주석 — "메시지" .ts entry tr() + "직접 " prefix 결합.
        act_direct = QAction(f"직접 {_tr('메시지')}", self)
        act_direct.setShortcut(QKeySequence("Ctrl+D"))
        act_direct.triggered.connect(self._on_open_direct_chat)
        menu_settings.addAction(act_direct)

        # 한글 주석 — "환경" + "설정" .ts entry 결합 (설정 tr() 의 매핑 활용).
        act_pref = QAction(f"환경{_tr('설정')}…", self)
        act_pref.setShortcut(QKeySequence("Ctrl+,"))
        act_pref.triggered.connect(self._on_open_settings_dialog)
        menu_settings.addAction(act_pref)

        menu_settings.addSeparator()

        act_quit = QAction("종료", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        menu_settings.addAction(act_quit)

        # "계정" 메뉴
        menu_account = menubar.addMenu("계정")

        # 한글 주석 — "회원가입" .ts entry tr() + "…" suffix.
        act_signup = QAction(f"{_tr('회원가입')}…", self)
        act_signup.triggered.connect(self._on_open_signup)
        menu_account.addAction(act_signup)

        # 한글 주석 — "로그인" .ts entry tr() + "…" suffix.
        act_login = QAction(f"{_tr('로그인')}…", self)
        act_login.setShortcut(QKeySequence("Ctrl+L"))
        act_login.triggered.connect(self._on_open_login)
        menu_account.addAction(act_login)

        # 한글 주석 — "비밀번호" .ts entry tr() + " 재설정…" suffix.
        act_reset = QAction(f"{_tr('비밀번호')} 재설정…", self)
        act_reset.triggered.connect(self._on_open_reset)
        menu_account.addAction(act_reset)

        menu_account.addSeparator()

        # cycle 144 — 친구 관리 진입점 2 actions (목록 + 추가).
        act_friend_list = QAction("친구 목록", self)
        act_friend_list.triggered.connect(self._on_open_friend_list)
        menu_account.addAction(act_friend_list)

        act_friend_add = QAction("친구 추가…", self)
        act_friend_add.triggered.connect(self._on_open_add_friend)
        menu_account.addAction(act_friend_add)

        menu_account.addSeparator()

        act_logout = QAction("로그아웃", self)
        act_logout.triggered.connect(self._on_logout)
        menu_account.addAction(act_logout)

        # cycle 148 — "관리자" 메뉴 (admin / owner role 만 가시).
        # _current_user_role 의 admin/owner 일 때만 메뉴 신설 + emoji moderation 항목.
        # 비-admin user 의 메뉴 의 외부 노출 차단 — UX 정합 + 보안 의 1차 차단.
        self._menu_admin = None  # type: Optional[object]
        self._act_emoji_moderation: Optional[QAction] = None
        if self._is_admin_role():
            self._menu_admin = menubar.addMenu("관리자")
            self._act_emoji_moderation = QAction("Emoji moderation…", self)
            self._act_emoji_moderation.triggered.connect(
                self._on_open_emoji_moderation
            )
            self._menu_admin.addAction(self._act_emoji_moderation)

        # "도움말" 메뉴
        menu_help = menubar.addMenu("도움말")
        act_about = QAction("TooTalk 정보…", self)
        act_about.triggered.connect(self._on_show_about)
        menu_help.addAction(act_about)

    def _is_admin_role(self) -> bool:
        """현재 user 의 role 가 admin / owner 인지 검사 (cycle 148 신설).

        Returns
        -------
        bool
            True = admin / owner. False = member / guest / 부재 (default).
        """

        # 한글 주석: admin + owner 둘 다 관리 권한 — emoji moderation 진입 path 공유
        return self._current_user_role in ("admin", "owner")

    def set_user_role(self, role: str) -> None:
        """로그인 응답 의 role 갱신 + 관리자 메뉴 가시성 재계산 (cycle 148).

        Parameters
        ----------
        role : str
            "admin" / "owner" / "member" / "guest" 중 하나. 빈 = member fallback.

        Notes
        -----
        - 본 메서드 호출 직후 menubar 의 "관리자" 메뉴 추가 / 제거.
        - role 갱신 = 로그인 다이얼로그 의 응답 / 세션 refresh chain 의 의무.
        """

        # 한글 주석: 빈 값 / None graceful — member fallback
        normalized = (role or "member").strip()
        if normalized not in ("admin", "owner", "member", "guest"):
            log.warning("[main_window] set_user_role 무효 — %r → member fallback", role)
            normalized = "member"
        self._current_user_role = normalized
        log.info("[main_window] user_role 갱신 — %s", normalized)
        # 한글 주석: menubar 재구성 — "관리자" 메뉴 가시성 재계산
        self._rebuild_admin_menu()

    def _rebuild_admin_menu(self) -> None:
        """admin 메뉴 의 가시성 재구성 — set_user_role 직후 호출 (cycle 148).

        기존 admin 메뉴 가 있으면 제거 + admin role 일 때만 재추가.
        """

        # 한글 주석: 기존 admin 메뉴 제거 — menubar 의 removeAction 의무
        menubar = self.menuBar()
        if self._menu_admin is not None:
            menubar.removeAction(self._menu_admin.menuAction())
            self._menu_admin = None
            self._act_emoji_moderation = None

        # 한글 주석: admin / owner 일 때만 재추가
        if self._is_admin_role():
            self._menu_admin = menubar.addMenu("관리자")
            self._act_emoji_moderation = QAction("Emoji moderation…", self)
            self._act_emoji_moderation.triggered.connect(
                self._on_open_emoji_moderation
            )
            self._menu_admin.addAction(self._act_emoji_moderation)

    # ------------------------------------------------------------------
    # cycle 148 — emoji moderation admin dialog 진입점
    # ------------------------------------------------------------------

    @pyqtSlot()
    def _on_open_emoji_moderation(self) -> None:
        """"Emoji moderation" 메뉴 슬롯 — admin dialog instantiation 진입점.

        흐름
        ----
        1. admin role 재검증 — 메뉴 우회 시 차단 의무 (방어적 guard).
        2. env ``EMOJI_MODERATION_ADMIN_TOKEN`` 조회 — 부재 시 graceful warning.
        3. base_url = UPDATE_SERVER_URL env 또는 _DEFAULT_UPDATE_SERVER_URL 폴백.
        4. asyncio loop 가용 시 fetch_pending_queue + dialog instantiation chain.
           loop 부재 시 빈 queue dialog instantiation (test / unittest 환경 graceful).
        5. dialog.decision_made signal → status bar feedback handler 의 wire.
        """

        # 한글 주석: 1차 admin role 재검증 — 메뉴 가시성 + 직접 호출 둘 다 차단
        from app.ui.confirm_dialog import ConfirmDialog
        if not self._is_admin_role():
            ConfirmDialog.show_warning(
                self, "TooTalk", "Emoji moderation = admin 권한 의무"
            )
            log.warning(
                "[main_window] emoji moderation 진입 차단 — role=%s",
                self._current_user_role,
            )
            return

        # 한글 주석: env token 의무 — 부재 시 graceful warning + return
        admin_token = os.environ.get("EMOJI_MODERATION_ADMIN_TOKEN", "").strip()
        if not admin_token:
            ConfirmDialog.show_warning(
                self,
                "TooTalk",
                "EMOJI_MODERATION_ADMIN_TOKEN env 미설정 — 진입 차단",
            )
            log.warning(
                "[main_window] EMOJI_MODERATION_ADMIN_TOKEN 부재 — graceful skip"
            )
            return

        # 한글 주석: base_url = UPDATE_SERVER_URL 재사용 (signaling 의 동일 호스트)
        base_url = (
            os.environ.get("UPDATE_SERVER_URL", "").strip()
            or _DEFAULT_UPDATE_SERVER_URL
        )

        # 한글 주석: lazy import — admin dialog (PyQt6 graceful)
        from app.ui.admin import open_emoji_moderation

        dialog = open_emoji_moderation(
            parent=self,
            base_url=base_url,
            admin_token=admin_token,
        )
        if dialog is None:
            log.warning(
                "[main_window] emoji moderation dialog 생성 실패 — graceful skip"
            )
            return

        # 한글 주석: decision_made signal → status bar feedback handler wire
        try:
            dialog.decision_made.connect(self._on_moderation_decision)
        except Exception as exc:  # noqa: BLE001
            # 한글 주석: PyQt6 graceful stub 환경 의 signal 부재 graceful
            log.debug(
                "[main_window] decision_made signal wire 실패 (stub 환경 가능) — %r",
                exc,
            )

        # 한글 주석: asyncio loop 가용 시 fetch_pending_queue background task 등록
        loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            asyncio.ensure_future(
                self._dispatch_moderation_queue_fetch(
                    dialog=dialog, base_url=base_url, admin_token=admin_token
                ),
                loop=loop,
            )
        else:
            log.debug(
                "[main_window] asyncio running loop 부재 — queue fetch skip"
            )

        # 한글 주석: dialog 참조 보관 — gc 회피 + 테스트 가시성
        self._current_moderation_dialog = dialog
        # 한글 주석: dialog 의 modal exec — caller 의 blocking 진입
        try:
            dialog.exec()
        except Exception as exc:  # noqa: BLE001
            # 한글 주석: PyQt6 stub 환경 graceful — exec 부재 시 skip
            log.debug(
                "[main_window] moderation dialog exec 실패 (stub 환경 가능) — %r",
                exc,
            )

    async def _dispatch_moderation_queue_fetch(
        self, *, dialog: object, base_url: str, admin_token: str
    ) -> None:
        """fetch_pending_queue + dialog.repopulate 의 async chain (cycle 148).

        Parameters
        ----------
        dialog : EmojiModerationDialog
            instantiation 직후 dialog. repopulate(items) 호출 의무.
        base_url : str
            signaling server base URL.
        admin_token : str
            admin Bearer token.

        Notes
        -----
        - fetch_pending_queue RuntimeError graceful catch — 빈 queue 유지.
        - 401/403/503 의 통합 graceful catch + status bar feedback.
        """

        from app.ui.admin.emoji_moderation_dialog import fetch_pending_queue

        try:
            items = await fetch_pending_queue(base_url, admin_token)
            # 한글 주석: dialog.repopulate(items) — QListWidget 재구성
            if hasattr(dialog, "repopulate"):
                dialog.repopulate(items)
            log.info(
                "[main_window] emoji moderation queue fetch PASS count=%d",
                len(items),
            )
        except Exception as exc:  # noqa: BLE001
            # 한글 주석: httpx 부재 / 401 / 503 / JSON 무효 의 통합 graceful catch
            log.warning(
                "[main_window] emoji moderation queue fetch FAIL — graceful (%r)",
                exc,
            )
            self._status_bar.showMessage(
                f"moderation queue fetch 실패 — {exc}", 4000
            )

    @pyqtSlot(int, str)
    def _on_moderation_decision(self, pack_id: int, decision: str) -> None:
        """EmojiModerationDialog 의 decision_made 시그널 핸들러 (cycle 148).

        Parameters
        ----------
        pack_id : int
            결정 대상 pack.id.
        decision : str
            "approve" / "reject" / "dmca" 중 하나.

        Notes
        -----
        - status bar feedback 의 즉각 표시.
        - 실 REST POST chain (post_decision) = dialog 내부 의 외부 callback / 별개 cycle 의 의무.
          본 슬롯 = UI feedback 만.
        """

        log.info(
            "[main_window] moderation decision pack_id=%d decision=%s",
            pack_id,
            decision,
        )
        self._status_bar.showMessage(
            f"moderation 결정 — pack_id={pack_id} decision={decision}", 3000
        )

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
        """세션 토큰 폐기."""

        from app.ui.confirm_dialog import ConfirmDialog
        if self._session_token is None:
            ConfirmDialog.show_info(self, "TooTalk", "로그인 상태 아님")
            return
        self._session_token = None
        self._current_user_id = None
        ConfirmDialog.show_info(self, "TooTalk", "로그아웃 완료")

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

    def _on_open_add_friend(self) -> None:
        """"친구 추가" 메뉴 슬롯 — AddFriendDialog 의 모달 실행."""

        if self._session_token is None:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(
                self, "TooTalk", "친구 추가 = 로그인 의무"
            )
            return

        dlg = AddFriendDialog(parent=self)
        dlg.friend_requested.connect(self._on_friend_requested)
        dlg.exec()

    def _on_friend_requested(self, user_id: int, nickname: str) -> None:
        """AddFriendDialog 의 friend_requested 시그널 수신 — REST POST 호출 placeholder.

        REST 호출 chain (POST /api/friends) 의 actual binding = 별개 cycle 의 의무.
        본 슬롯 = log + status bar feedback 만.
        """

        log.info(
            "[main_window] friend_requested user_id=%d nickname=%r",
            user_id,
            nickname,
        )
        self._status_bar.showMessage(
            f"친구 요청 발신 — user_id={user_id}", 3000
        )

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

    async def _post_and_resolve(self, msg_client, room_id: int, text: str, client_uuid: str) -> None:
        """server POST → message_id resolve → bubble.set_message_id chain (cycle 163)."""
        try:
            resp = await msg_client.post_message(room_id, text)
            server_message_id = resp.get("message_id") if isinstance(resp, dict) else None
            if server_message_id is not None:
                self._chat_view.resolve_pending_message_id(client_uuid, int(server_message_id))
                log.debug("post_message resolve — uuid=%s message_id=%s", client_uuid, server_message_id)
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("post_message 실패 graceful — %r", exc)

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
        # cycle 169.174 — chat_list entry preview + ts bump (sort + render)
        try:
            self._chat_list_panel.bump_entry(
                kind=kind, target_id=target_id,
                last_message=text, last_ts=ts,
                last_sender=sender if not is_self else "나",
                is_self=is_self,
            )
        except Exception:  # pragma: no cover - graceful
            pass
        # active chat 이면 chat_view render
        if self._active_chat_kind == kind and self._active_chat_target_id == target_id:
            try:
                # 1:1 chat = friend/bot kind → sender label suppress (room = retain)
                hide_sender = kind in ("friend", "bot")
                self._chat_view.add_message(
                    sender=sender, text=text, ts=ts, is_self=is_self,
                    reply_to=reply_to, hide_sender=hide_sender,
                )
                # cycle 169.165 — send/receive 직후 scroll bottom 자동 (telegram align)
                self._chat_view.scroll_to_bottom()
            except Exception as exc:  # pragma: no cover - graceful
                log.debug("chat_view add_message 실패 — %r", exc)

    async def _fetch_dm_history(self, friend_id: int) -> None:
        """cycle 169.225 — friend DM room resolve + message history fetch chain.

        1. GET /api/auth/dm/{friend_id}/room → room_id resolve (cycle 169.222 endpoint)
        2. list_messages(room_id, limit=50) → MessagePayload list
        3. active chat retain 시점 chat_view re-populate

        graceful — server 부재 시 DM cache replay retain.
        """
        import aiohttp
        from datetime import datetime
        try:
            api_base = getattr(self._config, "api_base", None) or "https://114.207.112.73"
            # cycle 169.228 — self._session_token 정합 회수 (cycle 169.221/222/225 chain)
            token = getattr(self, "_session_token", None) or ""
            if not token:
                return
            headers = {"Authorization": f"Bearer {token}"}
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                # step 1 — DM room resolve
                async with session.get(
                    f"{api_base}/api/auth/dm/{friend_id}/room",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return
                    dm = await resp.json()
                    room_id = dm.get("room_id")
                if not room_id:
                    return
                # step 2 — messages list (cycle 142 endpoint)
                async with session.get(
                    f"{api_base}/api/rooms/{room_id}/messages?limit=50&offset=0",
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return
                    page = await resp.json()
                    raw_messages = page.get("messages", [])
            # step 3 — active chat retain 시점 chat_view re-populate (cycle 169.411 saved 정합)
            active_match = (
                (self._active_chat_kind == "friend" and self._active_chat_target_id == friend_id)
                or (self._active_chat_kind == "saved")
            )
            if active_match:
                self._chat_view.clear_messages()
                for m in raw_messages:
                    sender = m.get("sender_name") or f"user#{m.get('sender_id', 0)}"
                    text = m.get("text", "")
                    ts_ms = m.get("ts_ms") or 0
                    ts = datetime.fromtimestamp(ts_ms / 1000.0) if ts_ms else datetime.now()
                    is_self = m.get("sender_id") == getattr(self._state, "user_id", -1)
                    self._chat_view.add_message(sender, text, ts, is_self=is_self, hide_sender=True)
                self._chat_view.scroll_to_bottom()
                log.info("[dm_history] friend=%d room=%d msgs=%d replay PASS", friend_id, room_id, len(raw_messages))
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("[dm_history] fetch 실패 — %r", exc)

    async def _send_saved_message_rest(self, text: str, client_uuid: str) -> None:
        """cycle 169.411 — saved messages self DM room REST POST chain.

        1. GET /api/auth/dm/{self_id}/room → server 의 saved-{uid} room return (viewer==target)
        2. POST /api/rooms/{room_id}/messages → server 영속화
        mesh broadcast 부재 (self 의 self echo loop 회피).
        """
        import aiohttp
        try:
            self_id = getattr(self, "_current_user_id", None)
            token = getattr(self, "_session_token", None) or ""
            api_base = getattr(self._config, "api_base", None) or "https://114.207.112.73"
            if not isinstance(self_id, int) or self_id <= 0 or not token:
                return
            headers = {"Authorization": f"Bearer {token}"}
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.get(
                    f"{api_base}/api/auth/dm/{self_id}/room",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        return
                    dm = await resp.json()
                    room_id = dm.get("room_id")
                if not room_id:
                    return
                async with session.post(
                    f"{api_base}/api/rooms/{room_id}/messages",
                    json={"body": text, "client_uuid": client_uuid},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status not in (200, 201):
                        log.warning("[saved_post] status=%d", resp.status)
                        return
                    data = await resp.json()
                    log.info("[saved_post] PASS room=%d msg_id=%s", room_id, data.get("message_id"))
        except Exception as exc:
            log.debug("[saved_post] 실패 graceful — %r", exc)

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

    async def _send_bot_message(self, text: str) -> None:
        """cycle 169.203 — 투네이션 고객센터 bot LLM 응답 chain (사용자 directive image #29).

        POST /api/bot/chat → reply.content → DM cache append.
        graceful exception (server fail 시 system message render).
        """
        import time, aiohttp
        # cycle 169.288 — typing indicator 표시 (사용자 directive image #58/62)
        from app.ui.typing_indicator import TypingIndicator
        typing = TypingIndicator(parent=self._chat_view._content)
        try:
            self._chat_view._messages_layout.addWidget(typing)
            self._chat_view._scroll_to_bottom_once()
        except Exception:  # pragma: no cover - graceful
            pass
        try:
            api_base = getattr(self._config, "api_base", None) or "https://114.207.112.73"
            token = getattr(self, "_session_token", None) or ""
            # cycle 169.263 — 사용자 critique bot 401 retain root cause trace log
            log.warning(
                "[bot_chat] token_present=%s token_len=%d api_base=%s",
                bool(token), len(token), api_base,
            )
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            payload = {
                "messages": [
                    {"role": "user", "content": text, "timestamp_ms": int(time.time() * 1000)},
                ],
            }
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    f"{api_base}/api/bot/chat", json=payload, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    # cycle 169.209 — ContentTypeError 회수 — content_type=None force parse
                    text_body = await resp.text()
                    status = resp.status
                    if status != 200:
                        log.warning("[bot_chat] HTTP %d body=%s", status, text_body[:200])
                        reply = f"⚠️ 서버 응답 부재 (HTTP {status}). 잠시 후 다시 시도해주세요."
                    else:
                        try:
                            import json
                            data = json.loads(text_body)
                            reply = data.get("reply", {}).get("content", "응답 부재")
                        except json.JSONDecodeError:
                            log.warning("[bot_chat] JSON parse 실패 — body=%s", text_body[:200])
                            reply = "⚠️ 응답 형식 오류. 잠시 후 다시 시도해주세요."
        except Exception as exc:  # pragma: no cover - graceful
            log.warning("[bot_chat] LLM 호출 실패 — %r", exc)
            reply = f"⚠️ 서버 연결 실패 — {exc.__class__.__name__}. 데모 서버 점검 중일 수 있습니다."
        finally:
            # cycle 169.288 — typing indicator 제거 (응답 도착 또는 graceful 분기 모두)
            try:
                typing.stop()
                typing.setParent(None)
                typing.deleteLater()
            except Exception:  # pragma: no cover - graceful
                pass
        self._append_dm_message(
            "bot", 1, "투네이션 고객센터", reply, datetime.now(), is_self=False,
        )

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
    def _on_folder_selected(self, folder_id: str) -> None:
        """folder click → chat_list_panel filter + edit popup (cycle 169.75)."""
        log.info("[main_window] folder_selected — folder_id=%s", folder_id)
        # cycle 169.75 회수 — 편집 click → FolderManageDialog popup
        if folder_id == "edit":
            from app.ui.folder_manage_dialog import FolderManageDialog
            user_folders = getattr(self, "_user_folders", [])
            dialog = FolderManageDialog(user_folders=user_folders, parent=self)
            dialog.folder_create_requested.connect(self._on_folder_create_requested)  # type: ignore[arg-type]
            dialog.folder_delete_requested.connect(self._on_folder_delete_requested)  # type: ignore[arg-type]
            dialog.folder_edit_requested.connect(self._on_folder_edit_requested)  # type: ignore[arg-type]
            dialog.exec()
            return
        if hasattr(self, "_chat_list_panel"):
            self._chat_list_panel.set_active_folder(folder_id)

    @pyqtSlot()
    def _on_folder_create_requested(self) -> None:
        """새 폴더 만들기 → FolderEditDialog popup (cycle 169.75)."""
        # cycle 169.230 — FolderEditDialog main 안 centered exec (image #31 회수)
        from app.ui.folder_edit_dialog import FolderEditDialog
        dialog = FolderEditDialog(parent=self)
        dialog.folder_saved.connect(self._on_folder_saved)  # type: ignore[arg-type]
        dialog.chat_picker_requested.connect(  # type: ignore[arg-type]
            lambda mode: self._open_chat_picker(dialog, mode)
        )
        self._exec_dialog_centered(dialog)

    def _open_chat_picker(self, edit_dialog, mode: str) -> None:
        """FolderEditDialog 안 대화방 추가 click → ChatPickerDialog."""
        from app.ui.chat_picker_dialog import ChatPickerDialog
        entries = list(getattr(self._chat_list_panel, "_entries", []))
        picker = ChatPickerDialog(chat_entries=entries, mode=mode, parent=edit_dialog)

        def _on_selected(chats):
            if mode == "include":
                edit_dialog.add_included_chats(chats)
            else:
                edit_dialog.add_excluded_chats(chats)
        picker.chats_selected.connect(_on_selected)  # type: ignore[arg-type]
        # cycle 169.370 — _exec_dialog_centered chain (main center modal + backdrop + ESC)
        self._exec_dialog_centered(picker)

    @pyqtSlot(dict)
    def _on_folder_saved(self, folder_data: dict) -> None:
        """FolderEditDialog 만들기 PASS → user_folders append/replace + REST 영속화 + sidebar refresh.

        cycle 169.388 — edit mode (사용자 critique image #153) — _is_edit flag retain 시점
        기존 folder_id 의 user_folders entry replace + UPDATE chain (INSERT 부재).
        """
        if not hasattr(self, "_user_folders"):
            self._user_folders = []
        is_edit = folder_data.pop("_is_edit", False)
        if is_edit:
            target_fid = str(folder_data.get("folder_id", ""))
            self._user_folders = [
                folder_data if str(f.get("folder_id", "")) == target_fid else f
                for f in self._user_folders
            ]
            # 한글 주석 — replace 부재 시 append fallback
            if not any(str(f.get("folder_id", "")) == target_fid for f in self._user_folders):
                self._user_folders.append(folder_data)
        else:
            self._user_folders.append(folder_data)
        # cycle 169.385 — included_chats debug log (사용자 critique image #148 folder filter fail 회수)
        log.warning(
            "[folder_saved] name=%s included=%d excluded=%d included_data=%s",
            folder_data.get("name"),
            len(folder_data.get("included_chats", [])),
            len(folder_data.get("excluded_chats", [])),
            folder_data.get("included_chats", [])[:3],
        )
        # cycle 169.373 — sidebar_rail folder entry 동적 갱신 (사용자 critique image #129)
        if hasattr(self, "_sidebar_rail") and hasattr(self._sidebar_rail, "set_folder_entries"):
            try:
                self._sidebar_rail.set_folder_entries(self._user_folders)
            except Exception as exc:
                log.debug("sidebar_rail set_folder_entries fail — %r", exc)
        # cycle 169.378 — chat_list_panel folder metadata sync (사용자 critique image #134 filter 의무)
        clp = getattr(self, "_chat_list_panel", None)
        if clp is not None and hasattr(clp, "set_user_folders"):
            try:
                clp.set_user_folders(self._user_folders)
            except Exception as exc:
                log.debug("chat_list_panel set_user_folders fail — %r", exc)
        # cycle 169.373 — active FolderManageDialog close chain (사용자 critique image #127)
        active_folder_dialog = getattr(self, "_active_folder_dialog", None)
        if active_folder_dialog is not None:
            try:
                active_folder_dialog.reject()
            except Exception:
                pass
            self._active_folder_dialog = None
        # cycle 169.77 회수 — FolderCreateWorker REST 영속화 chain
        base_url = getattr(self._auth_client, "_base_url", "") if self._auth_client else ""
        token = getattr(self, "_auth_token", None)
        if not base_url or not token:
            log.warning("[folder] base_url/token 부재 — REST 영속화 skip")
            return
        # cycle 169.411 — edit mode PATCH endpoint chain (Phase 1 잔존 회수)
        if is_edit:
            from app.net.folder_client import FolderUpdateWorker
            target_fid = str(folder_data.get("folder_id", ""))
            worker = FolderUpdateWorker(base_url, token, target_fid, folder_data, parent=self)
        else:
            from app.net.folder_client import FolderCreateWorker
            worker = FolderCreateWorker(base_url, token, folder_data, parent=self)
        worker.finished_with_result.connect(self._on_folder_persist_finished)  # type: ignore[arg-type]
        # cycle 169.79 회수 — worker list append (MED-2 dangling 차단)
        if not hasattr(self, "_folder_workers"):
            self._folder_workers = []
        self._folder_workers.append(worker)
        worker.finished.connect(lambda w=worker: self._folder_workers.remove(w))  # type: ignore[arg-type]
        worker.start()

    @pyqtSlot(bool, str, str, dict)
    def _on_folder_persist_finished(self, ok: bool, error_code: str, error_message: str, data: dict) -> None:
        """FolderCreateWorker finished — log + folder_id 갱신."""
        if ok:
            log.info("[folder] REST 영속화 PASS — id=%s", data.get("id"))
        else:
            log.warning("[folder] REST 영속화 실패 — code=%s msg=%s", error_code, error_message)

    @pyqtSlot(str)
    def _on_folder_edit_requested(self, folder_id: str) -> None:
        """folder edit click → FolderEditDialog open with existing data (cycle 169.381 사용자 critique image #139/140)."""
        user_folders = getattr(self, "_user_folders", [])
        existing = next((f for f in user_folders if str(f.get("folder_id", "")) == folder_id), None)
        if existing is None:
            log.warning("[folder_edit] folder_id=%s 부재", folder_id)
            return
        from app.ui.folder_edit_dialog import FolderEditDialog
        dialog = FolderEditDialog(existing=existing, parent=self)
        dialog.folder_saved.connect(self._on_folder_saved)  # type: ignore[arg-type]
        dialog.chat_picker_requested.connect(
            lambda mode: self._open_chat_picker(dialog, mode)
        )  # type: ignore[arg-type]
        self._exec_dialog_centered(dialog)

    @pyqtSlot(str)
    def _on_folder_delete_requested(self, folder_id: str) -> None:
        """folder delete request + REST DELETE chain (cycle 169.77)."""
        user_folders = getattr(self, "_user_folders", [])
        self._user_folders = [f for f in user_folders if f.get("folder_id") != folder_id]
        log.info("[main_window] folder deleted — folder_id=%s", folder_id)
        base_url = getattr(self._auth_client, "_base_url", "") if self._auth_client else ""
        token = getattr(self, "_auth_token", None)
        if not base_url or not token:
            return
        from app.net.folder_client import FolderDeleteWorker
        worker = FolderDeleteWorker(base_url, token, folder_id, parent=self)
        worker.finished_with_result.connect(  # type: ignore[arg-type]
            lambda ok, *_: log.info("[folder] DELETE finished ok=%s", ok)
        )
        # cycle 169.79 회수 — worker list append
        if not hasattr(self, "_folder_workers"):
            self._folder_workers = []
        self._folder_workers.append(worker)
        worker.finished.connect(lambda w=worker: self._folder_workers.remove(w))  # type: ignore[arg-type]
        worker.start()

    @pyqtSlot(str, int)
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
        # cycle 169.156~157 — chat 전환 + DM cache replay (image #12 telegram 동작성)
        try:
            # cycle 169.176 — prev active chat 의 scroll offset save (전환 직전)
            self._chat_view.save_scroll_offset()
            self._chat_view.clear_messages()
            self._active_chat_kind = kind
            self._active_chat_target_id = target_id
            # cycle 169.157 — cache replay (server REST fetch = 별 cycle 169.158+)
            # cycle 169.163 — 1:1 chat (friend/bot) sender label suppress propagate
            hide_sender = kind in ("friend", "bot")
            cached = self._dm_history.get((kind, target_id), [])
            for sender, text, ts, is_self in cached:
                self._chat_view.add_message(sender, text, ts, is_self=is_self, hide_sender=hide_sender)
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
    def _on_header_sidebar_toggle(self) -> None:
        """chat header sidebar toggle button — room_list visibility toggle (cycle 169.61)."""
        visible = self._room_list.isVisible()
        self._room_list.setVisible(not visible)
        log.info("[main_window] sidebar toggle — visible=%s", not visible)

    @pyqtSlot(str, str)
    def _on_signaling_offer(self, from_peer: str, sdp: str) -> None:
        """incoming OFFER → CallDialog incoming=True + CallClient.accept_offer (cycle 169.59)."""
        log.info("[call] incoming OFFER from=%s sdp_len=%d", from_peer, len(sdp))
        from app.ui.call_dialog import CallDialog
        from app.net.call_client import CallClient
        stun_url = getattr(self._config, "stun_url", "stun:stun.l.google.com:19302")
        turn_url = getattr(self._config, "turn_url", "")
        turn_username = getattr(self._config, "turn_username", "")
        turn_credential = getattr(self._config, "turn_credential", "")
        signaling = getattr(self, "_signaling_client", None)
        call_client = CallClient(
            stun_url=stun_url, signaling_client=signaling, peer_id=from_peer,
            turn_url=turn_url, turn_username=turn_username, turn_credential=turn_credential,
        )
        self._active_call_client = call_client
        # 한글 주석 — accept_offer fire (background) + CallDialog incoming=True modal
        import asyncio
        asyncio.ensure_future(call_client.accept_offer(remote_sdp=sdp, video=False))
        dialog = CallDialog(peer_name=from_peer, video_enabled=False, incoming=True, parent=self)
        dialog.attach_client(call_client)
        dialog.exec()

    @pyqtSlot(str, str)
    def _on_signaling_answer(self, from_peer: str, sdp: str) -> None:
        """incoming ANSWER → call_client.apply_answer dispatch."""
        log.info("[call] incoming ANSWER from=%s", from_peer)
        client = getattr(self, "_active_call_client", None)
        if client is None:
            log.warning("[call] active client 부재 — answer drop")
            return
        import asyncio
        asyncio.ensure_future(client.apply_answer(remote_sdp=sdp))

    @pyqtSlot(str, dict)
    def _on_signaling_ice(self, from_peer: str, candidate: dict) -> None:
        """incoming ICE candidate → pc.addIceCandidate dispatch."""
        log.debug("[call] incoming ICE from=%s", from_peer)
        client = getattr(self, "_active_call_client", None)
        if client is None or client._pc is None:
            return
        import asyncio
        try:
            from aiortc import RTCIceCandidate
            cand = RTCIceCandidate(
                candidate=candidate.get("candidate", ""),
                sdpMid=candidate.get("sdpMid"),
                sdpMLineIndex=candidate.get("sdpMLineIndex"),
            )
            asyncio.ensure_future(client._pc.addIceCandidate(cand))
        except Exception as exc:
            log.warning("[call] ICE addCandidate fail — %r", exc)

    @pyqtSlot(str)
    def _on_signaling_peer_joined(self, peer_id: str) -> None:
        """peer joined → active peer 자동 set (단일 peer chain)."""
        log.info("[signaling] peer joined — peer_id=%s", peer_id)
        self._active_peer_id = peer_id

    @pyqtSlot()
    def _on_hamburger_clicked(self) -> None:
        """좌상단 햄버거 click → HamburgerDrawer slide-in (cycle 169.113 회수).

        의 main_window 좌측 edge 부터 320px width drawer slide-in.
        높이 = main_window height match. 외부 click 시 popup 자동 close.
        """
        from app.ui.hamburger_drawer import HamburgerDrawer
        # cycle 169.404 — nickname 우선 (사용자 critique image #175 avatar stale 회수)
        nickname = getattr(self, "_current_nickname", "") or ""
        username = (
            nickname
            or getattr(self, "_current_user_nickname", None)
            or getattr(self._config, "user_nickname", "사용자")
        )
        if getattr(self, "_active_drawer", None) is not None:
            try:
                self._active_drawer.close_drawer()
            except Exception:
                pass
            self._active_drawer = None
            return
        drawer = HamburgerDrawer(username=username, nickname=nickname, parent=self)
        drawer.profile_clicked.connect(self._on_drawer_profile)  # type: ignore[arg-type]
        drawer.settings_clicked.connect(self._on_drawer_settings)  # type: ignore[arg-type]
        # cycle 169.320 — drawer 5 signal 전 connect (image #84 사용자 directive)
        drawer.new_group_clicked.connect(self._on_drawer_new_group)  # type: ignore[arg-type]
        drawer.new_channel_clicked.connect(self._on_drawer_new_channel)  # type: ignore[arg-type]
        drawer.contacts_clicked.connect(self._on_drawer_contacts)  # type: ignore[arg-type]
        drawer.calls_clicked.connect(self._on_drawer_calls)  # type: ignore[arg-type]
        drawer.saved_clicked.connect(self._on_drawer_saved)  # type: ignore[arg-type]
        drawer.logout_clicked.connect(self._on_drawer_logout)  # type: ignore[arg-type]
        # cycle 169.411 — night mode toggle signal binding (Phase 1 잔존 회수)
        drawer.night_mode_toggled.connect(self._on_night_mode_toggled)  # type: ignore[arg-type]
        # cycle 169.116 회수 — sidebar_rail (96px) 의 의 reserve — 햄버거 button click 가능
        # drawer x anchor = sidebar width — sidebar_rail visible retain
        central = self.centralWidget() if self.centralWidget() else self
        sidebar_w = self._sidebar_rail.width() if hasattr(self, "_sidebar_rail") else 96
        # cycle 169.303 — drawer width 320 → 256 (사용자 directive 20% 감소)
        drawer.setGeometry(sidebar_w, 0, 256, central.height())
        drawer.exec()  # show + raise + setFocus
        # 한글 주석 — close 시점 ref clear
        def _on_drawer_closed():
            self._active_drawer = None
        drawer.closed.connect(_on_drawer_closed)  # type: ignore[arg-type]
        self._active_drawer = drawer

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

    @pyqtSlot()
    def _on_drawer_profile(self) -> None:
        """내 프로필 dialog open. cycle 169.401 — nickname + display_name + username 3 entry 분리 (사용자 critique image #168)."""
        from app.ui.my_profile_dialog import MyProfileDialog
        nickname = getattr(self, "_current_nickname", "") or ""
        display_name = getattr(self, "_current_display_name", "") or ""
        username = getattr(self, "_current_username", "") or getattr(self._config, "user_nickname", "사용자")
        email = getattr(self, "_current_email", "") or ""
        phone = getattr(self, "_current_user_phone", "") or ""
        birthdate = getattr(self, "_current_user_birthdate", "") or ""
        bio = getattr(self, "_current_user_bio", "") or ""
        dialog = MyProfileDialog(
            username=username, nickname=nickname, display_name=display_name,
            email=email, phone=phone, birthdate=birthdate, bio=bio, parent=self,
        )
        # cycle 169.403 — active profile dialog reference retain (save 後 즉시 refresh chain)
        self._active_profile_dialog = dialog
        dialog.edit_requested.connect(self._on_profile_edit_requested)  # type: ignore[arg-type]
        self._exec_dialog_centered(dialog)

    @pyqtSlot()
    def _on_profile_edit_requested(self) -> None:
        """내 프로필 안 edit click → MyAccountDialog 진입 + save 시 PUT /api/auth/profile."""
        from app.ui.my_account_dialog import MyAccountDialog
        from app.net.account_client import ProfileUpdateWorker
        # cycle 169.399 — username + display_name + nickname 분리 (사용자 directive image #163/164)
        username = getattr(self, "_current_username", None) or getattr(self._config, "user_nickname", "사용자")
        display_name = getattr(self, "_current_display_name", "") or username
        nickname = getattr(self, "_current_nickname", "")
        email = getattr(self, "_current_email", "")
        phone = getattr(self, "_current_user_phone", "")
        bio = getattr(self, "_current_user_bio", "")
        birthdate = getattr(self, "_current_user_birthdate", "")
        dialog = MyAccountDialog(
            username=username, display_name=display_name, nickname=nickname,
            email=email, phone=phone, bio=bio,
            birthdate=birthdate, parent=self,
        )

        def _on_save(payload: dict) -> None:
            base_url = getattr(self._auth_client, "_base_url", "") if self._auth_client else ""
            token = getattr(self, "_auth_token", None)
            if not base_url or not token:
                log.warning("[profile] base_url/token 부재 — PUT skip")
                return
            # cycle 169.400 — display_name + nickname 동시 갱신 (사용자 directive image #166)
            new_disp = (payload.get("display_name") or "").strip()
            if new_disp:
                self._current_display_name = new_disp
            new_nick = (payload.get("nickname") or "").strip()
            if new_nick:
                self._current_nickname = new_nick
                self._current_user_nickname = new_nick  # alias retain
            new_bio = (payload.get("bio") or "").strip()
            # cycle 169.403 — active MyProfileDialog + HamburgerDrawer 즉시 refresh (사용자 critique image #169/171)
            active_profile = getattr(self, "_active_profile_dialog", None)
            if active_profile is not None and hasattr(active_profile, "refresh_profile"):
                try:
                    active_profile.refresh_profile(
                        nickname=self._current_nickname or "",
                        display_name=self._current_display_name or "",
                        phone=payload.get("phone", "") or self._current_user_phone or "",
                        birthdate=payload.get("birthdate", "") or self._current_user_birthdate or "",
                        username=getattr(self, "_current_username", "") or "",
                        email=getattr(self, "_current_email", "") or "",
                        bio=payload.get("bio", "") or getattr(self, "_current_user_bio", "") or "",
                    )
                except Exception as exc:
                    log.debug("active profile refresh fail — %r", exc)
            active_drawer = getattr(self, "_active_drawer", None)
            if active_drawer is not None and hasattr(active_drawer, "update_user_info"):
                try:
                    active_drawer.update_user_info(self._current_nickname or self._current_display_name or "")
                except Exception as exc:
                    log.debug("active drawer refresh fail — %r", exc)
            if new_bio:
                self._current_user_bio = new_bio
            new_phone = (payload.get("phone") or "").strip()
            if new_phone:
                self._current_user_phone = new_phone
            new_birth = (payload.get("birthdate") or "").strip()
            if new_birth:
                self._current_user_birthdate = new_birth
            worker = ProfileUpdateWorker(base_url, token, payload, parent=self)
            worker.finished_with_result.connect(self._on_profile_update_finished)  # type: ignore[arg-type]
            worker.start()
            self._profile_worker = worker  # gc 회피

        dialog.save_requested.connect(_on_save)  # type: ignore[arg-type]
        dialog.exec()

    @pyqtSlot(bool, str, str, dict)
    def _on_profile_update_finished(self, ok: bool, error_code: str, error_message: str, data: dict) -> None:
        """ProfileUpdateWorker finished slot."""
        from app.ui.confirm_dialog import ConfirmDialog
        if ok:
            ConfirmDialog.show_info(self, "TooTalk", "프로필 갱신 완료")
        else:
            ConfirmDialog.show_warning(self, "TooTalk", f"프로필 갱신 실패 — {error_message or error_code}")

    @pyqtSlot()
    def _on_drawer_settings(self) -> None:
        """설정 dialog open — cycle 169.301 _exec_dialog_centered chain (QWidget base 정합)."""
        try:
            from app.ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog(parent=self)
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("SettingsDialog 진입 실패 — %r", exc)

    @pyqtSlot()
    def _on_drawer_contacts(self) -> None:
        """연락처 dialog — ContactsDialog open chain (cycle 169.320)."""
        try:
            from app.ui.contacts_dialog import ContactsDialog
            entries = list(getattr(self._chat_list_panel, "_entries", []))
            contacts = [
                {"name": e.name, "email": getattr(e, "email", "")}
                for e in entries if getattr(e, "kind", "") == "friend"
            ]
            dialog = ContactsDialog(contacts=contacts, parent=self)
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("ContactsDialog open 실패 — %r", exc)

    @pyqtSlot()
    def _on_drawer_new_group(self) -> None:
        """그룹 만들기 wizard (cycle 169.333 image #97~101 telegram align)."""
        try:
            from app.ui.new_group_dialog import NewGroupDialog
            # 한글 주석 — chat_list_panel 의 friends 추출 (room/saved/bot 제외)
            friends_data: list[dict] = []
            clp = getattr(self, "_chat_list_panel", None)
            if clp is not None:
                for e in getattr(clp, "_entries", []):
                    if getattr(e, "kind", "") == "friend":
                        friends_data.append({
                            "target_id": e.target_id,
                            "name": e.name,
                            "last_seen": "온라인" if e.is_online else "최근에 접속함",
                        })
            dialog = NewGroupDialog(friends=friends_data, parent=self)
            dialog.group_created.connect(self._on_group_created)  # type: ignore[arg-type]
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("NewGroupDialog open 실패 — %r", exc)

    @pyqtSlot(str, list)
    def _on_group_created(self, name: str, member_ids: list) -> None:
        """그룹 생성 callback — ChatListEntry kind=group 추가 + chat 진입 + roster broadcast placeholder (cycle 169.333)."""
        from app.ui.chat_list_panel import ChatListEntry
        from datetime import datetime
        # 한글 주석 — group_id placeholder (negative range 의 server-side 부재 시점)
        gid = -abs(hash(name) % 100000) - 1
        entry = ChatListEntry(
            kind="group",
            target_id=gid,
            name=name,
            last_message="그룹을 만들었습니다.",
            last_ts=datetime.now(),
            unread_count=0,
            is_pinned=False,
            is_online=False,
        )
        clp = getattr(self, "_chat_list_panel", None)
        if clp is not None:
            entries = list(getattr(clp, "_entries", []))
            entries.insert(0, entry)
            clp.set_entries(entries)
        log.info("[group_created] name=%s member_count=%d gid=%d", name, len(member_ids), gid)
        # 한글 주석 — 그룹 chat 진입 chain
        self._on_chat_selected("group", gid)

    @pyqtSlot()
    def _on_drawer_new_channel(self) -> None:
        """채널 만들기 wizard (cycle 169.348 image #97~101 등가)."""
        try:
            from app.ui.new_channel_dialog import NewChannelDialog
            friends_data: list[dict] = []
            clp = getattr(self, "_chat_list_panel", None)
            if clp is not None:
                for e in getattr(clp, "_entries", []):
                    if getattr(e, "kind", "") == "friend":
                        friends_data.append({
                            "target_id": e.target_id,
                            "name": e.name,
                            "last_seen": "온라인" if e.is_online else "최근에 접속함",
                        })
            dialog = NewChannelDialog(friends=friends_data, parent=self)
            dialog.channel_created.connect(self._on_channel_created)  # type: ignore[arg-type]
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("NewChannelDialog open 실패 — %r", exc)

    @pyqtSlot(str, str, list)
    def _on_channel_created(self, name: str, desc: str, subscriber_ids: list) -> None:
        """채널 생성 callback — ChatListEntry kind=channel insert + chat focus (cycle 169.348)."""
        from app.ui.chat_list_panel import ChatListEntry
        from datetime import datetime
        cid = -abs(hash(name) % 100000) - 100001
        entry = ChatListEntry(
            kind="channel",
            target_id=cid,
            name=name,
            last_message=desc or "채널이 생성되었습니다.",
            last_ts=datetime.now(),
            unread_count=0,
            is_pinned=False,
            is_online=False,
        )
        clp = getattr(self, "_chat_list_panel", None)
        if clp is not None:
            entries = list(getattr(clp, "_entries", []))
            entries.insert(0, entry)
            clp.set_entries(entries)
        log.info("[channel_created] name=%s subscriber_count=%d cid=%d", name, len(subscriber_ids), cid)
        self._on_chat_selected("channel", cid)

    @pyqtSlot()
    def _on_drawer_calls(self) -> None:
        """전화 history dialog (cycle 169.320 image #84)."""
        try:
            from app.ui.calls_dialog import CallsDialog
            dialog = CallsDialog(calls=[], parent=self)
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("CallsDialog open 실패 — %r", exc)

    @pyqtSlot()
    def _on_drawer_saved(self) -> None:
        """저장한 메시지 → drawer close + chat_view focus (cycle 169.325 image #88 사용자 directive)."""
        try:
            # 한글 주석 — chat_list_panel 안 saved entry highlight + chat_view 안 saved chat open
            if hasattr(self, "_chat_list_panel"):
                self._chat_list_panel.set_active_tab("friends")
                self._chat_list_panel.set_current_chat("saved", 0)
            # cycle 169.411 — saved kind 의 target_id retain (0 유지 — server self-resolve viewer_id)
            self._on_chat_selected("saved", 0)
            # 한글 주석 — cycle 169.325 — drawer slide close (사용자 directive image #88)
            drawer = getattr(self, "_active_drawer", None)
            if drawer is not None and hasattr(drawer, "close_drawer"):
                drawer.close_drawer()
            elif drawer is not None:
                drawer.close()
            # 한글 주석 — chat input focus 이동
            if hasattr(self, "_input_bar"):
                self._input_bar.setFocus()
        except Exception as exc:
            log.warning("저장한 메시지 진입 실패 — %r", exc)

    @pyqtSlot(bool)
    def _on_night_mode_toggled(self, on: bool) -> None:
        """cycle 169.411 — drawer 야간 모드 toggle handler (Phase 1 잔존 회수).

        Phase 1 scope = log + drawer visual 자체 retain. theme stylesheet swap 의 의 Phase 2+
        (현재 default dark retain — 주간 light theme 별 cycle 의무).
        """
        log.info("[main_window] night_mode_toggled — on=%s", on)
        # 한글 주석 — 추후 light theme swap chain 진입 위치. 본 cycle = drawer visual 만.

    @pyqtSlot()
    def _on_drawer_logout(self) -> None:
        """로그아웃 confirm — cycle 169.365 모달 ConfirmDialog (i18n + frameless + main center)."""
        try:
            from app.ui.confirm_dialog import ConfirmDialog
            dialog = ConfirmDialog(
                title_key="로그아웃",
                message_key="로그아웃_의무_어플_종료_다음_진입_시_재_로그인",
                parent=self,
            )
            result = self._exec_dialog_centered(dialog)
            if result == 1:
                self.close()
        except Exception as exc:
            log.warning("ConfirmDialog logout 실패 — %r", exc)

    @pyqtSlot()
    def _on_header_search(self) -> None:
        """ChatHeader 검색 button — cycle 169.63 ChatListPanel filter focus."""
        log.info("ChatHeader 검색 click — chat list filter focus")
        # 한글 주석 — chat_list_panel 안 search input focus + visible 보장
        if hasattr(self, "_chat_list_panel"):
            self._chat_list_panel._search_edit.setFocus()
            self._chat_list_panel._search_edit.selectAll()

    @pyqtSlot()
    def _on_header_call(self) -> None:
        """ChatHeader 통화 button — cycle 169.57 CallDialog + CallClient binding.

        음성 통화 default. 영상 toggle 가능. WebRTC SDP/ICE actual exchange =
        signaling chain 안 fire (별도 cycle).
        """
        log.info("ChatHeader 통화 click — CallDialog 진입")
        from app.ui.call_dialog import CallDialog
        from app.net.call_client import CallClient
        # cycle 169.331 — active chat 의 peer name lookup (사용자 critique image #94/95)
        peer = "상대 사용자"
        active_kind = getattr(self, "_active_chat_kind", None)
        active_target = getattr(self, "_active_chat_target_id", None)
        clp = getattr(self, "_chat_list_panel", None)
        if clp is not None and active_kind is not None:
            for entry in getattr(clp, "_entries", []):
                if entry.kind == active_kind and entry.target_id == active_target:
                    peer = entry.name or peer
                    break
        dialog = CallDialog(peer_name=peer, video_enabled=False, incoming=False, parent=self)
        stun_url = getattr(self._config, "stun_url", "stun:stun.l.google.com:19302")
        turn_url = getattr(self._config, "turn_url", "")
        turn_username = getattr(self._config, "turn_username", "")
        turn_credential = getattr(self._config, "turn_credential", "")
        # 한글 주석 — cycle 169.60 회수 — signaling_client + peer_id + TURN inject
        signaling = getattr(self, "_signaling_client", None)
        peer_id = getattr(self, "_active_peer_id", None)
        call_client = CallClient(
            stun_url=stun_url, signaling_client=signaling, peer_id=peer_id,
            turn_url=turn_url, turn_username=turn_username, turn_credential=turn_credential,
        )
        dialog.attach_client(call_client)
        self._active_call_client = call_client
        # 한글 주석 — 통화 시점 즉시 outgoing offer fire (peer_id 부재 시 placeholder mode)
        import asyncio
        try:
            asyncio.ensure_future(call_client.create_offer(video=False))
        except Exception as exc:
            log.warning("[call] create_offer schedule fail — %r", exc)
        # cycle 169.327 — _exec_dialog_centered chain (main outside protrude 차단 + backdrop + ESC)
        self._exec_dialog_centered(dialog)

    @pyqtSlot()
    def _on_header_remote(self) -> None:
        """원격 제어 icon → dropdown menu (원격 요청 + 원격 연결) — cycle 169.330 사용자 directive image #93."""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QCursor
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #131C30; color: #e5e7eb; border: 1px solid #1f2937; padding: 4px; }"
            "QMenu::item { padding: 8px 16px; border-radius: 4px; }"
            "QMenu::item:selected { background-color: #1F2937; }"
        )
        # 한글 주석 — 원격 요청 + 원격 연결 2 action
        act_request = menu.addAction("원격 요청")
        act_connect = menu.addAction("원격 연결")
        act_request.triggered.connect(self._on_remote_request)  # type: ignore[arg-type]
        act_connect.triggered.connect(self._on_remote_connect)  # type: ignore[arg-type]
        menu.exec(QCursor.pos())

    @pyqtSlot()
    def _on_remote_request(self) -> None:
        """원격 요청 → RemoteCallDialog (outgoing mode) — cycle 169.338 사용자 directive."""
        try:
            from app.ui.remote_call_dialog import RemoteCallDialog
            peer = "상대 사용자"
            clp = getattr(self, "_chat_list_panel", None)
            kind = getattr(self, "_active_chat_kind", None)
            tid = getattr(self, "_active_chat_target_id", None)
            if clp is not None and kind is not None:
                for e in getattr(clp, "_entries", []):
                    if e.kind == kind and e.target_id == tid:
                        peer = e.name or peer
                        break
            dialog = RemoteCallDialog(peer_name=peer, mode="request", parent=self)
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("RemoteCallDialog request 실패 — %r", exc)

    @pyqtSlot()
    def _on_remote_connect(self) -> None:
        """원격 연결 → RemoteCallDialog outgoing — 사용자 directive cycle 169.424 회수.

        이전 mode='incoming' 폐기 — incoming UI = 상대가 me 측 요청 시점 별 trigger (peer signal).
        dropdown 클릭 = outgoing 의무. layout = 원격 요청 same dialog (RemoteCallDialog request mode).
        """
        try:
            from app.ui.remote_call_dialog import RemoteCallDialog
            peer = "상대 사용자"
            clp = getattr(self, "_chat_list_panel", None)
            kind = getattr(self, "_active_chat_kind", None)
            tid = getattr(self, "_active_chat_target_id", None)
            if clp is not None and kind is not None:
                for e in getattr(clp, "_entries", []):
                    if e.kind == kind and e.target_id == tid:
                        peer = e.name or peer
                        break
            # cycle 169.424 — outgoing mode + status text 분기 (원격 연결 발신)
            dialog = RemoteCallDialog(
                peer_name=peer, mode="request", parent=self,
                outgoing_label="원격 연결 발신 중…",
            )
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("RemoteCallDialog connect 실패 — %r", exc)

    @pyqtSlot()
    def _on_header_menu(self) -> None:
        """ChatHeader 메뉴 button — kind 분기 dropdown (group/channel/friend) 사용자 directive image #102."""
        log.info("ChatHeader 메뉴 click")
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QCursor
        kind = getattr(self, "_active_chat_kind", None) or "friend"
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background-color: #131C30; color: #e5e7eb; border: 1px solid #1f2937; padding: 4px; }"
            "QMenu::item { padding: 8px 16px; border-radius: 4px; }"
            "QMenu::item:selected { background-color: #1F2937; }"
            "QMenu::separator { height: 1px; background: #1f2937; margin: 4px 0; }"
        )
        # cycle 169.334 — group/channel kind = telegram align 6 entry (image #102)
        if kind in ("group", "channel"):
            act_mute = menu.addAction("알림 끄기")
            menu.addSeparator()
            act_info = menu.addAction("그룹 정보 보기" if kind == "group" else "채널 정보 보기")
            act_manage = menu.addAction("그룹 관리" if kind == "group" else "채널 관리")
            act_poll = menu.addAction("설문 만들기")
            act_clear = menu.addAction("대화 내용 비우기")
            menu.addSeparator()
            act_leave = menu.addAction("삭제하고 나가기")
            act_info.triggered.connect(self._on_group_info)  # type: ignore[arg-type]
            act_manage.triggered.connect(lambda: log.info("[group_manage] placeholder"))  # type: ignore[arg-type]
            act_poll.triggered.connect(lambda: log.info("[group_poll] placeholder"))  # type: ignore[arg-type]
            act_clear.triggered.connect(self._on_chat_clear)  # type: ignore[arg-type]
            act_leave.triggered.connect(self._on_chat_leave)  # type: ignore[arg-type]
        else:
            menu.addAction("채팅 정보")
            menu.addAction("알림 끄기")
            menu.addSeparator()
            menu.addAction("채팅 나가기")
        menu.exec(QCursor.pos())

    @pyqtSlot()
    def _on_group_info(self) -> None:
        """그룹 정보 보기 — GroupInfoDialog open (cycle 169.334 image #103)."""
        try:
            from app.ui.group_info_dialog import GroupInfoDialog
            kind = getattr(self, "_active_chat_kind", "group")
            target_id = getattr(self, "_active_chat_target_id", 0)
            clp = getattr(self, "_chat_list_panel", None)
            name = "?"
            if clp is not None:
                for e in getattr(clp, "_entries", []):
                    if e.kind == kind and e.target_id == target_id:
                        name = e.name
                        break
            dialog = GroupInfoDialog(group_name=name, members=[], parent=self)
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("GroupInfoDialog open 실패 — %r", exc)

    @pyqtSlot()
    def _on_chat_clear(self) -> None:
        """대화 내용 비우기 — chat_view + dm_history reset."""
        log.info("[chat_clear] active=%s/%s", getattr(self, "_active_chat_kind", "?"), getattr(self, "_active_chat_target_id", "?"))
        try:
            self._chat_view.clear_messages()
            key = (getattr(self, "_active_chat_kind", None), getattr(self, "_active_chat_target_id", None))
            if hasattr(self, "_dm_history") and key in self._dm_history:
                self._dm_history[key] = []
        except Exception as exc:
            log.debug("chat_clear 실패 — %r", exc)

    @pyqtSlot()
    def _on_chat_leave(self) -> None:
        """삭제하고 나가기 — chat_list_panel entry remove + chat clear."""
        kind = getattr(self, "_active_chat_kind", None)
        target_id = getattr(self, "_active_chat_target_id", None)
        log.info("[chat_leave] kind=%s target=%s", kind, target_id)
        clp = getattr(self, "_chat_list_panel", None)
        if clp is None or kind is None:
            return
        entries = [e for e in getattr(clp, "_entries", []) if not (e.kind == kind and e.target_id == target_id)]
        clp.set_entries(entries)
        self._chat_view.clear_messages()

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

    @pyqtSlot(int)
    def _on_room_entered(self, room_id: int) -> None:
        """RoomList sidebar 의 더블 클릭 → 그룹 채팅 진입 (cycle 139 신설).

        Parameters
        ----------
        room_id : int
            진입 대상 room. RoomItem.room_id payload 그대로.

        흐름:

        1. 기존 GroupChatView 인스턴스가 있으면 deleteLater + Stack 의 idx 1 의
           placeholder 교체.
        2. 신규 GroupChatView 인스턴스 생성 (room_id + self_username 주입) +
           시그널 wire (message_send_requested / members_panel_requested).
        3. StackedWidget idx = 1 swap + 1:1 입력 영역 비활성 (그룹 모드 의무).
        4. AppState.set_identity 의 room_id 갱신.
        """

        log.info("[main_window] room_entered room_id=%s", room_id)

        # 1) 기존 GroupChatView 의 cleanup
        if self._group_chat_view is not None:
            self._stacked.removeWidget(self._group_chat_view)
            self._group_chat_view.deleteLater()
            self._group_chat_view = None

        # 2) 신규 GroupChatView
        self_username = self._config.user_nickname
        new_view = GroupChatView(
            room_id=room_id,
            room_title=f"Room #{room_id}",
            member_count=0,
            self_username=self_username,
            parent=self._stacked,
        )
        new_view.message_send_requested.connect(
            lambda body, rid=room_id: self._on_group_message_send(rid, body)
        )
        new_view.members_panel_requested.connect(self._on_open_members_panel)

        # 3) StackedWidget 의 idx 1 위치 swap — placeholder 제거 + 신규 insert
        self._stacked.insertWidget(self._STACK_GROUP_CHAT, new_view)
        # placeholder 가 idx 2 로 밀려나 있으면 cleanup (최초 swap 1회)
        if self._group_placeholder is not None:
            self._stacked.removeWidget(self._group_placeholder)
            self._group_placeholder.deleteLater()
            self._group_placeholder = None

        self._group_chat_view = new_view
        self._current_room_id = room_id
        # 한글 주석 — cycle 169.59 회수 — room entry 시 active_peer_id = room_id str 형식 set
        # group chat = room peer 단위 (mesh broadcast). 1:1 = signaling peer_joined 의 의 set.
        self._active_peer_id = f"room:{room_id}"

        # 4) StackedWidget swap + 1:1 입력 영역 비활성
        self._stacked.setCurrentIndex(self._STACK_GROUP_CHAT)
        self._input_container.setVisible(False)

        # 5) AppState 갱신
        self._state.set_identity(room_id=str(room_id), peer_id=self_username)

    # 한글 주석: 메시지 body 의 client-side 상한 — server _MAX_BODY_LEN (65535) 와 정합.
    _MAX_MESSAGE_BODY_LEN: int = 65535

    def _on_group_message_send(self, room_id: int, body: str) -> None:
        """GroupChatView 의 message_send_requested 핸들러 (cycle 142 actual chain).

        cycle 142 의 dual chain — REST POST + WebRTC mesh broadcast:

        1. body 검증 (빈 / max length cap / room_id 의 활성 검증)
        2. UI append (local echo) — caller 의 즉각 피드백 의무
        3. REST POST `/api/rooms/{room_id}/messages` — server 영속화 + audit
           (graceful fail = mesh-only 모드 진입 + warning log)
        4. WebRTC mesh broadcast — ``GroupMessageClient.send_message``
           (graceful fail = REST 의 의 fallback 유지)

        Notes
        -----
        - REST + mesh 둘 다 fail → UI append 는 보존 (사용자 가 작성 흔적 유지).
        - REST 성공 시 message_id 의 capture → ``self._last_message_id`` 보관
          (ack chain / 삭제 / 추적 의무).
        - asyncio running loop 부재 (test 환경 등) 시 background task 등록 skip
          + graceful log.debug.
        """

        # 1) body 검증 — 빈 / 상한 초과 / 활성 룸 부재
        if not body or not body.strip():
            log.debug("[main_window] group_message_send 빈 body — skip")
            return
        if len(body) > self._MAX_MESSAGE_BODY_LEN:
            log.warning(
                "[main_window] group_message_send body 길이 %d > %d — truncate",
                len(body),
                self._MAX_MESSAGE_BODY_LEN,
            )
            body = body[: self._MAX_MESSAGE_BODY_LEN]
        if room_id <= 0:
            log.warning(
                "[main_window] group_message_send room_id 무효 — %s", room_id
            )
            return

        log.debug(
            "[main_window] group_message_send room=%s body_len=%d",
            room_id,
            len(body),
        )

        # 2) UI append — local echo (REST/mesh 결과 무관 의 즉각 피드백)
        if self._group_chat_view is not None:
            self._group_chat_view.append_message(
                sender=self._config.user_nickname,
                text=body,
                ts=datetime.now(),
                is_self=True,
            )

        # 3) REST POST + 4) mesh broadcast — async 의무, background task 의무
        loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            # 한글 주석: pytest 등 의 running loop 부재 환경 — graceful skip.
            log.debug(
                "[main_window] asyncio running loop 부재 — REST/mesh chain skip"
            )
            return

        asyncio.ensure_future(
            self._dispatch_message_chain(room_id=room_id, body=body), loop=loop
        )

    async def _dispatch_message_chain(self, *, room_id: int, body: str) -> None:
        """REST POST + mesh broadcast 의 async chain (cycle 142 신설).

        Parameters
        ----------
        room_id : int
            대상 room.id.
        body : str
            text 본문 — caller 영역 정규화 완료 의 의무.

        흐름
        ----
        1. REST POST `/api/rooms/{room_id}/messages` — server 영속화 + audit.
           응답 의 ``message_id`` 의 capture → ``self._last_message_id``.
        2. WebRTC mesh broadcast — GroupMessageClient.send_message.
        3. REST fail 시 mesh-only 모드 (warning log + mesh 계속 진행).
        4. mesh fail 시 REST 의 성공 보존 — server 영속화 만으로 chain 종료.
        5. 둘 다 fail = warning log + UI 의 local echo 만 보존 (직전 단계).
        """

        rest_ok = False
        # 한글 주석: REST POST chain — graceful fail = mesh-only fallback
        if self._messages_client is not None:
            try:
                resp = await self._messages_client.post_message(room_id, body)
                if isinstance(resp, dict):
                    msg_id = resp.get("message_id")
                    if isinstance(msg_id, int):
                        self._last_message_id = msg_id
                        log.info(
                            "[main_window] REST POST PASS room=%s message_id=%s",
                            room_id,
                            msg_id,
                        )
                rest_ok = True
            except Exception as exc:  # noqa: BLE001
                # 한글 주석: REST 401/403/500/network 모두 mesh-only fallback
                log.warning(
                    "[main_window] REST POST FAIL room=%s — mesh-only 모드 진입 (%r)",
                    room_id,
                    exc,
                )
        else:
            log.debug(
                "[main_window] messages_client 미주입 — REST skip + mesh-only"
            )

        # 한글 주석: WebRTC mesh broadcast — GroupMessageClient.send_message
        if self._group_message_client is not None:
            try:
                sender_id = self._current_user_id or 0
                await self._group_message_client.send_message(body, sender_id)
                log.debug(
                    "[main_window] mesh broadcast PASS room=%s rest_ok=%s",
                    room_id,
                    rest_ok,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    "[main_window] mesh broadcast FAIL room=%s rest_ok=%s — %r",
                    room_id,
                    rest_ok,
                    exc,
                )
        else:
            log.debug(
                "[main_window] group_message_client 미주입 — mesh broadcast skip"
            )

    @pyqtSlot()
    def _on_open_members_panel(self) -> None:
        """GroupChatView 의 members_panel_requested 핸들러 — MemberList toggle."""

        if self._current_room_id is None:
            return
        log.debug(
            "[main_window] open_members_panel room=%s", self._current_room_id
        )
        # cycle 139 stub — 빈 멤버 목록 으로 swap (RoomsClient.get_room binding 별개 cycle)
        self._member_list.set_members([], viewer_role="member")
        self._stacked.setCurrentIndex(self._STACK_MEMBERS)

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

    @pyqtSlot(int, int)
    def _on_invite_requested(self, room_id: int, friend_user_id: int) -> None:
        """InviteDialog 의 invite_requested 시그널 핸들러 — REST POST chain.

        Parameters
        ----------
        room_id : int
            초대 대상 room.id.
        friend_user_id : int
            초대 대상 users.id (dropdown 선택).

        흐름
        ----
        1. rooms_client 주입 검증 — 부재 시 warning + status bar feedback.
        2. asyncio running loop 가용 시 ``invite_user`` background task 등록.
        3. 성공 시 ``_on_invite_complete`` → MemberList 갱신 (get_room 재호출).
        """

        log.info(
            "[main_window] invite_requested room=%s friend_user_id=%s",
            room_id,
            friend_user_id,
        )

        if self._rooms_client is None:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(
                self, "TooTalk", "rooms_client 미주입 — 초대 차단"
            )
            return

        loop: Optional[asyncio.AbstractEventLoop] = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is None:
            log.debug(
                "[main_window] asyncio running loop 부재 — invite REST skip"
            )
            return

        asyncio.ensure_future(
            self._dispatch_invite_chain(
                room_id=room_id, friend_user_id=friend_user_id
            ),
            loop=loop,
        )

    async def _dispatch_invite_chain(
        self, *, room_id: int, friend_user_id: int
    ) -> None:
        """invite_user REST + MemberList 갱신 의 async chain.

        Parameters
        ----------
        room_id : int
            초대 대상 room.id.
        friend_user_id : int
            초대 대상 users.id.

        흐름
        ----
        1. ``RoomsClient.invite_user`` 호출 — 성공 시 peer_id 응답.
        2. 성공 시 ``RoomsClient.get_room`` 재호출 — 멤버 list 갱신.
        3. MemberList 의 ``set_members`` 호출 (viewer_role 추적).
        4. 403 (owner 만 가능) / 409 (이미 참여) / network err 의 graceful catch.
        """

        try:
            peer_id = await self._rooms_client.invite_user(
                room_id, friend_user_id
            )
            log.info(
                "[main_window] invite_user PASS room=%s friend=%s peer_id=%s",
                room_id,
                friend_user_id,
                peer_id,
            )
            self._status_bar.showMessage(
                f"초대 완료 — friend_id={friend_user_id} peer_id={peer_id}",
                3000,
            )
        except Exception as exc:  # noqa: BLE001
            # 한글 주석: 403/409/network 의 통합 graceful catch + 사용자 통보.
            msg = f"초대 실패 — {exc}"
            log.warning(
                "[main_window] invite_user FAIL room=%s friend=%s: %r",
                room_id,
                friend_user_id,
                exc,
            )
            self._status_bar.showMessage(msg, 4000)
            return

        # 한글 주석: MemberList 갱신 — get_room 재호출 + set_members.
        try:
            _room, members = await self._rooms_client.get_room(room_id)
            from app.ui.member_list import MemberItem  # lazy import (graceful)

            member_items = [
                MemberItem(
                    user_id=int(m.user_id),
                    username=f"user_{m.user_id}",
                    role=str(getattr(m, "role", "member")),
                    is_online=False,
                )
                for m in members
            ]
            viewer_role = "member"
            if self._current_user_id is not None:
                for m in members:
                    if int(m.user_id) == int(self._current_user_id):
                        viewer_role = str(getattr(m, "role", "member"))
                        break
            self._member_list.set_members(
                member_items, viewer_role=viewer_role
            )
            log.debug(
                "[main_window] MemberList refresh room=%s count=%d viewer_role=%s",
                room_id,
                len(member_items),
                viewer_role,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[main_window] get_room 재호출 FAIL room=%s — MemberList skip (%r)",
                room_id,
                exc,
            )

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

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt 규약
        """윈도우 종료 시점 훅.

        cycle 139 — auto-update background task 의 cancel + cleanup.
        """

        log.info("MainWindow 종료 — Qt 이벤트 루프 정리 단계 진입")
        # 한글 주석: auto-update background task 정상 cancel (cycle 139)
        self._cancel_update_task()
        super().closeEvent(event)
