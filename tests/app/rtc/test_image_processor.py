# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.rtc.image_processor`` 단위 테스트.

Pillow 의존 함수 의 실 실행 — qa-agent 사이클 13 의 "Pillow 의존 함수 미실행"
미커버 영역 의 회수 (handoff §9.2 후속 task #3).

테스트 범위:
- ``_read_thumb_max_size`` / ``_read_thumb_quality`` 환경변수 파싱
- ``guess_mime`` / ``is_image_mime`` MIME 판정
- ``_make_thumbnail_sync`` Pillow 디코딩 + 리샘플링 + RGB 변환
- ``make_thumbnail_base64`` async wrapper + base64 안전 디코드 round-trip
"""

from __future__ import annotations

import asyncio
import base64
import io
from pathlib import Path

import pytest

from app.rtc.image_processor import (
    _DEFAULT_THUMB_MAX_SIZE,
    _DEFAULT_THUMB_QUALITY,
    _make_thumbnail_sync,
    _read_thumb_max_size,
    _read_thumb_quality,
    guess_mime,
    is_image_mime,
    make_thumbnail_base64,
)

# Pillow import — 테스트 fixture 의 의 의 의 의 의 PNG 생성 의 위
from PIL import Image  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# fixture — 임시 PNG / JPEG / RGBA 파일
# ---------------------------------------------------------------------------


@pytest.fixture()
def png_path(tmp_path: Path) -> Path:
    """500x300 의 단색 RGB PNG 파일 fixture."""

    target = tmp_path / "sample.png"
    image = Image.new("RGB", (500, 300), color=(0x00, 0x66, 0xFF))
    image.save(target, format="PNG")
    return target


@pytest.fixture()
def rgba_png_path(tmp_path: Path) -> Path:
    """RGBA 알파 채널 의 PNG — JPEG 저장 시 RGB 변환 검증 의 의 의."""

    target = tmp_path / "rgba.png"
    image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
    image.save(target, format="PNG")
    return target


@pytest.fixture()
def palette_gif_path(tmp_path: Path) -> Path:
    """palette (P) mode GIF — JPEG 저장 시 RGB 변환 검증."""

    target = tmp_path / "palette.gif"
    image = Image.new("P", (80, 60))
    image.save(target, format="GIF")
    return target


# ---------------------------------------------------------------------------
# 1. 환경변수 파싱
# ---------------------------------------------------------------------------


class TestThumbEnvParsing:
    """``THUMB_MAX_PX`` / ``THUMB_QUALITY`` 환경변수 의 정수 파싱 + 폴백."""

    def test_max_size_default_when_unset(self) -> None:
        # isolate_env fixture (conftest.py) 가 자동으로 환경변수 비움
        assert _read_thumb_max_size() == _DEFAULT_THUMB_MAX_SIZE

    def test_max_size_custom(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("THUMB_MAX_PX", "300")
        # 단일 정수 → 정사각 박스 (width, height) 동일
        assert _read_thumb_max_size() == (300, 300)

    def test_max_size_invalid_falls_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("THUMB_MAX_PX", "not-a-number")
        assert _read_thumb_max_size() == _DEFAULT_THUMB_MAX_SIZE

    def test_max_size_zero_or_negative_falls_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("THUMB_MAX_PX", "0")
        assert _read_thumb_max_size() == _DEFAULT_THUMB_MAX_SIZE
        monkeypatch.setenv("THUMB_MAX_PX", "-50")
        assert _read_thumb_max_size() == _DEFAULT_THUMB_MAX_SIZE

    def test_quality_default(self) -> None:
        assert _read_thumb_quality() == _DEFAULT_THUMB_QUALITY

    def test_quality_custom(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("THUMB_QUALITY", "65")
        assert _read_thumb_quality() == 65

    @pytest.mark.parametrize("raw", ["0", "101", "-1", "garbage"])
    def test_quality_invalid_falls_back(
        self, monkeypatch: pytest.MonkeyPatch, raw: str
    ) -> None:
        monkeypatch.setenv("THUMB_QUALITY", raw)
        # 1~100 외 또는 비정수 → 기본값
        assert _read_thumb_quality() == _DEFAULT_THUMB_QUALITY


# ---------------------------------------------------------------------------
# 2. MIME 추측
# ---------------------------------------------------------------------------


class TestMime:
    """``guess_mime`` / ``is_image_mime``."""

    @pytest.mark.parametrize(
        "name,expected_prefix",
        [
            ("photo.png", "image/png"),
            ("photo.jpg", "image/jpeg"),
            ("photo.jpeg", "image/jpeg"),
            ("photo.webp", "image/webp"),
            ("photo.gif", "image/gif"),
        ],
    )
    def test_image_mime_detected(
        self, tmp_path: Path, name: str, expected_prefix: str
    ) -> None:
        path = tmp_path / name
        path.touch()
        assert guess_mime(path) == expected_prefix

    def test_unknown_extension_octet_stream(self, tmp_path: Path) -> None:
        path = tmp_path / "noext"
        path.touch()
        assert guess_mime(path) == "application/octet-stream"

    @pytest.mark.parametrize(
        "mime",
        ["image/png", "image/jpeg", "IMAGE/WEBP", "Image/Gif"],
    )
    def test_is_image_mime_true(self, mime: str) -> None:
        # case-insensitive — IMAGE/* + Image/* 도 인정
        assert is_image_mime(mime) is True

    @pytest.mark.parametrize(
        "mime",
        [
            "text/plain",
            "application/pdf",
            "application/octet-stream",
            "video/mp4",
            "",
        ],
    )
    def test_is_image_mime_false(self, mime: str) -> None:
        assert is_image_mime(mime) is False


# ---------------------------------------------------------------------------
# 3. _make_thumbnail_sync Pillow 디코딩 + 리샘플링
# ---------------------------------------------------------------------------


class TestMakeThumbnailSync:
    """Pillow 동기 본체 — 원본 → bytes 변환."""

    def test_rgb_png_to_jpeg_thumbnail(self, png_path: Path) -> None:
        raw = _make_thumbnail_sync(
            png_path,
            max_size=(100, 100),
            quality=80,
            out_format="JPEG",
        )
        # 결과 bytes = JPEG 헤더 시작 (FF D8 FF)
        assert raw[:3] == b"\xff\xd8\xff"
        # 디코딩 후 박스 의 의 안 — 500x300 이미지 의 100x100 박스 = 100x60 정도
        with Image.open(io.BytesIO(raw)) as out:
            assert out.format == "JPEG"
            assert out.size[0] <= 100
            assert out.size[1] <= 100

    def test_rgba_converted_to_rgb_for_jpeg(self, rgba_png_path: Path) -> None:
        # RGBA → JPEG 의 의 alpha 채널 의 의 의 의 RGB 변환 의 의무
        raw = _make_thumbnail_sync(
            rgba_png_path,
            max_size=(50, 50),
            quality=80,
            out_format="JPEG",
        )
        with Image.open(io.BytesIO(raw)) as out:
            assert out.mode == "RGB"

    def test_palette_converted_to_rgb(self, palette_gif_path: Path) -> None:
        # palette (P) mode → RGB 변환 의 의무 (JPEG 미지원 모드)
        raw = _make_thumbnail_sync(
            palette_gif_path,
            max_size=(50, 50),
            quality=80,
            out_format="JPEG",
        )
        with Image.open(io.BytesIO(raw)) as out:
            assert out.mode == "RGB"

    def test_png_output_preserved(self, png_path: Path) -> None:
        # out_format=PNG 의 의 quality 무시 + PNG 출력
        raw = _make_thumbnail_sync(
            png_path,
            max_size=(80, 80),
            quality=80,
            out_format="PNG",
        )
        # PNG signature = 89 50 4E 47 0D 0A 1A 0A
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"

    def test_aspect_ratio_preserved(self, png_path: Path) -> None:
        # 500x300 → 100x100 박스 의 의 의 의 비율 유지 = 100x60
        raw = _make_thumbnail_sync(
            png_path,
            max_size=(100, 100),
            quality=80,
            out_format="JPEG",
        )
        with Image.open(io.BytesIO(raw)) as out:
            # 비율 5:3 유지 — width 100 이면 height ≈ 60
            assert out.size == (100, 60)


# ---------------------------------------------------------------------------
# 4. make_thumbnail_base64 async wrapper
# ---------------------------------------------------------------------------


class TestMakeThumbnailBase64:
    """async public API — base64 안전 디코드 + 환경변수 정합."""

    @pytest.mark.asyncio
    async def test_returns_valid_base64(self, png_path: Path) -> None:
        b64 = await make_thumbnail_base64(png_path)
        # base64 의 의 의 의 utf-8 안전 + 정확한 디코딩
        assert isinstance(b64, str)
        decoded = base64.b64decode(b64, validate=True)
        # 디코딩 결과 = JPEG bytes (default format)
        assert decoded[:3] == b"\xff\xd8\xff"

    @pytest.mark.asyncio
    async def test_custom_max_size_override(self, png_path: Path) -> None:
        # 작은 박스 의 의 의 의 의 의 강제 의 의 의 의 결과 의 의 크기 ≤ 50
        b64 = await make_thumbnail_base64(png_path, max_size=(50, 50))
        decoded = base64.b64decode(b64)
        with Image.open(io.BytesIO(decoded)) as out:
            assert max(out.size) <= 50

    @pytest.mark.asyncio
    async def test_env_max_px_applied(
        self, png_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("THUMB_MAX_PX", "75")
        b64 = await make_thumbnail_base64(png_path)
        decoded = base64.b64decode(b64)
        with Image.open(io.BytesIO(decoded)) as out:
            assert max(out.size) <= 75

    @pytest.mark.asyncio
    async def test_png_format_override(self, png_path: Path) -> None:
        b64 = await make_thumbnail_base64(png_path, out_format="PNG")
        decoded = base64.b64decode(b64)
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    @pytest.mark.asyncio
    async def test_nonexistent_file_raises(self, tmp_path: Path) -> None:
        # 존재 안 함 의 의 의 의 Pillow 의 FileNotFoundError propagate
        with pytest.raises(FileNotFoundError):
            await make_thumbnail_base64(tmp_path / "missing.png")
