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
    """cycle 169.417 — macOS .app bundle swap actual binding (Phase 5 Item 2).

    chain:
    1. install_dir.parent 안 백업 디렉토리 ``.tootalk_backup_<ts>/`` 생성
    2. install_dir (현 .app) → 백업 디렉토리 이동 (shutil.move)
    3. zip extract → install_dir.parent
    4. extract 결과 검증 (TooTalk.app/Contents/MacOS/TooTalk 실행 binary 존재)
    5. 실패 시점 rollback (백업 .app 복원) + False 반환

    Notes
    -----
    relaunch + sys.exit = caller responsibility (update_dialog `_on_apply_clicked`).
    """
    import shutil
    import time as _time
    import zipfile

    ts = int(_time.time())
    backup_dir = install_dir.parent / f".tootalk_backup_{ts}"
    extract_dir = install_dir.parent
    try:
        # step 1 — 백업 디렉토리 생성
        backup_dir.mkdir(parents=True, exist_ok=False)
        # step 2 — 현 .app 백업 이동
        if install_dir.exists():
            shutil.move(str(install_dir), str(backup_dir / install_dir.name))
            log.info("[macOS apply] 현 .app 백업 이동 — %s → %s", install_dir, backup_dir)
        # step 3 — zip extract
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(str(extract_dir))
        log.info("[macOS apply] zip extract PASS — dest=%s", extract_dir)
        # step 4 — 실행 binary 검증
        new_app = extract_dir / install_dir.name
        executable = new_app / "Contents" / "MacOS" / "TooTalk"
        if not executable.is_file():
            raise RuntimeError(f"swap 검증 실패 — {executable} 부재")
        log.info("[macOS apply] swap chain PASS — new_app=%s", new_app)
        return True
    except Exception as exc:
        log.error("[macOS apply] swap 실패 — rollback 진입 — %r", exc)
        # rollback — 백업 .app 복원 (install_dir 부재 시점)
        backup_app = backup_dir / install_dir.name
        if backup_app.exists() and not install_dir.exists():
            try:
                shutil.move(str(backup_app), str(install_dir))
                log.info("[macOS apply] rollback PASS — backup → install_dir")
            except Exception as rb_exc:
                log.error("[macOS apply] rollback 실패 — %r", rb_exc)
        return False


def _apply_windows_skeleton(zip_path: Path, install_dir: Path) -> bool:
    """cycle 169.417 — Windows .exe self-update via batch script (Phase 5 Item 2).

    chain:
    1. tempdir 생성 → zip extract (TooTalk-new/)
    2. batch script 생성 (taskkill TooTalk.exe + xcopy /Y new → install_dir + relaunch)
    3. subprocess.Popen([batch], creationflags=DETACHED_PROCESS) + 본 process exit
    4. batch script = 본 process 종료 후 swap + relaunch + 자가 삭제

    Notes
    -----
    Windows 의 의 의 running .exe 자체 overwrite 불가 → batch script detached process pattern 의무.
    """
    import os as _os
    import subprocess
    import tempfile
    import zipfile

    try:
        tmp_root = Path(tempfile.mkdtemp(prefix="tootalk_update_"))
        extract_dir = tmp_root / "new"
        extract_dir.mkdir(parents=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(str(extract_dir))
        log.info("[Windows apply] zip extract PASS — tmp=%s", extract_dir)

        # 한글 주석 — batch script 생성 (kill + xcopy + relaunch + 자가 삭제)
        batch_path = tmp_root / "apply_update.bat"
        new_exe = extract_dir / "TooTalk.exe"
        if not new_exe.is_file():
            raise RuntimeError(f"swap 검증 실패 — {new_exe} 부재")
        batch_body = (
            "@echo off\r\n"
            "timeout /t 2 /nobreak >nul\r\n"
            f'taskkill /F /IM TooTalk.exe >nul 2>&1\r\n'
            "timeout /t 1 /nobreak >nul\r\n"
            f'xcopy /Y /E /I "{extract_dir}" "{install_dir}" >nul\r\n'
            f'start "" "{install_dir / "TooTalk.exe"}"\r\n'
            f'rmdir /S /Q "{tmp_root}"\r\n'
        )
        batch_path.write_text(batch_body, encoding="utf-8")

        # DETACHED_PROCESS = 0x00000008
        DETACHED = 0x00000008
        subprocess.Popen(
            ["cmd.exe", "/c", str(batch_path)],
            creationflags=DETACHED, close_fds=True,
        )
        log.info("[Windows apply] batch script Popen PASS — caller exit 의무")
        return True
    except Exception as exc:
        log.error("[Windows apply] swap 실패 — %r", exc)
        return False
