from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

# --- REUSABLE SUB-MODELS ---

class ConfidenceValue(BaseModel):
    value: Any = None
    confidence: Optional[Literal["high", "medium", "low"]] = None

class Demographics(BaseModel):
    female_age: Optional[int] = None
    male_age: Optional[int] = None
    unclear_age_ownership: List[int] = []
    # Test flags used in new Orchestrator
    female_tests_done: Optional[bool] = None
    ultrasound_done: Optional[bool] = None
    tubal_test_done: Optional[bool] = None
    semen_analysis_done: Optional[bool] = None
    all_tests_none: Optional[bool] = None

class RelationshipContext(BaseModel):
    first_marriage_both: Optional[bool] = None
    years_married: Optional[float] = None

class FertilityTimeline(BaseModel):
    years_trying: Optional[float] = None
    first_concern_date: Optional[str] = None
    first_doctor_visit: Optional[str] = None

class PregnancyHistoryItem(BaseModel):
    type: Optional[Literal["natural", "assisted"]] = None
    outcome: Optional[Literal["live_birth", "miscarriage", "ectopic", "chemical"]] = None
    weeks: Optional[int] = None
    confidence: Optional[Literal["high", "medium", "low"]] = None

class SemenAnalysis(BaseModel):
    done: Optional[bool] = None
    last_done_date: Optional[str] = None
    lab: Optional[str] = None
    reported_result: Optional[Literal["normal", "abnormal", "unknown"]] = None
    report_available: Optional[bool] = None
    confidence: Optional[Literal["high", "medium", "low"]] = None

class MalePartner(BaseModel):
    semen_analysis: SemenAnalysis = Field(default_factory=SemenAnalysis)
    sexual_intercourse_issues: Optional[bool] = None

class MenstrualHistory(BaseModel):
    regular: Optional[bool] = None
    cycle_length_days: Optional[int] = None
    predictable: Optional[bool] = None
    menarche_age: Optional[int] = None

class FemalePartner(BaseModel):
    menstrual_history: MenstrualHistory = Field(default_factory=MenstrualHistory)
    gynecologic_conditions: List[str] = [] # "pcos", "endometriosis", etc.

class HormonalTests(BaseModel):
    done: Optional[bool] = None
    tests_included: List[str] = []
    last_done_date: Optional[str] = None
    report_available: Optional[bool] = None
    confidence: Optional[Literal["high", "medium", "low"]] = None

class Ultrasound(BaseModel):
    done: Optional[bool] = None
    type: Optional[Literal["baseline", "follicular", "unknown"]] = None
    last_done_date: Optional[str] = None
    report_available: Optional[bool] = None
    confidence: Optional[Literal["high", "medium", "low"]] = None

class TubalPatencyTest(BaseModel):
    done: Optional[bool] = None
    type: Optional[Literal["HSG", "laparoscopy", "HyCoSy", "unknown"]] = None
    last_done_date: Optional[str] = None
    report_available: Optional[bool] = None
    confidence: Optional[Literal["high", "medium", "low"]] = None

class FemaleTests(BaseModel):
    hormonal_tests: HormonalTests = Field(default_factory=HormonalTests)
    ultrasound: Ultrasound = Field(default_factory=Ultrasound)
    tubal_patency_test: TubalPatencyTest = Field(default_factory=TubalPatencyTest)

class MaleTests(BaseModel):
    semen_analysis: SemenAnalysis = Field(default_factory=SemenAnalysis)
    hormonal_tests: HormonalTests = Field(default_factory=HormonalTests)

class TestsDone(BaseModel):
    female: FemaleTests = Field(default_factory=FemaleTests)
    male: MaleTests = Field(default_factory=MaleTests)

class IUI(BaseModel):
    done: Optional[bool] = None
    count: Optional[int] = None

class IVF(BaseModel):
    done: Optional[bool] = None
    total_cycles: Optional[int] = None

class Treatments(BaseModel):
    medications: List[str] = []
    iui: IUI = Field(default_factory=IUI)
    ivf: IVF = Field(default_factory=IVF)

class MostRecentCycle(BaseModel):
    clinic: Optional[str] = None
    cycle_type: Optional[Literal["fresh", "frozen", "unknown"]] = None
    protocol_known: Optional[bool] = None
    embryos_transferred: Optional[int] = None
    outcome: Optional[Literal["negative", "miscarriage", "ongoing", "unknown"]] = None

class Gap(BaseModel):
    item: str
    priority: Literal["high", "medium", "low"]
    reason: str

class Meta(BaseModel):
    created_at: str = ""
    last_updated: str = ""
    notes: str = ""

# --- MAIN CASE STATE ---

