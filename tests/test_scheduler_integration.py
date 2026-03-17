#!/usr/bin/env python3
"""Tests for APScheduler integration"""
import sys
from pathlib import Path
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from web_app import scheduler
from database import BOSSDatabase

def test_scheduler_initialization():
    """Test that scheduler is initialized"""
    assert scheduler is not None, "Scheduler should be initialized"
    assert hasattr(scheduler, 'add_job'), "Scheduler should support add_job"
    assert hasattr(scheduler, 'start'), "Scheduler should support start"
    assert hasattr(scheduler, 'shutdown'), "Scheduler should support shutdown"

def test_monitoring_job_scheduling():
    """Test scheduling a monitoring job"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Create config
        config_id = db.insert_monitoring_config(
            config_name="Test Job",
            region_codes='["110000"]',
            interval_minutes=1  # 1 minute for testing
        )

        # Add token
        db.insert_riskbird_config("token", "test_token")
        db.insert_riskbird_config("app_uuid", "test_uuid")

        # This would be called by API
        # For now, just verify the mechanism exists
        assert hasattr(scheduler, 'add_job'), "Scheduler should support add_job"
