import sys
import os
from datetime import date, timedelta

# Add parent directory to path (backend root)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.engine.phase2 import detect_test_type, check_validity, VALIDITY_DATASET

def test_detect_test_type():
    print("Testing detect_test_type...")
    cases = [
        ("AMH_Report.pdf", "AMH"),
        ("Semen_Analysis_Jan2024.pdf", "Semen Analysis"),
        ("hsg_report.jpg", "HSG"),
        ("tubal_patency.pdf", "HSG"),
        ("FSH_result.pdf", "FSH"),
        ("User_Scan.pdf", "Pelvic Ultrasound"),
        ("Unknown_File.pdf", "UNKNOWN_TEST"),
        ("hormonal_profile.pdf", "UNKNOWN_TEST") # Assuming 'hormonal' not specific enough unless mapped, but 'hormonal' is mapped in keyword map? Let's check.
    ]
    
    # Check keyword map in phase2.py source:
    # "amh": "AMH" ...
    # detect_test_type uses partial match.
    
    for filename, expected in cases:
        result = detect_test_type(filename)
        status = "PASS" if result == expected else f"FAIL (Expected {expected}, got {result})"
        print(f"[{status}] {filename} -> {result}")

def test_check_validity():
    print("\nTesting check_validity...")
    today = date.today()
    
    # AMH (365 days)
    valid_amh_date = (today - timedelta(days=300)).isoformat()
    expired_amh_date = (today - timedelta(days=400)).isoformat()
    
    # Semen Analysis (90 days)
    valid_semen = (today - timedelta(days=60)).isoformat()
    expired_semen = (today - timedelta(days=100)).isoformat()
    
    cases = [
        ("AMH", valid_amh_date, "Valid"),
        ("AMH", expired_amh_date, "Expired"),
        ("Semen Analysis", valid_semen, "Valid"),
        ("Semen Analysis", expired_semen, "Expired"),
        ("Male Karyotype", "2010-01-01", "Valid (No repetition required)") # Lifetime
    ]
    
    for test, d, expected in cases:
        result = check_validity(test, d)
        status = "PASS" if result == expected else f"FAIL (Expected {expected}, got {result})"
        print(f"[{status}] {test} on {d} -> {result}")

if __name__ == "__main__":
    test_detect_test_type()
    test_check_validity()
