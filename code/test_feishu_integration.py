#!/usr/bin/env python3
"""
Feishu Integration Test Script

Tests the Feishu push notification feature integration
"""
import os
import sys
from pathlib import Path

# Add code directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from feishu_service import FeishuService
from database import BOSSDatabase

# Load environment variables
load_dotenv()


def test_environment_variables():
    """Test 1: Verify environment variables are loaded"""
    print("=" * 50)
    print("Test 1: Environment Variables")
    print("=" * 50)

    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')

    print(f"FEISHU_APP_ID: {app_id}")
    print(f"FEISHU_APP_SECRET: {'*' * len(app_secret) if app_secret else 'NOT SET'}")

    if app_id and app_secret:
        print("✅ Environment variables loaded successfully")
        return True
    else:
        print("❌ Environment variables not loaded")
        return False


def test_feishu_service_init():
    """Test 2: Verify FeishuService can be initialized"""
    print("\n" + "=" * 50)
    print("Test 2: FeishuService Initialization")
    print("=" * 50)

    try:
        app_id = os.getenv('FEISHU_APP_ID')
        app_secret = os.getenv('FEISHU_APP_SECRET')

        feishu = FeishuService(app_id, app_secret)
        print("✅ FeishuService initialized successfully")
        return True
    except Exception as e:
        print(f"❌ FeishuService initialization failed: {e}")
        return False


def test_token_retrieval():
    """Test 3: Verify token can be retrieved"""
    print("\n" + "=" * 50)
    print("Test 3: Token Retrieval")
    print("=" * 50)

    try:
        app_id = os.getenv('FEISHU_APP_ID')
        app_secret = os.getenv('FEISHU_APP_SECRET')

        feishu = FeishuService(app_id, app_secret)
        token = feishu.get_tenant_access_token()

        print(f"Token (first 20 chars): {token[:20]}...")
        print("✅ Token retrieved successfully")
        return True
    except Exception as e:
        print(f"❌ Token retrieval failed: {e}")
        return False


def test_message_formatting():
    """Test 4: Verify message formatting works"""
    print("\n" + "=" * 50)
    print("Test 4: Message Formatting")
    print("=" * 50)

    try:
        app_id = os.getenv('FEISHU_APP_ID')
        app_secret = os.getenv('FEISHU_APP_SECRET')

        feishu = FeishuService(app_id, app_secret)

        companies = [
            {
                'company_name': '测试企业A',
                'reg_cap': '1000万',
                'monitoring_time': '2026-03-18 14:30:00'
            },
            {
                'company_name': '测试企业B',
                'reg_cap': '500万',
                'monitoring_time': '2026-03-18 14:30:00'
            }
        ]

        message = feishu.format_monitoring_notification(companies, '测试配置')

        print("Formatted message:")
        print("-" * 50)
        print(message)
        print("-" * 50)
        print("✅ Message formatting successful")
        return True
    except Exception as e:
        print(f"❌ Message formatting failed: {e}")
        return False


def test_database_schema():
    """Test 5: Verify database schema is correct"""
    print("\n" + "=" * 50)
    print("Test 5: Database Schema")
    print("=" * 50)

    try:
        # Get database path
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent.parent

        db_path = base_dir / "data" / "boss_jobs.db"
        db = BOSSDatabase(str(db_path))

        if not db.connect():
            print("❌ Database connection failed")
            return False

        # Check monitoring_configs table for Feishu columns
        db.cursor.execute("PRAGMA table_info(monitoring_configs)")
        columns = [col[1] for col in db.cursor.fetchall()]

        required_columns = ['feishu_enabled', 'feishu_target_type', 'feishu_target_id']
        missing_columns = [col for col in required_columns if col not in columns]

        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            db.close()
            return False

        print("✅ monitoring_configs table has Feishu columns")

        # Check feishu_push_logs table exists
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feishu_push_logs'")
        if not db.cursor.fetchone():
            print("❌ feishu_push_logs table does not exist")
            db.close()
            return False

        print("✅ feishu_push_logs table exists")

        db.close()
        return True
    except Exception as e:
        print(f"❌ Database schema check failed: {e}")
        return False


def test_database_methods():
    """Test 6: Verify database methods work"""
    print("\n" + "=" * 50)
    print("Test 6: Database Methods")
    print("=" * 50)

    try:
        # Get database path
        if getattr(sys, 'frozen', False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent.parent

        db_path = base_dir / "data" / "boss_jobs.db"
        db = BOSSDatabase(str(db_path))

        if not db.connect():
            print("❌ Database connection failed")
            return False

        # Test update_monitoring_config_feishu
        test_config_id = 19  # Use existing config

        success = db.update_monitoring_config_feishu(
            config_id=test_config_id,
            feishu_enabled=True,
            feishu_target_type='group',
            feishu_target_id='oc_test_12345'
        )

        if not success:
            print("❌ update_monitoring_config_feishu failed")
            db.close()
            return False

        print("✅ update_monitoring_config_feishu works")

        # Verify the update
        config = db.get_monitoring_config(test_config_id)
        if not config:
            print("❌ get_monitoring_config failed")
            db.close()
            return False

        print(f"✅ Config retrieved: feishu_enabled={config.get('feishu_enabled')}, "
              f"feishu_target_type={config.get('feishu_target_type')}")

        # Reset to disabled
        db.update_monitoring_config_feishu(
            config_id=test_config_id,
            feishu_enabled=False,
            feishu_target_type=None,
            feishu_target_id=None
        )

        # Test insert_feishu_push_log
        log_id = db.insert_feishu_push_log(
            config_id=test_config_id,
            company_count=5,
            success=True
        )

        if not log_id:
            print("❌ insert_feishu_push_log failed")
            db.close()
            return False

        print(f"✅ insert_feishu_push_log works (log_id: {log_id})")

        db.close()
        return True
    except Exception as e:
        print(f"❌ Database methods test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("Feishu Integration Test Suite")
    print("=" * 50)

    tests = [
        test_environment_variables,
        test_feishu_service_init,
        test_token_retrieval,
        test_message_formatting,
        test_database_schema,
        test_database_methods
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Test failed with exception: {e}")
            results.append(False)

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
