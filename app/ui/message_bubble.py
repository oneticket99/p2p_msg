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
        grouped: bool = False,
    ) -> None:
        super().__init__(parent)

        self._sender = sender
        self._text = text
        self._ts = ts
        self._is_self = is_self
        self._reply_to = reply_to
        self._reactions: dict[str, int] = dict(reactions or {})
        # cycle 169.144 — telegram align sender grouping (직전 bubble 의 sender 동일 시 True)
        self._grouped = grouped

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

        # cycle 169.144 — grouped=True 시 sender label 생략 (telegram align D-20)
        # peer 발신 + 첫 bubble (non-grouped) 만 sender label render
        if not is_self and not self._grouped:
            from app.ui.avatar_palette import palette_solid
            sender_color = palette_solid(sender)
            sender_label = QLabel(sender, bubble)
            sender_label.setStyleSheet(
                f"color: {sender_color}; font-size: 11px; font-weight: 600;"
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

        # 한글 주석 — cycle 169.69 회수 — 타임스탬프 + read receipt ✓✓ telegram desktop align
        # ts + check 3px gap + 우측 하단 정합 + baseline align
        ts_row = QHBoxLayout()
        ts_row.setContentsMargins(0, 2, 0, 0)
        ts_row.setSpacing(3)
        ts_row.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        ts_row.addStretch(1)
        ts_label = QLabel(self._format_ts(ts), bubble)
        ts_label.setStyleSheet(f"color: {self._COLOR_TS}; font-size: 11px;")
        ts_row.addWidget(ts_label, alignment=Qt.AlignmentFlag.AlignBottom)
        if is_self:
            # 한글 주석 — telegram align — check ✓✓ unicode 의 의 cyan + 의 의 baseline
            check_label = QLabel("✓✓", bubble)
            check_label.setStyleSheet("color: #67E8F9; font-size: 11px; font-weight: 700;")
            ts_row.addWidget(check_label, alignment=Qt.AlignmentFlag.AlignBottom)
        bubble_layout.addLayout(ts_row)

        # 말풍선 스타일 — self/peer 색상 분기 (cycle 169.110 — Figma radius 16 + corner 4 tail)
        bg = self._COLOR_SELF_BG if is_self else self._COLOR_PEER_BG
        # 한글 주석 — cycle 169.51 회수 — 사용자 directive verbatim "글자의 배경색 전부 제거".
        # cycle 169.110 — Figma 정합 — radius 16 + tail corner 4 (self bottom-right / peer bottom-left)
        tail_corner = "border-bottom-right-radius: 4px;" if is_self else "border-bottom-left-radius: 4px;"
        bubble.setStyleSheet(
            "QFrame#messageBubble {"
            f" background-color: {bg};"
            " border: none;"
            " border-radius: 16px;"
            f" {tail_corner}"
            "}"
            "QFrame#messageBubble QLabel {"
            " background-color: transparent;"
            "}"
        )
        # cycle 169.128 — sub-agent A drift D-14 — 420→480 (telegram 65% rule)
        bubble.setMaximumWidth(480)

        outer.addWidget(bubble)

        # peer 발신 — 우측 stretch 로 좌측 정렬
        if not is_self:
            outer.addStretch(1)

    # cycle 158 — message_id 보관 (server-side reactions REST chain 의무)
    _message_id: Optional[int] = None
    # cycle 159 — reactions_client 의존성 (graceful 부재 시 local-only chain)
    _reactions_client = None

    def set_message_id(self, message_id: int) -> None:
        """server-side message_id 등록 — reactions REST chain prereq."""
        self._message_id = message_id

    def set_reactions_client(self, client) -> None:
        """reactions_client (cycle 156) injection — REST persist chain (cycle 159 신설)."""
        self._reactions_client = client

    def message_id(self) -> Optional[int]:
        """현 message_id snapshot."""
        return self._message_id

    def add_reaction(self, emoji: str) -> None:
        """reaction pill 추가 — count 증분 + signal emit + REST persist + UI 즉시 갱신 (cycle 165)."""
        self._reactions[emoji] = self._reactions.get(emoji, 0) + 1
        self.reaction_added.emit(emoji)
        # cycle 165 — pill UI 즉시 갱신
        self.refresh_reactions_ui()
        # 한글 주석 — cycle 159 — server REST persist async chain (graceful 부재)
        if self._reactions_client is not None and self._message_id is not None:
            try:
                import asyncio
                asyncio.ensure_future(
                    self._reactions_client.add_reaction(self._message_id, emoji)
                )
            except Exception as exc:  # pragma: no cover - graceful
                import logging
                logging.getLogger(__name__).debug("reactions REST persist 실패 — %r", exc)

    def update_reactions(self, reactions: dict) -> None:
        """reactions dict 외부 갱신 — polling/WebSocket 수신 path (cycle 165 신설)."""
        self._reactions = dict(reactions)
        self.refresh_reactions_ui()

    def refresh_reactions_ui(self) -> None:
        """기존 reaction row 제거 + 신규 pill row rebuild (cycle 165 신설)."""
        # 한글 주석 — bubble 내부 QFrame 안 ts_row 직전 의 reaction layout 재 build
        # _reaction_row attribute 보관 + deleteLater + 재 생성 chain
        existing = getattr(self, "_reaction_row_widget", None)
        if existing is not None:
            existing.deleteLater()
            self._reaction_row_widget = None

        if not self._reactions:
            return

        # 한글 주석 — bubble 안 child QFrame 의 layout lookup
        bubble = self.findChild(QFrame, "messageBubble")
        if bubble is None:
            return
        bubble_layout = bubble.layout()
        if bubble_layout is None:
            return

        # 한글 주석 — 신규 reaction row container QWidget + HBoxLayout
        from PyQt6.QtWidgets import QHBoxLayout as _H, QWidget as _W
        row_widget = _W(bubble)
        row_layout = _H(row_widget)
        row_layout.setContentsMargins(0, 4, 0, 0)
        row_layout.setSpacing(4)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        for emoji, count in self._reactions.items():
            pill = QLabel(f"{emoji} {count}", row_widget)
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
            row_layout.addWidget(pill)
        row_layout.addStretch(1)
        # 한글 주석 — ts_row 직전 insert (count - 1 위치) — bubble layout 안 마지막 직전
        insert_at = max(0, bubble_layout.count() - 1)
        bubble_layout.insertWidget(insert_at, row_widget)
        self._reaction_row_widget = row_widget

    def _open_reaction_picker(self, global_pos: "QPoint") -> None:
        """EmojiPicker popup → 선택 시 add_reaction chain."""
        try:
            from app.ui.emoji_picker import EmojiPicker
        except Exception:  # pragma: no cover - graceful
            self.add_reaction("👍")
            return
        picker = EmojiPicker(parent=self)
        picker.setWindowFlags(Qt.WindowType.Popup)
        picker.emoji_selected.connect(self.add_reaction)  # type: ignore[arg-type]
        picker.move(global_pos.x(), global_pos.y())
        picker.show()

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
            self._open_reaction_picker(event.globalPos())
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

        # cycle 169.151 — telegram 한국어 format "오전/오후 H:MM" align
        hour = ts.hour
        minute = ts.minute
        am_pm = "오전" if hour < 12 else "오후"
        h12 = hour if 1 <= hour <= 12 else (hour - 12 if hour > 12 else 12)
        return f"{am_pm} {h12}:{minute:02d}"
