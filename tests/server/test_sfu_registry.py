# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.sfu_registry`` 단위 테스트 — cycle 169.801 SFU 확장 M3c.

SfuRegistry 의 lazy 생성·동일 인스턴스 공유·빈 room GC·shutdown 정리를
aiortc 실 결선 없이 검증한다 (room lifecycle 로직 격리).
"""

from __future__ import annotations

import pytest

pytest.importorskip("aiortc", reason="aiortc + av wheel install 의무")

from server.sfu_registry import SfuRegistry  # noqa: E402
from server.sfu_room import SfuRoom  # noqa: E402


class TestSfuRegistry:
    """room lifecycle 관리 검증."""

    @pytest.mark.asyncio
    async def test_get_or_create_lazy_and_shared(self) -> None:
        """첫 호출은 생성, 재호출은 동일 인스턴스 반환."""
        reg = SfuRegistry()
        assert reg.room_count() == 0
        room1 = await reg.get_or_create("r1")
        assert isinstance(room1, SfuRoom)
        assert reg.room_count() == 1
        room2 = await reg.get_or_create("r1")
        assert room1 is room2, "동일 room_id 는 같은 SfuRoom 공유"
        assert reg.room_count() == 1

    def test_get_without_create_returns_none(self) -> None:
        """get 은 미존재 room 을 생성하지 않고 None 반환."""
        reg = SfuRegistry()
        assert reg.get("ghost") is None
        assert reg.room_count() == 0

    @pytest.mark.asyncio
    async def test_remove_peer_gc_empty_room(self) -> None:
        """마지막 peer 이탈로 room 이 비면 registry 에서 GC 된다."""
        reg = SfuRegistry()
        await reg.get_or_create("r2")
        assert reg.room_count() == 1
        # producer/subscriber 가 없는 빈 room 은 remove_peer 후 GC
        await reg.remove_peer("r2", "nobody")
        assert reg.room_count() == 0

    @pytest.mark.asyncio
    async def test_remove_peer_unknown_room_noop(self) -> None:
        """존재하지 않는 room 의 remove_peer 는 무해(no-op)."""
        reg = SfuRegistry()
        await reg.remove_peer("ghost", "p1")  # 예외 없이 통과
        assert reg.room_count() == 0

    @pytest.mark.asyncio
    async def test_shutdown_clears_all(self) -> None:
        """shutdown 은 모든 room 을 정리한다."""
        reg = SfuRegistry()
        await reg.get_or_create("r3")
        await reg.get_or_create("r4")
        assert reg.room_count() == 2
        await reg.shutdown()
        assert reg.room_count() == 0
