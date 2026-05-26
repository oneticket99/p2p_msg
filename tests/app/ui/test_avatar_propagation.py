# SPDX-License-Identifier: GPL-3.0-or-later
"""avatar 표시 전파 단위 test — cycle 169.852 M6 (T-17).

ChatListEntry/MemberItem 의 avatar_ref 필드 + 렌더 site(chat-list delegate / member row)의
이니셜 fallback 무손상 + avatar_ready 구독 재렌더를 cover. 실 fetch 없이 결정적 검증
(seed_image 로 캐시 hit 모사). 실 서버 round-trip 은 G-final 사용자 ack 영역.
"""

from __future__ import annotations

from PyQt6.QtGui import QImage

from app.ui._avatar_cache import avatar_cache
from app.ui.chat_list_panel import ChatListEntry, ChatListPanel
from app.ui.member_list import MemberItem, _MemberRow

_REF = "avatars/" + ("b" * 64) + ".png"


def test_chat_list_entry_avatar_ref_default() -> None:
    # 한글 주석 — avatar_ref 기본값 빈 문자열(이니셜 fallback)
    e = ChatListEntry(kind="room", target_id=1, name="그룹방")
    assert e.avatar_ref == ""
    e2 = ChatListEntry(kind="room", target_id=2, name="채널", avatar_ref=_REF)
    assert e2.avatar_ref == _REF


def test_member_item_avatar_ref_default() -> None:
    # 한글 주석 — MemberItem avatar_ref 기본값 빈 문자열
    m = MemberItem(user_id=1, username="user")
    assert m.avatar_ref == ""
    m2 = MemberItem(user_id=2, username="user2", avatar_ref=_REF)
    assert m2.avatar_ref == _REF


def test_chat_list_panel_subscribes_avatar_ready(qapp) -> None:
    # 한글 주석 — 패널이 avatar_ready 구독 + 핸들러 no-crash(viewport repaint)
    panel = ChatListPanel()
    panel.set_entries([ChatListEntry(kind="room", target_id=1, name="방", avatar_ref=_REF)])
    panel._on_avatar_ready(_REF)  # 재페인트 trigger — 무crash


def test_member_row_initials_fallback_no_ref(qapp) -> None:
    # 한글 주석 — avatar_ref 부재 → 이니셜 pixmap(무손상, 비 null)
    row = _MemberRow(
        MemberItem(user_id=1, username="홍원표"),
        viewer_is_owner=False,
        kick_callback=lambda _uid: None,
    )
    assert not row._avatar.pixmap().isNull()


def test_member_row_avatar_ready_rerender_on_match(qapp) -> None:
    # 한글 주석 — seed 후 avatar_ready ref 일치 → 이미지 재렌더(무crash)
    avatar_cache().seed_image(_REF, QImage(80, 80, QImage.Format.Format_RGB32))
    row = _MemberRow(
        MemberItem(user_id=1, username="user", avatar_ref=_REF),
        viewer_is_owner=False,
        kick_callback=lambda _uid: None,
    )
    row._on_avatar_ready(_REF)  # 일치 → 재렌더
    row._on_avatar_ready("avatars/" + ("c" * 64) + ".png")  # 불일치 → no-op
    assert not row._avatar.pixmap().isNull()


def test_drawer_header_avatar_ref_and_update(qapp) -> None:
    # 한글 주석 — drawer header set_avatar_ref → seed 이미지 원형 표시(무crash)
    from app.ui.hamburger_drawer import HamburgerDrawer

    avatar_cache().seed_image(_REF, QImage(64, 64, QImage.Format.Format_RGB32))
    drawer = HamburgerDrawer(username="user", nickname="홍원표")
    assert drawer._avatar_ref == ""  # 초기 빈값(이니셜 fallback)
    assert not drawer._avatar_label.pixmap().isNull()
    drawer.set_avatar_ref(_REF)  # 내 avatar 설정 → 원형 이미지
    assert drawer._avatar_ref == _REF
    assert not drawer._avatar_label.pixmap().isNull()
    drawer.update_user_info("새이름")  # avatar_ref 유지 + 무crash(latent NameError 회수)
    assert drawer._username == "새이름"


def test_my_account_dialog_accepts_avatar_ref(qapp) -> None:
    # 한글 주석 — MyAccountDialog avatar_ref param 수용(렌더 무crash, 이니셜/이미지)
    from app.ui.my_account_dialog import MyAccountDialog

    dlg = MyAccountDialog(username="user", nickname="이름", avatar_ref="")
    assert dlg is not None  # avatar_ref 부재 → 이니셜 fallback 무손상
