# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk Phase 5 cycle 139 — i18n runtime switch + .qm load 5 PASS.

본 test 의 cycle 132 (i18n base) + cycle 133 (.ts 5 locale) + cycle 134
(main_window binding) chain 직후 actual lrelease 의 산출 .qm 5 file 의
QTranslator 실측 load + tr() lookup + 5 locale 의 reload 검증.

5 test 구성:

- TestInstallQtTranslator : 2 (PyQt6 graceful + .qm 부재 graceful False)
- TestQTranslatorLoad     : 1 (5 locale × .qm load PASS)
- TestTrLookup            : 1 (en locale 의 tr("로그인") → "Login" 검증)
- TestReloadLocale        : 1 (en → ja switch 의 tr() 변경 검증)

PyQt6 부재 환경 시 module level skip — collection graceful.
.qm artifact 부재 (lrelease 미실행) 시 load test skip — CI graceful.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# 한글 주석 — headless 환경변수 의 offscreen platform 강제 (macOS/Linux CI 정합)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 한글 주석 — PyQt6 부재 시 본 test 모듈 전체 skip
pytest.importorskip("PyQt6")

from PyQt6.QtCore import QTranslator  # noqa: E402 — importorskip 직후 의무
from PyQt6.QtWidgets import QApplication  # noqa: E402

from app.i18n import (  # noqa: E402
    SUPPORTED_LOCALES,
    install_qt_translator,
    resolve_locale,
)

# 한글 주석 — .qm 산출 디렉토리 + 5 locale 의 정본 기준
QM_DIR = Path(__file__).resolve().parents[1].parent / "app" / "i18n" / "translations"
LOCALES = ("ko", "en", "zh-CN", "zh-TW", "ja")


@pytest.fixture(scope="module")
def qapp():
    """모듈 단위 단일 QApplication 인스턴스 — install_qt_translator 의 install 대상."""

    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    # 한글 주석 — 명시 close 생략 — 다른 module 재사용 허용


def _qm_path(locale: str) -> Path:
    """한글 주석 — locale → .qm 파일 절대경로 helper."""

    return QM_DIR / f"tootalk_{locale}.qm"


def _all_qm_present() -> bool:
    """한글 주석 — 5 locale 의 .qm 의 전수 존재 검증 helper."""

    return all(_qm_path(loc).is_file() for loc in LOCALES)


# ----------------------------------------------------------------------
# TestInstallQtTranslator — 2 PASS
# ----------------------------------------------------------------------


