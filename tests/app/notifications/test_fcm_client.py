# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.notifications.fcm_client`` 의 단위 테스트.

firebase-admin SDK 미설치 환경 의 graceful is_available False + send
시 FCMUnavailableError + invalid target reject.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.notifications.fcm_client import (
    FCMClient,
    FCMError,
    FCMInvalidTargetError,
    FCMUnavailableError,
    from_env,
)
from app.notifications.push import Platform, PushPayload, PushTarget


def _fcm_target(token: str = "test-token-abc") -> PushTarget:
    return PushTarget(
        user_id=1,
        device_id="device-1",
        platform=Platform.FCM,
        push_token=token,
    )


def _apns_target() -> PushTarget:
    return PushTarget(
        user_id=2,
        device_id="device-2",
        platform=Platform.APNS,
        push_token="apns-token-xyz",
    )


class TestFCMClientAvailability:
    """firebase-admin import 가용 여부 검증."""

    def test_is_available_returns_bool(self) -> None:
        result = FCMClient.is_available()
        assert isinstance(result, bool)

    def test_client_construction_lazy(self) -> None:
        # 한글 주석: __init__ 에서 firebase-admin 호출 부재 — lazy init
        client = FCMClient(credential_path="/nonexistent/path.json")
        assert client._initialized is False
        assert client._app is None


class TestFCMClientInitialize:
    """initialize() 의 graceful + error 경로 검증."""

    def test_initialize_no_sdk_raises_unavailable(self) -> None:
        # 한글 주석: firebase-admin 미설치 환경 시 FCMUnavailableError
        client = FCMClient(credential_path="/nonexistent.json")
        with patch("app.notifications.fcm_client._FIREBASE_AVAILABLE", False):
            with pytest.raises(FCMUnavailableError, match="firebase-admin"):
                client.initialize()

    def test_initialize_missing_cred_path_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("FCM_CREDENTIAL_PATH", raising=False)
        # 한글 주석: SDK 가용 가정 + cred_path 부재 시 FCMUnavailableError
        client = FCMClient()
        with patch("app.notifications.fcm_client._FIREBASE_AVAILABLE", True):
            with pytest.raises(FCMUnavailableError, match="경로 부재"):
                client.initialize()

    def test_initialize_nonexistent_cred_raises(self) -> None:
        client = FCMClient(credential_path="/tmp/definitely-not-exists-abc.json")
        with patch("app.notifications.fcm_client._FIREBASE_AVAILABLE", True):
            with pytest.raises(FCMUnavailableError, match="부재"):
                client.initialize()


class TestFCMSendValidation:
    """send() 의 target validation 검증."""

    def test_send_non_fcm_platform_raises(self) -> None:
        client = FCMClient()
        payload = PushPayload(
            target=_apns_target(),
            title="test",
            body="body",
            data={},
            collapse_key=None,
        )
        with pytest.raises(FCMInvalidTargetError, match="FCM platform"):
            client.send(payload)

    def test_send_missing_token_raises(self) -> None:
        # 한글 주석: push_token 의 빈 값 검증 — PushTarget validation 회피용 직접 build
        target = PushTarget(
            user_id=1,
            device_id="device-1",
            platform=Platform.FCM,
            push_token="placeholder",
        )
        # 한글 주석: frozen dataclass — object.__setattr__ 로 강제 token 비우기
        object.__setattr__(target, "push_token", None)
        client = FCMClient()
        payload = PushPayload(
            target=target,
            title="t",
            body="b",
            data={},
            collapse_key=None,
        )
        with pytest.raises(FCMInvalidTargetError, match="push_token 부재"):
            client.send(payload)


class TestFromEnv:
    """from_env factory 의 environment variable parse."""

    def test_from_env_reads_credential_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FCM_CREDENTIAL_PATH", "/run/secrets/fcm.json")
        monkeypatch.setenv("FCM_PROJECT_ID", "tootalk-prod")
        client = from_env()
        assert client.credential_path == "/run/secrets/fcm.json"
        assert client.project_id == "tootalk-prod"

    def test_from_env_no_credentials_no_raise(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("FCM_CREDENTIAL_PATH", raising=False)
        monkeypatch.delenv("FCM_PROJECT_ID", raising=False)
        # 한글 주석: factory 호출 자체는 PASS — initialize() 호출 시점 에 raise
        client = from_env()
        assert client.credential_path is None
        assert client.project_id is None
