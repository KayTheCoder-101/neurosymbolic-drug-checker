"""
FastAPI service wrapping the neurosymbolic drug-interaction checker.
Every substantive claim in a response traces back to the OWL ontology + HermiT
reasoner; the LLM only translates/paraphrases, never asserts facts on its own.
"""

import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "llm"))

from fastapi import FastAPI
from pydantic import BaseModel
from agent import handle_question

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("drugkr_api")

app = FastAPI(
    title="Neurosymbolic Drug-Interaction Checker",
    description="LLM + OWL ontology hybrid reasoning system. All factual claims "
                "are verified by a Description Logic reasoner (HermiT), not the LLM.",
    version="1.0.0",
)


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    question: str
    raw_explanation: str | None
    polished_explanation: str
    timestamp: str


@app.get("/")
def root():
    return {
        "service": "Neurosymbolic Drug-Interaction Checker",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=QuestionResponse)
def ask(request: QuestionRequest):
    logger.info(f"Received question: {request.question}")

    result = handle_question(request.question)

    logger.info(f"Raw explanation: {result['raw']}")
    logger.info(f"Polished explanation: {result['polished']}")

    return QuestionResponse(
        question=request.question,
        raw_explanation=result["raw"],
        polished_explanation=result["polished"],
        timestamp=datetime.utcnow().isoformat(),
    )
class InconsistencyDemoResponse(BaseModel):
    consistent: bool
    message: str
    timestamp: str


@app.post("/demo/inconsistency", response_model=InconsistencyDemoResponse)
def demo_inconsistency():
    """
    Loads a deliberately dangerous scenario (a pregnant patient prescribed
    an absolute pregnancy-contraindicated drug) and shows that the reasoner
    detects it as logically impossible — not just 'risky', but inconsistent.
    """
    import sys as _sys
    from owlready2 import sync_reasoner, OwlReadyInconsistentOntologyError, default_world

    ontology_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "ontology"
    )
    if ontology_path not in _sys.path:
        _sys.path.insert(0, ontology_path)

    for mod_name in ("build_ontology", "populate_individuals", "populate_bad_case"):
        if mod_name in _sys.modules:
            del _sys.modules[mod_name]
    default_world.ontologies.clear()

    logger.info("Loading bad-case scenario: pregnant patient on Warfarin")

    try:
        import populate_bad_case as bad
        with bad.onto:
            sync_reasoner(infer_property_values=True)
        result = InconsistencyDemoResponse(
            consistent=True,
            message="Unexpected: ontology was consistent (this scenario should have failed).",
            timestamp=datetime.utcnow().isoformat(),
        )
    except OwlReadyInconsistentOntologyError:
        logger.info("Ontology correctly detected as INCONSISTENT (pregnant + Warfarin).")
        result = InconsistencyDemoResponse(
            consistent=False,
            message=("Ontology is INCONSISTENT: a patient was asserted as pregnant "
                      "while taking Warfarin, an absolute pregnancy contraindication. "
                      "The reasoner proved no valid model can satisfy both facts "
                      "simultaneously — this is not a 'risk flag', it is a logical "
                      "contradiction under the ontology's own axioms."),
            timestamp=datetime.utcnow().isoformat(),
        )

    logger.info(f"Demo result: consistent={result.consistent}")
    return result