# -*- mode: python ; coding: utf-8 -*-
import os

PROJECT = os.path.abspath(SPECPATH)
MAIN = os.path.join(PROJECT, "ugreen_nas_admin.py")
ICON = os.path.join(PROJECT, "nas_icon.ico")
PNG = os.path.join(PROJECT, "nas_icon_app.png")

a = Analysis(
    [MAIN],
    pathex=[PROJECT],
    binaries=[],
    datas=[
        (ICON, "."),
        (PNG, "."),
    ],
    hiddenimports=[
        "ugreen_app",
        "ugreen_app._paramiko",
        "ugreen_app.nas_manager",
        "ugreen_app.mixin_theme_ui",
        "ugreen_app.mixin_tabs_setup",
        "ugreen_app.mixin_storage_acl_snap",
        "ugreen_app.mixin_config_telegram",
        "ugreen_app.mixin_scripts_docker_monitor",
        "ugreen_app.mixin_explorer",
        "ugreen_app.mixin_transfer",
        "ugreen_app.rounded_ui",
        "ugreen_app.i18n",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageTk",
        "ugreen_app.mixin_editor_cron",
        "ugreen_app.transfer_log",
        "ugreen_app.tooltip",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="UgreenNASAdmin",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[ICON],
)
