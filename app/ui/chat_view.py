# SPDX-License-Identifier: GPL-3.0-or-later
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

from PyQt6.QtCore import QCoreApplication, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.message_bubble import MessageBubble
from app.ui.sound_player import SoundPlayer

log = logging.getLogger(__name__)


# 한글 주석 — cycle 144 i18n production binding helper. MainWindow context 정합.
_tr = lambda src: QCoreApplication.translate("MainWindow", src)


def connection_state_label(state: str) -> str:
    """연결 상태 의 i18n 라벨 — "온라인" / "오프라인" / "연결 중" 의 .ts 매핑.

    Parameters
    ----------
    state : str
        ``"online"`` | ``"offline"`` | ``"connecting"`` 의 3 path.

    Returns
    -------
    str
        활성 locale 의 tr() lookup. unsupported state = raw `state` 반환.
    """

    # 한글 주석 — 3 .ts entry tr() lookup (en=Online/Offline/Connecting 등).
    if state == "online":
        return _tr("온라인")
    if state == "offline":
        return _tr("오프라인")
    if state == "connecting":
        return _tr("연결 중")
    return state


def should_play_on_message(
    is_self: bool, sound_player: Optional[SoundPlayer]
) -> bool:
    """메시지 수신 시 시그니처 사운드 재생 여부 판정.

    Parameters
    ----------
    is_self : bool
        True = 자기 발신 (sound noise 회피 미재생).
    sound_player : SoundPlayer | None
        주입된 player. None = 미설정 = 미재생.

    Returns
    -------
    bool
        True = play_signature() 호출 대상. False = skip.

    Notes
    -----
    self 발신 미재생 = UX 의무 (자기 입력 직후 sound 발생 시 distracting).
    peer 발신만 trigger. player 부재 = graceful 폴백.
    """

    if is_self:
        return False
    if sound_player is None:
        return False
    return sound_player.enabled


