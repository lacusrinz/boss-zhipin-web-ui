"""
数据库飞书功能测试
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from database import BOSSDatabase
import pytest
import tempfile
import os


@pytest.fixture
def db():
    """创建测试数据库连接"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_tables()
        db.init_monitoring_tables()

        # 手动执行飞书迁移（添加列和创建表）
        # 1. 添加飞书相关列到 monitoring_configs 表
        db.cursor.execute("PRAGMA table_info(monitoring_configs)")
        columns = [col[1] for col in db.cursor.fetchall()]

        if 'feishu_enabled' not in columns:
            db.cursor.execute("""
                ALTER TABLE monitoring_configs ADD COLUMN feishu_enabled BOOLEAN DEFAULT 0
            """)
        if 'feishu_target_type' not in columns:
            db.cursor.execute("""
                ALTER TABLE monitoring_configs ADD COLUMN feishu_target_type TEXT
            """)
        if 'feishu_target_id' not in columns:
            db.cursor.execute("""
                ALTER TABLE monitoring_configs ADD COLUMN feishu_target_id TEXT
            """)

        # 2. 创建 feishu_push_logs 表
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

        db.conn.commit()

        yield db

        db.close()


class TestFeishuConfig:
    """测试飞书配置功能"""

    def test_update_monitoring_config_feishu(self, db):
        """测试更新监测配置的飞书设置"""
        # 先创建一个监测配置
        config_id = db.insert_monitoring_config(
            config_name="测试配置",
            region_codes='["310000"]',
            interval_minutes=5
        )

        # 更新飞书设置
        success = db.update_monitoring_config_feishu(
            config_id=config_id,
            feishu_enabled=True,
            feishu_target_type='group',
            feishu_target_id='oc_test123'
        )

        assert success is True

        # 验证更新
        config = db.get_monitoring_config(config_id)
        assert config['feishu_enabled'] == 1
        assert config['feishu_target_type'] == 'group'
        assert config['feishu_target_id'] == 'oc_test123'

    def test_insert_feishu_push_log(self, db):
        """测试插入飞书推送日志"""
        # 创建监测配置
        config_id = db.insert_monitoring_config(
            config_name="测试配置",
            region_codes='["310000"]',
            interval_minutes=5
        )

        # 插入成功日志
        log_id = db.insert_feishu_push_log(
            config_id=config_id,
            company_count=3,
            success=True
        )

        assert log_id is not None

        # 插入失败日志
        log_id = db.insert_feishu_push_log(
            config_id=config_id,
            company_count=0,
            success=False,
            error_message="Invalid target_id"
        )

        assert log_id is not None
