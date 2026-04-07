#!/usr/bin/env python3
"""Tests for riskbird_token_sets table and CRUD"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from database import BOSSDatabase
import tempfile
import os


def test_token_sets_table_created():
    """Test riskbird_token_sets table is created"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='riskbird_token_sets'")
        assert cursor.fetchone() is not None, "riskbird_token_sets table should exist"
        db.close()


def test_token_sets_crud():
    """Test token sets CRUD operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Insert
        token_set_id = db.insert_token_set("主账号", "encrypted_token_1", "uuid-1")
        assert token_set_id is not None

        # Get single
        ts = db.get_token_set(token_set_id)
        assert ts['name'] == "主账号"
        assert ts['token'] == "encrypted_token_1"
        assert ts['app_uuid'] == "uuid-1"

        # Get all
        db.insert_token_set("备用账号", "encrypted_token_2", "uuid-2")
        all_ts = db.get_all_token_sets()
        assert len(all_ts) == 2

        # Update
        db.update_token_set(token_set_id, name="主账号-更新", token="new_encrypted", app_uuid="new-uuid")
        updated = db.get_token_set(token_set_id)
        assert updated['name'] == "主账号-更新"
        assert updated['token'] == "new_encrypted"

        # Delete
        db.delete_token_set(token_set_id)
        assert db.get_token_set(token_set_id) is None
        db.close()


def test_token_set_name_unique():
    """Test that duplicate names are rejected"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        db.insert_token_set("主账号", "token1", "uuid1")
        try:
            db.insert_token_set("主账号", "token2", "uuid2")
            assert False, "Should have raised an error for duplicate name"
        except Exception:
            pass
        db.close()


def test_migration_adds_token_set_id():
    """Test that migration adds token_set_id to monitoring_configs"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Create a monitoring config before migration
        config_id = db.insert_monitoring_config(
            config_name="Test",
            region_codes='["110000"]',
            interval_minutes=5
        )

        # Run migration
        db._migrate_monitoring_tables()

        # Verify token_set_id column exists
        cursor = db.conn.cursor()
        cursor.execute("PRAGMA table_info(monitoring_configs)")
        columns = [row[1] for row in cursor.fetchall()]
        assert 'token_set_id' in columns, "token_set_id column should exist after migration"

        # Verify existing config still works (backward compatible)
        config = db.get_monitoring_config(config_id)
        assert config['token_set_id'] is None

        # Verify ALLOWED_COLUMNS includes token_set_id
        # First create a token set so FK constraint is satisfied
        ts_id = db.insert_token_set("测试套餐", "token_val", "uuid_val")
        db.update_monitoring_config(config_id, token_set_id=ts_id)
        config = db.get_monitoring_config(config_id)
        assert config['token_set_id'] == ts_id

        # Verify ON DELETE SET NULL: deleting token set should set token_set_id to NULL
        db.delete_token_set(ts_id)
        config = db.get_monitoring_config(config_id)
        assert config['token_set_id'] is None
        db.close()
