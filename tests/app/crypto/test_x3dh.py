# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.crypto.x3dh`` X3DH initial key agreement 단위 테스트."""

from __future__ import annotations

import pytest

from app.crypto.e2ee import generate_x25519_keypair
from app.crypto.x3dh import (
    PreKeyBundle,
    x3dh_initiator,
    x3dh_responder,
)


class TestPreKeyBundleValidation:
    def test_valid_bundle(self) -> None:
        bundle = PreKeyBundle(
            identity_public=b"\x01" * 32,
            signed_prekey_public=b"\x02" * 32,
            one_time_prekey_public=b"\x03" * 32,
        )
        assert len(bundle.identity_public) == 32
        assert bundle.one_time_prekey_public is not None

    def test_no_opk(self) -> None:
        bundle = PreKeyBundle(
            identity_public=b"\x01" * 32,
            signed_prekey_public=b"\x02" * 32,
        )
        assert bundle.one_time_prekey_public is None

    def test_invalid_identity_length(self) -> None:
        with pytest.raises(ValueError, match="identity_public"):
            PreKeyBundle(
                identity_public=b"\x01" * 31,
                signed_prekey_public=b"\x02" * 32,
            )

    def test_invalid_spk_length(self) -> None:
        with pytest.raises(ValueError, match="signed_prekey_public"):
            PreKeyBundle(
                identity_public=b"\x01" * 32,
                signed_prekey_public=b"\x02" * 30,
            )

    def test_invalid_opk_length(self) -> None:
        with pytest.raises(ValueError, match="one_time_prekey_public"):
            PreKeyBundle(
                identity_public=b"\x01" * 32,
                signed_prekey_public=b"\x02" * 32,
                one_time_prekey_public=b"\x03" * 33,
            )


class TestX3DHFullFlow:
    def test_alice_bob_with_opk(self) -> None:
        """Alice + Bob 의 X3DH 결과 동일 (peer 대칭) — OPK 포함."""

        # Bob 측 keypair 4종 (IK + SPK + OPK)
        bob_ik_priv, bob_ik_pub = generate_x25519_keypair()
        bob_spk_priv, bob_spk_pub = generate_x25519_keypair()
        bob_opk_priv, bob_opk_pub = generate_x25519_keypair()

        # Alice 측 IK
        alice_ik_priv, alice_ik_pub = generate_x25519_keypair()

        # Alice initiator
        bob_bundle = PreKeyBundle(
            identity_public=bob_ik_pub,
            signed_prekey_public=bob_spk_pub,
            one_time_prekey_public=bob_opk_pub,
        )
        ek_pub, ek_priv, alice_shared = x3dh_initiator(
            my_identity_private=alice_ik_priv,
            bob_bundle=bob_bundle,
        )

        # Bob responder
        bob_shared = x3dh_responder(
            my_identity_private=bob_ik_priv,
            my_signed_prekey_private=bob_spk_priv,
            my_one_time_prekey_private=bob_opk_priv,
            alice_identity_public=alice_ik_pub,
            alice_ephemeral_public=ek_pub,
        )

        # 양측 shared secret 동일 = 32 byte
        assert alice_shared == bob_shared
        assert len(alice_shared) == 32

    def test_alice_bob_without_opk(self) -> None:
        """OPK fallback — Alice + Bob 동일 (security 약화 단 동기 가능)."""

        bob_ik_priv, bob_ik_pub = generate_x25519_keypair()
        bob_spk_priv, bob_spk_pub = generate_x25519_keypair()
        alice_ik_priv, alice_ik_pub = generate_x25519_keypair()

        bundle = PreKeyBundle(
            identity_public=bob_ik_pub,
            signed_prekey_public=bob_spk_pub,
        )
        ek_pub, _, alice_shared = x3dh_initiator(
            my_identity_private=alice_ik_priv,
            bob_bundle=bundle,
        )
        bob_shared = x3dh_responder(
            my_identity_private=bob_ik_priv,
            my_signed_prekey_private=bob_spk_priv,
            my_one_time_prekey_private=None,
            alice_identity_public=alice_ik_pub,
            alice_ephemeral_public=ek_pub,
        )
        assert alice_shared == bob_shared

    def test_distinct_eve_cannot_derive(self) -> None:
        """Eve (third-party) 의 의 shared = Alice/Bob 와 다름."""

        bob_ik_priv, bob_ik_pub = generate_x25519_keypair()
        bob_spk_priv, bob_spk_pub = generate_x25519_keypair()
        alice_ik_priv, alice_ik_pub = generate_x25519_keypair()
        eve_ik_priv, _ = generate_x25519_keypair()

        bundle = PreKeyBundle(
            identity_public=bob_ik_pub,
            signed_prekey_public=bob_spk_pub,
        )
        _, _, alice_shared = x3dh_initiator(
            my_identity_private=alice_ik_priv,
            bob_bundle=bundle,
        )
        # Eve 의 다른 IK 의 X3DH = 다른 결과
        ek_pub_eve, _, eve_shared = x3dh_initiator(
            my_identity_private=eve_ik_priv,
            bob_bundle=bundle,
        )
        assert alice_shared != eve_shared

    def test_initiator_invalid_ik_length(self) -> None:
        bundle = PreKeyBundle(
            identity_public=b"\x01" * 32,
            signed_prekey_public=b"\x02" * 32,
        )
        with pytest.raises(ValueError, match="my_identity_private"):
            x3dh_initiator(
                my_identity_private=b"\x42" * 31,
                bob_bundle=bundle,
            )

    def test_responder_invalid_length(self) -> None:
        with pytest.raises(ValueError, match="32 의무"):
            x3dh_responder(
                my_identity_private=b"\x01" * 30,
                my_signed_prekey_private=b"\x02" * 32,
                my_one_time_prekey_private=None,
                alice_identity_public=b"\x03" * 32,
                alice_ephemeral_public=b"\x04" * 32,
            )

    def test_shared_secret_distinct_per_call(self) -> None:
        """Alice 의 매 X3DH 호출 = 새 ephemeral → 새 shared (forward secrecy)."""

        bob_ik_priv, bob_ik_pub = generate_x25519_keypair()
        _, bob_spk_pub = generate_x25519_keypair()
        alice_ik_priv, _ = generate_x25519_keypair()
        bundle = PreKeyBundle(
            identity_public=bob_ik_pub,
            signed_prekey_public=bob_spk_pub,
        )
        _, _, s1 = x3dh_initiator(my_identity_private=alice_ik_priv, bob_bundle=bundle)
        _, _, s2 = x3dh_initiator(my_identity_private=alice_ik_priv, bob_bundle=bundle)
        assert s1 != s2
