"""
Orchestration layer: routes a translated NL query to the reasoning service,
or decides to respond conversationally without touching the ontology.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reasoning"))

from nl_to_query import translate_llm
from explain_to_nl import polish_explanation
from reasoning_service import get_reasoning_service


def handle_question(nl_question: str) -> dict:
    query = translate_llm(nl_question)

    if query["intent"] == "llm_error":
        return {
            "raw": None,
            "polished": ("Sorry, I'm having trouble reaching the language model right now. "
                         "Please try again in a moment."),
            "severity": "Unknown",
        }

    if query["intent"] not in ("check_risk", "explain_risk"):
        return {
            "raw": None,
            "polished": ("I can only answer questions about interactions between known drugs "
                         "right now — try asking something like 'Is Warfarin risky with Aspirin?'"),
            "severity": "Unknown",
        }

    drug_names = query["drug_names"]

    if len(drug_names) < 1:
        return {
            "raw": None,
            "polished": ("I couldn't identify a known drug in that question. Try naming a "
                         "specific drug, e.g. 'Is Ketoconazole safe with Simvastatin?'"),
            "severity": "Unknown",
        }

    service = get_reasoning_service()
    result = service.check_custom_regimen(drug_names)

    if "error" in result:
        return {
            "raw": None,
            "polished": result["error"],
            "severity": "Unknown",
        }

    if result.get("consistent") is False:
        return {
            "raw": result.get("message"),
            "polished": result.get("message"),
            "severity": "Contraindicated",
        }

    raw = result["explanation"]
    severity = result["severity"]
    polish_result = polish_explanation(raw)

    return {
        "raw": polish_result["raw"],
        "polished": polish_result["polished"],
        "severity": severity,
    }


if __name__ == "__main__":
    test_questions = [
        "Is Warfarin and Aspirin risky together?",
        "Why is Ketoconazole with Simvastatin dangerous?",
        "Is Diazepam safe on its own?",
        "What's the weather today?",
        "Tell me about Xanax and alcohol",
    ]
    for q in test_questions:
        result = handle_question(q)
        print(f"Q: {q}")
        print(f"RAW:      {result['raw']}")
        print(f"POLISHED: {result['polished']}")
        print(f"SEVERITY: {result['severity']}")
        print()