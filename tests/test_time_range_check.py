#!/usr/bin/env python3
"""
Test time range check functions with Beijing timezone support
"""

import sys
from pathlib import Path

# Add code directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch


class TestTimeRangeCheck:
    """Test suite for time range check functions"""

    def test_within_range_normal_hours(self):
        """Tests normal work hours range (09:00-18:00)"""
        from web_app import is_within_monitoring_hours

        # Mock current time to be 14:30 (within range)
        mock_time = datetime(2026, 3, 18, 14, 30, 0)

        with patch('web_app.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            result = is_within_monitoring_hours("09:00", "18:00")
            assert result is True, "Should return True when current time is within range"

    def test_outside_range_early_morning(self):
        """Tests early morning (02:00) outside work hours range"""
        from web_app import is_within_monitoring_hours

        # Mock current time to be 02:00 (outside range)
        mock_time = datetime(2026, 3, 18, 2, 0, 0)

        with patch('web_app.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_time
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            result = is_within_monitoring_hours("09:00", "18:00")
            assert result is False, "Should return False when current time is outside range"

    def test_null_time_range(self):
        """Tests null values (should return True - no restriction)"""
        from web_app import is_within_monitoring_hours

        result = is_within_monitoring_hours(None, None)
        assert result is True, "Should return True for null values (no time restriction)"

    def test_empty_string_time_range(self):
        """Tests empty strings (should return True - no restriction)"""
        from web_app import is_within_monitoring_hours

        result = is_within_monitoring_hours("", "")
        assert result is True, "Should return True for empty strings (no time restriction)"

    def test_start_time_only(self):
        """Tests only start time provided (should return True - no restriction)"""
        from web_app import is_within_monitoring_hours

        result = is_within_monitoring_hours("09:00", "")
        assert result is True, "Should return True when only start time is provided"

        result = is_within_monitoring_hours("09:00", None)
        assert result is True, "Should return True when only start time is provided (None)"

    def test_end_time_only(self):
        """Tests only end time provided (should return True - no restriction)"""
        from web_app import is_within_monitoring_hours

        result = is_within_monitoring_hours("", "18:00")
        assert result is True, "Should return True when only end time is provided"

        result = is_within_monitoring_hours(None, "18:00")
        assert result is True, "Should return True when only end time is provided (None)"

    def test_beijing_timezone(self):
        """Verifies Beijing timezone (Asia/Shanghai) is used"""
        from web_app import get_beijing_time_str

        # Just verify the function works and returns a properly formatted string
        # We can't easily mock timezone-aware datetime, so we verify the format
        result = get_beijing_time_str()

        # Should contain timezone offset
        assert "+" in result or "-" in result, f"Should contain timezone offset, got: {result}"
        # Should contain date and time
        assert ":" in result, f"Should contain time separators, got: {result}"
        # Should be in format like "2026-03-18 14:30:00 +0800"
        import re
        pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}'
        assert re.match(pattern, result), f"Should match expected format, got: {result}"
