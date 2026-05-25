# SPDX-License-Identifier: GPL-3.0-or-later
"""MenuBarMixin — menubar 구성 + admin emoji moderation chain (cycle 169.520 신설).

codex 2.5 HIGH 진입 6차 — main_window.py 책임 분리.
cavecrew-investigator verdict — 327 line, LOW risk (UI-only).

분리 대상 method (cycle 148 origin):
- `_build_menu_bar()` — 상단 메뉴바 구성 (설정 + 계정 + 도움말 + 관리자 4 menu)
- `_is_admin_role()` — role 검사 helper
- `set_user_role(role)` — public role 갱신 + admin menu rebuild trigger
- `_rebuild_admin_menu()` — admin 메뉴 가시성 재구성
- `_on_open_emoji_moderation()` — admin emoji moderation dialog 진입
- `_dispatch_moderation_queue_fetch(*, dialog, base_url, admin_token)` — async fetch helper
- `_on_moderation_decision(pack_id, decision)` — decision_made signal handler

본 mixin 안 의존 attribute:
- `_current_user_role`, `_menu_admin`, `_act_emoji_moderation`
- `_auth_client`, `_status_bar`, `_current_moderation_dialog`
- 다수 메뉴 callback (self._on_open_*, self._on_logout 등 — TrayMixin/FriendSearchMixin retain)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QAction, QKeySequence

from app.i18n.labels import tr as _tr

# 한글 주석 — main_window 안 정의된 default URL retain
_DEFAULT_UPDATE_SERVER_URL = "http://114.207.112.73:8765"

log = logging.getLogger(__name__)


class MenuBarMixin:
    """menubar + admin emoji moderation chain mixin (cycle 169.520)."""

    def _build_menu_bar(self) -> None:
        """상단 메뉴바 구성 — "설정" + "계정" + "도움말" + "관리자" 4 진입점."""
        menubar = self.menuBar()

        # 한글 주석 — "설정" .ts entry tr() (5 locale)
        menu_settings = menubar.addMenu(_tr("설정"))

        act_room = QAction("방 입장…", self)
        act_room.setShortcut(QKeySequence("Ctrl+R"))
        act_room.triggered.connect(self._on_open_room_dialog)
        menu_settings.addAction(act_room)

        # cycle 139 — 1:1 직접 메시지 회귀 액션
        act_direct = QAction(f"직접 {_tr('메시지')}", self)
        act_direct.setShortcut(QKeySequence("Ctrl+D"))
        act_direct.triggered.connect(self._on_open_direct_chat)
        menu_settings.addAction(act_direct)

        # cycle 169.809 — SFU 그룹 음성·영상 통화 시작 (현재 방의 9 peer+ forward)
        act_group_call = QAction("그룹 통화 시작…", self)
        act_group_call.setShortcut(QKeySequence("Ctrl+Shift+G"))
        act_group_call.triggered.connect(self._on_start_group_call)
        menu_settings.addAction(act_group_call)

        # 한글 주석 — "환경" + "설정" .ts entry 결합
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

        # cycle 169.831 — auth 상태별 가시성 토글 대상 action 보관.
        # 로그인 시 회원가입/로그인/재설정 숨김 + 로그아웃/친구 노출, 로그아웃 시 반대.
        self._act_signup = QAction(f"{_tr('회원가입')}…", self)
        self._act_signup.triggered.connect(self._on_open_signup)
        menu_account.addAction(self._act_signup)

        self._act_login = QAction(f"{_tr('로그인')}…", self)
        self._act_login.setShortcut(QKeySequence("Ctrl+L"))
        self._act_login.triggered.connect(self._on_open_login)
        menu_account.addAction(self._act_login)

        self._act_reset = QAction(f"{_tr('비밀번호')} 재설정…", self)
        self._act_reset.triggered.connect(self._on_open_reset)
        menu_account.addAction(self._act_reset)

        menu_account.addSeparator()

        # cycle 144 — 친구 관리 진입점 2 actions
        self._act_friend_list = QAction("친구 목록", self)
        self._act_friend_list.triggered.connect(self._on_open_friend_list)
        menu_account.addAction(self._act_friend_list)

        self._act_friend_add = QAction("친구 추가…", self)
        self._act_friend_add.triggered.connect(self._on_open_add_friend)
        menu_account.addAction(self._act_friend_add)

        # cycle 169.499 — 받은 친구 요청 진입점
        self._act_pending = QAction("받은 친구 요청…", self)
        self._act_pending.triggered.connect(self._on_open_pending_requests)
        menu_account.addAction(self._act_pending)

        menu_account.addSeparator()

        self._act_logout = QAction("로그아웃", self)
        self._act_logout.triggered.connect(self._on_logout)
        menu_account.addAction(self._act_logout)

        # cycle 169.831 — 초기 = 로그아웃 상태 기준 가시성 적용 (login/logout 시 재토글)
        self.apply_auth_menu_visibility()

        # cycle 148 — "관리자" 메뉴 (admin / owner role 만 가시)
        self._menu_admin = None
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

    def apply_auth_menu_visibility(self) -> None:
        """cycle 169.831 — 로그인 상태별 계정 메뉴 action 가시성 토글.

        ``_session_token`` 보유(로그인) 시 회원가입/로그인/비밀번호 재설정을 숨기고
        로그아웃 + 친구 관리(목록/추가/받은 요청)를 노출한다. 로그아웃 시 반대.
        사용자 발견 버그(로그인 후 회원가입/로그인 메뉴 잔존) 회수.
        """
        logged_in = getattr(self, "_session_token", None) is not None
        # 한글 주석 — 로그아웃 전용 (로그인 시 숨김)
        for act in (
            getattr(self, "_act_signup", None),
            getattr(self, "_act_login", None),
            getattr(self, "_act_reset", None),
        ):
            if act is not None:
                act.setVisible(not logged_in)
        # 한글 주석 — 로그인 전용 (로그아웃 시 숨김)
        for act in (
            getattr(self, "_act_logout", None),
            getattr(self, "_act_friend_list", None),
            getattr(self, "_act_friend_add", None),
            getattr(self, "_act_pending", None),
        ):
            if act is not None:
                act.setVisible(logged_in)

    def _is_admin_role(self) -> bool:
        """현재 user 의 role 가 admin / owner 인지 검사 (cycle 148)."""
        return self._current_user_role in ("admin", "owner")

    def set_user_role(self, role: str) -> None:
        """로그인 응답 의 role 갱신 + 관리자 메뉴 가시성 재계산 (cycle 148)."""
        normalized = (role or "member").strip()
        if normalized not in ("admin", "owner", "member", "guest"):
            log.warning("[main_window] set_user_role 무효 — %r → member fallback", role)
            normalized = "member"
        self._current_user_role = normalized
        log.info("[main_window] user_role 갱신 — %s", normalized)
        self._rebuild_admin_menu()

    def _rebuild_admin_menu(self) -> None:
        """admin 메뉴 의 가시성 재구성 — set_user_role 직후 호출 (cycle 148)."""
        menubar = self.menuBar()
        if self._menu_admin is not None:
            menubar.removeAction(self._menu_admin.menuAction())
            self._menu_admin = None
            self._act_emoji_moderation = None

        if self._is_admin_role():
            self._menu_admin = menubar.addMenu("관리자")
            self._act_emoji_moderation = QAction("Emoji moderation…", self)
            self._act_emoji_moderation.triggered.connect(
                self._on_open_emoji_moderation
            )
            self._menu_admin.addAction(self._act_emoji_moderation)

    @pyqtSlot()
    def _on_open_emoji_moderation(self) -> None:
        """"Emoji moderation" 메뉴 슬롯 — admin dialog instantiation 진입점 (cycle 148)."""
        from app.ui.confirm_dialog import ConfirmDialog
        if not self._is_admin_role():
            ConfirmDialog.show_warning(self, "TooTalk", "Emoji moderation = admin 권한 의무")
            log.warning(
                "[main_window] emoji moderation 진입 차단 — role=%s",
                self._current_user_role,
            )
            return

        admin_token = os.environ.get("EMOJI_MODERATION_ADMIN_TOKEN", "").strip()
        if not admin_token:
            ConfirmDialog.show_warning(
                self, "TooTalk", "EMOJI_MODERATION_ADMIN_TOKEN env 미설정 — 진입 차단",
            )
            log.warning("[main_window] EMOJI_MODERATION_ADMIN_TOKEN 부재 — graceful skip")
            return

        base_url = (
            os.environ.get("UPDATE_SERVER_URL", "").strip()
            or _DEFAULT_UPDATE_SERVER_URL
        )

        from app.ui.admin import open_emoji_moderation

        dialog = open_emoji_moderation(
            parent=self, base_url=base_url, admin_token=admin_token,
        )
        if dialog is None:
            log.warning("[main_window] emoji moderation dialog 생성 실패 — graceful skip")
            return

        try:
            dialog.decision_made.connect(self._on_moderation_decision)
        except Exception as exc:  # noqa: BLE001
            log.debug(
                "[main_window] decision_made signal wire 실패 (stub 환경 가능) — %r", exc,
            )

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
            log.debug("[main_window] asyncio running loop 부재 — queue fetch skip")

        self._current_moderation_dialog = dialog
        try:
            dialog.exec()
        except Exception as exc:  # noqa: BLE001
            log.debug(
                "[main_window] moderation dialog exec 실패 (stub 환경 가능) — %r", exc,
            )

    async def _dispatch_moderation_queue_fetch(
        self, *, dialog: object, base_url: str, admin_token: str
    ) -> None:
        """fetch_pending_queue + dialog.repopulate 의 async chain (cycle 148)."""
        from app.ui.admin.emoji_moderation_dialog import fetch_pending_queue

        try:
            items = await fetch_pending_queue(base_url, admin_token)
            if hasattr(dialog, "repopulate"):
                dialog.repopulate(items)
            log.info(
                "[main_window] emoji moderation queue fetch PASS count=%d", len(items),
            )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "[main_window] emoji moderation queue fetch FAIL — graceful (%r)", exc,
            )
            # 한글 주석 — cycle 169.834 — 친절 안내 문구 i18n 바인딩 (dev jargon 제거)
            self._status_bar.showMessage(_tr("msg_moderation_queue_failed"), 4000)

    @pyqtSlot(int, str)
    def _on_moderation_decision(self, pack_id: int, decision: str) -> None:
        """EmojiModerationDialog 의 decision_made 시그널 handler (cycle 148)."""
        log.info(
            "[main_window] moderation decision pack_id=%d decision=%s", pack_id, decision,
        )
        self._status_bar.showMessage(
            f"moderation 결정 — pack_id={pack_id} decision={decision}", 3000,
        )
