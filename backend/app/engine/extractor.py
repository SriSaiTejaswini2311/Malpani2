import os
import json
import re
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, Any

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def extract_clinical_state(message: str, current_state: Dict) -> Dict:
    """
    HEURISTIC EXTRACTOR (PHASE 1 - FINAL SPEC)
    Parses user messages to update the flattened CaseState.
    """
    
    system_prompt = """
    You are an IVF Clinical Data Extractor. Update the flattened JSON state.
    
    FIELDS TO EXTRACT (Return as flat keys):
    - male_partner_type: "Partner", "Donor", "Unsure"
    - male_partner_present: bool
    - female_age: int
    - male_age: int
    - years_trying: float
    - has_prior_pregnancies: bool
    - pregnancy_source: "Natural", "Treatment", "NotSure"
    - pregnancy_outcome: "Miscarriage", "Ectopic", "Ongoing", "Live birth"
    - treatment_type: "IVF", "IUI", "Medications", "None"
    - ivf_cycles: int
    - iui_cycles: int
    - tests_done_list: list of strings
    - reports_availability: "Yes", "No", "Some"
    - confirmation_status: bool
    
    OUTPUT FORMAT:
    Return flat JSON keys ONLY.
    """

    user_content = f"Current State: {json.dumps(current_state)}\nUser Message: {message}"
    
    model = genai.GenerativeModel('gemini-1.5-flash', 
                                  generation_config={"response_mime_type": "application/json"})

    extracted_data = {}
    
    # 1. LLM Extraction
    try:
        response = model.generate_content([system_prompt, user_content])
        cleaned_text = response.text.strip()
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
        extracted_data = json.loads(cleaned_text)
    except Exception as e:
        print(f"Gemini Extraction Failed: {e}")

    # 2. Heuristic Augmentation (Safety Layer)
    
    # Partner Status
    if re.search(r'\b(partner|husband|wife|spouse)\b', message, re.IGNORECASE):
        extracted_data["male_partner_type"] = "Partner"
        extracted_data["male_partner_present"] = True
    elif re.search(r'\b(donor|donor sperm|conception using a donor)\b', message, re.IGNORECASE):
        extracted_data["male_partner_type"] = "Donor"
        extracted_data["male_partner_present"] = False
    elif re.search(r'\b(exploring|not sure|unsure)\b', message, re.IGNORECASE):
        extracted_data["male_partner_type"] = "Unsure"
        extracted_data["male_partner_present"] = False

    # Ages
    nums = re.findall(r'\b\d{2}\b', message)
    if len(nums) >= 2:
        self_match = re.search(r'\b(i am|i\'m|im|my age is|me)\s*(?:is)?\s*(\d{2})', message, re.IGNORECASE)
        partner_match = re.search(r'\b(husband|he|partner|spouse|she)(?:\'s)?\s*(?:age)?\s*(?:is)?\s*(\d{2})', message, re.IGNORECASE)
        
        if self_match and partner_match:
             extracted_data["female_age"] = int(self_match.group(2))
             extracted_data["male_age"] = int(partner_match.group(2))
        else:
             extracted_data["unclear_age_ownership"] = [int(n) for n in nums[:2]]
    elif len(nums) == 1:
        val = int(nums[0])
        if re.search(r'\b(i am|i\'m|im|me)\b', message, re.IGNORECASE):
            extracted_data["female_age"] = val
        elif re.search(r'\b(partner|he|husband|spouse)\b', message, re.IGNORECASE) or current_state.get("female_age"):
            extracted_data["male_age"] = val

    # Ambiguity clarification
    if "first is mine" in message.lower():
        ambig = current_state.get("unclear_age_ownership", [])
        if len(ambig) >= 2:
            extracted_data["female_age"], extracted_data["male_age"] = ambig[0], ambig[1]
            extracted_data["unclear_age_ownership"] = []
    elif "second is mine" in message.lower():
        ambig = current_state.get("unclear_age_ownership", [])
        if len(ambig) >= 2:
            extracted_data["female_age"], extracted_data["male_age"] = ambig[1], ambig[0]
            extracted_data["unclear_age_ownership"] = []

    # Duration
    yr_match = re.search(r'(\d+(?:\.\d+)?)\s*years?', message, re.IGNORECASE)
    mo_match = re.search(r'(\d+)\s*months?', message, re.IGNORECASE)
    if yr_match:
        extracted_data["years_trying"] = float(yr_match.group(1))
        extracted_data["pending_duration_value"] = None
    elif mo_match:
        extracted_data["years_trying"] = float(mo_match.group(1)) / 12.0
        extracted_data["pending_duration_value"] = None
    else:
        solitary_num = re.search(r'^\s*(\d+(?:\.\d+)?)\s*$', message)
        if solitary_num and current_state.get("female_age") and current_state.get("years_trying") is None:
            extracted_data["pending_duration_value"] = float(solitary_num.group(1))

    # Pregnancy
    if re.search(r'\b(yes|yeah|yep)\b', message, re.IGNORECASE) and current_state.get("has_prior_pregnancies") is None:
         extracted_data["has_prior_pregnancies"] = True
    elif re.search(r'\b(no|nope)\b', message, re.IGNORECASE) and current_state.get("has_prior_pregnancies") is None:
         extracted_data["has_prior_pregnancies"] = False
    
    if "natural" in message.lower(): extracted_data["pregnancy_source"] = "Natural"
    if "treatment" in message.lower(): extracted_data["pregnancy_source"] = "Treatment"
    for outcome in ["miscarriage", "ectopic", "ongoing", "live birth"]:
        if outcome in message.lower():
            extracted_data["pregnancy_outcome"] = outcome.capitalize()

    # Treatments
    if "ivf" in message.lower():
        extracted_data["has_had_treatments"] = True
        extracted_data["treatment_type"] = "IVF"
        extracted_data["treatments_reviewed"] = True
    elif "iui" in message.lower():
        extracted_data["has_had_treatments"] = True
        extracted_data["treatment_type"] = "IUI"
        extracted_data["treatments_reviewed"] = True
    elif "no treatments" in message.lower() or "no treatment" in message.lower():
        extracted_data["has_had_treatments"] = False
        extracted_data["treatment_type"] = "None"
        extracted_data["treatments_reviewed"] = True

    # Cycles
    cycles_match = re.search(r'(\d+)\s*cycles', message, re.IGNORECASE)
    if cycles_match:
        if extracted_data.get("treatment_type") == "IVF" or current_state.get("treatment_type") == "IVF":
            extracted_data["ivf_cycles"] = int(cycles_match.group(1))
        else:
            extracted_data["iui_cycles"] = int(cycles_match.group(1))

    # Tests
    tests_map = {"hormonal": "Hormonal blood tests", "ultrasound": "Ultrasound scans", "tube": "Tube testing (HSG / similar)", "hsg": "Tube testing (HSG / similar)", "semen": "Semen analysis"}
    found_tests = [label for kw, label in tests_map.items() if kw in message.lower()]
    if found_tests:
        # Avoid overwriting existing list if it's a multi-step conversation, but for now simple update
        extracted_data["tests_done_list"] = found_tests
        extracted_data["tests_reviewed"] = True
    elif "none" in message.lower() and "above" in message.lower():
        extracted_data["tests_done_list"] = ["None"]
        extracted_data["tests_reviewed"] = True

    # Reports
    if "have them" in message.lower():
        extracted_data["reports_availability"] = "Yes"
        extracted_data["reports_availability_checked"] = True
    elif "collect" in message.lower():
        extracted_data["reports_availability"] = "No"
        extracted_data["reports_availability_checked"] = True

    # Confirmation
    if "correct" in message.lower() or "yes" in message.lower():
         if current_state.get("years_trying") and current_state.get("confirmation_status") is None:
              extracted_data["confirmation_status"] = True

    return extracted_data