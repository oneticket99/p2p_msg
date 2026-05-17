"""``server.protocol`` 의 단위 테스트 — envelope 화이트리스트 검증.

DESIGN.md §10.1 정합 — 단위 테스트는 외부 IO 격리.
NFR-05 정합 (Specification.md) — 시그널링 envelope 외부 입력 화이트리스트 5종 외 거부.
사용자 directive 2026-05-17 — "qa 단계에서는 pytest 당연히 필요해".
"""

from __future__ import annotations


def test_is_valid_client_type_accepts_whitelist() -> None:
    """화이트리스트 5종 (JOIN/LEAVE/OFFER/ANSWER/ICE) 의 모두 통과."""

    from server.protocol import (
        CLIENT_MSG_TYPES,
        MSG_ANSWER,
        MSG_ICE,
        MSG_JOIN,
        MSG_LEAVE,
        MSG_OFFER,
        is_valid_client_type,
    )

    for msg_type in (MSG_JOIN, MSG_LEAVE, MSG_OFFER, MSG_ANSWER, MSG_ICE):
        assert is_valid_client_type(msg_type), (
            f"화이트리스트 의 정상 type {msg_type} 거부 발생 — 검증 실패"
        )

    assert len(CLIENT_MSG_TYPES) == 5


def test_is_valid_client_type_rejects_unknown() -> None:
    """화이트리스트 외 type 모두 거부."""

    from server.protocol import is_valid_client_type

    rejection_cases = [
        "UNKNOWN",
        "join",
        "Join",
        "",
        "PEERS",
        "PEER_JOINED",
        "PEER_LEFT",
        "ERROR",
    ]
    for case in rejection_cases:
        assert not is_valid_client_type(case), (
            f"화이트리스트 외 type '{case}' 통과 발생 — 보안 위반"
        )


def test_is_valid_client_type_rejects_non_string() -> None:
    """비-문자열 입력 의 거부 (보안 — TypeError 회피)."""

    from server.protocol import is_valid_client_type

    non_string_cases = [None, 123, [], {}, True]
    for case in non_string_cases:
        assert not is_valid_client_type(case), (
            f"비-문자열 {case!r} 통과 — 타입 검증 실패"
        )
