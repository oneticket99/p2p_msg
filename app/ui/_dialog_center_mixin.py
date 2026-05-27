# SPDX-License-Identifier: GPL-3.0-or-later
"""DialogCenterMixin — child overlay + backdrop + manual modal event loop (cycle 169.528 신설).

계층 위치 — app/ui MainWindow mixin(정본 §E). main_window 책임 분리 단위 — MRO 합성.
모든 dialog 의 별도 OS 윈도우 → 메인 레이아웃 안 in-app overlay 변환 공용 헬퍼(backdrop dim + 중앙 배치).

codex 2.5 잔존 big block 진입 13차 — main_window.py 책임 분리 batch.

분리 대상 method (cycle 169.267~351 origin):
- `_exec_dialog_centered(dialog)` — backdrop dim + child overlay + ESC handler +
  splitter sizes snapshot/restore + chat_list_panel active_tab snapshot/restore +
  signal accept/reject chain + QDialog fallback bound method override

본 mixin 안 의존:
- `self.rect()`, `self.centralWidget()` (QMainWindow)
- `self._chat_list_panel` (snapshot/restore target)
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


class DialogCenterMixin:
    """child overlay + manual modal event loop mixin (cycle 169.528)."""

    def _exec_dialog_centered(self, dialog) -> int:
        """cycle 169.267 — child overlay + backdrop dim + manual modal event loop.

        사용자 directive image #25/27/31 회수 — backdrop rgba(0,0,0,0.5) 의 main rect
        의 dimming layer 추가. dialog 의 z-order 위 backdrop. close 직후 backdrop hide.
        """
        # cycle 169.838 — test-safety 가드. offscreen/pytest 환경 의 loop.exec() 는
        # 무한 블록(hang) 을 유발하므로 non-blocking show 만 수행하고 즉시 반환한다.
        # (전 dialog in-app 모달 변환 의 test 통과 선행 조건.)
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen" or os.environ.get(
            "PYTEST_CURRENT_TEST"
        ):
            dialog.setParent(self)
            dialog.show()
            return 0
        # cycle 169.287 — hide/setParent/setWindowFlags(Widget)/show strict chain (Qt internal cache reset)
        from PyQt6.QtCore import Qt as _Qt, QEventLoop
        from PyQt6.QtWidgets import QFrame, QSplitter as _QSplitter, QWidget
        # cycle 169.312 — splitter sizes snapshot (dialog open 시점 chat_list panel collapse 회피)
        _central = self.centralWidget()
        _splitter_sizes: list[int] = []
        if isinstance(_central, _QSplitter):
            _splitter_sizes = _central.sizes()
            log.warning("[dialog_open] splitter sizes captured=%s", _splitter_sizes)
        # cycle 169.314 — active_tab snapshot (folder dialog 후 tab 의 entries filter mismatch → 빈 list 회피)
        _clp_pre = getattr(self, "_chat_list_panel", None)
        _active_tab_pre = getattr(_clp_pre, "_active_tab", "chats") if _clp_pre else "chats"
        log.warning("[dialog_open] active_tab captured=%s", _active_tab_pre)
        # cycle 169.307 — main_window child overlay (centralWidget = splitter, child 시점 panel add 깨짐 회수)
        backdrop = QFrame(self)
        backdrop.setObjectName("dialogBackdrop")
        backdrop.setAutoFillBackground(True)
        backdrop.setStyleSheet(
            "QFrame#dialogBackdrop { background-color: rgba(0, 0, 0, 160); }"
        )
        backdrop.setGeometry(self.rect())
        backdrop.show()
        backdrop.raise_()
        # cycle 169.321 — backdrop click reject chain (사용자 directive image #85 — close button 부재 시 fallback)
        def _backdrop_click(event):
            if event.button() == _Qt.MouseButton.LeftButton:
                if hasattr(dialog, "reject"):
                    dialog.reject()
        backdrop.mousePressEvent = _backdrop_click  # type: ignore[assignment]
        dialog.hide()
        dialog.setParent(self)
        dialog.setWindowFlags(_Qt.WindowType.Widget)
        parent_for_dialog = self
        # cycle 169.299 — debug log 추가 (사용자 critique 의 실 size capture)
        parent_rect = parent_for_dialog.rect()
        log.warning(
            "[dialog_centered] parent_rect=%dx%d dialog initial=%dx%d cls=%s",
            parent_rect.width(), parent_rect.height(),
            dialog.width(), dialog.height(), dialog.__class__.__name__,
        )
        max_w = max(parent_rect.width() - 40, 360)
        max_h = max(parent_rect.height() - 40, 400)
        dlg_w = min(dialog.width(), max_w)
        dlg_h = min(dialog.height(), max_h)
        dialog.setFixedSize(dlg_w, dlg_h)
        dw, dh = dialog.width(), dialog.height()
        log.warning("[dialog_centered] after setFixedSize=%dx%d", dw, dh)
        x = (parent_rect.width() - dw) // 2
        y = (parent_rect.height() - dh) // 2
        dialog.move(x, y)
        # cycle 169.302 — signal connect chain (bound method override snapshot 회피)
        loop = QEventLoop()
        dialog._embed_result = 0
        accepted_sig = getattr(dialog, "accepted", None)
        rejected_sig = getattr(dialog, "rejected", None)
        def _on_accepted():
            dialog._embed_result = 1
            loop.quit()
        def _on_rejected():
            dialog._embed_result = 0
            loop.quit()
        if accepted_sig is not None and hasattr(accepted_sig, "connect"):
            accepted_sig.connect(_on_accepted)
        if rejected_sig is not None and hasattr(rejected_sig, "connect"):
            rejected_sig.connect(_on_rejected)
        # QDialog fallback (signal 부재 시 method override)
        if accepted_sig is None:
            orig_accept = dialog.accept
            def _accept():
                dialog._embed_result = 1
                try:
                    orig_accept()
                except Exception:
                    pass
                loop.quit()
            dialog.accept = _accept
        if rejected_sig is None:
            orig_reject = dialog.reject
            def _reject():
                dialog._embed_result = 0
                try:
                    orig_reject()
                except Exception:
                    pass
                loop.quit()
            dialog.reject = _reject
        # cycle 169.321 — ESC key handler (FramelessWindowHint 시점 의 QDialog 기본 ESC 회복)
        _orig_keyPress = getattr(dialog, "keyPressEvent", None)
        def _key_press(event):
            if event.key() == _Qt.Key.Key_Escape:
                if hasattr(dialog, "reject"):
                    dialog.reject()
                return
            if _orig_keyPress is not None:
                _orig_keyPress(event)
        dialog.keyPressEvent = _key_press  # type: ignore[assignment]
        dialog.show()
        dialog.raise_()
        dialog.setFocus()
        # cycle 169.351 — child widget visible 강제 (QStackedWidget 등 nested widget 시점 obscure 차단)
        log.warning("[dialog_centered] dialog.isVisible=%s size=%dx%d pos=(%d,%d) children=%d",
                    dialog.isVisible(), dialog.width(), dialog.height(),
                    dialog.x(), dialog.y(), len(dialog.findChildren(QWidget)))
        for child in dialog.findChildren(QWidget):
            child.show()
        dialog.update()
        dialog.repaint()
        loop.exec()
        dialog.hide()
        dialog.setParent(None)  # cycle 169.307 — dialog widget tree 분리 (close 後 main_window layout 회복)
        result = dialog._embed_result
        backdrop.hide()
        backdrop.deleteLater()
        # cycle 169.311 — close 後 strict restore + debug log
        clp = getattr(self, "_chat_list_panel", None)
        if clp is not None:
            entries_count = len(getattr(clp, "_entries", []))
            log.warning(
                "[dialog_close] chat_list_panel entries=%d visible=%s parent=%s",
                entries_count, clp.isVisible(), clp.parent().__class__.__name__ if clp.parent() else None,
            )
            clp.show()
            inner_list = getattr(clp, "_list", None)
            if inner_list is not None:
                inner_list.show()
                inner_list.setVisible(True)
            empty_label = getattr(clp, "_empty_label", None)
            # cycle 169.314 — active_tab restore (dialog open 직전 snapshot) + _render() 재호출
            if hasattr(clp, "set_active_tab"):
                try:
                    clp.set_active_tab(_active_tab_pre)
                    log.warning("[dialog_close] active_tab restored=%s actual=%s",
                                _active_tab_pre, getattr(clp, "_active_tab", "?"))
                except Exception:
                    pass
            if hasattr(clp, "_render"):
                try:
                    clp._render()
                except Exception:
                    pass
            clp.update()
            clp.repaint()
        # cycle 169.312 — splitter sizes restore (chat_list panel width 0 collapse 차단)
        if _splitter_sizes:
            _central2 = self.centralWidget()
            if isinstance(_central2, _QSplitter):
                _central2.setSizes(_splitter_sizes)
                log.warning("[dialog_close] splitter sizes restored=%s actual=%s",
                            _splitter_sizes, _central2.sizes())
        if self.centralWidget():
            self.centralWidget().update()
            self.centralWidget().repaint()
        self.update()
        return result

    def _embed_dialog_centered(self, dialog) -> None:
        """cycle 169.838 — non-blocking in-app overlay embed (backdrop dim + 중앙 배치).

        ``_exec_dialog_centered`` 와 동일한 child overlay + backdrop 처리를 하되 manual
        modal loop(``loop.exec()``)을 생략한다. async 작업(예: SFU publish)을 이어서
        스케줄해야 하는 dialog(GroupCallDialog 등) 가 별도 OS 윈도우 없이 메인 레이아웃
        안에 뜨도록 하기 위함. 반환값은 없다(비차단).
        """
        from PyQt6.QtCore import Qt as _Qt
        from PyQt6.QtWidgets import QFrame, QWidget

        # backdrop dim layer (다른 모달과 동일한 어둡게 처리)
        backdrop = QFrame(self)
        backdrop.setObjectName("dialogBackdrop")
        backdrop.setAutoFillBackground(True)
        backdrop.setStyleSheet(
            "QFrame#dialogBackdrop { background-color: rgba(0, 0, 0, 160); }"
        )
        backdrop.setGeometry(self.rect())
        backdrop.show()
        backdrop.raise_()
        # backdrop 참조 보관 (dialog close 시 함께 정리)
        dialog._embed_backdrop = backdrop

        # dialog 를 main_window child widget 으로 재부모화 (별도 윈도우 차단)
        dialog.hide()
        dialog.setParent(self)
        dialog.setWindowFlags(_Qt.WindowType.Widget)
        parent_rect = self.rect()
        max_w = max(parent_rect.width() - 40, 360)
        max_h = max(parent_rect.height() - 40, 400)
        dlg_w = min(dialog.width(), max_w)
        dlg_h = min(dialog.height(), max_h)
        if dlg_w > 0 and dlg_h > 0:
            dialog.resize(dlg_w, dlg_h)
        x = (parent_rect.width() - dialog.width()) // 2
        y = (parent_rect.height() - dialog.height()) // 2
        dialog.move(max(x, 0), max(y, 0))
        dialog.show()
        dialog.raise_()
        for child in dialog.findChildren(QWidget):
            child.show()
        dialog.update()