class TestInstallQtTranslator:
    """install_qt_translator 의 PyQt6 graceful + .qm 부재 graceful 의 2 path."""

    def test_install_returns_true_when_qm_present(self, qapp, tmp_path: Path) -> None:
        # 한글 주석 — .qm 산출 직후 install_qt_translator 의 True 반환
        if not _all_qm_present():
            pytest.skip("qm artifact 부재 — tools/i18n_compile.sh 실행 필요")
        result = install_qt_translator(qapp, locale="en")
        assert result is True, "install_qt_translator(en) True 기대"

    def test_install_returns_false_when_qm_missing(
        self, qapp, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # 한글 주석 — 부재 locale (fr) 의 graceful False 반환
        result = install_qt_translator(qapp, locale="fr")
        # 한글 주석 — resolve_locale 의 fallback ko 작동 시 ko qm 존재 → True 의 케이스 회피
        # install_qt_translator 의 locale 의 명시 전달 → fallback 미작동
        assert result is False, "install_qt_translator(fr) False 기대 (qm 부재)"


# ----------------------------------------------------------------------
# TestQTranslatorLoad — 1 PASS
# ----------------------------------------------------------------------


class TestQTranslatorLoad:
    """QTranslator 의 5 locale × .qm load 의 실측 검증."""

    @pytest.mark.parametrize("locale", LOCALES)
    def test_qtranslator_load_each_locale(self, locale: str) -> None:
        # 한글 주석 — 각 locale .qm 의 QTranslator.load() PASS 검증
        qm = _qm_path(locale)
        if not qm.is_file():
            pytest.skip(f"qm 부재 — {qm} (tools/i18n_compile.sh 실행 필요)")
        translator = QTranslator()
        loaded = translator.load(str(qm))
        assert loaded is True, f"{locale} qm load FAIL — {qm}"
        # 한글 주석 — load 직후 isEmpty 의 False 검증 (실제 entry 존재 의 sanity)
        assert not translator.isEmpty(), f"{locale} translator empty"


# ----------------------------------------------------------------------
# TestTrLookup — 1 PASS
# ----------------------------------------------------------------------


class TestTrLookup:
    """en locale 의 tr() lookup → 영문 매핑 검증."""

    def test_tr_login_en(self, qapp) -> None:
        # 한글 주석 — en .qm load 직후 qapp.translate() 의 "로그인" → "Login" 매핑
        qm = _qm_path("en")
        if not qm.is_file():
            pytest.skip(f"qm 부재 — {qm}")
        translator = QTranslator()
        assert translator.load(str(qm)), "en qm load FAIL"
        qapp.installTranslator(translator)
        try:
            # 한글 주석 — context = "MainWindow" (cycle 133 .ts 의 context name)
            translated = qapp.translate("MainWindow", "로그인")
            assert translated == "Login", f"tr(로그인) en = {translated!r} (기대 Login)"
        finally:
            # 한글 주석 — test teardown 의 translator remove (다음 test 의 격리)
            qapp.removeTranslator(translator)


# ----------------------------------------------------------------------
# TestReloadLocale — 1 PASS
# ----------------------------------------------------------------------


class TestReloadLocale:
    """en → ja switch 의 tr() 매핑 변경 검증 — runtime reload 의 sanity."""

    def test_switch_en_to_ja(self, qapp) -> None:
        # 한글 주석 — en load → ja load reload 의 tr() 매핑 변경
        en_qm = _qm_path("en")
        ja_qm = _qm_path("ja")
        if not (en_qm.is_file() and ja_qm.is_file()):
            pytest.skip("en/ja qm 부재 — tools/i18n_compile.sh 실행 필요")

        en_translator = QTranslator()
        assert en_translator.load(str(en_qm)), "en qm load FAIL"
        qapp.installTranslator(en_translator)
        en_text = qapp.translate("MainWindow", "보내기")

        # 한글 주석 — en remove 직후 ja install
        qapp.removeTranslator(en_translator)
        ja_translator = QTranslator()
        assert ja_translator.load(str(ja_qm)), "ja qm load FAIL"
        qapp.installTranslator(ja_translator)
        try:
            ja_text = qapp.translate("MainWindow", "보내기")
            assert en_text == "Send", f"en tr(보내기) = {en_text!r}"
            assert ja_text != en_text, "en → ja switch 의 tr() 동일 (reload FAIL)"
            assert "送" in ja_text or "送信" in ja_text or ja_text == "送信", (
                f"ja tr(보내기) = {ja_text!r} (送信 기대)"
            )
        finally:
            qapp.removeTranslator(ja_translator)


# ----------------------------------------------------------------------
# 모듈 검증 — SUPPORTED_LOCALES 의 5 locale × resolve_locale 의 sanity
# ----------------------------------------------------------------------


def test_supported_locales_match_qm_files() -> None:
    # 한글 주석 — SUPPORTED_LOCALES 의 5 entry 의 LOCALES 정합
    assert set(SUPPORTED_LOCALES) == set(LOCALES), (
        f"SUPPORTED_LOCALES 불일치 — got={SUPPORTED_LOCALES}, expected={LOCALES}"
    )
    # 한글 주석 — resolve_locale 의 fallback 함수 의 sanity (env 부재 ko)
    # monkeypatch 미사용 — 본 환경 LANG 의존 무관 default 의 None safe
    loc = resolve_locale()
    assert loc in SUPPORTED_LOCALES
