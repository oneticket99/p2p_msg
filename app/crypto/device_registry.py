# SPDX-License-Identifier: GPL-3.0-or-later
"""multi-device sync — 사용자 1명 의 N대 device identity registry.

Phase 2 사이클 42 진입 — Signal Protocol multi-device 모델 정합.
사용자 1명 = N대 device (desktop / mobile / tablet). 각 device 는 별도
X3DH identity_key + signed_prekey + one_time_prekey 보유. 메시지 송신 시
모든 device 로 fan-out 송신 의무 (sender 는 매 recipient device 마다
별도 ratchet session 보유).

본 module 범위
-------------
- ``DeviceIdentity`` dataclass — device_id + user_id + PreKeyBundle 묶음
- ``DeviceRegistry`` — user_id → device list mapping + lookup + add/remove
- ``serialize_bundle`` / ``deserialize_bundle`` — wire format (JSON-safe)
- ``serialize_device`` / ``deserialize_device`` — device 직렬화 (서버 storage)

범위 외 (다음 cycle)
-------------------
- 서버 endpoint (POST /devices · GET /devices/<user_id>)
- X3DH session 의 fan-out 송신 (encrypt 의 매 recipient device loop)
- device 추가/제거 시 sender 의 sync 메시지 (Signal 의 SenderKey 모델)
- multi-device key rotation 정책 (signed prekey rotation 주기)

설계 결정
---------
- ``device_id`` = client-generated UUID4 (server fingerprint 검증 후 등록).
  동일 device 재설치 = 새 device_id 발급.
- ``DeviceRegistry`` = pure in-memory dict. 영속화 = 서버 storage 의무
  (별도 cycle). 클라이언트 = 서버 fetch 후 cache 보관.
- bundle wire format = base64-encoded bytes + JSON. 32-byte X25519 키 = 44
  char base64 (padding 포함).
"""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.crypto.x3dh import PreKeyBundle

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeviceIdentity:
    """단일 device 의 identity + X3DH bundle.

    Attributes
    ----------
    device_id : str
        client-generated UUID4 또는 임의 식별자 (서버 unique 의무).
    user_id : int
        소유자 user_id (server users.id FK).
    bundle : PreKeyBundle
        device 공개 X3DH bundle (peer 단말 X3DH initiator 호출 대상).
    label : str
        사용자 친화 표시명 (예: "Daisy 의 MacBook"). 빈 문자열 허용.
    """

    device_id: str
    user_id: int
    bundle: PreKeyBundle
    label: str = ""

    def __post_init__(self) -> None:
        if not self.device_id or not self.device_id.strip():
            raise ValueError("device_id 빈 값 = 무효")
        if self.user_id <= 0:
            raise ValueError(f"user_id = {self.user_id} (양수 의무)")


@dataclass
class DeviceRegistry:
    """user_id → DeviceIdentity 리스트 mapping.

    in-memory cache. 영속화 = 서버 storage 의무. add/remove/lookup 단순
    dict 조작 + 정합 검증 의무.
    """

    devices: Dict[int, List[DeviceIdentity]] = field(default_factory=dict)

    def add(self, device: DeviceIdentity) -> None:
        """device 등록. user 의 첫 device = 새 list 생성. 중복 device_id = 차단."""

        user_devices = self.devices.setdefault(device.user_id, [])
        for existing in user_devices:
            if existing.device_id == device.device_id:
                raise ValueError(
                    f"device_id={device.device_id} 중복 (user_id={device.user_id})"
                )
        user_devices.append(device)

    def remove(self, user_id: int, device_id: str) -> bool:
        """device 제거. 찾지 못한 경우 False, 제거 성공 = True.

        user_id 의 마지막 device 제거 시 = devices[user_id] 빈 list 잔존
        (key 의 의 자동 삭제 안 함 — pop 의무).
        """

        user_devices = self.devices.get(user_id, [])
        for idx, existing in enumerate(user_devices):
            if existing.device_id == device_id:
                user_devices.pop(idx)
                return True
        return False

    def get_devices(self, user_id: int) -> List[DeviceIdentity]:
        """user_id 의 모든 device 반환. 미등록 user = 빈 list (KeyError 미발생)."""

        return list(self.devices.get(user_id, []))

    def get_device(self, user_id: int, device_id: str) -> Optional[DeviceIdentity]:
        """단일 device lookup. 미등록 = None."""

        for existing in self.devices.get(user_id, []):
            if existing.device_id == device_id:
                return existing
        return None

    def __len__(self) -> int:
        """전체 등록 device 총 수 (모든 user 합산)."""

        return sum(len(lst) for lst in self.devices.values())


# ---------------------------------------------------------------------------
# wire format — base64 + JSON (서버 endpoint + 클라이언트 cache 정합)
# ---------------------------------------------------------------------------


def serialize_bundle(bundle: PreKeyBundle) -> dict:
    """``PreKeyBundle`` → JSON-safe dict.

    Returns
    -------
    dict
        ``{"identity_public": <base64>, "signed_prekey_public": <base64>,
        "one_time_prekey_public": <base64 | null>}``.
    """

    return {
        "identity_public": base64.b64encode(bundle.identity_public).decode("ascii"),
        "signed_prekey_public": base64.b64encode(bundle.signed_prekey_public).decode("ascii"),
        "one_time_prekey_public": (
            base64.b64encode(bundle.one_time_prekey_public).decode("ascii")
            if bundle.one_time_prekey_public is not None
            else None
        ),
    }


def deserialize_bundle(data: dict) -> PreKeyBundle:
    """JSON-safe dict → ``PreKeyBundle``.

    필드 누락 = KeyError. 길이 검증 = ``PreKeyBundle.__post_init__`` 위임.
    """

    opk_b64 = data.get("one_time_prekey_public")
    opk_bytes: Optional[bytes] = (
        base64.b64decode(opk_b64) if opk_b64 is not None else None
    )
    return PreKeyBundle(
        identity_public=base64.b64decode(data["identity_public"]),
        signed_prekey_public=base64.b64decode(data["signed_prekey_public"]),
        one_time_prekey_public=opk_bytes,
    )


def serialize_device(device: DeviceIdentity) -> dict:
    """``DeviceIdentity`` → JSON-safe dict (서버 storage / wire format)."""

    return {
        "device_id": device.device_id,
        "user_id": device.user_id,
        "label": device.label,
        "bundle": serialize_bundle(device.bundle),
    }


def deserialize_device(data: dict) -> DeviceIdentity:
    """JSON-safe dict → ``DeviceIdentity``.

    필드 누락 = KeyError. label 누락 = 빈 문자열 폴백.
    """

    return DeviceIdentity(
        device_id=data["device_id"],
        user_id=data["user_id"],
        bundle=deserialize_bundle(data["bundle"]),
        label=data.get("label", ""),
    )


def serialize_devices_json(devices: List[DeviceIdentity]) -> str:
    """다수 device 의 JSON wire format 직렬화 (서버 GET /devices/<user_id>)."""

    return json.dumps([serialize_device(d) for d in devices], ensure_ascii=False)


def deserialize_devices_json(payload: str) -> List[DeviceIdentity]:
    """JSON wire format → device list. 빈 list 허용."""

    raw = json.loads(payload)
    if not isinstance(raw, list):
        raise ValueError("devices wire format = list 의무")
    return [deserialize_device(item) for item in raw]
