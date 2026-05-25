# SPDX-License-Identifier: GPL-3.0-or-later
"""MemberPanel isolated 단위 테스트 — cycle 169.819 그룹 멤버 패널.

빈 목록 안내 / 멤버 리스트 토글 + 뒤로 가기 신호 + 추방 passthrough 를
offscreen Qt 로 검증한다 ("멤버 보기" 빈 화면 + back 부재 회수).
"""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6", reason="PyQt6 install 의무")

from app.ui.member_list import MemberItem  # noqa: E402
from app.ui.member_panel import MemberPanel  # noqa: E402


class TestMemberPanel:
    """그룹 멤버 패널 lifecycle 검증."""

    def test_empty_shows_guide_label(self, qapp) -> None:
        panel = MemberPanel()
        panel.set_members([], viewer_role="member")
        # 빈 목록 = 안내 라벨 page (idx 1)
        assert panel._stack.currentIndex() == 1

    def test_members_show_list(self, qapp) -> None:
        panel = MemberPanel()
        panel.set_members(
            [
                MemberItem(user_id=0, username="alice", role="owner", is_online=True),
                MemberItem(user_id=1, username="bob", role="member", is_online=True),
            ],
            viewer_role="owner",
        )
        # 멤버 존재 = 리스트 page (idx 0) + 2행
        assert panel._stack.currentIndex() == 0
        assert panel._list.count() == 2

    def test_back_requested_emits(self, qapp) -> None:
        panel = MemberPanel()
        captured = []
        panel.back_requested.connect(lambda: captured.append("back"))
        panel.back_requested.emit()
        assert captured == ["back"]

    def test_member_kicked_passthrough(self, qapp) -> None:
        panel = MemberPanel()
        captured = []
        panel.member_kicked.connect(lambda uid: captured.append(uid))
        # 내부 리스트 신호 → 패널 passthrough
        panel._list.member_kicked.emit(42)
        assert captured == [42]
