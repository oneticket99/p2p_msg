# SPDX-License-Identifier: GPL-3.0-or-later
"""auto-update UI dialog — PyQt6 새 버전 알림 + progress bar + 사용자 GO (cycle 133).

Phase 4 cycle 132 의 ``app/updater/`` skeleton (version_check / downloader /
applier) follow-up — 사용자 가시 (visible) UI layer. 새 버전 검출 시 dialog
표시 + release notes + 사용자 명시 GO 버튼 + progress bar + relaunch chain
trigger 지점 (실 download chain = Phase 5 본격 cycle 위탁).

설계 결정
---------
- PyQt6 ImportError graceful fallback — CI Linux runner 환경 정합 의무
  (``settings_dialog.py`` 동일 패턴 정합).
- UI logic 본체 = QWidget 부재 시 noop 분기 — pytest mock 가능.
- 사용자 GO 직후 download/apply chain trigger = 본 cycle skeleton 외
  (callback 주입 + progress hook 만 노출).
- progress callback ratio 0.0~1.0 clamp + 정수 0~100 변환 helper 분리.

본 cycle 범위 외
----------------
- 실 download chain 의 호출 (Phase 5 본격 cycle)
- 강제 업데이트 (force=true) 시 차단 dialog
- delta update / 채널 분기 (stable / beta / nightly)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QPushButton,
        QVBoxLayout,
    )

    _PYQT_AVAILABLE = True
except ImportError:  # pragma: no cover - PyQt6 미설치 환경 폴백
    QDialog = object  # type: ignore[assignment, misc]
    QHBoxLayout = None  # type: ignore[assignment, misc]
    QLabel = None  # type: ignore[assignment, misc]
    QProgressBar = None  # type: ignore[assignment, misc]
    QPushButton = None  # type: ignore[assignment, misc]
    QVBoxLayout = None  # type: ignore[assignment, misc]
    _PYQT_AVAILABLE = False


def clamp_progress_percent(ratio: float) -> int:
    """progress callback ratio 0.0~1.0 → 0~100 정수 변환 + clamp.

    Parameters
    ----------
    ratio : float
        downloader progress ratio (0.0 ~ 1.0). 범위 외 값 = clamp.

    Returns
    -------
    int
        0~100 정수 (QProgressBar.setValue 직접 주입 가능).
    """

    # 한글 주석: 범위 외 값 안전 clamp — UI freeze 방지
    if ratio < 0.0:
        return 0
    if ratio > 1.0:
        return 100
    return int(ratio * 100)


class UpdateDialog(QDialog):  # type: ignore[misc, valid-type]
    """새 버전 알림 dialog + progress bar + relaunch chain trigger.

    PyQt6 부재 시 ``__init__`` 의 early return + 모든 method noop.
    실 download chain = ``on_user_go`` callback 으로 주입 (Phase 5 cycle).
    """

    def __init__(
        self,
        current_version: str,
        latest_info: dict,
        parent: Any = None,
        on_user_go: Optional[Callable[[dict], None]] = None,
    ) -> None:
        # 한글 주석: PyQt6 부재 환경 의 graceful skip (CI Linux runner 정합)
        if not _PYQT_AVAILABLE:
            log.warning("[update-dialog] PyQt6 부재 — graceful skip")
            self.current_version = current_version
            self.latest_info = latest_info
            self.on_user_go = on_user_go
            self.progress = None
            self.btn_update = None
            self.btn_later = None
            return
        super().__init__(parent)
        self.current_version = current_version
        self.latest_info = latest_info
        self.on_user_go = on_user_go
        self._setup_ui()

    def _setup_ui(self) -> None:
        # 한글 주석: 새 버전 안내 label + release notes + 사용자 GO 버튼 row
        self.setWindowTitle("TooTalk 업데이트")
        self.setModal(True)
        layout = QVBoxLayout()
        latest_version = self.latest_info.get("version", "(unknown)")
        layout.addWidget(QLabel(f"새 버전 {latest_version} 사용 가능"))
        layout.addWidget(QLabel(f"현재 버전: {self.current_version}"))
        notes = self.latest_info.get("release_notes", "변경사항 없음")
        layout.addWidget(QLabel(f"변경사항:\n{notes}"))
        # 한글 주석: progress bar — 사용자 GO 직후 visible 전환
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        # 한글 주석: 사용자 GO / 연기 버튼 row
        btn_layout = QHBoxLayout()
        self.btn_update = QPushButton("업데이트")
        self.btn_later = QPushButton("나중에")
        self.btn_update.clicked.connect(self._on_update)
        self.btn_later.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_update)
        btn_layout.addWidget(self.btn_later)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _on_update(self) -> None:
        # 한글 주석: 사용자 GO 직후 progress bar 표시 + 버튼 비활성 + callback
        if not _PYQT_AVAILABLE:
            return
        self.progress.setVisible(True)
        self.btn_update.setEnabled(False)
        self.btn_later.setEnabled(False)
        log.info("[update-dialog] 사용자 GO — download chain trigger")
        # 한글 주석: 실 download chain = Phase 5 본격 cycle 위탁 callback
        if self.on_user_go is not None:
            try:
                self.on_user_go(self.latest_info)
            except Exception as exc:  # noqa: BLE001
                log.warning("[update-dialog] on_user_go callback 실패 — %r", exc)

    def update_progress(self, ratio: float) -> None:
        # 한글 주석: downloader progress callback → 0~100 정수 변환 후 setValue
        if not _PYQT_AVAILABLE or self.progress is None:
            return
        self.progress.setValue(clamp_progress_percent(ratio))
