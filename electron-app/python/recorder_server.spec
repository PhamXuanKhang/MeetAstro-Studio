# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

repo_root = Path.cwd()
electron_dir = repo_root / "electron-app"

block_cipher = None

analysis = Analysis(
    [str(electron_dir / "python" / "recorder_server.py")],
    pathex=[str(repo_root), str(electron_dir / "python")],
    binaries=[],
    datas=[
        (str(repo_root / "src" / "modules" / "audio_recorder.py"), "src/modules"),
        (str(repo_root / "src" / "config.py"), "src"),
        (str(repo_root / "src" / "__init__.py"), "src"),
    ],
    hiddenimports=[
        "numpy",
        "sounddevice",
        "pysysaudio",
        "websocket",
        "pydantic",
        "pydantic_settings",
        "dotenv",
        "src.modules.audio_recorder",
        "src.config",
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

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="recorder_server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="x86_64",
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="recorder_server",
)
