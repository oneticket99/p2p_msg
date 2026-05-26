# SPDX-License-Identifier: GPL-3.0-or-later
"""MyProfileDialog avatar picker 통합 test — cycle 169.852 M4 (T-13).

정보 dialog 의 avatar 가 AvatarPickerButton 으로 교체됐고, 선택 이미지가
`avatar_changed(QImage)` signal 로 상위(_drawer_mixin 업로드+PATCH)에 위임되는지 +
refresh_profile 의 set_name 이니셜 fallback 정합을 offscreen 검증한다.
"""

from __future__ import annotations

from PyQt6.QtGui import QImage

from app.ui._avatar_picker_button import AvatarPickerButton
from app.ui.my_profile_dialog import MyProfileDialog


def _img() -> QImage:
    img = QImage(300, 300, QImage.Format.Format_RGB32)
    img.fill(0x33AA66)
    return img


def test_profile_avatar_is_picker_button(qapp) -> None:
    # 한글 주석 — 정보 dialog avatar = AvatarPickerButton(클릭 시 드롭다운)
    d = MyProfileDialog(nickname="언탄", username="untan")
    assert isinstance(d._avatar_label, AvatarPickerButton)
    assert hasattr(d, "avatar_changed")
    # 드롭다운 3항목 이모지 제외
    texts = [a.text() for a in d._avatar_label.menu().actions()]
    assert texts == ["파일에서", "카메라에서", "클립보드에서"]


def test_avatar_selected_emits_avatar_changed(qapp) -> None:
    # 한글 주석 — picker 이미지 선택 → avatar_changed 상위 위임 emit
    d = MyProfileDialog(nickname="언탄", username="untan")
    captured = []
    d.avatar_changed.connect(lambda im: captured.append(im))
    d._avatar_label.set_image(_img())
    assert len(captured) == 1
    assert not captured[0].isNull()


def test_refresh_profile_set_name_no_crash(qapp) -> None:
    # 한글 주석 — refresh_profile 가 AvatarPickerButton.set_name 로 이니셜 fallback 갱신
    d = MyProfileDialog(nickname="언탄", username="untan")
    d.refresh_profile(nickname="홍원표", display_name="", username="untan", email="", bio="")
    assert not d._avatar_label.icon().isNull()
