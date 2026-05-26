# SPDX-License-Identifier: GPL-3.0-or-later
"""avatars REST binding — cycle 169.852 M3 (Exec Plan T-10).

server avatar endpoint(M2) 클라 호출 — QThread + sync urllib worker 패턴
(account_client 정합, GUI 스레드 non-block). httpx 미사용(코드베이스 컨벤션).

worker 3종:
- AvatarUploadWorker  — POST /api/avatars (multipart, 수동 boundary 인코딩) → avatar_ref.
- AvatarFetchWorker   — GET /api/avatars/{filename} → 이미지 byte.
- AvatarPatchMeWorker — PATCH /api/me/avatar → 프로필 avatar_ref 갱신(빈값=제거).

이미지 byte ↔ QImage 변환 헬퍼(qimage_to_bytes)도 제공 — picker 가 고른
QImage 를 업로드 byte 로 직렬화한다(PNG default, 알파 보존).
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
import uuid
from typing import Optional

from PyQt6.QtCore import QBuffer, QIODevice, QThread, pyqtSignal
from PyQt6.QtGui import QImage

log = logging.getLogger(__name__)


def qimage_to_bytes(image: QImage, fmt: str = "PNG") -> bytes:
    """QImage → 이미지 byte 직렬화 (업로드 payload). PNG default = 알파 보존,
    JPEG 는 Qt 가 알파 flatten(불투명 배경)."""

    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buf, fmt)
    data = bytes(buf.data())
    buf.close()
    return data


def _content_type(fmt: str) -> str:
    """포맷 → multipart content-type."""

    return "image/png" if fmt.upper() == "PNG" else "image/jpeg"


class AvatarUploadWorker(QThread):
    """POST /api/avatars multipart 업로드 worker → avatar_ref 회신."""

    # 한글 주석 — (ok, avatar_ref, error_message)
    finished_with_result = pyqtSignal(bool, str, str)

    def __init__(
        self,
        base_url: str,
        token: str,
        image_bytes: bytes,
        fmt: str = "PNG",
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self._url = f"{base_url.rstrip('/')}/api/avatars"
        self._token = token
        self._bytes = image_bytes
        self._fmt = fmt

    def _build_multipart(self) -> tuple[bytes, str]:
        """multipart/form-data body + boundary 수동 인코딩 (file field 단일)."""

        boundary = f"----TooTalkAvatar{uuid.uuid4().hex}"
        ct = _content_type(self._fmt)
        ext = "png" if self._fmt.upper() == "PNG" else "jpg"
        head = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="avatar.{ext}"\r\n'
            f"Content-Type: {ct}\r\n\r\n"
        ).encode("utf-8")
        tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
        body = head + self._bytes + tail
        return body, boundary

    def run(self) -> None:  # type: ignore[override]
        from app.net._ssl_util import build_ssl_context

        ctx = build_ssl_context()
        body, boundary = self._build_multipart()
        req = urllib.request.Request(
            self._url,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Authorization": f"Bearer {self._token}",
            },
            method="POST",
        )
        log.info("[AvatarUpload] fire url=%s bytes=%d", self._url, len(self._bytes))
        try:
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                raw = resp.read()
                data = json.loads(raw) if raw else {}
                ref = str(data.get("avatar_ref", ""))
                log.info("[AvatarUpload] 응답 status=%d ref=%s", resp.status, ref)
                self.finished_with_result.emit(bool(ref), ref, "")
        except urllib.error.HTTPError as exc:
            msg = self._parse_err(exc)
            self.finished_with_result.emit(False, "", msg)
        except Exception as exc:  # noqa: BLE001
            log.warning("[AvatarUpload] 내부 오류 — %r", exc)
            self.finished_with_result.emit(False, "", f"내부 오류: {exc}")

    @staticmethod
    def _parse_err(exc: "urllib.error.HTTPError") -> str:
        try:
            body = exc.read()
            data = json.loads(body) if body else {}
            return str(data.get("message") or data.get("error") or f"HTTP_{exc.code}")
        except Exception:
            return f"HTTP_{exc.code}"


class AvatarFetchWorker(QThread):
    """GET /api/avatars/{filename} → 이미지 byte worker (표시 전파 source)."""

    # 한글 주석 — (ok, avatar_ref, image_bytes)
    finished_with_result = pyqtSignal(bool, str, bytes)

    def __init__(
        self,
        base_url: str,
        token: str,
        avatar_ref: str,
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        # 한글 주석 — avatar_ref = "avatars/<sha>.<ext>" → GET /api/{avatar_ref}
        self._url = f"{base_url.rstrip('/')}/api/{avatar_ref.lstrip('/')}"
        self._token = token
        self._ref = avatar_ref

    def run(self) -> None:  # type: ignore[override]
        from app.net._ssl_util import build_ssl_context

        ctx = build_ssl_context()
        req = urllib.request.Request(
            self._url,
            headers={"Authorization": f"Bearer {self._token}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = resp.read()
                self.finished_with_result.emit(True, self._ref, bytes(data))
        except Exception as exc:  # noqa: BLE001
            log.warning("[AvatarFetch] 실패 ref=%s — %r", self._ref, exc)
            self.finished_with_result.emit(False, self._ref, b"")


class AvatarPatchMeWorker(QThread):
    """PATCH /api/me/avatar → 내 프로필 avatar_ref 갱신(빈값=제거) worker."""

    # 한글 주석 — (ok, avatar_ref, error_message)
    finished_with_result = pyqtSignal(bool, str, str)

    def __init__(
        self,
        base_url: str,
        token: str,
        avatar_ref: str,
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self._url = f"{base_url.rstrip('/')}/api/me/avatar"
        self._token = token
        self._ref = avatar_ref

    def run(self) -> None:  # type: ignore[override]
        from app.net._ssl_util import build_ssl_context

        ctx = build_ssl_context()
        body = json.dumps({"avatar_ref": self._ref}).encode("utf-8")
        req = urllib.request.Request(
            self._url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            },
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                raw = resp.read()
                data = json.loads(raw) if raw else {}
                self.finished_with_result.emit(
                    bool(data.get("updated")), str(data.get("avatar_ref", "")), ""
                )
        except urllib.error.HTTPError as exc:
            self.finished_with_result.emit(False, "", AvatarUploadWorker._parse_err(exc))
        except Exception as exc:  # noqa: BLE001
            log.warning("[AvatarPatchMe] 내부 오류 — %r", exc)
            self.finished_with_result.emit(False, "", f"내부 오류: {exc}")
