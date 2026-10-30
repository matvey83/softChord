# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for softChord (macOS .app, Windows .exe, Linux executable)."""

import os
import sys

# The version comes from src/softchord_version.py, the one place it is set.
sys.path.insert(0, os.path.join(SPECPATH, "src"))
from softchord_version import __version__  # noqa: E402

# Document type used in the macOS Info.plist so Finder associates *.songbook.
SONGBOOK_UTI = "com.matvey83.softchord.songbook"

info_plist = {
    "CFBundleName": "softChord",
    "CFBundleDisplayName": "softChord",
    "CFBundleGetInfoString": "softChord",
    "CFBundleIdentifier": "com.matvey83.softchord",
    "CFBundlePackageType": "APPL",
    "CFBundleShortVersionString": __version__,
    "CFBundleVersion": __version__,
    "NSHighResolutionCapable": True,
    "NSPrincipalClass": "NSApplication",
    "LSSupportsOpeningDocumentsInPlace": True,
    "NSDocumentsFolderUsageDescription":
        "softChord needs access to your documents to open and save songbook files.",
    "NSDesktopFolderUsageDescription":
        "softChord needs access to the Desktop to open and save songbook files.",
    "NSDownloadsFolderUsageDescription":
        "softChord needs access to Downloads to open and save songbook files.",
    "CFBundleDocumentTypes": [
        {
            "CFBundleTypeName": "softChord songbook",
            "CFBundleTypeRole": "Editor",
            "LSHandlerRank": "Owner",
            "LSItemContentTypes": [SONGBOOK_UTI],
            "CFBundleTypeExtensions": ["songbook"],
            "CFBundleTypeMIMETypes": ["application/x-softchord-songbook"],
        },
    ],
    "UTExportedTypeDeclarations": [
        {
            "UTTypeIdentifier": SONGBOOK_UTI,
            "UTTypeDescription": "softChord songbook",
            "UTTypeConformsTo": ["public.data", "public.content"],
            "UTTypeTagSpecification": {
                "public.filename-extension": ["songbook"],
                "public.mime-type": ["application/x-softchord-songbook"],
            },
        },
    ],
}

# Linux: the .desktop file, MIME type and icon that the AppImage registers in
# ~/.local/share on launch (see register_songbook_file_association).
LINUX_DATAS = []
if sys.platform.startswith("linux"):
    LINUX_DATAS = [("packaging/linux/com.matvey83.softchord.desktop", "linux"),
                   ("packaging/linux/softchord-mime.xml", "linux"),
                   ("packaging/linux/softchord.png", "linux")]

a = Analysis(
    ["src/softchord.py"],
    pathex=["src"],
    binaries=[],
    # The toolbar icons are the web app's SVGs (one copy, see softchord_toolbar.py).
    # songbook.sql sits next to softchord_store.py, which reads the schema
    # from it at import.
    datas=[("src/songbook.sql", "."),
           ("src/icons/softchord.png", "icons"),
           ("softChord_web/icons/toolbar/*.svg", "icons/toolbar")] + LINUX_DATAS,
    hiddenimports=[
        "softchord_version",
        "softchord_chords",
        "softchord_song",
        "softchord_io",
        "softchord_v1_compat",  # TODO(remove-v1-compat)
        "softchord_main_window_ui",
        "softchord_chord_dialog_ui",
        "softchord_pdf_dialog_ui",
        "PyQt6.QtPrintSupport",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngineQuick",
        "PyQt6.Qt3DCore",
        "PyQt6.Qt3DRender",
        "PyQt6.QtBluetooth",
        "PyQt6.QtNfc",
        "PyQt6.QtMultimedia",
        "PyQt6.QtMultimediaWidgets",
        "PyQt6.QtQml",
        "PyQt6.QtQuick",
        "PyQt6.QtQuickWidgets",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="softChord",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name="softChord",
    )
    app = BUNDLE(
        coll,
        name="softChord.app",
        icon="src/icons/softchord.icns",
        bundle_identifier="com.matvey83.softchord",
        info_plist=info_plist,
    )
else:
    # Windows (and Linux): single-file windowed executable.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="softChord",
        icon="src/icons/softchord.ico",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
