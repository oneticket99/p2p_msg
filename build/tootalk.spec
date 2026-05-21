# SPDX-License-Identifier: GPL-3.0-or-later
# PyInstaller spec — TooTalk(p2p_msg) 클라이언트 번들링.
#
# 사용:
#   pyinstaller build/tootalk.spec --clean --noconfirm
#
# 산출물 = dist/TooTalk/ (macOS .app 또는 Windows .exe 의 단일 디렉토리).
# wine cross-compile chain — build.yml + cdrx/pyinstaller-windows docker 정합.
#
# 본 파일 = Python 문법 — PyInstaller 가 직접 exec 한다.

# 한글 주석: macOS + Windows 단일 spec — sys.platform 분기 chain 정합.

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
    datas=[
        # cycle 169.95 회수 — frozen build 안 assets/branding + icons + sounds + sound/wav 패키징 의무
        # path resolve = Path(__file__).resolve().parent.parent / "assets" / ... (= app/assets)
        # PyInstaller 안 dest = app/assets/...
        (str(ROOT / "app" / "assets" / "branding"), "app/assets/branding"),
        (str(ROOT / "app" / "assets" / "icons"), "app/assets/icons"),
        (str(ROOT / "app" / "assets" / "sounds"), "app/assets/sounds"),
        (str(ROOT / "app" / "assets" / "themes"), "app/assets/themes"),
        (str(ROOT / "app" / "sound" / "wav"), "app/sound/wav"),
        # cycle 169.226 — i18n translations qm bundle (5 locale: en/ja/ko/zh-CN/zh-TW)
        (str(ROOT / "app" / "i18n" / "translations"), "app/i18n/translations"),
    ],
    hiddenimports=[
        # qasync + aiortc 누락 hidden dependency 명시
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
        # cycle 169.89 회수 — PyQt6 + PySide6 동시 collect 차단 (dev dependency 의 PySide6)
        "PySide6",
        "PySide2",
        "shiboken6",
        "shiboken2",
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
    upx=False,  # macOS UPX 미지원 + wine 환경 호환 부재 → 비활성
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # macOS .app dock drop file arg 전달 정합
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


# macOS .app 번들 (wine 환경 skip — wine path → .exe 산출)
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
            # cycle 169.112 회수 — TCC privacy crash 차단 (avfoundation + AVCaptureSession)
            "NSMicrophoneUsageDescription": "TooTalk 음성 통화 + 음성 메시지 녹음 의무 마이크 접근.",
            "NSCameraUsageDescription": "TooTalk 영상 통화 + 프로필 사진 촬영 의무 카메라 접근.",
            "NSDesktopFolderUsageDescription": "TooTalk 파일 전송 chain 의무 데스크탑 접근 (선택).",
            "NSDocumentsFolderUsageDescription": "TooTalk 파일 전송 chain 의무 문서 폴더 접근 (선택).",
            "NSDownloadsFolderUsageDescription": "TooTalk 다운로드 file 저장 의무 다운로드 폴더 접근 (선택).",
            "NSPhotoLibraryUsageDescription": "TooTalk 이미지 첨부 의무 사진 라이브러리 접근 (선택).",
        },
    )
