# Mac 开发者打包 Windows EXE 指南

## 🎯 方案对比

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **GitHub Actions** | 免费、自动化、无需Windows | 需要 GitHub 账号 | ⭐⭐⭐⭐⭐ |
| **虚拟机** | 完全控制 | 需要 Windows 许可证、占用资源 | ⭐⭐⭐ |
| **云端Windows** | 按需使用 | 需要付费 | ⭐⭐⭐ |
| **借朋友电脑** | 简单直接 | 不方便、依赖他人 | ⭐⭐ |

---

## 🚀 方案一：GitHub Actions（推荐）

### 第一步：创建 GitHub 仓库

```bash
# 在 worktree 目录中
cd .worktrees/web-ui

# 初始化 git（如果还没初始化）
git init

# 添加所有文件
git add .

# 提交
git commit -m "Add web application with Windows build support"
```

### 第二步：推送到 GitHub

```bash
# 在 GitHub 上创建新仓库（访问 github.com → New repository）
# 假设仓库名为 boss-zhipin-web-ui

# 添加远程仓库
git remote add origin https://github.com/你的用户名/boss-zhipin-web-ui.git

# 推送代码
git push -u origin main
```

### 第三步：自动构建

推送成功后，GitHub 会自动：
1. 在 Windows 环境运行构建
2. 打包 Windows exe
3. 生成下载链接

### 第四步：下载 exe

1. 访问 GitHub 仓库
2. 点击 **Actions** 标签
3. 选择最新的构建任务
4. 在 **Artifacts** 区域下载 `BOSS直聘管理工具-Windows`
5. 解压后得到 exe 文件

---

## 🔧 方案二：使用 Parallels/VMware

### 安装 Windows 虚拟机

```bash
# 1. 安装 Parallels Desktop 或 VMware Fusion
# 2. 下载 Windows 11 Dev VM（免费）
#    https://developer.microsoft.com/en-us/windows/downloads/virtual-machines/

# 3. 导入虚拟机

# 4. 在 Windows 虚拟机中：
#    - 安装 Python 3.11
#    - 复制项目文件
#    - 运行 build.bat
```

---

## 💻 方案三：云端 Windows 服务器

### 选项 A：Azure 免费账户

```bash
# 1. 注册 Azure 免费账户
#    https://azure.microsoft.com/

# 2. 创建 Windows 虚拟机

# 3. 远程桌面连接

# 4. 运行打包脚本
```

### 选项 B：AWS EC2

```bash
# 1. 注册 AWS
# 2. 启动 Windows 实例
# 3. 远程桌面连接
# 4. 打包项目
```

---

## 🔄 方案四：跨平台构建工具

### 使用 Docker（实验性）

```bash
# 1. 安装 Docker Desktop for Mac

# 2. 创建 Dockerfile
FROM python:3.11-windowsservercore
# ... 配置 Windows 环境 ...

# 3. 构建并运行
docker build -t boss-zhipin-build .
docker run boss-zhipin-build
```

*注意：Docker for Mac 对 Windows 容器支持有限*

---

## 📦 手动操作：文件传输

如果借朋友 Windows 电脑：

```bash
# 1. 打包项目文件（不含数据库）
zip -r boss-zhipin-web-ui.zip .worktrees/web-ui/code/ -x "*.pyc" "__pycache__"

# 2. 传到 Windows 电脑

# 3. 在 Windows 上：
cd code
python build.py
```

---

## 🎁 我可以帮你

告诉我你想用哪个方案，我可以：

**方案一（GitHub Actions）**：
- 帮你创建完整的 GitHub 仓库
- 生成 push 脚本
- 配置自动化构建

**方案二（虚拟机）**：
- 提供 Windows 11 Dev VM 下载链接
- 虚拟机配置步骤

**方案三（云端）**：
- Azure/AWS 详细设置教程
- 远程桌面连接指南

**方案四（手动传输）**：
- 创建干净的打包文件
- 生成传输清单

---

## ⚡ 快速开始

选择 GitHub Actions 的话，现在就可以：

```bash
# 1. 确认在 worktree 目录
pwd
# 应该显示: .../2026-03-10-boss直聘搜索/.worktrees/web-ui

# 2. 检查文件
ls -la .github/workflows/
# 应该看到: build-windows.yml

# 3. 检查 git 状态
git status

# 4. 如果需要，提交 GitHub Actions 配置
git add .github/
git commit -m "Add GitHub Actions for Windows build"
```

然后告诉我，我帮你完成后续步骤！
