# SPDX-License-Identifier: GPL-3.0-or-later
"""HTTP worker — QThread + urllib sync background fire (cycle 169.49 회수)."""

from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.request
from typing import Any, Optional

from PyQt6.QtCore import QThread, pyqtSignal

log = logging.getLogger(__name__)


class HttpJsonWorker(QThread):
    finished_with_result = pyqtSignal(bool, str, str, dict)

    def __init__(self, base_url: str, path: str, payload: dict, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self._url = f"{base_url.rstrip('/')}{path}"
        self._payload = payload

    def run(self) -> None:
        # cycle 169.79 회수 — TOOTALK_TLS_VERIFY env override
        from app.net._ssl_util import build_ssl_context
        ctx = build_ssl_context()
        body = json.dumps(self._payload).encode("utf-8")
        req = urllib.request.Request(self._url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        log.info("[HttpJsonWorker] fire url=%s keys=%s", self._url, list(self._payload.keys()))
        try:
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                raw = resp.read()
                data = json.loads(raw) if raw else {}
                log.info("[HttpJsonWorker] 응답 status=%d ok=%s", resp.status, data.get("ok"))
                self.finished_with_result.emit(bool(data.get("ok")), str(data.get("error", "")), str(data.get("message", "")), data)
        except urllib.error.HTTPError as exc:
            try:
                err_body = exc.read()
                err_data = json.loads(err_body) if err_body else {}
            except Exception:
                err_data = {}
            log.warning("[HttpJsonWorker] HTTPError status=%d body=%r", exc.code, err_data)
            self.finished_with_result.emit(False, str(err_data.get("error", f"HTTP_{exc.code}")), str(err_data.get("message", str(exc))), err_data)
        except urllib.error.URLError as exc:
            log.warning("[HttpJsonWorker] URLError reason=%r", exc.reason)
            self.finished_with_result.emit(False, "NETWORK", f"네트워크 오류: {exc.reason}", {})
        except TimeoutError as exc:
            log.warning("[HttpJsonWorker] TimeoutError — %r", exc)
            self.finished_with_result.emit(False, "TIMEOUT", "응답 시간 초과 — 잠시 후 재시도", {})
        except Exception as exc:
            log.warning("[HttpJsonWorker] 내부 오류 — %r", exc)
            self.finished_with_result.emit(False, "INTERNAL", f"내부 오류: {exc}", {})
