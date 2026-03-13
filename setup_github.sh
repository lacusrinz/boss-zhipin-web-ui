#!/bin/bash
# ========================================
# GitHub 仓库设置和推送脚本
# ========================================

set -e

echo "========================================"
echo " BOSS 直聘管理工具 - GitHub 设置向导"
echo "========================================"
echo ""

# 检查是否在 git 仓库中
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "[错误] 当前不在 git 仓库中"
    echo "请先在 worktree 目录中运行此脚本"
    exit 1
fi

echo "当前分支: $(git branch --show-current)"
echo ""

# 检查是否已有远程仓库
if git remote get-url origin > /dev/null 2>&1; then
    echo "当前远程仓库: $(git remote get-url origin)"
    echo ""
    read -p "是否使用现有远程仓库? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "推送代码到 GitHub..."
        git push -u origin $(git branch --show-current)
        echo ""
        echo "✅ 代码已推送！"
        echo ""
        echo "下一步："
        echo "1. 访问你的 GitHub 仓库"
        echo "2. 点击 'Actions' 标签"
        echo "3. 等待自动构建完成（约 5 分钟）"
        echo "4. 下载构建的 exe 文件"
        echo ""
        exit 0
    fi
fi

echo "请按以下步骤操作："
echo ""
echo "1️⃣  在浏览器中打开 GitHub"
echo "2️⃣  点击右上角 '+' → 'New repository'"
echo "3️⃣  填写仓库信息："
echo "   - Repository name: boss-zhipin-web-ui"
echo "   - Description: BOSS 直聘职位采集 Web 管理工具"
echo "   - 设为 Public 或 Private（Private 需付费账户才能用 Actions）"
echo "   - 不要勾选 'Add a README file'"
echo "4️⃣  点击 'Create repository'"
echo ""
echo "创建完成后，按回车继续..."
read

echo ""
read -p "请输入你的 GitHub 用户名: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "[错误] 用户名不能为空"
    exit 1
fi

REPO_URL="https://github.com/${GITHUB_USERNAME}/boss-zhipin-web-ui.git"

echo ""
echo "将添加远程仓库: $REPO_URL"
read -p "确认? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "[取消] 操作已取消"
    exit 0
fi

# 添加远程仓库
git remote add origin "$REPO_URL"

# 推送代码
echo ""
echo "推送代码到 GitHub..."
git push -u origin $(git branch --show-current)

echo ""
echo "========================================"
echo "✅ 设置完成！"
echo "========================================"
echo ""
echo "仓库地址: $REPO_URL"
echo ""
echo "下一步："
echo "1. 访问上面的仓库地址"
echo "2. 点击 'Actions' 标签"
echo "3. 选择 'Build Windows EXE' 工作流"
echo "4. 等待构建完成（约 5 分钟）"
echo "5. 滚动到页面底部，在 'Artifacts' 区域"
echo "6. 下载 'BOSS直聘管理工具-Windows'"
echo "7. 解压后得到 Windows exe 文件"
echo ""
echo "========================================"
