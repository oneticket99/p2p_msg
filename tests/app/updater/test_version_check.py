# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.updater.version_check`` 의 단위 테스트.

cycle 132 skeleton(semver compare + httpx 200/404) + cycle 169.851 coverage
2차 확장(prerelease 우선순위 + ValueError + httpx ImportError/non-dict/network 예외).
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


class TestVersionComparePrerelease:
    """compare_versions 의 prerelease 우선순위 + 형식 위반 분기 검증."""

    def test_release_newer_than_prerelease(self) -> None:
        # 한글 주석: release(prerelease 부재) 가 prerelease 보다 신 — 양수
        assert compare_versions("1.0.0", "1.0.0-beta") > 0

    def test_prerelease_older_than_release(self) -> None:
        # 한글 주석: current prerelease, latest release — latest 신, 음수
        assert compare_versions("1.0.0-beta", "1.0.0") < 0

    def test_prerelease_string_compare_less(self) -> None:
        # 한글 주석: 둘 다 prerelease — 문자열 비교 fallback (alpha < beta)
        assert compare_versions("1.0.0-alpha", "1.0.0-beta") < 0

    def test_prerelease_string_compare_greater(self) -> None:
        # 한글 주석: beta > alpha — 양수
        assert compare_versions("1.0.0-beta", "1.0.0-alpha") > 0

    def test_same_prerelease_returns_zero(self) -> None:
        # 한글 주석: 동일 prerelease — 0
        assert compare_versions("1.0.0-rc1", "1.0.0-rc1") == 0

    def test_invalid_semver_raises_value_error(self) -> None:
        # 한글 주석: semver 형식 위반 → ValueError (_parse_semver)
        with pytest.raises(ValueError, match="semver 형식 위반"):
            compare_versions("not-a-version", "1.0.0")


class TestCheckLatestVersionFallback:
    """check_latest_version 의 graceful None 경로(ImportError/형식/예외) 검증."""

    @pytest.mark.asyncio
    async def test_returns_none_on_httpx_import_error(self) -> None:
        # 한글 주석: httpx 미설치 → import 실패 → graceful None
        with patch.dict("sys.modules", {"httpx": None}):
            result = await check_latest_version("https://update.example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_non_dict_response(self) -> None:
        # 한글 주석: 200 OK 이나 응답이 dict 아님(list) → None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=["not", "a", "dict"])
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = await check_latest_version("https://update.example.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_network_exception(self) -> None:
        # 한글 주석: client.get 예외(network error 등) → graceful None
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=RuntimeError("network down"))

        mock_httpx = MagicMock()
        mock_httpx.AsyncClient = MagicMock(return_value=mock_client)

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = await check_latest_version("https://update.example.com")
        assert result is None
