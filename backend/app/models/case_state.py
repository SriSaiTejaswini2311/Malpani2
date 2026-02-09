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

    # 3. Relationship (Partner Only)
    first_marriage: Optional[bool] = None
    years_married: Optional[float] = None

    # 4. Duration
    years_trying: Optional[float] = None
    pending_duration_value: Optional[float] = None # Temp store for normalization flow
    
    # 5. Pregnancy History
    has_prior_pregnancies: Optional[bool] = None
    pregnancy_source: Optional[Literal["Natural", "Treatment", "NotSure"]] = None
    pregnancy_outcome: Optional[Literal["Miscarriage", "Ectopic", "Chemical", "Live birth", "Ongoing"]] = None
    pregnancy_history: List[Any] = []

    # 6. Menstrual History
    menstrual_regularity: Optional[Literal["Regular", "Irregular", "NotSure"]] = None
    cycle_length: Optional[str] = None # Range: "21-25", "26-30", etc.
    cycle_predictability: Optional[bool] = None
    menarche_age: Optional[str] = None # Free text/number

    # 6E. Sexual History
    sexual_difficulty: Optional[Literal["None", "Sometimes", "Rarely", "NotApplicable"]] = None
    
    # 7. Treatments
    has_had_treatments: Optional[bool] = None
    treatment_type: Optional[Literal["IVF", "IUI", "Medications", "None"]] = None
    treatments_reviewed: bool = False
    ivf_cycles: Optional[int] = None
    iui_cycles: Optional[int] = None
    
    # 8. Tests
    tests_reviewed: bool = False
    tests_done_list: List[str] = [] # Female Tests
    male_tests_done_list: List[str] = [] # Male Tests
    
    # Semen Analysis Details
    semen_analysis_date: Optional[str] = None
    semen_analysis_result: Optional[Literal["Normal", "Abnormal", "NotSure"]] = None
    semen_report_available: Optional[bool] = None

    # 9. Reports
    reports_availability: Optional[Literal["Yes", "No", "Some"]] = None
    reports_availability_checked: bool = False
    
    # 9. Confirmation
    confirmation_status: Optional[bool] = None # True (Correct), False (Needs Fix)

    class Config:
        use_enum_values = True

    # Internal status for the orchestrated flow
    status: str = "INTAKE"  # INTAKE, SUMMARIZED, CONFIRMED