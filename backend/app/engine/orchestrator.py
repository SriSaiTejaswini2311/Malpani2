import json
from typing import Tuple, List
from app.models.case_state import CaseState

def get_next_question(state: CaseState) -> Tuple[str, List[str]]:
    """
    DETERMINISTIC ORCHESTRATOR (FINAL SPEC - PHASE 1)
    Strictly follows the sequential decision flow from the USER'S FINAL SPEC.
    """

    # 0. Entry + Role Selection (CRITICAL - FIRST DECISION)
    if not state.intro_shown:
        state.intro_shown = True
        msg = (
            "Hello. I am Dr. Malpani’s AI assistant.\n"
            "To help us understand your case, I’ll walk through your fertility history step by step.\n\n"
            "Which of the following best describes your situation?"
        )
        options = ["I have a partner", "I am planning to conceive using a donor", "I’m exploring options / not sure yet"]
        return msg, options

    # 1. Age Intake (Partner vs Solo branch)
    if state.male_partner_present is None and state.male_partner_type is None:
        # Fallback if extractor missed it
        return "Which of the following best describes your situation?", ["I have a partner", "I am planning to conceive using a donor", "I’m exploring options / not sure yet"]

    # Branch A: Partner Flow
    if state.male_partner_type == "Partner" or (state.male_partner_present is True and state.male_partner_type != "Donor"):
        if state.female_age is None or state.male_age is None:
            if not state.female_age and not state.male_age and not state.unclear_age_ownership:
                 return "Please tell me the ages of both people involved.", []
            
            if state.unclear_age_ownership:
                 return (
                     "Just to make sure I record this correctly:\n"
                     "which age is yours, and which belongs to your partner?",
                     ["First is mine", "Second is mine"]
                 )
            
            if state.female_age and not state.male_age:
                 return "And how old is your partner?", []
            
            if state.male_age and not state.female_age:
                 return "And how old are you?", []

    # Branch B/C: Solo / Donor Flow
    else:
        if state.female_age is None:
            return "How old are you?", []

    # 3. Duration of Trying
    if state.pending_duration_value is not None:
         val = state.pending_duration_value
         val_str = str(int(val)) if val == int(val) else str(val)
         return f"Could you clarify the time period for '{val_str}'?", [f"{val_str} years", f"{val_str} months", "Something else"]

    if state.years_trying is None:
        return "How long have you been trying to conceive?", []

    # 4. Pregnancy History
    if state.has_prior_pregnancies is None:
        return "Has there ever been a pregnancy before?", ["Yes", "No"]
    
    if state.has_prior_pregnancies is True:
         if state.pregnancy_source is None:
              return "Which best applies?", ["Natural pregnancy", "Pregnancy after treatment", "I’m not sure"]
         if state.pregnancy_outcome is None:
              return "What was the outcome?", ["Miscarriage", "Ectopic", "Ongoing", "Live birth"]

    # 5. Treatment History
    if not state.treatments_reviewed:
        return "Have you tried any fertility treatments before?", ["IVF", "IUI", "Medications only", "No treatments so far"]

    if state.has_had_treatments:
         if state.treatment_type in ["IVF", "IUI"] and state.ivf_cycles is None and state.iui_cycles is None:
              return "How many cycles?", []

    # 6. Tests Overview
    if not state.tests_reviewed:
        # Multi-select note: Ordinarily we'd return flags, but for text interaction:
        return (
            "Have any fertility-related tests been done so far?",
            ["Hormonal blood tests", "Ultrasound scans", "Tube testing (HSG / similar)", "Semen analysis", "None of the above"]
        )

    # 7. Report Availability
    if not state.reports_availability_checked:
        return (
            "Do you currently have copies of these reports?",
            ["Yes, I have them", "No, I would need to collect them", "Some reports only"]
        )

    # 9. Confirmation Step
    if state.confirmation_status is None:
        # We don't return SUMMARY_READY yet, we return the summary text AS a question
        # Wait, the spec says "8. Section A... trigger 9. Confirmation".
        # Logic: If everything else is done, we return a special signal or the text.
        return "SUMMARY_READY", ["Yes, that’s correct", "No, I’d like to correct something"]

    return "CONVERSATION_COMPLETE", []
