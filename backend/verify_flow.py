import sys
import os
import json
from pathlib import Path

# Add backend to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.case_state import CaseState
from app.engine.extractor import extract_clinical_state
from app.engine.orchestrator import get_next_question

def run_simulation():
    print("--- STARTING HEADLESS SIMULATION ---")
    
    # Step 1: Init
    state = CaseState()
    print("\n[1] Initial State Created.")
    
    # Step 2: Get First Question
    q1 = get_next_question(state)
    print(f"Bot Q1: {q1}")
    # assert "start with ages" in q1.lower() or "how old are you" in q1.lower()
    
    # Step 3: User Reply (The "Ideal Flow" Example)
    user_reply_1 = "I am 32, husband is 34"
    print(f"User  : {user_reply_1}")
    
    # Step 4: Extract
    extracted_1 = extract_clinical_state(user_reply_1, state.model_dump())
    state.update_from_json(extracted_1)
    print(f"State Update: Female={state.demographics.female_age}, Male={state.demographics.male_age}")
    
    # Step 5: Get Second Question
    q2 = get_next_question(state)
    print(f"Bot Q2: {q2}")
    # Expect Duration question
    assert "how long" in q2.lower()
    
    # Step 6: User Reply
    user_reply_2 = "2 years"
    print(f"User  : {user_reply_2}")
    
    # Step 7: Update
    extracted_2 = extract_clinical_state(user_reply_2, state.model_dump())
    state.update_from_json(extracted_2)
    print(f"State Update: Years Trying={state.fertility_timeline.years_trying}")
    
    # Step 8: Get Third Question
    q3 = get_next_question(state)
    print(f"Bot Q3: {q3}")
    # Expect Pregnancy question
    assert "pregnant before" in q3.lower() or "pregnancy" in q3.lower()

    print("\n--- SIMULATION SUCCESS: Doctor-Led Flow Verified ---")

if __name__ == "__main__":
    run_simulation()
