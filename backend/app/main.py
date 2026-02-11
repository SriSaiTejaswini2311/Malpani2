from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json

# Internal imports - these files must exist in your /app folders
from app.models.case_state import CaseState
from app.engine.extractor import extract_clinical_state
from app.engine.summary import generate_section_a

app = FastAPI(title="IVF Consultation Engine - Phase 1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Server-side Session Storage
sessions: Dict[str, CaseState] = {}

class ChatResponse(BaseModel):
    reply: str
    options: List[str] = []
    state: Optional[Dict] = None
    multi_select: bool = False

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id
    
    # 1. Get or Create Session
    if session_id not in sessions:
        sessions[session_id] = CaseState(case_id=session_id)
    
    state = sessions[session_id]
    
    # 2. Extract Data from user message
    try:
        current_state_dict = state.dict()
        extracted_updates = extract_clinical_state(req.message, current_state_dict)
        
        # Apply updates to flattened state
        for key, val in extracted_updates.items():
            if hasattr(state, key):
                setattr(state, key, val)
            elif isinstance(val, dict):
                # Handle nested dicts if they appear (e.g. state.demographics)
                # But since we flattened CaseState, we mostly expect direct attributes.
                pass
    except Exception as e:
        print(f"Extraction Error: {e}")

    # 3. Get Next Question from Orchestrator
    from app.engine.orchestrator import get_next_question
    # Expecting tuple: (msg, options, multi_select)
    # But for backward compatibility with older steps, we might need a check, 
    # OR we just updated ALL returns in orchestrator.py?
    # I updated the critical paths. I should check if I missed any.
    # To be safe, let's unpack and handle if length is 2 or 3.
    orc_response = get_next_question(state)
    
    if len(orc_response) == 3:
        reply, options, multi_select = orc_response
    else:
        reply, options = orc_response
        multi_select = False
    
    # 4. Handle Special Signals
    if reply == "SUMMARY_READY":
        summary_text = generate_section_a(state)
        return ChatResponse(
            reply=summary_text,
            options=options, # ["Yes, that’s correct", "No, I’d like to correct something"]
            state=state.dict(),
            multi_select=False
        )
    
    if reply == "CONVERSATION_COMPLETE":
        return ChatResponse(
            reply="Thank you for providing those details. We are now ready to proceed with Phase 2.",
            options=[],
            state=state.dict(),
            multi_select=False
        )

    # 5. Standard Response
    return ChatResponse(
        reply=reply,
        options=options,
        state=state.dict(),
        multi_select=multi_select
    )

from fastapi import UploadFile, File, Form

@app.post("/upload")
async def upload_document(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    # 1. Get Session
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    state = sessions[session_id]
    
    # 2. Detect Test Type
    from app.engine.phase2 import detect_test_type
    test_type = detect_test_type(file.filename)
    
    if test_type == "UNKNOWN_TEST":
        return {
            "status": "error",
            "message": "I could not identify the test type from the filename. Please rename it to include the test name (e.g., 'AMH Report.pdf').",
            "detected_type": None
        }

    # 3. Validate against Phase 1 History
    # Construct allowed list
    allowed_tests = set()
    if state.tests_done_list:
        allowed_tests.update(state.tests_done_list)
    if state.male_tests_done_list:
        allowed_tests.update(state.male_tests_done_list)
        
    # Mapping for generic terms to allowed
    # If detected 'Semen Analysis' but user said 'Semen analysis', it matches (logic handles this via lower case checks in extractor usually but here we have normalized strings).
    # Let's check for containment or direct match.
    # We need to be careful. If user said "Hormonal blood tests", and uploads "AMH", is it allowed?
    # Yes, AMH is a hormonal test.
    # Simple Logic: If "None" is in list, no uploads allowed?
    # Or strict check?
    # User feedback: "Validate test is part of Phase 1 tests_done"
    
    # Heuristic for Validation:
    # If exact match in allowed_tests -> OK
    # If test_type is "AMH" and "Hormonal" in allowed -> OK
    # If test_type is "FSH" and "Hormonal" in allowed -> OK
    
    valid_upload = False
    
    # Normalization helper
    def normalize(s): return s.lower().strip()
    
    allowed_normalized = [normalize(t) for t in allowed_tests]
    type_normalized = normalize(test_type)
    
    if type_normalized in allowed_normalized:
        valid_upload = True
    else:
        # Hierarchy Check
        hormonal_subtypes = ["amh", "fsh", "lh", "tsh", "prolactin", "estradiol"]
        if type_normalized in hormonal_subtypes and any("hormonal" in t for t in allowed_normalized):
            valid_upload = True
            
        if type_normalized == "semen analysis" and any("semen" in t for t in allowed_normalized):
            valid_upload = True
            
        if type_normalized == "hsg" and any("tube" in t for t in allowed_normalized):
            valid_upload = True
            
    if not valid_upload:
         return {
            "status": "error",
            "message": f"This test ({test_type}) was not mentioned in your history. I am only entering reports for tests we discussed.",
            "detected_type": test_type
        }

    # 4. Update State
    from datetime import date
    new_doc = {
        "test_name": test_type,
        "filename": file.filename,
        "upload_date": date.today().isoformat(),
        "test_date": None, # Pending user input
        "validity_status": None
    }
    
    # Avoid Duplicates
    if not any(d["filename"] == file.filename for d in state.phase2_documents):
        state.phase2_documents.append(new_doc)
        
    return {
        "status": "success",
        "message": f"Received {test_type}. When was this test done?", # Frontend might display this or orchestrator next turn
        "document": new_doc
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)