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


class TestCrossDayCRUD:
    def test_insert_monitoring_config_with_cross_day_cutoff_time(self, db):
        config_id = db.insert_monitoring_config(
            config_name='test-cross-day',
            region_codes='[]',
            interval_minutes=5,
            cross_day_cutoff_time='06:00'
        )
        config = db.get_monitoring_config(config_id)
        assert config['cross_day_cutoff_time'] == '06:00'

    def test_get_all_monitoring_configs_includes_cross_day_cutoff_time(self, db):
        db.insert_monitoring_config(
            config_name='test1',
            region_codes='[]',
            interval_minutes=5,
            cross_day_cutoff_time='08:00'
        )
        configs = db.get_all_monitoring_configs()
        assert len(configs) >= 1
        # Find the one we just inserted (most recent)
        config = next(c for c in configs if c['config_name'] == 'test1')
        assert config['cross_day_cutoff_time'] == '08:00'

    def test_update_monitoring_config_cross_day_cutoff_time(self, db):
        config_id = db.insert_monitoring_config(
            config_name='test-update',
            region_codes='[]',
            interval_minutes=5
        )
        db.update_monitoring_config(config_id, cross_day_cutoff_time='07:30')
        config = db.get_monitoring_config(config_id)
        assert config['cross_day_cutoff_time'] == '07:30'

    def test_update_cross_day_cutoff_time_to_none(self, db):
        config_id = db.insert_monitoring_config(
            config_name='test-clear',
            region_codes='[]',
            interval_minutes=5,
            cross_day_cutoff_time='06:00'
        )
        db.update_monitoring_config(config_id, cross_day_cutoff_time=None)
        config = db.get_monitoring_config(config_id)
        assert config['cross_day_cutoff_time'] is None
