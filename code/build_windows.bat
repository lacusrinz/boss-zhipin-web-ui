@echo off
echo ============================================================
echo BOSS 直聘管理工具 - Windows 打包脚本（完整版）
echo ============================================================
echo.

REM 检查是否在正确的目录
if not exist "web_app.py" (
    echo 错误：请先进入 code 目录
    echo 使用命令：cd code
    pause
    exit /b 1
)

echo [步骤 1/6] 清理旧的构建...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
echo ✓ 清理完成
echo.

echo [步骤 2/6] 清理 PyInstaller 缓存...
if exist "%LocalAppData%\pyinstaller" rmdir /s /q "%LocalAppData%\pyinstaller"
if exist "%Temp%\_MEI*" rmdir /s /q "%Temp%\_MEI*"
echo ✓ 缓存清理完成
echo.

echo [步骤 3/6] 安装所有依赖...
echo 正在安装 requirements.txt 中的所有包...
pip install -r ..\requirements.txt
if errorlevel 1 (
    echo ❌ 依赖安装失败！
    pause
    exit /b 1
)
echo ✓ 依赖安装完成
echo.

echo [步骤 4/6] 开始打包（使用 spec 文件）...
echo 这可能需要 2-5 分钟，请耐心等待...
echo.

pyinstaller --clean web_app.spec

if errorlevel 1 (
    echo.
    echo ❌ 打包失败！
    pause
    exit /b 1
)

echo.
echo [步骤 5/6] 检查打包结果...
if not exist "dist\BOSS直聘管理工具.exe" (
    echo ❌ 打包失败：未找到 exe 文件
    pause
    exit /b 1
)
echo ✓ 打包成功
echo.

echo [步骤 6/6] 创建启动配置...
echo # 飞书推送配置 > dist\.env.example
echo FEISHU_APP_ID=your_app_id >> dist\.env.example
echo FEISHU_APP_SECRET=your_app_secret >> dist\.env.example
echo FEISHU_VERIFY_SSL=true >> dist\.env.example
echo.

echo ============================================================
echo ✓ 打包完成！
echo ============================================================
echo.
echo 生成的文件：dist\BOSS直聘管理工具.exe
echo.
echo 使用说明：
echo 1. 将 dist 目录重命名或复制到目标位置
echo 2. 双击运行 BOSS直聘管理工具.exe
echo 3. 在浏览器中访问 http://localhost:5001
echo.
echo 注意：
echo - 首次运行可能需要几分钟解压（因为使用了 --onefile）
echo - 如需禁用 SSL 验证，在 exe 同级目录创建 .env 文件并设置：
echo   FEISHU_VERIFY_SSL=false
echo.
echo ============================================================
pause
