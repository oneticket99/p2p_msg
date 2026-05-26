# SPDX-License-Identifier: GPL-3.0-or-later
"""AvatarPickerButton — 아바타 이미지 picker 공유 컴포넌트 (cycle 169.852 M3, T-8/T-9).

텔레그램 정합 — 그룹 만들기 / 채널 만들기 / 개인 프로필 3곳 공유(Exec Plan D-1).
원형 button + 클릭 시 드롭다운 3항목(**파일에서 / 카메라에서 / 클립보드에서**,
텔레그램 "이모지 사용"은 directive 명시 **제외**).

- 파일에서   : QFileDialog (jpg/png) → QImage.
- 클립보드에서 : QGuiApplication.clipboard().image() → QImage (빈 클립보드 graceful skip).
- 카메라에서  : ``camera_requested`` signal emit — M5 CameraCaptureDialog 가 연결.
                M3 단독에선 미연결 no-op(드롭다운 3항목 완성 유지).

선택 이미지 = center 정사각 crop + display size 다운스케일 + 원형 preview.
미선택 시 fallback(directive): name 있으면 2글자 이니셜(`_avatar_helper`), 없으면
camera 아이콘 blue circle("사진 추가" affordance). ``avatar_selected(QImage)`` signal.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QGuiApplication,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PyQt6.QtWidgets import QFileDialog, QMenu, QPushButton, QWidget

from app.ui._avatar_helper import make_initial_pixmap
from app.ui._icons import load_icon


class AvatarPickerButton(QPushButton):
    """원형 avatar picker — 드롭다운(파일/카메라/클립보드) + 원형 preview."""

    # 한글 주석 — 사용자가 이미지 선택 완료(파일/클립보드/카메라) 시 emit
    avatar_selected = pyqtSignal(QImage)
    # 한글 주석 — "카메라에서" 선택 시 emit — M5 CameraCaptureDialog 가 연결
    camera_requested = pyqtSignal()

    def __init__(
        self,
        name: str = "",
        size: int = 72,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._name = name
        self._size = size
        self._image: Optional[QImage] = None
        self.setFixedSize(size, size)
        self.setIconSize(QSize(size, size))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # 한글 주석 — 원형 + 투명 배경(아이콘이 원형 pixmap 을 직접 렌더)
        self.setStyleSheet(
            "QPushButton { background-color: transparent; border: 0; }"
            "QPushButton::menu-indicator { image: none; width: 0; }"
        )
        self.setMenu(self._build_menu())
        self._refresh()

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------

    def set_name(self, name: str) -> None:
        """이니셜 fallback 표시명 갱신 (이미지 미선택 시점 반영)."""

        self._name = name
        if self._image is None:
            self._refresh()

    def set_image(self, image: QImage) -> None:
        """외부(M5 카메라 등)에서 선택 이미지 주입 — preview + signal."""

        self._apply_image(image)

    @property
    def selected_image(self) -> Optional[QImage]:
        """현재 선택 이미지 (미선택 None)."""

        return self._image

    def to_bytes(self, fmt: str = "PNG") -> Optional[bytes]:
        """선택 이미지 → 업로드 byte (미선택 None). avatars_client 업로드 payload."""

        if self._image is None:
            return None
        from app.net.avatars_client import qimage_to_bytes

        return qimage_to_bytes(self._image, fmt)

    # ------------------------------------------------------------------
    # 드롭다운 + 소스 핸들러
    # ------------------------------------------------------------------

    def _build_menu(self) -> QMenu:
        """드롭다운 3항목 — 이모지 제외 (directive)."""

        menu = QMenu(self)
        act_file = menu.addAction(load_icon("image", size=18), "파일에서")
        act_file.triggered.connect(self._on_pick_file)
        act_camera = menu.addAction(load_icon("camera", size=18), "카메라에서")
        act_camera.triggered.connect(self._on_camera)
        act_clip = menu.addAction(load_icon("image", size=18), "클립보드에서")
        act_clip.triggered.connect(self._on_pick_clipboard)
        return menu

    def _on_pick_file(self) -> None:
        """파일에서 — QFileDialog (jpg/png) → QImage."""

        path, _ = QFileDialog.getOpenFileName(
            self, "이미지 선택", "", "이미지 (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        image = QImage(path)
        if image.isNull():
            return  # 한글 주석 — decode 실패 graceful skip
        self._apply_image(image)

    def _on_pick_clipboard(self) -> None:
        """클립보드에서 — clipboard().image() → QImage (빈 클립보드 skip)."""

        image = QGuiApplication.clipboard().image()
        if image is None or image.isNull():
            return  # 한글 주석 — 클립보드 이미지 부재 graceful skip
        self._apply_image(image)

    def _on_camera(self) -> None:
        """카메라에서 — CameraCaptureDialog(QtMultimedia in-app 모달) 촬영 → 적용 (M5)."""

        # 한글 주석 — 외부 listener 호환 유지 + 직접 카메라 모달 진입
        self.camera_requested.emit()
        from app.ui._camera_capture_dialog import CameraCaptureDialog
        from app.ui._modal_helper import exec_modal

        dlg = CameraCaptureDialog(parent=self)
        if exec_modal(dlg, self) == dlg.DialogCode.Accepted:
            image = dlg.captured_image
            if image is not None and not image.isNull():
                self._apply_image(image)

    # ------------------------------------------------------------------
    # 이미지 처리 + 렌더
    # ------------------------------------------------------------------

    def _apply_image(self, image: QImage) -> None:
        """center 정사각 crop + 다운스케일 → 저장 + preview + signal."""

        self._image = self._square_downscale(image, self._size)
        self._refresh()
        self.avatar_selected.emit(self._image)

    def _square_downscale(self, image: QImage, target: int) -> QImage:
        """center 정사각 crop 후 target px 다운스케일."""

        width, height = image.width(), image.height()
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        cropped = image.copy(left, top, side, side)
        return cropped.scaled(
            target,
            target,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _circular_pixmap(self, image: QImage) -> QPixmap:
        """이미지를 원형 clip 한 pixmap 생성 (QPainterPath ellipse clip)."""

        out = QPixmap(self._size, self._size)
        out.fill(Qt.GlobalColor.transparent)
        painter = QPainter(out)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, self._size, self._size)
        painter.setClipPath(path)
        painter.drawImage(0, 0, image)
        painter.end()
        return out

    def _camera_placeholder_pixmap(self) -> QPixmap:
        """이미지·이름 부재 시 blue circle + camera 아이콘 ("사진 추가")."""

        out = QPixmap(self._size, self._size)
        out.fill(Qt.GlobalColor.transparent)
        painter = QPainter(out)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 한글 주석 — Toonation primary blue circle (BI 상수, out.fill transparent 가 배경 cover)
        from PyQt6.QtGui import QColor

        painter.setBrush(QColor("#0066FF"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, self._size, self._size)
        # 한글 주석 — 중앙 camera 아이콘 (흰색, 절반 크기)
        icon_px = self._size // 2
        cam = load_icon("camera", size=icon_px, color="#ffffff").pixmap(icon_px, icon_px)
        off = (self._size - icon_px) // 2
        painter.drawPixmap(off, off, cam)
        painter.end()
        return out

    def _refresh(self) -> None:
        """현 상태(이미지/이름/빈)에 맞는 원형 pixmap 을 아이콘으로 설정."""

        if self._image is not None:
            pixmap = self._circular_pixmap(self._image)
        elif self._name:
            # 한글 주석 — directive: 이미지 미설정 시 기존 2글자 이니셜 fallback
            pixmap = make_initial_pixmap(self._name, size=self._size)
        else:
            pixmap = self._camera_placeholder_pixmap()
        self.setIcon(QIcon(pixmap))