class CaseState(BaseModel):
    case_id: str = ""
    phase: str = "phase_1"
    demographics: Demographics = Field(default_factory=Demographics)
    relationship_context: RelationshipContext = Field(default_factory=RelationshipContext)
    fertility_timeline: FertilityTimeline = Field(default_factory=FertilityTimeline)
    pregnancy_history: List[PregnancyHistoryItem] = []
    male_partner: MalePartner = Field(default_factory=MalePartner)
    female_partner: FemalePartner = Field(default_factory=FemalePartner)
    tests_done: TestsDone = Field(default_factory=TestsDone)
    treatments: Treatments = Field(default_factory=Treatments)
    most_recent_cycle: MostRecentCycle = Field(default_factory=MostRecentCycle)
    gaps: List[Gap] = []
    confidence_score: float = 0.0
    meta: Meta = Field(default_factory=Meta)
    
    # Internal/Flow Control Flags (to track simplified conversation state)
    has_prior_pregnancies: Optional[bool] = None
    pregnancy_history_reviewed: bool = False
    has_had_treatments: Optional[bool] = None  # Generic flag: True = "Yes" to treatments, but type unknown
    treatments_reviewed: bool = False
    tests_reviewed: bool = False
    reports_availability_checked: bool = False

    # Internal status for the orchestrated flow
    status: str = "INTAKE"  # INTAKE, SUMMARIZED, CONFIRMED

    def update_from_json(self, extracted_data: Dict):
        """
        recursively updates the state from a partial dictionary.
        This is a simplified version (non-recursive dict merge could cover most cases).
        """
        # Demographics
        if "demographics" in extracted_data:
             for k, v in extracted_data["demographics"].items():
                 if hasattr(self.demographics, k):
                     setattr(self.demographics, k, v)
             # Explicitly handle list overwrite/append if needed? For now strict overwrite is fine.
        if "demographics" in extracted_data:
            for k, v in extracted_data["demographics"].items():
                if hasattr(self.demographics, k):
                    setattr(self.demographics, k, v)
            
            # CRITICAL ADDITION:
            # If the LLM successfully extracted both ages, clear the ambiguity list
            if self.demographics.female_age and self.demographics.male_age:
                self.demographics.unclear_age_ownership = []
            # If the user corrected/clarified, the LLM might send an empty list explicitly
            elif "unclear_age_ownership" in extracted_data["demographics"]:
                self.demographics.unclear_age_ownership = extracted_data["demographics"]["unclear_age_ownership"]
        
        # Treatments
        if "treatments" in extracted_data:
            t_data = extracted_data["treatments"]
            if "ivf" in t_data:
                for k, v in t_data["ivf"].items():
                    setattr(self.treatments.ivf, k, v)
            if "iui" in t_data:
                 for k, v in t_data["iui"].items():
                    setattr(self.treatments.iui, k, v)
            if "medications" in t_data:
                self.treatments.medications = t_data["medications"]

        # Timeline
        if "fertility_timeline" in extracted_data:
             for k, v in extracted_data["fertility_timeline"].items():
                 if hasattr(self.fertility_timeline, k):
                     setattr(self.fertility_timeline, k, v)
        
        # Partners
        if "male_partner" in extracted_data:
             mp_data = extracted_data["male_partner"]
             if "semen_analysis" in mp_data:
                 for k, v in mp_data["semen_analysis"].items():
                     setattr(self.male_partner.semen_analysis, k, v)
        
        # Tests (Simplified for Demo)
        if "tests_done" in extracted_data:
             fd = extracted_data["tests_done"].get("female", {})
             if "hormonal_tests" in fd:
                 for k, v in fd["hormonal_tests"].items():
                     setattr(self.tests_done.female.hormonal_tests, k, v)
             if "ultrasound" in fd:
                 for k, v in fd["ultrasound"].items():
                     setattr(self.tests_done.female.ultrasound, k, v)
             if "tubal_patency_test" in fd:
                 for k, v in fd["tubal_patency_test"].items():
                     setattr(self.tests_done.female.tubal_patency_test, k, v)
             
             md = extracted_data["tests_done"].get("male", {})
             if "semen_analysis" in md:
                 for k, v in md["semen_analysis"].items():
                     setattr(self.tests_done.male.semen_analysis, k, v)

        # Flow Flags
        if "has_prior_pregnancies" in extracted_data:
            self.has_prior_pregnancies = extracted_data["has_prior_pregnancies"]
        if "reports_availability_checked" in extracted_data:
            self.reports_availability_checked = extracted_data["reports_availability_checked"]
        if "has_had_treatments" in extracted_data:
            self.has_had_treatments = extracted_data["has_had_treatments"]
        
        # Critical: Ensure Reviewed Flags are updated
        if "tests_reviewed" in extracted_data:
             self.tests_reviewed = extracted_data["tests_reviewed"]
        if "treatments_reviewed" in extracted_data:
             self.treatments_reviewed = extracted_data["treatments_reviewed"]
        if "pregnancy_history_reviewed" in extracted_data:
             self.pregnancy_history_reviewed = extracted_data["pregnancy_history_reviewed"]

        return True

    def is_ready_for_summary(self) -> bool:
        """
        STRICT CHECK: Section A may be generated ONLY if ALL are true.
        """
        print(f"DEBUG SUMMARY CHECK: Age={self.demographics.female_age}, Dur={self.fertility_timeline.years_trying}, Preg={self.has_prior_pregnancies}, TxRew={self.treatments_reviewed}, TxHas={self.has_had_treatments}, TestsRew={self.tests_reviewed}, RepChecked={self.reports_availability_checked}")
        
        # 1. Age
        if self.demographics.female_age is None:
            print("Blocked: Age missing")
            return False
        # 2. Duration
        if self.fertility_timeline.years_trying is None:
            print("Blocked: Duration missing")
            return False
        # 3. Pregnancy
        if self.has_prior_pregnancies is None:
            print("Blocked: Pregnancy status missing")
            return False
        # 4. Treatments
        if not self.treatments_reviewed:
            print("Blocked: Treatments not reviewed")
            return False
        if self.has_had_treatments and (self.treatments.ivf.done is None and self.treatments.iui.done is None):
            print("Blocked: Treatment type unclear")
            return False
        # 5. Tests
        if not self.tests_reviewed:
            print("Blocked: Tests not reviewed")
            return False
        # 6. Reports
        if not self.reports_availability_checked:
            print("Blocked: Reports not checked")
            return False
            
        return True