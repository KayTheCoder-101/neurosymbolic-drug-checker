"""
Takes the ontology-grounded, templated explanation (from reasoning/explain.py)
and rephrases it for readability via an LLM call — WITHOUT adding new claims.

The raw explanation is always preserved and returned alongside the polished
version, so the polish step is auditable rather than blindly trusted.
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


from openai import OpenAIError

def polish_explanation(raw_explanation: str) -> dict:
    system_prompt = """..."""  # unchanged

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_explanation},
            ],
            timeout=10,
        )
        parsed = json.loads(response.choices[0].message.content)
        return {
            "raw": raw_explanation,
            "polished": parsed.get("polished", raw_explanation),
        }
    except (OpenAIError, json.JSONDecodeError):
        # Fall back to the raw, ontology-grounded explanation if polishing fails —
        # never lose the actual answer just because the rephrasing step broke.
        return {
            "raw": raw_explanation,
            "polished": raw_explanation,
        }


if __name__ == "__main__":
    test_cases = [
        "P1_SerotoninRisk is at Serotonin Syndrome risk because they take Phenelzine (class: MAOI) and Sertraline (class: SSRI). Rule: MAOI + SSRI co-administration is flagged by definition (SerotoninSyndromeRiskPatient ≡ Patient ⊓ ∃takesMedication.MAOI ⊓ ∃takesMedication.SSRI).",
        "P5_Safe: no risk classes inferred — regimen appears safe under current axioms.",
    ]
    for case in test_cases:
        result = polish_explanation(case)
        print("RAW:     ", result["raw"])
        print("POLISHED:", result["polished"])
        print()