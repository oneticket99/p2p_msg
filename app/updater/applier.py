# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 132 — TooTalk 업데이트 패키지 의 적용 (binary swap skeleton).

zipfile.ZipFile extract + 기존 binary 백업 + macOS / Windows 분기.
Phase 5 본격 cycle 의 실 swap chain + atexit relaunch + rollback 의 완성 의무.

본 cycle 의 범위 (skeleton)
---------------------------
- platform 분기 (sys.platform 검사)
- zipfile 의 유효성 검사 (is_zipfile + namelist)
- 백업 디렉토리 경로 산출 (.tootalk_backup_<ts>)
- 실 swap = 미실행 (Phase 5)

본 cycle 의 범위 외 (Phase 5)
------------------------------
- 실 binary swap (file move + permission preserve)
- macOS .app bundle 의 in-place replace (atomic rename)
- Windows .exe 의 self-update 경로 (move-on-reboot 또는 sidecar updater.exe)
- atexit relaunch (subprocess.Popen + sys.exit)
- 실패 시 자동 rollback (백업 → 원위치 복원)
- 사용자 권한 elevation (Windows UAC + macOS sudo prompt)
"""

from __future__ import annotations

import logging
import sys
import zipfile
from pathlib import Path
from typing import Final

log = logging.getLogger(__name__)

# 한글 주석: 백업 디렉토리 prefix — install_dir 부모 의 sibling 으로 생성
_BACKUP_PREFIX: Final[str] = ".tootalk_backup_"

# 한글 주석: 지원 platform 목록
_PLATFORM_MACOS: Final[str] = "darwin"
_PLATFORM_WINDOWS: Final[str] = "win32"


def _detect_platform() -> str:
    """현 platform 식별자 반환 (sys.platform 기반).

    Returns
    -------
    str
        "darwin" (macOS) / "win32" (Windows) / 그 외 (raw sys.platform).
    """

    return sys.platform


def apply_update(zip_path: Path, install_dir: Path) -> bool:
    """업데이트 zip 의 적용 (cycle 132 skeleton — 실 swap 부재).

    Parameters
    ----------
    zip_path : Path
        다운로드 완료 + SHA-256 검증 PASS 의 zip 파일.
    install_dir : Path
        설치 경로 (macOS .app bundle 또는 Windows install dir).

    Returns
    -------
    bool
        True = skeleton chain PASS (validation + branch 진입).
        False = zip 무효 또는 platform 미지원.

    Notes
    -----
    실 binary swap 은 Phase 5 cycle 의 완성 의무. 본 함수는 chain skeleton
    + log + branch 진입 검증 만 수행.
    """

    # 한글 주석: zip 파일 존재 + 유효성 검사
    if not zip_path.exists():
        log.error("zip 부재 — %s", zip_path)
        return False
    if not zipfile.is_zipfile(zip_path):
        log.error("zip 형식 위반 — %s", zip_path)
        return False

    platform = _detect_platform()
    log.info(
        "업데이트 적용 시작 — platform=%s zip=%s install_dir=%s",
        platform,
        zip_path,
        install_dir,
    )

    # 한글 주석: zip 내부 목록 sanity check (extract 부재 — Phase 5 의무)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            if not namelist:
                log.error("zip 의 entry 부재 — %s", zip_path)
                return False
            log.info("zip entry 수=%d (sample=%s)", len(namelist), namelist[:3])
    except zipfile.BadZipFile as e:
        log.error("zip 손상 — %s", e)
        return False

    if platform == _PLATFORM_MACOS:
        return _apply_macos_skeleton(zip_path, install_dir)
    if platform == _PLATFORM_WINDOWS:
        return _apply_windows_skeleton(zip_path, install_dir)

    log.warning(
        "platform 미지원 — %s (skeleton 의 macOS/Windows 만 지원)", platform
    )
    return False


def _apply_macos_skeleton(zip_path: Path, install_dir: Path) -> bool:
    """macOS .app bundle 의 swap skeleton (Phase 5 의무).

    실 chain (Phase 5):
    1. install_dir.parent 에 백업 .tootalk_backup_<ts>/ 생성
    2. 현 .app bundle 을 백업 디렉토리 로 mv
    3. zip extract → install_dir.parent
    4. extract 결과 검증 (Info.plist + 실행 binary 존재)
    5. atexit hook 등록 + subprocess.Popen([new_app, ...]) + sys.exit
    """

    log.info(
        "[macOS skeleton] swap chain 진입 — zip=%s install_dir=%s "
        "(실 swap 은 Phase 5 의무)",
        zip_path,
        install_dir,
    )
    return True


def _apply_windows_skeleton(zip_path: Path, install_dir: Path) -> bool:
    """Windows .exe 의 self-update skeleton (Phase 5 의무).

    실 chain (Phase 5):
    1. install_dir.parent 에 백업 .tootalk_backup_<ts>/ 생성
    2. sidecar updater.exe 추출 → 임시 디렉토리
    3. updater.exe 를 subprocess.Popen + DETACHED_PROCESS 로 기동
    4. updater.exe 가 본 프로세스 종료 대기 → 본체 .exe 의 move + zip extract
    5. updater.exe 가 새 본체 .exe 기동 + 자가 삭제
    """

    log.info(
        "[Windows skeleton] swap chain 진입 — zip=%s install_dir=%s "
        "(실 swap 은 Phase 5 의무)",
        zip_path,
        install_dir,
    )
    return True
