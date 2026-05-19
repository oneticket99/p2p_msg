# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 Item 3 emoji pack moderation admin dialog — cycle 144 PyQt6.

memory `project_emoji_pack_share.md` 정합. owner role 만 access 의
moderation admin dialog. pending queue list + thumbnail preview +
approve/reject buttons + DMCA notice 의 4 widget layout.

본 module 범위 (cycle 144 skeleton)
-----------------------------------
- ``PendingPackItem`` frozen dataclass — admin UI 의 단일 row 데이터
  (pack_id + name + slug + owner_username + thumbnail_path + reasons).
- ``EmojiModerationDialog`` — PyQt6 dialog + pending queue list +
  approve/reject/dmca buttons + emit ``decision_made`` signal.
- PyQt6 graceful — ImportError 환경 의 stub 반환 (CI Linux runner 정합).

설계 결정
---------
- 실 REST 호출 = caller 책임 (signal emit + caller 의 POST 호출).
- thumbnail 표시 = file_path 기반 QPixmap 의 graceful load (실패 시 텍스트).
- owner role 검증 = caller 책임 (dialog 의 진입 시점 의 caller 가드).

본 cycle 의 범위 외 (별개 cycle 145+):
- 실 REST POST 호출 binding (`/api/emoji/moderation/approve` etc.)
- pagination + infinite scroll
- bulk approve/reject (다중 선택)
- audit log 표시 (이전 결정 이력)
- 실 DMCA notice 본문 templating
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

log = logging.getLogger(__name__)

try:
    from PyQt6.QtCore import pyqtSignal
    from PyQt6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMessageBox,
        QPushButton,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    _PYQT_AVAILABLE = True
except ImportError:  # pragma: no cover — PyQt6 부재 환경 graceful skip
    QDialog = object  # type: ignore[assignment, misc]
    QHBoxLayout = None  # type: ignore[assignment, misc]
    QLabel = None  # type: ignore[assignment, misc]
    QListWidget = None  # type: ignore[assignment, misc]
    QListWidgetItem = None  # type: ignore[assignment, misc]
    QMessageBox = None  # type: ignore[assignment, misc]
    QPushButton = None  # type: ignore[assignment, misc]
    QTextEdit = None  # type: ignore[assignment, misc]
    QVBoxLayout = None  # type: ignore[assignment, misc]
    QWidget = None  # type: ignore[assignment, misc]
    pyqtSignal = None  # type: ignore[assignment, misc]
    _PYQT_AVAILABLE = False


# ─── 도메인 dataclass ────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class PendingPackItem:
    """admin UI pending queue 의 단일 row 데이터.

    Attributes
    ----------
    pack_id : int
        emoji_packs.id (PK).
    name : str
        팩 이름 (사용자 표기).
    slug : str
        URL slug.
    owner_username : str
        팩 owner 의 username (audit 표시).
    thumbnail_path : Optional[str]
        대표 이미지 경로 (None = 텍스트 fallback).
    reasons : tuple[str, ...]
        dispatcher 의 결정 사유 누계 (예: OCR suspicious + DMCA clean).
    """

    pack_id: int
    name: str
    slug: str
    owner_username: str
    thumbnail_path: Optional[str] = None
    reasons: tuple = ()


# ─── PyQt6 부재 graceful stub ────────────────────────────────────────────────

