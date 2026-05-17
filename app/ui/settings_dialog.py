# SPDX-License-Identifier: GPL-3.0-or-later
"""설정 다이얼로그 — 사용자 환경 control 통합 UI.

Phase 2 사이클 40 진입 — 사이클 38~39 의 signature sound layer follow-up.
음소거 toggle + 볼륨 slider 0~100 → ``SoundPlayer.set_enabled`` /
``set_volume`` 즉시 반영. 추후 Phase 2~3 의 다른 설정 (테마 / 알림 /
백업 주기) 의 동일 dialog 의 section 으로 누적 의무.

설계 결정
---------
- ``SettingsState`` dataclass 분리 = GUI 부재 환경 의 logic 검증 가능
  (Mock player 주입 + helper 함수 의 unit test).
- 볼륨 UI = 0~100 정수 slider (Qt 표준), logic 의 0.0~1.0 float 변환은
  helper ``percent_to_volume`` / ``volume_to_percent`` 의 분리.
- ``apply_to_player`` = SettingsState → SoundPlayer 매핑 의무. dialog
  accept() 시 1회 호출 + 즉시 player 상태 반영.
- 영속 저장 = Phase 3 의 user_settings table 의 의무 (본 cycle 의 의무
  외 — env-only 폴백, dialog close 시 메모리 상태만 유지).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QFormLayout,
        QLabel,
        QSlider,
        QVBoxLayout,
        QWidget,
    )
    from PyQt6.QtCore import Qt
    _QT_AVAILABLE = True
except ImportError:  # pragma: no cover - PyQt6 미설치 환경 폴백
    QCheckBox = None  # type: ignore[assignment, misc]
    QDialog = object  # type: ignore[assignment, misc]
    QDialogButtonBox = None  # type: ignore[assignment, misc]
    QFormLayout = None  # type: ignore[assignment, misc]
    QLabel = None  # type: ignore[assignment, misc]
    QSlider = None  # type: ignore[assignment, misc]
    QVBoxLayout = None  # type: ignore[assignment, misc]
    QWidget = None  # type: ignore[assignment, misc]
    Qt = None  # type: ignore[assignment, misc]
    _QT_AVAILABLE = False

from app.ui.sound_player import SoundPlayer, _clamp_volume

log = logging.getLogger(__name__)


@dataclass
class SettingsState:
    """다이얼로그 의 사용자 입력 스냅샷.

    Attributes
    ----------
    sound_enabled : bool
        시그니처 사운드 활성 여부.
    sound_volume : float
        0.0~1.0 범위. 본 dataclass 의무 단 GUI 의 0~100 integer 의
        ``percent_to_volume`` 변환 후 보관.
    """

    sound_enabled: bool
    sound_volume: float

    def __post_init__(self) -> None:
        """볼륨 범위 clamp — 외부 dirty input 방어."""

        self.sound_volume = _clamp_volume(self.sound_volume)


def percent_to_volume(percent: int) -> float:
    """0~100 정수 percent → 0.0~1.0 float 변환 + clamp.

    Parameters
    ----------
    percent : int
        slider 위젯 출력 정수 (0~100). 범위 외 = clamp.

    Returns
    -------
    float
        0.0~1.0 범위 float.
    """

    if percent < 0:
        return 0.0
    if percent > 100:
        return 1.0
    return percent / 100.0


def volume_to_percent(volume: float) -> int:
    """0.0~1.0 float → 0~100 정수 percent 변환 + clamp + round.

    Parameters
    ----------
    volume : float
        0.0~1.0 범위 float.

    Returns
    -------
    int
        반올림된 0~100 정수.
    """

    clamped = _clamp_volume(volume)
    return round(clamped * 100)


def apply_to_player(state: SettingsState, player: Optional[SoundPlayer]) -> bool:
    """``SettingsState`` 의 값을 ``SoundPlayer`` 에 적용.

    Parameters
    ----------
    state : SettingsState
        다이얼로그 의 의 입력 스냅샷.
    player : SoundPlayer | None
        반영 대상. None = no-op (graceful 폴백).

    Returns
    -------
    bool
        실 반영 = True, player 부재 = False.
    """

    if player is None:
        log.debug("SoundPlayer 부재 — apply_to_player skip")
        return False
    player.set_enabled(state.sound_enabled)
    player.set_volume(state.sound_volume)
    return True


def build_state_from_player(player: Optional[SoundPlayer]) -> SettingsState:
    """``SoundPlayer`` 현재 상태 → ``SettingsState`` 초기값.

    player None = 기본값 (enabled=True, volume=0.7) 폴백.
    """

    if player is None:
        return SettingsState(sound_enabled=True, sound_volume=0.7)
    return SettingsState(
        sound_enabled=player.enabled,
        sound_volume=player.volume,
    )


class SettingsDialog(QDialog):  # type: ignore[misc, valid-type]
    """사용자 설정 다이얼로그 (PyQt6 GUI).

    Phase 2 사이클 40 = sound section 만 노출. 추후 cycle 의 테마/알림/
    백업 등 section 의 누적 의무.

    초기값 = ``build_state_from_player`` 로 ``SoundPlayer`` 현재 상태 반영.
    accept() = ``apply_to_player`` 호출 + dialog close.
    """

    def __init__(
        self,
        sound_player: Optional[SoundPlayer] = None,
        parent: Optional["QWidget"] = None,
    ) -> None:
        if not _QT_AVAILABLE:
            raise RuntimeError("PyQt6 부재 — SettingsDialog 생성 불가")
        super().__init__(parent)
        self._sound_player = sound_player
        self.setWindowTitle("TooTalk 설정")
        self.setMinimumWidth(360)

        initial = build_state_from_player(sound_player)

        layout = QVBoxLayout(self)

        # 사운드 section
        sound_label = QLabel("<b>시그니처 사운드</b>")
        layout.addWidget(sound_label)

        form = QFormLayout()

        self._enabled_check = QCheckBox("메시지 수신 시 재생")
        self._enabled_check.setChecked(initial.sound_enabled)
        form.addRow("활성", self._enabled_check)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(volume_to_percent(initial.sound_volume))
        self._volume_slider.setTickInterval(10)
        self._volume_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        form.addRow("볼륨 (0~100)", self._volume_slider)

        layout.addLayout(form)

        # OK / 취소 버튼
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)  # type: ignore[arg-type]
        buttons.rejected.connect(self.reject)  # type: ignore[arg-type]
        layout.addWidget(buttons)

    def current_state(self) -> SettingsState:
        """현재 위젯 값 → ``SettingsState`` 스냅샷."""

        return SettingsState(
            sound_enabled=self._enabled_check.isChecked(),
            sound_volume=percent_to_volume(self._volume_slider.value()),
        )

    def _on_accept(self) -> None:
        """OK 클릭 = state 적용 + dialog close."""

        state = self.current_state()
        apply_to_player(state, self._sound_player)
        self.accept()
