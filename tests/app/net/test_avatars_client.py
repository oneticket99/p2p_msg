# SPDX-License-Identifier: GPL-3.0-or-later
"""avatars_client 단위 test — cycle 169.852 M3 (Exec Plan T-10).

worker run() 은 urllib 실 network 라 단위 부적합(M2 e2e 가 서버측 cover) — 순수
헬퍼(qimage_to_bytes / _build_multipart boundary 인코딩 / url 조립 / _parse_err)만
검증. offscreen Qt (QImage/QBuffer).
"""

from __future__ import annotations

import urllib.error
from io import BytesIO

import pytest
from PyQt6.QtGui import QImage

from app.net.avatars_client import (
    AvatarFetchWorker,
    AvatarPatchMeWorker,
    AvatarUploadWorker,
    qimage_to_bytes,
)


def _img(w=64, h=48) -> QImage:
    img = QImage(w, h, QImage.Format.Format_RGB32)
    img.fill(0x3366FF)
    return img


def test_qimage_to_bytes_png_decodable() -> None:
    # 한글 주석 — 직렬화 byte 가 다시 QImage 로 decode 되는 round-trip
    data = qimage_to_bytes(_img(), "PNG")
    assert isinstance(data, bytes) and len(data) > 0
    back = QImage()
    assert back.loadFromData(data, "PNG") and not back.isNull()


def test_build_multipart_boundary_and_disposition() -> None:
    # 한글 주석 — multipart body = boundary + Content-Disposition file field + tail
    raw = qimage_to_bytes(_img(), "PNG")
    w = AvatarUploadWorker("https://x", "tok", raw, "PNG")
    body, boundary = w._build_multipart()
    assert boundary.startswith("----TooTalkAvatar")
    assert f"--{boundary}".encode() in body
    assert b'name="file"; filename="avatar.png"' in body
    assert b"Content-Type: image/png" in body
    assert raw in body
    assert body.rstrip().endswith(f"--{boundary}--".encode())


def test_build_multipart_jpeg_ext() -> None:
    raw = qimage_to_bytes(_img(), "JPEG")
    w = AvatarUploadWorker("https://x", "tok", raw, "JPEG")
    body, _ = w._build_multipart()
    assert b'filename="avatar.jpg"' in body
    assert b"Content-Type: image/jpeg" in body


def test_upload_url() -> None:
    w = AvatarUploadWorker("https://srv/", "tok", b"x", "PNG")
    assert w._url == "https://srv/api/avatars"


def test_fetch_url_from_ref() -> None:
    # 한글 주석 — avatar_ref "avatars/<sha>.png" → GET /api/avatars/<sha>.png
    ref = "avatars/" + ("a" * 64) + ".png"
    w = AvatarFetchWorker("https://srv", "tok", ref)
    assert w._url == f"https://srv/api/{ref}"


def test_patch_me_url() -> None:
    w = AvatarPatchMeWorker("https://srv", "tok", "avatars/x.png")
    assert w._url == "https://srv/api/me/avatar"


def test_parse_err_extracts_message() -> None:
    # 한글 주석 — HTTPError body 의 message 추출 (없으면 HTTP_<code>)
    exc = urllib.error.HTTPError(
        "u", 413, "Payload Too Large", {},
        BytesIO('{"message":"업로드 5 MB 초과"}'.encode("utf-8")),
    )
    assert AvatarUploadWorker._parse_err(exc) == "업로드 5 MB 초과"
    exc2 = urllib.error.HTTPError("u", 500, "err", {}, BytesIO(b""))
    assert AvatarUploadWorker._parse_err(exc2) == "HTTP_500"
