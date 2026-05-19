# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.updater.version_check`` 의 단위 테스트 — cycle 132 skeleton.

semver compare 3 + httpx mock 2 = 5 PASS.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.updater.version_check import (
    check_latest_version,
    compare_versions,
)


class TestVersionCompare:
    """compare_versions 의 음수/0/양수 분기 검증."""

    def test_current_equals_latest_returns_zero(self) -> None:
        # 한글 주석: 동일 버전 = 0
        assert compare_versions("1.2.3", "1.2.3") == 0

    def test_current_greater_than_latest_returns_positive(self) -> None:
        # 한글 주석: current 가 신 버전 (개발 빌드 시나리오) — 양수
        result = compare_versions("2.0.0", "1.9.9")
        assert result > 0

    def test_current_less_than_latest_returns_negative(self) -> None:
        # 한글 주석: 신 버전 가용 — 음수 (caller 의 업데이트 prompt 유도)
        result = compare_versions("0.4.0", "0.5.0")
        assert result < 0


class TestCheckLatestVersion:
    """check_latest_version 의 httpx mock 경로 검증."""

    @pytest.mark.asyncio
    async def test_check_latest_returns_dict_on_200(self) -> None:
        # 한글 주석: 200 OK + dict 응답 → 정상 반환
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "version": "0.5.0",
                "download_url": "https://example.com/tootalk-0.5.0.zip",
                "sha256": "a" * 64,
            }
        )
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = await check_latest_version("https://update.example.com")

        assert result is not None
        assert result["version"] == "0.5.0"
        assert result["sha256"] == "a" * 64

    @pytest.mark.asyncio
    async def test_check_latest_returns_none_on_404(self) -> None:
        # 한글 주석: 404 = 서버 endpoint 미구현 시나리오 → graceful None
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = await check_latest_version("https://update.example.com")

        assert result is None
