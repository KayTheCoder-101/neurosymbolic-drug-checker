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