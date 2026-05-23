# SPDX-License-Identifier: GPL-3.0-or-later
"""push_client unit test — cycle 169.653 omit 제거 path 2nd.

cycle 169.635 안 omit `app/net/push_client.py` 100% pre-omit. unit test 신설.

본 file = register/unregister 의 input validation + URL composition + urllib mock.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


class TestRegisterDeviceTokenValidation:
    """register_device_token — input validation guard."""

    def test_empty_base_url_returns_none(self) -> None:
        from app.net.push_client import register_device_token

        result = register_device_token("", "tok", "fcm-x")
        assert result is None

    def test_empty_auth_token_returns_none(self) -> None:
        from app.net.push_client import register_device_token

        result = register_device_token("https://api.local", "", "fcm-x")
        assert result is None

    def test_empty_fcm_token_returns_none(self) -> None:
        from app.net.push_client import register_device_token

        result = register_device_token("https://api.local", "tok", "")
        assert result is None


class TestUnregisterDeviceTokenValidation:
    """unregister_device_token — input validation guard."""

    def test_empty_base_url_returns_false(self) -> None:
        from app.net.push_client import unregister_device_token

        assert unregister_device_token("", "tok", 1) is False

    def test_empty_auth_token_returns_false(self) -> None:
        from app.net.push_client import unregister_device_token

        assert unregister_device_token("https://api.local", "", 1) is False

    def test_zero_token_id_returns_false(self) -> None:
        from app.net.push_client import unregister_device_token

        assert unregister_device_token("https://api.local", "tok", 0) is False

    def test_negative_token_id_returns_false(self) -> None:
        from app.net.push_client import unregister_device_token

        assert unregister_device_token("https://api.local", "tok", -1) is False


class TestRegisterDeviceTokenSuccess:
    """register_device_token — urllib mock + JSON parse."""

    def test_register_success_returns_token_id(self) -> None:
        from app.net.push_client import register_device_token

        fake_response = MagicMock()
        fake_response.read.return_value = json.dumps({"token_id": 42}).encode("utf-8")
        fake_cm = MagicMock()
        fake_cm.__enter__.return_value = fake_response
        fake_cm.__exit__.return_value = False

        with patch("urllib.request.urlopen", return_value=fake_cm):
            result = register_device_token(
                "https://api.local", "tok", "fcm-x", platform="macos", device_label="MBP"
            )
        assert result == 42

    def test_register_http_error_returns_none(self) -> None:
        from app.net.push_client import register_device_token
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "https://api.local", 500, "fail", {}, None
            ),
        ):
            result = register_device_token(
                "https://api.local", "tok", "fcm-x"
            )
        assert result is None


class TestUnregisterDeviceTokenSuccess:
    """unregister_device_token — urllib mock + status check."""

    def test_unregister_204_returns_true(self) -> None:
        from app.net.push_client import unregister_device_token

        fake_response = MagicMock()
        fake_response.status = 204
        fake_cm = MagicMock()
        fake_cm.__enter__.return_value = fake_response
        fake_cm.__exit__.return_value = False

        with patch("urllib.request.urlopen", return_value=fake_cm):
            result = unregister_device_token("https://api.local", "tok", 42)
        assert result is True

    def test_unregister_500_returns_false(self) -> None:
        from app.net.push_client import unregister_device_token

        fake_response = MagicMock()
        fake_response.status = 500
        fake_cm = MagicMock()
        fake_cm.__enter__.return_value = fake_response
        fake_cm.__exit__.return_value = False

        with patch("urllib.request.urlopen", return_value=fake_cm):
            result = unregister_device_token("https://api.local", "tok", 42)
        assert result is False
