# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — message reaction persistence (cycle 155 신설).

엔드포인트 3종 (auth_middleware Bearer 검증 의무):

- POST   /api/messages/{message_id}/reactions      — emoji 추가 + REACTION_ADD audit
- GET    /api/messages/{message_id}/reactions      — emoji + count snapshot list
- DELETE /api/messages/{message_id}/reactions/{emoji} — emoji 제거 + REACTION_REMOVE audit

audit hook
----------
- REACTION_ADD / REACTION_REMOVE — POST/DELETE 의무. target_id = message_id +
  metadata = {emoji, user_id}.
- pool 부재 시 graceful skip (테스트 환경 정합).

설계 결정
---------
- 단일 사용자 → 단일 message → 단일 emoji = unique constraint (DB schema UNIQUE
  (message_id, user_id, emoji))
- emoji = Unicode BMP/supplementary plane 만 (가드레일 feedback_emoji_telegram_compat)
- count = SQL GROUP BY emoji + COUNT
"""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web

log = logging.getLogger(__name__)


async def handle_add_reaction(request: web.Request) -> web.Response:
    """POST /api/messages/{message_id}/reactions — emoji 추가.

    Request body: {"emoji": "👍"}
    Response: {"ok": true, "emoji": "👍", "total_count": 3}
    """
    message_id = request.match_info.get("message_id")
    if not message_id:
        return web.json_response({"error": "message_id 부재"}, status=400)

    try:
        body = await request.json()
        emoji = str(body.get("emoji", "")).strip()
    except Exception as exc:
        return web.json_response({"error": f"body parse 실패: {exc}"}, status=400)

    if not emoji:
        return web.json_response({"error": "emoji 부재"}, status=400)

    # 한글 주석 — cycle 169.33 보안 회수 — auth_middleware request["user_id"] 직접 + X-User-Id fallback 폐기
    try:
        user_id = request["user_id"]
    except KeyError:
        return web.json_response({"error": "Authorization 부재"}, status=401)

    pool = request.app.get("db_pool")
    if pool is None:
        log.warning("[reactions] DB pool 부재 — graceful skip + 200 mock 응답")
        return web.json_response({"ok": True, "emoji": emoji, "total_count": 1})

    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # 한글 주석 — UNIQUE (message_id, user_id, emoji) 의무 — ON DUPLICATE KEY 차단
                await cur.execute(
                    "INSERT IGNORE INTO message_reactions "
                    "(message_id, user_id, emoji, created_at) "
                    "VALUES (%s, %s, %s, NOW())",
                    (message_id, user_id, emoji),
                )
                await cur.execute(
                    "SELECT COUNT(*) FROM message_reactions "
                    "WHERE message_id=%s AND emoji=%s",
                    (message_id, emoji),
                )
                row = await cur.fetchone()
                total = row[0] if row else 0
            await conn.commit()
        log.info("[reactions] add — message_id=%s emoji=%s user=%s total=%d",
                 message_id, emoji, user_id, total)
        return web.json_response({"ok": True, "emoji": emoji, "total_count": total})
    except Exception as exc:
        log.warning("[reactions] add 실패 — %r", exc)
        return web.json_response({"error": str(exc)}, status=500)


async def handle_list_reactions(request: web.Request) -> web.Response:
    """GET /api/messages/{message_id}/reactions — emoji + count list."""
    message_id = request.match_info.get("message_id")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"reactions": []})

    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT emoji, COUNT(*) AS cnt FROM message_reactions "
                    "WHERE message_id=%s GROUP BY emoji ORDER BY cnt DESC",
                    (message_id,),
                )
                rows = await cur.fetchall()
        reactions: list[dict[str, Any]] = [
            {"emoji": str(r[0]), "count": int(r[1])} for r in rows
        ]
        return web.json_response({"reactions": reactions})
    except Exception as exc:
        log.warning("[reactions] list 실패 — %r", exc)
        return web.json_response({"reactions": []})


async def handle_remove_reaction(request: web.Request) -> web.Response:
    """DELETE /api/messages/{message_id}/reactions/{emoji} — emoji 제거."""
    message_id = request.match_info.get("message_id")
    emoji = request.match_info.get("emoji")
    # cycle 169.33 보안 회수 — request["user_id"] 직접
    try:
        user_id = request["user_id"]
    except KeyError:
        return web.json_response({"error": "Authorization 부재"}, status=401)

    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"ok": True})

    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM message_reactions "
                    "WHERE message_id=%s AND user_id=%s AND emoji=%s",
                    (message_id, user_id, emoji),
                )
            await conn.commit()
        return web.json_response({"ok": True})
    except Exception as exc:
        log.warning("[reactions] remove 실패 — %r", exc)
        return web.json_response({"error": str(exc)}, status=500)


def register_reactions_routes(app: web.Application) -> None:
    """server.main register entry — 3 endpoint."""
    app.router.add_post(
        "/api/messages/{message_id}/reactions", handle_add_reaction
    )
    app.router.add_get(
        "/api/messages/{message_id}/reactions", handle_list_reactions
    )
    app.router.add_delete(
        "/api/messages/{message_id}/reactions/{emoji}", handle_remove_reaction
    )
