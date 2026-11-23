"""Deterministic checks for broken or wasteful agent communication."""

from swarmos.core.models import EventType, Trace
from swarmos.review.fixes import (
    fix_for_context_loss,
    fix_for_redundant,
    steps_for_context_loss,
    steps_for_empty_handoff,
    steps_for_loop,
    steps_for_redundant,
)
from swarmos.review.models import CommunicationFinding


def _domain_keys(keys: list) -> list[str]:
    return [key for key in keys if key and key != "messages"]


def heuristic_findings(
    trace: Trace,
    expectations: list | None = None,
) -> list[CommunicationFinding]:
    """Flag communication problems that can be seen directly on the trace."""
    required = _required_agents(expectations or [])
    findings: list[CommunicationFinding] = []
    findings.extend(_dropped_context(trace))
    findings.extend(_cleared_context(trace))
    findings.extend(_redundant_agents(trace, required))
    findings.extend(_loops(trace))
    findings.extend(_empty_handoffs(trace))
    return findings


def _required_agents(expectations: list) -> set[str]:
    required: set[str] = set()
    for expectation in expectations:
        if not isinstance(expectation, dict) or expectation.get("type") != "agent_sequence":
            continue
        required.update(expectation.get("agents") or [])
    return required


def _dropped_context(trace: Trace) -> list[CommunicationFinding]:
    findings = []
    for event in trace.events:
        if event.event_type != EventType.NODE_ENTRY:
            continue
        dropped = _domain_keys(event.data.get("dropped_keys") or [])
        if not dropped:
            continue
        agent = event.agent or "the next agent"
        findings.append(
            CommunicationFinding(
                severity="error",
                category="context_loss",
                agents=[agent],
                message=(
                    f"{agent} started without {', '.join(dropped)}, "
                    "which the previous agent had passed along."
                ),
                recommendation=(
                    f"Keep {', '.join(dropped)} on the handoff into {agent} "
                    "instead of dropping it between nodes."
                ),
                steps=[
                    f"{agent} started without {', '.join(dropped)}. The previous node cleared them.",
                    "Stop that previous node from setting those keys to an empty value, so LangGraph keeps them.",
                    "Re-run the scenario and confirm the keys are present for this agent.",
                ],
                event_ids=[event.id],
                source="heuristic",
            )
        )
    return findings


def _cleared_context(trace: Trace) -> list[CommunicationFinding]:
    findings = []
    for event in trace.events:
        if event.event_type != EventType.NODE_EXIT:
            continue
        cleared = _domain_keys(event.data.get("cleared_keys") or [])
        if not cleared:
            continue
        agent = event.agent or "an agent"
        findings.append(
            CommunicationFinding(
                severity="error",
                category="context_loss",
                agents=[agent],
                message=f"{agent} cleared {', '.join(cleared)} before the next agent ran.",
                recommendation=(
                    f"Pass {', '.join(cleared)} through from {agent} "
                    "unless a later agent truly does not need it."
                ),
                steps=steps_for_context_loss(agent, cleared),
                fix=fix_for_context_loss(agent, cleared) if event.agent else None,
                event_ids=[event.id],
                source="heuristic",
            )
        )
    return findings


def _redundant_agents(trace: Trace, required: set[str]) -> list[CommunicationFinding]:
    findings = []
    for event in trace.events:
        if event.event_type != EventType.NODE_EXIT:
            continue
        if event.data.get("changed"):
            continue
        if event.data.get("tool_calls"):
            continue
        agent = event.agent or "an agent"
        required_by_test = bool(event.agent and event.agent in required)
        findings.append(
            CommunicationFinding(
                severity="waste",
                category="redundant_agent",
                agents=[agent],
                message=f"{agent} ran without changing state or calling a tool.",
                recommendation=(
                    f"Give {agent} a distinct job, or remove it from the graph. "
                    "A step that adds nothing still costs a handoff."
                ),
                steps=(
                    [
                        f"{agent} is still in the expected sequence, so SwarmOS will not delete it.",
                        f"Give {agent} work that writes new state or calls a tool.",
                        "Re-run the scenario. This waste finding should disappear once the node changes something.",
                    ]
                    if required_by_test
                    else steps_for_redundant(agent)
                ),
                fix=None if required_by_test or not event.agent else fix_for_redundant(agent),
                event_ids=[event.id],
                source="heuristic",
            )
        )
    return findings


def _loops(trace: Trace) -> list[CommunicationFinding]:
    findings = []
    seen: set[tuple[str, str]] = set()
    reported: set[tuple[str, str]] = set()
    for event in trace.events:
        if event.event_type != EventType.HANDOFF:
            continue
        source = event.data.get("from_agent")
        target = event.data.get("to_agent")
        if not source or not target:
            continue
        pair = (source, target)
        reverse = (target, source)
        if reverse in seen and tuple(sorted(pair)) not in reported:
            reported.add(tuple(sorted(pair)))
            findings.append(
                CommunicationFinding(
                    severity="error",
                    category="loop",
                    agents=[source, target],
                    message=f"{source} and {target} handed control back and forth.",
                recommendation=(
                    "Stop the loop unless the return trip carries new information. "
                    "One of these agents should finish the task or call a tool."
                ),
                steps=steps_for_loop(source, target),
                event_ids=[event.id],
                    source="heuristic",
                )
            )
        seen.add(pair)
    return findings


def _empty_handoffs(trace: Trace) -> list[CommunicationFinding]:
    findings = []
    for event in trace.events:
        if event.event_type != EventType.HANDOFF:
            continue
        passed = _domain_keys(event.data.get("passed_keys") or [])
        excerpt = (event.data.get("excerpt") or "").strip()
        if passed or excerpt:
            continue
        source = event.data.get("from_agent") or "an agent"
        target = event.data.get("to_agent") or "the next agent"
        findings.append(
            CommunicationFinding(
                severity="error",
                category="empty_handoff",
                agents=[agent for agent in (source, target) if agent],
                message=f"The handoff from {source} to {target} carried no state and no message.",
                recommendation=(
                    f"Send {target} the fields it needs, or skip the handoff."
                ),
                steps=steps_for_empty_handoff(source, target),
                event_ids=[event.id],
                source="heuristic",
            )
        )
    return findings
