#!/bin/bash
# ========================================
# BOSS 直聘管理工具 - macOS/Linux 打包脚本
# ========================================

set -e

echo "========================================"
echo " BOSS 直聘管理工具 - 打包工具"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.8+"
    exit 1
fi

echo "[1/4] 安装依赖包..."
pip3 install -r requirements.txt

echo ""
echo "[2/4] 清理旧的打包文件..."
rm -rf dist build

echo ""
echo "[3/4] 开始打包（可能需要几分钟）..."
pyinstaller web_app.spec

echo ""
echo "[4/4] 复制用户说明文件..."
cp "用户使用说明.txt" dist/
mkdir -p dist/data

echo ""
echo "========================================"
echo " 打包完成！"
echo "========================================"
echo ""
echo "可执行文件位置: dist/BOSS直聘管理工具"
echo ""
echo "使用说明:"
echo "  1. 将 dist 文件夹复制到任意位置"
echo "  2. 双击运行 BOSS直聘管理工具"
echo "  3. 在浏览器中访问 http://localhost:5001"
echo ""
echo "========================================"
