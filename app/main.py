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
from typing import Optional

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
    # cycle 169.359 — labels singleton global state 갱신 (사용자 directive — 각 언어 클릭 시점 singleton)
    try:
        from app.i18n.labels import set_locale as _labels_set_locale
        _labels_set_locale(chosen_locale)
        log.info("[i18n] labels singleton _CURRENT_LOCALE → %s", chosen_locale)
    except Exception as labels_exc:
        log.debug("labels set_locale graceful skip — %r", labels_exc)
    log.info("i18n QTranslator — locale=%s installed=%s", chosen_locale, installed)

    loop = qasync.QEventLoop(qt_app)
    asyncio.set_event_loop(loop)

    # 4) AuthClient 초기화 — REST endpoint base URL
    # cycle 169.817 — REST API base = Config.api_base single source (auth/rooms/friends/bot/contacts mixin 공통).
    # 데모 = signaling 동일 8765 http 직결 (직전 nginx 443 https default 가 upstream 502 → 회수).
    # 7 client + mixin getattr(self._config, "api_base") 모두 동일 base 로 정합. TOOTALK_API_BASE env override.
    api_base = config.api_base
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
    # 한글 주석 — cycle 169.615: NFR-03 cold start probe 활성 시 auth/welcome dialog skip
    # (offscreen 안 modal exec stuck 회피). probe 의 목표 = window.show() 도달 시점 측정.
    if os.environ.get("TOOTALK_COLD_START_PROBE") == "1":
        auth_required = False
        skip_welcome = True

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
            authenticated = False
            current_dialog = "login"
            session_token: Optional[str] = None
            session_user_id: Optional[int] = None
            session_email: Optional[str] = None
            while not authenticated:
                if current_dialog == "login":
                    login = LoginDialog(auth_client=auth_client)
                    login_result = login.exec()
                    if login_result == 2:
                        current_dialog = "signup"
                        continue
                    if login_result == 3:
                        # cycle 169.410 — 아이디 찾기 dialog 진입 후 login 복귀
                        from app.ui.find_id_dialog import FindIdDialog
                        find_dialog = FindIdDialog(base_url=api_base)
                        find_dialog.exec()
                        current_dialog = "login"
                        continue
                    if login_result == 4:
                        # cycle 169.410 — 비밀번호 찾기 dialog 진입 후 login 복귀
                        from app.ui.password_reset_dialog import PasswordResetDialog
                        reset_dialog = PasswordResetDialog(auth_client=auth_client)
                        reset_dialog.exec()
                        current_dialog = "login"
                        continue
                    if login_result != login.DialogCode.Accepted:
                        logging.getLogger(__name__).info("LoginDialog 취소 — 종료")
                        loop.run_until_complete(auth_client.close())
                        return 0
                    session_token = login.token
                    session_user_id = login.user_id
                    session_email = login.email
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
                    # 한글 주석 — cycle 169.54 회수 — signup OTP PASS 직후 자동 로그인 session
                    session_token = signup.token
                    session_user_id = signup.user_id
                    authenticated = True

            logging.getLogger(__name__).info(
                "[auth] PASS user_id=%s token_set=%s", session_user_id, bool(session_token)
            )

        # 6) FriendsClient instantiate (cycle 169.494 — main_window 주입 부재 회수)
        # 한글 주석 — 친구 검색 dialog `_on_friend_search_requested` 안 friends_client None 분기 회수.
        # session_token 정합 (auth PASS 후) + api_base 동일 binding.
        friends_client_obj = None
        if session_token:
            try:
                from app.net.friends_client import FriendsClient
                friends_client_obj = FriendsClient(base_url=api_base, token=session_token)
            except (ImportError, RuntimeError, ValueError) as exc:  # pragma: no cover - graceful
                logging.getLogger(__name__).debug("FriendsClient 부재 graceful — %r", exc)

        # 7) MainWindow 표시
        window = MainWindow(
            config=config,
            auth_client=auth_client,
            reactions_client=reactions_client,
            friends_client=friends_client_obj,
        )
        # 한글 주석 — cycle 169.54 회수 — 인증 정보 propagate (MainWindow token + user_id)
        if session_user_id is not None:
            window._current_user_id = session_user_id
        if session_token is not None:
            # cycle 169.276 — attr name 정합 (사용자 critique bot 401 ROOT CAUSE 회수)
            window._session_token = session_token  # type: ignore[attr-defined]
            window._auth_token = session_token  # type: ignore[attr-defined]  # legacy retain
        if session_email:
            window._current_email = session_email  # type: ignore[attr-defined]  # cycle 169.279
        # 한글 주석 — cycle 169.55 회수 — auth PASS 시 status bar CONNECTED 강제 set
        if authenticated:
            window._status_bar.set_connection_state("CONNECTED")
        # cycle 169.375 — login 직後 folder list fetch chain (사용자 directive — 폴더 server 저장 retain)
        # cycle 169.398 — login 직後 GET /api/auth/profile fetch chain (사용자 critique image #160 visual reflect)
        if authenticated and session_token:
            try:
                from app.net.account_client import ProfileGetWorker
                profile_worker = ProfileGetWorker(api_base, session_token, parent=window)

                def _on_profile_get_finished(ok, error_code, error_message, data):
                    if not ok:
                        log.warning("[profile] GET fail — code=%s msg=%s", error_code, error_message)
                        return
                    # cycle 169.399 — username + display_name + nickname 분리 (사용자 directive image #163/164)
                    window._current_username = data.get("username", "")
                    window._current_display_name = data.get("display_name", "") or data.get("username", "")
                    window._current_nickname = data.get("nickname", "") or window._current_display_name
                    # 한글 주석 — backward compat alias (drawer header + avatar text)
                    window._current_user_nickname = window._current_nickname
                    window._current_user_phone = data.get("phone", "")
                    window._current_user_birthdate = data.get("birthdate", "")
                    window._current_user_bio = data.get("bio", "")
                    window._current_email = data.get("email", "")
                    log.info("[profile] GET PASS — username=%s display_name=%s nickname=%s",
                             window._current_username, window._current_display_name,
                             window._current_nickname)

                profile_worker.finished_with_result.connect(_on_profile_get_finished)  # type: ignore[arg-type]
                if not hasattr(window, "_profile_workers"):
                    window._profile_workers = []
                window._profile_workers.append(profile_worker)
                profile_worker.finished.connect(
                    lambda w=profile_worker: window._profile_workers.remove(w)
                )  # type: ignore[arg-type]
                profile_worker.start()
            except Exception as exc:
                log.debug("profile GET chain fail — %r", exc)

        if authenticated and session_token:
            try:
                from app.net.folder_client import FolderListWorker
                folder_worker = FolderListWorker(api_base, session_token, parent=window)

                def _on_folder_list_finished(ok, error_code, error_message, data):
                    if not ok:
                        log.warning("[folder] list fetch fail — code=%s msg=%s", error_code, error_message)
                        return
                    folders = data.get("folders", []) if isinstance(data, dict) else []
                    window._user_folders = list(folders)
                    log.info("[folder] list fetch PASS — count=%d", len(folders))
                    if hasattr(window, "_sidebar_rail") and hasattr(window._sidebar_rail, "set_folder_entries"):
                        window._sidebar_rail.set_folder_entries(folders)
                    # cycle 169.378 — chat_list_panel folder metadata sync (startup retain)
                    clp = getattr(window, "_chat_list_panel", None)
                    if clp is not None and hasattr(clp, "set_user_folders"):
                        clp.set_user_folders(folders)

                folder_worker.finished_with_result.connect(_on_folder_list_finished)  # type: ignore[arg-type]
                if not hasattr(window, "_folder_workers"):
                    window._folder_workers = []
                window._folder_workers.append(folder_worker)
                folder_worker.finished.connect(lambda w=folder_worker: window._folder_workers.remove(w))  # type: ignore[arg-type]
                folder_worker.start()
            except Exception as exc:
                log.debug("folder list fetch chain fail — %r", exc)
        window.show()

        # 한글 주석 — cycle 169.612 — NFR-03 cold start probe marker (cycle 169.597 swap).
        # PyInstaller windowed mode 안 stdout 차단 → log file fallback.
        if os.environ.get("TOOTALK_COLD_START_PROBE") == "1":
            print("READY: main_window shown", flush=True)
            try:
                _probe_path = os.path.expanduser("~/.tootalk/cold_start.log")
                os.makedirs(os.path.dirname(_probe_path), exist_ok=True)
                with open(_probe_path, "w", encoding="utf-8") as _fh:
                    _fh.write("READY: main_window shown\n")
            except OSError:
                pass

        # 한글 주석 — cycle 169.58 회수 — RoomsClient instantiate + list_rooms background fire
        if authenticated and session_token:
            try:
                from app.net.rooms_client import RoomsClient
                rooms_client = RoomsClient(base_url=api_base, token=session_token)
                window._rooms_client = rooms_client  # type: ignore[attr-defined]

                async def _populate_rooms():
                    try:
                        payloads = await rooms_client.list_rooms(scope="all")
                        from app.ui.room_list import RoomItem
                        from app.ui.chat_list_panel import ChatListEntry
                        items = [
                            RoomItem(
                                room_id=p.id,
                                room_code=p.room_code,
                                title=getattr(p, "name", "") or p.room_code,
                                role=getattr(p, "role", "member"),
                                member_count=getattr(p, "member_count", 0),
                                unread=0,
                            )
                            for p in payloads
                        ]
                        window._room_list.set_rooms(items)
                        # 한글 주석 — cycle 169.62 회수 — ChatListPanel rooms entry inject
                        chat_entries = [
                            ChatListEntry(
                                kind="room",
                                target_id=p.id,
                                name=getattr(p, "name", "") or p.room_code,
                                last_message="",
                                unread_count=0,
                                is_online=False,
                            )
                            for p in payloads
                        ]
                        # 한글 주석 — sample friends + bots placeholder (REST 신설 별도 cycle)
                        chat_entries += [
                            ChatListEntry(kind="friend", target_id=1, name="홍원표",
                                          last_message="안녕하세요", is_online=True),
                            ChatListEntry(kind="bot", target_id=2, name="투네이션 고객센터",
                                          last_message="무엇을 도와드릴까요?", is_online=True),
                        ]
                        window._chat_list_panel.set_entries(chat_entries)
                        logging.getLogger(__name__).info(
                            "[chat_list] entries 갱신 — rooms=%d total=%d",
                            len(items), len(chat_entries),
                        )
                    except Exception as exc:
                        logging.getLogger(__name__).warning("[rooms] list_rooms 실패 — %r", exc)
                asyncio.ensure_future(_populate_rooms())
            except Exception as r_exc:
                logging.getLogger(__name__).warning("[rooms] instantiate 실패 — %r", r_exc)

        # 한글 주석 — cycle 169.56 회수 — signaling WebSocket actual connect background task
        if authenticated:
            try:
                from app.net.signaling_client import SignalingClient
                signaling_client = SignalingClient(config=config)
                signaling_client.connection_state_changed.connect(  # type: ignore[attr-defined]
                    window._status_bar.set_connection_state
                )
                # 한글 주석 — cycle 169.59 회수 — incoming call signal dispatch chain
                signaling_client.offer_received.connect(  # type: ignore[attr-defined]
                    window._on_signaling_offer
                )
                signaling_client.answer_received.connect(  # type: ignore[attr-defined]
                    window._on_signaling_answer
                )
                signaling_client.ice_received.connect(  # type: ignore[attr-defined]
                    window._on_signaling_ice
                )
                signaling_client.peer_joined.connect(  # type: ignore[attr-defined]
                    window._on_signaling_peer_joined
                )
                window._signaling_client = signaling_client  # type: ignore[attr-defined]
                asyncio.ensure_future(signaling_client.connect())
            except Exception as sig_exc:
                logging.getLogger(__name__).warning("[signaling] connect schedule 실패 — %r", sig_exc)

        # 7) qasync loop run_forever — Qt + asyncio 단일 thread 통합
        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(auth_client.close())
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
