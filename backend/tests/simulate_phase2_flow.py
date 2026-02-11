import sys
import os
import json
from datetime import date

# Add parent directory to path (backend root)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.case_state import CaseState
from app.engine.orchestrator import get_next_question
from app.engine.extractor import extract_clinical_state

def simulate_flow():
    print("--- Simulating Phase 2 Flow ---")
    
    # 1. Setup Initial State (End of Phase 1)
    state = CaseState()
    state.status = "INTAKE"
    state.confirmation_status = True
    state.tests_done_list = ["AMH", "HSG"]
    state.male_tests_done_list = ["Semen Analysis"]
    
    print(f"\n[Step 0] Initial State: Status={state.status}, Phase={state.phase}")
    
    # 2. Trigger Phase 2 Transition (Orchestrator Turn 1)
    msg, options = get_next_question(state)
    # Orchestrator should set status=PHASE2_START then Phase=PHASE2 and return Intro/Prompt
    print(f"\n[Step 1] Orchestrator Output: {msg}")
    print(f"         State after Step 1: Phase={state.phase}")
    
    # 3. Simulate User Upload (Mocking /upload endpoint effect)
    # User uploads AMH
    print("\n[Step 2] User uploads 'AMH_Report.pdf'...")
    new_doc = {
        "test_name": "AMH",
        "filename": "AMH_Report.pdf",
        "upload_date": date.today().isoformat(),
        "test_date": None,
        "validity_status": None
    }
    state.phase2_documents.append(new_doc)
    
    # Orchestrator Turn 2 (Should ask for date or wait)
    msg, options = get_next_question(state)
    print(f"Orchestrator: {msg}")
    
    # 4. Simulate User Providing Date
    print("\n[Step 3] User says: 'It was done in Jan 2024'")
    updates = extract_clinical_state("It was done in Jan 2024", state.dict())
    print(f"Extractor Updates: {updates}")
    
    # Apply updates
    if "phase2_documents" in updates:
        state.phase2_documents = [dict(d) for d in updates["phase2_documents"]] # Reconstruct as dicts if needed
        
    # Orchestrator Turn 3 (Should ask for next doc or wait)
    msg, options = get_next_question(state)
    print(f"Orchestrator: {msg}")
    
    # 5. Simulate "Done Uploading"
    print("\n[Step 4] User says: 'Done uploading'")
    updates = extract_clinical_state("Done uploading", state.dict())
    print(f"Extractor Updates: {updates}")
    if "phase2_uploads_complete" in updates:
        state.phase2_uploads_complete = updates["phase2_uploads_complete"]
        
    # Orchestrator Turn 4 (Should Run Validity & Return Summary)
    msg, options = get_next_question(state)
    print(f"Orchestrator: {msg}")
    print(f"Final Phase 2 Verification Status: {state.phase2_verification_complete}")

if __name__ == "__main__":
    simulate_flow()
