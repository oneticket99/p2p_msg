# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk Phase 5 cycle 144 — i18n production binding tr() wrap 검증 8 PASS.

본 test 의 cycle 132 (i18n base) + cycle 133 (.ts 5 locale × 20 entry) + cycle 134
(install_qt_translator binding) + cycle 139 (.qm compile + runtime switch) chain
직후 actual `app/ui/*.py` 5 file 의 hardcoded 한글 string 의 의
`QCoreApplication.translate("MainWindow", ...)` wrap 의 매핑 정합 검증.

8 test 구성:

- TestTrCallSites          : 5 (5 file × tr() call site count >= 1 의 정합)
- TestTrLookupMatchesTs    : 2 (en/ja locale 의 tr() 매핑 의 .ts 정합)
- TestConnectionStateLabel : 1 (chat_view.connection_state_label 의 3 state path)

PyQt6 부재 환경 의 module skip — collection graceful.
.qm artifact 부재 (lrelease 미실행) 환경 의 tr() lookup test 의 skip 의무.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

# 한글 주석 — headless 환경변수 의 offscreen platform 강제 (macOS/Linux CI 정합).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 한글 주석 — PyQt6 부재 시 본 test 모듈 전체 skip.
pytest.importorskip("PyQt6")

from PyQt6.QtCore import QCoreApplication, QTranslator  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

# 한글 주석 — 5 대상 .py file 의 절대 경로.
ROOT = Path(__file__).resolve().parents[2]
UI_DIR = ROOT / "app" / "ui"
TARGET_FILES = (
    UI_DIR / "login_dialog.py",
    UI_DIR / "signup_dialog.py",
    UI_DIR / "main_window.py",
    UI_DIR / "settings_dialog.py",
    UI_DIR / "chat_view.py",
)

# 한글 주석 — .qm 산출 디렉토리 (cycle 139 정합).
QM_DIR = ROOT / "app" / "i18n" / "translations"


# 한글 주석 — `_tr("...")` 또는 `QCoreApplication.translate("MainWindow", "...")`
# 두 패턴 의 tr() call site detect 정규식.
_TR_PATTERN = re.compile(
    r"""(_tr\(\s*["']([^"']+)["']\s*\))|"""
    r"""(QCoreApplication\.translate\(\s*["']MainWindow["']\s*,\s*["']([^"']+)["']\s*\))"""
)


def _count_tr_callsites(py_path: Path) -> tuple[int, list[str]]:
    """단일 .py 의 tr() call site count + source string list 반환."""

    source = py_path.read_text(encoding="utf-8")
    sources: list[str] = []
    for match in _TR_PATTERN.finditer(source):
        # 한글 주석 — group 2 = _tr() 의 source, group 4 = translate() 의 source.
        src = match.group(2) or match.group(4)
        if src:
            sources.append(src)
    return len(sources), sources


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    """모듈 단위 단일 QApplication — translator install 대상."""

    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    # 한글 주석 — teardown 생략 (다른 module 재사용 허용).


# ----------------------------------------------------------------------
# TestTrCallSites — 5 PASS (file 단위 tr() call site 의 count + 매핑)
# ----------------------------------------------------------------------


class TestTrCallSites:
    """5 file 의 tr() call site 의 의 count >= 1 + source string 의 .ts 정합."""

    @pytest.mark.parametrize(
        "py_path,expected_min,expected_subset",
        [
            (
                UI_DIR / "login_dialog.py",
                4,
                {"로그인", "비밀번호", "취소"},
            ),
            (
                UI_DIR / "signup_dialog.py",
                4,
                {"회원가입", "비밀번호", "확인"},
            ),
            (
                # cycle 169.578: main_window 책임 분리 후 (cycle 169.526~530) tr() callsite mixin file 분산.
                # main_window.py 잔존 = "보내기" (input_bar tooltip) 만. 의무 subset 의 mixin 안 retain.
                UI_DIR / "main_window.py",
                1,
                {"보내기"},
            ),
            (
                UI_DIR / "settings_dialog.py",
                2,
                {"설정", "메시지"},
            ),
            (
                UI_DIR / "chat_view.py",
                3,
                {"온라인", "오프라인", "연결 중"},
            ),
        ],
    )
    def test_file_tr_callsites(
        self,
        py_path: Path,
        expected_min: int,
        expected_subset: set[str],
    ) -> None:
        # 한글 주석 — 파일 존재 + tr() call site 의 count 의 lower bound + source subset 정합.
        assert py_path.is_file(), f"target file 부재 — {py_path}"
        count, sources = _count_tr_callsites(py_path)
        assert count >= expected_min, (
            f"{py_path.name} tr() {count} < expected_min={expected_min}"
        )
        source_set = set(sources)
        missing = expected_subset - source_set
        assert not missing, (
            f"{py_path.name} tr() source 누락 — missing={missing} got={source_set}"
        )


