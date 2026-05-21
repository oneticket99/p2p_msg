# SPDX-License-Identifier: GPL-3.0-or-later
"""Typing indicator bubble — bot 응답 대기 시점 의 의 메시지 작성 중 animation (cycle 169.284).

사용자 directive image #58 회수:
- bot 응답 대기 시점 상대방 말풍선 의 의 "메시지 작성 중..." indicator
- "." → ".." → "..." → "." 순차 dot animation
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget


class TypingIndicator(QFrame):
    """상대방 말풍선 of 메시지 작성 중 + dot animation."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame {"
            " background-color: #1F2937;"
            " border-radius: 14px;"
            " padding: 8px 14px;"
            "}"
        )
        self.setMaximumWidth(160)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)
        self._label = QLabel("메시지 작성 중.")
        self._label.setStyleSheet("color: #9ca3af; font-size: 13px; background-color: transparent;")
        layout.addWidget(self._label)

        # 한글 주석 — dot animation cycle ('.' → '..' → '...')
        self._dot_count = 1
        self._timer = QTimer(self)
        self._timer.setInterval(400)
        self._timer.timeout.connect(self._tick)  # type: ignore[arg-type]
        self._timer.start()

    def _tick(self) -> None:
        self._dot_count = (self._dot_count % 3) + 1
        self._label.setText("메시지 작성 중" + ("." * self._dot_count))

    def stop(self) -> None:
        """timer 정지 + GC 정합."""
        try:
            self._timer.stop()
        except Exception:  # pragma: no cover
            pass
