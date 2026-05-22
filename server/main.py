# SPDX-License-Identifier: GPL-3.0-or-later
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
from typing import Any, Final, Optional

from aiohttp import web
from dotenv import load_dotenv

from app.bot.llm_proxy import (
    AnthropicProvider,
    MockLLMProvider,
    OpenAIProvider,
    RateLimitGate,
)

from .api.auth_handlers import register_auth_routes
from .api.bot_handlers import APP_KEY_PROVIDER, APP_KEY_RATE_GATE, register_bot_routes
from .api.devices_handlers import register_devices_routes
from .api.health_handlers import register_health_routes
from .api.messages_handlers import register_messages_routes
from .auth.middleware import auth_middleware
from .config import Config
from .db.connection import close_pool, create_pool
from .middleware import (
    APP_KEY_ACTIVITY,
    ActivityTracker,
    activity_middleware,
    request_id_middleware,
)
from .room import RoomRegistry
from .signaling import build_routes


# ---------------------------------------------------------------------------
# 환경변수 키 상수 — ``.env.example`` 과 정합 의무 (AGENTS.md 부록 B 참조)
# ---------------------------------------------------------------------------

ENV_HOST: Final[str] = "SIGNAL_SERVER_HOST"
ENV_PORT: Final[str] = "SIGNAL_SERVER_WS_PORT"
ENV_SCHEME: Final[str] = "SIGNAL_SERVER_WS_SCHEME"
ENV_LOG_LEVEL: Final[str] = "LOG_LEVEL"
# Bot LLM proxy — server-side LLM provider 의 활성 여부 + 분당 호출 cap
ENV_BOT_ENABLED: Final[str] = "BOT_ENABLED"
ENV_BOT_RATE_PER_MINUTE: Final[str] = "BOT_RATE_PER_MINUTE"

# 환경변수 미지정 시 사용하는 기본값 — 데모/로컬 개발 기본
DEFAULT_HOST: Final[str] = "0.0.0.0"
DEFAULT_PORT: Final[int] = 8765
DEFAULT_SCHEME: Final[str] = "ws"
DEFAULT_LOG_LEVEL: Final[str] = "INFO"
# Bot rate limit default — per-user 의 분당 cap (memory feedback_bot_rate_abuse 정합)
DEFAULT_BOT_RATE_PER_MINUTE: Final[int] = 20


def configure_logging(log_level: str, log_format: str = "text") -> None:
    """루트 로거 의 KST formatter + redact filter + JSON 분기.

    Phase 4 cycle 116~117 — server.logging_setup.configure_logging 의 wrapper.
    LOG_FORMAT env (text / json) 의 caller 영역 전달 의무.
    """

    from .logging_setup import configure_logging as _real_configure

    _real_configure(level=log_level, log_format=log_format)

    # 잘못된 레벨 문자열은 INFO 로 폴백 — 운영 사고 시 무중단 우선
    level = logging.getLevelName(log_level.upper())
    if not isinstance(level, int):
        level = logging.INFO
    logging.getLogger().setLevel(level)


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


async def _ensure_bot_user(pool: Any) -> None:
    """bot user (id=1) idempotent INSERT — cycle 169.502 신설.

    server/api/bot_handlers.py:371 의 `sender_id=1` hardcoded — users.id=1 row 부재 시점
    FK violation IntegrityError 1452 → bot reply insert silent skip → bot chat 답변
    사라짐 root cause. server startup chain 안 INSERT IGNORE 패턴 의 idempotent INSERT.
    """
    sql = (
        "INSERT IGNORE INTO users (id, email, password_hash, username, display_name, "
        "nickname, email_verified, status) VALUES "
        "(1, 'bot@tootalk.local', '!bot-no-login', 'tootalk_bot', "
        "'투네이션 고객센터', '투네이션 고객센터', 1, 'active')"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql)
        await conn.commit()
    logging.getLogger(__name__).info("[startup] ensure_bot_user PASS (id=1)")


