# SPDX-License-Identifier: GPL-3.0-or-later
"""AddFriendDialog — username 검색 + 친구 요청 발신 (cycle 144).

Phase 1 친구 관리 UI skeleton — 사용자 검색 keyword 입력 + 결과 list +
"친구 추가" 버튼 의 친구 요청 흐름.

흐름
----
1. caller (MainWindow) 가 ``AddFriendDialog(search_callback=..., parent=...)``
   인스턴스화.
2. 사용자가 keyword 입력 + "검색" 버튼 → ``search_requested`` 시그널 emit
   (keyword payload). caller 가 REST ``GET /api/friends/search`` 호출
   + ``set_search_results(results)`` 갱신.
3. 사용자가 결과 행 선택 + "친구 추가" → ``friend_requested`` 시그널 emit
   (user_id, nickname payload). caller 가 REST ``POST /api/friends``.

PyQt6 graceful (ImportError + stub) — 정본 §E 정합.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, List, Optional

# PyQt6 graceful — headless 환경 의 ImportError 차단
try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )

    _PYQT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYQT_AVAILABLE = False

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SearchResult:
    """검색 결과 단일 행.

    Parameters
    ----------
    user_id : int
        users.id (PK).
    username : str
        users.username — 로그인 식별자 (영문).
    display_name : str
        users.display_name — 표시 이름 (한글 가능, cycle 169.491 신설).
    nickname : str
        users.nickname — 닉네임 (한글 가능, cycle 169.491 신설).
    email_verified : bool
        OTP 검증 완료 flag — UI 의 verified badge 표시.
    """

    user_id: int
    username: str
    display_name: str = ""
    nickname: str = ""
    email_verified: bool = False


# ─── Graceful 폴백 ──────────────────────────────────────────────────────────


if not _PYQT_AVAILABLE:  # pragma: no cover

    class AddFriendDialog:  # type: ignore[no-redef]
        """PyQt6 부재 시 의 stub."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("PyQt6 미설치 — AddFriendDialog 사용 불가")

