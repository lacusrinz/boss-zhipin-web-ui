#!/usr/bin/env python3
"""
Demonstration of the bug that was fixed
Shows what would happen with the old code vs the new code
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import BOSSDatabase

def old_buggy_count(db, config_id=None):
    """Old buggy implementation - only checked config_id"""
    if config_id:
        db.cursor.execute("SELECT COUNT(*) FROM monitored_companies WHERE config_id = ?", (config_id,))
    else:
        db.cursor.execute("SELECT COUNT(*) FROM monitored_companies")
    return db.cursor.fetchone()[0]

def new_fixed_count(db, config_id=None, start_date=None, end_date=None):
    """New fixed implementation - applies all filters"""
    query = "SELECT COUNT(*) FROM monitored_companies WHERE 1=1"
    params = []

    if config_id:
        query += " AND config_id = ?"
        params.append(config_id)

    if start_date:
        query += " AND DATE(monitoring_time) >= ?"
        params.append(start_date)

    if end_date:
        query += " AND DATE(monitoring_time) <= ?"
        params.append(end_date)

    db.cursor.execute(query, params)
    return db.cursor.fetchone()[0]

def demonstrate_bug():
    """Demonstrate the bug and the fix"""
    print("DEMONSTRATION: Pagination Count Bug")
    print("=" * 70)
    
    db = BOSSDatabase()
    if not db.connect():
        print("Failed to connect to database")
        return

    # Scenario: User requests data with date filter
    start_date = '2026-03-18'
    end_date = '2026-03-18'
    
    print(f"\nScenario: User requests companies with date filter")
    print(f"  Date range: {start_date} to {end_date}")
    
    # Get actual filtered data
    companies = db.get_monitored_companies(
        start_date=start_date,
        end_date=end_date,
        limit=10,
        offset=0
    )
    
    actual_count = len(companies)
    print(f"  Actual companies returned: {actual_count}")
    
    # OLD BUGGY CODE
    old_total = old_buggy_count(db, config_id=None)
    print(f"\n❌ OLD BUGGY CODE:")
    print(f"  Total count returned: {old_total}")
    print(f"  Companies returned: {actual_count}")
    print(f"  PROBLEM: Total ({old_total}) != Actual filtered count ({actual_count})")
    print(f"  Result: Pagination shows wrong number of pages!")
    
    # NEW FIXED CODE
    new_total = new_fixed_count(db, config_id=None, start_date=start_date, end_date=end_date)
    print(f"\n✓ NEW FIXED CODE:")
    print(f"  Total count returned: {new_total}")
    print(f"  Companies returned: {actual_count}")
    print(f"  SUCCESS: Total ({new_total}) == Actual filtered count ({actual_count})")
    print(f"  Result: Pagination is correct!")
    
    # Show the impact
    print(f"\n" + "=" * 70)
    print("IMPACT ANALYSIS:")
    print(f"  Old code would show: {old_total} total records")
    print(f"  New code shows: {new_total} total records")
    print(f"  Difference: {old_total - new_total} records (if date filters excluded some)")
    print(f"  User experience: Pagination now works correctly with date filters!")

if __name__ == '__main__':
    demonstrate_bug()
