# SPDX-License-Identifier: GPL-3.0-or-later
"""avatar 이미지 업로드 + 조회 + 프로필 갱신 REST — cycle 169.852 M2 (Exec Plan §4).

계층 위치 — server API handler 계층(정본 §E). auth_middleware Bearer 통과 후
진입하며, byte 가공은 본 handler, 디스크 저장/조회는 `avatars` repository, 프로필
avatar_ref 갱신은 `users` repository 가 분담한다(계층 분리, D-3).

의존성 — aiohttp `web` + Pillow(`PIL.Image`/`ImageOps`, 부재 시 graceful) +
`avatars` repository(content-addressed 디스크 store/load) + `users` repository
(`update_avatar_ref`) + `request.app["db_pool"]`(PATCH 경로만).

범위 한계 — 이미지 가공 + 디스크 영속 + 프로필 ref 갱신만. CDN 배포/S3 이전/
썸네일 다중 사이즈는 본 module 범위 외(현 단계 = 로컬 디스크 단일 512 정사각).

endpoint:
- POST  /api/avatars            — multipart 업로드 → Pillow 정사각 512 crop + EXIF
                                   strip + sha256 디스크 저장 → avatar_ref 회신 (Bearer).
- GET   /api/avatars/{filename} — avatar 이미지 byte 조회 (Bearer, path traversal 방어).
- PATCH /api/me/avatar          — 내 프로필 users.avatar_ref 갱신 (Bearer, 빈값=제거).

저장 byte 가공(decode/crop/EXIF strip/재인코딩)은 본 handler 책임 — repository
(`avatars.py`)는 최종 byte 만 받아 sha256 키 산출 + 디스크 write (계층 분리, D-3).

이미지 제약 (D-4): content-type allowlist(image/jpeg·image/png) + Pillow format
화이트리스트(magic byte sniff) + 업로드 ≤ 5 MB(read_chunk 누적 guard) + 정사각
center 512 다운스케일 + EXIF strip 재인코딩.
"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Final, Optional

from aiohttp import web

from server.db.repositories import avatars as _avatars_repo
from server.db.repositories import users as _users_repo

log = logging.getLogger(__name__)

# 업로드 제약 상수 (D-4).
_MAX_UPLOAD_BYTES: Final[int] = 5 * 1024 * 1024  # 5 MB
_AVATAR_SIZE_PX: Final[int] = 512
_ALLOWED_CONTENT_TYPES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/png"}
)
# Pillow format → 저장 확장자 (magic byte sniff 결과 화이트리스트).
_FORMAT_EXT: Final[dict[str, str]] = {"JPEG": "jpg", "PNG": "png"}


def _process_image(raw: bytes) -> Optional[tuple[bytes, str]]:
    """원본 byte → 정사각 512 crop + EXIF strip 재인코딩 byte + ext.

    Returns
    -------
    (bytes, ext) | None
        Pillow decode 실패 또는 허용 외 format 시 None (caller 400).
    """

    try:
        from PIL import Image, ImageOps
    except ImportError as err:  # pragma: no cover - Pillow 부재 환경 폴백
        log.error("Pillow 미설치 — avatar 가공 불가 (%s)", err)
        return None

    try:
        img = Image.open(BytesIO(raw))
        fmt = (img.format or "").upper()  # magic byte sniff 결과
        if fmt not in _FORMAT_EXT:
            log.warning("avatar format 화이트리스트 외 — %s", fmt)
            return None
        # EXIF orientation 적용 후 strip (GPS 등 메타 유출 차단)
        img = ImageOps.exif_transpose(img)
        # center 정사각 crop → 512 다운스케일
        width, height = img.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        img = img.crop((left, top, left + side, top + side)).resize(
            (_AVATAR_SIZE_PX, _AVATAR_SIZE_PX), Image.LANCZOS
        )
        out = BytesIO()
        if fmt == "PNG":
            img.convert("RGBA").save(out, "PNG")  # exif kwarg 미전달 = strip
            ext = "png"
        else:
            img.convert("RGB").save(out, "JPEG", quality=88)
            ext = "jpg"
        return out.getvalue(), ext
    except Exception as err:  # decode/가공 실패 graceful 400
        log.warning("avatar 이미지 가공 실패 — %s", err)
        return None


async def handle_upload_avatar(request: web.Request) -> web.Response:
    """POST /api/avatars — multipart 이미지 업로드 + 가공 + 디스크 저장."""

    user_id = request.get("user_id")
    if user_id is None or not isinstance(user_id, int) or user_id <= 0:
        return web.json_response({"error": "UNAUTHORIZED"}, status=401)

    if not request.content_type.startswith("multipart/"):
        return web.json_response(
            {"error": "BAD_CONTENT_TYPE", "message": "multipart/form-data 의무"},
            status=415,
        )

    reader = await request.multipart()
    field = await reader.next()
    # field 'file' + content-type allowlist 검증
    if field is None or field.name != "file":
        return web.json_response(
            {"error": "NO_FILE", "message": "file field 부재"}, status=400
        )
    field_ct = (field.headers.get("Content-Type") or "").split(";")[0].strip()
    if field_ct not in _ALLOWED_CONTENT_TYPES:
        return web.json_response(
            {"error": "UNSUPPORTED_TYPE", "message": f"jpg/png 만 허용 — {field_ct}"},
            status=415,
        )

    # read_chunk 누적 + 5 MB cap (전량 적재 전 차단, DoS 방어)
    size = 0
    chunks: list[bytes] = []
    while True:
        chunk = await field.read_chunk(8192)
        if not chunk:
            break
        size += len(chunk)
        if size > _MAX_UPLOAD_BYTES:
            return web.json_response(
                {"error": "TOO_LARGE", "message": "업로드 5 MB 초과"}, status=413
            )
        chunks.append(chunk)
    raw = b"".join(chunks)
    if not raw:
        return web.json_response(
            {"error": "EMPTY", "message": "빈 업로드"}, status=400
        )

    processed = _process_image(raw)
    if processed is None:
        return web.json_response(
            {"error": "DECODE_FAIL", "message": "이미지 decode/format 실패"},
            status=400,
        )
    out_bytes, ext = processed
    avatar_ref = _avatars_repo.store_avatar(out_bytes, ext)
    log.info("[avatar] upload user_id=%d ref=%s bytes=%d", user_id, avatar_ref, len(out_bytes))
    return web.json_response(
        {
            "avatar_ref": avatar_ref,
            "width": _AVATAR_SIZE_PX,
            "height": _AVATAR_SIZE_PX,
            "bytes": len(out_bytes),
        },
        status=201,
    )


async def handle_get_avatar(request: web.Request) -> web.Response:
    """GET /api/avatars/{filename} — avatar 이미지 byte 조회 (traversal 방어)."""

    user_id = request.get("user_id")
    if user_id is None or not isinstance(user_id, int) or user_id <= 0:
        return web.json_response({"error": "UNAUTHORIZED"}, status=401)

    filename = request.match_info.get("filename", "")
    avatar_ref = f"avatars/{filename}"
    if not _avatars_repo.is_valid_ref(avatar_ref):
        return web.json_response(
            {"error": "BAD_REF", "message": "avatar_ref 형식 위반"}, status=400
        )
    data = _avatars_repo.load_avatar(avatar_ref)
    if data is None:
        return web.json_response({"error": "NOT_FOUND"}, status=404)
    return web.Response(
        body=data,
        content_type=_avatars_repo.content_type_for_ref(avatar_ref),
        headers={"Cache-Control": "private, max-age=86400"},
    )


async def handle_patch_me_avatar(request: web.Request) -> web.Response:
    """PATCH /api/me/avatar — 내 프로필 avatar_ref 갱신 (빈값=제거)."""

    user_id = request.get("user_id")
    if user_id is None or not isinstance(user_id, int) or user_id <= 0:
        return web.json_response({"error": "UNAUTHORIZED"}, status=401)

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "BAD_JSON"}, status=400)
    avatar_ref = body.get("avatar_ref", "")
    if not isinstance(avatar_ref, str):
        return web.json_response(
            {"error": "BAD_REF", "message": "avatar_ref string 의무"}, status=400
        )
    # 빈 문자열 = avatar 제거(이니셜 fallback 복귀), 비빈값 = 실재 검증
    if avatar_ref and not _avatars_repo.avatar_exists(avatar_ref):
        return web.json_response(
            {"error": "REF_NOT_FOUND", "message": "avatar_ref 미실재"}, status=400
        )

    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response(
            {"error": "DB_DISABLED", "message": "DB pool 비활성"}, status=503
        )
    await _users_repo.update_avatar_ref(pool, user_id, avatar_ref)
    log.info("[avatar] patch_me user_id=%d ref=%s", user_id, avatar_ref or "(제거)")
    return web.json_response({"updated": True, "avatar_ref": avatar_ref})


def register_avatars_routes(app: web.Application) -> None:
    """avatar REST endpoint 3종 등록 (server/main.py 호출)."""

    app.router.add_post("/api/avatars", handle_upload_avatar)
    app.router.add_get("/api/avatars/{filename}", handle_get_avatar)
    app.router.add_patch("/api/me/avatar", handle_patch_me_avatar)
