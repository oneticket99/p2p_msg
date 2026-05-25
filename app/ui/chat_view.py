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
    # cycle 169.444 — scroll-up lazy-load signal (caller = main_window subscribe)
    lazy_load_requested = pyqtSignal(int)  # room_id (local namespace)

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
        # cycle 169.179 — day separator state (date 변경 detect)
        self._prev_ts: Optional[datetime] = None
        # cycle 169.176 — per-chat scroll offset retain (chat 전환 시점 prev offset restore)
        # key = (kind, target_id) → int (scrollbar.value())
        self._scroll_offsets: dict[tuple[str, int], int] = {}
        self._scroll_active_key: Optional[tuple[str, int]] = None
        # cycle 169.830 — 표시된 msg_id 집합 (scroll-up lazy load 중복 prepend 차단).
        # add_message/prepend_message 가 msg_id>0 중복 시 skip → "하나씩 증식" 버그 회수.
        self._displayed_msg_ids: set[int] = set()

        self.setWidget(self._content)

        # cycle 169.444 — scroll-up lazy-load chain (사용자 directive — local SQLite + MariaDB sync)
        # scrollbar value <= 30 시점 lazy_load_requested emit. caller = before_msg_id cursor 활용 fetch.
        self._lazy_load_threshold_px: int = 30
        self._lazy_load_active: bool = False  # 중복 fire 차단
        self._active_room_id: int = 0  # 현 chat room_id (local namespace)
        # cycle 169.466 — lazy load valueChanged 재 활성 (prepend incremental chain 정합)
        # _on_scroll_value_changed → lazy_load_requested → main_window prepend chain (clear+replay 폐기)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_value_changed)  # type: ignore[arg-type]

    def set_active_room(self, room_id: int) -> None:
        """cycle 169.444 — chat 전환 시점 active room_id 갱신 (lazy load chain 의 cursor)."""
        self._active_room_id = int(room_id)
        self._lazy_load_active = False  # 새 chat 진입 = lock reset
        self._displayed_msg_ids.clear()  # cycle 169.830 — chat 전환 시 dedup 집합 reset

    def prepend_message(
        self,
        sender: str,
        text: str,
        ts: datetime,
        is_self: bool = False,
        *,
        hide_sender: bool = False,
        msg_id: int = 0,
    ) -> None:
        """cycle 169.466 — 기존 bubble 위 prepend 의무 (lazy load incremental chain).

        clear+replay 대신 layout 최상단 insertWidget(0) — scroll position retain 정합.
        rangeChanged 자동 scroll bottom 차단 (play_sound=False 정합).
        """
        # cycle 169.830 — 중복 msg_id skip (scroll-up 재fetch 시 동일 과거 메시지 재증식 차단)
        if isinstance(msg_id, int) and msg_id > 0:
            if msg_id in self._displayed_msg_ids:
                return
            self._displayed_msg_ids.add(int(msg_id))

        bubble = MessageBubble(
            sender=sender, text=text, ts=ts, is_self=is_self,
            parent=self._content,
            grouped=False, hide_sender=hide_sender,
            msg_id=int(msg_id),
        )
        # 한글 주석 — index 0 = layout 최상단 (모든 기존 bubble 위 prepend)
        self._messages_layout.insertWidget(0, bubble)

    def min_displayed_msg_id(self) -> int:
        """cycle 169.830 — 현재 표시된 msg_id 중 최소값 (lazy load cursor 정합).

        scroll-up older fetch 시 ``before_msg_id`` cursor 로 사용 — sync_state 기반
        stale cursor 대신 실제 화면 최하단(과거) msg_id 기준으로 strictly older fetch →
        동일 window 재fetch(중복 원인) 차단. 표시 id 부재 시 0 반환.
        """
        ids = [m for m in self._displayed_msg_ids if m > 0]
        return min(ids) if ids else 0

    def apply_last_read(self, last_read_msg_id: int) -> None:
        """cycle 169.470 — server last_read_msg_id 안 비교 chain → bubble set_read 갱신.

        peer bubble 의 의 msg_id <= last_read 시점 set_read(True) — 안 읽음 라벨 hide.
        """
        try:
            for i in range(self._messages_layout.count()):
                item = self._messages_layout.itemAt(i)
                if item is None:
                    continue
                widget = item.widget()
                if widget is None or not hasattr(widget, "msg_id"):
                    continue
                try:
                    mid = widget.msg_id()
                    if mid > 0:
                        widget.set_read(mid <= last_read_msg_id)
                except Exception:
                    continue
        except Exception as exc:
            log.debug("[apply_last_read] 실패 — %r", exc)

    def mark_all_bubbles_read(self) -> None:
        """cycle 169.457 — chat focus 시점 모든 peer bubble.set_read(True).

        사용자 directive — 정식 안 읽음 라벨 chain. chat 진입 시점 = 자동 읽음 처리.
        """
        try:
            for i in range(self._messages_layout.count()):
                item = self._messages_layout.itemAt(i)
                if item is None:
                    continue
                widget = item.widget()
                if widget is None:
                    continue
                # 한글 주석 — MessageBubble instance 만 set_read 호출
                if hasattr(widget, "set_read"):
                    try:
                        widget.set_read(True)
                    except Exception:
                        pass
        except Exception as exc:
            log.debug("[mark_all_bubbles_read] 실패 — %r", exc)

    def _on_scroll_value_changed(self, value: int) -> None:
        """cycle 169.444~466 — scrollbar 최상단 도달 시점 lazy load fire (debounce).

        chain:
        - value <= threshold + active_room_id > 0 + lazy_load_active False 시점 fire
        - lazy_load_active True 시점 prepend chain 진행 중 — 중복 fire 차단
        - 사용자 scroll-up 시점 1회 fire 후 prepend 완료 → 사용자 추가 scroll-up 시점 다시 fire
          (사용자 critique 'scroll-up 시점 강제 bottom snap' 회수 의무 — prepend chain = scroll position retain)
        """
        if self._lazy_load_active:
            return
        if value <= self._lazy_load_threshold_px and self._active_room_id > 0:
            self._lazy_load_active = True
            self.lazy_load_requested.emit(self._active_room_id)
            # 한글 주석 — prepend 완료 후 짧은 timer 의무 — 다음 scroll-up 진입 시점 재 fire 가능
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, self._release_lazy_lock)

    def _release_lazy_lock(self) -> None:
        """cycle 169.466 — lazy load lock 해제 (prepend 완료 후 짧은 cooldown chain)."""
        self._lazy_load_active = False

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
        play_sound: bool = True,
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

        # cycle 169.830 — 중복 msg_id skip (lazy load 재fetch 시 동일 메시지 재추가 차단)
        if isinstance(message_id, int) and message_id > 0:
            if message_id in self._displayed_msg_ids:
                return
            self._displayed_msg_ids.add(message_id)

        # cycle 169.179 — day separator inject (date 변경 시 label "오늘/어제/YYYY년 M월 D일")
        if self._prev_ts is None or self._prev_ts.date() != ts.date():
            self._insert_day_separator(ts)

        # cycle 169.144 — sender grouping detect (telegram align)
        # 직전 bubble = 동일 sender + 동일 is_self → grouped (sender label 생략)
        # cycle 169.179 — day separator inject 직후 grouped reset
        is_grouped = (
            self._prev_sender == sender
            and self._prev_is_self == is_self
            and (self._prev_ts is not None and self._prev_ts.date() == ts.date())
        )
        self._prev_sender = sender
        self._prev_is_self = is_self
        self._prev_ts = ts

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
            msg_id=int(message_id) if isinstance(message_id, int) else 0,
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
        # cycle 169.462~463 — play_sound = False 시점 scroll bottom chain 도 차단 (history replay 정합)
        if play_sound:
            scrollbar = self.verticalScrollBar()
            scrollbar.rangeChanged.connect(self._scroll_to_bottom_once)

        # peer 수신 메시지 = 시그니처 사운드 재생 트리거 (사용자 directive
        # 2026-05-17 "텔레그램/카카오톡 뿅 등가"). self 발신 + player 부재
        # + 음소거 상태 = should_play_on_message 의 False 폴백.
        # cycle 169.462 — play_sound parameter (history replay 시점 False 강제, 사용자 critique)
        if play_sound and should_play_on_message(is_self, self._sound_player):
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

    def _insert_day_separator(self, ts: datetime) -> None:
        """cycle 169.179 — day separator label inject (telegram align).

        오늘 = "오늘" / 어제 = "어제" / 그 외 = "YYYY년 M월 D일"
        """
        from PyQt6.QtWidgets import QLabel
        today = datetime.now().date()
        target = ts.date()
        delta = (today - target).days
        if delta == 0:
            text = "오늘"
        elif delta == 1:
            text = "어제"
        else:
            text = f"{target.year}년 {target.month}월 {target.day}일"
        label = QLabel(text, self._content)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            "QLabel {"
            " background-color: rgba(15,23,42,0.7);"
            " color: #9ca3af;"
            " font-size: 11px;"
            " padding: 4px 12px;"
            " border-radius: 12px;"
            "}"
        )
        label.setMaximumHeight(24)
        # stretch 직전 insert (chat_view spacing chain 정합)
        insert_at = max(0, self._messages_layout.count() - 1)
        # 한글 주석 — separator wrap horizontal box (label center align)
        from PyQt6.QtWidgets import QHBoxLayout, QWidget
        wrap = QWidget(self._content)
        wrap_layout = QHBoxLayout(wrap)
        wrap_layout.setContentsMargins(0, 8, 0, 8)
        wrap_layout.setSpacing(0)
        wrap_layout.addStretch(1)
        wrap_layout.addWidget(label)
        wrap_layout.addStretch(1)
        self._messages_layout.insertWidget(insert_at, wrap)
        # day separator 안 sender grouping reset (다음 bubble = 신규 group)
        self._prev_sender = None
        self._prev_is_self = None

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
        # cycle 169.830 — clear 시 dedup 집합도 reset (재로드 시 정상 재표시 보장)
        self._displayed_msg_ids.clear()
        self._prev_sender = None
        self._prev_is_self = None
        self._prev_ts = None
