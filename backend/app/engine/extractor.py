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
    
    # 2. Heuristic Augmentation (Safety Layer)
    
    # Partner Status
    # Fix: Ensure we don't match "no partner" as "Partner"
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
    # Global Guard: Only extract ages if we are missing them.
    # Exception: Explicit Ambiguity Resolution (we check regardless of missing or not, incase user is correcting).
    # BUT, we must be careful not to pick up dates/cycle lengths.
    
    # Fix: Ignore "days" context (e.g. 21-25 days)
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
                     # Only flag ambiguity if we reasonably think these are ages. 
                     # If Donor flow, we shouldn't care about 2 ages.
                     if current_state.get("male_partner_present") is not False: 
                        extracted_data["unclear_age_ownership"] = [int(n) for n in nums[:2]]
            elif len(nums) == 1:
                val = int(nums[0])
                # Check explicit pronouns first
                if re.search(r'\b(i am|i\'m|im|me)\b', message, re.IGNORECASE):
                    extracted_data["female_age"] = val
                elif re.search(r'\b(partner|he|husband|spouse)\b', message, re.IGNORECASE):
                    extracted_data["male_age"] = val
                else:
                    # No explicit pronouns. Check context.
                    # If Donor flow (no partner), it must be Female Age.
                    if current_state.get("male_partner_present") is False:
                        extracted_data["female_age"] = val
                    # If Partner flow, and Female Age exists, assume Male Age.
                    elif current_state.get("female_age"):
                        extracted_data["male_age"] = val
                    # If Partner flow, and Female Age missing, assume Female Age (Agent usually asks Female first).
                    # But risk of ambiguity if user says "He is 25". (Covered by elif above).
                    # So if no pronouns and no female age, assume Female Age.
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
    # Context-Aware Heuristic
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
             # Solitary number fallback
             solitary = re.search(r'^\s*(\d+(?:\.\d+)?)\s*$', message)
             if solitary: 
                 extracted_data["years_married"] = float(solitary.group(1))
                 just_extracted_marriage = True

    # Duration
    # STRICT CONTEXT GUARD:
    # Do NOT extract duration if:
    # 1. We just extracted years_married (it's the same number, e.g. "3 years").
    # 2. We are past the pregnancy step (e.g. answering Menarche logic "16 years").
    #    - Proxy: has_prior_pregnancies is NOT None.
    #    - Unless explicit "trying" keyword is used.
    
    is_post_duration_step = current_state.get("has_prior_pregnancies") is not None
    should_parse_duration = False
    
    if "trying" in message.lower() or "conceiv" in message.lower():
        should_parse_duration = True # Keyword override
    elif not just_extracted_marriage and not is_post_duration_step:
        should_parse_duration = True # Standard flow context (between Marriage and Pregnancy)
        
    if should_parse_duration:
        # Zero Duration Handling
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
                # Ambiguity check: Only if solitary and fitting context
                if solitary_num and current_state.get("female_age") and current_state.get("years_trying") is None:
                    if "years_married" not in extracted_data:
                        extracted_data["pending_duration_value"] = float(solitary_num.group(1))

    # Pregnancy
    # Context: Duration known, has_prior_pregnancies None
    if current_state.get("years_trying") is not None and current_state.get("has_prior_pregnancies") is None:
        if re.search(r'\b(yes|yeah|yep)\b', message, re.IGNORECASE):
             extracted_data["has_prior_pregnancies"] = True
        elif re.search(r'\b(no|nope)\b', message, re.IGNORECASE):
             extracted_data["has_prior_pregnancies"] = False
    # Keyword fallback
    elif re.search(r'\b(yes|yeah|yep)\b', message, re.IGNORECASE) and current_state.get("has_prior_pregnancies") is None:
         # Safer to only do this if "pregnancy" mentioned? No, prompts are "Has there ever...?" -> "Yes"
         # So we keep it but beware collisions.
         pass 

    if "natural" in message.lower(): extracted_data["pregnancy_source"] = "Natural"
    if "treatment" in message.lower(): extracted_data["pregnancy_source"] = "Treatment"
    for outcome in ["miscarriage", "ectopic", "chemical", "ongoing", "live birth"]:
        if outcome in message.lower():
            extracted_data["pregnancy_outcome"] = outcome.capitalize()

    # Menstrual History
    # Regularity
    # Context: Pregnancy history known (Step 5 done), Regularity None (Step 6 pending)
    if current_state.get("has_prior_pregnancies") is not None and current_state.get("menstrual_regularity") is None:
        if re.search(r'\b(yes|yeah|regular)\b', message, re.IGNORECASE) and "ir" not in message.lower():
            extracted_data["menstrual_regularity"] = "Regular"
        elif re.search(r'\b(no|nope|irregular|varies)\b', message, re.IGNORECASE):
            extracted_data["menstrual_regularity"] = "Irregular"
        elif "not sure" in message.lower():
             extracted_data["menstrual_regularity"] = "NotSure"
    # Keyword matches (fallback)
    elif "regular" in message.lower() and "ir" not in message.lower():
        extracted_data["menstrual_regularity"] = "Regular"
    elif "irregular" in message.lower() or "varies" in message.lower():
        extracted_data["menstrual_regularity"] = "Irregular"
    
    # Cycle Length
    # Handle different dash types (hyphen -, en-dash –, em-dash —)
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
    # Context: Menarche known (Step 6 Done), Sexual Difficulty None (Step 6E Pending)
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

    # Tests (Female & Male Context Aware)
    tests_map = {
        "hormonal": "Hormonal blood tests (AMH, TSH, FSH/LH)", 
        "ultrasound": "Ultrasound scans", 
        "tube": "Tube testing (HSG / Laparoscopy / HyCoSy)",
        "hsg": "Tube testing (HSG / Laparoscopy / HyCoSy)",
        "laparoscopy": "Tube testing (HSG / Laparoscopy / HyCoSy)"
    }
    
    # Are we in Message context (explicit keywords)?
    male_keywords = ["semen", "partner", "his"]
    is_explicit_male = any(kw in message.lower() for kw in male_keywords)
    
    # Context Check: If tests_reviewed is True, assume we are now answering Male Tests (if Partner flow)
    # Note: Extractor doesn't know flow type easily, but tests_reviewed=True implies Female done.
    is_implicit_male_step = current_state.get("tests_reviewed") is True
    
    if is_explicit_male or is_implicit_male_step:
        # Male Tests Logic
        male_tests = []
        if "semen" in message.lower(): male_tests.append("Semen analysis")
        if "hormonal" in message.lower(): male_tests.append("Hormonal blood tests")
        if "genetic" in message.lower(): male_tests.append("Genetic tests")
        if "none" in message.lower(): male_tests.append("None")
        
        # Only update if we found something or context strongly implies it
        if male_tests:
            # Append if exists? No, usually comprehensive answer.
            # If implicit step, assume overwriting or appending.
            # Let's overwrite for simplicity unless partial.
            extracted_data["male_tests_done_list"] = male_tests
    else:
        # Female Tests (default)
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

    return extracted_data