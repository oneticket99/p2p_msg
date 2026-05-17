# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.ui.sound_player`` 단위 테스트.

PyQt6 ``QSoundEffect`` 실 재생은 GUI thread + event loop 의무이므로
본 unit test 는 wrapper logic 만 검증한다 — path 해석 + 음소거 토글 +
볼륨 clamp + Config 연동.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.config import load_config
from app.ui import sound_player as sp_mod
from app.ui.sound_player import SoundPlayer, _clamp_volume, resolve_sound_path


@pytest.fixture
def base_config():
    """저장소 루트의 실 WAV path 의 의 Config 반환."""

    return load_config()


class TestClampVolume:
    def test_normal_range(self) -> None:
        assert _clamp_volume(0.5) == 0.5

    def test_below_zero(self) -> None:
        assert _clamp_volume(-0.3) == 0.0

    def test_above_one(self) -> None:
        assert _clamp_volume(1.5) == 1.0

    def test_boundary_zero(self) -> None:
        assert _clamp_volume(0.0) == 0.0

    def test_boundary_one(self) -> None:
        assert _clamp_volume(1.0) == 1.0


class TestResolveSoundPath:
    def test_relative_path_with_root(self, base_config, tmp_path: Path) -> None:
        path = resolve_sound_path(base_config, repo_root=tmp_path)
        assert path.is_absolute()
        assert path.name == "signature.wav"
        assert str(tmp_path) in str(path)

    def test_absolute_path_pass_through(self, base_config, tmp_path: Path) -> None:
        abs_path = tmp_path / "custom.wav"
        config = replace(base_config, sound_signature_path=str(abs_path))
        path = resolve_sound_path(config)
        assert path == abs_path


class TestSoundPlayer:
    def test_init_with_enabled_config(self, base_config) -> None:
        player = SoundPlayer(base_config)
        assert player.enabled is True
        assert 0.0 <= player.volume <= 1.0
        assert player.sound_path.name == "signature.wav"

    def test_init_with_disabled_config(self, base_config) -> None:
        config = replace(base_config, sound_enabled=False)
        player = SoundPlayer(config)
        assert player.enabled is False

    def test_volume_clamp_from_config(self, base_config) -> None:
        config = replace(base_config, sound_volume=2.5)
        player = SoundPlayer(config)
        assert player.volume == 1.0

        config2 = replace(base_config, sound_volume=-0.5)
        player2 = SoundPlayer(config2)
        assert player2.volume == 0.0

    def test_set_enabled_toggle(self, base_config) -> None:
        player = SoundPlayer(base_config)
        player.set_enabled(False)
        assert player.enabled is False
        player.set_enabled(True)
        assert player.enabled is True

    def test_set_volume_clamp(self, base_config) -> None:
        player = SoundPlayer(base_config)
        player.set_volume(0.3)
        assert player.volume == 0.3
        player.set_volume(2.0)
        assert player.volume == 1.0
        player.set_volume(-1.0)
        assert player.volume == 0.0

    def test_play_skip_when_disabled(self, base_config, monkeypatch) -> None:
        """음소거 상태 = play_signature() False 반환 + effect.play() 미호출."""

        config = replace(base_config, sound_enabled=False)
        player = SoundPlayer(config)
        # effect 가 존재해도 disabled 상태면 play() 미호출
        mock_effect = MagicMock()
        player._effect = mock_effect
        result = player.play_signature()
        assert result is False
        mock_effect.play.assert_not_called()

    def test_play_skip_when_qt_unavailable(self, base_config, monkeypatch) -> None:
        """Qt 부재 환경 = play_signature() False 반환."""

        monkeypatch.setattr(sp_mod, "_QT_AVAILABLE", False)
        player = SoundPlayer(base_config)
        result = player.play_signature()
        assert result is False

    def test_play_skip_when_effect_none(self, base_config) -> None:
        """파일 부재로 effect 미초기화 시 play_signature() False."""

        player = SoundPlayer(base_config)
        player._effect = None
        result = player.play_signature()
        # Qt 부재 = False, 존재 + effect=None 도 False
        assert result is False

    def test_play_invokes_effect_when_enabled(
        self, base_config, monkeypatch
    ) -> None:
        """enabled + Qt + effect 보유 = play() 호출 + True 반환."""

        monkeypatch.setattr(sp_mod, "_QT_AVAILABLE", True)
        player = SoundPlayer(base_config)
        mock_effect = MagicMock()
        player._effect = mock_effect
        result = player.play_signature()
        assert result is True
        mock_effect.play.assert_called_once()

    def test_set_volume_propagates_to_effect(self, base_config) -> None:
        """set_volume() = effect.setVolume() 동기 호출."""

        player = SoundPlayer(base_config)
        mock_effect = MagicMock()
        player._effect = mock_effect
        player.set_volume(0.42)
        mock_effect.setVolume.assert_called_once_with(0.42)

    def test_is_qt_available_classmethod(self) -> None:
        """static method 동작 확인 — 실행 환경 dependent."""

        result = SoundPlayer.is_qt_available()
        assert isinstance(result, bool)

    def test_missing_file_no_effect(self, base_config, tmp_path: Path) -> None:
        """파일 부재 시 effect None + 경고 로그만."""

        config = replace(
            base_config, sound_signature_path=str(tmp_path / "nonexistent.wav")
        )
        player = SoundPlayer(config)
        assert player._effect is None
