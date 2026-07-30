"""
Orchestration layer: routes a translated query to the right ontology/reasoning
action, or decides to respond conversationally without touching the ontology.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ontology"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reasoning"))

from owlready2 import sync_reasoner
import populate_individuals as pop
from explain import explain_patient
from nl_to_query import translate_llm
from explain_to_nl import polish_explanation

_reasoner_has_run = False


def _ensure_reasoner_run():
    global _reasoner_has_run
    if not _reasoner_has_run:
        with pop.onto:
            sync_reasoner(infer_property_values=True)
        _reasoner_has_run = True


def handle_question(nl_question: str) -> dict:
    query = translate_llm(nl_question)

    if query["intent"] == "llm_error":
        return {
            "raw": None,
            "polished": ("Sorry, I'm having trouble reaching the language model right now. "
                         "Please try again in a moment."),
            "severity": "Unknown",
        }

    if query["intent"] not in ("check_patient_risk", "explain_patient_risk"):
        return {
            "raw": None,
            "polished": ("I can only answer questions about patient drug-interaction risk right now "
                         "— try asking something like 'Is P1 at risk?' or 'Why is P2 flagged?'"),
            "severity": "Unknown",
        }

    if query["patient_id"] is None:
        return {
            "raw": None,
            "polished": ("I couldn't identify which patient you're asking about. "
                         "Please refer to a patient by ID (e.g. P1, P2, P3)."),
            "severity": "Unknown",
        }

    _ensure_reasoner_run()

    patient = getattr(pop, query["patient_id"].split("_")[0], None)
    if patient is None:
        return {
            "raw": None,
            "polished": f"I don't have a record for patient {query['patient_id']}.",
            "severity": "Unknown",
        }

    explain_result = explain_patient(patient)
    raw = explain_result["explanation"]
    severity = explain_result["severity"]

    polish_result = polish_explanation(raw)

    return {
        "raw": polish_result["raw"],
        "polished": polish_result["polished"],
        "severity": severity,
    }


if __name__ == "__main__":
    test_questions = [
        "Is P1 at risk?",
        "Why is P2_CYP3A4Risk flagged?",
        "Check P3 for bleeding risk",
        "Is P5 safe?",
        "What's the weather today?",
    ]
    for q in test_questions:
        result = handle_question(q)
        print(f"Q: {q}")
        print(f"RAW:      {result['raw']}")
        print(f"POLISHED: {result['polished']}")
        print(f"SEVERITY: {result['severity']}")
        print()