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
            "To help us understand your case, I’ll walk through your fertility history step by step.\n"
            "I may pause or clarify at times — that’s how doctors avoid missing important details.\n\n"
            "Which of the following best describes your situation?"
        )
        options = ["I have a partner", "I am planning to conceive using a donor", "I’m exploring options / not sure yet"]
        return msg, options

    # 1. Partner Status Extraction is handled, we move to Age Intake

    # 2. Age Intake
    # Case 1A: Partner Branch
    if state.male_partner_type == "Partner" or (state.male_partner_present is True and state.male_partner_type != "Donor"):
        if state.female_age is None or state.male_age is None:
            if not state.female_age and not state.male_age and not state.unclear_age_ownership:
                 return "Please tell me the ages of both people involved.", []
            
            if state.unclear_age_ownership:
                 # Explicit Clarification options
                 age1, age2 = state.unclear_age_ownership[0], state.unclear_age_ownership[1]
                 return (
                     "Just to confirm, please select one option so I record this correctly:",
                     [f"Female is {age1}, Male is {age2}", f"Female is {age2}, Male is {age1}"]
                 )
            
            if state.female_age and not state.male_age:
                 return "And how old is your partner?", []
            
            if state.male_age and not state.female_age:
                 return "And how old are you?", []

    # Case 1B/1C: Donor / Exploring Branch (Female only)
    else:
        if state.female_age is None:
            return "How old are you?", []

    # 3. Relationship & Timeline (PARTNER BRANCH ONLY)
    if state.male_partner_type == "Partner" or (state.male_partner_present is True and state.male_partner_type != "Donor"):
        if state.first_marriage is None:
            return "Is this the first marriage for both of you?", ["Yes", "No"]
        if state.years_married is None:
             # Free text expected, no options
             return "How long have you been married?", []

    # 4. Duration of Trying
    # Zero Duration Handling
    if state.years_trying == 0:
        pass # Fall through to next step
    elif state.pending_duration_value is not None:
         val = state.pending_duration_value
         val_str = str(int(val)) if val == int(val) else str(val)
         return f"Could you clarify the time period for '{val_str}'?", [f"{val_str} years", f"{val_str} months", "Something else"]

    if state.years_trying is None:
        return "How long have you been trying to conceive?", []

    # 5. Pregnancy History (CRITICAL)
    if state.has_prior_pregnancies is None:
        return "Has there ever been a pregnancy before?", ["Yes", "No"]
    
    if state.has_prior_pregnancies is False and not state.menstrual_regularity: # Check next step trigger
         # Empathy Message for NO
         return (
             "I understand. Thank you for sharing that.\n\n"
             "Are your menstrual cycles regular?", 
             ["Yes", "No", "Not sure"]
         )

    if state.has_prior_pregnancies is True:
         if state.pregnancy_source is None:
              return "Was it a natural pregnancy or with treatment?", ["Natural pregnancy", "Pregnancy after treatment", "I’m not sure"]
         if state.pregnancy_outcome is None:
              return "What was the outcome?", ["Miscarriage", "Ectopic pregnancy", "Chemical pregnancy", "Live birth", "Ongoing"]

    # 6. Menstrual History (NEW)
    if state.menstrual_regularity is None:
        return "Are your menstrual cycles regular?", ["Yes", "No", "Not sure"]

    if state.menstrual_regularity in ["Regular", "NotSure"] or state.menstrual_regularity == "Irregular": 
        # Logic: If Yes or Not Sure, ask Length. If No/Irregular, user likely knows it varies, but spec says ask length if Yes/NotSur.
        # Strict spec: "5B. Cycle Length (if Yes or Not sure)"
        if state.menstrual_regularity != "Irregular" and state.cycle_length is None:
             return "About how many days apart do your periods usually come?", ["21–25 days", "26–30 days", "31–35 days", "Irregular / varies", "Not sure"]

    if state.cycle_predictability is None:
        return "Do your periods usually come predictably each month?", ["Yes", "No"]

    if state.menarche_age is None:
        return "At what age did you get your first period?", []

    # 6E. Sexual History (Screening)
    if state.sexual_difficulty is None:
        return (
            "Are you and your partner generally able to have regular sexual intercourse without difficulty?",
            ["Yes, without difficulty", "Sometimes difficult", "Rarely / with difficulty", "Not applicable (using donor / no partner)"]
        )

    # 7. Treatments
    if not state.treatments_reviewed:
        return "Have you tried any fertility treatments before?", ["IVF", "IUI", "Medications only", "No treatments so far"]

    if state.has_had_treatments:
         if state.treatment_type in ["IVF", "IUI"] and state.ivf_cycles is None and state.iui_cycles is None:
              return "How many cycles have you undergone?", []

    # 8. Tests Overview (BRANCHING)
    if not state.tests_reviewed:
        # Female Tests (Multi-select)
        options = [
            "Hormonal blood tests (AMH, TSH, FSH/LH)", 
            "Ultrasound scans", 
            "Tube testing (HSG / Laparoscopy / HyCoSy)",
            "None of the above"
        ]
        return (
            "Which of the following tests have been done for you? You can select all that apply.",
            options,
            True # Multi-select
        )

    # 8B. Male Tests (Partner Branch Only)
    is_partner_flow = (state.male_partner_type == "Partner" or (state.male_partner_present is True and state.male_partner_type != "Donor"))
    
    # We use a virtual check: if we are in partner flow, tests_reviewed is True (meaning Female done), 
    # but we haven't checked male tests yet.
    # We can check if `male_tests_done_list` is populated OR if we just asked the male question?
    # Better: We rely on the Extractor to populate `male_tests_done_list`.
    # Complexity: How do we know if we *asked* it?
    # Let's add a state field or use a specific logic.
    # To keep CaseState simple, let's assume if tests_reviewed is True, we check male tests.
    
    # Logic: 
    # 1. Ask Female Tests (Step 8A). Extractor sets tests_reviewed=True.
    # 2. Next turn: tests_reviewed is True. Check if Partner Flow.
    # 3. If Partner Flow, check if we have Male Tests data or a "Male Tests Skipped" flag?
    # We don't have a flag. Let's look at `male_tests_done_list`.
    # If it's empty, we ASK. (Unless they really have none? Then extractor sets ["None"]).
    # So if `male_tests_done_list` is empty, we Ask.
    
    if is_partner_flow and state.tests_reviewed and not state.male_tests_done_list:
        options = [
            "Semen analysis",
            "Hormonal blood tests",
            "Genetic tests",
            "None of the above"
        ]
        return (
            "Which of the following tests have been done for your partner? You can select all that apply.",
            options,
            True # Multi-select
        )

    # 9. Reports Availability
    # Only ask if ANY tests exist (Female or Male)
    # Check: tests_done_list has entries (not "None") OR male_tests_done_list has entries (not "None")
    has_female_tests = state.tests_done_list and "None" not in state.tests_done_list
    has_male_tests = state.male_tests_done_list and "None" not in state.male_tests_done_list
    
    if (has_female_tests or has_male_tests) and not state.reports_availability_checked:
        return (
            "Do you currently have copies of these reports?",
            ["Yes, I have them", "No, I would need to collect them", "Some reports only"],
            False
        )

    # 10. Confirmation Step (Summary Generation)
    if state.confirmation_status is None:
        # Generate the Section A Summary string here or in the frontend? 
        # The prompt says "Auto-generate Section A". 
        # We return a specific signal "SUMMARY_READY" and let the Frontend or a separate tool generate it?
        # Re-reading: "Step 8: Section A - Doctor Summary... Options: Yes, No".
        # So we should return the Summary Text as the "Message".
        
        summary_text = (
            "Section A: My Understanding\n\n"
            f"• Age: Female {state.female_age}" + (f", Male {state.male_age}" if state.male_age else "") + "\n"
            f"• Duration trying to conceive: {state.years_trying} years\n"
        )
        
        # Add Menstrual History
        if state.menstrual_regularity:
            summary_text += f"• Menstrual history: {state.menstrual_regularity}, {state.cycle_length or ''} days\n"
            
        # Add Sexual History
        if state.sexual_difficulty:
             summary_text += f"• Intercourse Difficulty: {state.sexual_difficulty}\n"

        # Add Pregnancies
        summary_text += f"• Previous pregnancies: {'Yes' if state.has_prior_pregnancies else 'No'}"
        if state.has_prior_pregnancies:
            summary_text += f" ({state.pregnancy_outcome or 'Unknown'})"
        summary_text += "\n"

        # Add Treatments
        summary_text += f"• Fertility treatments: {state.treatment_type or 'None'}\n"
        
        # Add Tests
        f_tests = ", ".join(state.tests_done_list) if state.tests_done_list else "None"
        summary_text += f"• Female tests done: {f_tests}\n"
        
        if is_partner_flow:
            m_tests = ", ".join(state.male_tests_done_list) if state.male_tests_done_list else "None"
            summary_text += f"• Male tests done: {m_tests}\n"

        summary_text += "\n" + "Please let me know if I’ve understood this correctly so far."

        return summary_text, ["Yes, that’s correct", "No, I’d like to correct something"], False
        
    return "CONVERSATION_COMPLETE", [], False
