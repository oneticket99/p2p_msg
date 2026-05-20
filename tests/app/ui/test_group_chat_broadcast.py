# SPDX-License-Identifier: GPL-3.0-or-later
"""GroupChatView mesh broadcast UI test — cycle 169.61 신설.

message_send_requested signal fire chain 검증.
"""

from __future__ import annotations

import pytest

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QPushButton
    _PYQT_AVAILABLE = True
except ImportError:
    _PYQT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _PYQT_AVAILABLE, reason="PyQt6 미설치")


class TestGroupChatBroadcast:
    """GroupChatView 안 send button click → message_send_requested signal fire."""

    def test_send_clicked_emits_signal(self, qtbot) -> None:
        from app.ui.group_chat_view import GroupChatView
        view = GroupChatView(room_id=42, self_username="alice")
        qtbot.addWidget(view)
        captured: list[str] = []
        view.message_send_requested.connect(lambda text: captured.append(text))  # type: ignore[arg-type]
        view._input_edit.setText("안녕")
        view._on_send_clicked()
        assert captured == ["안녕"]

    def test_empty_input_no_emit(self, qtbot) -> None:
        from app.ui.group_chat_view import GroupChatView
        view = GroupChatView(room_id=42, self_username="alice")
        qtbot.addWidget(view)
        captured: list[str] = []
        view.message_send_requested.connect(lambda text: captured.append(text))  # type: ignore[arg-type]
        view._input_edit.setText("")
        view._on_send_clicked()
        assert captured == []

    def test_input_cleared_after_send(self, qtbot) -> None:
        from app.ui.group_chat_view import GroupChatView
        view = GroupChatView(room_id=42, self_username="alice")
        qtbot.addWidget(view)
        view._input_edit.setText("test")
        view._on_send_clicked()
        assert view._input_edit.text() == ""