else:

    class AddFriendDialog(QDialog):  # type: ignore[no-redef]
        """친구 추가 다이얼로그 — keyword 검색 + 결과 선택 + 요청 emit.

        Signals
        -------
        search_requested : pyqtSignal(str)
            검색 버튼 클릭 시 keyword payload emit. caller 의 REST 호출 + 결과 주입.
        friend_requested : pyqtSignal(int, str)
            친구 추가 버튼 클릭 시 (target_user_id, nickname) payload emit.
            nickname 비어있을 시 빈 문자열.
        """

        search_requested = pyqtSignal(str)
        friend_requested = pyqtSignal(int, str)

        def __init__(
            self,
            *,
            search_callback: Optional[Callable[[str], None]] = None,
            parent: Optional[QWidget] = None,
        ) -> None:
            """다이얼로그 위젯 트리 구성.

            Parameters
            ----------
            search_callback : Callable[[str], None] | None
                검색 버튼 클릭 시 inline 호출 callback (signal 의 alternative).
                None 시 signal 만 emit.
            """

            super().__init__(parent)
            self.setWindowTitle("TooTalk · 친구 추가")
            self.setMinimumWidth(420)
            self.setMinimumHeight(360)

            self._search_callback = search_callback
            self._results: List[SearchResult] = []

            root = QVBoxLayout(self)

            # ── 안내 라벨 ──────────────────────────────────
            heading = QLabel(
                "사용자명을 검색해 친구 요청을 발신합니다.", self
            )
            heading.setWordWrap(True)
            root.addWidget(heading)

            # ── keyword 입력 + 검색 버튼 ──────────────────
            search_row = QHBoxLayout()
            self._keyword_edit = QLineEdit(self)
            self._keyword_edit.setPlaceholderText("사용자명 (2자 이상)")
            self._keyword_edit.returnPressed.connect(self._on_search_clicked)
            self._search_btn = QPushButton("검색", self)
            self._search_btn.clicked.connect(self._on_search_clicked)
            search_row.addWidget(self._keyword_edit, stretch=1)
            search_row.addWidget(self._search_btn)
            root.addLayout(search_row)

            # ── 검색 결과 list ────────────────────────────
            # 한글 주석 — cycle 169.495 — chat list 패턴 visual 동기 (사용자 directive image #13).
            # ChatListItemDelegate 재사용 — avatar circle + name (14px bold) + subtitle (12px gray) + ts row.
            self._result_list = QListWidget(self)
            self._result_list.setSelectionMode(
                QListWidget.SelectionMode.SingleSelection
            )
            try:
                from app.ui.chat_list_panel import ChatListItemDelegate
                self._result_list.setItemDelegate(ChatListItemDelegate(self._result_list))
            except Exception as exc:  # noqa: BLE001 — graceful import fail
                log.debug("ChatListItemDelegate import fail graceful — %r", exc)
            root.addWidget(self._result_list, stretch=1)

            # ── nickname 입력 (선택) ──────────────────────
            nick_row = QHBoxLayout()
            nick_row.addWidget(QLabel("별명 (선택):", self))
            self._nickname_edit = QLineEdit(self)
            self._nickname_edit.setPlaceholderText("미입력 시 사용자명 사용")
            self._nickname_edit.setMaxLength(64)
            nick_row.addWidget(self._nickname_edit, stretch=1)
            root.addLayout(nick_row)

            # ── 버튼 줄 ───────────────────────────────────
            btn_row = QHBoxLayout()
            self._cancel_btn = QPushButton("닫기", self)
            self._cancel_btn.clicked.connect(self.reject)

            self._request_btn = QPushButton("친구 추가", self)
            self._request_btn.setDefault(True)
            self._request_btn.clicked.connect(self._on_request_clicked)

            btn_row.addStretch(1)
            btn_row.addWidget(self._cancel_btn)
            btn_row.addWidget(self._request_btn)
            root.addLayout(btn_row)

        # ----------------------------------------------------------------
        # public API
        # ----------------------------------------------------------------

        def set_search_results(self, results: List[SearchResult]) -> None:
            """검색 결과 list 갱신 — caller 의 REST 응답 처리 후 호출."""

            self._result_list.clear()
            self._results = list(results)

            if not self._results:
                placeholder = QListWidgetItem("검색 결과 없음")
                placeholder.setFlags(
                    placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable
                )
                self._result_list.addItem(placeholder)
                return

            # 한글 주석 — cycle 169.495 — ChatListEntry 변환 + UserRole + 2 set (delegate paint source).
            # name = nickname > display_name > username 우선. subtitle = @username (verify ✓ 보조).
            from app.ui.chat_list_panel import ChatListEntry
            for result in self._results:
                primary = result.nickname or result.display_name or result.username
                badge = " ✓" if result.email_verified else ""
                subtitle = f"@{result.username}{badge}"
                entry = ChatListEntry(
                    kind="friend",
                    target_id=result.user_id,
                    name=primary,
                    last_message=subtitle,
                    last_ts=None,
                    unread_count=0,
                    is_pinned=False,
                    is_online=False,
                )
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, result.user_id)
                item.setData(Qt.ItemDataRole.UserRole + 2, entry)
                self._result_list.addItem(item)

        def selected_user_id(self) -> Optional[int]:
            """현재 선택 결과 의 user_id (없으면 None)."""

            current = self._result_list.currentItem()
            if current is None:
                return None
            data = current.data(Qt.ItemDataRole.UserRole)
            if data is None:
                return None
            return int(data)

        def keyword(self) -> str:
            """현재 keyword 입력 값 — caller 의 외부 조회 helper."""

            return self._keyword_edit.text().strip()

        def nickname(self) -> str:
            """현재 별명 입력 값."""

            return self._nickname_edit.text().strip()

        # ----------------------------------------------------------------
        # 내부 헬퍼
        # ----------------------------------------------------------------

        def _on_search_clicked(self) -> None:
            """검색 버튼 슬롯 — keyword 검증 + 시그널 emit + callback."""

            keyword = self.keyword()
            if len(keyword) < 2:
                from app.ui.confirm_dialog import ConfirmDialog
                ConfirmDialog.show_warning(
                    self, "TooTalk", "검색 keyword 2자 이상 의무"
                )
                return
            log.info(
                "[add_friend] search_requested emit keyword=%r", keyword
            )
            self.search_requested.emit(keyword)
            if self._search_callback is not None:
                try:
                    self._search_callback(keyword)
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "search_callback 실패 keyword=%r: %s", keyword, exc
                    )

        def _on_request_clicked(self) -> None:
            """친구 추가 버튼 슬롯 — 선택 검증 + 시그널 emit.

            cycle 169.496 — alert 폐기 (사용자 directive image #18). selection 부재 시점
            silent return (단순 noop) — list 자체가 비어있으면 button click 의미 부재.
            """

            target_id = self.selected_user_id()
            if target_id is None:
                # 한글 주석 — 선택 부재 시점 silent return (alert 폐기). log 만 retain.
                log.info("[add_friend] click ignored — selection 부재")
                return
            nickname = self.nickname()
            log.info(
                "[add_friend] friend_requested emit user_id=%s nickname=%r",
                target_id,
                nickname,
            )
            self.friend_requested.emit(int(target_id), nickname)
