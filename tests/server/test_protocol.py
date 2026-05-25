"""``server.protocol`` 의 단위 테스트 — envelope 화이트리스트 검증.

DESIGN.md §10.1 정합 — 단위 테스트는 외부 IO 격리.
NFR-05 정합 (Specification.md) — 시그널링 envelope 외부 입력 화이트리스트 5종 외 거부.
사용자 directive 2026-05-17 — "qa 단계에서는 pytest 당연히 필요해".
"""

from __future__ import annotations


def test_is_valid_client_type_accepts_whitelist() -> None:
    """화이트리스트 7종 (JOIN/LEAVE/OFFER/ANSWER/ICE + SFU_PUBLISH/SFU_SUBSCRIBE) 통과.

    cycle 169.798 SFU 확장 M3a — 그룹 통화 upstream/downstream 제어 2종 추가.
    """

    from server.protocol import (
        CLIENT_MSG_TYPES,
        MSG_ANSWER,
        MSG_ICE,
        MSG_JOIN,
        MSG_LEAVE,
        MSG_OFFER,
        MSG_SFU_PUBLISH,
        MSG_SFU_SUBSCRIBE,
        is_valid_client_type,
    )

    for msg_type in (
        MSG_JOIN,
        MSG_LEAVE,
        MSG_OFFER,
        MSG_ANSWER,
        MSG_ICE,
        MSG_SFU_PUBLISH,
        MSG_SFU_SUBSCRIBE,
    ):
        assert is_valid_client_type(msg_type), (
            f"화이트리스트 의 정상 type {msg_type} 거부 발생 — 검증 실패"
        )

    assert len(CLIENT_MSG_TYPES) == 7


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


# ---------------------------------------------------------------------------
# SFU 그룹 통화 메시지 타입 (cycle 169.798 — SFU 확장 M3a)
# ---------------------------------------------------------------------------


def test_sfu_publish_subscribe_in_client_whitelist() -> None:
    """SFU_PUBLISH / SFU_SUBSCRIBE 는 클라 → 서버 허용 타입이어야 한다."""

    from server.protocol import (
        MSG_SFU_PUBLISH,
        MSG_SFU_SUBSCRIBE,
        is_valid_client_type,
    )

    assert is_valid_client_type(MSG_SFU_PUBLISH)
    assert is_valid_client_type(MSG_SFU_SUBSCRIBE)
    assert is_valid_client_type("SFU_PUBLISH")
    assert is_valid_client_type("SFU_SUBSCRIBE")


def test_sfu_server_to_client_types_rejected_as_client_input() -> None:
    """SFU_PRODUCERS / SFU_ANSWER 는 서버 → 클라 전용 — 클라 입력으로 거부."""

    from server.protocol import (
        MSG_SFU_ANSWER,
        MSG_SFU_PRODUCERS,
        is_valid_client_type,
    )

    # 서버 → 클라 방향 타입을 클라 입력으로 받으면 화이트리스트 위반
    assert not is_valid_client_type(MSG_SFU_PRODUCERS)
    assert not is_valid_client_type(MSG_SFU_ANSWER)


def test_sfu_message_type_constants_stable() -> None:
    """SFU 타입 식별자 문자열의 안정성 (와이어 호환 — 변경 시 클라 깨짐)."""

    from server import protocol

    assert protocol.MSG_SFU_PUBLISH == "SFU_PUBLISH"
    assert protocol.MSG_SFU_SUBSCRIBE == "SFU_SUBSCRIBE"
    assert protocol.MSG_SFU_PRODUCERS == "SFU_PRODUCERS"
    assert protocol.MSG_SFU_ANSWER == "SFU_ANSWER"
    assert protocol.ERR_SFU_NO_PRODUCER == "SFU_NO_PRODUCER"
