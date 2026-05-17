# SPDX-License-Identifier: GPL-3.0-or-later
"""TooTalk(p2p_msg) 빌드 래퍼 — macOS native + Windows wine.

사용::

    python tools/build.py --target macos     # macOS .app 의 의 PyInstaller native
    python tools/build.py --target windows   # wine cross-compile (Ubuntu + cdrx docker)
    python tools/build.py --target all       # 두 대상 의 순차 진행

산출:
    dist/TooTalk.app           (macOS)
    dist/TooTalk/TooTalk.exe   (Windows via wine)

[[project-windows-build-via-wine]] 정합 — GitHub-hosted Ubuntu + cdrx/pyinstaller-windows docker 이미지.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("build")

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "build" / "tootalk.spec"
DIST = ROOT / "dist"


def _run(cmd: list[str], *, cwd: Path | None = None) -> int:
    """subprocess 실행 + 표준출력 stream."""

    log.info("[build] $ %s", " ".join(cmd))
    return subprocess.call(cmd, cwd=cwd or ROOT)


def build_macos() -> int:
    """macOS PyInstaller native build."""

    if sys.platform != "darwin":
        log.error("[build] macos target = darwin 만 지원")
        return 1

    if not SPEC.exists():
        log.error("[build] spec 부재 — %s", SPEC)
        return 1

    return _run([
        sys.executable, "-m", "PyInstaller",
        str(SPEC), "--clean", "--noconfirm",
        "--distpath", str(DIST),
        "--workpath", str(ROOT / "build" / "work"),
    ])


def build_windows_via_wine() -> int:
    """Windows wine cross-compile — Ubuntu host + cdrx/pyinstaller-windows docker.

    Notes
    -----
    본 함수 = CI (GitHub Actions Ubuntu) 또는 사용자 직접 docker 환경 의 의 의 의 호출.
    Docker daemon 필요 — `docker version` 의 의 의 의 의 의 사전 점검.
    """

    if shutil.which("docker") is None:
        log.error("[build] docker 미설치 — wine cross-compile 불가")
        return 1

    image = "cdrx/pyinstaller-windows:python3"
    container_root = "/src"
    cmd_in_container = (
        "pip install -r app/requirements.txt && "
        "pyinstaller build/tootalk.spec --clean --noconfirm "
        "--distpath dist-windows --workpath build/work-win"
    )

    return _run([
        "docker", "run", "--rm",
        "-v", f"{ROOT}:{container_root}",
        "-w", container_root,
        image,
        "/bin/sh", "-c", cmd_in_container,
    ])


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="TooTalk 빌드 래퍼")
    parser.add_argument(
        "--target",
        choices=("macos", "windows", "all"),
        default="macos",
        help="빌드 대상 (default: macos)",
    )
    args = parser.parse_args()

    if args.target in ("macos", "all"):
        rc = build_macos()
        if rc != 0:
            return rc

    if args.target in ("windows", "all"):
        rc = build_windows_via_wine()
        if rc != 0:
            return rc

    log.info("[build] 완료 — dist=%s", DIST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
