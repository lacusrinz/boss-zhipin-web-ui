# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller 规范文件
用于将 BOSS 直聘 Web 管理界面打包为 Windows exe 文件
"""

import os
import sys

block_cipher = None

# 获取当前目录，确保 PyInstaller 能找到本地模块
current_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['web_app.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        # 包含模板文件
        ('templates', 'templates'),
        # 包含解析器模块
        ('parsers', 'parsers'),
        # 包含本地Python模块
        ('database.py', '.'),
        ('feishu_service.py', '.'),
        ('token_service.py', '.'),
    ],
    hiddenimports=[
        # External packages
        'bs4',
        'lxml',
        'lxml._elementpath',
        'openpyxl',
        'sqlite3',
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects',
        'apscheduler.jobstores.sqlalchemy',
        'apscheduler.executors.pool',
        'apscheduler.executors.base',
        'apscheduler.jobstores.base',
        # Local modules
        'database',
        'parsers',
        'parsers.base',
        'parsers.boss_zhipin',
        'feishu_service',
        'token_service',
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BOSS直聘管理工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台，方便查看日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加 .ico 图标文件
)