if not _PYQT_AVAILABLE:  # pragma: no cover

    class EmojiModerationDialog:  # type: ignore[no-redef]
        """PyQt6 부재 환경 의 stub — RuntimeError 즉시 raise."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError("PyQt6 미설치 — EmojiModerationDialog 사용 불가")

else:

    class EmojiModerationDialog(QDialog):  # type: ignore[no-redef]
        """emoji pack moderation 관리자 dialog — owner role 만 access.

        Layout (4 widget):
            1. QListWidget — pending pack queue
            2. QLabel — thumbnail preview (선택 항목)
            3. QTextEdit — reasons + DMCA notice 본문
            4. QHBoxLayout — approve / reject / dmca 3 button row

        Signals
        -------
        decision_made : pyqtSignal(int, str)
            (pack_id, decision_string) — caller 가 REST 호출 의무.
            decision_string ∈ {"approve", "reject", "dmca"}.
        """

        decision_made = pyqtSignal(int, str)  # type: ignore[misc]

        def __init__(
            self,
            pending_items: List[PendingPackItem],
            parent: Any = None,
            on_decision: Optional[Callable[[int, str], None]] = None,
        ) -> None:
            """admin dialog 신설.

            Parameters
            ----------
            pending_items : List[PendingPackItem]
                pending queue 의 단일 snapshot (caller 가 list_pending 호출).
            parent : Any
                parent QWidget (None = top level).
            on_decision : Optional[Callable[[int, str], None]]
                approve/reject/dmca 결정 시 callback (pack_id, decision_string).
                None = signal 만 emit + caller slot connect.
            """

            super().__init__(parent)
            self._pending_items: List[PendingPackItem] = list(pending_items)
            self._on_decision = on_decision
            self._selected_item: Optional[PendingPackItem] = None
            self._setup_ui()

        def _setup_ui(self) -> None:
            # 한글 주석: dialog window title + 4 widget layout
            self.setWindowTitle("emoji 팩 moderation 관리자 (cycle 144)")
            self.resize(700, 480)
            root = QVBoxLayout()

            # 한글 주석: pending queue list — 단일 row = pack_id + name + slug
            self._list_widget = QListWidget()
            for item in self._pending_items:
                lw_item = QListWidgetItem(
                    f"[{item.pack_id}] {item.name} (slug={item.slug}, "
                    f"owner={item.owner_username})"
                )
                # 한글 주석: QListWidgetItem 의 setData 로 도메인 객체 binding
                lw_item.setData(0x0100, item.pack_id)  # Qt.UserRole = 0x0100
                self._list_widget.addItem(lw_item)
            self._list_widget.currentRowChanged.connect(self._on_row_changed)
            root.addWidget(QLabel("pending 팩 queue"))
            root.addWidget(self._list_widget)

            # 한글 주석: thumbnail preview + reasons + DMCA notice 본문
            self._preview_label = QLabel("(미선택)")
            self._preview_label.setMinimumHeight(80)
            root.addWidget(self._preview_label)

            self._reasons_edit = QTextEdit()
            self._reasons_edit.setReadOnly(True)
            self._reasons_edit.setMaximumHeight(140)
            root.addWidget(QLabel("결정 사유 + DMCA notice"))
            root.addWidget(self._reasons_edit)

            # 한글 주석: approve / reject / dmca 3 button row
            btn_row = QHBoxLayout()
            self._btn_approve = QPushButton("승인 (approve)")
            self._btn_reject = QPushButton("거부 (reject)")
            self._btn_dmca = QPushButton("DMCA 신고 (takedown)")
            self._btn_approve.clicked.connect(lambda: self._emit_decision("approve"))
            self._btn_reject.clicked.connect(lambda: self._emit_decision("reject"))
            self._btn_dmca.clicked.connect(lambda: self._emit_decision("dmca"))
            btn_row.addWidget(self._btn_approve)
            btn_row.addWidget(self._btn_reject)
            btn_row.addWidget(self._btn_dmca)
            root.addLayout(btn_row)

            self.setLayout(root)
            # 한글 주석: 초기 button 비활성 — 선택 row 부재 시 클릭 차단
            self._set_buttons_enabled(False)

        def _set_buttons_enabled(self, enabled: bool) -> None:
            # 한글 주석: 선택 row 부재 시 3 button 비활성 — UX 의무
            self._btn_approve.setEnabled(enabled)
            self._btn_reject.setEnabled(enabled)
            self._btn_dmca.setEnabled(enabled)

        def _on_row_changed(self, row: int) -> None:
            # 한글 주석: 선택 row 변경 시 thumbnail + reasons 갱신
            if row < 0 or row >= len(self._pending_items):
                self._selected_item = None
                self._preview_label.setText("(미선택)")
                self._reasons_edit.setPlainText("")
                self._set_buttons_enabled(False)
                return
            self._selected_item = self._pending_items[row]
            # 한글 주석: thumbnail_path None graceful — 텍스트 fallback
            if self._selected_item.thumbnail_path:
                self._preview_label.setText(
                    f"thumbnail: {self._selected_item.thumbnail_path}"
                )
            else:
                self._preview_label.setText("(thumbnail 부재)")
            reasons_text = "\n".join(self._selected_item.reasons) or "(사유 부재)"
            self._reasons_edit.setPlainText(reasons_text)
            self._set_buttons_enabled(True)

        def _emit_decision(self, decision: str) -> None:
            # 한글 주석: 선택 row 부재 시 noop — UI 안전 guard
            if self._selected_item is None:
                log.warning("[admin-moderation] 선택 row 부재 — decision skip")
                return
            pack_id = self._selected_item.pack_id
            log.info(
                "[admin-moderation] decision pack_id=%d decision=%s",
                pack_id,
                decision,
            )
            # 한글 주석: signal emit + caller callback 의 dual chain
            self.decision_made.emit(pack_id, decision)
            if self._on_decision is not None:
                try:
                    self._on_decision(pack_id, decision)
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "[admin-moderation] on_decision callback 실패 — %r", exc
                    )

        def selected_pack_id(self) -> Optional[int]:
            """현재 선택 row 의 pack_id 반환 — 테스트 + caller 의 helper."""

            # 한글 주석: 테스트 + caller 의 직접 조회 의 helper
            if self._selected_item is None:
                return None
            return self._selected_item.pack_id
