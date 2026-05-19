# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.updater.downloader`` 의 단위 테스트 — cycle 132 skeleton.

sha256 match PASS + sha256 mismatch FAIL = 2 PASS.
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
