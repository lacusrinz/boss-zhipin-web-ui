#!/usr/bin/env python3
"""
更新历史数据的平台字段
将所有现有职位的 platform 设置为 BOSS直聘
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from database import BOSSDatabase


def update_platform():
    """更新所有历史数据的平台字段"""
    db = BOSSDatabase()

    if not db.connect():
        print("❌ 数据库连接失败")
        return False

    print("=" * 60)
    print(" 更新历史数据平台字段")
    print("=" * 60)

    # 检查是否有 platform 列
    db.cursor.execute("PRAGMA table_info(jobs)")
    columns = [col[1] for col in db.cursor.fetchall()]

    if 'platform' not in columns:
        print("⚠️  数据库中没有 platform 列，正在添加...")
        if not db.add_platform_column():
            print("❌ 添加 platform 列失败")
            return False
        print("✅ platform 列添加成功")

    # 查看当前状态
    db.cursor.execute("SELECT COUNT(*) FROM jobs WHERE platform IS NULL OR platform = ''")
    null_count = db.cursor.fetchone()[0]

    db.cursor.execute("SELECT COUNT(*) FROM jobs")
    total_count = db.cursor.fetchone()[0]

    print(f"\n当前状态:")
    print(f"  总职位数: {total_count}")
    print(f"  未设置平台的: {null_count}")

    if null_count == 0:
        print("\n✅ 所有职位已设置平台，无需更新")
        db.close()
        return True

    # 更新数据
    print(f"\n正在更新 {null_count} 条记录...")

    db.cursor.execute("""
        UPDATE jobs
        SET platform = 'boss_zhipin'
        WHERE platform IS NULL OR platform = ''
    """)

    updated_count = db.cursor.rowcount
    db.conn.commit()

    print(f"✅ 成功更新 {updated_count} 条记录")
    print("\n" + "=" * 60)
    print(" 更新完成！")
    print("=" * 60)

    # 验证结果
    db.cursor.execute("SELECT platform, COUNT(*) as count FROM jobs GROUP BY platform")
    print("\n平台统计:")
    for row in db.cursor.fetchall():
        platform, count = row
        if platform:
            print(f"  {platform}: {count} 个职位")
        else:
            print(f"  (未设置): {count} 个职位")

    db.close()
    return True


if __name__ == '__main__':
    try:
        success = update_platform()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
