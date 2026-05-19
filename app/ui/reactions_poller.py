# SPDX-License-Identifier: GPL-3.0-or-later
"""ReactionsPoller — bubble pill 실시간 갱신 polling chain (cycle 164 신설).

WebSocket push 부재 환경 fallback — reactions REST list endpoint 의 polling 30s.
cycle 165+ WebSocket actual binding 시점 본 polling 차단 (graceful disable).

설계:
- 활성 ChatView 의 bubble 안 message_id 보유 row 만 polling 대상
- 30s interval (TooTalk 텔레그램 모델 정합 — 즉시 push 부재 fallback)
- ReactionsClient.list_reactions(message_id) async + bubble._reactions dict 직접 갱신
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

log = logging.getLogger(__name__)

POLL_INTERVAL_MS = 30_000  # 30s


class ReactionsPoller(QObject):
    """ChatView 내부 bubble 안 reactions REST polling — 30s interval."""

    reactions_updated = pyqtSignal(int, dict)  # (message_id, {emoji: count})

    def __init__(
        self,
        chat_view,
        reactions_client,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._chat_view = chat_view
        self._client = reactions_client
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._on_timeout)  # type: ignore[arg-type]
        self._active = False

    def start(self) -> None:
        """polling timer 시작 — 30s interval fire."""
        if self._client is None:
            log.debug("ReactionsPoller — client 부재 graceful skip")
            return
        self._active = True
        self._timer.start()
        log.info("ReactionsPoller 시작 — interval=%dms", POLL_INTERVAL_MS)

    def stop(self) -> None:
        """polling timer 종료 — WebSocket push 활성 시 호출."""
        self._active = False
        self._timer.stop()

    def _on_timeout(self) -> None:
        """timer fire — 활성 bubble dict iterate + polling chain."""
        if not self._active or self._client is None:
            return
        try:
            asyncio.ensure_future(self._poll_all_bubbles())
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("poll dispatch 실패 — %r", exc)

    async def _poll_all_bubbles(self) -> None:
        """모든 message_id 보유 bubble 의 reactions REST polling."""
        layout = getattr(self._chat_view, "_messages_layout", None)
        if layout is None:
            return
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget is None or not hasattr(widget, "message_id"):
                continue
            msg_id = widget.message_id()
            if msg_id is None:
                continue
            await self._poll_single(widget, int(msg_id))

    async def _poll_single(self, bubble, message_id: int) -> None:
        """단일 bubble polling — list_reactions + emit + bubble.update_reactions chain (cycle 165)."""
        try:
            entries = await self._client.list_reactions(message_id)
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("poll list_reactions 실패 — message_id=%d %r", message_id, exc)
            return
        new_dict = {entry.emoji: entry.count for entry in entries}
        # cycle 165 — bubble.update_reactions 호출 (pill UI 즉시 갱신)
        if hasattr(bubble, "update_reactions"):
            bubble.update_reactions(new_dict)  # type: ignore[attr-defined]
        elif hasattr(bubble, "_reactions"):
            bubble._reactions = new_dict  # type: ignore[attr-defined]
        self.reactions_updated.emit(message_id, new_dict)
