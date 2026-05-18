# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 124 — health + readiness endpoint.

Docker healthcheck + nginx /healthz + Kubernetes liveness/readiness probe
정합. 인증 부재 (public path) + 빠른 응답 + 외부 의존성 부재 default.

설계 결정
---------
- `/healthz` = liveness — process 가 살아있음 만 (DB/외부 의존성 검증 부재).
  Docker HEALTHCHECK + nginx /healthz proxy 정합.
- `/readyz` = readiness — 사용 가능한 상태 (DB pool + bot provider + activity
  tracker 의 가용 여부). Kubernetes readiness probe 정합 + 진입 시점 의 dependency
  검증.
- 응답 = JSON `{"status": "ok"|"degraded"|"down", "checks": {...}}` + HTTP
  200 (ok/degraded) 또는 503 (down).
- _PUBLIC_PATHS 정합 — auth_middleware bypass.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from aiohttp import web

log = logging.getLogger(__name__)


async def handle_healthz(request: web.Request) -> web.Response:
    """liveness probe — process 가 살아있음.

    DB / 외부 의존성 검증 부재. 항상 200 OK + status=ok.
    Docker HEALTHCHECK + nginx /healthz proxy 정합.
    """

    return web.json_response({"status": "ok"})


async def handle_readyz(request: web.Request) -> web.Response:
    """readiness probe — dependency 검증.

    검사 항목 (cycle 124 base):
    - db_pool — app["db_pool"] not None (DB 가용 여부).
    - bot_provider — app[APP_KEY_PROVIDER] not None (BOT_ENABLED=1 시 의무).
    - activity_tracker — app[APP_KEY_ACTIVITY] not None.

    응답 schema:
        {
            "status": "ok"|"degraded"|"down",
            "checks": {"db_pool": "ok"|"absent", ...}
        }

    HTTP code:
    - 200 = ok + degraded (degraded = 일부 optional 항목 부재, 운영 가능).
    - 503 = down (필수 항목 부재 — 본 cycle = 모든 항목 optional 의 의 down 부재).
    """

    checks: Dict[str, str] = {}

    # 1) DB pool
    db_pool = request.app.get("db_pool")
    checks["db_pool"] = "ok" if db_pool is not None else "absent"

    # 2) bot provider (optional — BOT_ENABLED=1 시 의무)
    try:
        from server.api.bot_handlers import APP_KEY_PROVIDER

        provider = request.app.get(APP_KEY_PROVIDER)
        checks["bot_provider"] = "ok" if provider is not None else "absent"
    except Exception:
        checks["bot_provider"] = "unknown"

    # 3) activity tracker (cycle 111 신설)
    try:
        from server.middleware.activity import APP_KEY_ACTIVITY

        tracker = request.app.get(APP_KEY_ACTIVITY)
        checks["activity_tracker"] = "ok" if tracker is not None else "absent"
    except Exception:
        checks["activity_tracker"] = "unknown"

    # 4) config (cycle 110 신설)
    config = request.app.get("config")
    checks["config"] = "ok" if config is not None else "absent"

    # status 결정 — 모든 ok = ok / 일부 absent = degraded / unknown 포함 = degraded
    if all(v == "ok" for v in checks.values()):
        status = "ok"
    elif any(v == "unknown" for v in checks.values()):
        status = "degraded"
    else:
        status = "degraded"

    return web.json_response({"status": status, "checks": checks}, status=200)


def register_health_routes(app: web.Application) -> None:
    """`/healthz` + `/readyz` 라우트 등록 — server.main entry."""

    app.router.add_get("/healthz", handle_healthz)
    app.router.add_get("/readyz", handle_readyz)
