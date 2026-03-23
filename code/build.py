#!/usr/bin/env python3
"""
跨平台打包脚本
支持 Windows 和 macOS/Linux
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description=""):
    """运行命令并处理错误"""
    print(f"\n{'='*60}")
    print(f" {description}")
    print(f"{'='*60}")
    print(f"执行命令: {cmd}")

    result = subprocess.run(cmd, shell=True, capture_output=False)
    if result.returncode != 0:
        print(f"\n[错误] {description} 失败")
        return False
    return True


def main():
    """主打包流程"""
    print("=" * 60)
    print(" BOSS 直聘管理工具 - 打包工具")
    print("=" * 60)

    # 检查 Python 版本
    if sys.version_info < (3, 8):
        print("[错误] 需要 Python 3.8 或更高版本")
        return 1

    # 当前目录
    code_dir = Path(__file__).parent
    os.chdir(code_dir)

    # 1. 安装依赖
    if not run_command(
        "pip install -r requirements.txt",
        "[1/4] 安装依赖包"
    ):
        return 1

    # 2. 清理旧文件
    print(f"\n{'='*60}")
    print(" [2/4] 清理旧的打包文件")
    print(f"{'='*60}")

    for dir_name in ['dist', 'build']:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"  删除 {dir_name}/")

    # 3. 执行打包
    if not run_command(
        "pyinstaller web_app.spec",
        "[3/4] 开始打包（可能需要几分钟）"
    ):
        return 1

    # 4. 复制说明文件和配置文件到 dist 目录
    print(f"\n{'='*60}")
    print(" [4/4] 复制用户说明文件和配置文件")
    print(f"{'='*60}")

    readme_src = code_dir / "用户使用说明.txt"
    readme_dst = code_dir / "dist" / "用户使用说明.txt"

    if readme_src.exists():
        shutil.copy(readme_src, readme_dst)
        print(f"  ✓ 已复制用户说明文件")

    # 复制 .env 文件
    env_src = code_dir.parent / ".env"
    env_dst = code_dir / "dist" / ".env"

    if env_src.exists():
        shutil.copy(env_src, env_dst)
        print(f"  ✓ 已复制 .env 配置文件")
    else:
        print(f"  ⚠ 未找到 .env 文件，跳过复制")

    # 创建 data 目录占位符
    data_dir = code_dir / "dist" / "data"
    data_dir.mkdir(exist_ok=True)
    print(f"  ✓ 已创建 data 目录")

    # 完成
    print(f"\n{'='*60}")
    print(" 打包完成！")
    print(f"{'='*60}")
    print(f"\n可执行文件: {code_dir / 'dist' / 'BOSS直聘管理工具.exe'}")
    print(f"\n使用说明:")
    print(f"  1. 将 dist 文件夹复制到任意位置")
    print(f"  2. 双击运行 BOSS直聘管理工具.exe")
    print(f"  3. 在浏览器中访问 http://localhost:5001")
    print(f"\n{'='*60}\n")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n[中断] 用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 打包失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
