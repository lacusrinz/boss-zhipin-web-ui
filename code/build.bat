@echo off
REM ========================================
REM BOSS 直聘管理工具 - Windows 打包脚本
REM ========================================

echo ========================================
echo BOSS 直聘管理工具 - 打包工具
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [1/4] 安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo [2/4] 安装 PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo [错误] PyInstaller 安装失败
    pause
    exit /b 1
)

echo [3/4] 清理旧的打包文件...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build

echo [4/4] 开始打包（可能需要几分钟）...
pyinstaller web_app.spec

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 打包完成！
echo ========================================
echo.
echo 可执行文件位置: dist\BOSS直聘管理工具.exe
echo.
echo 使用说明:
echo 1. 将 dist 文件夹复制到任意位置
echo 2. 双击运行 BOSS直聘管理工具.exe
echo 3. 在浏览器中访问 http://localhost:5001
echo.
echo ========================================

pause
