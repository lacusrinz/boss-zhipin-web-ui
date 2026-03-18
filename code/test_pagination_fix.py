#!/usr/bin/env python3
"""
Test script to verify the pagination count fix for monitored companies endpoint
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from code.database import BOSSDatabase

def test_filtered_count():
    """Test the filtered count method"""
    print("Testing get_monitored_companies_count_filtered()...")
    print("=" * 60)

    db = BOSSDatabase()
    if not db.connect():
        print("Failed to connect to database")
        return False

    # Test 1: No filters
    print("\nTest 1: No filters (should return all)")
    count1 = db.get_monitored_companies_count_filtered()
    print(f"  Result: {count1}")

    # Verify with direct SQL
    db.cursor.execute("SELECT COUNT(*) FROM monitored_companies")
    expected1 = db.cursor.fetchone()[0]
    print(f"  Expected (SQL): {expected1}")
    print(f"  Match: {count1 == expected1}")

    # Test 2: Config filter only
    print("\nTest 2: Config filter only (config_id=1)")
    count2 = db.get_monitored_companies_count_filtered(config_id=1)
    print(f"  Result: {count2}")

    db.cursor.execute("SELECT COUNT(*) FROM monitored_companies WHERE config_id = ?", (1,))
    expected2 = db.cursor.fetchone()[0]
    print(f"  Expected (SQL): {expected2}")
    print(f"  Match: {count2 == expected2}")

    # Test 3: Start date filter only
    print("\nTest 3: Start date filter (>= 2026-03-18)")
    count3 = db.get_monitored_companies_count_filtered(start_date='2026-03-18')
    print(f"  Result: {count3}")

    db.cursor.execute("SELECT COUNT(*) FROM monitored_companies WHERE DATE(monitoring_time) >= ?", ('2026-03-18',))
    expected3 = db.cursor.fetchone()[0]
    print(f"  Expected (SQL): {expected3}")
    print(f"  Match: {count3 == expected3}")

    # Test 4: End date filter only
    print("\nTest 4: End date filter (<= 2026-03-18)")
    count4 = db.get_monitored_companies_count_filtered(end_date='2026-03-18')
    print(f"  Result: {count4}")

    db.cursor.execute("SELECT COUNT(*) FROM monitored_companies WHERE DATE(monitoring_time) <= ?", ('2026-03-18',))
    expected4 = db.cursor.fetchone()[0]
    print(f"  Expected (SQL): {expected4}")
    print(f"  Match: {count4 == expected4}")

    # Test 5: Date range filter
    print("\nTest 5: Date range filter (2026-03-18 to 2026-03-18)")
    count5 = db.get_monitored_companies_count_filtered(start_date='2026-03-18', end_date='2026-03-18')
    print(f"  Result: {count5}")

    db.cursor.execute("SELECT COUNT(*) FROM monitored_companies WHERE DATE(monitoring_time) >= ? AND DATE(monitoring_time) <= ?",
                     ('2026-03-18', '2026-03-18'))
    expected5 = db.cursor.fetchone()[0]
    print(f"  Expected (SQL): {expected5}")
    print(f"  Match: {count5 == expected5}")

    # Test 6: Config + Date range filter
    print("\nTest 6: Config + Date range filter (config_id=1, 2026-03-18)")
    count6 = db.get_monitored_companies_count_filtered(config_id=1, start_date='2026-03-18', end_date='2026-03-18')
    print(f"  Result: {count6}")

    db.cursor.execute("SELECT COUNT(*) FROM monitored_companies WHERE config_id = ? AND DATE(monitoring_time) >= ? AND DATE(monitoring_time) <= ?",
                     (1, '2026-03-18', '2026-03-18'))
    expected6 = db.cursor.fetchone()[0]
    print(f"  Expected (SQL): {expected6}")
    print(f"  Match: {count6 == expected6}")

    # Test 7: Date range with no matches
    print("\nTest 7: Date range with no matches (future dates)")
    count7 = db.get_monitored_companies_count_filtered(start_date='2027-01-01', end_date='2027-12-31')
    print(f"  Result: {count7}")
    print(f"  Expected: 0")
    print(f"  Match: {count7 == 0}")

    db.close()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    tests = [
        ("No filters", count1 == expected1),
        ("Config filter", count2 == expected2),
        ("Start date filter", count3 == expected3),
        ("End date filter", count4 == expected4),
        ("Date range filter", count5 == expected5),
        ("Config + Date range", count6 == expected6),
        ("No matches", count7 == 0)
    ]

    all_passed = all(result for _, result in tests)
    for name, passed in tests:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")

    print("\n" + ("=" * 60))
    if all_passed:
        print("All tests PASSED!")
        return True
    else:
        print("Some tests FAILED!")
        return False

if __name__ == '__main__':
    success = test_filtered_count()
    sys.exit(0 if success else 1)
