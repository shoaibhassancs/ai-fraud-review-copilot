"""
FastAPI wrapper for AI Fraud-Review Copilot.

One endpoint, one job: POST /review/{transaction_id} in, structured case
note out. Resist adding endpoints not needed yet — no health check, no
extra routes, matching SCOPE.md's "bare API" boundary.

Run locally:
    uvicorn src.api:app --reload

Call it:
    curl -X POST localhost:8000/review/T0001
"""

from fastapi import FastAPI, HTTPException

from src.agent import draft_case_note
from src.schemas import CaseNote
from pydantic import BaseModel

app = FastAPI(title="AI Fraud-Review Copilot")


class CaseReviewResponse(BaseModel):
    """Mirrors draft_case_note()'s existing, already-proven return shape exactly."""
    transaction_id: str
    fraud_pattern_source: str
    tools_called: list[str]
    case_note: CaseNote


@app.post("/review/{transaction_id}", response_model=CaseReviewResponse)
def review_transaction(transaction_id: str):
    """
    Plain `def`, not `async def` — agent.py's work (Gemini SDK calls, Chroma,
    CSV reads) is entirely blocking, none of it async. FastAPI runs a sync
    `def` path function in its own thread pool automatically; an `async def`
    here would block the event loop instead, a mistake a single curl test
    wouldn't reveal — it only shows up under concurrent load.
    """
    result = draft_case_note(transaction_id)

    if "error" in result:
        # tools.py/agent.py return {"error": ...} rather than raise, so the
        # agent can reason about missing data as part of its normal flow.
        # At the HTTP boundary that doesn't carry over unchanged — an API
        # signals "not found" with a status code instead.
        raise HTTPException(status_code=404, detail=result["error"])

    # No try/except around a genuine agent failure (e.g. generate_with_retry
    # exhausting all attempts) — that propagates up into an honest 500,
    # not smoothed over. Error handling gets added in response to what
    # testing actually reveals (Day 6), not preemptively.
    return result