# SPDX-License-Identifier: GPL-3.0-or-later
"""GroupCallDialog isolated 단위 테스트 — cycle 169.806 SFU 확장 M4b-2.

SFU 그룹 통화 타일 그리드의 동적 추가/교체/제거/정리를 offscreen Qt 로 검증한다
(VideoRenderer 미디어 loop 는 event loop 부재로 skip, 타일 구조만 검증).
"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6", reason="PyQt6 install 의무")

from app.ui.group_call_dialog import GroupCallDialog  # noqa: E402


class _DummyTrack:
    """VideoRenderer 에 넘길 최소 track 대역 (recv 미호출 — start 는 loop 부재로 skip)."""

    kind = "video"


class TestGroupCallDialog:
    """타일 grid lifecycle 검증."""

    def test_add_remote_track_creates_tile(self, qapp) -> None:
        dlg = GroupCallDialog("r1")
        assert dlg.tile_count() == 0
        dlg.add_remote_track("alice", _DummyTrack())
        dlg.add_remote_track("bob", _DummyTrack())
        assert dlg.tile_count() == 2
        assert set(dlg.producer_ids()) == {"alice", "bob"}
        dlg.close_all()

    def test_add_same_producer_replaces_tile(self, qapp) -> None:
        dlg = GroupCallDialog("r1")
        dlg.add_remote_track("alice", _DummyTrack())
        dlg.add_remote_track("alice", _DummyTrack())  # 재수신 — 교체
        assert dlg.tile_count() == 1
        dlg.close_all()

    def test_remove_producer(self, qapp) -> None:
        dlg = GroupCallDialog("r1")
        dlg.add_remote_track("alice", _DummyTrack())
        dlg.add_remote_track("bob", _DummyTrack())
        dlg.remove_producer("alice")
        assert dlg.producer_ids() == ["bob"]
        # 없는 producer 제거는 무해
        dlg.remove_producer("ghost")
        assert dlg.tile_count() == 1
        dlg.close_all()

    def test_close_all_clears_tiles(self, qapp) -> None:
        dlg = GroupCallDialog("r1")
        for pid in ("a", "b", "c"):
            dlg.add_remote_track(pid, _DummyTrack())
        assert dlg.tile_count() == 3
        dlg.close_all()
        assert dlg.tile_count() == 0

    def test_room_id_in_title(self, qapp) -> None:
        dlg = GroupCallDialog("room-xyz")
        assert dlg.room_id == "room-xyz"
        assert "room-xyz" in dlg.windowTitle()
        dlg.close_all()
