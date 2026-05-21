# SPDX-License-Identifier: GPL-3.0-or-later
"""CallDialog — 음성 / 영상 통화 modal (cycle 169.56 신설).

WebRTC SDP offer/answer + audio/video constraint scaffolding.
actual ICE + media stream binding = 별도 cycle 의무.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui._icons import load_icon, load_pixmap


class CallDialog(QDialog):
    """음성/영상 통화 modal — accept + end + mute + video toggle.

    Parameters
    ----------
    peer_name : str
        상대 사용자명 / 닉네임.
    video_enabled : bool
        영상 통화 시 True. False = 음성 only.
    incoming : bool
        수신 통화 시 True (수락/거절 button). 발신 시 False (취소 button only).
    """

    accepted_signal = pyqtSignal()
    ended_signal = pyqtSignal()
    mute_toggled = pyqtSignal(bool)
    video_toggled = pyqtSignal(bool)

    def __init__(
        self,
        peer_name: str,
        video_enabled: bool = False,
        incoming: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"TooTalk · {'영상' if video_enabled else '음성'} 통화")
        self.setModal(True)
        # cycle 169.327 — telegram align frameless + main center (사용자 directive image #91)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 600)
        self._peer_name = peer_name
        self._video_enabled = video_enabled
        self._incoming = incoming
        self._muted = False
        self._duration_seconds = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # 한글 주석 — cycle 169.58 회수 — video frame area (영상 통화 시 visible)
        self._video_frame = QLabel()
        self._video_frame.setFixedSize(360, 200)
        self._video_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._video_frame.setText("영상 부재" if not video_enabled else "영상 수신 대기…")
        self._video_frame.setStyleSheet(
            "background-color: #000000; color: #6b7280;"
            " border-radius: 8px; font-size: 12px;"
        )
        self._video_frame.setVisible(video_enabled)
        outer.addWidget(self._video_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # 한글 주석 — cycle 169.328 chat_list entry 등가 avatar (사용자 directive image #92)
        # palette_solid + initials chain (kind="saved" 시점 data icon 분기)
        self._avatar_widget = QLabel()
        self._avatar_widget.setFixedSize(160, 160)
        self._avatar_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if peer_name == "저장한 메시지":
            from PyQt6.QtGui import QPainter, QColor, QPixmap
            pix = QPixmap(160, 160)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor("#0066FF"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, 160, 160)
            icon_pix = load_pixmap("data", size=80, color="#ffffff")
            painter.drawPixmap(40, 40, icon_pix)
            painter.end()
            self._avatar_widget.setPixmap(pix)
        else:
            from app.ui._avatar_helper import make_initial_pixmap
            self._avatar_widget.setPixmap(make_initial_pixmap(peer_name or "?", size=160))
        outer.addWidget(self._avatar_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # 한글 주석 — peer 사용자명
        name_label = QLabel(peer_name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("color: #e5e7eb; font-size: 22px; font-weight: 700;")
        outer.addWidget(name_label)

        # 한글 주석 — 통화 status + duration
        self._status_label = QLabel("수신 통화…" if incoming else "발신 통화…")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #22D3EE; font-size: 14px;")
        outer.addWidget(self._status_label)

        outer.addStretch(1)

        # 한글 주석 — 중앙 control row (mute + video toggle)
        control_row = QHBoxLayout()
        control_row.setSpacing(20)
        control_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._mute_btn = self._build_circle_button("mic", "음소거 toggle")
        self._mute_btn.setCheckable(True)
        self._mute_btn.toggled.connect(self._on_mute_toggle)  # type: ignore[arg-type]
        control_row.addWidget(self._mute_btn)

        self._video_btn = self._build_circle_button("avatar", "영상 toggle")
        self._video_btn.setCheckable(True)
        self._video_btn.setChecked(video_enabled)
        self._video_btn.toggled.connect(self._on_video_toggle)  # type: ignore[arg-type]
        control_row.addWidget(self._video_btn)

        outer.addLayout(control_row)

        # 한글 주석 — 하단 action row (수락 + 거절 / 종료)
        action_row = QHBoxLayout()
        action_row.setSpacing(16)
        action_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if incoming:
            accept_btn = QPushButton("수락")
            accept_btn.setFixedSize(120, 48)
            accept_btn.setStyleSheet(
                "QPushButton {"
                " background-color: #16a34a;"
                " color: white;"
                " border: none;"
                " border-radius: 24px;"
                " font-size: 15px;"
                " font-weight: 600;"
                "}"
                " QPushButton:hover { background-color: #15803d; }"
            )
            accept_btn.clicked.connect(self._on_accept)  # type: ignore[arg-type]
            action_row.addWidget(accept_btn)

        end_btn = QPushButton("종료" if not incoming else "거절")
        end_btn.setFixedSize(120, 48)
        end_btn.setStyleSheet(
            "QPushButton {"
            " background-color: #dc2626;"
            " color: white;"
            " border: none;"
            " border-radius: 24px;"
            " font-size: 15px;"
            " font-weight: 600;"
            "}"
            " QPushButton:hover { background-color: #b91c1c; }"
        )
        end_btn.clicked.connect(self._on_end)  # type: ignore[arg-type]
        action_row.addWidget(end_btn)

        outer.addLayout(action_row)

        # 한글 주석 — duration timer (1초 tick)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)  # type: ignore[arg-type]

        # 한글 주석 — cycle 169.91 — 통화 사운드 player (incoming=ringtone / outgoing=ringback loop)
        try:
            from app.sound.ringtone import CallSoundPlayer
            self._sound = CallSoundPlayer(volume=0.6)
            initial_key = "ringtone" if incoming else "ringback"
            self._sound.play_loop(initial_key)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("[CallDialog] sound player init fail — %r", exc)
            self._sound = None

    def _build_circle_button(self, icon_name: str, tooltip: str) -> QPushButton:
        """원형 control button (mute + video toggle)."""
        btn = QPushButton()
        btn.setFixedSize(56, 56)
        btn.setIcon(load_icon(icon_name, size=24, color="#e5e7eb"))
        btn.setIconSize(QSize(24, 24))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        btn.setStyleSheet(
            "QPushButton {"
            " background-color: #1F2937;"
            " border: none;"
            " border-radius: 28px;"
            "}"
            " QPushButton:hover { background-color: #374151; }"
            " QPushButton:checked { background-color: #0066FF; }"
        )
        return btn

    def attach_client(self, call_client) -> None:  # type: ignore[no-untyped-def]
        """CallClient attach — accept/end/mute/video signal 의 binding chain.

        cycle 169.59 회수 — video track 수신 시 VideoRenderer 자동 start.
        """
        self._client = call_client
        self.accepted_signal.connect(lambda: self._handle_accept_with_client())  # type: ignore[arg-type]
        self.ended_signal.connect(lambda: self._handle_end_with_client())  # type: ignore[arg-type]
        self.mute_toggled.connect(call_client.toggle_mute)  # type: ignore[arg-type]
        self.video_toggled.connect(call_client.toggle_video)  # type: ignore[arg-type]

        # 한글 주석 — cycle 169.59 회수 — remote video track 수신 시 VideoRenderer start
        original_on_state = call_client._on_state_change

        def _wrapped_state(state: str) -> None:
            self._maybe_start_video_renderer()
            if original_on_state is not None:
                original_on_state(state)
        call_client._on_state_change = _wrapped_state

    def _maybe_start_video_renderer(self) -> None:
        """CallClient remote_track 의 video 시 VideoRenderer start."""
        client = getattr(self, "_client", None)
        if client is None or client._remote_track is None:
            return
        track = client._remote_track
        if getattr(track, "kind", "") != "video":
            return
        if hasattr(self, "_video_renderer"):
            return
        try:
            from app.ui._video_renderer import VideoRenderer
            self._video_renderer = VideoRenderer(self._video_frame, track)
            self._video_renderer.start()
            self._video_frame.setVisible(True)
            self._avatar_widget.setVisible(False)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("[CallDialog] VideoRenderer start fail — %r", exc)

    def _handle_accept_with_client(self) -> None:
        """accept 직후 client offer/answer fire — 별도 cycle binding chain."""
        # 한글 주석 — actual SDP offer/answer + ICE candidate exchange = signaling chain 별도 cycle
        pass

    def _handle_end_with_client(self) -> None:
        """end 직후 client hangup."""
        client = getattr(self, "_client", None)
        if client is None:
            return
        import asyncio
        try:
            asyncio.ensure_future(client.hangup())
        except Exception:
            pass

    def _on_accept(self) -> None:
        """수신 통화 수락."""
        self._status_label.setText("연결됨")
        self._timer.start()
        # 한글 주석 — cycle 169.91 — ring loop stop + connect tone 1회
        if getattr(self, "_sound", None) is not None:
            self._sound.stop_loop()
            self._sound.play_once("connect")
        self.accepted_signal.emit()

    def _on_end(self) -> None:
        """종료 / 거절 — cycle 169.336 end wav play 後 dialog close (사용자 directive 08_call_ended_soft.wav)."""
        self._timer.stop()
        # 한글 주석 — ring loop stop + end tone 1회 + 1.5s delay 後 reject (wav destroy 회피)
        if getattr(self, "_sound", None) is not None:
            self._sound.stop_loop()
            self._sound.play_once("end")
        self.ended_signal.emit()
        QTimer.singleShot(1500, self.reject)

    def _on_mute_toggle(self, checked: bool) -> None:
        """음소거 toggle."""
        self._muted = checked
        self.mute_toggled.emit(checked)

    def _on_video_toggle(self, checked: bool) -> None:
        """영상 toggle — video frame visible 동기."""
        self._video_enabled = checked
        self._video_frame.setVisible(checked)
        self._avatar_widget.setVisible(not checked)
        if checked:
            self._video_frame.setText("영상 수신 대기…")
        self.video_toggled.emit(checked)

    def _on_tick(self) -> None:
        """1초 tick — duration 갱신."""
        self._duration_seconds += 1
        m, s = divmod(self._duration_seconds, 60)
        self._status_label.setText(f"{m:02d}:{s:02d}")
