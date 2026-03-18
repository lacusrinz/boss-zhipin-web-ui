#!/usr/bin/env python3
"""
Test fixes for update_monitoring_config endpoint:
- C1: Database connection leak (db.close() on early returns)
- C2: Empty string handling (convert "" to None)
- I1: Consistent field stripping
"""

import sys
from pathlib import Path

# Add code directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

import pytest
from unittest.mock import patch, MagicMock, call
from flask import Flask


class TestUpdateMonitoringFixes:
    """Test suite for update_monitoring_config fixes"""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
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
            mock_db_instance.update_monitoring_config = MagicMock(return_value=True)
            mock_db_instance.close = MagicMock()
            mock_get_db.return_value = mock_db_instance
            yield mock_db_instance

    def test_db_connection_closed_on_validation_error(self, client, mock_db):
        """Test C1: Database connection is closed even when validation fails"""
        response = client.put('/api/monitoring/configs/1', json={
            'config_name': 'Test Config',
            'monitoring_start_time': '25:00'  # Invalid time format
        })

        # Should return validation error
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

        # CRITICAL: Database should be closed despite early return
        mock_db.close.assert_called_once()

    def test_db_connection_closed_on_cross_day_error(self, client, mock_db):
        """Test C1: Database connection is closed on cross-day validation error"""
        response = client.put('/api/monitoring/configs/1', json={
            'config_name': 'Test Config',
            'monitoring_start_time': '20:00',
            'monitoring_end_time': '08:00'  # Cross-day
        })

        # Should return validation error
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

        # CRITICAL: Database should be closed despite early return
        mock_db.close.assert_called_once()

    def test_empty_string_converted_to_none_for_config_name(self, client, mock_db):
        """Test C2: Empty string for config_name is converted to None"""
        response = client.put('/api/monitoring/configs/1', json={
            'config_name': '   '  # Whitespace only
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify update was called WITHOUT config_name (empty string -> None -> not in updates)
        call_args = mock_db.update_monitoring_config.call_args
        assert 'config_name' not in call_args[1], \
            f"Empty config_name should not be in updates, got {call_args[1]}"

    def test_empty_string_converted_to_none_for_reg_cap(self, client, mock_db):
        """Test C2: Empty string for reg_cap is converted to None"""
        response = client.put('/api/monitoring/configs/1', json={
            'reg_cap': '   '  # Whitespace only
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify update was called WITHOUT reg_cap (empty string -> None -> not in updates)
        call_args = mock_db.update_monitoring_config.call_args
        assert 'reg_cap' not in call_args[1], \
            f"Empty reg_cap should not be in updates, got {call_args[1]}"

    def test_empty_string_converted_to_none_for_time_fields(self, client, mock_db):
        """Test C2: Empty string for time fields is converted to None"""
        response = client.put('/api/monitoring/configs/1', json={
            'monitoring_start_time': '   ',  # Whitespace only
            'monitoring_end_time': ''  # Empty string
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify update was called WITHOUT time fields
        call_args = mock_db.update_monitoring_config.call_args
        assert 'monitoring_start_time' not in call_args[1], \
            f"Empty monitoring_start_time should not be in updates, got {call_args[1]}"
        assert 'monitoring_end_time' not in call_args[1], \
            f"Empty monitoring_end_time should not be in updates, got {call_args[1]}"

    def test_string_fields_are_stripped(self, client, mock_db):
        """Test I1: String fields are stripped of whitespace"""
        response = client.put('/api/monitoring/configs/1', json={
            'config_name': '  Test Config  ',
            'reg_cap': '  1000万人民币  ',
            'monitoring_start_time': '  09:00  ',
            'monitoring_end_time': '  18:00  '
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify all string fields were stripped
        call_args = mock_db.update_monitoring_config.call_args
        updates = call_args[1]

        assert updates['config_name'] == 'Test Config', \
            f"config_name should be stripped, got '{updates['config_name']}'"
        assert updates['reg_cap'] == '1000万人民币', \
            f"reg_cap should be stripped, got '{updates['reg_cap']}'"
        assert updates['monitoring_start_time'] == '09:00', \
            f"monitoring_start_time should be stripped, got '{updates['monitoring_start_time']}'"
        assert updates['monitoring_end_time'] == '18:00', \
            f"monitoring_end_time should be stripped, got '{updates['monitoring_end_time']}'"

    def test_db_connection_closed_on_success(self, client, mock_db):
        """Test C1: Database connection is closed on successful update"""
        response = client.put('/api/monitoring/configs/1', json={
            'config_name': 'Updated Config'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Database should be closed
        mock_db.close.assert_called_once()

    def test_db_connection_closed_on_db_failure(self, client, mock_db):
        """Test C1: Database connection is closed even when update fails"""
        mock_db.update_monitoring_config.return_value = False

        response = client.put('/api/monitoring/configs/1', json={
            'config_name': 'Updated Config'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is False

        # Database should be closed even on failure
        mock_db.close.assert_called_once()

    def test_partial_update_with_valid_fields(self, client, mock_db):
        """Test that partial updates work correctly with stripped fields"""
        response = client.put('/api/monitoring/configs/1', json={
            'config_name': '  New Name  ',
            'interval_minutes': 10
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify only specified fields were updated
        call_args = mock_db.update_monitoring_config.call_args
        updates = call_args[1]

        assert 'config_name' in updates
        assert updates['config_name'] == 'New Name'  # Stripped
        assert updates['interval_minutes'] == 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
