"""
FastAPI wrapper for AI Fraud-Review Copilot.

One endpoint, one job: POST /review/{transaction_id} in, structured case
note out. Resist adding endpoints not needed yet -- no health check, no
extra routes, matching SCOPE.md's "bare API" boundary.

Structured logging (Action 22) lives here, not in agent.py -- Action 15 put
the guardrail inside agent.py so every call path (API, direct script, eval)
is protected equally, a correctness concern. Logging is different: it's
specifically about production request handling, and Render only ever runs
this file in production, so this is the one place it needs to be. Plain
logging.info(json.dumps(...)) to stdout -- Render/Docker/GitHub Actions all
capture stdout natively, no new dependency needed for a project this size.

Run locally:
    uvicorn src.api:app --reload

Call it:
    curl -X POST localhost:8000/review/T0001
"""

import json
import logging
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.agent import draft_case_note
from src.guardrail import GuardrailViolation
from src.schemas import CaseNote

logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Fraud-Review Copilot")


class CaseReviewResponse(BaseModel):
    """Mirrors draft_case_note()'s return shape, minus total_tokens -- that's
    ops telemetry for the log, not something the reviewing analyst needs."""
    transaction_id: str
    fraud_pattern_source: str
    tools_called: list[str]
    case_note: CaseNote


@app.post("/review/{transaction_id}", response_model=CaseReviewResponse)
def review_transaction(transaction_id: str):
    """
    Plain `def`, not `async def` -- agent.py's work (Gemini SDK calls, Chroma,
    CSV reads) is entirely blocking, none of it async.
    """
    start = time.monotonic()

    try:
        result = draft_case_note(transaction_id)
    except GuardrailViolation as e:
        # Logging is visibility, not a safety net -- log that a guardrail
        # specifically fired (not just "a 500 happened"), then re-raise
        # unchanged so it still surfaces as a loud, unhandled failure to the
        # caller exactly as before Action 22.
        logger.info(json.dumps({
            "transaction_id": transaction_id,
            "latency_seconds": round(time.monotonic() - start, 2),
            "guardrail_triggered": True,
            "guardrail_detail": str(e),
            "total_tokens": getattr(e, "total_tokens", None),
        }))
        raise

    latency_seconds = round(time.monotonic() - start, 2)

    if "error" in result:
        logger.info(json.dumps({
            "transaction_id": transaction_id,
            "latency_seconds": latency_seconds,
            "status": "not_found",
        }))
        raise HTTPException(status_code=404, detail=result["error"])

    case_note = result["case_note"]
    logger.info(json.dumps({
        "transaction_id": transaction_id,
        "flag_reason": case_note.flag_reason,
        "recommendation": case_note.recommendation.value,
        "confidence": case_note.confidence,
        "latency_seconds": latency_seconds,
        "total_tokens": result.get("total_tokens"),
        "guardrail_triggered": False,
    }))

    return result