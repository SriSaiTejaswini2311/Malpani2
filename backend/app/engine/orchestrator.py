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
         
         # 7B. IVF Drill-Down
         if state.treatment_type == "IVF":
              # 1. Fresh/Frozen
              if state.last_ivf_transfer_type is None:
                   msg = f"You mentioned {state.ivf_cycles} IVF cycles. Let’s focus on the most recent one.\nWas it a fresh embryo transfer or a frozen embryo transfer?"
                   return msg, ["Fresh transfer", "Frozen transfer", "Not sure"]
              
              # 2. Outcome
              if state.last_ivf_outcome is None:
                   return "What was the outcome of that last cycle?", ["Beta negative", "Biochemical pregnancy", "Miscarriage", "Ectopic pregnancy", "Ongoing pregnancy", "Live birth"]

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
    
    # 9A. Date Collection Loop (NEW REQ: Ask dates immediately)
    if has_female_tests or has_male_tests:
        all_tests = []
        if has_female_tests: all_tests.extend(state.tests_done_list)
        if has_male_tests: all_tests.extend(state.male_tests_done_list)
        
        # Check if we have dates for all
        for test in all_tests:
            if test not in state.reported_test_dates:
                state.active_date_inquiry = test
                return f"When was your {test} test done?", []
        
        # If loop finishes, all dates are present
        state.active_date_inquiry = None

    if (has_female_tests or has_male_tests) and not state.reports_availability_checked:
        return (
            "Do you currently have copies of these reports?",
            ["Yes, I have them", "No, I would need to collect them", "Some reports only"],
            False
        )

    # 10. Confirmation Step (Summary Generation)
    if state.confirmation_status is None:
        from app.engine.phase2 import check_validity
        
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
        if state.treatment_type == "IVF":
            details = []
            if state.ivf_cycles: details.append(f"{state.ivf_cycles} cycles")
            if state.last_ivf_transfer_type: details.append(f"Last transfer: {state.last_ivf_transfer_type}")
            if state.last_ivf_outcome: details.append(f"Outcome: {state.last_ivf_outcome}")
            if details:
                summary_text += f"  - Details: {', '.join(details)}\n"
        
        # Add Tests with Validity
        if state.tests_done_list:
            f_tests_display = []
            for t in state.tests_done_list:
                if t == "None": continue
                date_val = state.reported_test_dates.get(t)
                if date_val:
                    validity = check_validity(t, date_val)
                    f_tests_display.append(f"{t} ({validity})")
                else:
                    f_tests_display.append(t)
            
            f_str = ", ".join(f_tests_display) if f_tests_display else "None"
            summary_text += f"• Female tests done: {f_str}\n"
        
        if is_partner_flow:
            m_tests_display = []
            if state.male_tests_done_list:
                for t in state.male_tests_done_list:
                    if t == "None": continue
                    date_val = state.reported_test_dates.get(t)
                    if date_val:
                        validity = check_validity(t, date_val)
                        m_tests_display.append(f"{t} ({validity})")
                    else:
                        m_tests_display.append(t)
                        
                m_str = ", ".join(m_tests_display) if m_tests_display else "None"
                summary_text += f"• Male tests done: {m_str}\n"

        summary_text += "\n" + "Please let me know if I’ve understood this correctly so far."

        return summary_text, ["Yes, that’s correct", "No, I’d like to correct something"], False
        
    # 11. Phase 2 Transition Logic (End of Phase 1)
    if state.status == "INTAKE":
         # Check if we should move to Phase 2
         # Trigger: Confirmation is True
         if state.confirmation_status is True:
             state.status = "PHASE2_START" # Transient status to trigger Phase 2 logic next block
             state.phase = "PHASE2"
             # Fall through to Phase 2 block
             
    # --- PHASE 2 ORCHESTRATION ---
    if state.phase == "PHASE2":
        
        # A. Entry Check (Skip if no tests)
        has_tests = False
        if state.tests_done_list and "None" not in state.tests_done_list: has_tests = True
        if state.male_tests_done_list and "None" not in state.male_tests_done_list: has_tests = True
        
        if not has_tests:
            state.phase = "COMPLETE"
            return "Based on your history, no prior tests were reported. We can proceed to the next stage.", []

        # B. Introduction
        # We need a flag to know if we already showed the intro vs we are in the loop.
        # Use state.phase2_documents check? No, user might not have uploaded yet.
        # Let's use a specific flag or reuse `intro_shown`? No, specific Phase 2 intro.
        # Let's assume if we are in PHASE2 and no docs yet, we show intro.
        # But what if they truly have none to upload despite having tests?
        # We need an option "I don't have reports".
        
        # Better: Check existing documents count or a specific "phase2_intro_shown" flag.
        # Let's use a dynamic check:
        # If we haven't asked for uploads yet.
        # But we don't have a flag. Let's add one to State if needed, or infer.
        # Inference: If `phase2_documents` is empty AND we haven't received a "No files" signal.
        # Complexity: The user can upload 1 file, then waiting for more. 
        # So we need an explicit "Done uploading" Loop.
        
        docs_count = len(state.phase2_documents)
        
        # Upload Loop
        # If we are waiting for uploads or dates.
        
        # 1. Ask for Uploads (Initial)
        # Condition: We just entered Phase 2 (implied by lack of docs and 'verification_complete' is False)
        # But wait, what if they upoaded 0 files?
        # We need to detect the "Start of Phase 2".
        # Let's rely on the previous turn returning "CONVERSATION_COMPLETE" which wasn't quite right.
        # The previous block returned "Please let me know if correct".
        # User says "Yes". Extractor sets confirmation_status=True.
        # NEXT REQUEST: Orchestrator sees confirmation=True -> sets PHASE2.
        # AND THEN executes this block.
        
        if not state.phase2_documents and not hasattr(state, "phase2_intro_shown"):
             # We need to store that we showed it.
             pass 
             
        # Use phase2_uploads_complete flag
        # If user is NOT done uploading, and we are not forcing a date question (which we do if doc exists),
        # Actually, if user uploads, we receive file. if user talks, we receive message.
        
        # Priority 1: Check if verification already done
        if state.phase2_verification_complete:
             # Transition to Phase 3
             return "Phase 2 Analysis Complete. Moving to Pattern Recognition.", []

        # Priority 2: Missing Dates (ALWAYS ask immediately)
        missing_date_doc = next((d for d in state.phase2_documents if d['test_date'] is None), None)
        if missing_date_doc:
            return f"When was the {missing_date_doc['test_name']} test done?", []

        # Priority 3: Uploads Done?
        # If NOT done uploading, keep asking/waiting.
        if not state.phase2_uploads_complete:
            docs_count = len(state.phase2_documents)
            msg = "If you have your test reports, you can upload them here. I’ll review them the way a doctor would."
            if docs_count > 0:
                msg = f"I have received {docs_count} report(s). Upload more if you have them, or click 'Done uploading' to proceed."
            
            return msg, ["Done uploading", "I don't have any reports"]

        # Priority 4: All Dates Present & Uploads Done -> VALIDITY CHECK & SUMMARY
        # We reach here if uploads_complete is True AND no missing dates.
        
        from app.engine.phase2 import check_validity, generate_validity_summary
        
        # Run Checks
        processed_docs = []
        for doc in state.phase2_documents:
            status = check_validity(doc["test_name"], doc["test_date"])
            doc["validity_status"] = status
            processed_docs.append(doc)
            
        # Update State (In-place modification works for object refs, but cleaner to assign?)
        # Orchestrator doesn't usually update state, Extractor (or Main) does.
        # But here we are the "Engine". We are allowed to modify state before returning?
        # Yes, python objects are mutable.
        state.phase2_documents = processed_docs
        state.phase2_verification_complete = True
        
        summary = generate_validity_summary(processed_docs)
        
        return summary, ["Proceed to next steps"]

    return "CONVERSATION_COMPLETE", [], False
