# SPDX-License-Identifier: GPL-3.0-or-later
"""tests/app/ui 의 단일 진입 fixture — cycle 169.601 신설 — fixture hang root cause 회수.

cycle 169.585 의 ci.yml `--ignore=tests/app/ui` 의 fixture chain hang root
cause = qapp fixture scope=module 안 QTimer.singleShot(0) callback delivery
overhead + 다른 module 의 leftover event 누적 (cycle 169.580 standalone PASS
하지만 fixture chain stuck).

본 conftest = session-scope 단일 qapp + 매 test 종료 시점 processEvents flush
chain 의 hang 회수.
"""

from __future__ import annotations

import os
import sys

import pytest

# 한글 주석 — headless 의무 — Qt offscreen platform (CI Linux/macOS 정합)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    """세션 1개 단일 QApplication — PyQt6 의 process 안 1개 의무 정합.

    cycle 169.601 — module-scope 의 multi-instance 누적 폐기 + session-scope retain.
    """

    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        pytest.skip("PyQt6 미설치 — tests/app/ui skip")
    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    # 한글 주석 — session 끝 시점 명시 close 미수행 (cleanup 안 leftover event chain 회피)


@pytest.fixture(autouse=True)
def _flush_events(qapp):
    """매 test 종료 시점 processEvents flush — QTimer.singleShot(0) callback chain 소비."""

    yield
    try:
        qapp.processEvents()
    except Exception:
        pass
