"""Findings produced by a communication review."""

from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


FindingSeverity = Literal["error", "waste"]
FindingSource = Literal["heuristic", "llm"]

REVIEW_CATEGORIES = {
    "context_loss",
    "empty_handoff",
    "redundant_agent",
    "loop",
    "serial_when_parallel",
    "weak_synthesis",
    "effort_mismatch",
}


class CommunicationFinding(BaseModel):
    """One problem in how agents communicated during a run."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    severity: FindingSeverity
    category: str
    agents: List[str] = Field(default_factory=list)
    message: str
    recommendation: str
    steps: List[str] = Field(default_factory=list)
    fix: Optional[Dict[str, Any]] = None
    event_ids: List[str] = Field(default_factory=list)
    source: FindingSource
