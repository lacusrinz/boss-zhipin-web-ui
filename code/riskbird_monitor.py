#!/usr/bin/env python3
"""
RiskBird monitoring service
Automatically queries RiskBird API for newly registered companies
"""
import logging
import json
import time
import random
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

    def parse_companies_from_response(self, response: dict) -> tuple[List[Dict], int]:
        """
        Parse companies from RiskBird API response

        Args:
            response: API response dict

        Returns:
            tuple: (list of parsed company data, total record count)
        """
        companies = []

        if 'error' in response:
            self.logger.error(f"API error: {response.get('message')}")
            return companies, 0

        data = response.get('data', [])

        if not isinstance(data, list):
            # Some API responses might have different structure
            total_records = data.get('iTotalRecords', 0)
            data = data.get('aaData', [])
        else:
            total_records = len(data)

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

        return companies, total_records

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
            encrypted_token = self.db.get_riskbird_config('token')
            app_uuid = self.db.get_riskbird_config('app_uuid')

            if not encrypted_token or not app_uuid:
                result['error'] = 'API credentials not configured'
                return result

            # Decrypt the token
            from token_service import TokenService
            token_service = TokenService()
            try:
                token = token_service.decrypt(encrypted_token)
            except Exception as e:
                result['error'] = f'Token decryption failed: {e}'
                return result

            # Parse region codes
            region_codes_value = config.get('region_codes', '[]')
            if isinstance(region_codes_value, list):
                region_codes = region_codes_value
            else:
                region_codes = json.loads(region_codes_value)

            # API can handle 5 regions at a time - split into batches
            MAX_REGIONS_PER_REQUEST = 5
            region_batches = []

            for i in range(0, len(region_codes), MAX_REGIONS_PER_REQUEST):
                batch = region_codes[i:i + MAX_REGIONS_PER_REQUEST]
                region_batches.append(batch)

            self.logger.info(f"Querying RiskBird API: {len(region_codes)} regions in {len(region_batches)} batch(es)")

            # Process each batch
            all_companies = []
            batch_errors = []

            for batch_idx, batch_regions in enumerate(region_batches, 1):
                regions_str = ','.join(batch_regions)
                self.logger.info(f"Batch {batch_idx}/{len(region_batches)}: regions={regions_str}")

                # Add random delay between batches to avoid rate limiting
                if batch_idx > 1:
                    delay = random.uniform(1, 3)
                    self.logger.info(f"Waiting {delay:.1f} seconds before batch {batch_idx}...")
                    time.sleep(delay)

                # Build search params for this batch
                today = datetime.now().strftime('%Y-%m-%d')
                es_date = f'{today}￥{today}'
                reg_cap = config.get('reg_cap', '')

                # Pagination settings
                PAGE_SIZE = 10
                page_start = 0
                batch_total_companies = 0
                batch_has_more = True

                # Fetch all pages for this batch
                while batch_has_more:
                    search_params = build_search_params(
                        regionid=regions_str,
                        regcap=reg_cap,
                        esdate=es_date,
                        status='1',
                        page_start=page_start,
                        page_length=PAGE_SIZE
                    )

                    # Debug: log the search params
                    self.logger.info(f"Fetching page {page_start // PAGE_SIZE + 1} (start={page_start}) for batch {batch_idx}")

                    # Call API for this batch/page
                    api_response = self.call_riskbird_api(token, app_uuid, search_params)

                    if 'error' in api_response:
                        error_msg = f"Batch {batch_idx} (page {page_start // PAGE_SIZE + 1}) failed: {api_response.get('message', 'Unknown error')}"
                        batch_errors.append(error_msg)
                        self.logger.error(error_msg)
                        # Stop pagination for this batch and continue with next batch
                        break

                    # Parse companies from this page
                    companies, total_records = self.parse_companies_from_response(api_response)
                    all_companies.extend(companies)
                    batch_total_companies += len(companies)

                    self.logger.info(f"Page {page_start // PAGE_SIZE + 1}: {len(companies)} companies (total so far: {batch_total_companies}, total available: {total_records})")

                    # Check if we need to fetch more pages
                    if batch_total_companies >= total_records or len(companies) < PAGE_SIZE:
                        batch_has_more = False
                        self.logger.info(f"Batch {batch_idx} pagination complete: {batch_total_companies}/{total_records} companies fetched")
                    else:
                        # Add small delay between pages to avoid rate limiting
                        time.sleep(0.5)
                        page_start += PAGE_SIZE

            # Check if all batches failed
            if len(batch_errors) == len(region_batches):
                result['error'] = f"All {len(region_batches)} batch(es) failed: {'; '.join(batch_errors)}"
                return result

            # Log partial errors if any
            if batch_errors:
                self.logger.warning(f"Some batches failed: {'; '.join(batch_errors)}")

            # Save all companies to database
            added = 0
            skipped = 0

            for company in all_companies:
                company['config_id'] = config_id
                company_id = self.db.insert_monitored_company(company)

                if company_id:
                    added += 1
                else:
                    skipped += 1

            # Mark as successful even if no companies found
            result['success'] = True
            result['companies_added'] = added
            result['companies_skipped'] = skipped
            result['error'] = None  # Clear error for successful runs

            self.logger.info(f"Monitoring task completed: {added} added, {skipped} skipped")

        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Monitoring task failed: {e}")

        return result
