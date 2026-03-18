#!/usr/bin/env python3
"""
Test time range validation in create monitoring config API
"""

import sys
from pathlib import Path

# Add code directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


class TestAPITimeRangeValidation:
    """Test suite for API time range validation"""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        # Import here to avoid initialization issues
        from web_app import app
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def mock_db(self):
        """Mock database operations"""
        with patch('web_app.get_db') as mock_get_db:
            mock_db_instance = MagicMock()
            mock_db_instance.conn = MagicMock()
            mock_db_instance.cursor = MagicMock()
            mock_db_instance.insert_monitoring_config = MagicMock(return_value=1)
            mock_db_instance.close = MagicMock()
            mock_get_db.return_value = mock_db_instance
            yield mock_db_instance

    @pytest.fixture
    def mock_scheduler(self):
        """Mock scheduler operations"""
        with patch('web_app.add_monitoring_job') as mock_add_job:
            mock_add_job.return_value = True
            yield mock_add_job

    def test_create_config_with_time_range(self, client, mock_db, mock_scheduler):
        """Test creating config with custom time range"""
        response = client.post('/api/monitoring/configs', json={
            'config_name': 'Test Config with Time Range',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '08:00',
            'monitoring_end_time': '20:00'
        })

        data = response.get_json()
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {data}"
        assert data['success'] is True, "Should return success=True"
        assert data['config_id'] == 1, "Should return config_id"

        # Verify database was called with time parameters
        mock_db.insert_monitoring_config.assert_called_once()
        call_args = mock_db.insert_monitoring_config.call_args
        assert call_args.kwargs['monitoring_start_time'] == '08:00'
        assert call_args.kwargs['monitoring_end_time'] == '20:00'

    def test_create_config_invalid_time_format(self, client, mock_db, mock_scheduler):
        """Test that invalid time format is rejected"""
        response = client.post('/api/monitoring/configs', json={
            'config_name': 'Test Config Invalid Time',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '25:00',  # Invalid hour
            'monitoring_end_time': '18:00'
        })

        data = response.get_json()
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert data['success'] is False, "Should return success=False"
        assert '无效' in data['error'] or 'invalid' in data['error'].lower() or 'format' in data['error'].lower(), \
            f"Error message should mention invalid format: {data['error']}"

        # Verify database was NOT called
        mock_db.insert_monitoring_config.assert_not_called()

    def test_create_config_cross_day_rejected(self, client, mock_db, mock_scheduler):
        """Test that cross-day time ranges are rejected"""
        response = client.post('/api/monitoring/configs', json={
            'config_name': 'Test Config Cross Day',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '20:00',
            'monitoring_end_time': '08:00'  # Earlier than start time
        })

        data = response.get_json()
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert data['success'] is False, "Should return success=False"
        assert '跨天' in data['error'] or 'cross day' in data['error'].lower() or \
               'after' in data['error'].lower() or 'end' in data['error'].lower() or \
               '晚于' in data['error'], \
            f"Error message should mention cross-day rejection: {data['error']}"

        # Verify database was NOT called
        mock_db.insert_monitoring_config.assert_not_called()

    def test_create_config_default_time_range(self, client, mock_db, mock_scheduler):
        """Test that default values work when time range not provided"""
        response = client.post('/api/monitoring/configs', json={
            'config_name': 'Test Config Default Time',
            'region_codes': ['110000'],
            'interval_minutes': 10
            # No time range parameters
        })

        data = response.get_json()
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {data}"
        assert data['success'] is True, "Should return success=True"

        # Verify database was called with default time parameters
        mock_db.insert_monitoring_config.assert_called_once()
        call_args = mock_db.insert_monitoring_config.call_args
        assert call_args.kwargs['monitoring_start_time'] == '09:00', \
            f"Default start time should be 09:00, got {call_args.kwargs['monitoring_start_time']}"
        assert call_args.kwargs['monitoring_end_time'] == '18:00', \
            f"Default end time should be 18:00, got {call_args.kwargs['monitoring_end_time']}"

    def test_create_config_invalid_format_minutes(self, client, mock_db, mock_scheduler):
        """Test that invalid minutes format is rejected"""
        response = client.post('/api/monitoring/configs', json={
            'config_name': 'Test Config Invalid Minutes',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '09:60',  # Invalid minutes
            'monitoring_end_time': '18:00'
        })

        data = response.get_json()
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert data['success'] is False, "Should return success=False"
        assert '无效' in data['error'] or 'invalid' in data['error'].lower() or 'format' in data['error'].lower(), \
            f"Error message should mention invalid format: {data['error']}"

        # Verify database was NOT called
        mock_db.insert_monitoring_config.assert_not_called()

    def test_create_config_edge_case_boundaries(self, client, mock_db, mock_scheduler):
        """Test edge case time boundaries"""
        # Test midnight to midnight (should fail - cross day)
        response = client.post('/api/monitoring/configs', json={
            'config_name': 'Test Config Midnight',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '00:00',
            'monitoring_end_time': '00:00'
        })

        data = response.get_json()
        assert response.status_code == 400, "Midnight to midnight should be rejected (cross day)"

        # Test valid early hours
        response = client.post('/api/monitoring/configs', json={
            'config_name': 'Test Config Early Hours',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '00:00',
            'monitoring_end_time': '23:59'
        })

        data = response.get_json()
        assert response.status_code == 200, f"Early hours should be valid: {data}"
        assert data['success'] is True
