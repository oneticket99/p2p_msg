# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.crypto.session`` Double Ratchet session state 단위 테스트."""

from __future__ import annotations

import pytest

from app.crypto.session import (
    SessionState,
    initialize_session_initiator,
    initialize_session_responder,
)


class TestSessionStateValidation:
    def test_valid_state(self) -> None:
        s = SessionState(
            root_key=b"\x42" * 32,
            my_dh_private=b"\x01" * 32,
            my_dh_public=b"\x02" * 32,
        )
        assert s.sending_chain is None
        assert s.receiving_chain is None
        assert s.peer_dh_public is None

    def test_invalid_root_key_length(self) -> None:
        with pytest.raises(ValueError, match="root_key 길이"):
            SessionState(
                root_key=b"\x42" * 31,
                my_dh_private=b"\x01" * 32,
                my_dh_public=b"\x02" * 32,
            )

    def test_invalid_dh_private_length(self) -> None:
        with pytest.raises(ValueError, match="my_dh_private"):
            SessionState(
                root_key=b"\x42" * 32,
                my_dh_private=b"\x01" * 31,
                my_dh_public=b"\x02" * 32,
            )

    def test_invalid_peer_dh_public(self) -> None:
        with pytest.raises(ValueError, match="peer_dh_public"):
            SessionState(
                root_key=b"\x42" * 32,
                my_dh_private=b"\x01" * 32,
                my_dh_public=b"\x02" * 32,
                peer_dh_public=b"\x03" * 31,
            )


class TestInitiator:
    def test_basic_init(self) -> None:
        # peer_dh_public 32 byte 가짜 (실 X25519 point 아님 — exchange 단순 검증)
        ss = b"\x42" * 32
        peer_pk = b"\x01" * 32
        state = initialize_session_initiator(shared_secret=ss, peer_dh_public=peer_pk)
        assert state.sending_chain is not None
        assert state.sending_chain.counter == 0
        assert len(state.sending_chain.key) == 32
        # root key advanced (shared_secret 와 다름)
        assert state.root_key != ss
        assert state.peer_dh_public == peer_pk
        # 본인 keypair 생성 검증
        assert len(state.my_dh_private) == 32
        assert len(state.my_dh_public) == 32

    def test_invalid_shared_secret(self) -> None:
        with pytest.raises(ValueError, match="shared_secret"):
            initialize_session_initiator(
                shared_secret=b"\x42" * 31, peer_dh_public=b"\x01" * 32
            )

    def test_invalid_peer_public(self) -> None:
        with pytest.raises(ValueError, match="peer_dh_public"):
            initialize_session_initiator(
                shared_secret=b"\x42" * 32, peer_dh_public=b"\x01" * 30
            )

    def test_distinct_root_per_call(self) -> None:
        # 같은 input 단 my_keypair random → root_key 별개
        ss = b"\x42" * 32
        peer_pk = b"\x01" * 32
        s1 = initialize_session_initiator(shared_secret=ss, peer_dh_public=peer_pk)
        s2 = initialize_session_initiator(shared_secret=ss, peer_dh_public=peer_pk)
        # 의 my_keypair 의 random 의 root_key 의 결과 별개
        assert s1.root_key != s2.root_key


class TestResponder:
    def test_basic_init(self) -> None:
        ss = b"\x42" * 32
        state = initialize_session_responder(shared_secret=ss)
        # 첫 DH ratchet 전 = root = shared_secret
        assert state.root_key == ss
        assert state.sending_chain is None
        assert state.receiving_chain is None
        assert state.peer_dh_public is None
        assert len(state.my_dh_private) == 32
        assert len(state.my_dh_public) == 32

    def test_invalid_shared_secret(self) -> None:
        with pytest.raises(ValueError, match="shared_secret"):
            initialize_session_responder(shared_secret=b"\x42" * 33)

    def test_unique_keypair(self) -> None:
        # 매 호출 random keypair
        ss = b"\x42" * 32
        s1 = initialize_session_responder(shared_secret=ss)
        s2 = initialize_session_responder(shared_secret=ss)
        assert s1.my_dh_private != s2.my_dh_private
        assert s1.my_dh_public != s2.my_dh_public
