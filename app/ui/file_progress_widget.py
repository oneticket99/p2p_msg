"""FileProgressWidget — 송신/수신 양방향 ProgressBar 위젯.

본 위젯은 1 개 파일 전송의 진행률을 시각화한다. ``role`` 인자에 따라 두
모드로 동작한다:

- ``role='send'`` (송신자 시점)
    - 회색 막대 = 송신 큐에 넣은 누적 바이트 (``progress_sent``)
    - 파란 막대 = 수신자가 ACK 한 누적 바이트 (``progress_acked``)
    - 회색 위에 파란이 따라가는 2-stack 표현 — 큐 깊이를 한눈에 확인

- ``role='recv'`` (수신자 시점)
    - 파란 막대 = 디스크에 누적 기록된 바이트 (``progress``)

레이아웃:

```
+------------------------------------------------------+
| 📄 filename.ext                    1.2/3.4 MB · 35% |
|  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░         |
|  ←─ acked ─→←── 송신 큐 in-flight ──→               |
| 상태: 전송 중 / 완료 / 실패                          |
+------------------------------------------------------+
```

``chat_view.add_message`` 와의 결합:

본 위젯은 ``QWidget`` 상속이므로 ``ChatView._messages_layout.insertWidget``
에 그대로 삽입 가능하다. ``MessageBubble`` 자리에 본 위젯을 끼워 넣는
어댑터 함수는 Task #16 (메인 윈도우 통합) 에서 추가한다.
"""

from __future__ import annotations

import logging
from typing import Final, Optional

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)


# 역할 식별자 — 외부에서도 사용
ROLE_SEND: Final[str] = "send"
ROLE_RECV: Final[str] = "recv"
_VALID_ROLES: Final[frozenset[str]] = frozenset({ROLE_SEND, ROLE_RECV})


# QProgressBar 해상도 — 0~PROGRESS_RESOLUTION 범위로 정규화 후 표시
# (바이트 수 자체를 그대로 넣으면 int32 overflow 위험 — 100K 분해능 사용)
_PROGRESS_RESOLUTION: Final[int] = 100_000


# 색상 — 회색(송신 큐), 파란(상대 확인 / 수신 완료)
_COLOR_QUEUED = "#9CA3AF"   # 회색 (Tailwind gray-400)
_COLOR_ACKED = "#3B82F6"    # 파랑 (Tailwind blue-500)
_COLOR_RECV = "#3B82F6"     # 동일 파랑 (수신자 시점)
_COLOR_TRACK = "#E5E7EB"    # 트랙 배경 (Tailwind gray-200)
_COLOR_ERROR = "#EF4444"    # 실패 (Tailwind red-500)


