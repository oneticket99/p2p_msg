# SPDX-License-Identifier: GPL-3.0-or-later
"""GroupChatView — N peer 그룹 채팅 컨테이너 위젯.

기존 ``app.ui.chat_view.ChatView`` 의 1:1 패턴 참조 + 그룹 의 sender label
의무 (peer 식별을 위해 모든 메시지 에 발신자 표시). 본 cycle 136 의 group
chat UI skeleton 4 widget 중 2번째.

레이아웃 구조:

```
+---------------------------------------------------+
| 헤더: 방 제목 + member_count + 멤버 보기 버튼     |
+---------------------------------------------------+
|                                                   |
|  메시지 스크롤 영역 (MessageBubble 누적)          |
|  — 모든 peer 메시지 의 sender label 의무          |
|                                                   |
+---------------------------------------------------+
| [메시지 입력 QLineEdit                ] [보내기]   |
+---------------------------------------------------+
```

Signals:

- ``message_send_requested(str)`` — 사용자 의 입력 + 보내기/Enter trigger.
  caller (MainWindow) 가 본 시그널 을 받아 WebRTC DataChannel 송신.
- ``members_panel_requested()`` — 헤더 의 "멤버 보기" 버튼 클릭.

PyQt6 graceful (ImportError + stub) — 정본 §E 정합.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

# PyQt6 graceful — headless 환경 의 ImportError 차단
try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )

    from app.ui.message_bubble import MessageBubble

    _PYQT_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PYQT_AVAILABLE = False

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Graceful 폴백
# ----------------------------------------------------------------------

if not _PYQT_AVAILABLE:  # pragma: no cover

    class GroupChatView:  # type: ignore[no-redef]
        """PyQt6 부재 시 의 stub."""

        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("PyQt6 미설치 — GroupChatView 사용 불가")

else:

    class GroupChatView(QWidget):  # type: ignore[no-redef]
        """그룹 채팅 메인 View — header + 메시지 영역 + 입력 영역.

        Signals
        -------
        message_send_requested : pyqtSignal(str)
            사용자 의 입력창 텍스트 + 보내기 / Enter trigger.
        members_panel_requested : pyqtSignal()
            헤더 의 "멤버 보기" 버튼 클릭 시.
        """

        message_send_requested = pyqtSignal(str)
        members_panel_requested = pyqtSignal()

        def __init__(
            self,
            *,
            room_id: int,
            room_title: str = "",
            member_count: int = 0,
            self_username: str = "self",
            parent: Optional[QWidget] = None,
        ) -> None:
            """위젯 트리 + 입력 영역 + 헤더 구성.

            Parameters
            ----------
            room_id : int
                rooms.id — 본 view 가 표시할 방 의 식별자.
            room_title : str
                헤더 표시명 (방장 지정 친근한 이름). 부재 시 "Room #<id>".
            member_count : int
                현재 멤버 수 (헤더 표기). set_member_count() 갱신 가능.
            self_username : str
                자기 발신 메시지 의 sender 라벨 (그룹 모드 에서도 sender label
                의무 — 1:1 의 ``ChatView`` 가 self 는 sender 미표시 와 차이).
            """

            super().__init__(parent)
            self._room_id = room_id
            self._self_username = self_username

            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            # ── 1) 헤더 ────────────────────────────────────
            header = QWidget(self)
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(8, 6, 8, 6)

            title_text = room_title or f"Room #{room_id}"
            self._title_label = QLabel(title_text, header)
            self._title_label.setStyleSheet("font-weight: 700; font-size: 14px;")

            self._member_count_label = QLabel(f"멤버 {member_count}", header)
            self._member_count_label.setStyleSheet("color: #6b7280; font-size: 12px;")

            # cycle 169.836 — "멤버 보기" 별도 버튼 제거. 멤버 보기는 헤더 "..." 드롭다운
            # entry 로 이동(텔레그램 그룹 멤버보기 플로우 directive). members_panel_requested
            # 신호는 호환 위해 정의 유지(현재 미발화 — "..." 메뉴가 핸들러 직접 호출).
            header_layout.addWidget(self._title_label, stretch=1)
            header_layout.addWidget(self._member_count_label)

            root.addWidget(header)

            # ── 2) 메시지 스크롤 영역 ──────────────────────
            self._scroll = QScrollArea(self)
            self._scroll.setWidgetResizable(True)
            self._scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self._scroll.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )

            self._content = QWidget(self._scroll)
            self._messages_layout = QVBoxLayout(self._content)
            self._messages_layout.setContentsMargins(8, 8, 8, 8)
            self._messages_layout.setSpacing(6)
            self._messages_layout.addStretch(1)

            self._scroll.setWidget(self._content)
            self._scroll.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            root.addWidget(self._scroll, stretch=1)

            # ── 3) 입력 영역 ───────────────────────────────
            input_row = QHBoxLayout()
            input_row.setContentsMargins(8, 6, 8, 8)
            input_row.setSpacing(6)

            self._input_edit = QLineEdit(self)
            self._input_edit.setPlaceholderText("메시지를 입력하세요…")
            self._input_edit.returnPressed.connect(self._on_send_clicked)

            self._send_btn = QPushButton("보내기", self)
            self._send_btn.clicked.connect(self._on_send_clicked)

            input_row.addWidget(self._input_edit, stretch=1)
            input_row.addWidget(self._send_btn)

            input_container = QWidget(self)
            input_container.setLayout(input_row)
            root.addWidget(input_container)

        # --------------------------------------------------------------
        # public API
        # --------------------------------------------------------------

        @property
        def room_id(self) -> int:
            """본 view 의 room_id getter."""

            return self._room_id

        def append_message(
            self,
            *,
            sender: str,
            text: str,
            ts: Optional[datetime] = None,
            is_self: bool = False,
        ) -> None:
            """신규 메시지 1건 의 버블 누적 + 자동 스크롤.

            그룹 모드 에서는 self 발신 일지라도 sender 라벨 의무. 단, 본
            skeleton 은 ``MessageBubble`` 의 is_self 분기 (좌/우 정렬) 그대로
            활용 — sender 표기는 caller 가 explicit 으로 username 주입.
            """

            actual_ts = ts or datetime.now()
            bubble = MessageBubble(
                sender=sender,
                text=text,
                ts=actual_ts,
                is_self=is_self,
                parent=self._content,
            )

            # stretch 슬롯 직전 (count - 1) 에 삽입
            insert_at = max(0, self._messages_layout.count() - 1)
            self._messages_layout.insertWidget(insert_at, bubble)

            # 다음 이벤트 사이클 에서 스크롤바 끝까지 이동
            scrollbar = self._scroll.verticalScrollBar()
            scrollbar.rangeChanged.connect(self._scroll_to_bottom_once)

        def set_member_count(self, count: int) -> None:
            """헤더 의 멤버 수 표기 갱신."""

            self._member_count_label.setText(f"멤버 {count}")

        def clear_messages(self) -> None:
            """모든 메시지 버블 제거 — 방 전환 등 호출 (stretch 유지)."""

            while self._messages_layout.count() > 1:
                item = self._messages_layout.takeAt(0)
                widget = item.widget() if item is not None else None
                if widget is not None:
                    widget.deleteLater()

        # --------------------------------------------------------------
        # 내부 헬퍼
        # --------------------------------------------------------------

        def _on_send_clicked(self) -> None:
            """보내기 / Enter 슬롯 — 입력 정규화 + 시그널 emit + 입력창 clear.

            본 widget 자체 는 echo 처리 하지 않음 (1:1 ``MainWindow`` 와 차이).
            caller 가 message_send_requested 시그널 을 받아 WebRTC DataChannel
            송신 + 결과 ack 후 append_message() 를 호출하는 흐름.
            """

            text = self._input_edit.text().strip()
            if not text:
                return
            self._input_edit.clear()
            log.debug("[group_chat] message_send_requested emit len=%d", len(text))
            self.message_send_requested.emit(text)

        def _scroll_to_bottom_once(self) -> None:
            """rangeChanged 1회용 핸들러 — 스크롤바 끝 이동 후 disconnect."""

            scrollbar = self._scroll.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            try:
                scrollbar.rangeChanged.disconnect(self._scroll_to_bottom_once)
            except TypeError:
                pass
