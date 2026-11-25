"""LLM review of a trace digest. Skipped when no API key is configured."""

import json
import os
from typing import Any

import httpx

from swarmos.core.models import EventType, Trace
from swarmos.review.models import REVIEW_CATEGORIES, CommunicationFinding

_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4o-mini"
_DIGEST_EVENTS = {
    EventType.NODE_ENTRY,
    EventType.NODE_EXIT,
    EventType.HANDOFF,
    EventType.TOOL_CALL,
    EventType.ERROR,
}


def llm_findings(trace: Trace, expectations: list[dict[str, Any]]) -> tuple[list[CommunicationFinding], str | None]:
    """Ask an OpenAI-compatible chat model to review the digest.

    Returns findings and an error string. The error is None when the call
    succeeded. A missing API key is reported by the caller before this runs.
    """
    api_key = os.environ.get("SWARMOS_LLM_API_KEY", "").strip()
    base_url = os.environ.get("SWARMOS_LLM_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("SWARMOS_LLM_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL

    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(trace, expectations)},
        ],
    }

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=45.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_findings(content), None
    except Exception as exc:
        return [], str(exc)


def _user_prompt(trace: Trace, expectations: list[dict[str, Any]]) -> str:
    digest = []
    for event in trace.events:
        if event.event_type not in _DIGEST_EVENTS:
            continue
        digest.append(
            {
                "id": event.id,
                "type": event.event_type.value,
                "agent": event.agent,
                "data": event.data,
            }
        )
    body = {
        "workflow_id": trace.workflow_id,
        "expectations": expectations,
        "events": digest,
    }
    return json.dumps(body, default=str)


def _parse_findings(content: str) -> list[CommunicationFinding]:
    data = json.loads(content)
    raw_findings = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(raw_findings, list):
        return []

    findings: list[CommunicationFinding] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        category = item.get("category")
        severity = item.get("severity")
        message = item.get("message")
        recommendation = item.get("recommendation")
        if category not in REVIEW_CATEGORIES:
            continue
        if severity not in {"error", "waste"}:
            continue
        if not isinstance(message, str) or not message.strip():
            continue
        if not isinstance(recommendation, str) or not recommendation.strip():
            continue
        agents = item.get("agents") if isinstance(item.get("agents"), list) else []
        event_ids = item.get("event_ids") if isinstance(item.get("event_ids"), list) else []
        raw_steps = item.get("steps") if isinstance(item.get("steps"), list) else []
        steps = [str(step).strip() for step in raw_steps if str(step).strip()]
        findings.append(
            CommunicationFinding(
                severity=severity,
                category=category,
                agents=[str(agent) for agent in agents if agent],
                message=message.strip(),
                recommendation=recommendation.strip(),
                steps=steps or [recommendation.strip()],
                event_ids=[str(event_id) for event_id in event_ids if event_id],
                source="llm",
            )
        )
    return findings


_SYSTEM_PROMPT = """You review one LangGraph multi-agent run. The user already has YAML checks for the contract they wrote. You look for communication failures and wasted handoffs that those checks can miss.

Return JSON only, with this shape:
{"findings": [{"severity": "error" or "waste", "category": "...", "agents": ["..."], "message": "...", "recommendation": "...", "steps": ["..."], "event_ids": ["..."]}]}

steps is 2 or 3 short imperative sentences telling the builder exactly what to change and to re-run. Do not tell them to apply a patch themselves when the change is only "think about it".

Allowed categories:
- context_loss: a fact the next agent needed was missing or cleared
- empty_handoff: control moved with nothing useful attached
- redundant_agent: an agent ran and added nothing
- loop: agents passed control back and forth without new information
- serial_when_parallel: independent work ran one agent after another
- weak_synthesis: several agents produced overlapping results and nobody merged them
- effort_mismatch: a heavy step did a lookup, or a thin step was asked to synthesize
- unused_context: a field with real content was handed to the next agent and that agent's output does not use it. Waste. Name the field and the agents.
- misread: a number, direction, or conclusion in one agent's output contradicts what the previous agent wrote, with no new evidence in between. Error. Quote both versions.

severity is "error" when the collaboration is wrong, and "waste" when it worked but cost a needless step. Cite event ids from the digest. recommendation is one concrete change. Return an empty findings list when the communication looks sound. Do not repeat a problem that is already obvious from a single cleared or dropped key unless you can add a cause the key list does not show.
"""
