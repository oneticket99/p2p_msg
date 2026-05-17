"""ChatView — 메시지 리스트 스크롤 영역.

QScrollArea 안에 QVBoxLayout 을 배치하고 신규 메시지가 도착할 때마다
``MessageBubble`` 위젯을 ``addWidget`` 으로 누적한다. 본 Phase 1 스켈레톤은
텍스트 메시지만 표시하며, 이미지/파일 미리보기는 Task #16 에서 별도
추가한다.

핵심 동작:

- ``add_message(sender, text, ts, is_self)`` — 호출 시 새 버블 추가 + 자동
  스크롤 (가장 최근 메시지가 시야 안에 들어오도록 스크롤바를 아래로 이동).
- 위 메서드는 Qt slot 안에서 동기 호출 가능 (정본 §E — UI 표시만 수행).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.message_bubble import MessageBubble

log = logging.getLogger(__name__)


class ChatView(QScrollArea):
    """채팅 메시지 리스트 컨테이너.

    내부 구조:

    - 본 위젯 자체는 ``QScrollArea``
    - 콘텐츠 위젯은 ``QWidget`` (``_content``)
    - 콘텐츠 안에는 수직 ``QVBoxLayout`` (``_messages_layout``)
    - 신규 버블은 ``_messages_layout`` 의 ``stretch`` 슬롯 직전에 삽입
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """ScrollArea + 내부 VBox 레이아웃 초기화."""

        super().__init__(parent)

        # 스크롤 영역 기본 설정 — 가로 스크롤은 비활성, 세로만 사용
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 콘텐츠 위젯 — 본 위젯 안에 실제 버블들이 쌓이는 영역
        self._content = QWidget(self)
        self._messages_layout = QVBoxLayout(self._content)
        self._messages_layout.setContentsMargins(8, 8, 8, 8)
        self._messages_layout.setSpacing(6)
        # 마지막에 빈 stretch 를 두어 메시지가 적을 때 위쪽으로 정렬
        self._messages_layout.addStretch(1)

        self.setWidget(self._content)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def add_message(
        self,
        sender: str,
        text: str,
        ts: datetime,
        is_self: bool = False,
    ) -> None:
        """신규 메시지를 리스트에 추가하고 하단으로 자동 스크롤.

        Parameters
        ----------
        sender : str
            발신자 표시명 (peer_id 또는 닉네임).
        text : str
            메시지 본문 (텍스트).
        ts : datetime
            메시지 도착 시각.
        is_self : bool
            ``True`` 인 경우 본인 발신 — 버블이 우측 정렬되고 색상 분기.
        """

        bubble = MessageBubble(
            sender=sender,
            text=text,
            ts=ts,
            is_self=is_self,
            parent=self._content,
        )

        # stretch 슬롯 직전 (count - 1 위치) 에 삽입
        insert_at = max(0, self._messages_layout.count() - 1)
        self._messages_layout.insertWidget(insert_at, bubble)

        # 다음 이벤트 사이클에 스크롤바를 끝까지 이동
        # (현재 사이클에서는 layout 이 아직 갱신되지 않을 수 있음)
        scrollbar = self.verticalScrollBar()
        scrollbar.rangeChanged.connect(self._scroll_to_bottom_once)

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    def _scroll_to_bottom_once(self) -> None:
        """rangeChanged 시그널 1회용 핸들러 — 스크롤을 끝까지 이동 후 해제."""

        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # 1회 연결이므로 동일 시그널과 연결 해제하여 누적 호출을 방지
        try:
            scrollbar.rangeChanged.disconnect(self._scroll_to_bottom_once)
        except TypeError:
            # 이미 해제됐거나 연결 정보 누락 — 무시
            pass

    def clear_messages(self) -> None:
        """모든 메시지 버블 제거 — 방 전환 등에서 호출.

        stretch 슬롯은 유지하고 그 앞의 위젯만 일괄 제거한다.
        """

        # stretch 슬롯(마지막 1개) 직전까지 역순 제거
        while self._messages_layout.count() > 1:
            item = self._messages_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
