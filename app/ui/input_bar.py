# SPDX-License-Identifier: GPL-3.0-or-later
"""InputBar — 채팅 입력 bar (cycle 153 phase 6 신설).

텔레그램 desktop input bar 등가 — 첨부 + emoji_picker popup + 텍스트 + voice mic + 보내기.
정합 = telegram-ui-survey.md §6 + EmojiPicker (cycle 153.5) + drag & drop event.

signal:
    message_sent(str) — text emit
    file_attached(list[str]) — file path list emit
    emoji_inserted(str) — emoji 입력 시 emit
    voice_recorded() — voice mic click (cycle 154+ entry)
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QCoreApplication, Qt, QSize, pyqtSignal
from app.ui._icons import load_icon
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)
_tr = lambda src: QCoreApplication.translate("MainWindow", src)


class InputBar(QFrame):
    """채팅 입력 bar — 첨부 + emoji + 텍스트 + voice + 보내기 + drag & drop."""

    message_sent = pyqtSignal(str)
    file_attached = pyqtSignal(list)
    emoji_inserted = pyqtSignal(str)
    voice_recorded = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("inputBar")
        self.setAcceptDrops(True)
        self.setMinimumHeight(64)
        self.setMaximumHeight(140)
        self.setStyleSheet(
            "QFrame#inputBar {"
            " background-color: #0F172A;"
            " border-top: 1px solid #1f2937;"
            "}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        # 한글 주석 — cycle 169.52 회수 — SVG icon 변환 (첨부 + emoji)
        self._attach_btn = QPushButton()
        self._attach_btn.setProperty("variant", "ghost")
        self._attach_btn.setFixedSize(36, 36)
        self._attach_btn.setIcon(load_icon("attach", size=20, color="#9ca3af"))
        self._attach_btn.setIconSize(QSize(20, 20))
        self._attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._attach_btn.setToolTip(_tr("파일 첨부"))
        self._attach_btn.clicked.connect(self._on_attach_clicked)  # type: ignore[arg-type]
        layout.addWidget(self._attach_btn)

        self._emoji_btn = QPushButton()
        self._emoji_btn.setProperty("variant", "ghost")
        self._emoji_btn.setFixedSize(36, 36)
        self._emoji_btn.setIcon(load_icon("emoji", size=20, color="#9ca3af"))
        self._emoji_btn.setIconSize(QSize(20, 20))
        self._emoji_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._emoji_btn.setToolTip(_tr("emoji 선택"))
        self._emoji_btn.clicked.connect(self._on_emoji_clicked)  # type: ignore[arg-type]
        layout.addWidget(self._emoji_btn)

        # 한글 주석 — multi-line text edit (Shift+Enter newline + Enter send)
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText(_tr("메시지 입력…"))
        self._text_edit.setMinimumHeight(40)
        self._text_edit.setMaximumHeight(120)
        self._text_edit.installEventFilter(self)
        layout.addWidget(self._text_edit, stretch=1)

        # 한글 주석 — cycle 169.55 회수 — voice mic SVG button
        self._voice_btn = QPushButton()
        self._voice_btn.setProperty("variant", "ghost")
        self._voice_btn.setFixedSize(36, 36)
        self._voice_btn.setIcon(load_icon("mic", size=20, color="#9ca3af"))
        self._voice_btn.setIconSize(QSize(20, 20))
        self._voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._voice_btn.setToolTip(_tr("음성 메시지 (cycle 154+ entry)"))
        self._voice_btn.clicked.connect(self._on_voice_clicked)  # type: ignore[arg-type]
        layout.addWidget(self._voice_btn)

        # 한글 주석 — cycle 169.55 회수 — 보내기 SVG button (primary)
        self._send_btn = QPushButton()
        self._send_btn.setProperty("variant", "primary")
        self._send_btn.setFixedSize(48, 36)
        self._send_btn.setIcon(load_icon("send", size=18, color="#ffffff"))
        self._send_btn.setIconSize(QSize(18, 18))
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setToolTip(_tr("보내기 (Enter)"))
        self._send_btn.clicked.connect(self._on_send_clicked)  # type: ignore[arg-type]
        layout.addWidget(self._send_btn)

        self._emoji_picker: Optional[QWidget] = None
        # cycle 154 — reply mode state + preview bar
        self._reply_context: Optional[tuple[str, str]] = None
        self._reply_preview: Optional[QFrame] = None

    def set_reply_to(self, sender: str, text: str) -> None:
        """reply mode 활성 — input bar 상단 preview bar 표시."""
        self._reply_context = (sender, text)
        self._render_reply_preview()

    def clear_reply_to(self) -> None:
        """reply mode 해제 + preview bar 제거."""
        self._reply_context = None
        if self._reply_preview is not None:
            self._reply_preview.deleteLater()
            self._reply_preview = None

    def reply_context(self) -> Optional[tuple[str, str]]:
        """현 reply context (sender, text) snapshot."""
        return self._reply_context

    def _render_reply_preview(self) -> None:
        """reply preview bar render — text_edit 직전 inject."""
        if self._reply_context is None:
            return
        if self._reply_preview is not None:
            self._reply_preview.deleteLater()
        sender, text = self._reply_context
        self._reply_preview = QFrame(self)
        self._reply_preview.setStyleSheet(
            "QFrame {"
            " border-left: 3px solid #22D3EE;"
            " background-color: rgba(34, 211, 238, 0.1);"
            " border-radius: 4px;"
            " padding: 4px 8px;"
            "}"
        )
        from PyQt6.QtWidgets import QLabel
        v = QVBoxLayout(self._reply_preview)
        v.setContentsMargins(8, 4, 8, 4)
        v.setSpacing(2)
        sender_label = QLabel(f"↳ {sender} (답장 중)")
        sender_label.setStyleSheet("color: #22D3EE; font-size: 11px; font-weight: 600;")
        v.addWidget(sender_label)
        preview_label = QLabel(text[:60])
        preview_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        preview_label.setWordWrap(True)
        v.addWidget(preview_label)
        cancel_btn = QPushButton("✕ 취소")
        cancel_btn.setProperty("variant", "ghost")
        cancel_btn.setFlat(True)
        cancel_btn.setMaximumWidth(80)
        cancel_btn.clicked.connect(self.clear_reply_to)  # type: ignore[arg-type]
        v.addWidget(cancel_btn)
        # 한글 주석 — preview = inputbar 본 layout 첫 row inject
        self.layout().insertWidget(0, self._reply_preview)  # type: ignore[union-attr]

    def eventFilter(self, obj, event):  # type: ignore[override]
        """text_edit 안 Enter = send + Shift+Enter = newline 분기."""
        if obj is self._text_edit and isinstance(event, QKeyEvent):
            if event.type() == QKeyEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                        self._on_send_clicked()
                        return True
        return super().eventFilter(obj, event)

    def _on_attach_clicked(self) -> None:
        """파일 첨부 dialog open + multi-select."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, _tr("파일 첨부"), "", "All Files (*.*)"
        )
        if paths:
            self.file_attached.emit(paths)
            log.info("input_bar 첨부 — %d file", len(paths))

    def _on_emoji_clicked(self) -> None:
        """emoji button click → EmojiPicker popup."""
        try:
            from app.ui.emoji_picker import EmojiPicker
        except Exception as exc:  # pragma: no cover - graceful
            log.debug("EmojiPicker import 실패 — %r", exc)
            return

        # 한글 주석 — popup 1회 생성 + reuse pattern
        if self._emoji_picker is None:
            self._emoji_picker = EmojiPicker(parent=self)
            self._emoji_picker.setWindowFlags(Qt.WindowType.Popup)  # type: ignore[attr-defined]
            self._emoji_picker.emoji_selected.connect(self._on_emoji_inserted)  # type: ignore[attr-defined]

        # 한글 주석 — emoji button 위 popup 위치 + 표시
        btn_pos = self._emoji_btn.mapToGlobal(self._emoji_btn.rect().topLeft())
        self._emoji_picker.move(btn_pos.x(), btn_pos.y() - self._emoji_picker.height() - 8)
        self._emoji_picker.show()

    def _on_emoji_inserted(self, emoji: str) -> None:
        """EmojiPicker → text_edit insert chain."""
        self._text_edit.insertPlainText(emoji)
        self.emoji_inserted.emit(emoji)
        if self._emoji_picker is not None:
            self._emoji_picker.hide()

    def _on_voice_clicked(self) -> None:
        """voice mic click — cycle 154+ entry."""
        self.voice_recorded.emit()
        log.info("input_bar voice mic click — cycle 154+ entry")

    def _on_send_clicked(self) -> None:
        """보내기 button + Enter → message_sent emit + text clear."""
        text = self._text_edit.toPlainText().strip()
        if not text:
            return
        self.message_sent.emit(text)
        self._text_edit.clear()

    def dragEnterEvent(self, event: Optional[QDragEnterEvent]) -> None:  # type: ignore[override]
        """drag enter — file URL accept."""
        if event is None:
            return
        if event.mimeData() and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: Optional[QDropEvent]) -> None:  # type: ignore[override]
        """drop event — file path list extract + file_attached emit."""
        if event is None:
            return
        mime = event.mimeData()
        if mime is None or not mime.hasUrls():
            return
        paths: list[str] = []
        for url in mime.urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        if paths:
            self.file_attached.emit(paths)
            event.acceptProposedAction()
            log.info("input_bar drag-drop — %d file", len(paths))
