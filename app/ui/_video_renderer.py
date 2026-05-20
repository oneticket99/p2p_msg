# SPDX-License-Identifier: GPL-3.0-or-later
"""VideoRenderer — aiortc VideoStreamTrack 의 frame → QImage 변환 (cycle 169.59 신설).

QTimer 33ms tick (30 fps) — frame.to_ndarray(format="rgb24") → QImage.Format_RGB888.
remote track 의 av.VideoFrame asyncio.Queue 경유.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel

log = logging.getLogger(__name__)


class VideoRenderer:
    """aiortc VideoStreamTrack → QLabel frame loop.

    Parameters
    ----------
    label : QLabel
        frame 표시 대상 QLabel (setPixmap chain).
    track : VideoStreamTrack
        aiortc 의 remote video track (on_track callback 안 받음).
    """

    def __init__(self, label: QLabel, track: Any) -> None:
        self._label = label
        self._track = track
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=2)
        self._timer = QTimer()
        self._timer.setInterval(33)  # 30 fps
        self._timer.timeout.connect(self._on_tick)  # type: ignore[arg-type]
        self._recv_task: Optional[asyncio.Task] = None

    async def _recv_loop(self) -> None:
        """track frame async loop — queue 안 put (overflow drop)."""
        while True:
            try:
                frame = await self._track.recv()
            except Exception as exc:  # noqa: BLE001
                log.warning("[VideoRenderer] recv fail — %r", exc)
                break
            try:
                self._queue.put_nowait(frame)
            except asyncio.QueueFull:
                # 한글 주석 — overflow drop (older frame discard)
                try:
                    self._queue.get_nowait()
                    self._queue.put_nowait(frame)
                except Exception:
                    pass

    def _on_tick(self) -> None:
        """QTimer tick — queue 안 latest frame extract + setPixmap."""
        if self._queue.empty():
            return
        frame = None
        while not self._queue.empty():
            try:
                frame = self._queue.get_nowait()
            except Exception:
                break
        if frame is None:
            return
        try:
            ndarr = frame.to_ndarray(format="rgb24")
            h, w, _ = ndarr.shape
            bytes_per_line = 3 * w
            qimg = QImage(ndarr.tobytes(), w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pix = QPixmap.fromImage(qimg).scaled(
                self._label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._label.setPixmap(pix)
        except Exception as exc:  # noqa: BLE001
            log.warning("[VideoRenderer] render fail — %r", exc)

    def start(self) -> None:
        """recv loop + QTimer 진행."""
        try:
            loop = asyncio.get_event_loop()
            self._recv_task = loop.create_task(self._recv_loop())
        except RuntimeError as exc:
            log.warning("[VideoRenderer] event loop 부재 — start skip (%r)", exc)
            return
        self._timer.start()

    def stop(self) -> None:
        """recv loop + QTimer 종료."""
        self._timer.stop()
        if self._recv_task is not None:
            try:
                self._recv_task.cancel()
            except Exception:
                pass
            self._recv_task = None
