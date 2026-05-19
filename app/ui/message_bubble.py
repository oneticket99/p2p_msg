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

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QContextMenuEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class ReplyContext:
    """reply preview view model — bubble 안 border-left preview 표기."""
    original_sender: str
    original_text: str
    original_ts: Optional[datetime] = None


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

    # 색상 클래스 상수 — Toonation BI 정합 (cycle 153.6 회수)
    # FRONTEND.md §15 + base-dark.qss QSS#messageBubbleSelf/#messageBubblePeer 정합
    _COLOR_SELF_BG = "#0066FF"      # Toonation Blue primary
    _COLOR_PEER_BG = "#1F2937"      # Deep Navy 변형
    _COLOR_BORDER = "#374151"
    _COLOR_TS = "#9ca3af"
    _COLOR_SENDER = "#67E8F9"       # 포인트 cyan
    _COLOR_REPLY_BORDER = "#22D3EE" # reply preview border-left

    reply_requested = pyqtSignal(str, str)  # (sender, text) emit
    reaction_added = pyqtSignal(str)         # emoji emit

    def __init__(
        self,
        sender: str,
        text: str,
        ts: datetime,
        is_self: bool,
        parent: Optional[QWidget] = None,
        *,
        reply_to: Optional[ReplyContext] = None,
        reactions: Optional[dict[str, int]] = None,
    ) -> None:
        super().__init__(parent)

        self._sender = sender
        self._text = text
        self._ts = ts
        self._is_self = is_self
        self._reply_to = reply_to
        self._reactions: dict[str, int] = dict(reactions or {})

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

        # 한글 주석 — reply preview (border-left + 원본 sender + 첫 줄 preview, cycle 153.6 신설)
        if reply_to is not None:
            reply_frame = QFrame(bubble)
            reply_frame.setStyleSheet(
                "QFrame {"
                f" border-left: 3px solid {self._COLOR_REPLY_BORDER};"
                " background-color: rgba(34, 211, 238, 0.08);"
                " padding: 4px 8px;"
                " border-radius: 4px;"
                "}"
            )
            reply_layout = QVBoxLayout(reply_frame)
            reply_layout.setContentsMargins(8, 4, 4, 4)
            reply_layout.setSpacing(2)
            reply_sender = QLabel(f"↳ {reply_to.original_sender}", reply_frame)
            reply_sender.setStyleSheet(f"color: {self._COLOR_REPLY_BORDER}; font-size: 11px; font-weight: 600;")
            reply_layout.addWidget(reply_sender)
            reply_text = QLabel(reply_to.original_text[:60], reply_frame)
            reply_text.setStyleSheet("color: #9ca3af; font-size: 12px;")
            reply_text.setWordWrap(True)
            reply_layout.addWidget(reply_text)
            bubble_layout.addWidget(reply_frame)

        # 본문 텍스트 라벨 — Toonation BI 통합 + self/peer 색상 분기
        text_label = QLabel(text, bubble)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        text_color = "#ffffff" if is_self else "#e5e7eb"
        text_label.setStyleSheet(
            f"color: {text_color};"
            " font-size: 13px;"
            " font-family: -apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR',"
            " 'Malgun Gothic', sans-serif;"
        )
        bubble_layout.addWidget(text_label)

        # 한글 주석 — reaction pill row (cycle 153.6 신설) — emoji + count
        if self._reactions:
            reaction_row = QHBoxLayout()
            reaction_row.setContentsMargins(0, 4, 0, 0)
            reaction_row.setSpacing(4)
            reaction_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
            for emoji, count in self._reactions.items():
                pill = QLabel(f"{emoji} {count}", bubble)
                pill.setStyleSheet(
                    "QLabel {"
                    " background-color: rgba(34, 211, 238, 0.15);"
                    " border: 1px solid rgba(34, 211, 238, 0.3);"
                    " border-radius: 10px;"
                    " padding: 2px 8px;"
                    " font-size: 11px;"
                    " color: #67E8F9;"
                    "}"
                )
                reaction_row.addWidget(pill)
            reaction_row.addStretch(1)
            bubble_layout.addLayout(reaction_row)

        # 타임스탬프 + read receipt ✓✓ — 우측 하단
        ts_row = QHBoxLayout()
        ts_row.setContentsMargins(0, 0, 0, 0)
        ts_row.setSpacing(4)
        ts_row.addStretch(1)
        ts_label = QLabel(self._format_ts(ts), bubble)
        ts_label.setStyleSheet(f"color: {self._COLOR_TS}; font-size: 10px;")
        ts_row.addWidget(ts_label)
        if is_self:
            check_label = QLabel("✓✓", bubble)
            check_label.setStyleSheet("color: #67E8F9; font-size: 10px;")
            ts_row.addWidget(check_label)
        bubble_layout.addLayout(ts_row)

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

    def add_reaction(self, emoji: str) -> None:
        """reaction pill 추가 — count 증분 + signal emit."""
        self._reactions[emoji] = self._reactions.get(emoji, 0) + 1
        self.reaction_added.emit(emoji)

    def reactions(self) -> dict[str, int]:
        """현 reaction count snapshot."""
        return dict(self._reactions)

    def contextMenuEvent(self, event: Optional[QContextMenuEvent]) -> None:  # type: ignore[override]
        """우 click context menu — 답장 / 반응 / 복사 / 전달 / 삭제 5 entry."""
        if event is None:
            return
        menu = QMenu(self)
        act_reply = menu.addAction("↳ 답장")
        act_react = menu.addAction("😀 반응 추가")
        act_copy = menu.addAction("📋 복사")
        act_forward = menu.addAction("➡ 전달 (cycle 155+)")
        menu.addSeparator()
        act_delete = menu.addAction("🗑 삭제")

        chosen = menu.exec(event.globalPos())
        if chosen is None:
            return
        if chosen is act_reply:
            self.reply_requested.emit(self._sender, self._text)
        elif chosen is act_react:
            self.add_reaction("👍")
        elif chosen is act_copy:
            app = QApplication.instance()
            if app is not None:
                clipboard = app.clipboard()  # type: ignore[attr-defined]
                if clipboard is not None:
                    clipboard.setText(self._text)

    @staticmethod
    def _format_ts(ts: datetime) -> str:
        """타임스탬프 표시 형식 — 정본 §E ``[YYYY-mm-dd H:i:s]`` 의 짧은 변형.

        리스트에 가지런히 노출되도록 ``HH:MM`` 만 노출. 전체 시각이 필요하면
        툴팁으로 분리(추후 작업)한다.
        """

        return ts.strftime("%H:%M")
