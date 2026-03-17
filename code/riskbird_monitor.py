#!/usr/bin/env python3
"""
RiskBird monitoring service
Automatically queries RiskBird API for newly registered companies
"""
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
from database import BOSSDatabase
from riskbird_search import build_search_params, call_riskbird_search_api


class RiskBirdMonitor:
    """RiskBird API monitoring service"""

    def __init__(self, db: BOSSDatabase = None):
        """
        Initialize monitor

        Args:
            db: Database connection (optional, creates new if not provided)
        """
        self.db = db
        self.logger = logging.getLogger(__name__)

    def build_search_params_from_config(self, config: Dict) -> Dict:
        """
        Build RiskBird API search params from monitoring config

        Args:
            config: Monitoring config dict

        Returns:
            dict: API request parameters
        """
        region_codes_value = config.get('region_codes', '[]')

        # Handle both list and JSON string formats
        if isinstance(region_codes_value, list):
            region_codes = region_codes_value
        else:
            region_codes = json.loads(region_codes_value)

        region_codes_str = ','.join(region_codes) if region_codes else ''

        # Set date range to today only
        today = datetime.now().strftime('%Y-%m-%d')
        es_date = f'{today}￥{today}'

        reg_cap = config.get('reg_cap', '')

        return build_search_params(
            regionid=region_codes_str,
            regcap=reg_cap,
            esdate=es_date
        )

    def call_riskbird_api(self, token: str, app_uuid: str, search_params: dict) -> dict:
        """
        Call RiskBird search API

        Args:
            token: JWT token
            app_uuid: App UUID
            search_params: Search parameters

        Returns:
            dict: API response
        """
        return call_riskbird_search_api(token, app_uuid, search_params)

    def parse_companies_from_response(self, response: dict) -> List[Dict]:
        """
        Parse companies from RiskBird API response

        Args:
            response: API response dict

        Returns:
            list: Parsed company data
        """
        companies = []

        if 'error' in response:
            self.logger.error(f"API error: {response.get('message')}")
            return companies

        data = response.get('data', [])

        if not isinstance(data, list):
            # Some API responses might have different structure
            data = data.get('aaData', []) if isinstance(data, dict) else []

        for item in data:
            try:
                company = {
                    'company_name': item.get('name', ''),
                    'credit_code': item.get('creditNo', ''),
                    'reg_date': item.get('esDate', ''),
                    'reg_cap': item.get('regCap', ''),
                    'legal_representative': item.get('frname', ''),
                    'contact': item.get('contact', ''),
                    'address': item.get('dom', ''),
                    'region_code': self._extract_region_code(item),
                    'region_name': self._extract_region_name(item)
                }
                companies.append(company)
            except Exception as e:
                self.logger.warning(f"Failed to parse company: {e}")
                continue

        return companies

    def _extract_region_code(self, company_data: dict) -> str:
        """Extract region code from company data"""
        # Implementation depends on actual API response structure
        # This is a placeholder
        return company_data.get('regionCode', '')

    def _extract_region_name(self, company_data: dict) -> str:
        """Extract region name from company data"""
        # Implementation depends on actual API response structure
        return company_data.get('regionName', '')

    def run_monitoring_task(self, config_id: int) -> Dict:
        """
        Execute a single monitoring task

        Args:
            config_id: Monitoring configuration ID

        Returns:
            dict: Task result with stats
        """
        result = {
            'success': False,
            'companies_added': 0,
            'companies_skipped': 0,
            'error': None
        }

        try:
            # Get config
            config = self.db.get_monitoring_config(config_id)
            if not config:
                result['error'] = f'Config {config_id} not found'
                return result

            # Get API credentials
            token = self.db.get_riskbird_config('token')
            app_uuid = self.db.get_riskbird_config('app_uuid')

            if not token or not app_uuid:
                result['error'] = 'API credentials not configured'
                return result

            # Build search params
            search_params = self.build_search_params_from_config(config)

            # Call API
            api_response = self.call_riskbird_api(token, app_uuid, search_params)

            if 'error' in api_response:
                if api_response['error'] == 'unauthorized':
                    result['error'] = 'Token expired or invalid'
                else:
                    result['error'] = api_response.get('message', 'API call failed')
                return result

            # Parse companies
            companies = self.parse_companies_from_response(api_response)

            # Save to database
            added = 0
            skipped = 0

            for company in companies:
                company['config_id'] = config_id
                company_id = self.db.insert_monitored_company(company)

                if company_id:
                    added += 1
                else:
                    skipped += 1

            result['success'] = True
            result['companies_added'] = added
            result['companies_skipped'] = skipped

            self.logger.info(f"Monitoring task completed: {added} added, {skipped} skipped")

        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Monitoring task failed: {e}")

        return result
