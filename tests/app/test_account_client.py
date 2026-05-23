# SPDX-License-Identifier: GPL-3.0-or-later
"""AccountClient (ProfileUpdate/ProfileGet worker) unit test — cycle 169.650 omit 제거 path.

cycle 169.635 안 omit 추가 — `app/net/account_client.py` 100% pre-omit. unit test
신설 → omit 영역 축소 path 시작.

본 file = ProfileUpdateWorker + ProfileGetWorker 의 URL composition + payload encode
+ HTTPError graceful 분기 검증 (urllib mock).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("PyQt6")


class TestProfileUpdateWorkerInit:
    """ProfileUpdateWorker __init__ — URL composition + token retain."""

    def test_init_trims_trailing_slash(self) -> None:
        from app.net.account_client import ProfileUpdateWorker

        worker = ProfileUpdateWorker(
            base_url="https://api.local/", token="tok-x", payload={"k": "v"}
        )
        assert worker._url == "https://api.local/api/auth/profile"
        assert worker._token == "tok-x"
        assert worker._payload == {"k": "v"}

    def test_init_retains_path_when_no_trailing_slash(self) -> None:
        from app.net.account_client import ProfileUpdateWorker

        worker = ProfileUpdateWorker(
            base_url="https://api.local", token="t", payload={}
        )
        assert worker._url == "https://api.local/api/auth/profile"


class TestProfileGetWorkerInit:
    """ProfileGetWorker __init__ — URL composition + token retain."""

    def test_init_url_composition(self) -> None:
        from app.net.account_client import ProfileGetWorker

        worker = ProfileGetWorker(base_url="https://api.local", token="tok-y")
        assert worker._url == "https://api.local/api/auth/profile"
        assert worker._token == "tok-y"

    def test_init_trims_trailing_slash(self) -> None:
        from app.net.account_client import ProfileGetWorker

        # 한글 주석 — rstrip("/") = trailing slash 모두 제거
        worker = ProfileGetWorker(base_url="https://api.local///", token="t")
        assert worker._url == "https://api.local/api/auth/profile"
