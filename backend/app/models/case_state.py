from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Any

# --- MAIN CASE STATE ---

class CaseState(BaseModel):
    case_id: str = ""
    phase: str = "phase_1"
    intro_shown: bool = False
    
    # 1. Partner Status
    male_partner_present: Optional[bool] = None
    male_partner_type: Optional[Literal["Partner", "Donor", "Unsure"]] = None
    
    # 2. Ages
    female_age: Optional[int] = None
    male_age: Optional[int] = None
    unclear_age_ownership: List[int] = []
    
    # 3. Duration
    years_trying: Optional[float] = None
    pending_duration_value: Optional[float] = None
    
    # 4. Pregnancy
    has_prior_pregnancies: Optional[bool] = None
    pregnancy_source: Optional[Literal["Natural", "Treatment", "NotSure"]] = None
    pregnancy_outcome: Optional[str] = None # Miscarriage, Ectopic, Ongoing, Live Birth
    pregnancy_history: List[Any] = []
    
    # 5. Treatments
    treatments_reviewed: bool = False
    has_had_treatments: Optional[bool] = None
    treatment_type: Optional[Literal["IVF", "IUI", "Medications", "None"]] = None
    ivf_cycles: Optional[int] = None
    iui_cycles: Optional[int] = None
    
    # 6. Tests
    tests_reviewed: bool = False
    tests_done_list: List[str] = [] # Hormonal, Ultrasound, HSG, Semen, None
    
    # 7. Reports
    reports_availability: Optional[str] = None # Yes, No, Some
    reports_availability_checked: bool = False
    
    # 9. Confirmation
    confirmation_status: Optional[bool] = None # True (Correct), False (Needs Fix)

    class Config:
        use_enum_values = True

    # Internal status for the orchestrated flow
    status: str = "INTAKE"  # INTAKE, SUMMARIZED, CONFIRMED