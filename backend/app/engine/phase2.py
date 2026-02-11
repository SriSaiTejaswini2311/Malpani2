import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from app.models.case_state import CaseState

# 1. VALIDITY DATASET (Days)
VALIDITY_DATASET = {
    # Male Tests
    "Semen Analysis": 90, # 3 months
    "Semen Culture": 90,
    "Sperm DNA Fragmentation": 180, # 6 months
    "Sperm Vitality Test": 90,
    "Antisperm Antibodies": 180,
    "Male Hormonal Profile": 180,
    "Male Karyotype": 36500, # Lifetime (approx 100 years)
    "Y-Chromosome Microdeletion": 36500,
    "Genetic Carrier Screening (Male)": 36500,
    "HIV (Male)": 180,
    "HBsAg (Male)": 180,
    "HCV (Male)": 180,
    "Blood Group & Rh (Male)": 36500,

    # Female Tests
    "AMH": 365, # 12 months (Range 6-12, taking optimistic)
    "FSH": 180,
    "LH": 180,
    "Estradiol E2": 180,
    "Prolactin": 180,
    "TSH": 180,
    "Thyroid Antibodies": 365,
    "AFC": 180,
    "HSG": 730, # 2 years
    "Tubal Patency Test": 730, # Alias for HSG
    "Pelvic Ultrasound": 180,
    "HIV (Female)": 180,
    "HBsAg (Female)": 180,
    "HCV (Female)": 180,
    "Blood Group & Rh (Female)": 36500,
    "Female Karyotype": 36500,
    "Genetic Carrier Screening (Female)": 36500,
    
    # Generic / Groups
    "Hormonal blood tests": 180,
    "Genetic tests": 36500,
    "Ultrasound scans": 180,
    "Tube testing": 730
}

# 2. TEST TYPE DETECTION
KEYWORD_MAP = {
    "amh": "AMH",
    "semen": "Semen Analysis",
    "sperm": "Semen Analysis",
    "hsg": "HSG",
    "tube": "HSG",
    "hysterosalpingogram": "HSG",
    "tsh": "TSH",
    "prolactin": "Prolactin",
    "afc": "AFC",
    "follicle": "AFC",
    "fsh": "FSH",
    "lh": "LH",
    "estradiol": "Estradiol E2",
    "thyroid": "TSH",
    "karyotype": "Male Karyotype", # Need context for Female/Male, defaulting generic if logic allows, or explicit check
    "genetic": "Genetic Tests"
}

def detect_test_type(filename: str) -> str:
    """
    Identifies the test type based on the filename keywords.
    Returns 'UNKNOWN_TEST' if no match found.
    """
    fname = filename.lower()
    
    # Specific Checks
    if "semen" in fname or "sperm" in fname:
        return "Semen Analysis"
    if "hsg" in fname or "tube" in fname or "patency" in fname:
        return "HSG"
    if "amh" in fname:
        return "AMH"
    if "tsh" in fname:
        return "TSH"
    if "fsh" in fname:
        return "FSH"
    if "lh" in fname:
        return "LH"
    if "prolactin" in fname:
        return "Prolactin"
    if "afc" in fname or "antral" in fname:
        return "AFC"
    if "scan" in fname or "ultrasound" in fname:
        return "Pelvic Ultrasound"
    if "karyotype" in fname:
        return "Genetic tests" # Generic for validity lookup
        
    return "UNKNOWN_TEST"

def check_validity(test_name: str, test_date_str: str) -> str:
    """
    Compares test_date with today based on VALIDITY_DATASET.
    test_date_str expected in ISO format YYYY-MM-DD or similar parsable.
    """
    try:
        # Simple parser - assuming ISO for now as state stores it
        # If user input is "Jan 2024", extractor must convert it before calling this, 
        # OR we parse here.
        # Let's assume the state stores a datetime date object or ISO string.
        if isinstance(test_date_str, date):
             t_date = test_date_str
        else:
             t_date = datetime.strptime(test_date_str, "%Y-%m-%d").date()
    except:
        return "Date Unknown"

    validity_days = VALIDITY_DATASET.get(test_name, VALIDITY_DATASET.get(test_name.split(" ")[0], 180)) # Default 6 months
    
    today = date.today()
    delta = today - t_date
    days_diff = delta.days
    
    if days_diff > validity_days:
        return "Expired"
    elif days_diff > (validity_days - 30) and validity_days < 30000: # Borderline (1 month left) - exclude lifetime
        return "Close to expiry"
    else:
        if validity_days > 10000:
             return "Valid (No repetition required)"
        return "Valid"

def generate_validity_summary(documents: List[Dict]) -> str:
    """
    Generates the Phase 2 Report Validity Summary.
    """
    summary = "Phase 2: Report Validity Summary\n\n"
    
    for doc in documents:
        name = doc.get("test_name", "Unknown Document")
        date_str = doc.get("test_date", "Date Unknown")
        status = doc.get("validity_status", "Pending")
        
        # Format date for display if possible
        display_date = date_str
        
        summary += f"• {name} ({display_date}) → {status}\n"
    
    summary += "\nNotes:\n"
    summary += "Different laboratories may use different reference ranges.\n"
    summary += "I will review the specific values in the next step before drawing conclusions."
    
    return summary