# ----------------------------------------------------------------------
# TestTrLookupMatchesTs — 2 PASS (en/ja locale 의 tr() 의 .ts 매핑 정합)
# ----------------------------------------------------------------------


def _qm_path(locale: str) -> Path:
    return QM_DIR / f"tootalk_{locale}.qm"


class TestTrLookupMatchesTs:
    """en/ja locale 의 tr() 의 실측 lookup 의 .ts 매핑 정합."""

    def test_tr_en_locale_login_and_send(self, qapp: QApplication) -> None:
        # 한글 주석 — en .qm load 직후 QCoreApplication.translate 의 tr() 의 매핑.
        qm = _qm_path("en")
        if not qm.is_file():
            pytest.skip(f"qm 부재 — {qm} (tools/i18n_compile.sh 실행 필요)")
        translator = QTranslator()
        assert translator.load(str(qm)), "en qm load FAIL"
        qapp.installTranslator(translator)
        try:
            login = QCoreApplication.translate("MainWindow", "로그인")
            send = QCoreApplication.translate("MainWindow", "보내기")
            settings = QCoreApplication.translate("MainWindow", "설정")
            assert login == "Login", f"en tr(로그인) = {login!r}"
            assert send == "Send", f"en tr(보내기) = {send!r}"
            assert settings == "Settings", f"en tr(설정) = {settings!r}"
        finally:
            qapp.removeTranslator(translator)

    def test_tr_ja_locale_password_and_cancel(self, qapp: QApplication) -> None:
        # 한글 주석 — ja .qm load 직후 패스워드 + 취소 의 tr() 의 매핑.
        qm = _qm_path("ja")
        if not qm.is_file():
            pytest.skip(f"qm 부재 — {qm}")
        translator = QTranslator()
        assert translator.load(str(qm)), "ja qm load FAIL"
        qapp.installTranslator(translator)
        try:
            password = QCoreApplication.translate("MainWindow", "비밀번호")
            cancel = QCoreApplication.translate("MainWindow", "취소")
            assert password == "パスワード", f"ja tr(비밀번호) = {password!r}"
            assert cancel == "キャンセル", f"ja tr(취소) = {cancel!r}"
        finally:
            qapp.removeTranslator(translator)


# ----------------------------------------------------------------------
# TestConnectionStateLabel — 1 PASS (chat_view helper 의 3 state path)
# ----------------------------------------------------------------------


class TestConnectionStateLabel:
    """chat_view.connection_state_label 의 3 state path 의 i18n 정합."""

    def test_connection_state_label_three_paths(self, qapp: QApplication) -> None:
        # 한글 주석 — en .qm load 직후 connection_state_label 의 3 state 매핑.
        from app.ui.chat_view import connection_state_label

        qm = _qm_path("en")
        if not qm.is_file():
            pytest.skip(f"qm 부재 — {qm}")
        translator = QTranslator()
        assert translator.load(str(qm)), "en qm load FAIL"
        qapp.installTranslator(translator)
        try:
            assert connection_state_label("online") == "Online"
            assert connection_state_label("offline") == "Offline"
            assert connection_state_label("connecting") == "Connecting"
            # 한글 주석 — unsupported state = raw passthrough.
            assert connection_state_label("unknown") == "unknown"
        finally:
            qapp.removeTranslator(translator)
