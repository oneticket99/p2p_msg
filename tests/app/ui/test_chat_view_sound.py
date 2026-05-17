# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.ui.chat_view`` 의 ``should_play_on_message`` 트리거 판정 테스트.

ChatView 자체는 PyQt6 ``QScrollArea`` 의무로 QApplication 부재 환경의
unit test 직접 인스턴스화 불가. 본 테스트는 trigger 판정 logic 만
module-level helper 로 검증한다.

ChatView 의 실 호출 흐름은 manual smoke (GUI thread + 실 sound 재생).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.ui.chat_view import should_play_on_message


class TestShouldPlayOnMessage:
    def test_peer_with_enabled_player(self) -> None:
        """peer 발신 + enabled player = True."""

        player = MagicMock()
        player.enabled = True
        assert should_play_on_message(is_self=False, sound_player=player) is True

    def test_self_with_enabled_player(self) -> None:
        """self 발신 = 즉시 False (sound noise 회피)."""

        player = MagicMock()
        player.enabled = True
        assert should_play_on_message(is_self=True, sound_player=player) is False

    def test_peer_with_disabled_player(self) -> None:
        """음소거 상태 player = False."""

        player = MagicMock()
        player.enabled = False
        assert should_play_on_message(is_self=False, sound_player=player) is False

    def test_peer_with_none_player(self) -> None:
        """player 미설정 = False (graceful 폴백)."""

        assert should_play_on_message(is_self=False, sound_player=None) is False

    def test_self_with_none_player(self) -> None:
        """self 발신 + player 미설정 = 이중 False."""

        assert should_play_on_message(is_self=True, sound_player=None) is False

    def test_priority_self_over_player_state(self) -> None:
        """self 발신 우선순위 = player 상태 무관 False."""

        player = MagicMock()
        player.enabled = True
        # is_self=True → player.enabled 검사 자체 도달 불가 (short-circuit)
        result = should_play_on_message(is_self=True, sound_player=player)
        assert result is False


class TestSoundPlayerIntegration:
    """trigger 결과의 SoundPlayer.play_signature() 호출 검증.

    실 ChatView 의 add_message 안의 호출 패턴 등가 시뮬레이션.
    """

    def test_trigger_invokes_play(self) -> None:
        """trigger True = play_signature() 호출 1회."""

        player = MagicMock()
        player.enabled = True
        if should_play_on_message(is_self=False, sound_player=player):
            player.play_signature()
        player.play_signature.assert_called_once()

    def test_no_trigger_no_invoke(self) -> None:
        """trigger False = play_signature() 미호출."""

        player = MagicMock()
        player.enabled = True
        if should_play_on_message(is_self=True, sound_player=player):
            player.play_signature()
        player.play_signature.assert_not_called()

    def test_disabled_player_no_invoke(self) -> None:
        """음소거 player = play_signature() 미호출."""

        player = MagicMock()
        player.enabled = False
        if should_play_on_message(is_self=False, sound_player=player):
            player.play_signature()
        player.play_signature.assert_not_called()
