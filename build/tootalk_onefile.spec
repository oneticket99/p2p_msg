# SPDX-License-Identifier: GPL-3.0-or-later
# cycle 169.651 — PyInstaller --onefile mode spec (NFR-03 Team ID mismatch 회수 path 1st).
#
# 기존 build/tootalk.spec = onedir mode (EXE + COLLECT + BUNDLE).
# 본 spec = onefile mode (EXE 안 binaries 통합 + BUNDLE 직접 wrap).
#
# 의도: PyInstaller bootloader 가 single self-extract binary 안 Python framework + dependencies
# 통합 → Team ID mismatch 회피 가능성 (Apple-signed Python framework 의 standalone load 부재).
#
# 사용:
#   pyinstaller build/tootalk_onefile.spec --clean --noconfirm

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

ROOT = Path(SPECPATH).parent.resolve()
ENTRY = str(ROOT / "app" / "main.py")
APP_NAME = "TooTalk"


a = Analysis(
    [ENTRY],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "app" / "assets" / "branding"), "app/assets/branding"),
        (str(ROOT / "app" / "assets" / "icons"), "app/assets/icons"),
        (str(ROOT / "app" / "assets" / "sounds"), "app/assets/sounds"),
        (str(ROOT / "app" / "assets" / "themes"), "app/assets/themes"),
        (str(ROOT / "app" / "sound" / "wav"), "app/sound/wav"),
        (str(ROOT / "app" / "i18n" / "translations"), "app/i18n/translations"),
    ],
    hiddenimports=collect_submodules("aiortc") + collect_submodules("av") + [
        "qasync",
        "aiortc",
        "aiortc.contrib.media",
        "aiortc.contrib.signaling",
        "av",
        "av.audio",
        "av.video",
        "av.container",
        "av.codec",
        "av.filter",
        "av.frame",
        "av.packet",
        "av.stream",
        "google_crc32c",
        "google.crc32c",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 한글 주석 — onefile EXE — a.binaries + a.zipfiles + a.datas 의 전수 통합 + exclude_binaries=False.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)


# 한글 주석 — macOS BUNDLE — onefile EXE 직접 wrap (COLLECT 폐기).
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name=f"{APP_NAME}.app",
        icon=None,
        bundle_identifier="com.toonation.tootalk",
        info_plist={
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "NSMicrophoneUsageDescription": "TooTalk 음성 통화 + 음성 메시지 녹음 의무 마이크 접근.",
            "NSCameraUsageDescription": "TooTalk 영상 통화 + 프로필 사진 촬영 의무 카메라 접근.",
            "NSDesktopFolderUsageDescription": "TooTalk 파일 전송 chain 의무 데스크탑 접근 (선택).",
            "NSDocumentsFolderUsageDescription": "TooTalk 파일 전송 chain 의무 문서 폴더 접근 (선택).",
            "NSDownloadsFolderUsageDescription": "TooTalk 다운로드 file 저장 의무 다운로드 폴더 접근 (선택).",
            "NSPhotoLibraryUsageDescription": "TooTalk 이미지 첨부 의무 사진 라이브러리 접근 (선택).",
        },
    )
