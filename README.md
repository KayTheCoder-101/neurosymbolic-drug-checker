# Regimen Reasoner — Neurosymbolic Drug-Interaction Checker

**Every risk claim is a Description Logic inference, verified by a real reasoner
(HermiT) against a formal OWL ontology — not a lookup table, and not a language
model's guess.**

🔗 **Live demo:** https://lustrous-pika-881461.netlify.app
🔗 **Live API + docs:** https://neurosymbolic-drug-checker.onrender.com/docs

> First request may take up to a minute — the backend runs on free-tier hosting
> that sleeps after inactivity. This is expected, not a bug (see [Known
> Limitations](#known-limitations)).

---

## What this is

A drug-interaction checker where an LLM handles natural language, but every
factual claim about risk is proven by a real Description Logic reasoner
against a hand-built OWL ontology. The LLM has exactly two jobs — extract drug
names from a question, and rephrase the reasoner's own explanation for
readability — and is structurally prevented from doing anything else. It
never asserts a medical fact; it only translates one HermiT already derived.

This isn't a simplification for the demo. The reasoning core (ontology,
HermiT, SWRL) runs standalone with zero LLM involvement, has its own pytest
suite, and can be inspected, queried, and validated independently of the AI
layer entirely.

## Why this is not another chatbot

| | Typical LLM approach | This system |
|---|---|---|
| **How it answers** | Pattern-matches from training data | Asserts facts into a formal ontology, reasoner derives the answer |
| **Failure mode** | Confidently wrong, inconsistent between phrasings | Either derives a named risk class or proves the ontology inconsistent |
| **Can it hallucinate a risk?** | Yes | No — the LLM never generates a risk claim, only rephrases one already proven |
| **Unknown drug or combination** | May guess an answer | Explicitly declines — nothing to reason over |

---

## Architecture

```
FRONTEND (Netlify, static)
  Regimen picker, free-text Ask box, live "Proof Console"
        |
        |  HTTPS / JSON
        v
FASTAPI BACKEND (Render, Docker)
  GET  /drugs
  POST /check-regimen   { drugs: [], pregnant }
  POST /ask              { question }
  Rate-limited (slowapi). CORS locked to the frontend origin.
        |
        |-----------------------------------------|
        v                                          v
REASONING SERVICE (warm)                  LLM LAYER (OpenAI)
  Owlready2 singleton,                      translate_llm:
  loaded once at startup                      NL question -> drug names,
        |                                      category resolution
        |  uses                                (MAOI -> Phenelzine, etc.),
        v                                      pregnancy detection
  OWL ONTOLOGY
    12 drug categories                       polish_explanation:
    6 risk classes as DL restrictions          rephrases the reasoner's
    1 SWRL property-chain rule                 own explanation only,
      (CYP3A4 toxicity)                        never adds a new claim
    1 unsatisfiable class
      (pregnancy contraindication)           Both calls have a tested
        |                                    graceful fallback if OpenAI
        v                                    errors or rate-limits.
  HermiT (via Owlready2)
    subsumption classification
    consistency checking
        |
        v
  Explanation layer
    inferred class -> exact drugs,
    categories, and axiom that
    produced it
```

### Request flow for a free-text question (`/ask`)

```
"Is Warfarin safe during pregnancy?"
        |
        v
[1] OpenAI extracts structure:
      { drugs: ["Warfarin"], pregnant: true, intent: "check_risk" }
        |
        v
[2] Reasoning service asserts a temporary patient
    (pregnant = true, takes Warfarin), then runs HermiT.

      consistent   -> inferred risk class + severity
      inconsistent -> proven logically impossible
                       (pregnancy contraindication)
        |
        v
[3] OpenAI rephrases the reasoner's own text for
    readability. No new claims are permitted.
        |
        v
Response: { raw_explanation, polished_explanation,
            severity, consistent }
```

`/check-regimen` skips steps [1] and [3] entirely. The frontend's drug picker
sends structured input directly, so that path never touches the LLM at all.

---

## The six layers

1. **OWL Ontology** — `Patient`, `Drug`, 12 pharmacological categories
   (`MAOI`, `SSRI`, `Anticoagulant`, and others), and six risk classes defined
   as DL restrictions, for example:

```
   SerotoninSyndromeRiskPatient
     = Patient AND (some takesMedication MAOI) AND (some takesMedication SSRI)
```

   No drug pair is ever hardcoded. Risk emerges purely from category
   membership.

2. **HermiT Reasoner** (via Owlready2) — performs real subsumption
   classification: given a patient's asserted facts, it derives which risk
   classes apply. Nothing in the code tells it the answer.

3. **SWRL property-chain rule** — CYP3A4 toxicity cannot be expressed as a
   simple class intersection, because it depends on which specific enzyme is
   shared between an inhibitor and a substrate, a join across two separate
   facts. This needed a Horn-rule extension on top of the DL restrictions:

```
   Patient(?p), takesMedication(?p, ?d1), CYP3A4Inhibitor(?d1), inhibits(?d1, ?e),
   takesMedication(?p, ?d2), CYP3A4Substrate(?d2), metabolizedBy(?d2, ?e)
     -> CYP3A4ToxicityRiskPatient(?p)
```

4. **Inconsistency detection** — a pregnant patient prescribed Warfarin is not
   flagged "risky." The axiom `ForbiddenPregnancyRegimen = owl:Nothing`
   combined with the asserted facts makes the ontology logically
   unsatisfiable. HermiT proves no valid model can exist and raises
   `OwlReadyInconsistentOntologyError` rather than returning a risk score.

5. **Explanation layer** — walks back from an inferred class to the exact
   drugs, categories, and axiom that produced it. Fully traceable, not a
   black box.

6. **LLM layer, translation only** — two narrow jobs, both under a system
   prompt that explicitly forbids adding or softening any claim. Both calls
   degrade gracefully, falling back to the raw ontology text or a plain
   refusal message, if OpenAI errors or rate-limits.

---

## Tech stack

Python, Owlready2, HermiT (Java), OWL 2 and SWRL, FastAPI, slowapi (rate
limiting), OpenAI API (`gpt-4o-mini`), pytest, Docker, and a plain HTML, CSS,
and JS frontend with no framework and no build step. Deployed on Render
(backend) and Netlify (frontend).

---

## Run it locally

```bash
git clone https://github.com/KayTheCoder-101/neurosymbolic-drug-checker.git
cd neurosymbolic-drug-checker

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "OPENAI_API_KEY=your_key_here" > .env

# Backend
python3 -m uvicorn api.main:app --reload --port 8000

# Frontend, in a second terminal
open frontend/index.html
```

Requires a local Java runtime, since HermiT runs on the JVM. If you don't have
one: `brew install openjdk` on macOS, or your platform's equivalent.

### Run the reasoning core standalone, no API and no LLM

```bash
python reasoning/explain.py
# runs the reasoner and prints inferred classes with explanations

pytest tests/test_reasoning.py -v
# 5 tests: 3 subsumption inferences, 1 negative case, 1 inconsistency case
```

### Run with Docker

```bash
docker build -t drugkr .
docker run -p 8000:8000 --env-file .env drugkr
```

---

## API reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Liveness check |
| `/drugs` | GET | List all drugs known to the ontology |
| `/check-regimen` | POST | `{drugs: string[], pregnant?: bool}`, direct reasoning, no LLM |
| `/ask` | POST | `{question: string}`, free text, routed through the LLM extraction layer |

Full interactive docs are available at
[`/docs`](https://neurosymbolic-drug-checker.onrender.com/docs), a Swagger UI
auto-generated by FastAPI.

---

## Known limitations

- **Free-tier cold starts.** The backend spins down after inactivity, so the
  first request can take up to a minute while it wakes. The frontend shows a
  progressive loading message so this reads as expected rather than broken.
- **OpenAI rate limits.** On lower usage tiers, rapid successive testing can
  occasionally trigger a graceful fallback message instead of a real answer.
  This is expected behavior, not a system failure, since the fallback exists
  specifically to handle it.
- **Ontology scale.** Twenty drugs across twelve categories. Scoped
  deliberately: each of the six reasoning patterns, simple intersection,
  OR-logic, cardinality, SWRL property-chain, and hard inconsistency, is
  demonstrated by at least one real case. Adding more drugs to existing
  categories would add coverage, not new reasoning behavior.
- **No persistence.** Patient data created through `/check-regimen` is
  temporary. It is asserted, reasoned over, and destroyed within a single
  request. There is no database.
- **No authentication.** The API is public and rate-limited, not
  access-controlled. Fine for a portfolio demo, not for handling real patient
  data.
- **Single-threaded reasoning.** The reasoning service uses a lock to
  serialize HermiT calls, since HermiT itself is not thread-safe. Concurrent
  requests queue rather than run in parallel.

---

## Project structure

```
ontology/       OWL ontology definition, individuals, bad-case scenario
reasoning/      HermiT integration, explanation layer, warm reasoning service
llm/            NL to query translation, explanation polishing, orchestration
api/            FastAPI app, rate limiting, CORS
frontend/       Single-page static site
tests/          pytest suite for the reasoning core
Dockerfile
requirements.txt
```