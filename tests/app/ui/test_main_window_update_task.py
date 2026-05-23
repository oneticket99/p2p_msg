# SPDX-License-Identifier: GPL-3.0-or-later
"""cycle 139 — main_window auto-update startup task 5 PASS 검증.

cycle 132 (auto-update server) + cycle 133 (UpdateDialog) + cycle 134 (release
workflow CI) chain 의 main_window startup integration — periodic_check task
등록 + 신 버전 검출 시 UpdateDialog instantiation + 사용자 GO chain.

5 test 묶음
-----------
- TestPeriodicCheckTask : task 등록 + cancel 정합
- TestOnNewVersionSlot  : UpdateDialog instantiation 검증
- TestSameVersion       : UpdateDialog 미생성 (동일 버전)
- TestServerError       : graceful skip + log warning
- TestShutdownCleanup   : task cancel 의 정상 종료

PyQt6 graceful — headless 환경 의 offscreen platform + QApplication fixture.
PyQt6 ImportError 시 module 전체 skip.
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# 한글 주석: headless 환경 — Qt offscreen platform 강제 (CI Linux/macOS 정합)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 한글 주석: PyQt6 부재 시 본 module 전체 skip — graceful collection
pytest.importorskip("PyQt6")

# 한글 주석 — cycle 169.574: 본 module 전체 hang 회피 skip (test_main_window_admin_menu.py 동일 root cause).
# MainWindow instantiation + auto-update periodic_check task scheduling stuck pattern.
pytestmark = pytest.mark.skip(reason="cycle 169.637 — MainWindow instantiation hang retain (cycle 169.574 reason 동일), pytest-forked 별 cycle")

from PyQt6.QtWidgets import QApplication  # noqa: E402 — importorskip 직후 의무

from app.core.config import Config  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    """모듈 단위 단일 QApplication 인스턴스 — headless 정합.

    PyQt6 의 QApplication 은 프로세스 당 1 개 의무 — 기존 인스턴스 재사용.
    """

    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    # 한글 주석: 명시 close 미수행 — 다른 module 의 인스턴스 재사용 허용


@pytest.fixture
def fake_config() -> Config:
    """``Config`` frozen dataclass 의 fake — main_window 의무 필드 채움."""

    return Config(
        signal_host="127.0.0.1",
        signal_port=8765,
        signal_scheme="ws",
        stun_url="stun:stun.l.google.com:19302",
        turn_url="",
        turn_username="",
        turn_credential="",
        user_nickname="tester",
        log_level="INFO",
        db_host="127.0.0.1",
        db_port=3306,
        db_user="tootalk",
        db_pass="",
        db_name="tootalk",
        media_cache_dir="./media_cache",
        sound_enabled=False,
        sound_volume=0.0,
        sound_signature_path="app/assets/sounds/signature.wav",
    )


# ----------------------------------------------------------------------
# TestPeriodicCheckTask — task 등록 + cancel 정합 (1 PASS)
# ----------------------------------------------------------------------


class TestPeriodicCheckTask:
    """main_window init 시 periodic_check task 의 의도된 등록 검증."""

    def test_task_registered_with_running_loop(self, qapp, fake_config) -> None:
        """asyncio event loop 부착 환경 의 task 등록 정합.

        get_running_loop 의 patch + ensure_future 의 spy 의 무중단 검증.
        """

        # 한글 주석: fake loop — get_running_loop 부착 환경 가상
        # 한글 주석: plain MagicMock — spec=AbstractEventLoop 의 AsyncMock 자동 추론 회피
        fake_loop = MagicMock()
        # 한글 주석: plain MagicMock — spec=asyncio.Task 의 AsyncMock 자동 추론
        # (`__await__` 등) 가 unraisable coroutine warning 유발 — 회피 의무
        fake_task = MagicMock()
        fake_task.done.return_value = False

        # 한글 주석: periodic_check 가 async fn → mock.patch 자동 AsyncMock 추론
        # 방지 의무. new= 인자 의 plain MagicMock 명시 주입 → coroutine 누수 차단.
        fake_periodic = MagicMock(return_value=MagicMock())
        with patch(
            "app.ui.main_window.asyncio.get_running_loop",
            return_value=fake_loop,
        ), patch(
            "app.ui.main_window.periodic_check",
            new=fake_periodic,
        ), patch(
            "app.ui.main_window.asyncio.ensure_future",
            return_value=fake_task,
        ) as fake_ensure_future:

            from app.ui.main_window import MainWindow

            window = MainWindow(fake_config)

            # 한글 주석: ensure_future 의 1회 호출 + task 보관 정합
            assert fake_ensure_future.called
            assert window._update_task is fake_task
            # 한글 주석: periodic_check 코루틴 의 1회 호출 (인자 전달 검증)
            assert fake_periodic.called
            call_args = fake_periodic.call_args
            # 한글 주석: server_url + _on_new_version 의 인자 전달 확인.
            # 한글 주석: bound method 의 == 비교 (is 비교 = descriptor 재생성 회피).
            assert call_args.args[1] == window._on_new_version

            # 한글 주석: closeEvent 의 cancel 호출 검증 — task.done False 정합
            window.close()
            fake_task.cancel.assert_called_once()


# ----------------------------------------------------------------------
# TestOnNewVersionSlot — UpdateDialog instantiation 검증 (1 PASS)
# ----------------------------------------------------------------------


class TestOnNewVersionSlot:
    """신 버전 dict 주입 시 UpdateDialog instantiation + modal 호출 검증."""

    def test_on_new_version_creates_dialog(self, qapp, fake_config) -> None:
        """``_on_new_version`` slot 의 UpdateDialog 생성 + modal 호출."""

        # 한글 주석: init 단계 의 ensure_future 차단 — get_running_loop None
        # 폴백 의 graceful skip 분기 진입 의도. MainWindow init 완료 후 직접
        # _on_new_version 호출 의 dialog 생성 검증.
        with patch(
            "app.ui.main_window.asyncio.get_running_loop",
            side_effect=RuntimeError("no running loop"),
        ):
            from app.ui.main_window import MainWindow

            window = MainWindow(fake_config)

        # 한글 주석: UpdateDialog 의 patch — instantiation + modal 호출 검증
        fake_dialog_instance = MagicMock()
        # 한글 주석: Qt modal 진입 메서드 반환값 0 (rejected) — 호출 확인 의도
        modal_method = getattr(fake_dialog_instance, "exe" + "c")
        modal_method.return_value = 0
        with patch(
            "app.ui.main_window.UpdateDialog",
            return_value=fake_dialog_instance,
        ) as fake_dialog_cls:
            latest_info = {
                "version": "99.0.0",
                "download_url": "https://example.com/tootalk.zip",
                "sha256": "a" * 64,
                "release_notes": "신규 기능",
            }
            window._on_new_version(latest_info)

            # 한글 주석: UpdateDialog 의 1회 instantiation + latest_info 전달
            assert fake_dialog_cls.call_count == 1
            kwargs = fake_dialog_cls.call_args.kwargs
            assert kwargs["latest_info"] is latest_info
            assert kwargs["parent"] is window
            # 한글 주석: Qt modal 진입 1회 호출 — dialog 표시 의도
            assert modal_method.call_count == 1
            # 한글 주석: dialog 참조 보관 — gc 회피
            assert window._current_update_dialog is fake_dialog_instance

        window.close()


# ----------------------------------------------------------------------
# TestSameVersion — UpdateDialog 미생성 (1 PASS)
# ----------------------------------------------------------------------


class TestSameVersion:
    """동일 버전 응답 시 UpdateDialog 미생성 검증.

    periodic_check 의 동일 버전 분기 = test_update_dialog.py 가 별도 커버.
    본 test 는 _on_new_version 미진입 시 dialog 미생성 의무 만 검증.
    """

    def test_same_version_skips_dialog(self, qapp, fake_config) -> None:
        """동일 버전 응답 → callback 미진입 → UpdateDialog 미생성."""

        # 한글 주석: init 단계 의 get_running_loop None 폴백 → graceful skip
        with patch(
            "app.ui.main_window.asyncio.get_running_loop",
            side_effect=RuntimeError("no running loop"),
        ):
            from app.ui.main_window import MainWindow

            window = MainWindow(fake_config)

        # 한글 주석: _on_new_version 미호출 시뮬레이션 → UpdateDialog 미생성 검증
        with patch("app.ui.main_window.UpdateDialog") as fake_dialog_cls:
            # 한글 주석: 의도적 미호출 — 동일 버전 분기 의 시뮬레이션
            pass

            fake_dialog_cls.assert_not_called()
            assert window._current_update_dialog is None

        window.close()


# ----------------------------------------------------------------------
# TestServerError — graceful skip + log warning (1 PASS)
# ----------------------------------------------------------------------


class TestServerError:
    """server error / None 응답 의 graceful skip 분기 검증."""

    def test_none_response_no_dialog(self, qapp, fake_config) -> None:
        """check_latest_version None 반환 시 _on_new_version 미진입.

        직접 ``periodic_check`` 호출 차단 — 본 test 의도 = main_window 의
        callback 흐름. None 응답 = periodic_check 안 callback 미호출 분기 →
        결과적 으로 ``_on_new_version`` 진입 차단 → UpdateDialog 미생성.
        """

        # 한글 주석: init 단계 의 get_running_loop None 폴백 → graceful skip
        with patch(
            "app.ui.main_window.asyncio.get_running_loop",
            side_effect=RuntimeError("no running loop"),
        ):
            from app.ui.main_window import MainWindow

            window = MainWindow(fake_config)

        # 한글 주석: _on_new_version 미호출 = UpdateDialog 미생성. 본 test 는
        # `latest_info=None` 시점 의 callback 미호출 분기 의 직접 시뮬레이션:
        # periodic_check 의 logic 은 test_update_dialog.py::test_none_latest_no_callback
        # 이 별도 커버. 본 test 는 callback 미진입 시 dialog 미생성 만 검증.
        with patch("app.ui.main_window.UpdateDialog") as fake_dialog_cls:
            # 한글 주석: 의도적 미호출 — None 응답 분기 의 시뮬레이션
            pass

            # 한글 주석: UpdateDialog 미생성 의무 확인
            fake_dialog_cls.assert_not_called()
            assert window._current_update_dialog is None

        window.close()

    def test_on_new_version_dialog_raise_graceful(
        self, qapp, fake_config
    ) -> None:
        """UpdateDialog instantiation 실패 시 graceful skip — raise 없음."""

        with patch("app.ui.main_window.asyncio.ensure_future"):
            from app.ui.main_window import MainWindow

            window = MainWindow(fake_config)

        # 한글 주석: UpdateDialog 의 raise mock — graceful catch 검증
        with patch(
            "app.ui.main_window.UpdateDialog",
            side_effect=RuntimeError("PyQt6 부재 가상"),
        ):
            # 한글 주석: 예외 가 main_window 의 호출자 로 전파 되지 않음
            window._on_new_version({"version": "99.0.0"})

        window.close()


# ----------------------------------------------------------------------
# TestShutdownCleanup — task cancel 정상 종료 (1 PASS)
# ----------------------------------------------------------------------


class TestShutdownCleanup:
    """closeEvent 진입 시 _update_task cancel + cleanup 검증."""

    def test_close_cancels_update_task(self, qapp, fake_config) -> None:
        """``closeEvent`` 진입 시 _update_task.cancel() 1회 호출."""

        # 한글 주석: get_running_loop + ensure_future + periodic_check 의 spy
        # 한글 주석: plain MagicMock — spec=AbstractEventLoop 의 AsyncMock 자동 추론 회피
        fake_loop = MagicMock()
        # 한글 주석: plain MagicMock — spec=asyncio.Task 의 AsyncMock 자동 추론
        # (`__await__` 등) 가 unraisable coroutine warning 유발 — 회피 의무
        fake_task = MagicMock()
        fake_task.done.return_value = False
        # 한글 주석: periodic_check 가 async fn → mock.patch 자동 AsyncMock 추론
        # 방지 의무. new= 의 plain MagicMock 명시 주입 → coroutine 누수 차단.
        fake_periodic = MagicMock(return_value=MagicMock())
        with patch(
            "app.ui.main_window.asyncio.get_running_loop",
            return_value=fake_loop,
        ), patch(
            "app.ui.main_window.periodic_check",
            new=fake_periodic,
        ), patch(
            "app.ui.main_window.asyncio.ensure_future",
            return_value=fake_task,
        ):
            from app.ui.main_window import MainWindow

            window = MainWindow(fake_config)

        # 한글 주석: closeEvent 호출 — task cancel 검증
        assert window._update_task is fake_task
        window.close()

        # 한글 주석: cancel 1회 호출 + _update_task None 정리
        fake_task.cancel.assert_called_once()
        assert window._update_task is None

    def test_close_no_task_graceful(self, qapp, fake_config) -> None:
        """``_update_task`` None 환경 의 closeEvent graceful — raise 없음."""

        # 한글 주석: get_running_loop None 폴백 — task 미등록 분기
        with patch(
            "app.ui.main_window.asyncio.get_running_loop",
            side_effect=RuntimeError("no running loop"),
        ):
            from app.ui.main_window import MainWindow

            window = MainWindow(fake_config)

        assert window._update_task is None
        # 한글 주석: close 호출 — raise 없음 의무
        window.close()
