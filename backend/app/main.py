from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
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

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    # 1. Initialize or get the session
    if req.session_id not in sessions:
        sessions[req.session_id] = CaseState()
    
    state = sessions[req.session_id]

    # 2. STATE MACHINE: Handle Confirmation Pause (Day 3 Requirement)
    if state.status == "SUMMARIZED":
        # Check if user confirmed the Section A summary
        if any(word in req.message.lower() for word in ["yes", "correct", "accurate", "yeah"]):
            state.status = "CONFIRMED"
            return {
                "reply": "Thank you for confirming. I have locked this history. Please proceed to upload any medical reports you have.",
                "state": state.dict()
            }
        else:
            # If user says no, go back to intake to fix errors
            state.status = "INTAKE"
            return {
                "reply": "I apologize. Please tell me exactly what I misunderstood so I can correct the record.",
                "state": state.dict()
            }

    # 3. EXTRACTION: Update JSON State from Message
    try:
        # Calls the LLM to find facts (age, years trying, etc)
        extracted_data = extract_clinical_state(req.message, state.model_dump())
        print(f"DEBUG EXTRACTED: {extracted_data}")
        state.update_from_json(extracted_data)
        print(f"DEBUG NEW DEMOGRAPHICS: {state.demographics.model_dump()}")
    except Exception as e:
        print(f"Extraction Error: {e}")
        # Rule: No fallback apologies to user

    # 4. SUMMARIZATION TRIGGER: Check if we have enough info for Section A
    # (Triggered if we have age and at least one history point)
    if state.is_ready_for_summary():
        state.status = "SUMMARIZED"
        section_a = generate_section_a(state)
        
        # DEBUG: Print the final state for the walkthrough artifact
        print("\n--- FINAL CASE STATE JSON ---")
        print(json.dumps(state.model_dump(), indent=2))
        print("-----------------------------\n")
        
        return {
            "reply": f"{section_a}\n\nPlease let me know if I’ve understood this correctly so far.",
            "state": state.model_dump()
        }

    # 5. ORCHESTRATOR: Determine the next best question
    from app.engine.orchestrator import get_next_question
    next_question = get_next_question(state)
    
    return {
        "reply": next_question,
        "state": state.model_dump()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)