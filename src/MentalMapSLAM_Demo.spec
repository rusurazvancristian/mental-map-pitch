# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['pitch_demo\\launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('pitch_demo\\ui.html', 'pitch_demo'), ('pitch_demo\\photogrammetry.html', 'pitch_demo'), ('pitch_demo\\thumbs', 'pitch_demo\\thumbs'), ('pitch_demo\\assets', 'pitch_demo\\assets'), ('vendor', 'vendor'), ('output\\demo_3d.html', 'output'), ('output\\video_1_demo.mp4', 'output'), ('output\\video_2_demo.mp4', 'output'), ('output\\video_3_demo.mp4', 'output'), ('output\\video_4_demo.mp4', 'output'), ('output\\video_5_demo.mp4', 'output'), ('output\\all_maps.png', 'output'), ('output\\merged_cloud.ply', 'output'), ('output\\video_1_cloud.ply', 'output'), ('output\\video_2_cloud.ply', 'output'), ('output\\video_3_cloud.ply', 'output'), ('output\\video_4_cloud.ply', 'output'), ('output\\video_5_cloud.ply', 'output')],
    hiddenimports=['webview.platforms.edgechromium', 'webview.platforms.winforms'],
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
    [],
    exclude_binaries=True,
    name='MentalMapSLAM_Demo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    upx=True,
    upx_exclude=[],
    name='MentalMapSLAM_Demo',
)
