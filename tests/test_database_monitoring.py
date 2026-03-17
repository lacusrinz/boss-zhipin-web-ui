#!/usr/bin/env python3
"""Tests for monitoring database tables"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from database import BOSSDatabase
import tempfile
import os

def test_init_monitoring_tables():
    """Test that monitoring tables are created"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()

        # Initialize monitoring tables
        result = db.init_monitoring_tables()

        assert result == True, "Table initialization should succeed"

        # Verify tables exist
        cursor = db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='riskbird_config'")
        assert cursor.fetchone() is not None, "riskbird_config table should exist"

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monitoring_configs'")
        assert cursor.fetchone() is not None, "monitoring_configs table should exist"

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monitored_companies'")
        assert cursor.fetchone() is not None, "monitored_companies table should exist"

        db.close()

def test_riskbird_config_crud():
    """Test riskbird_config CRUD operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Insert config
        db.insert_riskbird_config("token", "test_token_value")
        db.insert_riskbird_config("app_uuid", "test_uuid_value")

        # Read config
        token = db.get_riskbird_config("token")
        assert token == "test_token_value", f"Expected 'test_token_value', got {token}"

        # Update config
        db.update_riskbird_config("token", "new_token_value")
        token = db.get_riskbird_config("token")
        assert token == "new_token_value", f"Expected 'new_token_value', got {token}"

        db.close()

def test_monitoring_config_crud():
    """Test monitoring_configs CRUD operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Insert config
        config_id = db.insert_monitoring_config(
            config_name="Test Config",
            region_codes='["110000", "310000"]',
            interval_minutes=5
        )

        assert config_id is not None, "Config ID should not be None"

        # Read config
        configs = db.get_all_monitoring_configs()
        assert len(configs) == 1, f"Expected 1 config, got {len(configs)}"
        assert configs[0]['config_name'] == "Test Config"

        db.close()

def test_monitored_company_insert():
    """Test monitored_companies insert"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Insert config first
        config_id = db.insert_monitoring_config(
            config_name="Test Config",
            region_codes='["110000"]',
            interval_minutes=5
        )

        # Insert company
        company_id = db.insert_monitored_company({
            'config_id': config_id,
            'company_name': 'Test Company',
            'credit_code': '91110000123456789X',
            'reg_date': '2026-03-17',
            'region_code': '110000',
            'region_name': '北京市'
        })

        assert company_id is not None, "Company ID should not be None"

        # Check for duplicate
        company_id2 = db.insert_monitored_company({
            'config_id': config_id,
            'company_name': 'Test Company',
            'credit_code': '91110000123456789X',  # Same credit code
            'reg_date': '2026-03-17',
            'region_code': '110000',
            'region_name': '北京市'
        })

        assert company_id2 is None, "Duplicate credit_code should be rejected"

        db.close()
