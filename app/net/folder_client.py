# SPDX-License-Identifier: GPL-3.0-or-later
"""FolderClient — folder REST endpoint binding (cycle 169.77 신설).

server/api/folder_handlers.py 4 endpoint 정합 (cycle 169.76).
QThread + sync urllib pattern (cycle 169.49 AccountClient + HttpJsonWorker 정합).
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.request
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

log = logging.getLogger(__name__)


class _BaseFolderWorker(QThread):
    """folder REST background worker base — Bearer 인증 + 10s timeout."""

    finished_with_result = pyqtSignal(bool, str, str, dict)

    def __init__(
        self,
        base_url: str,
        token: str,
        path: str,
        method: str = "GET",
        payload: Optional[dict] = None,
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self._url = f"{base_url.rstrip('/')}{path}"
        self._token = token
        self._method = method
        self._payload = payload

    def run(self) -> None:  # type: ignore[override]
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        body = json.dumps(self._payload).encode("utf-8") if self._payload is not None else None
        req = urllib.request.Request(
            self._url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            },
            method=self._method,
        )
        log.info("[FolderWorker] fire %s %s", self._method, self._url)
        try:
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                raw = resp.read()
                data = json.loads(raw) if raw else {}
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
            log.warning("[FolderWorker] 내부 오류 — %r", exc)
            self.finished_with_result.emit(False, "INTERNAL", f"내부 오류: {exc}", {})


class FolderCreateWorker(_BaseFolderWorker):
    def __init__(self, base_url: str, token: str, folder_data: dict, parent=None) -> None:
        super().__init__(base_url, token, "/api/folders", "POST", folder_data, parent)


class FolderListWorker(_BaseFolderWorker):
    def __init__(self, base_url: str, token: str, parent=None) -> None:
        super().__init__(base_url, token, "/api/folders", "GET", None, parent)


class FolderDeleteWorker(_BaseFolderWorker):
    def __init__(self, base_url: str, token: str, folder_id: str, parent=None) -> None:
        super().__init__(base_url, token, f"/api/folders/{folder_id}", "DELETE", None, parent)


class FolderInviteWorker(_BaseFolderWorker):
    def __init__(self, base_url: str, token: str, folder_id: str, parent=None) -> None:
        super().__init__(base_url, token, f"/api/folders/{folder_id}/invite", "POST", {}, parent)
