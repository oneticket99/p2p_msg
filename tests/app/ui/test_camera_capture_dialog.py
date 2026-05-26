# SPDX-License-Identifier: GPL-3.0-or-later
"""CameraCaptureDialog 단위 test — cycle 169.852 M5 (T-14/T-15).

실 카메라 open 회피(결정적 + macOS LED/누수 차단) 위해 `_init_camera` 를 monkeypatch
로 unavailable 경로 강제. 촬영 핸들러(fake QImage)·오류·자원 해제 분기를 카메라 없이
검증한다. 실 webcam live preview/촬영은 G-final 사용자 visual ack 영역(headless 대체 불가).
"""

from __future__ import annotations

import pytest
from PyQt6.QtGui import QImage

from app.ui import _camera_capture_dialog as cam_mod
from app.ui._camera_capture_dialog import CameraCaptureDialog


@pytest.fixture(autouse=True)
def _no_real_camera(monkeypatch):
    """_init_camera 를 unavailable 경로로 강제 — 실 카메라 미오픈(결정적)."""

    monkeypatch.setattr(
        cam_mod.CameraCaptureDialog,
        "_init_camera",
        lambda self: self._show_unavailable("test mock — 카메라 미오픈"),
    )


def _img() -> QImage:
    img = QImage(200, 200, QImage.Format.Format_RGB32)
    img.fill(0x44AA88)
    return img


def test_unavailable_disables_capture(qapp) -> None:
    # 한글 주석 — 카메라 부재/권한 거부 경로 → 촬영 button 비활성 + status(graceful)
    dlg = CameraCaptureDialog()
    assert dlg._capture_btn.isEnabled() is False
    assert dlg.captured_image is None
    assert dlg._status.text() != ""


def test_image_captured_handler_stores_and_emits(qapp) -> None:
    # 한글 주석 — 촬영 핸들러(mock frame) → captured_image + signal + accept
    dlg = CameraCaptureDialog()
    captured = []
    dlg.image_captured.connect(lambda im: captured.append(im))
    dlg._on_image_captured(0, _img())
    assert dlg.captured_image is not None
    assert not dlg.captured_image.isNull()
    assert len(captured) == 1
    assert dlg.result() == dlg.DialogCode.Accepted


def test_image_captured_null_no_store(qapp) -> None:
    # 한글 주석 — null QImage → 저장 안 함(graceful)
    dlg = CameraCaptureDialog()
    dlg._on_image_captured(0, QImage())
    assert dlg.captured_image is None


def test_camera_error_graceful(qapp) -> None:
    # 한글 주석 — 카메라 오류(권한 거부 등) → unavailable 표시(crash 차단)
    dlg = CameraCaptureDialog()
    dlg._on_camera_error(None, "permission denied")
    assert dlg._capture_btn.isEnabled() is False
    assert dlg._status.text() != ""


def test_release_camera_no_crash_when_none(qapp) -> None:
    # 한글 주석 — 카메라 부재 시 release no-op(무crash) + reject 자원 해제 경로
    dlg = CameraCaptureDialog()
    dlg._release_camera()  # camera None — 무crash
    dlg.reject()
    assert dlg.result() == dlg.DialogCode.Rejected
