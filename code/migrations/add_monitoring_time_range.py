#!/usr/bin/env python3
"""
Database migration script for adding monitoring time range columns

This script adds monitoring_start_time and monitoring_end_time columns
to the monitoring_configs table.
"""

import sys
from pathlib import Path

# Add parent directory to path to import database module
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import BOSSDatabase


def migrate():
    """
    Run the database migration to add monitoring time range columns
    """
    print("=" * 60)
    print("Database Migration: Add Monitoring Time Range Columns")
    print("=" * 60)

    # Detect database path (handles both dev and exe environments)
    if getattr(sys, 'frozen', False):
        # Frozen (exe) environment
        base_dir = Path(sys.executable).parent
    else:
        # Development environment
        base_dir = Path(__file__).parent.parent.parent

    db_path = base_dir / "data" / "boss_jobs.db"

    print(f"\n📁 Database path: {db_path}")

    # Check if database exists
    if not db_path.exists():
        print(f"❌ Database file not found at: {db_path}")
        return False

    # Connect to database
    print("\n🔌 Connecting to database...")
    db = BOSSDatabase(str(db_path))

    if not db.connect():
        print("❌ Failed to connect to database")
        return False

    print("✅ Connected to database")

    try:
        # Run migration
        print("\n🔄 Running migration...")
        success = db.add_monitoring_time_columns()

        if not success:
            print("❌ Migration failed")
            return False

        print("✅ Migration completed successfully")

        # Verify migration by checking sample configs
        print("\n🔍 Verifying migration...")
        configs = db.get_all_monitoring_configs()

        if not configs:
            print("ℹ️  No monitoring configs found in database")
        else:
            print(f"✅ Found {len(configs)} monitoring config(s)")

            # Show sample configs (max 3)
            sample_count = min(3, len(configs))
            print(f"\n📋 Sample config(s) (showing {sample_count}):")
            print("-" * 60)

            for i, config in enumerate(configs[:sample_count], 1):
                print(f"\nConfig #{i}:")
                print(f"  ID: {config['id']}")
                print(f"  Name: {config['config_name']}")
                print(f"  Start Time: {config.get('monitoring_start_time', 'N/A')}")
                print(f"  End Time: {config.get('monitoring_end_time', 'N/A')}")
                print(f"  Active: {config['is_active']}")
                print(f"  Interval: {config['interval_minutes']} minutes")

            if len(configs) > sample_count:
                print(f"\n... and {len(configs) - sample_count} more config(s)")

        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Close database connection
        db.close()
        print("\n🔒 Database connection closed")


if __name__ == '__main__':
    try:
        success = migrate()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
