"""Review how agents communicated during a run."""

import os
from typing import Any

from swarmos.core.models import Trace
from swarmos.review.heuristics import heuristic_findings
from swarmos.review.llm import llm_findings
from swarmos.review.models import CommunicationFinding


def review_trace(trace: Trace, expectations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run deterministic checks, then an LLM review when an API key is set.

    A missing key or a failed model call does not drop the heuristic findings.
    YAML pass/fail stays independent of this review.
    """
    expectations = expectations or []
    findings = heuristic_findings(trace, expectations)
    status = "complete"
    note = None

    api_key = os.environ.get("SWARMOS_LLM_API_KEY", "").strip()
    if not api_key:
        status = "skipped"
        note = "SWARMOS_LLM_API_KEY is not set"
    else:
        extra, error = llm_findings(trace, expectations)
        if error:
            status = "partial"
            note = f"LLM review failed: {error}"
        else:
            findings.extend(_without_duplicates(findings, extra))

    return _payload(findings, status, note)


def _without_duplicates(
    existing: list[CommunicationFinding],
    extra: list[CommunicationFinding],
) -> list[CommunicationFinding]:
    seen = {(item.category, tuple(item.agents), item.message) for item in existing}
    unique = []
    for item in extra:
        key = (item.category, tuple(item.agents), item.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _payload(
    findings: list[CommunicationFinding],
    status: str,
    note: str | None,
) -> dict[str, Any]:
    error_count = sum(1 for item in findings if item.severity == "error")
    waste_count = sum(1 for item in findings if item.severity == "waste")
    payload: dict[str, Any] = {
        "status": status,
        "findings": [item.model_dump() for item in findings],
        "error_count": error_count,
        "waste_count": waste_count,
    }
    if note:
        payload["note"] = note
    return payload
