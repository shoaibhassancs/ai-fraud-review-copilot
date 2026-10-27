from pydantic import BaseModel, Field
from enum import Enum

class Recommendation(str, Enum):
    ESCALATE = "escalate"
    CLEAR = "clear"

class CaseNote(BaseModel):
    flag_reason: str          # why it got flagged
    risk_factors: list[str]   # evidence points
    evidence: str              # the explanation text
    recommendation: Recommendation   # only "escalate" or "clear", nothing else
    confidence: float = Field(ge=0.0, le=1.0)   # a number between 0 and 1