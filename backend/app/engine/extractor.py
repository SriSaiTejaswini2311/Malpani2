import os
import json
import re
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def extract_clinical_state(message: str, current_state: dict):
    system_prompt = """
    You are an IVF Clinical Data Extractor. Update the JSON state.
    
    STRICT VARIABLE MAPPING (Must match Pydantic Model):
    1. AGES:
       - 'I am 25' -> demographics.female_age = 25.
       - 'Husband is 30' -> demographics.male_age = 30.
       - 'Partner is 29' (neutral) -> demographics.unclear_age_ownership = [25, 29].
    
    2. DURATION (years_trying):
       - '2 years' -> fertility_timeline.years_trying = 2.0
       - '6 months' -> fertility_timeline.years_trying = 0.5
       - 'Since 2020' (if now 2025) -> fertility_timeline.years_trying = 5.0

    3. TESTS / PREGNANCY:
       - 'No' to reports/tests -> set 'reports_availability_checked' or 'tests_reviewed' to True.
       - 'No' to pregnancy -> has_prior_pregnancies = False.

    OUTPUT FORMAT:
    {
        "demographics": {
            "female_age": 25,
            "male_age": 30,
            "unclear_age_ownership": []
        },
        "fertility_timeline": {
            "years_trying": 2.0
        },
        "treatments": {
            "ivf": {"done": false, "total_cycles": 1},
            "iui": {"done": true, "count": 2}
        }
    }
    Return ONLY raw valid JSON.
    """

    user_content = f"State: {json.dumps(current_state)}\nMessage: {message}"
    
    # Init model
    model = genai.GenerativeModel('gemini-pro', 
                                  generation_config={"response_mime_type": "application/json"})

    # --- 1. LLM EXTRACTION ---
    extracted_data = {}
    try:
        response = model.generate_content([system_prompt, user_content])
        cleaned_text = response.text.strip()
        if "```json" in cleaned_text:
            cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
        
        extracted_data = json.loads(cleaned_text)
        print(f"DEBUG GEMINI RAW: {json.dumps(extracted_data)}")
    except Exception as e:
        print(f"Gemini Extraction Failed: {e}")
        extracted_data = {}

    # --- 2. HEURISTIC ENHANCEMENT (REGEX) ---
    # Always run this to catch things LLM might miss, especially for short answers.
    print("Running Heuristic Augmentation...")
    
    # Init sub-dicts if missing
    if "demographics" not in extracted_data: extracted_data["demographics"] = {}
    if "fertility_timeline" not in extracted_data: extracted_data["fertility_timeline"] = {}
    
    # A. AGES
    # 1. Matches "I am 24", "I'm 25", "Im 26", "Me 27" -> Female Age
    # using flexible whitespace and optional words
    if not extracted_data["demographics"].get("female_age"):
        self_match = re.search(r'\b(i am|i\'m|im|my age is|me)\s*(?:is)?\s*(\d{2})', message, re.IGNORECASE)
        if self_match:
            extracted_data["demographics"]["female_age"] = int(self_match.group(2))
        
    # 2. Matches "Husband/Partner is 28", "Husband's age is 29" -> Male Age
    if not extracted_data["demographics"].get("male_age"):
        # Match 'husband', 'partner', 'spouse', 'he' followed by some text then digits
        partner_match = re.search(r'\b(husband|he|partner|spouse|wife|she)(?:\'s)?\s*(?:age)?\s*(?:is)?\s*(\d{2})', message, re.IGNORECASE)
        if partner_match:
            extracted_data["demographics"]["male_age"] = int(partner_match.group(2))
    
    # B. DURATION
    # Matches: "2 years", "1.5 years", "6 months"
    years_match = re.search(r'(\d+(?:\.\d+)?)\s*years?', message, re.IGNORECASE)
    if years_match and not extracted_data["fertility_timeline"].get("years_trying"):
        extracted_data["fertility_timeline"]["years_trying"] = float(years_match.group(1))
    
    months_match = re.search(r'(\d+)\s*months?', message, re.IGNORECASE)
    if months_match and not extracted_data["fertility_timeline"].get("years_trying"):
        extracted_data["fertility_timeline"]["years_trying"] = float(months_match.group(1)) / 12.0

    # C. CONTEXTUAL 'NO'
    negative_match = re.search(r'\b(no|nope|never|not really|none)\b', message, re.IGNORECASE)
    if negative_match:
        # Check missing fields in order
        if current_state.get("has_prior_pregnancies") is None and "has_prior_pregnancies" not in extracted_data:
            extracted_data["has_prior_pregnancies"] = False
        
        elif current_state.get("treatments", {}).get("ivf", {}).get("done") is None:
            if "treatments" not in extracted_data: extracted_data["treatments"] = {}
            if "ivf" not in extracted_data["treatments"]: extracted_data["treatments"]["ivf"] = {}
            if extracted_data["treatments"]["ivf"].get("done") is None:
                extracted_data["treatments"]["ivf"]["done"] = False
            extracted_data["has_had_treatments"] = False
            extracted_data["treatments_reviewed"] = True
        
        elif current_state.get("tests_reviewed") is False:
             extracted_data["tests_reviewed"] = True
             extracted_data["demographics"]["all_tests_none"] = True
        
        elif current_state.get("reports_availability_checked") is False:
             extracted_data["reports_availability_checked"] = True

    # D. CONTEXTUAL 'YES' (Breaking the Loop)
    affirmative_match = re.search(r'\b(yes|yeah|sure|yep|correct)\b', message, re.IGNORECASE)
    if affirmative_match:
         # If asking about treatments (and ivf.done is None), mark distinct generic flag.
         if current_state.get("treatments", {}).get("ivf", {}).get("done") is None:
             if current_state.get("has_had_treatments") is None:
                  extracted_data["has_had_treatments"] = True
         
         # Fallback for Tests: if we are at tests stage and user says yes, assuming "some tests done"
         if current_state.get("treatments_reviewed") is True and current_state.get("tests_reviewed") is False:
              # This triggers the "which tests?" follow up in orchestrator if needed
              pass

    print(f"DEBUG FINAL EXTRACTED: {json.dumps(extracted_data)}")
    return extracted_data