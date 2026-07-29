"""
NL -> structured query translation.
Stage A: mock translator (rule-based/keyword matching) — no API calls.
Stage B (later): replace `translate_mock` calls with real OpenAI calls,
keeping the same output shape so nothing downstream changes.
"""

import re

KNOWN_PATIENTS = ["P1_SerotoninRisk", "P2_CYP3A4Risk", "P3_BleedingRisk", "P5_Safe"]


def translate_mock(nl_question: str) -> dict:
    question_lower = nl_question.lower()

    patient_id = None
    for pid in KNOWN_PATIENTS:
        if pid.lower() in question_lower or pid.split("_")[0].lower() in question_lower:
            patient_id = pid
            break

    if "why" in question_lower or "explain" in question_lower:
        intent = "explain_patient_risk"
    elif "safe" in question_lower or "risk" in question_lower or "check" in question_lower:
        intent = "check_patient_risk"
    else:
        intent = "unknown"

    return {
        "intent": intent,
        "patient_id": patient_id,
        "raw_question": nl_question,
    }

if __name__ == "__main__":
    test_questions = [
        "Is P1 at risk?",
        "Why is P2_CYP3A4Risk flagged?",
        "Check P3 for bleeding risk",
        "Is P5 safe?",
    ]
    for q in test_questions:
        print(q, "->", translate_mock(q))