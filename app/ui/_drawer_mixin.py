# SPDX-License-Identifier: GPL-3.0-or-later
"""DrawerMixin — hamburger drawer + 9 drawer slot chain (cycle 169.514 신설).

codex 2.5 HIGH 진입 4차 — main_window.py 책임 분리.
TrayMixin (cycle 169.509) + FriendSearchMixin (cycle 169.511) + BotChatMixin (cycle 169.513) 등가 패턴.

분리 대상 method (cycle 169.113~500 origin):
- `_on_hamburger_clicked()` — HamburgerDrawer 생성 + 9 signal connect + geometry + exec
- `_on_drawer_profile()` — MyProfileDialog 진입
- `_on_profile_edit_requested()` — MyAccountDialog + PUT /api/auth/profile chain
- `_on_profile_update_finished(ok, code, msg, data)` — ProfileUpdateWorker callback
- `_on_drawer_settings()` — SettingsDialog
- `_on_drawer_contacts()` — ContactsDialog
- `_on_drawer_new_group()` + `_on_group_created(name, ids)` — NewGroupDialog wizard chain
- `_on_drawer_new_channel()` + `_on_channel_created(name, desc, ids)` — NewChannelDialog
- `_on_drawer_calls()` — CallsDialog
- `_on_drawer_saved()` — saved messages chat focus
- `_on_night_mode_toggled(on)` — 야간 모드 placeholder
- `_on_drawer_pending_requests()` — drawer close + PendingRequestsDialog dispatch
- `_on_drawer_logout()` — ConfirmDialog 로그아웃

본 mixin 안 의존 attribute (MainWindow init 안 retain 의무):
- `_active_drawer` (Optional[HamburgerDrawer])
- `_active_profile_dialog` (Optional)
- `_profile_worker` (gc 회피)
- `_current_nickname` / `_current_display_name` / `_current_username` / `_current_email`
  / `_current_user_phone` / `_current_user_birthdate` / `_current_user_bio` / `_auth_token`
- `_sidebar_rail`, `_chat_list_panel`, `_input_bar`, `_auth_client`, `_config`
- `_exec_dialog_centered(dialog) -> int` (main_window 안 retain helper)
- `_on_chat_selected(kind, target_id)` (main_window 안 retain handler)
- `_on_open_pending_requests()` (FriendSearchMixin 안 retain)
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSlot

log = logging.getLogger(__name__)


class DrawerMixin:
    """HamburgerDrawer + 9 slot chain mixin (cycle 169.514)."""

    def _on_hamburger_clicked(self) -> None:
        """좌상단 햄버거 click → HamburgerDrawer slide-in (cycle 169.113 origin)."""
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
        # cycle 169.320 — drawer 5 signal 전 connect
        drawer.new_group_clicked.connect(self._on_drawer_new_group)  # type: ignore[arg-type]
        drawer.new_channel_clicked.connect(self._on_drawer_new_channel)  # type: ignore[arg-type]
        drawer.contacts_clicked.connect(self._on_drawer_contacts)  # type: ignore[arg-type]
        drawer.calls_clicked.connect(self._on_drawer_calls)  # type: ignore[arg-type]
        drawer.saved_clicked.connect(self._on_drawer_saved)  # type: ignore[arg-type]
        drawer.logout_clicked.connect(self._on_drawer_logout)  # type: ignore[arg-type]
        # cycle 169.500 — 받은 친구 요청 entry
        drawer.pending_requests_clicked.connect(self._on_drawer_pending_requests)  # type: ignore[arg-type]
        # cycle 169.411 — night mode toggle signal binding
        drawer.night_mode_toggled.connect(self._on_night_mode_toggled)  # type: ignore[arg-type]
        # cycle 169.116 — sidebar_rail reserve
        sidebar_w = self._sidebar_rail.width() if hasattr(self, "_sidebar_rail") else 96
        # cycle 169.501 — drawer height = main_window full client area
        drawer.setGeometry(sidebar_w, 0, 256, self.height())
        # cycle 169.838 — HamburgerDrawer 는 QFrame child overlay(parent=self, main_window
        # 내부 slide-in)이며 .exec() 는 show+raise 호환 shim 일 뿐 별도 OS 윈도우/모달 loop 가
        # 아니다. 따라서 in-app overlay 모달 directive 에 이미 정합(원형 _exec_dialog_centered
        # 중앙배치 대신 좌측 slide-in geometry 를 유지).
        drawer.exec()
        # 한글 주석 — close 시점 ref clear
        def _on_drawer_closed():
            self._active_drawer = None
        drawer.closed.connect(_on_drawer_closed)  # type: ignore[arg-type]
        self._active_drawer = drawer

    @pyqtSlot()
    def _on_drawer_profile(self) -> None:
        """내 프로필 dialog open (cycle 169.401 — nickname + display_name + username 3 entry)."""
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
        # cycle 169.403 — active profile dialog reference retain
        self._active_profile_dialog = dialog
        dialog.edit_requested.connect(self._on_profile_edit_requested)  # type: ignore[arg-type]
        self._exec_dialog_centered(dialog)

    @pyqtSlot()
    def _on_profile_edit_requested(self) -> None:
        """MyAccountDialog 진입 + save 시 PUT /api/auth/profile."""
        from app.ui.my_account_dialog import MyAccountDialog
        from app.net.account_client import ProfileUpdateWorker
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
            new_disp = (payload.get("display_name") or "").strip()
            if new_disp:
                self._current_display_name = new_disp
            new_nick = (payload.get("nickname") or "").strip()
            if new_nick:
                self._current_nickname = new_nick
                self._current_user_nickname = new_nick  # alias retain
            new_bio = (payload.get("bio") or "").strip()
            # cycle 169.403 — active MyProfileDialog + HamburgerDrawer 즉시 refresh
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
        # cycle 169.838 — 별도 OS 윈도우 .exec() → 메인 레이아웃 안 in-app overlay 모달.
        self._exec_dialog_centered(dialog)

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
        """설정 dialog open."""
        try:
            from app.ui.settings_dialog import SettingsDialog
            dialog = SettingsDialog(parent=self)
            self._exec_dialog_centered(dialog)
        except Exception as exc:
            log.warning("SettingsDialog 진입 실패 — %r", exc)

    @pyqtSlot()
    def _on_drawer_contacts(self) -> None:
        """연락처 dialog — ContactsDialog open (cycle 169.320)."""
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
        """그룹 생성 callback — ChatListEntry kind=group + chat 진입 (cycle 169.333)."""
        from app.ui.chat_list_panel import ChatListEntry
        from datetime import datetime
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
        self._on_chat_selected("group", gid)

    @pyqtSlot()
    def _on_drawer_new_channel(self) -> None:
        """채널 만들기 wizard (cycle 169.348)."""
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
        """채널 생성 callback — ChatListEntry kind=channel insert + chat focus."""
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
        """저장한 메시지 → drawer close + chat_view focus (cycle 169.325 image #88)."""
        try:
            if hasattr(self, "_chat_list_panel"):
                self._chat_list_panel.set_active_tab("friends")
                self._chat_list_panel.set_current_chat("saved", 0)
            # cycle 169.411 — saved kind target_id retain (0 — server self-resolve viewer_id)
            self._on_chat_selected("saved", 0)
            drawer = getattr(self, "_active_drawer", None)
            if drawer is not None and hasattr(drawer, "close_drawer"):
                drawer.close_drawer()
            elif drawer is not None:
                drawer.close()
            if hasattr(self, "_input_bar"):
                self._input_bar.setFocus()
        except Exception as exc:
            log.warning("저장한 메시지 진입 실패 — %r", exc)

    @pyqtSlot(bool)
    def _on_night_mode_toggled(self, on: bool) -> None:
        """drawer 야간 모드 toggle handler (cycle 169.411 Phase 1 잔존 회수).

        Phase 1 scope = log + drawer visual 자체 retain. theme stylesheet swap = Phase 2+.
        """
        log.info("[main_window] night_mode_toggled — on=%s", on)
        # 한글 주석 — light theme swap chain 진입 위치 (Phase 2+)

    @pyqtSlot()
    def _on_drawer_pending_requests(self) -> None:
        """drawer "받은 친구 요청" click → drawer close + PendingRequestsDialog open."""
        log.info("[drawer] pending_requests")
        try:
            if self._active_drawer is not None:
                self._active_drawer.close_drawer()
        except Exception:
            pass
        self._active_drawer = None
        self._on_open_pending_requests()

    @pyqtSlot()
    def _on_drawer_logout(self) -> None:
        """로그아웃 confirm — cycle 169.365 modal ConfirmDialog (i18n + frameless + main center)."""
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