class FileProgressWidget(QWidget):
    """파일 전송 1건의 진행률 표시 위젯.

    Parameters
    ----------
    file_id : str
        ``FileSender`` / ``FileReceiver`` 의 file_id 와 일치해야 슬롯이 매칭.
    name : str
        표시용 파일명.
    size : int
        파일 전체 바이트 수 — 진행률 계산 기준.
    role : str
        ``'send'`` 또는 ``'recv'``. 잘못된 값은 ``ValueError``.

    Notes
    -----
    - 본 위젯의 슬롯(``on_sent`` / ``on_acked`` / ``on_recv``) 은 매 파일별
      file_id 가 일치하는 경우에만 막대를 갱신한다 — 다중 위젯이 동일
      signal 에 결선돼도 서로 간섭하지 않도록 보호.
    """

    def __init__(
        self,
        file_id: str,
        name: str,
        size: int,
        role: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        if role not in _VALID_ROLES:
            raise ValueError(
                f"role 은 {sorted(_VALID_ROLES)} 중 하나여야 합니다 — got={role!r}"
            )
        if size <= 0:
            raise ValueError(f"size 는 양수여야 합니다 — got={size}")

        self._file_id: str = file_id
        self._name: str = name
        self._size: int = int(size)
        self._role: str = role

        # 진행 상태 (바이트)
        self._sent_bytes: int = 0   # role='send' 에서만 의미
        self._acked_bytes: int = 0  # role='send' 에서만 의미
        self._recv_bytes: int = 0   # role='recv' 에서만 의미

        # 레이아웃 — 헤더(파일명 + 크기/퍼센트) + ProgressBar + 상태
        self._build_layout()
        self._refresh_text()

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    # ------------------------------------------------------------------
    # 외부 진입점 — Qt slot 으로 연결 가능
    # ------------------------------------------------------------------

    @property
    def file_id(self) -> str:
        """본 위젯이 추적 중인 file_id."""

        return self._file_id

    @pyqtSlot(str, int, int)
    def on_sent(self, file_id: str, sent: int, total: int) -> None:
        """``FileSender.progress_sent`` 슬롯 — 회색(송신 큐) 막대 갱신.

        file_id 가 본 위젯과 다르면 무시. ``total`` 은 생성자 ``size`` 와
        동일해야 하나 누적 일관성을 위해 갱신 시점에 다시 받는다.
        """

        if file_id != self._file_id or self._role != ROLE_SEND:
            return
        self._sent_bytes = max(0, min(int(sent), int(total)))
        self._update_send_bars()
        self._refresh_text()

    @pyqtSlot(str, int, int)
    def on_acked(self, file_id: str, acked: int, total: int) -> None:
        """``FileSender.progress_acked`` 슬롯 — 파란(상대 확인) 막대 갱신."""

        if file_id != self._file_id or self._role != ROLE_SEND:
            return
        self._acked_bytes = max(0, min(int(acked), int(total)))
        self._update_send_bars()
        self._refresh_text()

    @pyqtSlot(str, int, int)
    def on_recv(self, file_id: str, received: int, total: int) -> None:
        """``FileReceiver.progress`` 슬롯 — 파란(수신) 막대 갱신."""

        if file_id != self._file_id or self._role != ROLE_RECV:
            return
        self._recv_bytes = max(0, min(int(received), int(total)))
        # 단일 막대 갱신
        self._recv_bar.setValue(self._scaled(self._recv_bytes))
        self._refresh_text()

    @pyqtSlot(str, bool)
    def on_completed(self, file_id: str, success: bool) -> None:
        """``FileSender.completed`` / ``FileReceiver`` 완료 신호 슬롯.

        상태 라벨을 "완료" 또는 "실패" 로 갱신한다. file_id 가 다르면 무시.
        """

        if file_id != self._file_id:
            return
        if success:
            self._status_label.setText("완료")
            self._status_label.setStyleSheet(f"color: {_COLOR_ACKED}; font-weight: bold;")
            if self._role == ROLE_SEND:
                # 완료 시 acked 막대를 100% 로 고정
                self._acked_bytes = self._size
                self._update_send_bars()
        else:
            self._status_label.setText("실패")
            self._status_label.setStyleSheet(f"color: {_COLOR_ERROR}; font-weight: bold;")
        self._refresh_text()

    @pyqtSlot(str, str)
    def on_error(self, file_id: str, message: str) -> None:
        """``FileSender.error`` / ``FileReceiver.error`` 슬롯 — 상태 라벨 갱신."""

        if file_id != self._file_id:
            return
        log.warning(
            "[FileProgressWidget] 오류 — file_id=%s msg=%s", file_id, message
        )
        self._status_label.setText(f"실패: {message}")
        self._status_label.setStyleSheet(f"color: {_COLOR_ERROR}; font-weight: bold;")

    # ------------------------------------------------------------------
    # 레이아웃 빌더
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        """위젯 트리 구성 — 헤더 / ProgressBar / 상태."""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(4)

        # ---- 헤더: 아이콘 + 파일명 + (크기/퍼센트 라벨) ----
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        icon_text = "📤" if self._role == ROLE_SEND else "📥"
        icon_label = QLabel(icon_text, self)
        icon_label.setFixedWidth(20)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._name_label = QLabel(self._name, self)
        self._name_label.setToolTip(self._name)
        self._name_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._name_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        self._size_label = QLabel("", self)
        self._size_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        header_row.addWidget(icon_label)
        header_row.addWidget(self._name_label, stretch=1)
        header_row.addWidget(self._size_label)
        outer.addLayout(header_row)

        # ---- ProgressBar 영역 ----
        if self._role == ROLE_SEND:
            # 2-stack: 회색 막대 위에 파란 막대를 겹쳐 그린다.
            # QStackedLayout 으로 동일 영역에 두 QProgressBar 를 겹친다.
            stack_container = QWidget(self)
            self._stack_layout = QStackedLayout(stack_container)
            self._stack_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
            self._stack_layout.setContentsMargins(0, 0, 0, 0)

            # 회색 막대 — 아래 layer
            self._queued_bar = self._make_progress_bar(_COLOR_QUEUED)
            # 파란 막대 — 위 layer
            self._acked_bar = self._make_progress_bar(_COLOR_ACKED)

            self._stack_layout.addWidget(self._queued_bar)
            self._stack_layout.addWidget(self._acked_bar)

            outer.addWidget(stack_container)
        else:
            # 수신 — 단일 파란 막대
            self._recv_bar = self._make_progress_bar(_COLOR_RECV)
            outer.addWidget(self._recv_bar)

        # ---- 상태 라벨 ----
        initial_status = "전송 중" if self._role == ROLE_SEND else "수신 중"
        self._status_label = QLabel(initial_status, self)
        self._status_label.setStyleSheet("color: #6B7280;")  # gray-500
        outer.addWidget(self._status_label)

    def _make_progress_bar(self, fill_color: str) -> QProgressBar:
        """공통 스타일 ``QProgressBar`` 인스턴스 생성.

        스타일시트로 chunk 색상과 트랙 배경을 조정. 텍스트는 부모 위젯의
        size_label 이 표기하므로 본 막대는 텍스트를 숨긴다.
        """

        bar = QProgressBar(self)
        bar.setRange(0, _PROGRESS_RESOLUTION)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {_COLOR_TRACK};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {fill_color};
                border-radius: 4px;
            }}
            """
        )
        # 팔레트 폴백 (스타일시트 미적용 환경)
        palette = bar.palette()
        palette.setColor(QPalette.ColorRole.Highlight, QColor(fill_color))
        palette.setColor(QPalette.ColorRole.Base, QColor(_COLOR_TRACK))
        bar.setPalette(palette)
        return bar

    # ------------------------------------------------------------------
    # 갱신 헬퍼
    # ------------------------------------------------------------------

    def _update_send_bars(self) -> None:
        """송신자 시점 — 두 막대(회색/파란) 동시 갱신."""

        self._queued_bar.setValue(self._scaled(self._sent_bytes))
        self._acked_bar.setValue(self._scaled(self._acked_bytes))

    def _scaled(self, value: int) -> int:
        """바이트 → 0~_PROGRESS_RESOLUTION 정규화."""

        if self._size <= 0:
            return 0
        ratio = max(0.0, min(1.0, value / self._size))
        return int(round(ratio * _PROGRESS_RESOLUTION))

    def _refresh_text(self) -> None:
        """상단 우측 ``size_label`` 갱신 — "x/y · z%" 형식."""

        if self._role == ROLE_SEND:
            primary = self._acked_bytes if self._acked_bytes > 0 else self._sent_bytes
        else:
            primary = self._recv_bytes

        percent = 0
        if self._size > 0:
            percent = int(round((primary / self._size) * 100))
        text = (
            f"{self._humanize(primary)} / {self._humanize(self._size)} · {percent}%"
        )
        self._size_label.setText(text)

    # ------------------------------------------------------------------
    # 정적 헬퍼 — 바이트 사람 친화 표기
    # ------------------------------------------------------------------

    @staticmethod
    def _humanize(n: int) -> str:
        """바이트 수를 KB/MB/GB 단위로 표기.

        1024 진수 사용 (전통적 메모리/파일 크기 표기).
        """

        n = max(0, int(n))
        if n < 1024:
            return f"{n} B"
        units = ["KB", "MB", "GB", "TB"]
        size = float(n) / 1024.0
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                # 소수 1자리 — KB 단위에서도 가독성 위해 동일 포맷
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
