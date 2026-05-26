# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.updater.downloader`` 의 단위 테스트.

cycle 132 skeleton(sha256 match/mismatch) + cycle 169.851 coverage 2차 확장
(httpx ImportError + content-length 비정수 + empty chunk skip + progress callback
예외 isolate + download 예외 cleanup).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.updater.downloader import download_update_async


def _make_mock_httpx(chunks: list[bytes], content_length: int) -> MagicMock:
    """httpx mock 빌더 — chunk iterator + content-length 헤더."""

    async def _aiter(chunk_size: int = 64 * 1024):  # noqa: ARG001
        for chunk in chunks:
            yield chunk

    mock_response = MagicMock()
    mock_response.headers = {"content-length": str(content_length)}
    mock_response.aiter_bytes = _aiter
    mock_response.raise_for_status = MagicMock()

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.stream = MagicMock(return_value=mock_stream_ctx)

    mock_httpx = MagicMock()
    mock_httpx.AsyncClient = MagicMock(return_value=mock_client)
    return mock_httpx


class TestDownload:
    """download_update_async 의 SHA-256 검증 분기."""

    @pytest.mark.asyncio
    async def test_download_sha256_match_returns_true(
        self, tmp_path: Path
    ) -> None:
        # 한글 주석: 정상 다운로드 + SHA-256 일치 → True
        payload = b"tootalk-update-payload-cycle-132"
        expected_sha = hashlib.sha256(payload).hexdigest()
        chunks = [payload[:10], payload[10:]]

        mock_httpx = _make_mock_httpx(chunks, len(payload))
        dest = tmp_path / "update.zip"

        progress_values: list[float] = []

        def _on_progress(ratio: float) -> None:
            progress_values.append(ratio)

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = await download_update_async(
                "https://example.com/update.zip",
                dest,
                expected_sha,
                _on_progress,
            )

        assert result is True
        assert dest.exists()
        assert dest.read_bytes() == payload
        # 한글 주석: progress callback 1회 이상 호출 확인
        assert len(progress_values) >= 1
        assert progress_values[-1] == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_download_sha256_mismatch_removes_file_returns_false(
        self, tmp_path: Path
    ) -> None:
        # 한글 주석: SHA-256 mismatch → dest 파일 제거 + False
        payload = b"corrupted-payload-bytes"
        wrong_sha = "0" * 64
        chunks = [payload]

        mock_httpx = _make_mock_httpx(chunks, len(payload))
        dest = tmp_path / "bad.zip"

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = await download_update_async(
                "https://example.com/bad.zip",
                dest,
                wrong_sha,
                None,
            )

        assert result is False
        assert not dest.exists()


def _make_httpx_custom(chunks, *, content_length="0", raise_status=None) -> MagicMock:
    """확장 mock — content-length 임의값 + raise_for_status 예외 주입."""

    async def _aiter(chunk_size: int = 64 * 1024):  # noqa: ARG001
        for chunk in chunks:
            yield chunk

    resp = MagicMock()
    resp.headers = {"content-length": content_length}
    resp.aiter_bytes = _aiter
    resp.raise_for_status = MagicMock(side_effect=raise_status)

    stream_ctx = MagicMock()
    stream_ctx.__aenter__ = AsyncMock(return_value=resp)
    stream_ctx.__aexit__ = AsyncMock(return_value=None)

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.stream = MagicMock(return_value=stream_ctx)

    httpx = MagicMock()
    httpx.AsyncClient = MagicMock(return_value=client)
    return httpx


class TestDownloadEdge:
    """download_update_async 의 fallback/예외/skip 분기 검증."""

    @pytest.mark.asyncio
    async def test_httpx_import_error_returns_false(self, tmp_path: Path) -> None:
        # 한글 주석: httpx 미설치 → graceful False
        with patch.dict("sys.modules", {"httpx": None}):
            result = await download_update_async(
                "https://x/y.zip", tmp_path / "y.zip", "0" * 64
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_invalid_content_length_skips_progress(
        self, tmp_path: Path
    ) -> None:
        # 한글 주석: content-length 비정수 → total_bytes 0, progress 미호출이나 PASS
        payload = b"abc"
        sha = hashlib.sha256(payload).hexdigest()
        ratios: list[float] = []
        httpx = _make_httpx_custom([payload], content_length="not-int")
        dest = tmp_path / "pkg.zip"

        with patch.dict("sys.modules", {"httpx": httpx}):
            result = await download_update_async(
                "https://x/pkg.zip", dest, sha, ratios.append
            )

        assert result is True
        assert ratios == []  # total_bytes 0 → callback 미호출

    @pytest.mark.asyncio
    async def test_empty_chunk_skipped(self, tmp_path: Path) -> None:
        # 한글 주석: 빈 chunk(b'') skip, 유효 chunk 만 누적
        sha = hashlib.sha256(b"data").hexdigest()
        httpx = _make_httpx_custom([b"", b"data", b""], content_length="4")
        dest = tmp_path / "pkg.zip"

        with patch.dict("sys.modules", {"httpx": httpx}):
            result = await download_update_async(
                "https://x/pkg.zip", dest, sha, None
            )

        assert result is True
        assert dest.read_bytes() == b"data"

    @pytest.mark.asyncio
    async def test_progress_callback_exception_isolated(
        self, tmp_path: Path
    ) -> None:
        # 한글 주석: progress callback 예외 isolate — 다운로드 자체 PASS
        payload = b"payload"
        sha = hashlib.sha256(payload).hexdigest()

        def _boom(_ratio: float) -> None:
            raise RuntimeError("callback boom")

        httpx = _make_httpx_custom([payload], content_length=str(len(payload)))
        dest = tmp_path / "pkg.zip"

        with patch.dict("sys.modules", {"httpx": httpx}):
            result = await download_update_async(
                "https://x/pkg.zip", dest, sha, _boom
            )

        assert result is True

    @pytest.mark.asyncio
    async def test_download_exception_cleans_partial(
        self, tmp_path: Path
    ) -> None:
        # 한글 주석: stream 단계 예외(raise_for_status) → 부분 파일 정리 + False
        httpx = _make_httpx_custom([], raise_status=RuntimeError("HTTP 500"))
        dest = tmp_path / "pkg.zip"

        with patch.dict("sys.modules", {"httpx": httpx}):
            result = await download_update_async(
                "https://x/pkg.zip", dest, "0" * 64, None
            )

        assert result is False
        assert not dest.exists()
