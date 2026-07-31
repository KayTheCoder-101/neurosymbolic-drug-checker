"""
NL -> structured query translation.
Extracts intent + a list of known drug names mentioned in the question —
no longer tied to fixed demo patient IDs.
"""

import os
import json
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

KNOWN_DRUGS = [
    "Alprazolam", "Amiodarone", "Aspirin", "Citalopram", "Clarithromycin",
    "Clopidogrel", "Diazepam", "Fluoxetine", "Haloperidol", "Ibuprofen",
    "Ketoconazole", "Morphine", "Phenelzine", "Pseudoephedrine", "Sertraline",
    "Simvastatin", "Sumatriptan", "Tramadol", "Tranylcypromine", "Warfarin",
]


def translate_llm(nl_question: str) -> dict:
    system_prompt = f"""You translate natural-language questions about drug-interaction
risk into a structured query. Respond in JSON format only.

You do NOT answer the medical question yourself — you only extract structure.

Known drugs: {", ".join(KNOWN_DRUGS)}.

If the question mentions a drug CATEGORY instead of a specific drug name (e.g. "MAOI",
"SSRI", "NSAID", "anticoagulant"), resolve it to one representative known drug using
this mapping:
- MAOI -> Phenelzine
- SSRI -> Sertraline
- NSAID -> Ibuprofen
- Anticoagulant -> Warfarin
- Antiplatelet -> Clopidogrel
- Benzodiazepine -> Diazepam
- Opioid -> Tramadol
- CYP3A4 inhibitor -> Ketoconazole
- CYP3A4 substrate -> Simvastatin
- QT-prolonging agent / QT prolonger -> Haloperidol
- Sympathomimetic -> Pseudoephedrine
- Triptan -> Sumatriptan

Identify which of the known drugs are mentioned or implied by category, using their
exact spelling from the known drugs list above. Also classify intent.

Respond ONLY with JSON in this exact shape:
{{"intent": "check_risk" | "explain_risk" | "unknown",
  "drug_names": ["ExactDrugName1", "ExactDrugName2", ...]}}

Use "explain_risk" when the user asks why/how something is risky.
Use "check_risk" for general risk/safety questions.
Use "unknown" if the question doesn't mention any known drug or category, or isn't about drug risk.
If no known drug or category is mentioned, drug_names should be an empty list."""

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
            "drug_names": parsed.get("drug_names", []),
            "raw_question": nl_question,
        }
    except (OpenAIError, json.JSONDecodeError) as e:
        return {
            "intent": "llm_error",
            "drug_names": [],
            "raw_question": nl_question,
            "error": str(e),
        }


if __name__ == "__main__":
    test_questions = [
        "Is Warfarin and Aspirin risky together?",
        "Why is Ketoconazole with Simvastatin dangerous?",
        "Is Diazepam safe on its own?",
        "What's the weather today?",
        "Can I take an MAOI with an SSRI?",
    ]
    for q in test_questions:
        print(q, "->", translate_llm(q))