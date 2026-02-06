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
    reply, options = get_next_question(state)
    
    # 4. Handle Special Signals
    if reply == "SUMMARY_READY":
        summary_text = generate_section_a(state)
        return ChatResponse(
            reply=summary_text,
            options=options, # ["Yes, that’s correct", "No, I’d like to correct something"]
            state=state.dict()
        )
    
    if reply == "CONVERSATION_COMPLETE":
        return ChatResponse(
            reply="Thank you for providing those details. We are now ready to proceed with Phase 2.",
            options=[],
            state=state.dict()
        )

    # 5. Standard Response
    return ChatResponse(
        reply=reply,
        options=options,
        state=state.dict()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)