class ChatView(QScrollArea):
    """채팅 메시지 리스트 컨테이너.

    내부 구조:

    - 본 위젯 자체는 ``QScrollArea``
    - 콘텐츠 위젯은 ``QWidget`` (``_content``)
    - 콘텐츠 안에는 수직 ``QVBoxLayout`` (``_messages_layout``)
    - 신규 버블은 ``_messages_layout`` 의 ``stretch`` 슬롯 직전에 삽입
    """

    # cycle 154 — bubble reply_requested signal 재발산 → main_window reply mode set
    reply_to_message = pyqtSignal(str, str)  # (sender, text)

    def _on_bubble_reply_requested(self, sender: str, text: str) -> None:
        """bubble reply_requested 재발산 → main_window reply mode chain."""
        self.reply_to_message.emit(sender, text)

    def resolve_last_message_id(self, message_id: int) -> None:
        """server POST 응답 message_id resolve → 직전 bubble.set_message_id chain (cycle 162)."""
        if self._last_bubble is not None:
            self._last_bubble.set_message_id(message_id)

    def register_pending_bubble(self, client_uuid: str) -> None:
        """송신 직전 client uuid → bubble mapping 등록 (cycle 163 race 해소).

        main_window post_message 직전 호출 의무. server resolve 시점 lookup chain.
        """
        if self._last_bubble is not None:
            self._pending_bubbles[client_uuid] = self._last_bubble

    def resolve_pending_message_id(self, client_uuid: str, message_id: int) -> bool:
        """client uuid lookup → bubble.set_message_id chain (cycle 163).

        Returns
        -------
        bool
            lookup 성공 + set 완료 시 True, uuid 부재 시 False.
        """
        bubble = self._pending_bubbles.pop(client_uuid, None)
        if bubble is None:
            return False
        bubble.set_message_id(message_id)
        return True

    def add_message_from_payload(self, payload) -> None:
        """MessagePayload (cycle 156) → add_message 변환 — DataChannel 수신 path.

        Parameters
        ----------
        payload : MessagePayload
            DataChannel.from_json 결과 model.
        """
        # 한글 주석 — ReplyToField → ReplyContext 변환 (message_bubble dataclass 정합)
        from datetime import datetime
        from app.ui.message_bubble import ReplyContext

        reply_ctx = None
        if payload.reply_to is not None:
            reply_ctx = ReplyContext(
                original_sender=payload.reply_to.sender,
                original_text=payload.reply_to.preview,
            )
        # 한글 주석 — epoch millis → datetime 변환
        ts = datetime.fromtimestamp(payload.ts / 1000.0) if payload.ts else datetime.now()
        self.add_message(
            sender=payload.sender,
            text=payload.text,
            ts=ts,
            is_self=False,  # 수신 path = peer 발신
            reply_to=reply_ctx,
            reactions=payload.reactions,
        )

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        sound_player: Optional[SoundPlayer] = None,
        reactions_client: Optional[object] = None,
    ) -> None:
        """ScrollArea + 내부 VBox 레이아웃 초기화.

        Parameters
        ----------
        parent : QWidget | None
            Qt 부모 위젯.
        sound_player : SoundPlayer | None
            peer 메시지 수신 시 시그니처 사운드 재생 트리거. None =
            미재생 (graceful 폴백, test 환경 정합).
        """

        super().__init__(parent)
        self._sound_player = sound_player
        # cycle 159 — reactions_client (app.net.reactions_client) 주입 — bubble 전달
        self._reactions_client = reactions_client
        # cycle 162 — 마지막 bubble 참조 보관 (server message_id resolve 후 set_message_id chain)
        self._last_bubble = None
        # cycle 163 — pending bubble dict (client uuid → bubble) — race 해소 chain
        # multi-bubble 동시 송신 시 server resolve 시점 uuid lookup 의무
        self._pending_bubbles: dict[str, object] = {}

        # 스크롤 영역 기본 설정 — 가로 스크롤은 비활성, 세로만 사용
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 콘텐츠 위젯 — 본 위젯 안에 실제 버블들이 쌓이는 영역
        self._content = QWidget(self)
        self._messages_layout = QVBoxLayout(self._content)
        # cycle 169.129 — sub-agent A drift D-19 — telegram align (margins 8→16 + spacing 6→4)
        self._messages_layout.setContentsMargins(16, 12, 16, 12)
        self._messages_layout.setSpacing(4)
        # 마지막에 빈 stretch 를 두어 메시지가 적을 때 위쪽으로 정렬
        self._messages_layout.addStretch(1)

        # cycle 169.144 — sender grouping state (telegram align D-20)
        # 동일 sender 연속 시 sender label/tail 생략 + spacing 단축 (2px)
        self._prev_sender: Optional[str] = None
        self._prev_is_self: Optional[bool] = None
        # cycle 169.176 — per-chat scroll offset retain (chat 전환 시점 prev offset restore)
        # key = (kind, target_id) → int (scrollbar.value())
        self._scroll_offsets: dict[tuple[str, int], int] = {}
        self._scroll_active_key: Optional[tuple[str, int]] = None

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
        *,
        reply_to: Optional["object"] = None,
        reactions: Optional[dict] = None,
        message_id: Optional[int] = None,
        hide_sender: bool = False,
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
            ``True`` 인 경우 self 발신 — 버블이 우측 정렬되고 색상 분기.
        """

        # cycle 169.144 — sender grouping detect (telegram align)
        # 직전 bubble = 동일 sender + 동일 is_self → grouped (sender label 생략)
        is_grouped = (
            self._prev_sender == sender
            and self._prev_is_self == is_self
        )
        self._prev_sender = sender
        self._prev_is_self = is_self

        bubble = MessageBubble(
            sender=sender,
            text=text,
            ts=ts,
            is_self=is_self,
            parent=self._content,
            reply_to=reply_to,  # type: ignore[arg-type]
            reactions=reactions,
            grouped=is_grouped,
            hide_sender=hide_sender,
        )
        # 한글 주석 — cycle 154 reply_requested signal → parent main_window 안 reply mode set
        try:
            bubble.reply_requested.connect(self._on_bubble_reply_requested)  # type: ignore[arg-type]
        except Exception:  # pragma: no cover - graceful
            pass
        # 한글 주석 — cycle 159 reactions_client injection (REST persist chain)
        if self._reactions_client is not None:
            bubble.set_reactions_client(self._reactions_client)
        # cycle 162 — message_id 주입 (server POST 응답 안 message_id 의무)
        if message_id is not None:
            bubble.set_message_id(message_id)
        # cycle 162 — bubble dict 추적 (server message_id resolve 시점 lookup chain)
        self._last_bubble = bubble

        # stretch 슬롯 직전 (count - 1 위치) 에 삽입
        insert_at = max(0, self._messages_layout.count() - 1)
        self._messages_layout.insertWidget(insert_at, bubble)

        # 다음 이벤트 사이클에 스크롤바를 끝까지 이동
        # (현재 사이클에서는 layout 이 아직 갱신되지 않을 수 있음)
        scrollbar = self.verticalScrollBar()
        scrollbar.rangeChanged.connect(self._scroll_to_bottom_once)

        # peer 수신 메시지 = 시그니처 사운드 재생 트리거 (사용자 directive
        # 2026-05-17 "텔레그램/카카오톡 뿅 등가"). self 발신 + player 부재
        # + 음소거 상태 = should_play_on_message 의 False 폴백.
        if should_play_on_message(is_self, self._sound_player):
            self._sound_player.play_signature()  # type: ignore[union-attr]

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

    def scroll_to_bottom(self) -> None:
        """cycle 169.164 — chat 전환 + replay 직후 scrollbar bottom 강제 이동 (telegram align)."""
        from PyQt6.QtCore import QTimer
        # 한글 주석 — layout 갱신 직후 scroll 호출 의무 (QTimer.singleShot 0 ms)
        QTimer.singleShot(0, self._do_scroll_bottom)

    def _do_scroll_bottom(self) -> None:
        """deferred scroll bottom — layout 갱신 후 호출 (cycle 169.164)."""
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def save_scroll_offset(self) -> None:
        """cycle 169.176 — 현 active chat 의 scroll offset retain (chat 전환 직전 호출)."""
        if self._scroll_active_key is not None:
            self._scroll_offsets[self._scroll_active_key] = self.verticalScrollBar().value()

    def restore_scroll_offset(self, kind: str, target_id: int) -> bool:
        """cycle 169.176 — kind/target_id 의 prev scroll offset restore.

        Returns
        -------
        bool
            True = restore PASS / False = prev offset 부재 (caller scroll_to_bottom fallback).
        """
        from PyQt6.QtCore import QTimer
        key = (kind, target_id)
        self._scroll_active_key = key
        if key in self._scroll_offsets:
            offset = self._scroll_offsets[key]
            QTimer.singleShot(0, lambda v=offset: self.verticalScrollBar().setValue(v))
            return True
        return False

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
