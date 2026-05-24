# SPDX-License-Identifier: GPL-3.0-or-later
"""messages_cache 실 SQLite chain unit — cycle 169.741 신설.

local_db _DB_PATH monkeypatch + tmp SQLite → insert/list/count/min/max/delete chain.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    # 한글 주석 — local_db singleton connection 의 tmp SQLite path 주입
    from app.db import local_db

    db_file = tmp_path / "test_cache.sqlite"
    monkeypatch.setattr(local_db, "_DB_PATH", db_file)
    monkeypatch.setattr(local_db, "_conn", None)
    yield db_file
    local_db.close_connection()


class TestInsertListChain:
    def test_insert_and_list(self, tmp_db) -> None:
        from app.db import messages_cache as mc

        mc.insert_message(msg_id=1, room_id=100, sender_id=10,
                          kind="text", body="hello", ts_ms=1000)
        mc.insert_message(msg_id=2, room_id=100, sender_id=20,
                          kind="text", body="world", ts_ms=2000)
        rows = mc.list_messages_by_room(room_id=100, limit=10)
        assert len(rows) == 2

    def test_count(self, tmp_db) -> None:
        from app.db import messages_cache as mc

        mc.insert_message(msg_id=1, room_id=200, sender_id=10,
                          kind="text", body="a", ts_ms=1000)
        mc.insert_message(msg_id=2, room_id=200, sender_id=10,
                          kind="text", body="b", ts_ms=2000)
        assert mc.count_messages(200) == 2

    def test_min_max_msg_id(self, tmp_db) -> None:
        from app.db import messages_cache as mc

        for i in range(5, 10):
            mc.insert_message(msg_id=i, room_id=300, sender_id=10,
                              kind="text", body=f"m{i}", ts_ms=i * 1000)
        assert mc.get_min_msg_id(300) == 5
        assert mc.get_max_msg_id(300) == 9

    def test_min_max_empty_none(self, tmp_db) -> None:
        from app.db import messages_cache as mc

        assert mc.get_min_msg_id(999) is None
        assert mc.get_max_msg_id(999) is None

    def test_delete_room_messages(self, tmp_db) -> None:
        from app.db import messages_cache as mc

        mc.insert_message(msg_id=1, room_id=400, sender_id=10,
                          kind="text", body="x", ts_ms=1000)
        mc.insert_message(msg_id=2, room_id=400, sender_id=10,
                          kind="text", body="y", ts_ms=2000)
        deleted = mc.delete_room_messages(400)
        assert deleted == 2
        assert mc.count_messages(400) == 0

    def test_duplicate_msg_id_ignored(self, tmp_db) -> None:
        # 한글 주석 — INSERT OR IGNORE → 중복 msg_id skip
        from app.db import messages_cache as mc

        mc.insert_message(msg_id=1, room_id=500, sender_id=10,
                          kind="text", body="first", ts_ms=1000)
        mc.insert_message(msg_id=1, room_id=500, sender_id=10,
                          kind="text", body="dup", ts_ms=2000)
        assert mc.count_messages(500) == 1

    def test_file_kind_with_file_id(self, tmp_db) -> None:
        from app.db import messages_cache as mc

        mc.insert_message(msg_id=1, room_id=600, sender_id=10,
                          kind="file", file_id="a" * 32, ts_ms=1000)
        rows = mc.list_messages_by_room(room_id=600, limit=10)
        assert len(rows) == 1
        assert rows[0]["kind"] == "file"
