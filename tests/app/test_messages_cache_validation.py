# SPDX-License-Identifier: GPL-3.0-or-later
"""messages_cache validation unit test — cycle 169.682 omit retain.

실 SQLite connection 부재 path — pre-execution validation 만.
"""

from __future__ import annotations

import pytest


class TestInsertMessageValidation:
    def test_negative_msg_id_raises(self) -> None:
        from app.db.messages_cache import insert_message

        with pytest.raises(ValueError, match="msg_id"):
            insert_message(msg_id=-1, room_id=1, sender_id=10)

    def test_zero_room_id_raises(self) -> None:
        from app.db.messages_cache import insert_message

        with pytest.raises(ValueError, match="room_id"):
            insert_message(msg_id=1, room_id=0, sender_id=10)

    def test_negative_room_id_raises(self) -> None:
        from app.db.messages_cache import insert_message

        with pytest.raises(ValueError, match="room_id"):
            insert_message(msg_id=1, room_id=-5, sender_id=10)

    def test_zero_sender_id_raises(self) -> None:
        from app.db.messages_cache import insert_message

        with pytest.raises(ValueError, match="sender_id"):
            insert_message(msg_id=1, room_id=1, sender_id=0)

    def test_invalid_kind_raises(self) -> None:
        # 한글 주석 — kind ENUM 의무 = text/file/system
        from app.db.messages_cache import insert_message

        with pytest.raises(ValueError, match="kind"):
            insert_message(msg_id=1, room_id=1, sender_id=10, kind="voice")
