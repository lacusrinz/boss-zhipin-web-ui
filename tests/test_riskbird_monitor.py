#!/usr/bin/env python3
"""Tests for RiskBird monitor"""
import sys
from pathlib import Path
import tempfile
import os
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "code"))

from riskbird_monitor import RiskBirdMonitor
from database import BOSSDatabase

def test_build_search_params():
    """Test building search params from config"""
    monitor = RiskBirdMonitor()

    config = {
        'region_codes': ['110000', '310000', '440000'],
        'interval_minutes': 5,
        'reg_cap': '5000￥'
    }

    params = monitor.build_search_params_from_config(config)

    assert 'aoData' in params, "Params should contain aoData"
    assert params['queryType'] == 'senior', "Query type should be senior"
    assert params['queryLimitType'] == 2, "Query limit type should be 2"

def test_parse_company_response():
    """Test parsing RiskBird API response"""
    monitor = RiskBirdMonitor()

    # Mock response
    mock_response = {
        'data': [
            {
                'id': '123',
                'name': 'Test Company',
                'creditNo': '91110000123456789X',
                'esDate': '2026-03-17',
                'regCap': '5000万人民币',
                'regOrg': '北京市市场监督管理局',
                'frname': '张三',
                'contact': '13800138000',
                'dom': '北京市朝阳区'
            }
        ]
    }

    companies = monitor.parse_companies_from_response(mock_response)

    assert len(companies) == 1, "Should parse 1 company"
    assert companies[0]['company_name'] == 'Test Company'
    assert companies[0]['credit_code'] == '91110000123456789X'

def test_run_monitoring_task_integration():
    """Test full monitoring task flow"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = BOSSDatabase(db_path)
        db.connect()
        db.init_monitoring_tables()

        # Insert test API credentials
        db.insert_riskbird_config('token', 'test_token_123')
        db.insert_riskbird_config('app_uuid', 'test_uuid_456')

        # Create monitoring config
        config_id = db.insert_monitoring_config(
            config_name="Test Config",
            region_codes='["110000"]',
            interval_minutes=5
        )

        monitor = RiskBirdMonitor(db)

        # Mock API call
        with patch.object(monitor, 'call_riskbird_api') as mock_api:
            mock_api.return_value = {
                'data': [
                    {
                        'id': '1',
                        'name': 'New Company',
                        'creditNo': '91110000999999999X',
                        'esDate': '2026-03-17',
                        'regCap': '1000万人民币',
                        'regOrg': '北京市市场监督管理局',
                        'frname': '李四',
                        'contact': '13900139000',
                        'dom': '北京市海淀区'
                    }
                ]
            }

            result = monitor.run_monitoring_task(config_id)

            assert result['success'] == True
            assert result['companies_added'] == 1

            # Verify company was saved
            companies = db.get_monitored_companies(config_id=config_id)
            assert len(companies) == 1
            assert companies[0]['company_name'] == 'New Company'
