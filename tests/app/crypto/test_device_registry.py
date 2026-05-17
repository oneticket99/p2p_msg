# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.crypto.device_registry`` 단위 테스트.

multi-device sync skeleton — DeviceIdentity dataclass + DeviceRegistry 의
add/remove/lookup + wire format serialize/deserialize 검증.
"""

from __future__ import annotations

import json

import pytest

from app.crypto.device_registry import (
    DeviceIdentity,
    DeviceRegistry,
    deserialize_bundle,
    deserialize_device,
    deserialize_devices_json,
    serialize_bundle,
    serialize_device,
    serialize_devices_json,
)
from app.crypto.x3dh import PreKeyBundle


def _make_bundle(seed: int = 1) -> PreKeyBundle:
    """test fixture — 32-byte deterministic seed 기반 PreKeyBundle."""

    base = bytes([seed % 256]) * 32
    return PreKeyBundle(
        identity_public=base,
        signed_prekey_public=bytes([(seed + 1) % 256]) * 32,
        one_time_prekey_public=bytes([(seed + 2) % 256]) * 32,
    )


def _make_device(
    device_id: str = "dev-1",
    user_id: int = 42,
    seed: int = 1,
    label: str = "",
) -> DeviceIdentity:
    return DeviceIdentity(
        device_id=device_id,
        user_id=user_id,
        bundle=_make_bundle(seed),
        label=label,
    )


class TestDeviceIdentityValidation:
    def test_valid_device(self) -> None:
        device = _make_device()
        assert device.device_id == "dev-1"
        assert device.user_id == 42
        assert device.label == ""

    def test_empty_device_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="device_id"):
            _make_device(device_id="")

    def test_whitespace_device_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="device_id"):
            _make_device(device_id="   ")

    def test_zero_user_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="user_id"):
            _make_device(user_id=0)

    def test_negative_user_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="user_id"):
            _make_device(user_id=-5)

    def test_label_preserved(self) -> None:
        device = _make_device(label="Daisy 의 MacBook")
        assert device.label == "Daisy 의 MacBook"


class TestDeviceRegistryAdd:
    def test_first_device(self) -> None:
        reg = DeviceRegistry()
        reg.add(_make_device(device_id="dev-1", user_id=1))
        assert len(reg) == 1

    def test_multiple_devices_same_user(self) -> None:
        reg = DeviceRegistry()
        reg.add(_make_device(device_id="dev-1", user_id=1))
        reg.add(_make_device(device_id="dev-2", user_id=1, seed=2))
        assert len(reg) == 2
        assert len(reg.get_devices(1)) == 2

    def test_multiple_users(self) -> None:
        reg = DeviceRegistry()
        reg.add(_make_device(device_id="dev-1", user_id=1))
        reg.add(_make_device(device_id="dev-1", user_id=2))
        assert len(reg) == 2
        assert len(reg.get_devices(1)) == 1
        assert len(reg.get_devices(2)) == 1

    def test_duplicate_device_id_same_user_rejected(self) -> None:
        reg = DeviceRegistry()
        reg.add(_make_device(device_id="dev-1", user_id=1))
        with pytest.raises(ValueError, match="중복"):
            reg.add(_make_device(device_id="dev-1", user_id=1, seed=99))


class TestDeviceRegistryRemove:
    def test_remove_existing(self) -> None:
        reg = DeviceRegistry()
        reg.add(_make_device(device_id="dev-1", user_id=1))
        reg.add(_make_device(device_id="dev-2", user_id=1, seed=2))
        result = reg.remove(user_id=1, device_id="dev-1")
        assert result is True
        assert len(reg.get_devices(1)) == 1
        assert reg.get_devices(1)[0].device_id == "dev-2"

    def test_remove_missing_user(self) -> None:
        reg = DeviceRegistry()
        result = reg.remove(user_id=999, device_id="dev-1")
        assert result is False

    def test_remove_missing_device(self) -> None:
        reg = DeviceRegistry()
        reg.add(_make_device(device_id="dev-1", user_id=1))
        result = reg.remove(user_id=1, device_id="dev-2")
        assert result is False
        assert len(reg.get_devices(1)) == 1


class TestDeviceRegistryLookup:
    def test_get_devices_empty_user(self) -> None:
        reg = DeviceRegistry()
        assert reg.get_devices(99) == []

    def test_get_device_found(self) -> None:
        reg = DeviceRegistry()
        device = _make_device(device_id="dev-x", user_id=5)
        reg.add(device)
        result = reg.get_device(user_id=5, device_id="dev-x")
        assert result is not None
        assert result.device_id == "dev-x"

    def test_get_device_missing(self) -> None:
        reg = DeviceRegistry()
        assert reg.get_device(user_id=5, device_id="missing") is None

    def test_get_devices_returns_copy(self) -> None:
        """get_devices 결과 mutation 시 내부 list 보존."""

        reg = DeviceRegistry()
        reg.add(_make_device(device_id="dev-1", user_id=1))
        external = reg.get_devices(1)
        external.clear()
        assert len(reg.get_devices(1)) == 1


class TestSerializeBundle:
    def test_roundtrip_with_opk(self) -> None:
        bundle = _make_bundle(seed=10)
        wire = serialize_bundle(bundle)
        assert isinstance(wire, dict)
        restored = deserialize_bundle(wire)
        assert restored.identity_public == bundle.identity_public
        assert restored.signed_prekey_public == bundle.signed_prekey_public
        assert restored.one_time_prekey_public == bundle.one_time_prekey_public

    def test_roundtrip_without_opk(self) -> None:
        bundle = PreKeyBundle(
            identity_public=b"\x01" * 32,
            signed_prekey_public=b"\x02" * 32,
        )
        wire = serialize_bundle(bundle)
        assert wire["one_time_prekey_public"] is None
        restored = deserialize_bundle(wire)
        assert restored.one_time_prekey_public is None

    def test_json_compatible(self) -> None:
        """wire dict = json.dumps 가능 의무."""

        bundle = _make_bundle()
        wire = serialize_bundle(bundle)
        serialized = json.dumps(wire)
        reloaded = json.loads(serialized)
        restored = deserialize_bundle(reloaded)
        assert restored.identity_public == bundle.identity_public


class TestSerializeDevice:
    def test_roundtrip(self) -> None:
        device = _make_device(device_id="dev-z", user_id=99, label="태블릿")
        wire = serialize_device(device)
        restored = deserialize_device(wire)
        assert restored.device_id == "dev-z"
        assert restored.user_id == 99
        assert restored.label == "태블릿"
        assert restored.bundle.identity_public == device.bundle.identity_public

    def test_missing_label_default(self) -> None:
        device = _make_device()
        wire = serialize_device(device)
        del wire["label"]
        restored = deserialize_device(wire)
        assert restored.label == ""


class TestSerializeDevicesJson:
    def test_empty_list(self) -> None:
        payload = serialize_devices_json([])
        assert payload == "[]"
        assert deserialize_devices_json(payload) == []

    def test_multiple_devices(self) -> None:
        d1 = _make_device(device_id="d1", user_id=1, seed=1)
        d2 = _make_device(device_id="d2", user_id=1, seed=2, label="phone")
        payload = serialize_devices_json([d1, d2])
        restored = deserialize_devices_json(payload)
        assert len(restored) == 2
        assert restored[0].device_id == "d1"
        assert restored[1].device_id == "d2"
        assert restored[1].label == "phone"

    def test_invalid_root_rejected(self) -> None:
        with pytest.raises(ValueError, match="list"):
            deserialize_devices_json('{"not": "a list"}')

    def test_korean_label_utf8(self) -> None:
        """ensure_ascii=False → 한글 label 의 raw UTF-8 보존."""

        device = _make_device(label="홍원표 의 노트북")
        payload = serialize_devices_json([device])
        # raw 한글 보존 검증 (escape sequence 미사용)
        assert "홍원표" in payload
        restored = deserialize_devices_json(payload)
        assert restored[0].label == "홍원표 의 노트북"
