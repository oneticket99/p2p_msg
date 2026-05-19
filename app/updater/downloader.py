# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 132 — TooTalk 업데이트 패키지 다운로드 + SHA-256 검증.

httpx async chunk download + hashlib.sha256 progressive 누적 + progress
0.0~1.0 callback. SHA-256 mismatch 시 dest 파일 제거 + False 반환.

설계 결정
---------
- chunk size = 64KB — Python aiohttp/httpx 권장값. 메모리 RSS 폭증 회피.
- progress_callback Optional — None 시 호출 부재 (CLI/headless 시나리오 정합).
- SHA-256 검증 의무 — code-signing 부재 환경 의 변조 차단 1차 layer.
- httpx 미설치 환경 의 graceful — ImportError catch + False 반환.

본 cycle 의 범위 외
-------------------
- resume / range request (HTTP 206) — 별개 cycle
- 다중 mirror + 자동 failover
- bandwidth throttle (사용자 설정)
- BitTorrent fallback
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Callable, Final, Optional

log = logging.getLogger(__name__)

# 한글 주석: chunk size — 64 KiB (httpx/aiohttp 권장 default)
_CHUNK_SIZE_BYTES: Final[int] = 64 * 1024

# 한글 주석: 다운로드 timeout — 초 단위 (대용량 zip 가정 의 60 초 cap)
_DEFAULT_TIMEOUT_SECONDS: Final[float] = 60.0


ProgressCallback = Callable[[float], None]


async def download_update_async(
    url: str,
    dest_path: Path,
    expected_sha256: str,
    progress_callback: Optional[ProgressCallback] = None,
) -> bool:
    """업데이트 패키지 의 async 다운로드 + SHA-256 검증.

    Parameters
    ----------
    url : str
        다운로드 URL (HTTPS 의무 — 평문 차단 caller 의 의무).
    dest_path : Path
        저장 경로. 부모 디렉토리 자동 생성.
    expected_sha256 : str
        예상 SHA-256 해시 (hex, 64 자). mismatch 시 파일 제거 + False.
    progress_callback : Optional[ProgressCallback]
        progress 0.0~1.0 의 callback. None 시 호출 부재.

    Returns
    -------
    bool
        True = 다운로드 + 검증 PASS. False = 어느 단계든 FAIL.
    """

    # 한글 주석: httpx 미설치 환경 의 graceful fallback
    try:
        import httpx  # type: ignore[import-not-found]
    except ImportError as e:
        log.warning("httpx 미설치 — 다운로드 skip (%s)", e)
        return False

    # 한글 주석: 부모 디렉토리 자동 생성 (Path.mkdir parents=True)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    hasher = hashlib.sha256()
    bytes_downloaded = 0

    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                # 한글 주석: Content-Length 헤더 의 total size (없으면 progress 0.0 고정)
                total_str = response.headers.get("content-length", "0")
                try:
                    total_bytes = int(total_str)
                except (TypeError, ValueError):
                    total_bytes = 0

                with open(dest_path, "wb") as fh:
                    async for chunk in response.aiter_bytes(
                        chunk_size=_CHUNK_SIZE_BYTES
                    ):
                        if not chunk:
                            continue
                        fh.write(chunk)
                        hasher.update(chunk)
                        bytes_downloaded += len(chunk)
                        if progress_callback and total_bytes > 0:
                            ratio = min(1.0, bytes_downloaded / total_bytes)
                            try:
                                progress_callback(ratio)
                            except Exception as cb_err:
                                # 한글 주석: callback 의 예외 의무 isolate
                                log.warning(
                                    "progress callback 예외 — %s (계속)", cb_err
                                )

        actual_sha = hasher.hexdigest()
        if actual_sha.lower() != expected_sha256.lower():
            log.error(
                "SHA-256 mismatch — expected=%s actual=%s (파일 제거)",
                expected_sha256,
                actual_sha,
            )
            try:
                dest_path.unlink(missing_ok=True)
            except OSError as rm_err:
                log.warning("mismatch dest unlink 실패 — %s", rm_err)
            return False

        log.info(
            "다운로드 PASS — bytes=%d sha256=%s dest=%s",
            bytes_downloaded,
            actual_sha,
            dest_path,
        )
        return True
    except Exception as e:
        log.error("다운로드 FAIL — %s", e)
        # 한글 주석: 부분 다운로드 파일 정리
        try:
            dest_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False
