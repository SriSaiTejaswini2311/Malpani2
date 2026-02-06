import json
from app.models.case_state import CaseState

def generate_section_a(state: CaseState) -> str:
    """
    Generates the 'Section A' summary using DETERMINISTIC templating.
    Strictly follows the Final Spec example including headers and format.
    """
    
    # 1. Age
    age_str = f"{state.female_age or 'Unclear'}"
    if state.male_partner_present:
        age_str += f" (Partner: {state.male_age or 'Unclear'})"
    elif state.male_partner_type == "Donor":
        age_str += " (Donor sperm planning)"
    
    # 2. Duration
    dur = state.years_trying
    if dur is not None:
        dur_str = f"{int(dur)} years" if dur == int(dur) else f"{dur} years"
    else:
        dur_str = "Unclear"

    # 3. Pregnancy
    if state.has_prior_pregnancies is False:
        preg_str = "None reported"
    elif state.has_prior_pregnancies is True:
        source = state.pregnancy_source or "Unknown source"
        outcome = state.pregnancy_outcome or "outcome unknown"
        preg_str = f"{source} pregnancy, {outcome}"
    else:
        preg_str = "Unclear"

    # 4. Treatments
    tx_list = []
    if state.has_had_treatments is False:
        tx_str = "None so far"
    elif state.has_had_treatments is True:
        # Check specific types
        if state.treatment_type == "IVF":
             cycles = f" ({state.ivf_cycles} cycles)" if state.ivf_cycles else ""
             tx_str = f"IVF{cycles}"
        elif state.treatment_type == "IUI":
             cycles = f" ({state.iui_cycles} cycles)" if state.iui_cycles else ""
             tx_str = f"IUI{cycles}"
        elif state.treatment_type == "Medications":
             tx_str = "Medications only"
        else:
             tx_str = "Yes (Type unclear)"
    else:
        tx_str = "Pending"

    # 5. Tests
    if not state.tests_done_list or state.tests_done_list == ["None"]:
        tests_str = "None"
    else:
        tests_str = ", ".join(state.tests_done_list)

    # 6. Reports
    reports_str = state.reports_availability or "No"

    # Construct Final String
    summary = f"""Section A: My Understanding

- Age: {age_str}
- Duration trying to conceive: {dur_str}
- Previous pregnancies: {preg_str}
- Fertility treatments: {tx_str}
- Tests done: {tests_str}
- Reports available: {reports_str}

Please let me know if I’ve understood this correctly so far."""

    return summary