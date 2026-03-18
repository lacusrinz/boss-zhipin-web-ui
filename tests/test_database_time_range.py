#!/usr/bin/env python3
"""
Test time range columns in monitoring_configs table
"""

import pytest
import sqlite3
from pathlib import Path
import sys

# Add parent directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from database import BOSSDatabase


@pytest.fixture
def test_db(tmp_path):
    """Create a test database instance"""
    db_path = tmp_path / "test.db"
    db = BOSSDatabase(str(db_path))
    db.connect()
    db.init_monitoring_tables()
    yield db
    db.close()


def test_monitoring_configs_has_time_columns(test_db):
    """Test that monitoring_configs table has time range columns"""
    # Get table schema
    test_db.cursor.execute("PRAGMA table_info(monitoring_configs)")
    columns = [col[1] for col in test_db.cursor.fetchall()]

    # Verify time range columns exist
    assert 'monitoring_start_time' in columns, "monitoring_start_time column should exist"
    assert 'monitoring_end_time' in columns, "monitoring_end_time column should exist"


def test_insert_monitoring_config_with_time_range(test_db):
    """Test inserting monitoring config with custom time range"""
    config_id = test_db.insert_monitoring_config(
        config_name="Test Config",
        region_codes='{"codes": ["110000"]}',
        interval_minutes=10,
        reg_cap="1000万以上",
        monitoring_start_time="08:00",
        monitoring_end_time="20:00"
    )

    assert config_id is not None, "Config ID should be returned"

    # Verify the data was inserted correctly
    config = test_db.get_monitoring_config(config_id)
    assert config is not None, "Config should be retrieved"
    assert config['monitoring_start_time'] == "08:00", f"Start time should be 08:00, got {config.get('monitoring_start_time')}"
    assert config['monitoring_end_time'] == "20:00", f"End time should be 20:00, got {config.get('monitoring_end_time')}"


def test_insert_monitoring_config_default_time_range(test_db):
    """Test inserting monitoring config with default time range"""
    config_id = test_db.insert_monitoring_config(
        config_name="Default Time Config",
        region_codes='{"codes": ["310000"]}',
        interval_minutes=5
    )

    assert config_id is not None, "Config ID should be returned"

    # Verify default values
    config = test_db.get_monitoring_config(config_id)
    assert config is not None, "Config should be retrieved"
    assert config['monitoring_start_time'] == "09:00", f"Default start time should be 09:00, got {config.get('monitoring_start_time')}"
    assert config['monitoring_end_time'] == "18:00", f"Default end time should be 18:00, got {config.get('monitoring_end_time')}"


def test_get_monitoring_config_includes_time_fields(test_db):
    """Test that get_monitoring_config returns time range fields"""
    # Insert a config
    config_id = test_db.insert_monitoring_config(
        config_name="Time Range Test",
        region_codes='{"codes": ["440000"]}',
        monitoring_start_time="10:00",
        monitoring_end_time="22:00"
    )

    assert config_id is not None, "Config ID should be returned"

    # Get the config
    config = test_db.get_monitoring_config(config_id)

    # Verify all expected fields are present
    assert config is not None, "Config should be retrieved"
    expected_fields = ['id', 'config_name', 'region_codes', 'is_active',
                      'interval_minutes', 'reg_cap', 'created_at', 'updated_at',
                      'monitoring_start_time', 'monitoring_end_time']

    for field in expected_fields:
        assert field in config, f"Field '{field}' should be in config"

    # Verify values
    assert config['monitoring_start_time'] == "10:00"
    assert config['monitoring_end_time'] == "22:00"
