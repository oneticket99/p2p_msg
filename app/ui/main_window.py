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
        self._session_token: Optional[str] = None
        self._current_user_id: Optional[int] = None
        # cycle 148 — 현재 user 의 service-wide role (admin / owner / member).
        # admin / owner 만 "관리자" 메뉴 가시 + emoji moderation dialog 진입 path.
        # 로그인 응답 의 role 의 caller 의 set_user_role 갱신 의무 (별개 cycle 의 chain).
        self._current_user_role: str = "member"
        # cycle 139 — 현재 활성 그룹 채팅 방 의 GroupChatView (방 전환 시 swap)
        self._group_chat_view: Optional[GroupChatView] = None
        self._current_room_id: Optional[int] = None
        # cycle 142 — 가장 최근 REST POST 응답 의 message_id capture (UI / 추후 ack chain)
        self._last_message_id: Optional[int] = None

        # 0-1) 시그니처 사운드 player — Config 의 sound_* 3 필드 기반 init
        self._sound_player: SoundPlayer = SoundPlayer(config)

        # 1) 윈도우 기본 속성
        self.setWindowTitle("TooTalk")
        self.setMinimumSize(720, 640)  # cycle 139 sidebar 추가로 가로 확장

        # 2) 중앙 위젯 — QSplitter 3 column (rail | room_list | right_panel)
        # cycle 153.4 phase 3 통합 — SidebarRail (64px) + RoomListWidget (220~320px) + ChatHeader + stacked
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setContentsMargins(0, 0, 0, 0)

        # 3-1) 좌측 rail — SidebarRail (cycle 153 phase 3 신설)
        # 한글 주석 — 4 tab (👥 친구 + 🏠 방 + 🤖 봇 + ⚙️ 설정) + tab_clicked signal
        from app.ui.sidebar_rail import SidebarRail
        self._sidebar_rail = SidebarRail(parent=splitter)
        self._sidebar_rail.tab_clicked.connect(self._on_sidebar_tab_clicked)  # type: ignore[arg-type]

        # 3-2) 중앙 sidebar — RoomListWidget (cycle 139 신설, 보존)
        self._room_list = RoomListWidget(parent=splitter)
        self._room_list.setMinimumWidth(220)
        self._room_list.setMaximumWidth(320)
        self._room_list.room_entered.connect(self._on_room_entered)
        self._room_list.set_rooms([])

        # 4) 우측 — ChatHeader (cycle 153 phase 3 신설) + QStackedWidget + 입력 영역 컨테이너
        right_panel = QWidget(splitter)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 4-0) ChatHeader top bar (56px) — cycle 153 phase 3 신설
        from app.ui.chat_header import ChatHeader
        self._chat_header = ChatHeader(parent=right_panel)
        self._chat_header.search_clicked.connect(self._on_header_search)  # type: ignore[arg-type]
        self._chat_header.call_clicked.connect(self._on_header_call)  # type: ignore[arg-type]
        self._chat_header.menu_clicked.connect(self._on_header_menu)  # type: ignore[arg-type]
        right_layout.addWidget(self._chat_header)

        self._stacked = QStackedWidget(right_panel)
        right_layout.addWidget(self._stacked, stretch=1)

        # 4-1) ChatView (1:1) — index 0 (기존 호환 유지)
        self._chat_view = ChatView(
            parent=self._stacked,
            sound_player=self._sound_player,
            reactions_client=self._reactions_client,
        )
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
        splitter.addWidget(self._sidebar_rail)
        splitter.addWidget(self._room_list)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)  # rail fixed
        splitter.setStretchFactor(1, 0)  # room_list resizable
        splitter.setStretchFactor(2, 1)  # right_panel flex

        self.setCentralWidget(splitter)

        # 7) StatusBar
        self._status_bar = StatusBar(parent=self)
        self.setStatusBar(self._status_bar)
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
        if not self._is_admin_role():
            QMessageBox.warning(
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
            QMessageBox.warning(
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
            QMessageBox.warning(self, "TooTalk", "AuthClient 미초기화 — main 진입점 의무")
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
            log.info("[main_window] 로그인 PASS user_id=%s", self._current_user_id)
            QMessageBox.information(
                self, "TooTalk", f"로그인 완료. user_id={self._current_user_id}"
            )

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

        if self._session_token is None:
            QMessageBox.information(self, "TooTalk", "로그인 상태 아님")
            return
        self._session_token = None
        self._current_user_id = None
        QMessageBox.information(self, "TooTalk", "로그아웃 완료")

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
        self._stacked.setCurrentIndex(self._STACK_FRIENDS)
        log.info(
            "[main_window] friend_list page 활성 viewer_id=%d", viewer_id
        )

    def _on_open_add_friend(self) -> None:
        """"친구 추가" 메뉴 슬롯 — AddFriendDialog 의 모달 실행."""

        if self._session_token is None:
            QMessageBox.warning(
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

        tab_key ∈ {"friends", "rooms", "bots", "settings"}
        """
        # 한글 주석 — friends tab = FriendListWidget index 3 / rooms = direct chat default
        if tab_key == "friends":
            self._stacked.setCurrentIndex(self._STACK_FRIENDS)
            self._chat_header.set_chat("친구 목록", "", "👥")
        elif tab_key == "rooms":
            self._stacked.setCurrentIndex(self._STACK_DIRECT_CHAT)
            self._chat_header.clear_chat()
        elif tab_key == "bots":
            # 한글 주석 — bots tab = BotPanel widget instantiate + stacked 안 inject (cycle 153.5)
            self._chat_header.set_chat("봇 디렉토리", "cycle 150~160 base", "🤖")
            if not hasattr(self, "_bot_panel_idx"):
                from app.ui.bot_panel import BotPanel
                bot_panel = BotPanel(parent=self._stacked)
                # cycle 153.8 — command click → InputBar text inject chain
                bot_panel.command_invoked.connect(self._on_bot_command_invoked)  # type: ignore[arg-type]
                self._bot_panel_idx = self._stacked.addWidget(bot_panel)
            self._stacked.setCurrentIndex(self._bot_panel_idx)
        elif tab_key == "settings":
            # 한글 주석 — settings tab = SettingsDialog modal open (cycle 153.5)
            self._chat_header.set_chat("설정", "10 section tabbed", "⚙️")
            try:
                dialog = SettingsDialog(sound_player=self._sound_player, parent=self)
                dialog.exec()
            except Exception as exc:  # pragma: no cover - graceful
                log.debug("SettingsDialog open 실패 graceful — %r", exc)
            # 한글 주석 — dialog close 후 sidebar tab default friends 복귀
            self._sidebar_rail.set_active_tab("friends")
            self._on_sidebar_tab_clicked("friends")

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

    @pyqtSlot(str, str)
    def _on_bot_command_invoked(self, bot_username: str, command: str) -> None:
        """BotPanel command click → InputBar text inject + send chain."""
        # 한글 주석 — bot command 본문 = "/command @bot_username" pattern
        message = f"{command} @{bot_username}"
        try:
            if hasattr(self, "_input_bar"):
                self._input_bar._text_edit.setPlainText(message)
                self._input_bar._text_edit.setFocus()
            log.info("bot command inject — %s %s", command, bot_username)
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("bot command inject 실패 — %r", exc)

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
        """profile 메시지 button → modal close + chat 진입 (cycle 154.2)."""
        modal.accept()
        # 한글 주석 — 1:1 chat 진입 — friend_chat_clicked 등가 path 이미 main_window 안 처리
        self._stacked.setCurrentIndex(self._STACK_DIRECT_CHAT)
        self._chat_header.set_chat(f"friend #{friend_id}", "online", "👤")

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
        from PyQt6.QtWidgets import QMessageBox
        confirm = QMessageBox.question(
            self,
            "TooTalk",
            f"friend #{friend_id} 차단?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            client = getattr(self, "_friends_client", None)
            if client is not None:
                import asyncio
                try:
                    asyncio.ensure_future(client.block(friend_id))  # type: ignore[attr-defined]
                except Exception as exc:  # pragma: no cover - graceful
                    log.debug("block chain 실패 — %r", exc)
            modal.accept()

    @pyqtSlot()
    def _on_header_search(self) -> None:
        """ChatHeader 검색 button — cycle 154+ entry."""
        log.info("ChatHeader 검색 click — cycle 154+ entry")

    @pyqtSlot()
    def _on_header_call(self) -> None:
        """ChatHeader 통화 button — cycle 200+ entry (WebRTC SDP)."""
        log.info("ChatHeader 통화 click — cycle 200+ entry")

    @pyqtSlot()
    def _on_header_menu(self) -> None:
        """ChatHeader 메뉴 button — context menu (cycle 153.5+ entry)."""
        log.info("ChatHeader 메뉴 click — cycle 153.5+ entry")

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

        self._chat_view.add_message(
            sender=self._config.user_nickname,
            text=text,
            ts=datetime.now(),
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
            QMessageBox.warning(self, "TooTalk", "초대 = 그룹 방 진입 의무")
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
            QMessageBox.warning(
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
        """환경설정 다이얼로그 — 시그니처 사운드 음소거/볼륨 즉시 반영."""

        dialog = SettingsDialog(sound_player=self._sound_player, parent=self)
        result = dialog.exec()
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

        QMessageBox.about(
            self,
            "TooTalk 정보",
            (
                "<h3>TooTalk</h3>"
                f"<p>버전: {app_version}</p>"
                "<p>PyQt6 기반 데스크탑 P2P 메신저 (WebRTC DataChannel 직결).</p>"
                "<p>코드명: p2p_msg · Phase 1 MVP</p>"
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
