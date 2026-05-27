# SPDX-License-Identifier: GPL-3.0-or-later
"""ContactsDialog — 연락처 modal (cycle 169.317).

계층 위치 — app/ui dialog(정본 §E). QDialog 위젯 — DrawerMixin 이 instantiate(친구 목록 표시 +
친구 추가 진입). 친구 data 는 caller 주입 + 추가 요청은 signal 회신(서버 호출 caller 책임).

사용자 directive image #84 — drawer 의 "연락처" click → 본 dialog (친구 목록 + 추가).
"""

from __future__ import annotations
from app.core.config import DEMO_FALLBACK_API_BASE

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._close_button import make_close_button
from app.i18n.labels import tr as _tr

import logging
log = logging.getLogger(__name__)


class ContactsDialog(QDialog):
    """연락처 dialog — 친구 list + 신규 친구 추가."""

    contact_added = pyqtSignal(str)  # (user_id_or_email)

    def __init__(self, contacts: Optional[list[dict]] = None, parent: Optional[QWidget] = None) -> None:
        # telegram align outer wrap + 420x600 strict
        super().__init__(parent)
        self.setWindowTitle(_tr("tootalk_연락처"))
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self.setStyleSheet("QDialog { background-color: transparent; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        wrap = QFrame()
        wrap.setObjectName("contactsWrap")
        wrap.setStyleSheet(
            "QFrame#contactsWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)

        body = QVBoxLayout(wrap)
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(12)

        # header
        header_row = QHBoxLayout()
        title = QLabel("연락처")
        title.setStyleSheet("color: #f3f4f6; font-size: 18px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)
        # cycle 169.324 — 공통 close button factory (telegram align)
        close_btn = make_close_button(self.reject, self)
        header_row.addWidget(close_btn)
        body.addLayout(header_row)

        # cycle 169.450 — telegram align 신규 연락처 추가 button (사용자 directive)
        # 이전 이메일/유저ID 단일 input 폐기 → NewContactDialog (성+이름+전화번호 마스크) chain
        # cycle 169.450~457 — telegram 2 mode 친구 추가 button row (연락처 + 사용자명)
        add_row = QHBoxLayout()
        new_contact_btn = QPushButton("+ 새 연락처")
        new_contact_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_contact_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #0066FF;"
            " border: 0; border-radius: 8px; padding: 10px 16px;"
            " font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background-color: #0052cc; }"
        )
        new_contact_btn.clicked.connect(self._on_open_new_contact)  # type: ignore[arg-type]
        add_row.addWidget(new_contact_btn, stretch=1)
        by_username_btn = QPushButton("@ 사용자명")
        by_username_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        by_username_btn.setStyleSheet(
            "QPushButton { color: #67E8F9; background-color: #1F2937;"
            " border: 1px solid #67E8F9; border-radius: 8px; padding: 10px 16px;"
            " font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background-color: #2c3a52; }"
        )
        by_username_btn.clicked.connect(self._on_open_by_username)  # type: ignore[arg-type]
        add_row.addWidget(by_username_btn, stretch=1)
        body.addLayout(add_row)
        # placeholder retain 이메일/유저 ID 검색 (별 chain 의무 retain)
        self._add_edit = QLineEdit()
        self._add_edit.setVisible(False)  # cycle 169.450 = telegram align dialog chain 의무로 hidden

        # 친구 list
        self._list = QListWidget()
        self._list.setStyleSheet(
            "QListWidget { color: #f3f4f6; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 8px; }"
            "QListWidget::item { padding: 10px; }"
            "QListWidget::item:hover { background-color: #2c3a52; }"
        )
        body.addWidget(self._list, stretch=1)

        self._populate(contacts or [])

    def _populate(self, contacts: list[dict]) -> None:
        # 외부 친구 list 주입
        for c in contacts:
            name = c.get("name") or c.get("username") or c.get("email", "?")
            item = QListWidgetItem(name)
            self._list.addItem(item)
        if not contacts:
            empty = QListWidgetItem("등록된 연락처 부재")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(empty)

    def _on_add(self) -> None:
        # 친구 추가 signal emit
        identifier = self._add_edit.text().strip()
        if identifier:
            self.contact_added.emit(identifier)
            self._add_edit.clear()

    def _on_open_new_contact(self) -> None:
        """cycle 169.450 — telegram align 신규 연락처 dialog spawn (사용자 directive)."""
        try:
            from app.ui.new_contact_dialog import NewContactDialog
            dialog = NewContactDialog(parent=self)
            dialog.contact_submitted.connect(self._on_new_contact_submitted)
            from app.ui._modal_helper import exec_modal
            exec_modal(dialog, self)  # cycle 169.838 — in-app overlay 모달 (별도 윈도우 금지)
        except Exception as exc:
            log.warning("[new_contact_dialog] spawn 실패 — %r", exc)

    def _on_open_by_username(self) -> None:
        """cycle 169.457 — telegram align 사용자명 검색 dialog spawn."""
        try:
            from app.ui.add_friend_by_username_dialog import AddFriendByUsernameDialog
            dialog = AddFriendByUsernameDialog(parent=self)
            dialog.friend_added.connect(self._on_friend_username_submitted)
            from app.ui._modal_helper import exec_modal
            exec_modal(dialog, self)  # cycle 169.838 — in-app overlay 모달 (별도 윈도우 금지)
        except Exception as exc:
            log.warning("[add_friend_by_username] spawn 실패 — %r", exc)

    def _on_friend_username_submitted(self, username: str) -> None:
        """cycle 169.457 — POST /api/friends/by-username async chain."""
        if not username:
            return
        try:
            mw = self.parent()
            while mw is not None and not hasattr(mw, "_session_token"):
                mw = mw.parent()
            if mw is None or not getattr(mw, "_session_token", None):
                log.warning("[friend_by_username] main_window/token 부재 — POST skip")
                return
            import asyncio
            asyncio.ensure_future(self._async_post_friend_username(mw, username))
        except Exception as exc:
            log.warning("[friend_by_username] post chain 실패 — %r", exc)
        self.contact_added.emit(username)

    async def _async_post_friend_username(self, main_window, username: str) -> None:
        """POST /api/friends/by-username chain."""
        import aiohttp
        try:
            api_base = getattr(main_window._config, "api_base", None) or DEMO_FALLBACK_API_BASE
            token = getattr(main_window, "_session_token", "") or ""
            if not token:
                return
            headers = {"Authorization": f"Bearer {token}"}
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.post(
                    f"{api_base}/api/friends/by-username",
                    json={"username": username},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 201:
                        data = await resp.json()
                        log.info(
                            "[friend_by_username] PASS username=%s friend_id=%s room=%s",
                            username, data.get("friend_user_id"), data.get("room_id"),
                        )
                    elif resp.status == 404:
                        from app.ui.confirm_dialog import ConfirmDialog
                        ConfirmDialog.show_warning(
                            self, "친구 추가", f"@{username} 사용자 부재",
                        )
                    else:
                        log.warning("[friend_by_username] HTTP %d", resp.status)
        except Exception as exc:
            log.debug("[friend_by_username] async POST 실패 — %r", exc)

    def _on_new_contact_submitted(self, payload: dict) -> None:
        """cycle 169.455 — POST /api/contacts chain + contact_added signal 재 emit.

        server upsert + 양방향 매칭 attempt fire — telegram align friend chain.
        """
        phone = payload.get("phone", "")
        last_name = payload.get("last_name", "")
        first_name = payload.get("first_name", "")
        if not phone:
            return
        try:
            mw = self.parent()
            while mw is not None and not hasattr(mw, "_session_token"):
                mw = mw.parent()
            if mw is not None and getattr(mw, "_session_token", None):
                import asyncio
                asyncio.ensure_future(self._async_post_contact(
                    mw, phone, last_name, first_name,
                ))
            else:
                log.warning("[contacts] main_window 부재 — POST skip")
        except Exception as exc:
            log.warning("[contacts] post chain 실패 — %r", exc)
        # legacy chain — local contact_added signal retain
        self.contact_added.emit(phone)

    async def _async_post_contact(self, main_window, phone: str, last_name: str, first_name: str) -> None:
        """cycle 169.455 — POST /api/contacts async chain."""
        import aiohttp
        try:
            api_base = getattr(main_window._config, "api_base", None) or DEMO_FALLBACK_API_BASE
            token = getattr(main_window, "_session_token", "") or ""
            if not token:
                return
            headers = {"Authorization": f"Bearer {token}"}
            connector = aiohttp.TCPConnector(ssl=False)
            payload = {
                "phone": phone,
                "last_name": last_name or None,
                "first_name": first_name or None,
            }
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                async with session.post(
                    f"{api_base}/api/contacts",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 201:
                        data = await resp.json()
                        matched = data.get("matched_user_id")
                        log.info("[contacts] POST PASS phone=%s matched=%s", phone, matched)
                    else:
                        log.warning("[contacts] POST HTTP %d", resp.status)
        except Exception as exc:
            log.debug("[contacts] async POST 실패 — %r", exc)
