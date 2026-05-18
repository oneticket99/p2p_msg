# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.crypto.session`` Double Ratchet session state 단위 테스트."""

from __future__ import annotations

import pytest

from app.crypto.double_ratchet import ChainKey
from app.crypto.e2ee import generate_x25519_keypair
from app.crypto.session import (
    SessionState,
    _skip_forward_chain_keys,
    advance_dh_ratchet,
    initialize_session_initiator,
    initialize_session_responder,
)
from app.crypto.skipped_keys import SkippedKeyStore


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
        # self keypair 생성 검증
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


class TestAdvanceDhRatchet:
    def test_invalid_peer_public(self) -> None:
        state = initialize_session_responder(shared_secret=b"\x42" * 32)
        with pytest.raises(ValueError, match="new_peer_dh_public"):
            advance_dh_ratchet(state, b"\x01" * 30)

    def test_both_chains_activated(self) -> None:
        # 실 X25519 keypair 필요 (가짜 peer pk 의 ECDH 결과 = 의미 없음 단 32 byte syntactic)
        _, peer_pk = generate_x25519_keypair()
        state = initialize_session_responder(shared_secret=b"\x42" * 32)
        next_state = advance_dh_ratchet(state, peer_pk)

        assert next_state.sending_chain is not None
        assert next_state.receiving_chain is not None
        assert next_state.sending_chain.counter == 0
        assert next_state.receiving_chain.counter == 0

    def test_keypair_rotated(self) -> None:
        # forward secrecy = self keypair 갱신
        _, peer_pk = generate_x25519_keypair()
        state = initialize_session_responder(shared_secret=b"\x42" * 32)
        old_sk = state.my_dh_private
        old_pk = state.my_dh_public
        next_state = advance_dh_ratchet(state, peer_pk)
        assert next_state.my_dh_private != old_sk
        assert next_state.my_dh_public != old_pk

    def test_root_key_advanced_twice(self) -> None:
        # root_key 의 2회 advance (recv + send) → 초기 shared_secret 과 다름
        _, peer_pk = generate_x25519_keypair()
        state = initialize_session_responder(shared_secret=b"\x42" * 32)
        next_state = advance_dh_ratchet(state, peer_pk)
        assert next_state.root_key != state.root_key
        assert next_state.peer_dh_public == peer_pk

    def test_distinct_per_call(self) -> None:
        # 같은 peer pk 단 새 keypair → 다른 chain
        _, peer_pk = generate_x25519_keypair()
        state = initialize_session_responder(shared_secret=b"\x42" * 32)
        s1 = advance_dh_ratchet(state, peer_pk)
        s2 = advance_dh_ratchet(state, peer_pk)
        # my_dh keypair 의 random → sending_chain 별개
        assert s1.sending_chain.key != s2.sending_chain.key


class TestSkipForwardChainKeys:
    def test_no_skip(self) -> None:
        store = SkippedKeyStore()
        chain = ChainKey(key=b"\x42" * 32, counter=0)
        result = _skip_forward_chain_keys(chain, 0, b"\x01" * 32, store)
        # 동일 counter — skip 0
        assert result.counter == 0
        assert len(store) == 0

    def test_skip_3(self) -> None:
        store = SkippedKeyStore()
        chain = ChainKey(key=b"\x42" * 32, counter=0)
        result = _skip_forward_chain_keys(chain, 3, b"\x01" * 32, store)
        # 3 skip — store 의 counter 0, 1, 2 보관
        assert result.counter == 3
        assert len(store) == 3
        # counter 0, 1, 2 의 key 조회 가능 (one-shot)
        assert store.get(b"\x01" * 32, 0) is not None

    def test_target_less_than_current(self) -> None:
        store = SkippedKeyStore()
        chain = ChainKey(key=b"\x42" * 32, counter=5)
        with pytest.raises(ValueError, match="target_counter"):
            _skip_forward_chain_keys(chain, 3, b"\x01" * 32, store)

    def test_max_skip_exceeded(self) -> None:
        store = SkippedKeyStore(max_skip=200)
        chain = ChainKey(key=b"\x42" * 32, counter=0)
        with pytest.raises(ValueError, match="MAX_SKIP_PER_CHAIN"):
            _skip_forward_chain_keys(chain, 101, b"\x01" * 32, store)
