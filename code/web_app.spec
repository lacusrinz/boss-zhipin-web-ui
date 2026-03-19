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
        # External packages - HTML parsing
        'bs4',
        'lxml',
        'lxml._elementpath',
        # External packages - Excel processing
        'openpyxl',
        # External packages - Database
        'sqlite3',
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects',
        'sqlalchemy.engine',
        'sqlalchemy.pool',
        # External packages - HTTP requests
        'requests',
        'requests.packages',
        'requests.packages.urllib3',
        'urllib3',
        'urllib3.packages',
        # External packages - SSL/Encoding
        'certifi',
        'charset_normalizer',
        'idna',
        # External packages - APScheduler
        'apscheduler',
        'apscheduler.jobstores',
        'apscheduler.jobstores.sqlalchemy',
        'apscheduler.jobstores.base',
        'apscheduler.executors',
        'apscheduler.executors.pool',
        'apscheduler.executors.base',
        'apscheduler.schedulers',
        'apscheduler.schedulers.background',
        'apscheduler.triggers',
        'apscheduler.triggers.interval',
        # External packages - Environment & Config
        'dotenv',
        'dotenv.parser',
        'dotenv.main',
        'python-dotenv',
        # External packages - Timezone & Crypto
        'zoneinfo',
        'cryptography',
        'cryptography.fernet',
        'tzdata',
        # External packages - Flask
        'flask',
        'flask.templating',
        'jinja2',
        'werkzeug',
        'werkzeug.serving',
        # External packages - Logging
        'logging',
        'logging.handlers',
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
