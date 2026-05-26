# SPDX-License-Identifier: GPL-3.0-or-later
"""avatar 이미지 byte 의 디스크 영속 repository — cycle 169.852 (0018 정합).

저장 backend = server volume(디스크) relative path (Exec Plan D-3). DB blob(row
bloat) / object storage(S3 인프라 미배치) 회피. content-addressed 키
``avatars/<sha256>.<ext>`` — 동일 byte 재업로드 시 자동 dedup(write skip).

본 모듈은 **최종 byte**(handler 가 Pillow 로 정사각 crop + EXIF strip + 재인코딩
완료한 결과)만 받아 sha256 키 산출 + 디스크 write 한다 — 이미지 가공은 handler
책임(계층 분리). S3 전환 시 본 모듈 인터페이스 불변, 내부 write/read 만 교체.

경로 traversal 방어: ``avatar_ref`` 는 ``^avatars/[0-9a-f]{64}\\.(png|jpg|jpeg)$``
정규식 검증을 통과해야만 디스크 접근 — 키 형식 + 위조(``../`` 등) 동시 차단.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Final, Optional

log = logging.getLogger(__name__)

# 한글 주석 — avatar byte 영속 디렉토리 (환경변수 override, default = server/_avatar_store/).
#   .gitignore 등재 의무 (실 이미지 byte 는 git 추적 대상 아님).
_DEFAULT_STORAGE_DIR: Final[str] = str(
    Path(__file__).resolve().parents[2] / "_avatar_store"
)

# 한글 주석 — 허용 확장자 (content-type allowlist 와 정합 — handler 검증 후 전달).
_ALLOWED_EXT: Final[frozenset[str]] = frozenset({"png", "jpg", "jpeg"})

# 한글 주석 — avatar_ref 키 형식 + path traversal 방어 정규식 (sha256 hex 64 + ext).
#   \A...\Z anchor (^/$ 아님) — $ 가 trailing newline 까지 매치하는 허점 차단 (엄밀 전체 일치).
_KEY_RE: Final[re.Pattern[str]] = re.compile(
    r"\Aavatars/[0-9a-f]{64}\.(png|jpg|jpeg)\Z"
)


def _storage_dir() -> Path:
    """AVATAR_STORAGE_DIR 환경변수 resolve (default server/_avatar_store/)."""

    return Path(os.environ.get("AVATAR_STORAGE_DIR", _DEFAULT_STORAGE_DIR))


def is_valid_ref(avatar_ref: str) -> bool:
    """avatar_ref 가 키 형식 + traversal 안전한지 검증 (디스크 접근 전 gate)."""

    return bool(_KEY_RE.match(avatar_ref))


def store_avatar(image_bytes: bytes, ext: str) -> str:
    """가공 완료 이미지 byte 를 디스크에 영속 + avatar_ref 키 반환.

    Parameters
    ----------
    image_bytes : bytes
        handler 가 정사각 crop + EXIF strip + 재인코딩 완료한 최종 byte.
    ext : str
        확장자 (png/jpg/jpeg — handler content-type 검증 결과).

    Returns
    -------
    str
        ``avatars/<sha256>.<ext>`` 키. 동일 byte 존재 시 write skip(dedup) 후 동일 키.

    Raises
    ------
    ValueError
        ext 가 허용 목록 외.
    """

    norm_ext = ext.lower().lstrip(".")
    if norm_ext not in _ALLOWED_EXT:
        raise ValueError(f"허용 외 확장자 — {ext!r}")

    digest = hashlib.sha256(image_bytes).hexdigest()
    key = f"avatars/{digest}.{norm_ext}"

    storage = _storage_dir()
    dest = storage / f"{digest}.{norm_ext}"
    # 한글 주석 — 디렉토리 자동 생성 + content-addressed dedup (존재 시 재기록 skip).
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        log.info("avatar dedup — 기존 키 재사용 key=%s", key)
        return key
    # 한글 주석 — 임시 파일 write 후 atomic rename (부분 write 노출 차단).
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_bytes(image_bytes)
    tmp.replace(dest)
    log.info("avatar 저장 PASS key=%s bytes=%d", key, len(image_bytes))
    return key


def load_avatar(avatar_ref: str) -> Optional[bytes]:
    """avatar_ref 의 이미지 byte 조회 — 키 검증 통과 + 파일 존재 시만 반환.

    Returns
    -------
    bytes | None
        키 형식 위반(traversal 시도 포함) 또는 파일 부재 시 None.
    """

    if not is_valid_ref(avatar_ref):
        log.warning("avatar_ref 형식 위반 — 접근 거부 ref=%r", avatar_ref)
        return None
    # 한글 주석 — 키는 "avatars/<sha256>.<ext>" — basename 만 디스크 경로에 결합.
    filename = avatar_ref.split("/", 1)[1]
    path = _storage_dir() / filename
    if not path.is_file():
        return None
    try:
        return path.read_bytes()
    except OSError as err:
        log.warning("avatar read 실패 — %s (%s)", avatar_ref, err)
        return None


def avatar_exists(avatar_ref: str) -> bool:
    """avatar_ref 가 실재 파일을 가리키는지 — PATCH /api/me/avatar 검증용."""

    if not is_valid_ref(avatar_ref):
        return False
    filename = avatar_ref.split("/", 1)[1]
    return (_storage_dir() / filename).is_file()


def content_type_for_ref(avatar_ref: str) -> str:
    """avatar_ref 확장자 → HTTP Content-Type (GET 응답 헤더용)."""

    if avatar_ref.endswith(".png"):
        return "image/png"
    return "image/jpeg"
