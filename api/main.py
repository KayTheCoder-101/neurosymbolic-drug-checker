"""
FastAPI service wrapping the neurosymbolic drug-interaction checker.
Every substantive claim in a response traces back to the OWL ontology + HermiT
reasoner; the LLM only translates/paraphrases, never asserts facts on its own.
"""

import sys
import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "llm"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reasoning"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from agent import handle_question
from fastapi import FastAPI, HTTPException, Request
from reasoning_service import get_reasoning_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("drugkr_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: loading ontology and running initial reasoning pass...")
    get_reasoning_service()  # triggers one-time load + reasoning at startup, not per-request
    logger.info("Startup complete. Reasoning service is warm.")
    yield


app = FastAPI(
    title="Neurosymbolic Drug-Interaction Checker",
    description="LLM + OWL ontology hybrid reasoning system. All factual claims "
                "are verified by a Description Logic reasoner (HermiT), not the LLM.",
    version="1.0.0",
    lifespan=lifespan,
)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# Allow a frontend served from a different origin to call this API.
# Tighten allow_origins to your actual deployed frontend URL before going live.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    question: str
    raw_explanation: str | None
    polished_explanation: str
    timestamp: str


class RegimenRequest(BaseModel):
    drugs: list[str] = Field(..., min_length=1, max_length=10,
                              description="List of drug names, e.g. ['Phenelzine', 'Sertraline']")


class RegimenResponse(BaseModel):
    drugs: list[str]
    consistent: bool
    inferred_classes: list[str]
    explanation: str | None
    message: str | None = None
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


@app.get("/drugs")
def list_drugs():
    service = get_reasoning_service()
    return {"drugs": service.list_known_drugs()}


@app.post("/ask", response_model=QuestionResponse)
@limiter.limit("10/minute")
def ask(request: Request, body: QuestionRequest):
    logger.info(f"Received question: {body.question}")
    result = handle_question(body.question)
    logger.info(f"Raw explanation: {result['raw']}")
    logger.info(f"Polished explanation: {result['polished']}")
    return QuestionResponse(
        question=body.question,
        raw_explanation=result["raw"],
        polished_explanation=result["polished"],
        timestamp=datetime.utcnow().isoformat(),
    )


@app.post("/check-regimen", response_model=RegimenResponse)
@limiter.limit("15/minute")
def check_regimen(request: Request, body: RegimenRequest):
    logger.info(f"Checking custom regimen: {body.drugs}")
    service = get_reasoning_service()
    result = service.check_custom_regimen(body.drugs)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result)

    logger.info(f"Regimen result: consistent={result.get('consistent')}, "
                f"classes={result.get('inferred_classes')}")

    return RegimenResponse(
        drugs=body.drugs,
        consistent=result.get("consistent", True),
        inferred_classes=result.get("inferred_classes", []),
        explanation=result.get("explanation"),
        message=result.get("message"),
        timestamp=datetime.utcnow().isoformat(),
    )

class InconsistencyDemoResponse(BaseModel):
    consistent: bool
    message: str
    timestamp: str


@app.post("/demo/inconsistency", response_model=InconsistencyDemoResponse)
def demo_inconsistency():
    """
    Fixed scripted scenario: pregnant patient + Warfarin (absolute
    pregnancy contraindication) -> ontology becomes inconsistent.
    """
    import sys as _sys
    from owlready2 import sync_reasoner, OwlReadyInconsistentOntologyError, default_world

    ontology_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ontology")
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

    # IMPORTANT: this scripted demo loads a SEPARATE module state than the
    # singleton ReasoningService uses for /check-regimen and /ask. Calling
    # this endpoint does not affect or reset the warm service. See note below.
    return result