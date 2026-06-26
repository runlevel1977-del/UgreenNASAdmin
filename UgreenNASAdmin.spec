# -*- mode: python ; coding: utf-8 -*-
import os

PROJECT = os.path.abspath(SPECPATH)
MAIN = os.path.join(PROJECT, "ugreen_nas_admin.py")
ICON = os.path.join(PROJECT, "nas_icon.ico")
PNG = os.path.join(PROJECT, "nas_icon_app.png")
NAS_WATCH = os.path.join(PROJECT, "ugreen_app", "resources", "nas_central_watch.py")
NAS_DAILY = os.path.join(PROJECT, "ugreen_app", "resources", "nas_daily_report.py")
NAS_SB_RUNNER = os.path.join(PROJECT, "ugreen_app", "resources", "ugreen_scheduled_backup_runner.py")
README = os.path.join(PROJECT, "README.md")
CHANGELOG = os.path.join(PROJECT, "CHANGELOG.md")
MANUAL_DE_PDF = os.path.join(PROJECT, "HANDBUCH.pdf")
MANUAL_EN_PDF = os.path.join(PROJECT, "HANDBOOK_EN.pdf")
MANUAL_DE_MD = os.path.join(PROJECT, "HANDBUCH.md")
MANUAL_EN_MD = os.path.join(PROJECT, "HANDBOOK_EN.md")
HANDBOOK_PAGE_INDEX = os.path.join(PROJECT, "handbook_page_index.json")

_DATAS = [
    (ICON, "."),
    (PNG, "."),
    (NAS_WATCH, "ugreen_app/resources"),
    (NAS_DAILY, "ugreen_app/resources"),
]
if os.path.isfile(NAS_SB_RUNNER):
    _DATAS.append((NAS_SB_RUNNER, "ugreen_app/resources"))
if os.path.isfile(README):
    _DATAS.append((README, "."))
if os.path.isfile(CHANGELOG):
    _DATAS.append((CHANGELOG, "."))
if os.path.isfile(MANUAL_DE_PDF):
    _DATAS.append((MANUAL_DE_PDF, "."))
if os.path.isfile(MANUAL_EN_PDF):
    _DATAS.append((MANUAL_EN_PDF, "."))
if os.path.isfile(MANUAL_DE_MD):
    _DATAS.append((MANUAL_DE_MD, "."))
if os.path.isfile(MANUAL_EN_MD):
    _DATAS.append((MANUAL_EN_MD, "."))
if os.path.isfile(HANDBOOK_PAGE_INDEX):
    _DATAS.append((HANDBOOK_PAGE_INDEX, "."))

a = Analysis(
    [MAIN],
    pathex=[PROJECT],
    binaries=[],
    datas=_DATAS,
    hiddenimports=[
        "ugreen_app",
        "ugreen_app._paramiko",
        "ugreen_app.nas_manager",
        "ugreen_app.mixin_safety_lock",
        "ugreen_app.mixin_theme_ui",
        "ugreen_app.mixin_tabs_setup",
        "ugreen_app.mixin_storage_acl_snap",
        "ugreen_app.mixin_config_telegram",
        "ugreen_app.keyring_helper",
        "ugreen_app.mixin_scripts_docker_monitor",
        "ugreen_app.mixin_qnap_smb",
        "ugreen_app.win_smb_peer",
        "ugreen_app.mixin_explorer",
        "ugreen_app.mixin_transfer",
        "ugreen_app.rounded_ui",
        "ugreen_app.i18n",
        "ugreen_app.i18n_backup_locales",
        "ugreen_app.i18n_supplement_devices_telegram",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageTk",
        "ugreen_app.mixin_login_track",
        "ugreen_app.mixin_nas_admin",
        "ugreen_app.resources.login_track_collect",
        "ugreen_app.i18n_supplement_login_track",
        "ugreen_app.i18n_supplement_nas_admin",
        "ugreen_app.mixin_nas_watch_deploy",
        "ugreen_app.docker_deploy_wizard",
        "ugreen_app.mixin_editor_cron",
        "ugreen_app.transfer_log",
        "ugreen_app.tooltip",
        "ugreen_app.mixin_update_check",
        "ugreen_app.update_check",
        "ugreen_app.mixin_ugos_api",
        "ugreen_app.ugos_api_client",
        "ugreen_app.mixin_migration_assistant",
        "ugreen_app.mixin_handbook_tab",
        "ugreen_app.mixin_runlevel_apps",
        "ugreen_app.runlevel_apps_scan",
        "ugreen_app.handbook_nav",
        "ugreen_app.docker_app_center_recipes",
        "cryptography",
        "cryptography.hazmat.primitives.asymmetric.padding",
        "cryptography.hazmat.primitives.serialization",
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
    upx=False,
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
