#!/usr/bin/env python3
"""Tests for cross-day monitoring cutoff time column"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

import pytest
from database import BOSSDatabase


@pytest.fixture
def db():
    database = BOSSDatabase(':memory:')
    database.connect()
    database.init_monitoring_tables()
    yield database
    database.close()


class TestCrossDayColumnMigration:
    def test_monitoring_configs_has_cross_day_cutoff_time_column(self, db):
        """cross_day_cutoff_time column exists after init_monitoring_tables"""
        db.cursor.execute("PRAGMA table_info(monitoring_configs)")
        columns = [row[1] for row in db.cursor.fetchall()]
        assert 'cross_day_cutoff_time' in columns

    def test_cross_day_cutoff_time_default_is_none(self, db):
        """Default value is NULL (disabled)"""
        config_id = db.insert_monitoring_config(
            config_name='test',
            region_codes='[]',
            interval_minutes=5
        )
        config = db.get_monitoring_config(config_id)
        assert config['cross_day_cutoff_time'] is None
