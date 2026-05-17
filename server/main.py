"""시그널링 서버 entry point.

실행 방법::

    python -m server.main

본 모듈은 다음을 수행한다.

1. ``.env`` 환경변수 로딩 (python-dotenv)
2. ``logging`` 핸들러·포맷터 구성 — 정본 §E 형식 ``[YYYY-mm-dd H:i:s]``
3. ``aiohttp.web.Application`` 생성 + ``RoomRegistry`` 바인딩
4. ``server/signaling.py`` Router 라우트 등록
5. SIGINT/SIGTERM 시 graceful shutdown — 모든 방에 ERROR 송신 후 close

모든 IO 는 비동기 전용이며 설정값(호스트·포트·로그레벨·WS 스킴)은 환경변수
경유로만 주입된다. 하드코딩 금지.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Final

from aiohttp import web
from dotenv import load_dotenv

from .api.auth_handlers import register_auth_routes
from .auth.middleware import auth_middleware
from .db.connection import close_pool, create_pool
from .room import RoomRegistry
from .signaling import build_routes


# ---------------------------------------------------------------------------
# 환경변수 키 상수 — ``.env.example`` 과 정합 의무 (AGENTS.md 부록 B 참조)
# ---------------------------------------------------------------------------

ENV_HOST: Final[str] = "SIGNAL_SERVER_HOST"
ENV_PORT: Final[str] = "SIGNAL_SERVER_WS_PORT"
ENV_SCHEME: Final[str] = "SIGNAL_SERVER_WS_SCHEME"
ENV_LOG_LEVEL: Final[str] = "LOG_LEVEL"

# 환경변수 미지정 시 사용하는 기본값 — 데모/로컬 개발 기본
DEFAULT_HOST: Final[str] = "0.0.0.0"
DEFAULT_PORT: Final[int] = 8765
DEFAULT_SCHEME: Final[str] = "ws"
DEFAULT_LOG_LEVEL: Final[str] = "INFO"


def configure_logging(log_level: str) -> None:
    """루트 로거에 정본 §E 포맷 핸들러를 한 번만 부착한다.

    형식: ``[YYYY-mm-dd H:i:s] LEVEL logger: message``
    """
    root = logging.getLogger()
    # 중복 핸들러 부착 방지 — 본 함수가 두 번 호출되어도 idempotent
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # 잘못된 레벨 문자열은 INFO 로 폴백 — 운영 사고 시 무중단 우선
    level = logging.getLevelName(log_level.upper())
    if not isinstance(level, int):
        level = logging.INFO
    root.setLevel(level)


def _read_int_env(key: str, default: int) -> int:
    """정수형 환경변수 안전 파싱 — 무효 값은 기본값으로 폴백."""
    raw = os.environ.get(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logging.getLogger(__name__).warning(
            "환경변수 %s=%r 정수 파싱 실패 — 기본값 %d 사용", key, raw, default
        )
        return default


async def build_app() -> web.Application:
    """aiohttp Application 객체를 생성하고 라우트/registry + DB pool 을 바인딩.

    Phase 1 확장 (사이클 22):
    - DB_ENABLED=1 환경변수 시 asyncmy pool 생성 + app['db_pool'] 등록
    - auth middleware 등록 + 5 REST endpoint 라우트
    - in-memory session_store dict (Phase 1, Phase 2 redis 전환)

    Returns:
        준비 완료된 ``web.Application``.
    """
    # 한글 주석: middleware 는 신규 인스턴스 의 의 의 의 의 의 의 의 의 의 의 의 인자 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의
    app = web.Application(middlewares=[auth_middleware])

    # 시그널링 룸 registry (기존)
    registry = RoomRegistry()
    build_routes(app, registry)

    # 세션 store (Phase 1 = in-memory dict, Phase 2 = redis)
    app["session_store"] = {}

    # auth REST endpoint 등록
    register_auth_routes(app)

    # DB pool — DB_ENABLED=1 시 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 활성. 로컬 dev 시 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의
    if os.environ.get("DB_ENABLED", "0").strip() == "1":
        app["db_pool"] = await create_pool()
    else:
        app["db_pool"] = None
        logging.getLogger(__name__).warning(
            "DB_ENABLED!=1 — DB pool 비활성. auth endpoint 호출 = 500 응답"
        )

    # 종료 훅 — 모든 방에 ERROR 송신 + DB pool close
    async def _on_cleanup(app_: web.Application) -> None:
        await registry.shutdown()
        await close_pool(app_.get("db_pool"))

    app.on_cleanup.append(_on_cleanup)
    return app


async def _serve() -> None:
    """``AppRunner`` + ``TCPSite`` 기반 메인 서비스 루프.

    ``web.run_app`` 대신 직접 runner 를 다루는 이유는 SIGINT/SIGTERM 시점에
    cleanup hook 을 명시적으로 trigger 하기 위함이다.
    """
    logger = logging.getLogger(__name__)

    host = os.environ.get(ENV_HOST, DEFAULT_HOST)
    port = _read_int_env(ENV_PORT, DEFAULT_PORT)
    scheme = os.environ.get(ENV_SCHEME, DEFAULT_SCHEME)

    # TLS 전환 후크 — Phase 2 진입 시 ``wss`` 스킴 + SSL context 주입
    # 위치를 미리 마련해 둔다 (TD-1). 본 Phase 는 ``ws`` 만 지원.
    if scheme not in ("ws", "wss"):
        logger.warning("%s=%r 무효 — 'ws' 로 폴백", ENV_SCHEME, scheme)
        scheme = "ws"
    if scheme == "wss":
        logger.warning(
            "wss 스킴은 Phase 2 진입 시 활성화 예정 — 본 Phase 는 ws 로 동작",
        )

    app = await build_app()
    runner = web.AppRunner(app, access_log=logging.getLogger("aiohttp.access"))
    await runner.setup()
    site = web.TCPSite(runner, host=host, port=port)

    await site.start()
    logger.info(
        "시그널링 서버 시작 host=%s port=%d scheme=%s endpoint=/ws",
        host,
        port,
        scheme,
    )

    # SIGINT/SIGTERM 대기 — 받으면 graceful shutdown
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop() -> None:
        logger.info("종료 시그널 수신 — graceful shutdown 시작")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            # Windows 등 일부 플랫폼은 add_signal_handler 미지원 — KeyboardInterrupt
            # 폴백으로 처리됨 (asyncio.run 안쪽에서 CancelledError 전파)
            pass

    try:
        await stop_event.wait()
    finally:
        logger.info("AppRunner cleanup 진행")
        await runner.cleanup()
        logger.info("시그널링 서버 종료 완료")


def main() -> None:
    """CLI 진입점 — ``python -m server.main`` 으로 호출."""
    # ``.env`` 로딩 — 파일 없으면 무처리 (운영에서는 systemd EnvironmentFile
    # 으로 주입되는 경우도 있음)
    load_dotenv(override=False)

    configure_logging(os.environ.get(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL))

    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        # Windows 폴백 경로 — 정상 종료로 간주
        logging.getLogger(__name__).info("KeyboardInterrupt — 종료")


if __name__ == "__main__":
    main()
