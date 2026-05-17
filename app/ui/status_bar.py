"""StatusBar — 시그널링 연결 상태 + 동일 방 peer 수 표시.

``QStatusBar`` 를 상속하여 다음 두 영역을 보유한다.

- 좌측 (``addWidget``)         : 연결 상태 (DISCONNECTED / CONNECTING / CONNECTED / ERROR)
- 우측 (``addPermanentWidget``): peer 수 표시 ("peers: N")

연결 상태 문자열은 화이트리스트로 검증하여 의도치 않은 값이 들어오지
않도록 한다.
"""

from __future__ import annotations

from typing import Final, Optional

from PyQt6.QtWidgets import QLabel, QStatusBar, QWidget


# 허용 연결 상태 화이트리스트
_VALID_STATES: Final[frozenset[str]] = frozenset(
    {"DISCONNECTED", "CONNECTING", "CONNECTED", "ERROR"}
)


class StatusBar(QStatusBar):
    """시그널링 연결 상태 + peer 수 표시 StatusBar."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # 좌측 라벨 — 연결 상태
        self._state_label = QLabel("DISCONNECTED", self)
        self._state_label.setStyleSheet("padding-left: 8px;")
        self.addWidget(self._state_label, 1)

        # 우측 라벨 — peer 수
        self._peer_label = QLabel("peers: 0", self)
        self._peer_label.setStyleSheet("padding-right: 8px;")
        self.addPermanentWidget(self._peer_label, 0)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def set_connection_state(self, state: str) -> None:
        """연결 상태 표시 갱신.

        Parameters
        ----------
        state : str
            허용 값: ``DISCONNECTED`` / ``CONNECTING`` / ``CONNECTED`` /
            ``ERROR``. 허용 범위 밖이면 ``ERROR`` 로 강제한다.
        """

        normalized = state if state in _VALID_STATES else "ERROR"
        self._state_label.setText(normalized)

    def set_peer_count(self, count: int) -> None:
        """동일 방 안의 다른 peer 수 표시 갱신 (본인 제외).

        Parameters
        ----------
        count : int
            음수가 들어오면 0 으로 보정.
        """

        safe = max(0, int(count))
        self._peer_label.setText(f"peers: {safe}")
