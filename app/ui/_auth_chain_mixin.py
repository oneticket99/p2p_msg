# SPDX-License-Identifier: GPL-3.0-or-later
"""AuthChainMixin — 회원가입/로그인/비번재설정/로그아웃 6 method chain (cycle 169.526 신설).

계층 위치 — app/ui MainWindow mixin(정본 §E). main_window 책임 분리 단위 — MRO 합성.
AuthClient(net) + dialog 3종(Signup/Login/PasswordReset) 결선 + 세션 토큰 보관 진입점.

codex 2.5 LOW 진입 11차 — main_window.py 책임 분리 batch.

분리 대상 method (cycle 144 origin):
- `_require_auth_client()` — AuthClient 미주입 경고
- `_on_open_signup()` — SignupDialog modal
- `_on_open_login()` — LoginDialog modal + 세션 토큰 보관 + post_login_refresh 진입
- `_post_login_refresh()` — friend/room server fetch + chat_list populate
- `_on_open_reset()` — PasswordResetDialog modal
- `_on_logout()` — 세션 폐기 + LoginDialog re-spawn (TrayMixin chain)

본 mixin 안 의존:
- `self._auth_client`, `self._friends_client`, `self._rooms_client`
- `self._session_token`, `self._current_user_id`
- `self._friend_list`, `self._rooms_cache`
- `self._refresh_chat_list_panel()`, `self._fetch_unread_counts()`, `self._refresh_pending_badge()`
- `self._perform_logout_and_relogin()` (TrayMixin)
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import pyqtSlot

from app.net.auth_client import AuthClient
from app.ui.login_dialog import LoginDialog
from app.ui.password_reset_dialog import PasswordResetDialog
from app.ui.signup_dialog import SignupDialog
# cycle 169.834 — user-facing 문구 i18n 바인딩 (labels.tr 5언어 dict 조회)
from app.i18n import labels as _i18n_labels

log = logging.getLogger(__name__)


class AuthChainMixin:
    """회원가입/로그인/재설정/로그아웃 chain mixin (cycle 169.526)."""

    def _require_auth_client(self) -> Optional[AuthClient]:
        """AuthClient 미주입 시 경고."""

        if self._auth_client is None:
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_warning(
                self, "TooTalk", _i18n_labels.tr("msg_auth_client_unavailable")
            )
            return None
        return self._auth_client

    @pyqtSlot()
    def _on_open_signup(self) -> None:
        """회원가입 다이얼로그."""

        client = self._require_auth_client()
        if client is None:
            return
        dialog = SignupDialog(client, self)
        # cycle 169.838 — 별도 OS 윈도우 .exec() → 메인 레이아웃 안 in-app overlay 모달.
        self._exec_dialog_centered(dialog)

    @pyqtSlot()
    def _on_open_login(self) -> None:
        """로그인 다이얼로그 — PASS 시 세션 토큰 보관."""

        client = self._require_auth_client()
        if client is None:
            return
        dialog = LoginDialog(client, self)
        # cycle 169.838 — 별도 OS 윈도우 .exec() → 메인 레이아웃 안 in-app overlay 모달.
        # 반환값(int) == DialogCode.Accepted 비교 패턴 유지.
        if self._exec_dialog_centered(dialog) == dialog.DialogCode.Accepted:
            self._session_token = dialog.token
            self._current_user_id = dialog.user_id
            # cycle 169.271 — 사용자 critique bot 401 root cause trace
            log.warning(
                "[main_window] _session_token set token_present=%s token_len=%d user_id=%s",
                bool(self._session_token), len(self._session_token or ""), self._current_user_id,
            )
            log.info("[main_window] 로그인 PASS user_id=%s", self._current_user_id)
            # cycle 169.831 — 로그인 직후 계정 메뉴 가시성 재토글 (회원가입/로그인 숨김)
            if hasattr(self, "apply_auth_menu_visibility"):
                self.apply_auth_menu_visibility()
            # cycle 169.107 회수 — login PASS 직후 friend/room server fetch chain
            self._post_login_refresh()
            from app.ui.confirm_dialog import ConfirmDialog
            ConfirmDialog.show_info(
                self, "TooTalk", _i18n_labels.tr("msg_login_done")
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
                        # cycle 169.843 M3 — room 적재 source-of-truth = _rooms_cache.
                        # cycle 169.845 M5 — legacy _room_list.set_rooms 병행 호출 회수
                        # (RoomListWidget 제거). _refresh_chat_list_panel 가 본 cache 를 읽는다.
                        self._rooms_cache = list(rooms)
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
        # cycle 169.838 — 별도 OS 윈도우 .exec() → 메인 레이아웃 안 in-app overlay 모달.
        self._exec_dialog_centered(PasswordResetDialog(client, self))

    @pyqtSlot()
    def _on_logout(self) -> None:
        """세션 토큰 폐기 + LoginDialog re-spawn (cycle 169.498)."""

        from app.ui.confirm_dialog import ConfirmDialog
        if self._session_token is None:
            ConfirmDialog.show_info(self, "TooTalk", _i18n_labels.tr("msg_not_logged_in"))
            return
        # tray menu logout 과 동일 chain 호출 (TrayMixin._perform_logout_and_relogin 단일화)
        self._perform_logout_and_relogin()
