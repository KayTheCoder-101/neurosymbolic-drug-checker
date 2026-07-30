"""
NL -> structured query translation.
Stage A: mock translator (rule-based/keyword matching) — no API calls.
Stage B (later): replace `translate_mock` calls with real OpenAI calls,
keeping the same output shape so nothing downstream changes.
"""

import re
import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
KNOWN_PATIENTS = ["P1_SerotoninRisk", "P2_CYP3A4Risk", "P3_BleedingRisk", "P5_Safe"]

from openai import OpenAIError

def translate_llm(nl_question: str) -> dict:
    system_prompt = f"""..."""  # unchanged

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": nl_question},
            ],
            timeout=10,
        )
        parsed = json.loads(response.choices[0].message.content)
        return {
            "intent": parsed.get("intent", "unknown"),
            "patient_id": parsed.get("patient_id"),
            "raw_question": nl_question,
        }
    except (OpenAIError, json.JSONDecodeError) as e:
        return {
            "intent": "llm_error",
            "patient_id": None,
            "raw_question": nl_question,
            "error": str(e),
        }


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
        "What's the weather today?",
    ]
    for q in test_questions:
        print(q, "->", translate_llm(q))