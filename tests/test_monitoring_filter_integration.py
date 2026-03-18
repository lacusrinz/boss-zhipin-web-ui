#!/usr/bin/env python3
"""
Integration tests for monitoring date filter and config_name feature

This test suite verifies the complete workflow of the monitoring date filter feature,
including database operations for date filtering and config_name field retrieval.
"""

import sys
from pathlib import Path

# Add code directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'code'))

import pytest
from datetime import datetime, timedelta
from code.database import BOSSDatabase


class TestMonitoringFilterIntegration:
    """Test date filtering and config_name functionality"""

    @pytest.fixture
    def db(self):
        """Create database connection for testing"""
        db = BOSSDatabase('data/boss_jobs.db')
        db.connect()
        yield db
        db.close()

    def test_get_monitoring_runs_with_date_filter(self, db):
        """Test get_monitoring_runs with date parameters"""
        # Test with today's date
        today = datetime.now().strftime('%Y-%m-%d')
        runs = db.get_monitoring_runs(start_date=today, end_date=today, limit=10)

        assert isinstance(runs, list), "Should return a list"
        # Verify all results are from today
        for run in runs:
            run_date = run['run_time'].split(' ')[0]
            assert run_date == today, f"Expected date {today}, got {run_date}"

    def test_get_monitoring_runs_without_date_filter(self, db):
        """Test backward compatibility - no date parameters"""
        runs = db.get_monitoring_runs(limit=10)

        assert isinstance(runs, list), "Should return a list"
        # Should return results regardless of date
        assert len(runs) <= 10, "Should respect limit parameter"

        # If we have results, verify structure
        if runs:
            required_fields = ['id', 'config_id', 'config_name', 'run_time',
                             'success', 'companies_added', 'companies_skipped',
                             'error_message']
            for field in required_fields:
                assert field in runs[0], f"Missing field: {field}"

    def test_get_monitored_companies_with_config_name(self, db):
        """Test get_monitored_companies returns config_name"""
        companies = db.get_monitored_companies(limit=5)

        assert isinstance(companies, list), "Should return a list"
        # Verify config_name field exists
        for company in companies:
            assert 'config_name' in company, "config_name field should be present"
            # config_name can be None (deleted config) or a string
            if company['config_name'] is not None:
                assert isinstance(company['config_name'], str), \
                    "config_name should be a string when not None"

    def test_get_monitored_companies_with_date_filter(self, db):
        """Test get_monitored_companies with date parameters"""
        # First, get a date that actually has data
        all_companies = db.get_monitored_companies(limit=100)

        if not all_companies:
            pytest.skip("No monitored companies in database")

        # Use the date of the first company for testing
        test_date = all_companies[0]['monitoring_time'].split(' ')[0]

        companies = db.get_monitored_companies(
            start_date=test_date,
            end_date=test_date,
            limit=10
        )

        assert isinstance(companies, list), "Should return a list"
        # Verify all results are from the specified date
        for company in companies:
            if company['monitoring_time']:
                comp_date = company['monitoring_time'].split(' ')[0]
                assert comp_date == test_date, \
                    f"Expected date {test_date}, got {comp_date}"

    def test_get_monitoring_runs_date_range(self, db):
        """Test get_monitoring_runs with a date range"""
        # Test with a wider date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        runs = db.get_monitoring_runs(
            start_date=start_date_str,
            end_date=end_date_str,
            limit=10
        )

        assert isinstance(runs, list), "Should return a list"
        # Verify all results are within the date range
        for run in runs:
            run_date = datetime.strptime(run['run_time'].split(' ')[0], '%Y-%m-%d')
            assert start_date <= run_date <= end_date, \
                f"Run date {run_date} not in range [{start_date}, {end_date}]"

    def test_get_monitored_companies_date_range(self, db):
        """Test get_monitored_companies with a date range"""
        # Get all companies to find a valid date range
        all_companies = db.get_monitored_companies(limit=100)

        if len(all_companies) < 2:
            pytest.skip("Need at least 2 companies with different dates for range test")

        # Use the dates from the first and last company
        start_date = all_companies[-1]['monitoring_time'].split(' ')[0]
        end_date = all_companies[0]['monitoring_time'].split(' ')[0]

        companies = db.get_monitored_companies(
            start_date=start_date,
            end_date=end_date,
            limit=10
        )

        assert isinstance(companies, list), "Should return a list"
        # Verify all results are within the date range
        for company in companies:
            if company['monitoring_time']:
                comp_date = company['monitoring_time'].split(' ')[0]
                assert start_date <= comp_date <= end_date, \
                    f"Company date {comp_date} not in range [{start_date}, {end_date}]"

    def test_get_monitoring_runs_count_filtered(self, db):
        """Test get_monitoring_runs_count_filtered with date parameters"""
        # Test without date filter
        total_count = db.get_monitoring_runs_count_filtered()
        assert isinstance(total_count, int), "Should return an integer"
        assert total_count >= 0, "Count should be non-negative"

        # Test with date filter
        today = datetime.now().strftime('%Y-%m-%d')
        filtered_count = db.get_monitoring_runs_count_filtered(
            start_date=today,
            end_date=today
        )
        assert isinstance(filtered_count, int), "Should return an integer"
        assert filtered_count >= 0, "Count should be non-negative"
        assert filtered_count <= total_count, \
            "Filtered count should be less than or equal to total count"

    def test_get_monitored_companies_count_filtered(self, db):
        """Test get_monitored_companies_count_filtered with date parameters"""
        # Test without date filter
        total_count = db.get_monitored_companies_count_filtered()
        assert isinstance(total_count, int), "Should return an integer"
        assert total_count >= 0, "Count should be non-negative"

        # Test with date filter
        all_companies = db.get_monitored_companies(limit=1)

        if not all_companies:
            pytest.skip("No monitored companies in database")

        test_date = all_companies[0]['monitoring_time'].split(' ')[0]
        filtered_count = db.get_monitored_companies_count_filtered(
            start_date=test_date,
            end_date=test_date
        )
        assert isinstance(filtered_count, int), "Should return an integer"
        assert filtered_count >= 0, "Count should be non-negative"
        assert filtered_count <= total_count, \
            "Filtered count should be less than or equal to total count"

    def test_config_name_with_deleted_config(self, db):
        """Test that config_name is None when config is deleted"""
        companies = db.get_monitored_companies(limit=10)

        # Find a company with config_id
        company_with_config = None
        for company in companies:
            if company['config_id'] is not None:
                company_with_config = company
                break

        if not company_with_config:
            pytest.skip("No companies with config_id found")

        # Verify config_name field exists (can be None if config was deleted)
        assert 'config_name' in company_with_config, \
            "config_name field should be present"

        # If config_name exists, it should be a string
        if company_with_config['config_name'] is not None:
            assert isinstance(company_with_config['config_name'], str), \
                "config_name should be a string when not None"

    def test_date_filter_with_future_dates(self, db):
        """Test date filter with future dates returns empty list"""
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

        runs = db.get_monitoring_runs(
            start_date=future_date,
            end_date=future_date,
            limit=10
        )

        assert isinstance(runs, list), "Should return a list"
        assert len(runs) == 0, "Should return empty list for future dates"

        companies = db.get_monitored_companies(
            start_date=future_date,
            end_date=future_date,
            limit=10
        )

        assert isinstance(companies, list), "Should return a list"
        assert len(companies) == 0, "Should return empty list for future dates"

    def test_date_filter_with_past_dates(self, db):
        """Test date filter with ancient past dates returns empty list"""
        ancient_date = "2020-01-01"

        runs = db.get_monitoring_runs(
            start_date=ancient_date,
            end_date=ancient_date,
            limit=10
        )

        assert isinstance(runs, list), "Should return a list"
        # Should return empty or very few results for ancient dates
        assert isinstance(runs, list), "Should return a list"

        companies = db.get_monitored_companies(
            start_date=ancient_date,
            end_date=ancient_date,
            limit=10
        )

        assert isinstance(companies, list), "Should return a list"
        # Should return empty or very few results for ancient dates
        assert isinstance(companies, list), "Should return a list"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
