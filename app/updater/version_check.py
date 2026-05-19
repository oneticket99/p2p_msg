# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 132 — TooTalk 자동 업데이트 의 버전 확인 layer.

서버 `/api/version/latest` endpoint 의 GET + semver 비교 + graceful fallback.
실 server call 부재 시 (404 또는 network error) None 반환 — caller 의
"최신 버전 정보 없음" UI 표시 의무.

설계 결정
---------
- CURRENT_VERSION = "0.4.0-phase4-infra" — Phase 4 infra cycle 정합. semver
  + pre-release tag (PEP 440 호환).
- httpx 미설치 환경 의 graceful fallback — import 시도 + ImportError 시
  RuntimeError. 실 호출은 caller 의 mock 의무 (cycle 132 skeleton 정합).
- compare_versions 음수 = 신 버전 가용 / 0 = 동일 / 양수 = 현 버전 신
  (Python list compare 패턴 정합).

본 cycle 의 범위 외
-------------------
- 실 server 의 endpoint 구현 (별개 cycle)
- 채널 분기 (stable / beta / nightly)
- 강제 업데이트 (force=true 시 차단 UI)
"""

from __future__ import annotations

import logging
import re
from typing import Final, Optional

log = logging.getLogger(__name__)

# 한글 주석: TooTalk 의 현 버전 — Phase 4 infra cycle 정합 (cycle 132)
CURRENT_VERSION: Final[str] = "0.4.0-phase4-infra"

# 한글 주석: semver MAJOR.MINOR.PATCH + 선택 pre-release tag (-<id>)
_SEMVER_RE: Final[re.Pattern[str]] = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z\.\-]+))?$"
)

# 한글 주석: 서버 endpoint path — base URL caller 주입 의무
_VERSION_ENDPOINT_PATH: Final[str] = "/api/version/latest"

# 한글 주석: httpx timeout default — 초 단위
_DEFAULT_TIMEOUT_SECONDS: Final[float] = 10.0


def _parse_semver(version: str) -> tuple[int, int, int, str]:
    """semver 문자열 → (major, minor, patch, prerelease) tuple 파싱.

    Raises
    ------
    ValueError
        semver 형식 위반 (정규식 mismatch).
    """

    match = _SEMVER_RE.match(version.strip())
    if not match:
        raise ValueError(f"semver 형식 위반 — {version!r}")
    major, minor, patch, pre = match.groups()
    return (int(major), int(minor), int(patch), pre or "")


def compare_versions(current: str, latest: str) -> int:
    """두 semver 문자열 의 비교.

    Returns
    -------
    int
        음수 = current < latest (신 버전 가용)
        0    = current == latest
        양수 = current > latest (현 버전 신 — 개발 빌드 등)

    Raises
    ------
    ValueError
        둘 중 하나가 semver 형식 위반.
    """

    cur = _parse_semver(current)
    lat = _parse_semver(latest)
    # 한글 주석: major.minor.patch 우선 비교
    for c, l in zip(cur[:3], lat[:3]):
        if c != l:
            return c - l
    # 한글 주석: prerelease 의 비교 — 부재 (release) 가 prerelease 보다 신
    cur_pre, lat_pre = cur[3], lat[3]
    if cur_pre == lat_pre:
        return 0
    if not cur_pre:
        # 한글 주석: current 가 release, latest 가 prerelease — current 신
        return 1
    if not lat_pre:
        # 한글 주석: latest 가 release, current 가 prerelease — latest 신
        return -1
    # 한글 주석: 둘 다 prerelease — 문자열 비교 fallback (semver spec 의 단순화)
    if cur_pre < lat_pre:
        return -1
    if cur_pre > lat_pre:
        return 1
    return 0


async def check_latest_version(server_url: str) -> Optional[dict]:
    """서버 `/api/version/latest` GET + 응답 dict 반환.

    Parameters
    ----------
    server_url : str
        base URL (예 "https://update.tootalk.example"). 경로 자동 부착.

    Returns
    -------
    Optional[dict]
        성공 시 ``{"version": "0.5.0", "download_url": "...", "sha256": "..."}``
        형태. 404 또는 network error 시 None.
    """

    # 한글 주석: httpx 미설치 환경 의 graceful fallback (cycle 132 skeleton)
    try:
        import httpx  # type: ignore[import-not-found]
    except ImportError as e:
        log.warning("httpx 미설치 — 버전 확인 skip (%s)", e)
        return None

    url = f"{server_url.rstrip('/')}{_VERSION_ENDPOINT_PATH}"
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
            if response.status_code == 404:
                log.info("최신 버전 정보 없음 — 404 (서버 endpoint 미구현 가능)")
                return None
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                log.warning("응답 형식 위반 — dict 아님 (%s)", type(data).__name__)
                return None
            log.info(
                "최신 버전 확인 PASS — latest=%s",
                data.get("version", "(unknown)"),
            )
            return data
    except Exception as e:
        log.warning("버전 확인 FAIL — %s (graceful None)", e)
        return None
