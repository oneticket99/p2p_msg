# SPDX-License-Identifier: GPL-3.0-or-later
"""GroupCallDialog — SFU 그룹 음성·영상 통화 화면 (cycle 169.806 M4b-2).

계층 위치 — app/ui dialog(정본 §E). QDialog 위젯 — SfuCallMixin 이 instantiate(그룹 통화 타일 그리드).
SfuCallClient(net) 와 협력하되 미디어 협상 무관(UI 전용) — add_remote_track 콜백으로만 결합.

9 peer 이상의 그룹 통화에서 각 producer 의 forward 미디어를 타일 그리드로
표시한다. producer 1명당 ``QLabel`` 타일 + ``VideoRenderer`` (aiortc track →
QImage 30fps) 1개를 매핑하고, 합류·이탈에 따라 타일을 동적 추가/제거한다.

본 위젯은 미디어 협상(SFU_PUBLISH/SUBSCRIBE)에 관여하지 않는다 — ``SfuCallClient``
(net 계층)가 forward track 을 ``on_remote_track`` 콜백으로 넘기면 본 위젯의
``add_remote_track`` 이 타일을 그린다 (계층 분리, UI 전용).
"""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)


class GroupCallDialog(QDialog):
    """SFU 그룹 통화 타일 그리드 — producer 별 video 타일 동적 관리."""

    def __init__(self, room_id: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"TooTalk · 그룹 통화 ({room_id})")
        self.setModal(False)
        self.resize(720, 540)
        self._room_id = room_id
        # producer_id → (QLabel 타일, VideoRenderer)
        self._tiles: dict[str, tuple[QLabel, Any]] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        self._grid = QGridLayout()
        self._grid.setSpacing(8)
        outer.addLayout(self._grid)

    @property
    def room_id(self) -> str:
        return self._room_id

    def tile_count(self) -> int:
        """현재 표시 중인 producer 타일 수."""
        return len(self._tiles)

    def producer_ids(self) -> list[str]:
        """타일이 존재하는 producer 목록."""
        return list(self._tiles.keys())

    def add_remote_track(self, producer_id: str, track: Any) -> None:
        """producer 의 forward track 을 새 타일로 추가한다 (재수신 시 교체).

        ``SfuCallClient.on_remote_track`` 콜백에서 호출된다. VideoRenderer 시작은
        실행 중 event loop 가 없으면 (headless 등) 조용히 skip 하고 타일만 둔다.
        """
        if producer_id in self._tiles:
            # 동일 producer 재수신 — 기존 타일 정리 후 교체
            self.remove_producer(producer_id)

        label = QLabel(producer_id)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(240, 180)
        label.setStyleSheet("background:#1e1e1e;color:#aaa;border-radius:8px;")

        renderer = None
        try:
            from app.ui._video_renderer import VideoRenderer

            renderer = VideoRenderer(label, track)
            renderer.start()
        except Exception as exc:  # noqa: BLE001
            # event loop 부재(headless)·track 무효 시 타일만 유지
            log.warning("[GroupCallDialog] VideoRenderer 시작 skip producer=%s — %r", producer_id, exc)

        self._tiles[producer_id] = (label, renderer)
        self._relayout()

    def remove_producer(self, producer_id: str) -> None:
        """producer 이탈 시 타일 + VideoRenderer 를 정리한다."""
        tile = self._tiles.pop(producer_id, None)
        if tile is None:
            return
        label, renderer = tile
        if renderer is not None:
            try:
                renderer.stop()
            except Exception as exc:  # noqa: BLE001
                log.warning("[GroupCallDialog] VideoRenderer 정지 실패 — %r", exc)
        self._grid.removeWidget(label)
        label.deleteLater()
        self._relayout()

    def _relayout(self) -> None:
        """타일을 정사각형에 가까운 그리드로 재배치한다 (cols = ceil(sqrt(n)))."""
        count = len(self._tiles)
        if count == 0:
            return
        cols = max(1, math.ceil(math.sqrt(count)))
        for index, (label, _renderer) in enumerate(self._tiles.values()):
            row, col = divmod(index, cols)
            self._grid.addWidget(label, row, col)

    def close_all(self) -> None:
        """모든 타일 + VideoRenderer 정리 (통화 종료)."""
        for producer_id in list(self._tiles.keys()):
            self.remove_producer(producer_id)

    def closeEvent(self, event: Any) -> None:  # noqa: N802 — Qt override
        """다이얼로그 닫힘 시 전 VideoRenderer 정리."""
        self.close_all()
        super().closeEvent(event)
