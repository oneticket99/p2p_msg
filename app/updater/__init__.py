# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk 자동 업데이트 client base — version check + download + verify + apply (cycle 132 skeleton).

Phase 4 cycle 132 — 사용자 directive 의 자동 업데이트 client skeleton 신설.
Phase 5 본격 cycle 에서 실 binary swap + relaunch chain 의 완성 의무.

본 module 의 구성
-----------------
- version_check : 서버 /api/version/latest GET + semver 비교
- downloader    : httpx async chunk download + SHA-256 progressive 검증
- applier       : zipfile extract + macOS/Windows swap skeleton

본 cycle 의 범위 외 (별개 cycle)
--------------------------------
- 실 binary swap chain (Phase 5)
- code-signing 검증 (notarization + Windows Authenticode)
- 자동 rollback (실패 시 이전 버전 복원)
- delta patch (bsdiff/zsync)
- 백그라운드 자동 다운로드 정책 (Wi-Fi only + 야간)
"""

from app.updater.applier import apply_update
from app.updater.downloader import download_update_async
from app.updater.version_check import (
    CURRENT_VERSION,
    check_latest_version,
    compare_versions,
)

__all__ = [
    "CURRENT_VERSION",
    "check_latest_version",
    "compare_versions",
    "download_update_async",
    "apply_update",
]
