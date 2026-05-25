# SPDX-License-Identifier: GPL-3.0-or-later
"""MenuActionsMixin — 메뉴/페이지 진입 slot 5 method (cycle 169.528 신설).

codex 2.5 13차 — main_window.py 책임 분리 batch.

분리 대상 method (cycle 139/144/169.106 origin):
- `_on_open_friend_list()` — FriendListWidget page 활성 + chat_list refresh
- `_on_open_direct_chat()` — 1:1 직접 메시지 페이지 진입
- `_on_open_settings_dialog()` — SettingsDialog modal (centered)
- `_on_show_about()` — About 다이얼로그 (서비스명/버전/라이선스)

cycle 169.838 — "방 입장"(room_id/peer_id 직접 입력) 제거. 그룹방은 채팅창의
"그룹 만들기" + 멤버 초대로만 생성하므로 `_on_open_room_dialog` 핸들러 전수 삭제.

본 mixin 안 의존:
- `self._friend_list`, `self._stacked`, `self._STACK_FRIENDS`, `self._STACK_DIRECT_CHAT`
- `self._input_container`, `self._current_user_id`
- `self._sound_player`, `self._state`, `self._config`, `self._chat_view`
- `self._refresh_chat_list_panel()` (ChatNavigationMixin)
- `self._exec_dialog_centered()` (DialogCenterMixin)
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSlot

from app.ui.settings_dialog import SettingsDialog

log = logging.getLogger(__name__)


class MenuActionsMixin:
    """메뉴/페이지 진입 + about/room/settings dialog chain mixin (cycle 169.528)."""

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

    @pyqtSlot()
    def _on_open_direct_chat(self) -> None:
        """1:1 직접 메시지 페이지 회귀 (cycle 139 신설)."""

        self._stacked.setCurrentIndex(self._STACK_DIRECT_CHAT)
        self._input_container.setVisible(True)
        log.debug("[main_window] direct chat 페이지 진입")

    @pyqtSlot()
    def _on_open_settings_dialog(self) -> None:
        """환경설정 다이얼로그 — 시그니처 사운드 음소거/볼륨 즉시 반영.

        cycle 169.250 — _exec_dialog_centered apply (main embed center + 사용자 critique image #10 회수).
        """

        dialog = SettingsDialog(sound_player=self._sound_player, parent=self)
        result = self._exec_dialog_centered(dialog)
        log.debug("SettingsDialog 종료 — result=%s", result)

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
