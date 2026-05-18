# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk 메인 윈도우 — QMainWindow 상속.

레이아웃:

```
+--------------------------------------------------+
| 메뉴바: 설정 · About                              |
+--------------------------------------------------+
|                                                  |
|   ChatView (QScrollArea + QVBoxLayout)           |
|   ─ MessageBubble 가 차곡차곡 쌓이는 영역         |
|                                                  |
+--------------------------------------------------+
| [📎]  [메시지 입력 QLineEdit            ] [보내기] |
+--------------------------------------------------+
| StatusBar: 연결 상태 · peer 수                    |
+--------------------------------------------------+
```

- 메뉴바: 사용자가 room/peer_id 를 입력하는 "설정" 다이얼로그 진입점과
  버전/저작권 정보 "About" 다이얼로그 진입점을 제공한다.
- 첨부 버튼(📎): Phase 1 후반 (Task #16) 에서 이미지/파일 송신 다이얼로그를
  열도록 활성화 예정. 본 스켈레톤에서는 placeholder 슬롯만 보유.
- 보내기 버튼: 입력창 텍스트를 ChatView 에 echo 한다. 본 Phase 1 스켈레톤
  단계에서는 실제 DataChannel 송신 코드가 없으므로 로컬 echo 로 동작하며,
  Task #16 에서 WebRTC DataChannel send() 호출로 대체된다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.app_state import AppState
from app.core.config import Config
from app.net.auth_client import AuthClient
from app.ui.chat_view import ChatView
from app.ui.login_dialog import LoginDialog
from app.ui.password_reset_dialog import PasswordResetDialog
from app.ui.settings_dialog import SettingsDialog
from app.ui.signup_dialog import SignupDialog
from app.ui.sound_player import SoundPlayer
from app.ui.status_bar import StatusBar

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """TooTalk 최상위 윈도우.

    본 위젯은 ``app.core.AppState`` 인스턴스를 보유하여 현재 room/peer_id/
    연결 상태를 추적하고, ``app.ui.chat_view.ChatView`` 와 ``StatusBar`` 의
    상위 컨테이너 역할을 한다.

    Qt slot 내부 동기 코드만 사용하며, 시그널링 IO 는 ``asyncio.create_task``
    를 통해 ``app.net.signaling_client`` 의 코루틴을 예약한다 (정본 §E).
    """

    def __init__(
        self,
        config: Config,
        parent: Optional[QWidget] = None,
        *,
        auth_client: Optional[AuthClient] = None,
    ) -> None:
        """초기 위젯 트리 구성 + 메뉴/StatusBar/입력 영역 배치.

        Parameters
        ----------
        config : Config
            ``.env`` 로딩 결과. signaling_url/stun_url/user_nickname 등.
        parent : QWidget | None
            상위 위젯 (보통 None).
        """

        super().__init__(parent)

        # 0) 외부 의존 보관
        self._config: Config = config
        self._state: AppState = AppState.instance()
        self._auth_client: Optional[AuthClient] = auth_client
        self._session_token: Optional[str] = None
        self._current_user_id: Optional[int] = None

        # 0-1) 시그니처 사운드 player — Config 의 sound_* 3 필드 기반 init
        # (사이클 38~40 chain — wrapper + ChatView trigger + SettingsDialog)
        self._sound_player: SoundPlayer = SoundPlayer(config)

        # 1) 윈도우 기본 속성 — 명명 규약 정합: UI 표기는 "TooTalk"
        self.setWindowTitle("TooTalk")
        self.setMinimumSize(480, 640)

        # 2) 중앙 위젯 + 수직 레이아웃
        central = QWidget(self)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 3) ChatView — 스크롤 가능한 메시지 리스트 + SoundPlayer 의 peer 수신 trigger inject
        self._chat_view = ChatView(parent=central, sound_player=self._sound_player)
        root_layout.addWidget(self._chat_view, stretch=1)

        # 4) 입력 영역 (첨부 + 입력창 + 보내기)
        input_row = QHBoxLayout()
        input_row.setContentsMargins(8, 8, 8, 8)
        input_row.setSpacing(8)

        self._attach_button = QPushButton("📎", parent=central)
        self._attach_button.setToolTip("이미지/파일 첨부 (Phase 1 후반 활성)")
        self._attach_button.setFixedWidth(36)
        # Phase 1 스켈레톤 단계는 비활성 — Task #16 에서 활성화
        self._attach_button.setEnabled(False)

        self._input_edit = QLineEdit(parent=central)
        self._input_edit.setPlaceholderText("메시지를 입력하세요…")
        # Enter 키로 송신 트리거 — returnPressed 시그널 사용
        self._input_edit.returnPressed.connect(self._on_send_clicked)

        self._send_button = QPushButton("보내기", parent=central)
        self._send_button.clicked.connect(self._on_send_clicked)

        input_row.addWidget(self._attach_button)
        input_row.addWidget(self._input_edit, stretch=1)
        input_row.addWidget(self._send_button)

        input_container = QWidget(central)
        input_container.setLayout(input_row)
        root_layout.addWidget(input_container, stretch=0)

        self.setCentralWidget(central)

        # 5) StatusBar — 연결 상태 + peer 수
        self._status_bar = StatusBar(parent=self)
        self.setStatusBar(self._status_bar)
        self._status_bar.set_connection_state("DISCONNECTED")
        self._status_bar.set_peer_count(0)

        # 6) 메뉴바 (설정 / About)
        self._build_menu_bar()

        # 7) 초기 안내 메시지 한 줄
        self._chat_view.add_message(
            sender="system",
            text=f"TooTalk 클라이언트 준비 완료 — 닉네임: {config.user_nickname}",
            ts=datetime.now(),
            is_self=False,
        )

    # ------------------------------------------------------------------
    # 메뉴 구성
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        """상단 메뉴바 구성 — "설정" 과 "About" 두 진입점."""

        menubar = self.menuBar()

        # "설정" 메뉴 — room/peer_id 입력 다이얼로그 + 종료
        menu_settings = menubar.addMenu("설정")

        act_room = QAction("방 입장…", self)
        act_room.setShortcut(QKeySequence("Ctrl+R"))
        act_room.triggered.connect(self._on_open_room_dialog)
        menu_settings.addAction(act_room)

        # 사운드/UI 의 사용자 control (사이클 40 신설, 41 wire)
        act_pref = QAction("환경설정…", self)
        act_pref.setShortcut(QKeySequence("Ctrl+,"))
        act_pref.triggered.connect(self._on_open_settings_dialog)
        menu_settings.addAction(act_pref)

        menu_settings.addSeparator()

        act_quit = QAction("종료", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        menu_settings.addAction(act_quit)

        # "계정" 메뉴 — 회원가입/로그인/비번 재설정/로그아웃 (사이클 23)
        menu_account = menubar.addMenu("계정")

        act_signup = QAction("회원가입…", self)
        act_signup.triggered.connect(self._on_open_signup)
        menu_account.addAction(act_signup)

        act_login = QAction("로그인…", self)
        act_login.setShortcut(QKeySequence("Ctrl+L"))
        act_login.triggered.connect(self._on_open_login)
        menu_account.addAction(act_login)

        act_reset = QAction("비밀번호 재설정…", self)
        act_reset.triggered.connect(self._on_open_reset)
        menu_account.addAction(act_reset)

        menu_account.addSeparator()

        act_logout = QAction("로그아웃", self)
        act_logout.triggered.connect(self._on_logout)
        menu_account.addAction(act_logout)

        # "도움말" 메뉴 — About
        menu_help = menubar.addMenu("도움말")
        act_about = QAction("TooTalk 정보…", self)
        act_about.triggered.connect(self._on_show_about)
        menu_help.addAction(act_about)

    # ------------------------------------------------------------------
    # Qt slot — 사용자 입력 핸들러
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

    @pyqtSlot()
    def _on_send_clicked(self) -> None:
        """보내기 버튼 / Enter 키 슬롯.

        입력창 텍스트를 가져와 ChatView 에 self 발신으로 추가한다. 본 Phase
        스켈레톤에서는 echo 처리만 수행하며, 실제 WebRTC DataChannel 송신은
        Task #16 에서 활성화한다.
        """

        text = self._input_edit.text().strip()
        if not text:
            return

        self._chat_view.add_message(
            sender=self._config.user_nickname,
            text=text,
            ts=datetime.now(),
            is_self=True,
        )
        self._input_edit.clear()

        # TODO(Task #16): DataChannel 송신 코루틴 예약
        # asyncio.create_task(self._datachannel.send(text))

    @pyqtSlot()
    def _on_open_settings_dialog(self) -> None:
        """환경설정 다이얼로그 — 시그니처 사운드 음소거/볼륨 즉시 반영.

        ``SettingsDialog`` 의 accept() 안에서 ``apply_to_player`` 가
        ``SoundPlayer.set_enabled`` + ``set_volume`` 을 호출하므로 본 메서드는
        단순 modal 호출 + 결과 로깅만 수행. Phase 3 의 user_settings table
        영속화 시 이 자리에서 DB 저장 코루틴 추가 예정.
        """

        dialog = SettingsDialog(sound_player=self._sound_player, parent=self)
        result = dialog.exec()
        log.debug("SettingsDialog 종료 — result=%s", result)

    @pyqtSlot()
    def _on_open_room_dialog(self) -> None:
        """"방 입장" 다이얼로그 — room_id 와 peer_id 를 사용자에게 입력받는다.

        본 Phase 스켈레톤에서는 입력값을 ``AppState`` 에 저장만 하고 시그널링
        연결은 수행하지 않는다. 실제 ``SignalingClient.connect() + join()``
        호출은 Task #16 에서 ``asyncio.create_task`` 로 예약한다.
        """

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
    # 윈도우 종료 훅 — 정상 종료 시 시그널링 LEAVE 송신 (Task #16)
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt 규약
        """윈도우 종료 시점 훅.

        Task #16 에서 ``SignalingClient.disconnect()`` 코루틴을 예약하고
        이벤트 루프 종료 처리를 추가한다. 본 스켈레톤은 로그만 남긴다.
        """

        log.info("MainWindow 종료 — Qt 이벤트 루프 정리 단계 진입")
        super().closeEvent(event)
