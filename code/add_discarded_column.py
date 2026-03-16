#!/usr/bin/env python3
"""
添加企业废弃状态字段
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from database import BOSSDatabase


def add_discarded_column():
    """添加 is_discarded 列"""
    db = BOSSDatabase()

    if not db.connect():
        print("❌ 数据库连接失败")
        return False

    print("=" * 60)
    print(" 添加企业废弃状态字段")
    print("=" * 60)

    # 添加列
    if not db.add_discarded_column():
        print("❌ 添加 is_discarded 列失败")
        db.close()
        return False

    print("✅ is_discarded 列添加成功")
    print("\n" + "=" * 60)
    print(" 迁移完成！")
    print("=" * 60)

    # 验证
    db.cursor.execute("PRAGMA table_info(companies)")
    columns = [col[1] for col in db.cursor.fetchall()]
    print(f"\n当前 companies 表字段: {', '.join(columns)}")

    db.close()
    return True


if __name__ == '__main__':
    try:
        success = add_discarded_column()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
