import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

print("Checking imports...")
try:
    from app.models.case_state import CaseState
    print("✅ models.case_state imported")
    
    from app.engine.extractor import extract_clinical_state
    print("✅ engine.extractor imported")
    
    from app.engine.orchestrator import get_next_question
    print("✅ engine.orchestrator imported")
    
    from app.engine.summary import generate_section_a
    print("✅ engine.summary imported")
    
    from app.main import app
    print("✅ main app imported")
    
    print("ALL MODULES VALID.")
except Exception as e:
    print(f"❌ IMPORT ERROR: {e}")
    sys.exit(1)
