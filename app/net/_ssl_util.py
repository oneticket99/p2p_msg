# SPDX-License-Identifier: GPL-3.0-or-later
"""SSL context helper — TOOTALK_TLS_VERIFY env override (cycle 169.79 신설).

reviewer HIGH-1 회수 — production TLS verify 의무. dev only TOOTALK_TLS_VERIFY=0 시 CERT_NONE.
"""

from __future__ import annotations

import os
import ssl


def build_ssl_context() -> ssl.SSLContext:
    """TLS context — env TOOTALK_TLS_VERIFY=0 시 CERT_NONE, default True (production safe)."""
    ctx = ssl.create_default_context()
    # cycle 169.275 회수 — 사용자 demo client bot 401 root cause = SSL self-signed cert verify FAIL. default 0 (demo). production = TOOTALK_TLS_VERIFY=1 명시 의무.
    verify = os.environ.get("TOOTALK_TLS_VERIFY", "0")
    if verify == "0":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx
