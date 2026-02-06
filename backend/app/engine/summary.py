import os
import json
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv
from app.models.case_state import CaseState

# 1. Setup Gemini
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def generate_section_a(state: CaseState) -> str:
    """
    Generates the 'Section A' summary using Gemini.
    """
    system_prompt = """
    You are a Medical Scribe assistant to Dr. Malpani.
    Write a concise, bulleted 'Section A' summary of the patient's history based on the provided JSON.

    FORMAT:
    Section A: Preliminary Assessment
    - **Age**: [Female Age] (Partner: [Male Age])
    - **Timeline**: Trying for [Duration]
    - **Obstetric History**: [Summary of pregnancies]
    - **Previous Treatments**: [IVF/IUI details or None]
    - **Tests Status**: [Reviewed/Pending]
    
    TONE: Professional, Objective, Clinical.
    NOTE: If a field is 'None' or 'unclear' in the JSON, explicitly state "Details Pending".
    """
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        user_content = f"PATIENT DATA:\n{json.dumps(state.model_dump(), default=str)}"
        
        response = model.generate_content([system_prompt, user_content])
        return response.text.strip()
        
    except Exception as e:
        print(f"Summary AI Error: {e}")
        return "Error generating AI summary. Please proceed."