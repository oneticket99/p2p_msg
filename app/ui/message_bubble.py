"""MessageBubble — 단일 메시지 표시 위젯 (텍스트 + 타임스탬프).

self 발신 / peer 발신 분기:

- self 발신 (``is_self=True``)  : 버블이 우측 정렬, 배경색 분기
- peer 발신 (``is_self=False``) : 버블이 좌측 정렬, 발신자 라벨 노출

색상값은 하드코딩하지 않고 객체 속성 이름으로만 노출하며, 실제 색상은
Phase 후반의 통합 테마 시트(``app/ui/theme.qss``)에서 ``objectName`` 셀렉터
경유로 적용한다 — 정본 §E 하드코딩 금지 규약 정합. 본 스켈레톤에서는
최소한의 setStyleSheet 만 사용하되 색상 코드는 클래스 상수로 분리한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class MessageBubble(QFrame):
    """단일 메시지 버블 위젯.

    레이아웃:

    ```
    [발신자 표시명]                     ← peer 발신 시에만 노출
    [메시지 본문 ……………………………]
                          [HH:MM]       ← 타임스탬프 (우측 하단)
    ```

    Parameters
    ----------
    sender : str
        발신자 표시명 — self 발신일 때도 보관하지만 라벨로 표시하지는 않는다.
    text : str
        메시지 본문 텍스트.
    ts : datetime
        메시지 도착 시각.
    is_self : bool
        self 발신 여부 — 정렬·색상 분기 기준.
    parent : QWidget | None
        상위 위젯.
    """

    # 색상 클래스 상수 — 추후 ``app/ui/theme.qss`` 변수로 이관 예정
    # (Phase 1 후반 테마 시스템 도입 시점에 setStyleSheet 호출 제거)
    _COLOR_SELF_BG = "#dcf8c6"
    _COLOR_PEER_BG = "#ffffff"
    _COLOR_BORDER = "#dddddd"
    _COLOR_TS = "#888888"
    _COLOR_SENDER = "#555555"

    def __init__(
        self,
        sender: str,
        text: str,
        ts: datetime,
        is_self: bool,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._sender = sender
        self._text = text
        self._ts = ts
        self._is_self = is_self

        # 본 위젯은 가로로 가득 차도록 두고, 내부 정렬을 통해 좌/우 분기
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # self 발신 — 좌측 stretch 로 우측 밀어두기
        if is_self:
            outer.addStretch(1)

        # 실제 말풍선 컨테이너
        bubble = QFrame(self)
        bubble.setObjectName("messageBubble")
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(8, 6, 8, 6)
        bubble_layout.setSpacing(2)

        # peer 발신 시 발신자 라벨 노출
        if not is_self:
            sender_label = QLabel(sender, bubble)
            sender_label.setStyleSheet(
                f"color: {self._COLOR_SENDER}; font-size: 11px; font-weight: 600;"
            )
            bubble_layout.addWidget(sender_label)

        # 본문 텍스트 라벨 — 줄바꿈 허용 + 한글 글꼴 fallback + dark mode 안 text color 명시
        text_label = QLabel(text, bubble)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        text_label.setStyleSheet(
            "color: #1a1a1a;"
            " font-size: 13px;"
            " font-family: -apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR',"
            " 'Malgun Gothic', sans-serif;"
        )
        bubble_layout.addWidget(text_label)

        # 타임스탬프 — 우측 하단 회색 텍스트
        ts_label = QLabel(self._format_ts(ts), bubble)
        ts_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom
        )
        ts_label.setStyleSheet(
            f"color: {self._COLOR_TS}; font-size: 10px;"
        )
        bubble_layout.addWidget(ts_label)

        # 말풍선 스타일 — self/peer 색상 분기
        bg = self._COLOR_SELF_BG if is_self else self._COLOR_PEER_BG
        bubble.setStyleSheet(
            "QFrame#messageBubble {"
            f" background-color: {bg};"
            f" border: 1px solid {self._COLOR_BORDER};"
            " border-radius: 8px;"
            "}"
        )
        bubble.setMaximumWidth(380)

        outer.addWidget(bubble)

        # peer 발신 — 우측 stretch 로 좌측 정렬
        if not is_self:
            outer.addStretch(1)

    @staticmethod
    def _format_ts(ts: datetime) -> str:
        """타임스탬프 표시 형식 — 정본 §E ``[YYYY-mm-dd H:i:s]`` 의 짧은 변형.

        리스트에 가지런히 노출되도록 ``HH:MM`` 만 노출. 전체 시각이 필요하면
        툴팁으로 분리(추후 작업)한다.
        """

        return ts.strftime("%H:%M")
