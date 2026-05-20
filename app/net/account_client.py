# SPDX-License-Identifier: GPL-3.0-or-later
"""AccountClient — 내 계정 + 내 프로필 endpoint REST binding (cycle 169.57 신설).

server `/api/auth/profile` PUT (cycle 128 PASS) + email/avatar change endpoint chain.
QThread + sync urllib pattern (cycle 169.49 `HttpJsonWorker` 정합).
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.request
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

log = logging.getLogger(__name__)


class ProfileUpdateWorker(QThread):
    """PUT /api/auth/profile background worker."""

    finished_with_result = pyqtSignal(bool, str, str, dict)

    def __init__(
        self,
        base_url: str,
        token: str,
        payload: dict,
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self._url = f"{base_url.rstrip('/')}/api/auth/profile"
        self._token = token
        self._payload = payload

    def run(self) -> None:  # type: ignore[override]
        """background HTTP PUT — Bearer 인증."""
        # cycle 169.79 회수 — TOOTALK_TLS_VERIFY env override
        from app.net._ssl_util import build_ssl_context
        ctx = build_ssl_context()
        body = json.dumps(self._payload).encode("utf-8")
        req = urllib.request.Request(
            self._url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            },
            method="PUT",
        )
        log.info("[ProfileUpdate] fire url=%s keys=%s", self._url, list(self._payload.keys()))
        try:
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                raw = resp.read()
                data = json.loads(raw) if raw else {}
                log.info("[ProfileUpdate] 응답 status=%d ok=%s", resp.status, data.get("ok"))
                self.finished_with_result.emit(
                    bool(data.get("ok")),
                    str(data.get("error", "")),
                    str(data.get("message", "")),
                    data,
                )
        except urllib.error.HTTPError as exc:
            try:
                err_body = exc.read()
                err_data = json.loads(err_body) if err_body else {}
            except Exception:
                err_data = {}
            self.finished_with_result.emit(
                False,
                str(err_data.get("error", f"HTTP_{exc.code}")),
                str(err_data.get("message", str(exc))),
                err_data,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("[ProfileUpdate] 내부 오류 — %r", exc)
            self.finished_with_result.emit(False, "INTERNAL", f"내부 오류: {exc}", {})
