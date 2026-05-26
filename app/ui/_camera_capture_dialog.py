# SPDX-License-Identifier: GPL-3.0-or-later
"""CameraCaptureDialog — webcam 촬영 in-app 모달 (cycle 169.852 M5, T-14/T-15).

avatar picker "카메라에서" 진입점. QtMultimedia(QCamera/QMediaCaptureSession/
QImageCapture/QVideoWidget) live preview + 촬영 → QImage. FRONTEND.md §16 정합
(in-app overlay 모달 — `_modal_helper.exec_modal` parent walk → MainWindow
`_exec_dialog_centered`, 별도 OS 창 예외 4종 미해당).

자원 해제 의무 (feedback_objc_memory_release_mandatory): 종료(촬영/취소/close) 시
`QCamera.stop()` + `setActive(False)` 로 카메라 release (macOS LED 잔존/누수 차단).
권한 거부·카메라 부재 시 graceful — error label 표시 + 촬영 button 비활성(crash 없음).
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CameraCaptureDialog(QDialog):
    """webcam live preview + 촬영 in-app 모달 — 촬영 결과 QImage."""

    # 한글 주석 — 촬영 완료 시 QImage emit (picker 가 수신해 avatar 적용)
    image_captured = pyqtSignal(QImage)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("카메라")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(420, 480)
        self.setStyleSheet("QDialog { background-color: transparent; }")
        self._captured: Optional[QImage] = None
        self._camera = None
        self._capture = None
        self._session = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        wrap = QFrame()
        wrap.setObjectName("camWrap")
        wrap.setStyleSheet(
            "QFrame#camWrap { background-color: #131C30; border: 1px solid #1f2937; }"
        )
        outer.addWidget(wrap)
        body = QVBoxLayout(wrap)
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(12)

        title = QLabel("카메라 촬영")
        title.setStyleSheet("color: #f3f4f6; font-size: 16px; font-weight: 600;")
        body.addWidget(title)

        # 한글 주석 — preview 영역(카메라 가용 시 QVideoWidget, 부재 시 error label)
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet("color: #9ca3af; font-size: 13px;")
        self._preview_host = QVBoxLayout()
        body.addLayout(self._preview_host, stretch=1)
        body.addWidget(self._status)

        # 버튼 행 (취소 / 촬영)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel = QPushButton("취소")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.setStyleSheet(
            "QPushButton { color: #9ca3af; background: transparent; border: 0; padding: 8px 16px; }"
        )
        cancel.clicked.connect(self.reject)  # type: ignore[arg-type]
        btn_row.addWidget(cancel)
        self._capture_btn = QPushButton("촬영")
        self._capture_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._capture_btn.setStyleSheet(
            "QPushButton { color: #ffffff; background-color: #0066FF; border: 0;"
            " border-radius: 6px; padding: 8px 20px; font-weight: 600; }"
            "QPushButton:disabled { background-color: #374151; color: #9ca3af; }"
        )
        self._capture_btn.clicked.connect(self._on_capture_clicked)  # type: ignore[arg-type]
        btn_row.addWidget(self._capture_btn)
        body.addLayout(btn_row)

        self._init_camera()

    def _init_camera(self) -> None:
        """QtMultimedia 카메라 초기화 — 부재/권한 거부 시 graceful."""
        try:
            from PyQt6.QtMultimedia import (
                QCamera,
                QImageCapture,
                QMediaCaptureSession,
                QMediaDevices,
            )
            from PyQt6.QtMultimediaWidgets import QVideoWidget
        except ImportError:
            self._show_unavailable("카메라 모듈(QtMultimedia) 부재")
            return

        device = QMediaDevices.defaultVideoInput()
        if device is None or device.isNull():
            # 한글 주석 — 연결된 카메라 부재 → graceful(촬영 비활성)
            self._show_unavailable("사용 가능한 카메라 부재")
            return

        video = QVideoWidget()
        video.setStyleSheet("background-color: #000;")
        self._preview_host.addWidget(video)
        self._session = QMediaCaptureSession(self)
        self._camera = QCamera(device, self)
        self._capture = QImageCapture(self)
        self._session.setCamera(self._camera)
        self._session.setVideoOutput(video)
        self._session.setImageCapture(self._capture)
        # 한글 주석 — 촬영 결과 + 오류 핸들러
        self._capture.imageCaptured.connect(self._on_image_captured)
        self._camera.errorOccurred.connect(self._on_camera_error)
        self._camera.start()

    def _show_unavailable(self, reason: str) -> None:
        """카메라 부재/권한 거부 — error label + 촬영 비활성(graceful)."""
        self._status.setText(f"{reason} — 파일/클립보드로 선택하세요")
        self._capture_btn.setEnabled(False)

    def _on_capture_clicked(self) -> None:
        if self._capture is not None:
            self._capture.capture()

    def _on_image_captured(self, _id: int, image: QImage) -> None:
        """촬영 완료 — QImage 저장 + emit + 카메라 release + accept."""
        if image is not None and not image.isNull():
            self._captured = image
            self.image_captured.emit(image)
        self._release_camera()
        self.accept()

    def _on_camera_error(self, _error, message: str = "") -> None:
        """카메라 오류(권한 거부 등) — graceful 표시(crash 차단)."""
        self._show_unavailable(f"카메라 오류: {message}" if message else "카메라 접근 불가")

    def _release_camera(self) -> None:
        """카메라 자원 해제 — stop + setActive(False) + deleteLater (macOS LED/누수 차단).

        Exec Plan §9 사양 정합 — stop/비활성으로 하드웨어(LED) 점유를 풀고,
        QObject(camera/session/capture)를 deleteLater 로 명시 회수한다(parent 소유라
        dialog 파괴 시 회수되나 즉시 해제 보장). 참조를 None 으로 끊어 이중 호출
        (accept→close 경로 중복)에서도 무crash 유지.
        """
        if self._camera is not None:
            try:
                self._camera.stop()
                self._camera.setActive(False)
            except Exception:  # noqa: BLE001 - 종료 경로 graceful
                pass
        # 한글 주석 — QObject 3종 명시 회수 + 참조 차단(dangling 방지)
        for attr in ("_capture", "_session", "_camera"):
            obj = getattr(self, attr, None)
            if obj is not None:
                try:
                    obj.deleteLater()
                except Exception:  # noqa: BLE001 - 종료 경로 graceful
                    pass
                setattr(self, attr, None)

    @property
    def captured_image(self) -> Optional[QImage]:
        """촬영 결과 QImage (미촬영 None)."""
        return self._captured

    # 한글 주석 — 닫힘/취소 전 경로에서 카메라 release 보장
    def reject(self) -> None:  # type: ignore[override]
        self._release_camera()
        super().reject()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._release_camera()
        super().closeEvent(event)
