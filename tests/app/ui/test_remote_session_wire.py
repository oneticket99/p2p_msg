# SPDX-License-Identifier: GPL-3.0-or-later
"""ChatHeaderMixin 원격 세션 accept 결선 mock isolation test — cycle 169.782 (M3c).

Exec Plan M3c — RemoteCallDialog accept → RemoteSessionRunner 기동 결선 검증.
MagicMock self 에 `_start_remote_session` 을 직접 호출(mixin method = DI 등가)하여
MainWindow 21-mixin cumulative QWidget hang 을 회피하고 결선 logic 만 격리 검증한다.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.ui._chat_header_mixin import ChatHeaderMixin
from app.remote.session_runner import RemoteSessionRunner, SessionRole


class TestStartRemoteSession:
    """accept → runner 생성 + 역할 매핑."""

    def test_controller_role(self) -> None:
        # 한글 주석 — 상대 PC 제어 의도 = CONTROLLER
        mock_self = MagicMock()
        mock_self._remote_data_channel = None
        ChatHeaderMixin._start_remote_session(mock_self, "controller", "친구A")
        runner = mock_self._remote_runner
        assert isinstance(runner, RemoteSessionRunner)
        assert runner._role is SessionRole.CONTROLLER

    def test_host_role(self) -> None:
        # 한글 주석 — 내 PC 제어 위임 = HOST
        mock_self = MagicMock()
        mock_self._remote_data_channel = None
        ChatHeaderMixin._start_remote_session(mock_self, "host", "친구B")
        runner = mock_self._remote_runner
        assert isinstance(runner, RemoteSessionRunner)
        assert runner._role is SessionRole.HOST

    def test_send_callable_no_channel_graceful(self) -> None:
        # 한글 주석 — 채널 미확립 시 send no-op graceful (예외 부재)
        mock_self = MagicMock()
        mock_self._remote_data_channel = None
        ChatHeaderMixin._start_remote_session(mock_self, "controller", "친구C")
        runner = mock_self._remote_runner
        # send_frame 호출이 예외 없이 통과 (no-op)
        assert runner._send_frame(b"x") is None

    def test_send_callable_routes_to_channel(self) -> None:
        # 한글 주석 — 채널 확립 시 send 가 채널.send 로 결선
        mock_self = MagicMock()
        chan = MagicMock()
        mock_self._remote_data_channel = chan
        ChatHeaderMixin._start_remote_session(mock_self, "host", "친구D")
        runner = mock_self._remote_runner
        runner._send_input(b"payload")
        chan.send.assert_called_once_with(b"payload")
