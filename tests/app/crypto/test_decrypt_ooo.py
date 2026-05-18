# SPDX-License-Identifier: GPL-3.0-or-later
"""``decrypt_with_session_ooo`` out-of-order delivery 통합 테스트."""

from __future__ import annotations

import pytest
from cryptography.exceptions import InvalidTag

from app.crypto.double_ratchet import ChainKey, encrypt_message
from app.crypto.e2ee import EncryptedPayload, generate_x25519_keypair
from app.crypto.session import (
    SessionState,
    decrypt_with_session_ooo,
)
from app.crypto.skipped_keys import SkippedKeyStore


_SENDER_PK = b"\x01" * 32


def _make_state_with_chain(chain_key: bytes, counter: int = 0) -> SessionState:
    return SessionState(
        root_key=b"\x42" * 32,
        my_dh_private=b"\x10" * 32,
        my_dh_public=b"\x11" * 32,
        peer_dh_public=_SENDER_PK,
        sending_chain=None,
        receiving_chain=ChainKey(key=chain_key, counter=counter),
        skipped_store=SkippedKeyStore(),
    )


class TestDecryptOOO:
    def test_in_order_delivery(self) -> None:
        """counter = chain.counter — 정상 forward."""

        root_key = b"\x42" * 32
        # 송신 단 chain (Alice) + 수신 단 chain (Bob) 동기 시작
        send_chain = ChainKey(key=root_key, counter=0)
        state = _make_state_with_chain(root_key, counter=0)

        payload, _ = encrypt_message(send_chain, b"msg-0")
        decoded, new_state = decrypt_with_session_ooo(
            state, payload, sender_dh_public=_SENDER_PK, counter=0
        )
        assert decoded == b"msg-0"
        assert new_state.receiving_chain.counter == 1

    def test_out_of_order_2_then_1(self) -> None:
        """송신 counter 0, 1, 2 — 수신 0, 2, 1 (1 = ooo)."""

        root_key = b"\x42" * 32
        send_chain = ChainKey(key=root_key, counter=0)

        # 3 메시지 송신 (counter 0/1/2)
        p0, send_chain = encrypt_message(send_chain, b"msg-0")
        p1, send_chain = encrypt_message(send_chain, b"msg-1")
        p2, send_chain = encrypt_message(send_chain, b"msg-2")

        state = _make_state_with_chain(root_key, counter=0)

        # 1. counter 0 정상 수신
        decoded0, state = decrypt_with_session_ooo(
            state, p0, sender_dh_public=_SENDER_PK, counter=0
        )
        assert decoded0 == b"msg-0"
        # receiving_chain counter = 1 (advance)

        # 2. counter 2 도착 (1 skip) — skipped_store 에 counter 1 의 key 보관
        decoded2, state = decrypt_with_session_ooo(
            state, p2, sender_dh_public=_SENDER_PK, counter=2
        )
        assert decoded2 == b"msg-2"
        # receiving_chain counter = 3 (advance)
        assert state.receiving_chain.counter == 3
        # skipped_store 에 counter 1 보관됨
        assert len(state.skipped_store) == 1

        # 3. counter 1 (out-of-order) 도착 — store fallback
        decoded1, state = decrypt_with_session_ooo(
            state, p1, sender_dh_public=_SENDER_PK, counter=1
        )
        assert decoded1 == b"msg-1"
        # store 의 counter 1 use + 폐기 (one-shot)
        assert len(state.skipped_store) == 0

    def test_replay_detection(self) -> None:
        """동일 counter 의 OOO 재수신 = store empty → ValueError."""

        root_key = b"\x42" * 32
        send_chain = ChainKey(key=root_key, counter=0)
        p0, _ = encrypt_message(send_chain, b"msg-0")

        state = _make_state_with_chain(root_key, counter=0)
        _, state = decrypt_with_session_ooo(
            state, p0, sender_dh_public=_SENDER_PK, counter=0
        )
        # counter 0 재전송 = chain advance (counter=1) + store empty
        with pytest.raises(ValueError, match="counter 0 < chain.counter 1"):
            decrypt_with_session_ooo(
                state, p0, sender_dh_public=_SENDER_PK, counter=0
            )

    def test_missing_store_runtime_error(self) -> None:
        state = SessionState(
            root_key=b"\x42" * 32,
            my_dh_private=b"\x10" * 32,
            my_dh_public=b"\x11" * 32,
            peer_dh_public=_SENDER_PK,
            sending_chain=None,
            receiving_chain=ChainKey(key=b"\x42" * 32),
            skipped_store=None,
        )
        with pytest.raises(RuntimeError, match="skipped_store"):
            decrypt_with_session_ooo(
                state,
                EncryptedPayload(nonce=b"\x00" * 12, ciphertext=b"\x00" * 16),
                sender_dh_public=_SENDER_PK,
                counter=0,
            )

    def test_missing_receiving_chain(self) -> None:
        state = SessionState(
            root_key=b"\x42" * 32,
            my_dh_private=b"\x10" * 32,
            my_dh_public=b"\x11" * 32,
            peer_dh_public=_SENDER_PK,
            sending_chain=None,
            receiving_chain=None,
            skipped_store=SkippedKeyStore(),
        )
        with pytest.raises(RuntimeError, match="receiving_chain"):
            decrypt_with_session_ooo(
                state,
                EncryptedPayload(nonce=b"\x00" * 12, ciphertext=b"\x00" * 16),
                sender_dh_public=_SENDER_PK,
                counter=0,
            )

    def test_tampered_ciphertext(self) -> None:
        root_key = b"\x42" * 32
        send_chain = ChainKey(key=root_key, counter=0)
        p0, _ = encrypt_message(send_chain, b"original")
        # ciphertext 1 byte flip
        tampered = bytearray(p0.ciphertext)
        tampered[0] ^= 0x01
        p0_bad = EncryptedPayload(nonce=p0.nonce, ciphertext=bytes(tampered))
        state = _make_state_with_chain(root_key, counter=0)
        with pytest.raises(InvalidTag):
            decrypt_with_session_ooo(
                state, p0_bad, sender_dh_public=_SENDER_PK, counter=0
            )
