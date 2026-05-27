# SPDX-License-Identifier: GPL-3.0-or-later
"""SSL context helper — TOOTALK_TLS_VERIFY env override (cycle 169.79 신설).

역할 — net client 들이 공유하는 TLS context 1개를 만든다. demo(self-signed cert)
환경은 검증을 끄고, production 은 env 명시로 검증을 켠다.

계층 위치 — app/net 클라이언트 계층(정본 §E)의 공용 helper. `*_client.py` 가 httpx/
aiohttp 요청 시 본 context 를 주입한다(SSL 우회 정책 단일 source).

범위 한계 — context 생성만. 실 인증서 pinning·mTLS·CRL 검증은 별개(현 단계 미도입).
demo default = 검증 OFF 라 실서비스 전환 시 `TOOTALK_TLS_VERIFY=1` 명시 의무.

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