async def build_app(config: Optional[Config] = None) -> web.Application:
    """aiohttp Application 객체를 생성하고 라우트/registry + DB pool 을 바인딩.

    Phase 1 확장 (사이클 22):
    - DB_ENABLED=1 환경변수 시 asyncmy pool 생성 + app['db_pool'] 등록
    - auth middleware 등록 + 5 REST endpoint 라우트
    - in-memory session_store dict (Phase 1, Phase 2 redis 전환)

    Phase 4 cycle 110 (Config 통합):
    - ``config`` 인자 주입 시 본 Config 사용 (test mock 또는 caller 명시 주입).
    - None 시 ``Config.from_env()`` 의 .env chain load 의 single entry point.
    - BOT / DB 의 env 직접 access 의 폐기 — cfg.bot.enabled + cfg.bot.rate_per_minute
      의 frozen dataclass 경유.

    Returns:
        준비 완료된 ``web.Application``.
    """
    # cycle 110 — Config 통합 single entry. None 시 lazy load.
    cfg = config if config is not None else Config.from_env()
    # 한글 주석: middleware chain — request_id → auth → activity 의 순차.
    # request_id 가 최상단 (모든 request 의 trace 의무, log correlation base).
    app = web.Application(
        middlewares=[request_id_middleware, auth_middleware, activity_middleware]
    )
    # 한글 주석: 후속 endpoint 의 의존성 주입 — app["config"] 등록
    app["config"] = cfg
    # cycle 111 — DB audit migration 0003 의 actual code wiring base.
    # ActivityTracker = 1분 throttle in-memory (single-worker 정합).
    app[APP_KEY_ACTIVITY] = ActivityTracker(throttle_seconds=60)

    # 시그널링 룸 registry (기존)
    registry = RoomRegistry()
    build_routes(app, registry)

    # 세션 store (Phase 1 = in-memory dict, Phase 2 = redis)
    app["session_store"] = {}

    # auth REST endpoint 등록
    register_auth_routes(app)

    # folder REST endpoint 등록 (cycle 169.76 신설 — telegram folder management)
    # cycle 169.78 회수 — LEGB scope shadow 차단 — module-level logging 직접 사용
    try:
        from .api.folder_handlers import register_folder_routes
        register_folder_routes(app)
    except Exception as folder_exc:
        logging.getLogger(__name__).warning(
            "[folder] route 등록 실패 graceful — %r", folder_exc,
        )

    # devices REST endpoint 등록 (Phase 2 사이클 43 multi-device sync)
    register_devices_routes(app)

    # messages REST endpoint 등록 (Phase 3 사이클 60 ChatView lazy load)
    register_messages_routes(app)

    # reactions REST endpoint 등록 (cycle 155 신설 — emoji + count + UNIQUE constraint)
    try:
        from .api.reactions_handlers import register_reactions_routes
        register_reactions_routes(app)
        logging.getLogger(__name__).info("[api] reactions 3 endpoint 등록 완료 (cycle 155)")
    except Exception as exc:  # pragma: no cover - graceful
        logging.getLogger(__name__).debug("[api] reactions 등록 실패 graceful — %r", exc)

    # health + readiness endpoint 등록 (cycle 124 — Docker HEALTHCHECK + nginx + k8s probe)
    register_health_routes(app)

    # 자동 업데이트 endpoint 등록 (cycle 132 — Phase 5 GET latest + POST release skeleton)
    # 한글 주석: lazy import + try/except graceful — 모듈 부재 시 server 기동 영향 차단.
    try:
        from .api.version_handlers import register_version_routes

        register_version_routes(app)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "version_handlers 등록 실패 — skeleton skip (%s)", exc
        )

    # cycle 169.415 — emoji pack share endpoint 등록 (Phase 5 Item 3 actual binding)
    try:
        from .api.emoji_handlers import register_emoji_routes
        register_emoji_routes(app)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "emoji_handlers 등록 실패 — skip (%s)", exc
        )

    # cycle 169.420 — bot framework BotFather 등가 (Phase 3+ 차별화)
    try:
        from .api.bot_directory_handlers import register_bot_directory_routes
        register_bot_directory_routes(app)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "bot_directory_handlers 등록 실패 — skip (%s)", exc
        )

    # cycle 169.446 — FCM push notification endpoint 등록 (사용자 directive 실시간 알림 base)
    try:
        from .api.push_handlers import register_push_routes
        register_push_routes(app)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "push_handlers 등록 실패 — skip (%s)", exc
        )

    # cycle 169.486 — streaming OAuth endpoint 등록 (Phase 5 token persistence)
    try:
        from .api.streaming_oauth_handlers import register_streaming_oauth_routes
        register_streaming_oauth_routes(app)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "streaming_oauth_handlers 등록 실패 — skip (%s)", exc
        )

    # cycle 169.447 — 읽음 상태 추적 endpoint 등록 (사용자 directive 정식 read state)
    try:
        from .api.read_handlers import register_read_routes
        register_read_routes(app)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "read_handlers 등록 실패 — skip (%s)", exc
        )

    # cycle 169.452 — telegram align 연락처 + 양방향 매칭 endpoint
    try:
        from .api.contacts_handlers import register_contacts_routes
        register_contacts_routes(app)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "contacts_handlers 등록 실패 — skip (%s)", exc
        )

    # cycle 169.457 — telegram align 사용자명 검색 친구 추가
    try:
        from .api.friends_by_username_handler import register_friends_by_username_routes
        register_friends_by_username_routes(app)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "friends_by_username_handler 등록 실패 — skip (%s)", exc
        )

    # remote control endpoint 등록 (cycle 132 — Phase 5 Item 5 진입 prerequisite skeleton)
    # 한글 주석: lazy import + try/except graceful — 모듈 부재 시 server 기동 영향 차단.
    try:
        from .api.remote_handlers import register_remote_routes

        register_remote_routes(app)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "remote_handlers 등록 실패 — skeleton skip (%s)", exc
        )

    # 그룹 채팅 룸 endpoint 등록 (cycle 135 — 6 REST endpoint + audit)
    # 한글 주석: lazy import + try/except graceful — 모듈 부재 시 server 기동 영향 차단.
    try:
        from .api.rooms_handlers import register_rooms_routes

        register_rooms_routes(app)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "rooms_handlers 등록 실패 — skeleton skip (%s)", exc
        )

    # 친구 관리 endpoint 등록 (cycle 144 — 8 REST endpoint + 5 audit ENUM)
    # 한글 주석: lazy import + try/except graceful — 모듈 부재 시 server 기동 영향 차단.
    try:
        from .api.friends_handlers import register_friends_routes

        register_friends_routes(app)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            "friends_handlers 등록 실패 — skeleton skip (%s)", exc
        )

    # bot LLM proxy endpoint 등록 (Phase 3 사이클 74 — BOT_ENABLED=1 시 활성)
    # cycle 169.345 — 사용자 directive verbatim "챗봇은 gpt 로만 진행" — OpenAI only strict
    # Anthropic / Mock fallback chain 폐기. OPENAI_API_KEY 부재 시점 startup fail.
    if cfg.bot.enabled:
        bot_logger = logging.getLogger(__name__)
        if not OpenAIProvider.is_available():
            raise RuntimeError(
                "OPENAI_API_KEY 부재 — 챗봇 = OpenAI only strict (사용자 directive cycle 169.345). "
                "BOT_ENABLED=1 + OPENAI_API_KEY 필수."
            )
        app[APP_KEY_PROVIDER] = OpenAIProvider()
        bot_logger.info(
            "Bot LLM provider = OpenAIProvider (사용자 directive cycle 169.345 OpenAI only strict)"
        )
        app[APP_KEY_RATE_GATE] = RateLimitGate(rate_per_minute=cfg.bot.rate_per_minute)
        register_bot_routes(app)
        logging.getLogger(__name__).info(
            "Bot endpoint POST /api/bot/chat 활성 — rate=%d/min",
            cfg.bot.rate_per_minute,
        )
    else:
        logging.getLogger(__name__).info(
            "BOT_ENABLED!=1 — /api/bot/chat 비활성 (LLM proxy off)"
        )

    # DB pool — DB_ENABLED=1 시 활성. 로컬 dev 시 의
    if os.environ.get("DB_ENABLED", "0").strip() == "1":
        app["db_pool"] = await create_pool()
        # cycle 169.502 — bot user (id=1) row ensure (사용자 directive 회수).
        # users.id=1 row 부재 시점 bot reply insert FK violation IntegrityError 1452 silent skip
        # → bot chat 답변 사라짐 root cause. server startup chain 안 idempotent INSERT 의무.
        try:
            await _ensure_bot_user(app["db_pool"])
        except Exception as exc:  # noqa: BLE001 - graceful
            logging.getLogger(__name__).warning(
                "[startup] ensure_bot_user 실패 graceful — %r", exc
            )
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

    configure_logging(
        os.environ.get(ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL),
        os.environ.get("LOG_FORMAT", "text"),
    )

    try:
        asyncio.run(_serve())
    except KeyboardInterrupt:
        # Windows 폴백 경로 — 정상 종료로 간주
        logging.getLogger(__name__).info("KeyboardInterrupt — 종료")


if __name__ == "__main__":
    main()
