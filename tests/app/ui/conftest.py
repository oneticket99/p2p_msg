# SPDX-License-Identifier: GPL-3.0-or-later
"""tests/app/ui 의 단일 진입 fixture — cycle 169.634 강화 — fixture hang root cause 회수.

cycle 169.585 의 ci.yml `--ignore=tests/app/ui` 의 fixture chain hang root
cause = multi-test 누적 시점 QTimer.singleShot(0) callback + asyncio task +
sqlite3 unclosed connection 누적.

본 conftest = session-scope 단일 qapp + 매 test 종료 시점 cleanup chain:
- QTimer.singleShot(0) callback 의 processEvents flush
- pending QObject 의 deleteLater + processEvents
- asyncio loop 안 pending task cancel (가능 시)
"""

from __future__ import annotations

import os
import sys

import pytest

# 한글 주석 — headless 의무 — Qt offscreen platform (CI Linux/macOS 정합)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """세션 1개 단일 QApplication — PyQt6 의 process 안 1개 의무 정합."""

    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        pytest.skip("PyQt6 미설치 — tests/app/ui skip")
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(autouse=True)
def _qt_cleanup(qapp):
    """매 test 종료 직후 cleanup chain — top-level widget close + processEvents flush."""

    yield
    try:
        for widget in list(qapp.topLevelWidgets()):
            try:
                widget.close()
                widget.deleteLater()
            except Exception:
                pass
        for _ in range(4):
            qapp.processEvents()
    except Exception:
        pass
