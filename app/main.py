"""TooTalk PyQt6 클라이언트 진입점 — qasync 통합 이벤트 루프 부트스트랩.

본 모듈은 다음 순서로 애플리케이션을 기동한다.

1. ``app.core.config`` 가 ``.env`` 로딩 후 ``Config`` 인스턴스 반환
2. ``logging`` 포맷터를 ``[YYYY-mm-dd H:i:s]`` 형식으로 설정 (정본 §E)
3. ``QApplication`` 생성 후 ``qasync.QEventLoop`` 을 단일 asyncio 이벤트
   루프로 채택하여 Qt 시그널과 비동기 코루틴을 동일 스레드에서 운용
4. ``MainWindow`` 표시 후 ``loop.run_forever()`` 로 진입

비동기 전용 규약(정본 §E): Qt slot 내부 동기 코드는 허용되나 IO 가 필요한
경우 반드시 ``asyncio.create_task`` 또는 ``asyncio.ensure_future`` 로
코루틴을 예약해야 한다. ``time.sleep`` 등 블로킹 IO 금지.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

import qasync
from PyQt6.QtWidgets import QApplication

from app.core.config import Config, load_config
from app.i18n import install_qt_translator, resolve_locale
from app.net.auth_client import AuthClient
from app.ui.login_dialog import LoginDialog
from app.ui.main_window import MainWindow
from app.ui.signup_dialog import SignupDialog


def _configure_logging(level: str) -> None:
    """루트 로거 포맷 통일.

    정본 §E 규약: 로그 형식 ``[YYYY-mm-dd H:i:s]``. ``datefmt`` 에 24시간
    표기 사용. 이미 핸들러가 붙어 있으면 중복 추가하지 않는다.
    """

    # 동일 프로세스 안에서 main() 이 두 번 호출돼도 핸들러가 누적되지
    # 않도록 기존 핸들러를 제거한 뒤 재설정한다.
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def main() -> int:
    """애플리케이션 메인 — QApplication + qasync.QEventLoop 진입.

    Returns
    -------
    int
        프로세스 종료 코드. ``loop.run_forever()`` 는 일반적으로 None 을
        반환하므로 호출 지점에서 ``or 0`` 으로 보정한다.
    """

    # 1) 환경변수 로딩 (.env → Config dataclass)
    config: Config = load_config()

    # 2) 로깅 포맷 통일
    _configure_logging(config.log_level)
    log = logging.getLogger(__name__)
    log.info("TooTalk 클라이언트 기동 — signaling=%s", config.signaling_url)

    # 3) QApplication + qasync 이벤트 루프 결합
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("TooTalk")
    qt_app.setOrganizationName("TooTalk")

    # 3-0) Toonation BI 통합 theme load — cycle 153 phase 1 (FRONTEND.md §15 정합)
    # 한글 주석 — persist preference 우선 + base-dark.qss 적용 + palette auto-detect
    try:
        from app.ui.theme import load_theme
        try:
            from app.config.user_preferences import load_user_theme_preference
            chosen_theme = load_user_theme_preference()
        except Exception:  # pragma: no cover - graceful
            chosen_theme = "auto"
        load_theme(qt_app, theme=chosen_theme)  # type: ignore[arg-type]
    except Exception as theme_exc:  # pragma: no cover - graceful 부재
        log.debug("theme load 실패 graceful — %r", theme_exc)

    # 3-1) i18n QTranslator 부착 — Phase 5 cycle 134 actual binding
    # 한글 주석 — UserLocalePreferences 의 persist locale 우선, 부재 시 env LOCALE/LANG → resolve_locale fallback
    try:
        from app.config.user_preferences import load_user_locale_preferences
        locale_pref = load_user_locale_preferences()
        chosen_locale = locale_pref.locale
    except Exception as locale_exc:  # pragma: no cover - 의존 부재 graceful
        log.debug("locale pref 로딩 실패 — env fallback (%r)", locale_exc)
        chosen_locale = resolve_locale()
    installed = install_qt_translator(qt_app, locale=chosen_locale)
    log.info("i18n QTranslator — locale=%s installed=%s", chosen_locale, installed)

    loop = qasync.QEventLoop(qt_app)
    asyncio.set_event_loop(loop)

    # 4) AuthClient 초기화 — REST endpoint base URL
    # cycle 169.35 회수 — signaling_url (ws://:8765) ≠ REST endpoint (https://:443)
    # TOOTALK_API_BASE env 우선 + 부재 시 signaling_url 변환 fallback (개발 환경 만)
    api_base = os.environ.get("TOOTALK_API_BASE")
    if not api_base:
        api_base = config.signaling_url.replace("ws://", "http://").replace("wss://", "https://").removesuffix("/ws")
    auth_client = AuthClient(api_base)

    # cycle 160 — ReactionsClient instantiate (graceful httpx 부재)
    reactions_client = None
    try:
        from app.net.reactions_client import ReactionsClient
        reactions_client = ReactionsClient(base_url=api_base)
    except (ImportError, RuntimeError) as exc:  # pragma: no cover - graceful
        logging.getLogger(__name__).debug("ReactionsClient 부재 graceful — %r", exc)

    # 한글 주석 — cycle 169.28 회수 — qasync loop context 안 모든 dialog + MainWindow 의무
    # 직전 chain 안 dialog.exec() 호출 시점 = loop not running →
    # asyncio.get_running_loop() RuntimeError 'no running event loop' (aiohttp ClientSession.__init__ fail)
    # `with loop:` block 안 dialog.exec() = qasync 의 nested Qt + asyncio loop 동시 활성
    auth_required = os.environ.get("AUTH_REQUIRED", "1") == "1"
    skip_welcome = os.environ.get("SKIP_WELCOME", "0") == "1"

    with loop:
        if auth_required:
            # 5-1) WelcomeDialog 진입
            if not skip_welcome:
                from app.ui.welcome_dialog import WelcomeDialog
                welcome = WelcomeDialog()
                if welcome.exec() != welcome.DialogCode.Accepted:
                    logging.getLogger(__name__).info("WelcomeDialog 취소 — 종료")
                    loop.run_until_complete(auth_client.close())
                    return 0

            # 5-2) LoginDialog ↔ SignupDialog switch chain (cycle 169.53 회수)
            # 한글 주석 — 무한 switch loop — login done(2) → signup, signup done(3) → login.
            # 사용자 비판 "로그인 버튼 누르면 엡 종료" 회수 + cancel 만 종료.
            authenticated = False
            current_dialog = "login"
            while not authenticated:
                if current_dialog == "login":
                    login = LoginDialog(auth_client=auth_client)
                    login_result = login.exec()
                    if login_result == 2:
                        current_dialog = "signup"
                        continue
                    if login_result != login.DialogCode.Accepted:
                        logging.getLogger(__name__).info("LoginDialog 취소 — 종료")
                        loop.run_until_complete(auth_client.close())
                        return 0
                    authenticated = True
                else:  # signup
                    signup = SignupDialog(auth_client=auth_client)
                    signup_result = signup.exec()
                    if signup_result == 3:
                        current_dialog = "login"
                        continue
                    if signup_result != signup.DialogCode.Accepted:
                        logging.getLogger(__name__).info("SignupDialog 취소 — 종료")
                        loop.run_until_complete(auth_client.close())
                        return 0
                    authenticated = True

        # 6) MainWindow 표시
        window = MainWindow(
            config=config,
            auth_client=auth_client,
            reactions_client=reactions_client,
        )
        window.show()

        # 7) qasync loop run_forever — Qt + asyncio 단일 thread 통합
        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(auth_client.close())
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
