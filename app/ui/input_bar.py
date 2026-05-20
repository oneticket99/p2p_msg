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
    QSizePolicy,
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
        # cycle 169.148 — telegram align inputBar fit content (bg transparent + border-top only)
        self.setMinimumHeight(56)
        self.setMaximumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        # cycle 169.137 — telegram align bg transparent + border-top only
        self.setStyleSheet(
            "QFrame#inputBar {"
            " background-color: transparent;"
            " border-top: 1px solid #1f2937;"
            "}"
        )

        # cycle 169.149 — composite pill 본격 재 구조 (telegram desktop 95% align)
        # outer = pill_frame (emoji + text_edit + attach) + voice/send circle (외부 우측)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

        # pill composite frame — emoji + text_edit + attach 단일 rounded container
        self._pill = QFrame(self)
        self._pill.setObjectName("inputBarPill")
        self._pill.setStyleSheet(
            "QFrame#inputBarPill {"
            " background-color: #1F2937;"
            " border: 1px solid #2c3a52;"
            " border-radius: 20px;"
            "}"
        )
        pill_layout = QHBoxLayout(self._pill)
        pill_layout.setContentsMargins(6, 0, 6, 0)
        pill_layout.setSpacing(2)
        pill_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # emoji 의 의 pill 안 좌측 inline
        self._emoji_btn = QPushButton(self._pill)
        self._emoji_btn.setFixedSize(32, 32)
        self._emoji_btn.setIcon(load_icon("emoji", size=20, color="#9ca3af"))
        self._emoji_btn.setIconSize(QSize(20, 20))
        self._emoji_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._emoji_btn.setToolTip(_tr("emoji 선택"))
        self._emoji_btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; border-radius: 16px; }"
            " QPushButton:hover { background-color: rgba(255,255,255,0.06); }"
        )
        self._emoji_btn.clicked.connect(self._on_emoji_clicked)  # type: ignore[arg-type]
        pill_layout.addWidget(self._emoji_btn)

        # text edit (pill 안 transparent + border 부재)
        self._text_edit = QTextEdit(self._pill)
        self._text_edit.setPlaceholderText(_tr("메시지"))
        self._text_edit.setFixedHeight(40)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text_edit.setFrameShape(QFrame.Shape.NoFrame)
        self._text_edit.setStyleSheet(
            "QTextEdit {"
            " background-color: transparent;"
            " border: none;"
            " padding: 8px 4px;"
            " color: #e5e7eb;"
            "}"
        )
        self._text_edit.installEventFilter(self)
        self._text_edit.textChanged.connect(self._on_text_changed)  # type: ignore[arg-type]
        self._text_edit.document().contentsChanged.connect(self._adjust_text_height)  # type: ignore[arg-type]
        pill_layout.addWidget(self._text_edit, stretch=1)

        # attach 의 의 pill 안 우측 inline
        self._attach_btn = QPushButton(self._pill)
        self._attach_btn.setFixedSize(32, 32)
        self._attach_btn.setIcon(load_icon("attach", size=20, color="#9ca3af"))
        self._attach_btn.setIconSize(QSize(20, 20))
        self._attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._attach_btn.setToolTip(_tr("파일 첨부"))
        self._attach_btn.setStyleSheet(
            "QPushButton { background-color: transparent; border: none; border-radius: 16px; }"
            " QPushButton:hover { background-color: rgba(255,255,255,0.06); }"
        )
        self._attach_btn.clicked.connect(self._on_attach_clicked)  # type: ignore[arg-type]
        pill_layout.addWidget(self._attach_btn)

        layout.addWidget(self._pill, stretch=1)

        # 외부 우측 circle button — voice (default) + send (text 있음 시 toggle)
        self._voice_btn = QPushButton(self)
        self._voice_btn.setFixedSize(40, 40)
        self._voice_btn.setIcon(load_icon("mic", size=22, color="#9ca3af"))
        self._voice_btn.setIconSize(QSize(22, 22))
        self._voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._voice_btn.setToolTip(_tr("음성 메시지"))
        self._voice_btn.setStyleSheet(
            "QPushButton { background-color: #1F2937; border: 1px solid #2c3a52; border-radius: 20px; }"
            " QPushButton:hover { background-color: #2c3a52; }"
        )
        self._voice_btn.clicked.connect(self._on_voice_clicked)  # type: ignore[arg-type]
        layout.addWidget(self._voice_btn)

        self._send_btn = QPushButton(self)
        self._send_btn.setFixedSize(40, 40)
        self._send_btn.setIcon(load_icon("send", size=20, color="#ffffff"))
        self._send_btn.setIconSize(QSize(20, 20))
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setToolTip(_tr("보내기 (Enter)"))
        self._send_btn.setStyleSheet(
            "QPushButton {"
            " background-color: #0066FF;"
            " border-radius: 20px;"
            " border: none;"
            "}"
            " QPushButton:hover { background-color: #1a75ff; }"
        )
        self._send_btn.clicked.connect(self._on_send_clicked)  # type: ignore[arg-type]
        self._send_btn.setVisible(False)
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
        cancel_btn = QPushButton("✕")
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

    def _on_text_changed(self) -> None:
        """cycle 169.137 — voice/send mutually exclusive toggle (telegram align).

        text 빈 = mic only / text 있음 = send only.
        """
        has_text = bool(self._text_edit.toPlainText().strip())
        self._voice_btn.setVisible(not has_text)
        self._send_btn.setVisible(has_text)

    def _adjust_text_height(self) -> None:
        """cycle 169.148 — text edit document height 기반 autoexpand (telegram align).

        single-row default 40px + multi-line 시점 content height + padding 6 (max 160).
        """
        doc = self._text_edit.document()
        h = int(doc.size().height()) + 16
        new_h = max(40, min(160, h))
        if self._text_edit.height() != new_h:
            self._text_edit.setFixedHeight(new_h)

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
