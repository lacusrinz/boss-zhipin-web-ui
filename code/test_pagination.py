#!/usr/bin/env python3
"""Test pagination fix for RiskBird monitoring"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import BOSSDatabase
from riskbird_monitor import RiskBirdMonitor
from token_service import TokenService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_pagination():
    """Test pagination by running config 14"""
    print("=" * 80)
    print("Testing Pagination Fix")
    print("=" * 80)
    print()

    # Connect to database
    db_path = Path(__file__).parent.parent / "data" / "boss_jobs.db"
    db = BOSSDatabase(str(db_path))

    if not db.connect():
        print("❌ Cannot connect to database")
        return

    # Get config 14 (the one that had the issue)
    config = db.get_monitoring_config(14)
    if not config:
        print("❌ Config 14 not found")
        db.close()
        return

    print(f"Testing with config: {config['config_name']}")
    print(f"Region codes: {config['region_codes']}")
    print()

    # Create monitor and run task
    monitor = RiskBirdMonitor(db)
    result = monitor.run_monitoring_task(14)

    print()
    print("=" * 80)
    print("Test Results")
    print("=" * 80)
    print(f"✅ Success: {result['success']}")
    print(f"📊 Companies added: {result['companies_added']}")
    print(f"📊 Companies skipped: {result['companies_skipped']}")
    if result['error']:
        print(f"❌ Error: {result['error']}")

    db.close()

if __name__ == "__main__":
    test_pagination()
