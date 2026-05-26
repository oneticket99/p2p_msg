# SPDX-License-Identifier: GPL-3.0-or-later
"""AvatarPickerButton 단위 test — cycle 169.852 M3 (Exec Plan T-8/T-9).

offscreen Qt + QFileDialog/clipboard monkeypatch — 드롭다운 3항목(이모지 제외) +
파일/클립보드 분기 + 정사각 crop + signal emit + 이니셜/camera fallback 검증.
"""

from __future__ import annotations

import pytest
from PyQt6.QtGui import QImage

from app.ui._avatar_picker_button import AvatarPickerButton


@pytest.fixture
def picker(qapp):
    return AvatarPickerButton(name="언탄", size=72)


def _solid_image(w=600, h=400) -> QImage:
    img = QImage(w, h, QImage.Format.Format_RGB32)
    img.fill(0xFF3366)
    return img


def test_dropdown_three_items_no_emoji(picker) -> None:
    # 한글 주석 — 드롭다운 = 파일/카메라/클립보드 3항목, 이모지 항목 부재 (directive)
    texts = [a.text() for a in picker.menu().actions()]
    assert texts == ["파일에서", "카메라에서", "클립보드에서"]
    assert not any("이모지" in t for t in texts)


def test_initial_state_no_image(picker) -> None:
    # 한글 주석 — 초기 = 이미지 미선택 (이니셜 fallback 표시)
    assert picker.selected_image is None
    assert picker.to_bytes() is None
    assert not picker.icon().isNull()  # 이니셜 pixmap 아이콘 set


def test_pick_file_loads_and_emits(picker, monkeypatch, tmp_path) -> None:
    # 한글 주석 — QFileDialog mock → 임시 png path → QImage load + signal
    png = tmp_path / "a.png"
    _solid_image().save(str(png), "PNG")
    monkeypatch.setattr(
        "app.ui._avatar_picker_button.QFileDialog.getOpenFileName",
        staticmethod(lambda *a, **k: (str(png), "")),
    )
    captured = []
    picker.avatar_selected.connect(lambda img: captured.append(img))
    picker._on_pick_file()
    assert picker.selected_image is not None
    # 정사각 다운스케일 → size x size
    assert picker.selected_image.width() == 72 and picker.selected_image.height() == 72
    assert len(captured) == 1
    assert picker.to_bytes() is not None


def test_pick_file_cancel_noop(picker, monkeypatch) -> None:
    # 한글 주석 — 취소(빈 path) → 변경 없음
    monkeypatch.setattr(
        "app.ui._avatar_picker_button.QFileDialog.getOpenFileName",
        staticmethod(lambda *a, **k: ("", "")),
    )
    picker._on_pick_file()
    assert picker.selected_image is None


def test_pick_file_invalid_image_skip(picker, monkeypatch, tmp_path) -> None:
    # 한글 주석 — decode 실패(빈 파일) → graceful skip
    bad = tmp_path / "bad.png"
    bad.write_text("not an image")
    monkeypatch.setattr(
        "app.ui._avatar_picker_button.QFileDialog.getOpenFileName",
        staticmethod(lambda *a, **k: (str(bad), "")),
    )
    picker._on_pick_file()
    assert picker.selected_image is None


def test_pick_clipboard_image(picker, monkeypatch) -> None:
    # 한글 주석 — clipboard().image() mock → QImage 적용
    class _Clip:
        def image(self):
            return _solid_image(300, 300)

    monkeypatch.setattr(
        "app.ui._avatar_picker_button.QGuiApplication.clipboard",
        staticmethod(lambda: _Clip()),
    )
    picker._on_pick_clipboard()
    assert picker.selected_image is not None
    assert picker.selected_image.width() == 72


def test_pick_clipboard_empty_skip(picker, monkeypatch) -> None:
    # 한글 주석 — 클립보드 이미지 부재(null) → skip
    class _Clip:
        def image(self):
            return QImage()  # null

    monkeypatch.setattr(
        "app.ui._avatar_picker_button.QGuiApplication.clipboard",
        staticmethod(lambda: _Clip()),
    )
    picker._on_pick_clipboard()
    assert picker.selected_image is None


def test_camera_action_emits_signal(picker, monkeypatch) -> None:
    # 한글 주석 — "카메라에서" → camera_requested signal emit (후방 호환) +
    # M5 핸들러는 실 카메라/blocking 모달 진입 → headless 에선 stub 로 차단:
    #   _init_camera 무력화(실 webcam 미오픈) + exec_modal 즉시 Rejected(미block).
    import app.ui._camera_capture_dialog as cam_mod
    import app.ui._modal_helper as modal_mod

    monkeypatch.setattr(
        cam_mod.CameraCaptureDialog,
        "_init_camera",
        lambda self: self._show_unavailable("test stub — 카메라 미오픈"),
    )
    monkeypatch.setattr(
        modal_mod,
        "exec_modal",
        lambda dlg, opener: dlg.DialogCode.Rejected,
    )

    fired = []
    picker.camera_requested.connect(lambda: fired.append(True))
    cam_action = next(a for a in picker.menu().actions() if a.text() == "카메라에서")
    cam_action.trigger()
    assert fired == [True]
    # 한글 주석 — Rejected 경로라 이미지 미적용(부수효과 없음 확인)
    assert picker.selected_image is None


def test_set_image_external(picker) -> None:
    # 한글 주석 — M5 카메라 등 외부 주입 경로
    picker.set_image(_solid_image(500, 500))
    assert picker.selected_image is not None
    assert picker.selected_image.width() == 72


def test_set_name_updates_fallback(qapp) -> None:
    # 한글 주석 — name 없는 빈 상태(camera placeholder) → name set 시 이니셜 fallback
    p = AvatarPickerButton(name="", size=72)
    assert p.selected_image is None
    p.set_name("홍원표")
    assert not p.icon().isNull()
