#!/usr/bin/env python3
"""
飞书推送支持 - 数据库迁移脚本

为 monitoring_configs 表添加飞书推送相关字段
创建 feishu_push_logs 表记录推送历史
"""
import sys
import logging
from pathlib import Path

# 添加 code 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import BOSSDatabase

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def migrate_feishu_push_support():
    """
    添加飞书推送支持到现有数据库
    """
    # 获取数据库路径
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent.parent

    db_path = base_dir / "data" / "boss_jobs.db"

    if not db_path.exists():
        logging.error(f"数据库文件不存在: {db_path}")
        return False

    db = BOSSDatabase(str(db_path))

    if not db.connect():
        logging.error("数据库连接失败")
        return False

    try:
        # 1. 检查并添加 feishu_enabled 列
        logging.info("检查 monitoring_configs 表结构...")
        db.cursor.execute("PRAGMA table_info(monitoring_configs)")
        columns = [col[1] for col in db.cursor.fetchall()]

        if 'feishu_enabled' not in columns:
            logging.info("添加 feishu_enabled 列...")
            db.cursor.execute("""
                ALTER TABLE monitoring_configs ADD COLUMN feishu_enabled BOOLEAN DEFAULT 0
            """)
            logging.info("✅ feishu_enabled 列添加成功")
        else:
            logging.info("✅ feishu_enabled 列已存在")

        if 'feishu_target_type' not in columns:
            logging.info("添加 feishu_target_type 列...")
            db.cursor.execute("""
                ALTER TABLE monitoring_configs ADD COLUMN feishu_target_type TEXT
            """)
            logging.info("✅ feishu_target_type 列添加成功")
        else:
            logging.info("✅ feishu_target_type 列已存在")

        if 'feishu_target_id' not in columns:
            logging.info("添加 feishu_target_id 列...")
            db.cursor.execute("""
                ALTER TABLE monitoring_configs ADD COLUMN feishu_target_id TEXT
            """)
            logging.info("✅ feishu_target_id 列添加成功")
        else:
            logging.info("✅ feishu_target_id 列已存在")

        # 2. 创建 feishu_push_logs 表
        logging.info("创建 feishu_push_logs 表...")
        db.cursor.execute("""
            CREATE TABLE IF NOT EXISTS feishu_push_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_id INTEGER NOT NULL,
                run_id INTEGER,
                company_count INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (config_id) REFERENCES monitoring_configs (id)
            )
        """)

        # 创建索引
        db.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feishu_push_logs_config_id
            ON feishu_push_logs(config_id)
        """)

        db.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feishu_push_logs_created_at
            ON feishu_push_logs(created_at)
        """)

        logging.info("✅ feishu_push_logs 表创建成功")

        # 提交更改
        db.conn.commit()

        logging.info("=" * 50)
        logging.info("✅ 飞书推送支持迁移完成！")
        logging.info("=" * 50)
        return True

    except Exception as e:
        logging.error(f"迁移失败: {e}")
        db.conn.rollback()
        return False
    finally:
        db.close()


if __name__ == '__main__':
    success = migrate_feishu_push_support()
    sys.exit(0 if success else 1)
