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
    
    # 1. LLM Extraction (DISABLED due to 404 errors - Relying on robust heuristics)
    # try:
    #     response = model.generate_content([system_prompt, user_content])
    #     cleaned_text = response.text.strip()
    #     if "```json" in cleaned_text:
    #         cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
    #     extracted_data = json.loads(cleaned_text)
    # except Exception as e:
    #     print(f"Gemini Extraction Failed: {e}")

    # 2. Heuristic Augmentation (Safety Layer)
    
    # Partner Status
    if re.search(r'\b(partner|husband|wife|spouse)\b', message, re.IGNORECASE):
        # Negative lookbehind/lookahead wrapper or simpler check
        if not re.search(r'\b(no|without|not)\s+(partner|husband|wife|spouse)\b', message, re.IGNORECASE):
            extracted_data["male_partner_type"] = "Partner"
            extracted_data["male_partner_present"] = True
    elif re.search(r'\b(donor|donor sperm|conception using a donor)\b', message, re.IGNORECASE):
        extracted_data["male_partner_type"] = "Donor"
        extracted_data["male_partner_present"] = False
    elif re.search(r'\b(exploring|not sure|unsure)\b', message, re.IGNORECASE):
        extracted_data["male_partner_type"] = "Unsure"
        extracted_data["male_partner_present"] = False

    # Ages
    if "days" in message.lower() or "cycle" in message.lower():
        pass # Skip age extraction if discussing cycles/days explicitly
    elif current_state.get("female_age") is None or current_state.get("male_age") is None:
        # Handle explicit "Female is X, Male is Y" format (Ambiguity Resolution)
        female_explicit = re.search(r'Female is (\d+)', message, re.IGNORECASE)
        male_explicit = re.search(r'Male is (\d+)', message, re.IGNORECASE)
        
        if female_explicit and male_explicit:
            extracted_data["female_age"] = int(female_explicit.group(1))
            extracted_data["male_age"] = int(male_explicit.group(1))
            extracted_data["unclear_age_ownership"] = []
            
        else:
            # Fallback to standard extraction
            nums = re.findall(r'\b\d{2}\b', message)
            if len(nums) >= 2:
                self_match = re.search(r'\b(i am|i\'m|im|my age is|me)\s*(?:is)?\s*(\d{2})', message, re.IGNORECASE)
                partner_match = re.search(r'\b(husband|he|partner|spouse|she)(?:\'s)?\s*(?:age)?\s*(?:is)?\s*(\d{2})', message, re.IGNORECASE)
                
                if self_match and partner_match:
                     extracted_data["female_age"] = int(self_match.group(2))
                     extracted_data["male_age"] = int(partner_match.group(2))
                     extracted_data["unclear_age_ownership"] = []
                else:
                     if current_state.get("male_partner_present") is not False: 
                        extracted_data["unclear_age_ownership"] = [int(n) for n in nums[:2]]
            elif len(nums) == 1:
                val = int(nums[0])
                if re.search(r'\b(i am|i\'m|im|me)\b', message, re.IGNORECASE):
                    extracted_data["female_age"] = val
                elif re.search(r'\b(partner|he|husband|spouse)\b', message, re.IGNORECASE):
                    extracted_data["male_age"] = val
                else:
                    if current_state.get("male_partner_present") is False:
                        extracted_data["female_age"] = val
                    elif current_state.get("female_age"):
                        extracted_data["male_age"] = val
                    else:
                        extracted_data["female_age"] = val

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

    # Relationship (Partner Context)
    if current_state.get("male_age") and current_state.get("first_marriage") is None:
        if re.search(r'\b(yes|yeah|yep)\b', message, re.IGNORECASE):
            extracted_data["first_marriage"] = True
        elif re.search(r'\b(no|nope)\b', message, re.IGNORECASE):
            extracted_data["first_marriage"] = False
    elif "marriage" in message.lower(): 
        if re.search(r'\b(yes|yeah)\b', message, re.IGNORECASE):
            extracted_data["first_marriage"] = True
        elif re.search(r'\b(no|nope)\b', message, re.IGNORECASE):
            extracted_data["first_marriage"] = False
    
    # Years Married
    just_extracted_marriage = False
    if current_state.get("first_marriage") is not None and current_state.get("years_married") is None:
        yr_match = re.search(r'(\d+(?:\.\d+)?)\s*years?', message, re.IGNORECASE)
        if yr_match:
             extracted_data["years_married"] = float(yr_match.group(1))
             just_extracted_marriage = True
        else:
             solitary = re.search(r'^\s*(\d+(?:\.\d+)?)\s*$', message)
             if solitary: 
                 extracted_data["years_married"] = float(solitary.group(1))
                 just_extracted_marriage = True

    # Duration
    is_post_duration_step = current_state.get("has_prior_pregnancies") is not None
    should_parse_duration = False
    
    if "trying" in message.lower() or "conceiv" in message.lower():
        should_parse_duration = True
    elif not just_extracted_marriage and not is_post_duration_step:
        should_parse_duration = True
        
    if should_parse_duration:
        if re.search(r'\b(0|zero|not yet|never)\b', message, re.IGNORECASE):
            extracted_data["years_trying"] = 0.0
            extracted_data["pending_duration_value"] = None
        else:
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
                    if "years_married" not in extracted_data:
                        extracted_data["pending_duration_value"] = float(solitary_num.group(1))

    # Pregnancy
    if current_state.get("years_trying") is not None and current_state.get("has_prior_pregnancies") is None:
        if re.search(r'\b(yes|yeah|yep)\b', message, re.IGNORECASE):
             extracted_data["has_prior_pregnancies"] = True
        elif re.search(r'\b(no|nope)\b', message, re.IGNORECASE):
             extracted_data["has_prior_pregnancies"] = False
    elif re.search(r'\b(yes|yeah|yep)\b', message, re.IGNORECASE) and current_state.get("has_prior_pregnancies") is None:
         pass 

    if "natural" in message.lower(): extracted_data["pregnancy_source"] = "Natural"
    if "treatment" in message.lower(): extracted_data["pregnancy_source"] = "Treatment"
    for outcome in ["miscarriage", "ectopic", "chemical", "ongoing", "live birth"]:
        if outcome in message.lower():
            extracted_data["pregnancy_outcome"] = outcome.capitalize()

    # Menstrual History
    if current_state.get("has_prior_pregnancies") is not None and current_state.get("menstrual_regularity") is None:
        if re.search(r'\b(yes|yeah|regular)\b', message, re.IGNORECASE) and "ir" not in message.lower():
            extracted_data["menstrual_regularity"] = "Regular"
        elif re.search(r'\b(no|nope|irregular|varies)\b', message, re.IGNORECASE):
            extracted_data["menstrual_regularity"] = "Irregular"
        elif "not sure" in message.lower():
             extracted_data["menstrual_regularity"] = "NotSure"
    elif "regular" in message.lower() and "ir" not in message.lower():
        extracted_data["menstrual_regularity"] = "Regular"
    elif "irregular" in message.lower() or "varies" in message.lower():
        extracted_data["menstrual_regularity"] = "Irregular"
    
    # Cycle Length
    if re.search(r'\b(21|26|31)[-–—to\s]+', message, re.IGNORECASE): 
         extracted_data["cycle_length"] = message.strip()
    
    # Predictability
    if "predictabl" in message.lower() or (current_state.get("cycle_length") and current_state.get("cycle_predictability") is None):
         if re.search(r'\b(yes|yeah)\b', message, re.IGNORECASE): extracted_data["cycle_predictability"] = True
         if re.search(r'\b(no|nope)\b', message, re.IGNORECASE): extracted_data["cycle_predictability"] = False

    # Menarche
    if "first period" in message.lower() or (current_state.get("cycle_predictability") is not None and current_state.get("menarche_age") is None):
         num = re.search(r'(\d{2})', message)
         if num: extracted_data["menarche_age"] = num.group(1)

    # Sexual History
    if "difficulty" in message.lower():
        if "without" in message.lower(): extracted_data["sexual_difficulty"] = "None"
        elif "sometimes" in message.lower(): extracted_data["sexual_difficulty"] = "Sometimes"
        elif "rarely" in message.lower(): extracted_data["sexual_difficulty"] = "Rarely"
    elif "not applicable" in message.lower():
        extracted_data["sexual_difficulty"] = "NotApplicable"
    elif current_state.get("menarche_age") and current_state.get("sexual_difficulty") is None:
        if "without" in message.lower() or "yes" in message.lower():
             extracted_data["sexual_difficulty"] = "None"
        elif "sometimes" in message.lower(): extracted_data["sexual_difficulty"] = "Sometimes"
        elif "rarely" in message.lower(): extracted_data["sexual_difficulty"] = "Rarely"
        elif "not applicable" in message.lower(): extracted_data["sexual_difficulty"] = "NotApplicable"

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
            
    # IVF Details (Fresh/Frozen & Outcome)
    if current_state.get("treatment_type") == "IVF" and current_state.get("ivf_cycles"):
        if "fresh" in message.lower():
            extracted_data["last_ivf_transfer_type"] = "Fresh"
        elif "frozen" in message.lower():
            extracted_data["last_ivf_transfer_type"] = "Frozen"
            
        if "beta negative" in message.lower() or "negative" in message.lower():
            extracted_data["last_ivf_outcome"] = "Beta Negative"
        elif "biochemical" in message.lower() or "chemical" in message.lower():
            extracted_data["last_ivf_outcome"] = "Biochemical Pregnancy"
        elif "miscarriage" in message.lower():
            extracted_data["last_ivf_outcome"] = "Miscarriage"
        elif "ectopic" in message.lower():
            extracted_data["last_ivf_outcome"] = "Ectopic Pregnancy"
        elif "ongoing" in message.lower():
            extracted_data["last_ivf_outcome"] = "Ongoing Pregnancy"
        elif "live birth" in message.lower() or "baby" in message.lower():
            extracted_data["last_ivf_outcome"] = "Live Birth"

    # Tests (Female & Male Context Aware)
    tests_map = {
        "hormonal": "Hormonal blood tests (AMH, TSH, FSH/LH)", 
        "ultrasound": "Ultrasound scans", 
        "tube": "Tube testing (HSG / Laparoscopy / HyCoSy)",
        "hsg": "Tube testing (HSG / Laparoscopy / HyCoSy)",
        "laparoscopy": "Tube testing (HSG / Laparoscopy / HyCoSy)"
    }
    
    male_keywords = ["semen", "partner", "his"]
    is_explicit_male = any(kw in message.lower() for kw in male_keywords)
    
    is_implicit_male_step = current_state.get("tests_reviewed") is True
    
    if is_explicit_male or is_implicit_male_step:
        male_tests = []
        if "semen" in message.lower(): male_tests.append("Semen analysis")
        if "hormonal" in message.lower(): male_tests.append("Hormonal blood tests")
        if "genetic" in message.lower(): male_tests.append("Genetic tests")
        if "none" in message.lower(): male_tests.append("None")
        
        if male_tests:
            extracted_data["male_tests_done_list"] = male_tests
    else:
        found_tests = [label for kw, label in tests_map.items() if kw in message.lower()]
        if found_tests:
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
         if current_state.get("reports_availability_checked") or (current_state.get("tests_reviewed") and not current_state.get("tests_done_list")):
              extracted_data["confirmation_status"] = True

    # --- PHASE 1 REFINEMENT: Test Date Extraction ---
    if current_state.get("active_date_inquiry"):
        test_name = current_state["active_date_inquiry"]
        date_str = None
        
        # Reuse Regex from Phase 2
        # Month Year (Jan 2024 or January 2024)
        mon_yr = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.-]+(\d{4})', message, re.IGNORECASE)
        # Full Date (DD/MM/YYYY or similar)
        full_date = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', message)
        # Year only
        year_only = re.search(r'\b(20\d{2})\b', message)
        
        if mon_yr:
            months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
            m_str = mon_yr.group(1).lower()[:3]
            m_idx = months.index(m_str) + 1
            y_str = mon_yr.group(2)
            date_str = f"{y_str}-{m_idx:02d}-01" # Default to 1st
        elif full_date:
            d, m, y = full_date.group(1), full_date.group(2), full_date.group(3)
            if len(y) == 2: y = "20" + y
            date_str = f"{y}-{int(m):02d}-{int(d):02d}"
        elif year_only:
            date_str = f"{year_only.group(1)}-01-01"
        elif "last month" in message.lower():
            from datetime import date, timedelta
            today = date.today()
            d = today - timedelta(days=30)
            date_str = d.isoformat()
            
        if date_str:
            # We need to update the dictionary `reported_test_dates`
            # CaseState stores it as a Dict. 
            # We need to make sure we don't overwrite existing if multi-turn? 
            # Extractor returns partial updates.
            # We need to get the existing dict from state, update it, and return new dict.
            existing_dates = current_state.get("reported_test_dates", {})
            # Ensure it's a dict (pydantic model conversion might leave it as is?)
            if not isinstance(existing_dates, dict): existing_dates = {}
            
            existing_dates[test_name] = date_str
            extracted_data["reported_test_dates"] = existing_dates
            
            # Note: We do NOT clear `active_date_inquiry` here. Orchestrator checks if date exists.
            
    # --- PHASE 2 EXTRACTION ---
    if current_state.get("phase") == "PHASE2":
        # 1. Check for "Done Uploading" / "No Reports"
        if "done" in message.lower() or "no report" in message.lower() or "do not have" in message.lower():
            extracted_data["phase2_uploads_complete"] = True
            
        # 2. Extract Dates for Pending Documents
        # Find doc with missing date
        docs = current_state.get("phase2_documents", [])
        pending_doc_idx = -1
        # Safe iteration
        if docs:
            for i, doc in enumerate(docs):
                is_dict = isinstance(doc, dict)
                val = doc.get("test_date") if is_dict else getattr(doc, "test_date", None)
                
                if val is None:
                    pending_doc_idx = i
                    break
        
        if pending_doc_idx != -1:
            date_str = None
            
            # Month Year (Jan 2024 or January 2024)
            mon_yr = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.-]+(\d{4})', message, re.IGNORECASE)
            # Full Date (DD/MM/YYYY)
            full_date = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', message)
            # Year only
            year_only = re.search(r'\b(20\d{2})\b', message)
            
            if mon_yr:
                months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
                m_str = mon_yr.group(1).lower()[:3]
                m_idx = months.index(m_str) + 1
                y_str = mon_yr.group(2)
                date_str = f"{y_str}-{m_idx:02d}-01"
            elif full_date:
                d, m, y = full_date.group(1), full_date.group(2), full_date.group(3)
                if len(y) == 2: y = "20" + y
                date_str = f"{y}-{int(m):02d}-{int(d):02d}"
            elif year_only:
                date_str = f"{year_only.group(1)}-01-01"
            elif "last month" in message.lower():
                from datetime import date, timedelta
                today = date.today()
                d = today - timedelta(days=30)
                date_str = d.isoformat()
            
            if date_str:
                updated_docs = list(docs)
                if isinstance(updated_docs[pending_doc_idx], dict):
                     updated_docs[pending_doc_idx]["test_date"] = date_str
                else: 
                     try:
                        d_dict = updated_docs[pending_doc_idx].dict()
                     except AttributeError:
                        d_dict = dict(updated_docs[pending_doc_idx])
                     
                     d_dict["test_date"] = date_str
                     updated_docs[pending_doc_idx] = d_dict
                     
                extracted_data["phase2_documents"] = updated_docs

    return extracted_data