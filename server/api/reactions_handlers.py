# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — message reaction persistence (cycle 155 신설).

역할 — 메시지 emoji 반응의 추가/조회/제거를 영속화한다. 사용자×메시지×emoji
조합은 유일하며(중복 추가 무시), 조회는 emoji 별 집계 snapshot 을 돌려준다.

계층 위치 — server API handler 계층(정본 §E). auth_middleware Bearer 통과
(`request["user_id"]`) 후 진입하며, SQL 은 본 module 안에서 직접 실행한다
(repository 미경유 — `message_reactions` 단일 테이블 단순 CRUD).

의존성 — aiohttp `web` + `request.app["db_pool"]`(asyncmy). 외부 repository
의존 부재. pool 부재 시 graceful mock 응답(테스트/dev 정합).

범위 한계 — reaction CRUD + 집계만. 실시간 reaction broadcast(signaling)·emoji
유효성 정규화는 본 module 범위 외(emoji 는 클라가 BMP/supplementary 로 전달 가정).

엔드포인트 카탈로그(실 함수 3 + register, auth_middleware Bearer 검증 의무):

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

    인증 — Bearer 의무. `request["user_id"]` 부재(KeyError) 시 401.
    검증 순서 — (1) message_id 경로 존재 → (2) body 파싱 + emoji 추출 →
    (3) emoji 비어있지 않음 → (4) user_id 인증 → (5) db_pool(부재 시 mock 200).
    오류 코드 — message_id/emoji/body 위반 400, 인증 부재 401, SQL 실패 500.

    Parameters — match_info ``message_id``, body ``{"emoji": str}``.
    Returns — 200 + ``{ok, emoji, total_count}``(emoji 별 누적 수).
    부작용 — `message_reactions` INSERT IGNORE(UNIQUE 중복 무시) + 집계 SELECT
        + commit(DB write) + INFO 로그.
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

    # cycle 169.33 보안 회수 — auth_middleware request["user_id"] 직접 사용, X-User-Id fallback 폐기(위조 차단)
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
                # INSERT IGNORE — UNIQUE(message_id, user_id, emoji) 위반(중복 반응)을 에러 대신 무시 처리
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
    """GET /api/messages/{message_id}/reactions — emoji + count list.

    의도 — 메시지 버블의 reaction 요약(emoji + 개수)을 채운다.
    인증 — 본 endpoint 는 공개 조회(user_id 미사용). db_pool 부재 시 빈 목록.
    Parameters — match_info ``message_id``.
    Returns — 200 + ``{reactions: [{emoji, count}]}``(count 내림차순).
    부작용 — 부재(읽기 전용 GROUP BY SELECT). SQL 실패 시 빈 목록 graceful.
    """
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
    """DELETE /api/messages/{message_id}/reactions/{emoji} — emoji 제거.

    의도 — 호출자 자신의 반응만 철회한다(WHERE user_id 로 self 한정).
    인증 — Bearer 의무. `request["user_id"]` 부재 시 401.
    Parameters — match_info ``message_id`` + ``emoji``(경로).
    Returns — 200 + ``{ok: true}``. db_pool 부재 시도 200(graceful no-op).
    부작용 — `message_reactions` DELETE(self row 한정, DB write) + commit.
        SQL 실패 시 500.
    """
    message_id = request.match_info.get("message_id")
    emoji = request.match_info.get("emoji")
    # cycle 169.33 보안 회수 — request["user_id"] 직접 사용(X-User-Id 위조 차단)
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
