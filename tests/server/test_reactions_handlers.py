# SPDX-License-Identifier: GPL-3.0-or-later
"""server.api.reactions_handlers 검증 — cycle 155 신설 + cycle 158 test.

3 case (pytest-aiohttp 부재 env 정합):
- handler import + callable 검증
- register_reactions_routes 호출 시 app.router 3 endpoint 등록
- pyqt protocol 정합 검증 (message_protocol 안 reactions field 통합)
"""

from __future__ import annotations

import pytest
from aiohttp import web

from server.api.reactions_handlers import (
    handle_add_reaction,
    handle_list_reactions,
    handle_remove_reaction,
    register_reactions_routes,
)


class TestReactionsHandlerImport:
    """import 검증 — 1 case."""

    def test_handlers_callable(self) -> None:
        assert callable(handle_add_reaction)
        assert callable(handle_list_reactions)
        assert callable(handle_remove_reaction)


class TestReactionsRouteRegistration:
    """register_reactions_routes 검증 — 1 case."""

    def test_routes_registered(self) -> None:
        app = web.Application()
        register_reactions_routes(app)
        routes = list(app.router.routes())
        # POST + GET + DELETE + (HEAD auto) ≥ 3
        assert len(routes) >= 3
        # 한글 주석 — 등록 path 검증
        paths = [r.resource.canonical for r in routes]  # type: ignore[union-attr]
        assert any("/reactions" in p for p in paths)


class TestReactionsProtocolIntegration:
    """message_protocol 안 reactions field 정합 — 1 case."""

    def test_reactions_field_in_payload(self) -> None:
        from app.net.message_protocol import MessagePayload
        p = MessagePayload(type="text", sender="alice", text="hi", reactions={"👍": 3})
        assert p.reactions == {"👍": 3}
        raw = p.to_json()
        parsed = MessagePayload.from_json(raw)
        assert parsed.reactions == {"👍": 3}
