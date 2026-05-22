# SPDX-License-Identifier: GPL-3.0-or-later
"""PendingRequestsDialog — 받은 친구 요청 list + 수락/거절 (cycle 169.499 신설).

사용자 directive 2026-05-22 — 친구 추가와 친구 요청 수락 로직 본격 binding.

흐름
----
1. `_on_open_pending_requests` (main_window) → 본 dialog instantiate.
2. dialog `show()` 직후 `FriendsClient.list_pending()` async fetch.
3. 결과 list 안 각 row = `nickname (@username)` + [수락] + [거절] 2 button.
4. button click → `accept_friend(user_id)` / `reject_friend(user_id)` async + row 제거.
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._close_button import make_close_button

log = logging.getLogger(__name__)


class PendingRequestsDialog(QDialog):
    """받은 친구 요청 list + 수락/거절 modal.

    Signals
    -------
    request_resolved(int, bool)
        user_id + accepted flag emit (caller refresh chain).
    """

    request_resolved = pyqtSignal(int, bool)

    def __init__(
        self,
        friends_client: Optional[object] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._fc = friends_client
        self.setWindowTitle("TooTalk · 받은 친구 요청")
        self.setModal(True)
        self.setMinimumSize(420, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        # header
        header = QHBoxLayout()
        title = QLabel("받은 친구 요청")
        title.setStyleSheet("color: #e5e7eb; font-size: 18px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch(1)
        close_btn = make_close_button(self.reject, self)
        header.addWidget(close_btn)
        root.addLayout(header)

        hint = QLabel("아래 요청을 수락 또는 거절 하세요.")
        hint.setStyleSheet("color: #9ca3af; font-size: 12px;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        # list — 각 row = QListWidgetItem + setItemWidget(row widget)
        # 한글 주석 — cycle 169.501 — placeholder = QLabel overlay (center 정렬, 사용자 directive image #28)
        list_container = QFrame()
        list_container.setStyleSheet(
            "QFrame { background-color: #131C30; border: 1px solid #1f2937;"
            " border-radius: 8px; }"
        )
        container_layout = QVBoxLayout(list_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        self._list = QListWidget(list_container)
        self._list.setStyleSheet(
            "QListWidget { background-color: transparent; border: 0; color: #e5e7eb; }"
        )
        container_layout.addWidget(self._list)
        # 한글 주석 — center placeholder overlay (parent = list_container)
        self._empty_label = QLabel("로딩 중...", list_container)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "QLabel { color: #9ca3af; font-size: 14px; background-color: transparent; }"
        )
        self._empty_label.hide()
        self._list_container = list_container
        root.addWidget(list_container, stretch=1)

        # placeholder row (legacy retain — populate() 안 별 사용 차단)
        self._placeholder_item: Optional[QListWidgetItem] = None
        self._show_placeholder("로딩 중...")

    def populate(self, payloads: List[object]) -> None:
        """list 갱신 — caller 의 list_pending 결과 주입."""
        self._list.clear()
        if not payloads:
            self._show_placeholder("받은 요청이 없습니다.")
            return
        # 한글 주석 — cycle 169.501 — empty overlay hide + list show
        self._empty_label.hide()
        self._list.show()
        for p in payloads:
            row = self._build_row_widget(p)
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, row)

    def _show_placeholder(self, text: str) -> None:
        """검색 결과 부재 — QLabel center overlay (사용자 directive image #28)."""
        self._list.clear()
        self._list.hide()
        self._empty_label.setText(text)
        # 한글 주석 — list_container 의 rect 안 center 정렬
        self._empty_label.setGeometry(0, 0, self._list_container.width(), self._list_container.height())
        self._empty_label.show()
        self._empty_label.raise_()

    def _build_row_widget(self, payload: object) -> QWidget:
        """단일 pending 행 widget — chat list 패턴 (avatar + nickname + 요청 시각) + 수락/거절 button.

        cycle 169.500 — 사용자 directive image #25 — chat list 동일 visual.
        avatar = palette_solid hash bg + nickname initials (cycle 169.249 정합).
        """
        from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPixmap
        from app.ui.avatar_palette import palette_solid
        from app.ui._avatar_helper import get_initials
        from datetime import datetime

        # 한글 주석 — FriendProfilePayload getattr fallback (테스트 mock 호환)
        user_id = int(getattr(payload, "friend_user_id", 0) or getattr(payload, "user_id", 0))
        username = str(getattr(payload, "friend_username", "")
                       or getattr(payload, "username", "")
                       or f"user#{user_id}")
        nickname = str(getattr(payload, "nickname", "") or "")
        display = nickname or username
        # 한글 주석 — 요청 시각 = requested_at_iso fallback (사용자 directive)
        req_iso = str(getattr(payload, "requested_at_iso", "") or "")
        ts_text = ""
        if req_iso:
            try:
                dt = datetime.fromisoformat(req_iso.replace("Z", "+00:00"))
                h = dt.hour
                m = dt.minute
                ap = "오전" if h < 12 else "오후"
                h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
                ts_text = f"{ap} {h12}:{m:02d}"
            except Exception:
                ts_text = req_iso[:16]

        wrap = QFrame()
        wrap.setFixedHeight(72)
        wrap.setStyleSheet("QFrame { background-color: transparent; }")
        row = QHBoxLayout(wrap)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(12)

        # 한글 주석 — avatar circle (chat_list_panel ChatListItemDelegate 등가 visual)
        avatar_size = 54
        bg_color = palette_solid(display or username)
        initials = get_initials(display or username)
        pix = QPixmap(avatar_size, avatar_size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, avatar_size, avatar_size)
        painter.setPen(QPen(QColor("#ffffff")))
        f = QFont()
        f.setPixelSize(20 if len(initials) >= 2 else 24)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, initials)
        painter.end()
        avatar_lbl = QLabel()
        avatar_lbl.setPixmap(pix)
        avatar_lbl.setFixedSize(avatar_size, avatar_size)
        row.addWidget(avatar_lbl)

        # name + ts column
        name_col = QVBoxLayout()
        name_col.setContentsMargins(0, 0, 0, 0)
        name_col.setSpacing(2)
        name_lbl = QLabel(display)
        name_lbl.setStyleSheet("color: #e5e7eb; font-size: 14px; font-weight: 700;")
        name_col.addWidget(name_lbl)
        if ts_text:
            ts_lbl = QLabel(ts_text)
            ts_lbl.setStyleSheet("color: #A1AAB3; font-size: 12px;")
            name_col.addWidget(ts_lbl)
        else:
            sub_lbl = QLabel(f"@{username}")
            sub_lbl.setStyleSheet("color: #A1AAB3; font-size: 12px;")
            name_col.addWidget(sub_lbl)
        row.addLayout(name_col, stretch=1)

        accept_btn = QPushButton("수락")
        accept_btn.setFixedSize(64, 32)
        accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        accept_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #0066FF;"
            " border: 0; border-radius: 6px; font-weight: 600; }"
            "QPushButton:hover { background-color: #0052cc; }"
        )
        accept_btn.clicked.connect(lambda _=False, uid=user_id, item_wrap=wrap: self._on_accept(uid, item_wrap))  # type: ignore[arg-type]
        row.addWidget(accept_btn)

        reject_btn = QPushButton("거절")
        reject_btn.setFixedSize(64, 32)
        reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reject_btn.setStyleSheet(
            "QPushButton { color: #e5e7eb; background-color: #1F2937;"
            " border: 1px solid #374151; border-radius: 6px; font-weight: 500; }"
            "QPushButton:hover { background-color: #2c3a52; }"
        )
        reject_btn.clicked.connect(lambda _=False, uid=user_id, item_wrap=wrap: self._on_reject(uid, item_wrap))  # type: ignore[arg-type]
        row.addWidget(reject_btn)

        return wrap

    def _on_accept(self, user_id: int, row_widget: QWidget) -> None:
        """수락 button → friends_client.accept_friend async."""
        log.info("[pending] accept user_id=%d", user_id)
        if self._fc is None:
            QMessageBox.warning(self, "TooTalk", "friends_client 부재")
            return
        async def _do():
            try:
                await self._fc.accept_friend(user_id)  # type: ignore[attr-defined]
                log.info("[pending] accept PASS user_id=%d", user_id)
                self.request_resolved.emit(int(user_id), True)
                self._remove_row(row_widget)
            except Exception as exc:  # noqa: BLE001
                log.warning("[pending] accept fail — %r", exc)
                QMessageBox.warning(self, "TooTalk", f"수락 실패: {exc.__class__.__name__}")
        try:
            asyncio.ensure_future(_do())
        except Exception as exc:  # noqa: BLE001
            log.warning("[pending] accept spawn fail — %r", exc)

    def _on_reject(self, user_id: int, row_widget: QWidget) -> None:
        """거절 button → friends_client.reject_friend async."""
        log.info("[pending] reject user_id=%d", user_id)
        if self._fc is None:
            QMessageBox.warning(self, "TooTalk", "friends_client 부재")
            return
        async def _do():
            try:
                await self._fc.reject_friend(user_id)  # type: ignore[attr-defined]
                log.info("[pending] reject PASS user_id=%d", user_id)
                self.request_resolved.emit(int(user_id), False)
                self._remove_row(row_widget)
            except Exception as exc:  # noqa: BLE001
                log.warning("[pending] reject fail — %r", exc)
                QMessageBox.warning(self, "TooTalk", f"거절 실패: {exc.__class__.__name__}")
        try:
            asyncio.ensure_future(_do())
        except Exception as exc:  # noqa: BLE001
            log.warning("[pending] reject spawn fail — %r", exc)

    def resizeEvent(self, event) -> None:  # noqa: N802 — Qt 규약
        """dialog resize 시점 empty_label geometry 동기."""
        super().resizeEvent(event)
        try:
            if hasattr(self, "_empty_label") and self._empty_label.isVisible():
                self._empty_label.setGeometry(
                    0, 0, self._list_container.width(), self._list_container.height()
                )
        except Exception:
            pass

    def _remove_row(self, row_widget: QWidget) -> None:
        """row 1건 제거 — 모두 처리 시점 placeholder 표시."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            w = self._list.itemWidget(item)
            if w is row_widget:
                self._list.takeItem(i)
                break
        if self._list.count() == 0:
            self._show_placeholder("받은 요청이 없습니다.")
