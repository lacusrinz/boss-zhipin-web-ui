# Windows 打包问题解决指南

## 问题：ModuleNotFoundError: No module named 'requests'

此错误表示 PyInstaller 没有将所有必要的模块打包到 exe 文件中。

## 解决步骤

### 第一步：在 Windows 上拉取最新代码

```cmd
# 进入项目目录
cd path\to\boss-zhipin-web-ui

# 拉取最新代码（包含更新的 spec 文件）
git pull origin feature/web-ui

# 或者如果你有未提交的更改，先 stash
git stash
git pull origin feature/web-ui
git stash pop
```

### 第二步：确保所有依赖都已安装

```cmd
# 进入 code 目录
cd code

# 清理旧的 Python 缓存
pip cache purge

# 重新安装所有依赖
pip install -r ..\requirements.txt

# 验证 requests 已安装
pip show requests
```

### 第三步：完全清理旧的构建

```cmd
# 在 code 目录中
cd ..

# 删除构建缓存目录
rmdir /s /q code\build
rmdir /s /q code\dist
rmdir /s /q code\__pycache__

# 删除 PyInstaller 缓存
rmdir /s /q %LocalAppData%\pyinstaller
rmdir /s /q %Temp%\pyinstaller
```

### 第四步：重新打包

```cmd
cd code

# 方法1：使用 spec 文件
pyinstaller web_app.spec

# 方法2：如果上面失败，尝试显式指定
pyinstaller --clean web_app.spec
```

### 第五步：验证打包结果

```cmd
# 检查生成的文件
dir dist\BOSS直聘管理工具

# 应该看到：
# - BOSS直聘管理工具.exe
# - database.py
# - feishu_service.py
# - templates 目录
# - parsers 目录
```

### 第六步：测试运行

```cmd
cd dist
"BOSS直聘管理工具.exe"
```

## 如果还是失败

### 诊断步骤 1：检查 spec 文件版本

```cmd
# 确保 code/web_app.spec 包含以下导入：
type code\web_app.spec | findstr "requests"
```

应该看到：
```
'requests',
'requests.packages',
'requests.packages.urllib3',
```

### 诊断步骤 2：手动验证导入

在 Windows 上创建测试文件 `test_imports.py`：

```python
import sys
print("Python path:", sys.path)

try:
    import requests
    print("✓ requests imported successfully")
except ImportError as e:
    print("✗ requests import failed:", e)

try:
    import feishu_service
    print("✓ feishu_service imported successfully")
except ImportError as e:
    print("✗ feishu_service import failed:", e)
```

运行测试：
```cmd
python test_imports.py
```

### 诊断步骤 3：查看详细构建日志

```cmd
pyinstaller web_app.spec --log-level DEBUG
```

查看输出中是否有 warnings 关于 missing modules。

## 常见问题

### Q1: git pull 失败？
**A:**
```cmd
# 如果有冲突，使用强制重置
git fetch origin
git reset --hard origin/feature/web-ui
```

### Q2: pip install 失败？
**A:**
```cmd
# 使用国内镜像源
pip install -r ..\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q3: PyInstaller 卡住？
**A:**
```cmd
# 杀掉所有 Python 进程
taskkill /f /im python.exe
taskkill /f /im pyinstaller.exe

# 然后重新开始
```

## 终极解决方案：使用 PyInstaller 的 --collect-all

如果上述方法都失败，在 spec 文件中添加：

```python
# 在 Analysis 中添加
a = Analysis(
    ['web_app.py'],
    ...
    # 添加这一行
    collect_all=['requests', 'flask', 'apscheduler'],
    ...
)
```

或者使用命令行：
```cmd
pyinstaller --collect-all requests --collect-all flask web_app.spec
```

## 验证成功的标志

运行 exe 后应该看到：
```
============================================================
BOSS 直聘 Web 管理界面
============================================================

启动服务器...
数据库路径: C:\xxx\data\boss_jobs.db

访问地址: http://localhost:5001

按 Ctrl+C 停止服务器
============================================================
```

而不是 ModuleNotFoundError。
