#!/usr/bin/env python3
"""
Integration test script for enterprise monitoring module
Tests all API endpoints and functionality
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:5001"

def print_test_header(test_name):
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print('='*60)

def print_result(test_name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"  Details: {details}")

def test_1_token_configuration():
    """Test 1: Token Configuration"""
    print_test_header("Token Configuration")

    test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"
    test_uuid = "test-app-uuid-12345"

    # Test 1.1: Save token configuration
    try:
        response = requests.post(f"{BASE_URL}/api/monitoring/token", json={
            "token": test_token,
            "app_uuid": test_uuid
        })

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print_result("1.1 Save token configuration", True, "Token saved successfully")
            else:
                print_result("1.1 Save token configuration", False, result.get('message', 'Unknown error'))
        else:
            print_result("1.1 Save token configuration", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("1.1 Save token configuration", False, str(e))

    # Test 1.2: Get token status
    time.sleep(1)
    try:
        response = requests.get(f"{BASE_URL}/api/monitoring/token")
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('configs'):
                print_result("1.2 Get token status", True, f"Token configured, app_uuid: {result.get('configs', {}).get('app_uuid')}")
            else:
                print_result("1.2 Get token status", False, "Token not configured")
        else:
            print_result("1.2 Get token status", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("1.2 Get token status", False, str(e))

def test_2_monitoring_configuration():
    """Test 2: Monitoring Configuration"""
    print_test_header("Monitoring Configuration")

    config_data = {
        "config_name": "测试配置",
        "region_codes": ["beijing", "shanghai"],
        "interval_minutes": 1,
        "reg_cap": ""
    }

    # Test 2.1: Create monitoring configuration
    try:
        response = requests.post(f"{BASE_URL}/api/monitoring/configs", json=config_data)

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print_result("2.1 Create monitoring configuration", True, f"Config ID: {result.get('config_id')}")
            else:
                print_result("2.1 Create monitoring configuration", False, result.get('message', 'Unknown error'))
        else:
            print_result("2.1 Create monitoring configuration", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("2.1 Create monitoring configuration", False, str(e))

    # Test 2.2: Get monitoring configurations
    time.sleep(1)
    try:
        response = requests.get(f"{BASE_URL}/api/monitoring/configs")
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and len(result.get('configs', [])) > 0:
                config = result['configs'][0]
                print_result("2.2 Get monitoring configurations", True, f"Found {len(result['configs'])} config(s)")
                print(f"  Config name: {config.get('config_name')}")
                print(f"  Active: {config.get('is_active')}")
            else:
                print_result("2.2 Get monitoring configurations", False, "No configs found")
        else:
            print_result("2.2 Get monitoring configurations", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("2.2 Get monitoring configurations", False, str(e))

def test_3_job_control():
    """Test 3: Job Control"""
    print_test_header("Job Control")

    # Test 3.1: Get jobs list
    try:
        response = requests.get(f"{BASE_URL}/api/monitoring/jobs")
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and len(result.get('jobs', [])) > 0:
                print_result("3.1 Get jobs list", True, f"Found {len(result['jobs'])} job(s)")
                job = result['jobs'][0]
                print(f"  Job ID: {job.get('config_id')}")
                print(f"  Job name: {job.get('name')}")
                print(f"  Status: {'Paused' if job.get('paused') else 'Active'}")
                print(f"  Next run: {job.get('next_run_time', 'N/A')}")
            else:
                print_result("3.1 Get jobs list", False, "No jobs found")
        else:
            print_result("3.1 Get jobs list", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("3.1 Get jobs list", False, str(e))

    # Test 3.2: Execute job immediately
    try:
        response = requests.get(f"{BASE_URL}/api/monitoring/jobs")
        result = response.json()
        if result.get('jobs'):
            config_id = result['jobs'][0]['config_id']

            response = requests.post(f"{BASE_URL}/api/monitoring/jobs/{config_id}/run-now")

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print_result("3.2 Execute job immediately", True, result.get('message'))
                else:
                    print_result("3.2 Execute job immediately", False, result.get('message', result.get('error', 'Unknown error')))
            else:
                print_result("3.2 Execute job immediately", False, f"HTTP {response.status_code}")
        else:
            print_result("3.2 Execute job immediately", False, "No job to execute")
    except Exception as e:
        print_result("3.2 Execute job immediately", False, str(e))

    # Wait for job to complete
    print("\n⏳ Waiting 5 seconds for job execution...")
    time.sleep(5)

def test_4_statistics_display():
    """Test 4: Statistics Display"""
    print_test_header("Statistics Display")

    try:
        response = requests.get(f"{BASE_URL}/api/monitoring/stats")
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                stats = result.get('statistics', {})
                print_result("4.1 Get statistics", True)
                print(f"  Total monitored companies: {stats.get('total_companies', 0)}")
                print(f"  Today's new companies: {stats.get('today_new', 0)}")
                print(f"  Active configurations: {stats.get('active_configs', 0)}")
                print(f"  Pending processing: {stats.get('pending_count', 0)}")
                print(f"  Total companies in DB: {stats.get('total_in_db', 0)}")
            else:
                print_result("4.1 Get statistics", False, result.get('message', 'Unknown error'))
        else:
            print_result("4.1 Get statistics", False, f"HTTP {response.status_code}")
    except Exception as e:
        print_result("4.1 Get statistics", False, str(e))

def test_5_jobs_toggle():
    """Test 5: Jobs Toggle"""
    print_test_header("Jobs Toggle")

    # Get active job
    try:
        response = requests.get(f"{BASE_URL}/api/monitoring/jobs")
        result = response.json()

        if not result.get('jobs'):
            print_result("5.1 Toggle job status", False, "No jobs found")
            return

        config_id = result['jobs'][0]['config_id']
        is_paused = result['jobs'][0].get('paused', False)

        # Test 5.1: Toggle job (pause if running, resume if paused)
        response = requests.post(f"{BASE_URL}/api/monitoring/jobs/{config_id}/toggle")

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                new_paused = result.get('paused', not is_paused)
                action = "Paused" if new_paused else "Resumed"
                print_result(f"5.1 Toggle job status", True, f"{action} successfully")
            else:
                print_result("5.1 Toggle job status", False, result.get('error', 'Unknown error'))
        else:
            print_result("5.1 Toggle job status", False, f"HTTP {response.status_code}")

        time.sleep(1)

        # Test 5.2: Toggle back
        response = requests.post(f"{BASE_URL}/api/monitoring/jobs/{config_id}/toggle")

        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                new_paused = result.get('paused', is_paused)
                action = "Paused" if new_paused else "Resumed"
                print_result(f"5.2 Toggle job status back", True, f"{action} successfully")
            else:
                print_result("5.2 Toggle job status back", False, result.get('error', 'Unknown error'))
        else:
            print_result("5.2 Toggle job status back", False, f"HTTP {response.status_code}")

    except Exception as e:
        print_result("5.1 Toggle job status", False, str(e))

def test_6_database_verification():
    """Test 6: Database Verification"""
    print_test_header("Database Verification")

    import sqlite3

    try:
        conn = sqlite3.connect('data/boss_jobs.db')
        cursor = conn.cursor()

        # Check monitored companies
        cursor.execute("SELECT COUNT(*) FROM monitored_companies")
        companies_count = cursor.fetchone()[0]
        print_result("6.1 Monitored companies in database", True, f"Count: {companies_count}")

        # Check monitoring configs
        cursor.execute("SELECT config_name, interval_minutes, is_active FROM monitoring_configs")
        configs = cursor.fetchall()
        print_result("6.2 Monitoring configs in database", True, f"Count: {len(configs)}")
        for config in configs:
            print(f"  - {config[0]}: {config[1]}min, active={config[2]}")

        # Check token configs
        cursor.execute("SELECT config_key FROM riskbird_config")
        tokens = cursor.fetchall()
        print_result("6.3 Token configs in database", True, f"Count: {len(tokens)}")

        conn.close()
    except Exception as e:
        print_result("6.1 Database verification", False, str(e))

def test_7_monitoring_run():
    """Test 7: Verify Monitoring Run Results"""
    print_test_header("Monitoring Run Results")

    import sqlite3

    try:
        conn = sqlite3.connect('data/boss_jobs.db')
        cursor = conn.cursor()

        # Check recent companies
        cursor.execute("""
            SELECT company_name, region_name, business_scope, monitoring_time
            FROM monitored_companies
            ORDER BY monitoring_time DESC
            LIMIT 5
        """)
        companies = cursor.fetchall()

        if companies:
            print_result("7.1 Recent monitored companies", True, f"Found {len(companies)} companies")
            for idx, company in enumerate(companies, 1):
                scope_preview = company[2][:50] if company[2] else 'N/A'
                print(f"  {idx}. {company[0]} - {company[1]} - {scope_preview}... ({company[3]})")
        else:
            print_result("7.1 Recent monitored companies", False, "No companies found")

        # Check total companies in main table
        cursor.execute("SELECT COUNT(*) FROM companies")
        total_companies = cursor.fetchone()[0]
        print_result("7.2 Total companies in database", True, f"Count: {total_companies}")

        conn.close()
    except Exception as e:
        print_result("7.1 Monitoring run results", False, str(e))

def main():
    print("\n" + "="*60)
    print("ENTERPRISE MONITORING MODULE - INTEGRATION TEST")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Wait for server to be fully ready
    print("\n⏳ Waiting for server to be ready...")
    time.sleep(2)

    # Run all tests
    test_1_token_configuration()
    test_2_monitoring_configuration()
    test_3_job_control()
    test_4_statistics_display()
    test_5_jobs_toggle()
    test_6_database_verification()
    test_7_monitoring_run()

    print("\n" + "="*60)
    print("INTEGRATION TEST COMPLETED")
    print("="*60)
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
