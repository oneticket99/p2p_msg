# SPDX-License-Identifier: GPL-3.0-or-later
"""이미지 썸네일 생성 — Pillow 기반 + asyncio 친화 래퍼.

본 모듈은 송신 직전 이미지 파일에서 작은 미리보기 썸네일을 생성해
``FILE_META`` 메시지의 ``thumbnail_base64`` 필드에 담을 수 있도록 한다.
수신자 UI 는 원본 파일이 도착하기 전이라도 이 썸네일을 즉시 표시하여
체감 대기 시간을 줄인다.

비동기 규약 (정본 §E):

- Pillow 자체는 동기 라이브러리이므로 CPU bound 작업을
  ``asyncio.to_thread`` 로 감싸 이벤트 루프를 막지 않는다.
- 파일 디스크 IO 도 동일하게 ``to_thread`` 안에서 수행한다 — Pillow 가
  내부적으로 파일을 열고 닫기 때문에 별도 ``aiofiles`` 불필요.

본 모듈의 모든 함수는 입력이 유효하지 않으면 ``ValueError`` 를 던지고,
Pillow 가 디코딩 실패 시 원인 예외를 그대로 propagate 한다 — 호출자가
try/except 로 감싸 UI 에 적절한 안내 메시지를 표시한다.

계층 위치 — app/rtc 계층(정본 §E)의 CPU-bound helper. file_sender 가 FILE_META
구성 시 호출한다. UI/네트워크 직접 의존 부재(순수 변환 + to_thread).

의존성 — Pillow(`PIL`) + 표준 base64/io/mimetypes. 외부 네트워크 IO 부재.

범위 한계 — 썸네일 byte/base64 생성만. 원본 파일 전송은 file_sender, 표시는 UI
책임. CPU-bound 라 반드시 to_thread 경유(이벤트 루프 블로킹 차단).
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import mimetypes
import os
from pathlib import Path
from typing import Final, Optional

log = logging.getLogger(__name__)


# 환경변수 override 가능한 썸네일 파라미터 (정본 §E — 하드코딩 금지)
_DEFAULT_THUMB_MAX_SIZE: Final[tuple[int, int]] = (200, 200)
_DEFAULT_THUMB_QUALITY: Final[int] = 80
_DEFAULT_THUMB_FORMAT: Final[str] = "JPEG"


def _read_thumb_max_size() -> tuple[int, int]:
    """``THUMB_MAX_PX`` 환경변수에서 정사각 박스 크기 읽기 (단일 정수).

    형식 잘못 또는 미지정 시 기본값 (200, 200) 사용.
    """

    raw = os.environ.get("THUMB_MAX_PX", "").strip()
    if not raw:
        return _DEFAULT_THUMB_MAX_SIZE
    try:
        pixels = int(raw)
        if pixels <= 0:
            raise ValueError("양수가 아님")
        return (pixels, pixels)
    except ValueError:
        log.warning(
            "THUMB_MAX_PX 환경변수 무효 — raw=%r 기본값 %r 사용",
            raw,
            _DEFAULT_THUMB_MAX_SIZE,
        )
        return _DEFAULT_THUMB_MAX_SIZE


def _read_thumb_quality() -> int:
    """``THUMB_QUALITY`` 환경변수 — 1~100 범위 JPEG 품질.

    범위 밖 또는 미지정 시 기본값 80.
    """

    raw = os.environ.get("THUMB_QUALITY", "").strip()
    if not raw:
        return _DEFAULT_THUMB_QUALITY
    try:
        quality = int(raw)
        if not (1 <= quality <= 100):
            raise ValueError("1~100 범위 벗어남")
        return quality
    except ValueError:
        log.warning(
            "THUMB_QUALITY 환경변수 무효 — raw=%r 기본값 %d 사용",
            raw,
            _DEFAULT_THUMB_QUALITY,
        )
        return _DEFAULT_THUMB_QUALITY


# ---------------------------------------------------------------------------
# MIME 추측 — Pillow import 없이 빠르게 결정
# ---------------------------------------------------------------------------


def guess_mime(path: Path) -> str:
    """확장자 기반 MIME 추측. 실패 시 ``application/octet-stream`` 폴백.

    Parameters
    ----------
    path : Path
        대상 파일 경로.

    Returns
    -------
    str
        MIME 문자열 (예: ``image/png``, ``application/pdf``).
    """

    mime, _ = mimetypes.guess_type(str(path))
    if not mime:
        return "application/octet-stream"
    return mime


def is_image_mime(mime: str) -> bool:
    """MIME 가 이미지 계열인지 판정."""

    return mime.lower().startswith("image/")


# ---------------------------------------------------------------------------
# 동기 본체 — Pillow 호출 (to_thread 안에서 실행)
# ---------------------------------------------------------------------------


def _make_thumbnail_sync(
    src_path: Path,
    max_size: tuple[int, int],
    quality: int,
    out_format: str,
) -> bytes:
    """Pillow 동기 호출 본체 — 원본 → 썸네일 bytes 변환.

    Notes
    -----
    - ``Image.thumbnail()`` 은 in-place 로 크기를 줄이며 비율을 유지한다.
    - 입력이 RGBA / palette 등인 경우 JPEG 저장을 위해 RGB 로 변환한다.
    - 호출자는 본 함수를 직접 호출하지 말고 ``make_thumbnail_base64`` 의
      ``to_thread`` 경유 호출만 사용한다.
    """

    # Pillow 는 선택적 의존성 — 모듈 진입 시점에 import 하여 import 비용을
    # ``make_thumbnail_base64`` 가 호출될 때만 지불하도록 한다.
    from PIL import Image, ImageOps  # type: ignore[import-not-found]

    with Image.open(src_path) as image:
        # EXIF orientation 자동 보정 — 모바일 사진의 회전 정보 반영
        image = ImageOps.exif_transpose(image)

        # JPEG 저장을 위해 알파 / 팔레트 컬러 모드를 RGB 로 통일
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")

        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        save_kwargs: dict[str, object] = {
            "format": out_format,
            "optimize": True,
        }
        if out_format.upper() == "JPEG":
            save_kwargs["quality"] = quality
        image.save(buffer, **save_kwargs)
        return buffer.getvalue()


# ---------------------------------------------------------------------------
# public async API
# ---------------------------------------------------------------------------


async def make_thumbnail_base64(
    src_path: Path,
    *,
    max_size: Optional[tuple[int, int]] = None,
    quality: Optional[int] = None,
    out_format: Optional[str] = None,
) -> str:
    """원본 이미지 파일 → base64 인코딩 썸네일 문자열.

    CPU bound (Pillow 디코딩 + 리샘플링) 이므로 ``asyncio.to_thread`` 로
    워커 스레드에서 실행. 이벤트 루프는 본 함수 await 동안 다른 IO 를
    계속 처리한다.

    Parameters
    ----------
    src_path : Path
        원본 이미지 경로 — 존재해야 함.
    max_size : tuple[int, int] | None
        ``(width, height)`` 최대 박스. None 이면 환경변수 ``THUMB_MAX_PX``
        또는 기본값 (200, 200).
    quality : int | None
        JPEG 품질 1~100. None 이면 환경변수 ``THUMB_QUALITY`` 또는 80.
    out_format : str | None
        Pillow 저장 포맷 — ``JPEG``/``PNG``/``WEBP`` 등. None 이면 JPEG.

    Returns
    -------
    str
        base64 인코딩된 썸네일 (``utf-8`` 안전 문자열).

    Raises
    ------
    FileNotFoundError
        원본 파일이 존재하지 않을 때.
    ValueError
        파일이 빈 경우 (``size == 0``).
    """

    if not src_path.exists():
        raise FileNotFoundError(f"썸네일 원본 미존재 — path={src_path}")
    if src_path.stat().st_size == 0:
        raise ValueError(f"썸네일 원본 빈 파일 — path={src_path}")

    resolved_max = max_size or _read_thumb_max_size()
    resolved_quality = quality if quality is not None else _read_thumb_quality()
    resolved_format = (out_format or _DEFAULT_THUMB_FORMAT).upper()

    log.debug(
        "썸네일 생성 — src=%s max=%s quality=%d format=%s",
        src_path,
        resolved_max,
        resolved_quality,
        resolved_format,
    )

    raw_bytes: bytes = await asyncio.to_thread(
        _make_thumbnail_sync,
        src_path,
        resolved_max,
        resolved_quality,
        resolved_format,
    )
    return base64.b64encode(raw_bytes).decode("ascii")


async def decode_thumbnail_base64(b64_text: str) -> bytes:
    """수신한 base64 썸네일 문자열 → raw bytes 디코딩.

    base64 디코딩은 CPU bound 가 사실상 무시 가능한 수준이지만,
    아주 큰 썸네일이 들어왔을 경우를 대비해 ``to_thread`` 경유로 통일.
    호출자(UI) 가 직접 ``QPixmap.loadFromData(raw)`` 등으로 사용.
    """

    return await asyncio.to_thread(base64.b64decode, b64_text)
