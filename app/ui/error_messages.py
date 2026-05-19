# SPDX-License-Identifier: GPL-3.0-or-later
"""dialog 오류 메시지 한글화 helper — 사용자 directive cycle 169.44 회수.

사용자 directive verbatim: "다이얼로그 오류 메시지는 전부 한글화해".

raw exception text (영문) → user-facing 한국어 메시지 mapping.
debug 정보 보존 — log 측면 raw exc 잔존 + UI 표시는 한국어.
"""

from __future__ import annotations


def translate_error(exc: BaseException) -> str:
    """exception → 사용자 친화 한국어 메시지 변환.

    Parameters
    ----------
    exc : BaseException
        catch 된 exception 인스턴스.

    Returns
    -------
    str
        한국어 사용자 메시지. mapping 부재 시 generic 메시지 + 첫 80자 잔존.
    """

    s = str(exc)
    s_lower = s.lower()

    # 한글 주석 — asyncio + qasync loop 충돌 mapping
    if "running event loop" in s_lower or "no running event loop" in s_lower:
        return "내부 이벤트 루프 충돌 — 재시도 의무"

    # 한글 주석 — network connectivity mapping
    if "connection refused" in s_lower:
        return "서버 연결 거부 — 서버 점검 중 또는 부재"
    if "connection reset" in s_lower:
        return "서버 연결 끊김 — 재시도 의무"
    if "name resolution" in s_lower or "name or service" in s_lower or "getaddrinfo" in s_lower:
        return "DNS 조회 실패 — 도메인 부재 또는 네트워크 오류"
    if "network is unreachable" in s_lower or "unreachable" in s_lower:
        return "네트워크 도달 부재 — 인터넷 연결 확인 의무"
    if "timeout" in s_lower or "timed out" in s_lower:
        return "응답 시간 초과 — 서버 부하 또는 네트워크 지연"

    # 한글 주석 — TLS / SSL mapping
    if "ssl" in s_lower or "certificate" in s_lower:
        return "SSL 인증서 오류 — 인증서 만료 또는 신뢰 부재"
    if "handshake" in s_lower:
        return "TLS 핸드셰이크 실패 — 서버 인증서 검증 부재"

    # 한글 주석 — HTTP status mapping
    if "401" in s or "unauthorized" in s_lower:
        return "인증 실패 — 자격 정보 부재 또는 만료"
    if "403" in s or "forbidden" in s_lower:
        return "권한 부재 — 접근 차단"
    if "404" in s or "not found" in s_lower:
        return "endpoint 부재 — 서버 버전 mismatch"
    if "500" in s or "internal server error" in s_lower:
        return "서버 내부 오류 — 운영자 문의 의무"
    if "502" in s or "bad gateway" in s_lower:
        return "게이트웨이 오류 — 백엔드 부재"
    if "503" in s or "service unavailable" in s_lower:
        return "서비스 부재 — 점검 중"

    # 한글 주석 — JSON / encoding mapping
    if "json" in s_lower or "expecting value" in s_lower or "extra data" in s_lower:
        return "응답 형식 오류 — 서버 응답 parse 실패"
    if "decode" in s_lower or "encoding" in s_lower:
        return "문자 인코딩 오류 — 서버 응답 형식 부재"

    # 한글 주석 — generic fallback (debug 정보 80자 잔존)
    return f"내부 오류 — {s[:80]}"
