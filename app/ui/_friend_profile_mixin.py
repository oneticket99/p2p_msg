# SPDX-License-Identifier: GPL-3.0-or-later
"""FriendProfileMixin — friend 프로필/lookup 6 method chain (cycle 169.527 신설).

codex 2.5 MED 진입 12차 — main_window.py 책임 분리 batch.

분리 대상 method (cycle 144/153.7/154.2 origin):
- `_on_friend_profile_open(friend_id)` — ProfileView modal + 4 button binding
- `_profile_message_clicked(modal, friend_id)` — modal close + chat 진입
- `_profile_call_clicked(friend_id)` — Phase 5 WebRTC SDP entry placeholder
- `_profile_mute_clicked(friend_id)` — _muted_friends set toggle
- `_profile_block_clicked(modal, friend_id)` — friends_client.block REST chain
- `_lookup_friend_name(friend_id)` — friend_list cache nickname lookup

본 mixin 안 의존:
- `self._friend_list`, `self._muted_friends`, `self._friends_client`
- `self._on_chat_selected()` (ChatNavigationMixin)
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import QCoreApplication, pyqtSlot

log = logging.getLogger(__name__)

# 한글 주석 — main_window 와 동일 i18n helper.
_tr = lambda src: QCoreApplication.translate("MainWindow", src)


class FriendProfileMixin:
    """friend ProfileView + 4 button + lookup chain mixin (cycle 169.527)."""

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
