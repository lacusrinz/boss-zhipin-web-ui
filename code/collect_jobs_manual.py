#!/usr/bin/env python3
"""
半自动化收集脚本
手动操作浏览器收集，然后从文件提取数据
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 添加 code 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from extract_jobs_v6 import main as extract_main


def main():
    print("=" * 60)
    print("BOSS 直聘半自动化收集系统")
    print("=" * 60)

    print("\n请按照以下步骤操作：")
    print("\n1. 在普通浏览器中打开 BOSS 直聘")
    print("2. 登录账号")
    print("3. 搜索以下行业，并将每个搜索结果页面保存为 HTML：")

    industries = ["智能制造", "机器人", "医疗器械", "新能源", "芯片", "光伏"]

    print("\n行业列表：")
    for i, industry in enumerate(industries, 1):
        print(f"  {i}. {industry}")

    print("\n4. 保存 HTML 文件到 data/collected/ 目录")
    print("   文件命名格式: {行业名称}.html")
    print("   例如: 智能制造.html, 机器人.html")

    # 确保 collected 目录存在
    base_dir = Path(__file__).parent.parent
    collected_dir = base_dir / "data" / "collected"
    collected_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n目标目录: {collected_dir}")

    print("\n" + "=" * 60)
    print("保存完成后，按 Enter 键继续提取数据...")
    print("=" * 60)
    input()

    # 运行提取脚本
    print("\n开始提取数据...")
    extract_main()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断程序")
