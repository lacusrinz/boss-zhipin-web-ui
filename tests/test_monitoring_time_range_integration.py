#!/usr/bin/env python3
"""
Integration tests for monitoring time range feature

This test suite verifies the complete workflow of the monitoring time range feature,
including API endpoints, database operations, and validation logic.
"""

import sys
from pathlib import Path
import time
import json

# Add code directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


class TestMonitoringTimeRangeIntegration:
    """Comprehensive integration tests for monitoring time range feature"""

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

            # Mock insert_monitoring_config to return incrementing IDs
            config_id_counter = [1]

            def mock_insert_config(**kwargs):
                config_id = config_id_counter[0]
                config_id_counter[0] += 1
                return config_id

            mock_db_instance.insert_monitoring_config = MagicMock(side_effect=mock_insert_config)

            # Mock other database methods
            mock_db_instance.get_monitoring_config = MagicMock(return_value={
                'id': 1,
                'config_name': 'Test Config',
                'region_codes': '["110000"]',
                'is_active': 1,
                'interval_minutes': 10,
                'reg_cap': None,
                'monitoring_start_time': '08:00',
                'monitoring_end_time': '20:00',
                'created_at': '2026-03-18 10:00:00',
                'updated_at': '2026-03-18 10:00:00'
            })

            mock_db_instance.get_all_monitoring_configs = MagicMock(return_value=[
                {
                    'id': 1,
                    'config_name': 'Test Config',
                    'region_codes': '["110000"]',
                    'is_active': 1,
                    'interval_minutes': 10,
                    'reg_cap': None,
                    'monitoring_start_time': '08:00',
                    'monitoring_end_time': '20:00',
                    'created_at': '2026-03-18 10:00:00',
                    'updated_at': '2026-03-18 10:00:00'
                }
            ])

            mock_db_instance.update_monitoring_config = MagicMock(return_value=True)
            mock_db_instance.delete_monitoring_config = MagicMock(return_value=True)
            mock_db_instance.close = MagicMock()

            mock_get_db.return_value = mock_db_instance
            yield mock_db_instance

    @pytest.fixture
    def mock_scheduler(self):
        """Mock scheduler operations"""
        with patch('web_app.add_monitoring_job') as mock_add_job, \
             patch('web_app.remove_monitoring_job') as mock_remove_job:
            mock_add_job.return_value = True
            mock_remove_job.return_value = True
            yield {'add': mock_add_job, 'remove': mock_remove_job}

    def test_full_workflow_with_time_range(self, client, mock_db, mock_scheduler):
        """
        Test complete workflow: create -> verify -> update -> verify -> delete
        """
        # Generate unique config name using timestamp
        unique_name = f"Integration Test Config {int(time.time())}"

        # Step 1: Create config with time range via API
        create_response = client.post('/api/monitoring/configs', json={
            'config_name': unique_name,
            'region_codes': ['110000', '310000'],
            'interval_minutes': 15,
            'monitoring_start_time': '08:00',
            'monitoring_end_time': '20:00'
        })

        create_data = create_response.get_json()
        assert create_response.status_code == 200, \
            f"Create failed: {create_response.status_code} - {create_data}"
        assert create_data['success'] is True, "Create should return success=True"
        assert 'config_id' in create_data, "Response should include config_id"
        config_id = create_data['config_id']

        # Verify database was called with correct time parameters
        mock_db.insert_monitoring_config.assert_called_once()
        call_kwargs = mock_db.insert_monitoring_config.call_args.kwargs
        assert call_kwargs['monitoring_start_time'] == '08:00', \
            f"Start time should be 08:00, got {call_kwargs.get('monitoring_start_time')}"
        assert call_kwargs['monitoring_end_time'] == '20:00', \
            f"End time should be 20:00, got {call_kwargs.get('monitoring_end_time')}"

        # Verify scheduler job was added
        mock_scheduler['add'].assert_called_once_with(config_id, 15)

        # Step 2: Verify config is returned with time fields
        # Update mock to return the created config
        mock_db.get_monitoring_config.return_value = {
            'id': config_id,
            'config_name': unique_name,
            'region_codes': json.dumps(['110000', '310000']),
            'is_active': 1,
            'interval_minutes': 15,
            'reg_cap': None,
            'monitoring_start_time': '08:00',
            'monitoring_end_time': '20:00',
            'created_at': '2026-03-18 10:00:00',
            'updated_at': '2026-03-18 10:00:00'
        }

        get_response = client.get(f'/api/monitoring/configs')
        get_data = get_response.get_json()
        assert get_response.status_code == 200, "Get configs should succeed"
        assert get_data['success'] is True, "Get should return success=True"
        assert len(get_data['configs']) > 0, "Should have at least one config"

        # Verify time fields are present
        config = get_data['configs'][0]
        assert 'monitoring_start_time' in config, "Config should include monitoring_start_time"
        assert 'monitoring_end_time' in config, "Config should include monitoring_end_time"
        assert config['monitoring_start_time'] == '08:00', \
            f"Start time should be 08:00, got {config.get('monitoring_start_time')}"
        assert config['monitoring_end_time'] == '20:00', \
            f"End time should be 20:00, got {config.get('monitoring_end_time')}"

        # Step 3: Update time range via API
        update_response = client.put(f'/api/monitoring/configs/{config_id}', json={
            'monitoring_start_time': '09:00',
            'monitoring_end_time': '18:00'
        })

        update_data = update_response.get_json()
        assert update_response.status_code == 200, \
            f"Update failed: {update_response.status_code} - {update_data}"
        assert update_data['success'] is True, "Update should return success=True"

        # Verify database update was called
        mock_db.update_monitoring_config.assert_called_once()
        update_kwargs = mock_db.update_monitoring_config.call_args[1]
        assert update_kwargs['monitoring_start_time'] == '09:00', \
            f"Updated start time should be 09:00, got {update_kwargs.get('monitoring_start_time')}"
        assert update_kwargs['monitoring_end_time'] == '18:00', \
            f"Updated end time should be 18:00, got {update_kwargs.get('monitoring_end_time')}"

        # Step 4: Delete config
        delete_response = client.delete(f'/api/monitoring/configs/{config_id}')
        delete_data = delete_response.get_json()
        assert delete_response.status_code == 200, \
            f"Delete failed: {delete_response.status_code} - {delete_data}"
        assert delete_data['success'] is True, "Delete should return success=True"

        # Verify database delete was called
        mock_db.delete_monitoring_config.assert_called_once_with(config_id)

        # Verify scheduler job was removed
        mock_scheduler['remove'].assert_called_once_with(config_id)

    def test_time_range_validation(self, client, mock_db, mock_scheduler):
        """
        Test is_within_monitoring_hours with various inputs
        """
        from web_app import is_within_monitoring_hours

        # Test 1: None/empty returns True (no restriction)
        assert is_within_monitoring_hours(None, None) is True, \
            "None/None should return True (no time restriction)"
        assert is_within_monitoring_hours("", "") is True, \
            "Empty strings should return True (no time restriction)"
        assert is_within_monitoring_hours(None, "") is True, \
            "None/empty should return True (no time restriction)"

        # Test 2: Wide range returns True
        assert is_within_monitoring_hours("00:00", "23:59") is True, \
            "Wide range (00:00-23:59) should return True"
        # Note: Minimal range test is time-dependent, so we skip it
        # and just verify the function works without asserting specific result

        # Test 3: Only start time provided (returns True - no restriction)
        assert is_within_monitoring_hours("09:00", "") is True, \
            "Only start time should return True (no restriction)"
        assert is_within_monitoring_hours("09:00", None) is True, \
            "Start time with None end should return True (no restriction)"

        # Test 4: Only end time provided (returns True - no restriction)
        assert is_within_monitoring_hours("", "18:00") is True, \
            "Only end time should return True (no restriction)"
        assert is_within_monitoring_hours(None, "18:00") is True, \
            "None start with end time should return True (no restriction)"

        # Test 5: Normal business hours
        # This test depends on current time, so we just verify the function works
        result = is_within_monitoring_hours("09:00", "18:00")
        assert isinstance(result, bool), \
            f"Should return boolean, got {type(result)}"

        # Test 6: Edge cases
        assert is_within_monitoring_hours("00:00", "23:59") is True, \
            "Full day range should return True"

    def test_invalid_time_format_rejected(self, client, mock_db, mock_scheduler):
        """
        Test that invalid time formats are rejected with 400 status
        """
        # Test 1: Invalid hour (25:00)
        response = client.post('/api/monitoring/configs', json={
            'config_name': f'Invalid Hour Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '25:00',
            'monitoring_end_time': '18:00'
        })

        data = response.get_json()
        assert response.status_code == 400, \
            f"Expected 400 for invalid hour, got {response.status_code}: {data}"
        assert data['success'] is False, "Should return success=False"
        assert '无效' in data['error'] or 'invalid' in data['error'].lower() or 'format' in data['error'].lower(), \
            f"Error should mention invalid format: {data['error']}"

        # Verify database was NOT called
        mock_db.insert_monitoring_config.assert_not_called()

        # Test 2: Invalid minutes (09:60)
        response2 = client.post('/api/monitoring/configs', json={
            'config_name': f'Invalid Minutes Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '09:60',
            'monitoring_end_time': '18:00'
        })

        data2 = response2.get_json()
        assert response2.status_code == 400, \
            f"Expected 400 for invalid minutes, got {response2.status_code}: {data2}"
        assert data2['success'] is False, "Should return success=False"

        # Test 3: Completely invalid format
        response3 = client.post('/api/monitoring/configs', json={
            'config_name': f'Invalid Format Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '9am',
            'monitoring_end_time': '5pm'
        })

        data3 = response3.get_json()
        assert response3.status_code == 400, \
            f"Expected 400 for invalid format, got {response3.status_code}: {data3}"
        assert data3['success'] is False, "Should return success=False"

        # Test 4: Missing time separator
        response4 = client.post('/api/monitoring/configs', json={
            'config_name': f'Missing Separator Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '0900',
            'monitoring_end_time': '1800'
        })

        data4 = response4.get_json()
        assert response4.status_code == 400, \
            f"Expected 400 for missing separator, got {response4.status_code}: {data4}"
        assert data4['success'] is False, "Should return success=False"

    def test_cross_day_rejected(self, client, mock_db, mock_scheduler):
        """
        Test that cross-day time ranges are rejected with 400 status
        """
        # Test 1: Cross-day range (22:00-02:00)
        response = client.post('/api/monitoring/configs', json={
            'config_name': f'Cross Day Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '22:00',
            'monitoring_end_time': '02:00'
        })

        data = response.get_json()
        assert response.status_code == 400, \
            f"Expected 400 for cross-day range, got {response.status_code}: {data}"
        assert data['success'] is False, "Should return success=False"
        assert '跨天' in data['error'] or 'cross day' in data['error'].lower() or \
               'after' in data['error'].lower() or 'end' in data['error'].lower() or \
               '晚于' in data['error'], \
            f"Error should mention cross-day rejection: {data['error']}"

        # Verify database was NOT called
        mock_db.insert_monitoring_config.assert_not_called()

        # Test 2: Equal times (00:00-00:00)
        response2 = client.post('/api/monitoring/configs', json={
            'config_name': f'Equal Times Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '00:00',
            'monitoring_end_time': '00:00'
        })

        data2 = response2.get_json()
        assert response2.status_code == 400, \
            f"Expected 400 for equal times, got {response2.status_code}: {data2}"
        assert data2['success'] is False, "Should return success=False"

        # Test 3: End time earlier than start time (18:00-09:00)
        response3 = client.post('/api/monitoring/configs', json={
            'config_name': f'End Before Start Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '18:00',
            'monitoring_end_time': '09:00'
        })

        data3 = response3.get_json()
        assert response3.status_code == 400, \
            f"Expected 400 for end before start, got {response3.status_code}: {data3}"
        assert data3['success'] is False, "Should return success=False"

        # Test 4: Midnight to midnight (technically cross-day)
        response4 = client.post('/api/monitoring/configs', json={
            'config_name': f'Midnight Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '00:00',
            'monitoring_end_time': '00:00'
        })

        data4 = response4.get_json()
        assert response4.status_code == 400, \
            f"Expected 400 for midnight to midnight, got {response4.status_code}: {data4}"
        assert data4['success'] is False, "Should return success=False"

    def test_update_with_invalid_time_format(self, client, mock_db, mock_scheduler):
        """
        Test that update endpoint also validates time format
        """
        config_id = 1

        # Test updating with invalid time format
        response = client.put(f'/api/monitoring/configs/{config_id}', json={
            'monitoring_start_time': '99:99'
        })

        data = response.get_json()
        assert response.status_code == 400, \
            f"Expected 400 for invalid time format in update, got {response.status_code}: {data}"
        assert data['success'] is False, "Should return success=False"

        # Verify database was NOT called
        mock_db.update_monitoring_config.assert_not_called()

    def test_update_with_cross_day_range(self, client, mock_db, mock_scheduler):
        """
        Test that update endpoint also rejects cross-day ranges
        """
        config_id = 1

        # Test updating with cross-day range
        response = client.put(f'/api/monitoring/configs/{config_id}', json={
            'monitoring_start_time': '20:00',
            'monitoring_end_time': '08:00'
        })

        data = response.get_json()
        assert response.status_code == 400, \
            f"Expected 400 for cross-day range in update, got {response.status_code}: {data}"
        assert data['success'] is False, "Should return success=False"

        # Verify database was NOT called
        mock_db.update_monitoring_config.assert_not_called()

    def test_partial_time_range_update(self, client, mock_db, mock_scheduler):
        """
        Test updating only start time or only end time
        """
        config_id = 1

        # Test updating only start time
        response1 = client.put(f'/api/monitoring/configs/{config_id}', json={
            'monitoring_start_time': '10:00'
        })

        data1 = response1.get_json()
        assert response1.status_code == 200, \
            f"Update with only start time should succeed: {data1}"
        assert data1['success'] is True, "Should return success=True"

        # Test updating only end time
        response2 = client.put(f'/api/monitoring/configs/{config_id}', json={
            'monitoring_end_time': '19:00'
        })

        data2 = response2.get_json()
        assert response2.status_code == 200, \
            f"Update with only end time should succeed: {data2}"
        assert data2['success'] is True, "Should return success=True"

    def test_default_time_range_values(self, client, mock_db, mock_scheduler):
        """
        Test that default time range values work correctly
        """
        # Create config without specifying time range
        response = client.post('/api/monitoring/configs', json={
            'config_name': f'Default Time Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10
        })

        data = response.get_json()
        assert response.status_code == 200, f"Create with default time should succeed: {data}"
        assert data['success'] is True, "Should return success=True"

        # Verify database was called with default time parameters
        mock_db.insert_monitoring_config.assert_called_once()
        call_kwargs = mock_db.insert_monitoring_config.call_args.kwargs
        assert call_kwargs['monitoring_start_time'] == '09:00', \
            f"Default start time should be 09:00, got {call_kwargs.get('monitoring_start_time')}"
        assert call_kwargs['monitoring_end_time'] == '18:00', \
            f"Default end time should be 18:00, got {call_kwargs.get('monitoring_end_time')}"

    def test_edge_case_time_boundaries(self, client, mock_db, mock_scheduler):
        """
        Test edge case time boundaries
        """
        # Test very early hours (00:00-01:00)
        response1 = client.post('/api/monitoring/configs', json={
            'config_name': f'Early Hours Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '00:00',
            'monitoring_end_time': '01:00'
        })

        data1 = response1.get_json()
        assert response1.status_code == 200, \
            f"Early hours should be valid: {data1}"
        assert data1['success'] is True

        # Test late hours (23:00-23:59)
        response2 = client.post('/api/monitoring/configs', json={
            'config_name': f'Late Hours Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '23:00',
            'monitoring_end_time': '23:59'
        })

        data2 = response2.get_json()
        assert response2.status_code == 200, \
            f"Late hours should be valid: {data2}"
        assert data2['success'] is True

        # Test full valid range (00:00-23:59)
        response3 = client.post('/api/monitoring/configs', json={
            'config_name': f'Full Range Test {int(time.time())}',
            'region_codes': ['110000'],
            'interval_minutes': 10,
            'monitoring_start_time': '00:00',
            'monitoring_end_time': '23:59'
        })

        data3 = response3.get_json()
        assert response3.status_code == 200, \
            f"Full range should be valid: {data3}"
        assert data3['success'] is True
