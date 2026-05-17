# SPDX-License-Identifier: GPL-3.0-or-later
# PyInstaller spec — TooTalk(p2p_msg) 클라이언트 번들링.
#
# 사용:
#   pyinstaller build/tootalk.spec --clean --noconfirm
#
# 산출물 = dist/TooTalk/ (macOS .app 또는 Windows .exe 의 단일 디렉토리).
# wine cross-compile 의 의 의 의 의 의 의 의 의 의 build.yml + cdrx/pyinstaller-windows docker 정합.
#
# 본 파일 = Python 문법 — PyInstaller 가 직접 exec 한다.

# 한글 주석: macOS 와 Windows 의 의 의 의 의 의 의 의 의 단일 spec — sys.platform 분기 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의

import sys
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH).parent.resolve()
ENTRY = str(ROOT / "app" / "main.py")
APP_NAME = "TooTalk"


a = Analysis(
    [ENTRY],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # qasync + aiortc 의 의 의 의 의 의 의 의 의 의 의 의 의 의 hidden dependency
        "qasync",
        "aiortc",
        "aiortc.contrib.media",
        "av",
        "asyncmy",
        "aiosmtplib",
        "aiofiles",
        "PIL.Image",
        "PIL.ImageOps",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 미사용 대용량 의존성 제외
        "tkinter",
        "matplotlib",
        "numpy.f2py",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # macOS UPX 미지원 + wine 환경 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # macOS .app 의 의 의 의 의 의 의 의 의 의 의 의 dock 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)


# macOS .app 번들 (wine 환경 의 의 의 의 의 의 의 의 의 의 의 skip — wine 의 .exe 산출)
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=None,
        bundle_identifier="com.toonation.tootalk",
        info_plist={
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",  # macOS Big Sur 이상 (arm64 정합)
        },
    )
