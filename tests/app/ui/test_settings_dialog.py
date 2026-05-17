# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.ui.settings_dialog`` 단위 테스트.

``SettingsDialog`` GUI class = PyQt6 ``QDialog`` 의무 단 본 테스트는
helper 함수 + ``SettingsState`` 의 logic 만 검증한다. GUI 실 동작 =
manual smoke 의무.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.ui.settings_dialog import (
    SettingsState,
    apply_to_player,
    build_state_from_player,
    percent_to_volume,
    volume_to_percent,
)


class TestSettingsStateClamp:
    def test_normal_volume(self) -> None:
        state = SettingsState(sound_enabled=True, sound_volume=0.5)
        assert state.sound_volume == 0.5

    def test_below_zero_clamp(self) -> None:
        state = SettingsState(sound_enabled=True, sound_volume=-0.3)
        assert state.sound_volume == 0.0

    def test_above_one_clamp(self) -> None:
        state = SettingsState(sound_enabled=False, sound_volume=2.5)
        assert state.sound_volume == 1.0

    def test_enabled_preserved(self) -> None:
        state = SettingsState(sound_enabled=False, sound_volume=0.7)
        assert state.sound_enabled is False


class TestPercentToVolume:
    def test_zero(self) -> None:
        assert percent_to_volume(0) == 0.0

    def test_hundred(self) -> None:
        assert percent_to_volume(100) == 1.0

    def test_fifty(self) -> None:
        assert percent_to_volume(50) == 0.5

    def test_negative_clamp(self) -> None:
        assert percent_to_volume(-10) == 0.0

    def test_above_hundred_clamp(self) -> None:
        assert percent_to_volume(150) == 1.0


class TestVolumeToPercent:
    def test_zero(self) -> None:
        assert volume_to_percent(0.0) == 0

    def test_one(self) -> None:
        assert volume_to_percent(1.0) == 100

    def test_half(self) -> None:
        assert volume_to_percent(0.5) == 50

    def test_rounding_up(self) -> None:
        # 0.456 * 100 = 45.6 → round 46
        assert volume_to_percent(0.456) == 46

    def test_rounding_down(self) -> None:
        # 0.123 * 100 = 12.3 → round 12
        assert volume_to_percent(0.123) == 12

    def test_clamp_above_one(self) -> None:
        assert volume_to_percent(2.5) == 100

    def test_clamp_below_zero(self) -> None:
        assert volume_to_percent(-0.5) == 0


class TestRoundTripConversion:
    """percent → volume → percent 역변환 정확성."""

    @pytest.mark.parametrize("percent", [0, 10, 25, 50, 75, 100])
    def test_round_trip(self, percent: int) -> None:
        volume = percent_to_volume(percent)
        assert volume_to_percent(volume) == percent


class TestApplyToPlayer:
    def test_none_player_no_op(self) -> None:
        """player None = False 반환 + 호출 없음."""

        state = SettingsState(sound_enabled=True, sound_volume=0.5)
        result = apply_to_player(state, None)
        assert result is False

    def test_player_set_enabled_and_volume(self) -> None:
        """player 보유 = set_enabled + set_volume 각 1회 호출."""

        player = MagicMock()
        state = SettingsState(sound_enabled=False, sound_volume=0.3)
        result = apply_to_player(state, player)
        assert result is True
        player.set_enabled.assert_called_once_with(False)
        player.set_volume.assert_called_once_with(0.3)

    def test_player_enabled_true(self) -> None:
        player = MagicMock()
        state = SettingsState(sound_enabled=True, sound_volume=1.0)
        apply_to_player(state, player)
        player.set_enabled.assert_called_once_with(True)
        player.set_volume.assert_called_once_with(1.0)


class TestBuildStateFromPlayer:
    def test_none_player_default(self) -> None:
        """player None = 기본값 (enabled=True + volume=0.7) 폴백."""

        state = build_state_from_player(None)
        assert state.sound_enabled is True
        assert state.sound_volume == 0.7

    def test_player_state_reflected(self) -> None:
        """player 상태 반영."""

        player = MagicMock()
        player.enabled = False
        player.volume = 0.42
        state = build_state_from_player(player)
        assert state.sound_enabled is False
        assert state.sound_volume == 0.42

    def test_player_volume_clamped(self) -> None:
        """player.volume 비정상 값 = post_init clamp."""

        player = MagicMock()
        player.enabled = True
        player.volume = 1.5
        state = build_state_from_player(player)
        assert state.sound_volume == 1.0
