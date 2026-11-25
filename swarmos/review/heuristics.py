"""Deterministic checks for broken or wasteful agent communication."""

import re

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
    findings.extend(_unused_context(trace))
    findings.extend(_misread(trace))
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


_STOP = {
    "about", "after", "again", "their", "there", "these", "those", "which", "while",
    "would", "could", "should", "other", "into", "from", "with", "that", "this",
    "have", "been", "were", "they", "them", "than", "then", "also", "only", "over",
    "under", "such", "some", "more", "most", "each", "when", "where", "what",
}
_DIRECTION = {
    "grew": "up",
    "grown": "up",
    "growth": "up",
    "increased": "up",
    "increase": "up",
    "rose": "up",
    "rising": "up",
    "higher": "up",
    "fell": "down",
    "fallen": "down",
    "declined": "down",
    "decline": "down",
    "dropped": "down",
    "lower": "down",
    "down": "down",
    "cut": "down",
}
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _unused_context(trace: Trace) -> list[CommunicationFinding]:
    """A long field was handed off and the next agent did not use it."""
    findings = []
    events = list(trace.events)
    for index, event in enumerate(events):
        if event.event_type != EventType.HANDOFF:
            continue
        fields = event.data.get("passed_fields") or {}
        if not isinstance(fields, dict):
            continue
        source = event.data.get("from_agent") or "an agent"
        target = event.data.get("to_agent") or "the next agent"
        sender = next(
            (
                item
                for item in reversed(events[:index])
                if item.event_type == EventType.NODE_EXIT and item.agent == event.data.get("from_agent")
            ),
            None,
        )
        contributed = set((sender.data.get("wrote") or {}).keys()) if sender else set()
        receiver = next(
            (
                item
                for item in events[index + 1 :]
                if item.event_type == EventType.NODE_EXIT and item.agent == event.data.get("to_agent")
            ),
            None,
        )
        if receiver is None:
            continue
        wrote = receiver.data.get("wrote") or {}
        receiver_text = " ".join(str(value) for value in wrote.values()) if isinstance(wrote, dict) else ""
        receiver_text = f"{receiver_text} {receiver.data.get('excerpt') or ''}"
        receiver_words = set(_content_words(receiver_text))
        unused: list[tuple[str, int]] = []
        for key, value in fields.items():
            if key == "messages" or not isinstance(value, str):
                continue
            if contributed and key not in contributed:
                continue
            words = _content_words(value)[:80]
            if len(words) < 12:
                continue
            used = sum(1 for word in words if word in receiver_words)
            if used / len(words) < 0.25:
                unused.append((key, len(value)))
        if not unused:
            continue
        names = ", ".join(key for key, _size in unused)
        tokens = max(1, sum(size for _key, size in unused) // 4)
        findings.append(
            CommunicationFinding(
                severity="waste",
                category="unused_context",
                agents=[source, target],
                message=(
                    f"{source} passed {names} to {target}, about {tokens} tokens, "
                    f"and {target} did not use that material."
                ),
                recommendation=(
                    f"Stop sending {names} on this handoff, or have {target} use the part that should "
                    "change the result. Unused research still costs the tokens to produce and to pass."
                ),
                steps=[
                    f"Read what {source} put in {names}. Compare it with what {target} wrote.",
                    f"If {target} does not need it, remove it from the state {target} receives.",
                    f"If it should change the result, have {target} cite it. Re-run and confirm this waste finding is gone.",
                ],
                event_ids=[event.id, receiver.id],
                source="heuristic",
            )
        )
    return findings


def _misread(trace: Trace) -> list[CommunicationFinding]:
    """A later agent states a different figure than the agent it just heard."""
    findings = []
    exits = [
        event
        for event in trace.events
        if event.event_type == EventType.NODE_EXIT and isinstance(event.data.get("wrote"), dict)
    ]
    for earlier, later in zip(exits, exits[1:]):
        earlier_text = " ".join(str(value) for value in earlier.data["wrote"].values())
        later_text = " ".join(str(value) for value in later.data["wrote"].values())
        earlier_claims = {claim[0]: claim for claim in _claims(earlier_text)}
        for label, number, direction, shown in _claims(later_text):
            previous = earlier_claims.get(label)
            if previous is None:
                continue
            number_changed = abs(previous[1] - number) > 0.5
            direction_changed = bool(previous[2] and direction and previous[2] != direction)
            if not number_changed and not direction_changed:
                continue
            source = earlier.agent or "the previous agent"
            target = later.agent or "the next agent"
            findings.append(
                CommunicationFinding(
                    severity="error",
                    category="misread",
                    agents=[source, target],
                    message=(
                        f"{target} wrote {label} {shown} after {source} wrote {label} {previous[3]}."
                    ),
                    recommendation=(
                        f"Have {target} use the figure {source} wrote, including the direction, "
                        "unless a later calculation is supposed to replace it and is shown in the handoff."
                    ),
                    steps=[
                        f"Open what {source} wrote for {label}: {previous[3]}.",
                        f"Open what {target} wrote for the same thing: {shown}.",
                        "Make the later agent carry the earlier figure forward, or show the calculation that replaced it. Re-run the scenario.",
                    ],
                    event_ids=[earlier.id, later.id],
                    source="heuristic",
                )
            )
            break
    return findings


def _content_words(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z]{5,}", text.lower()) if word not in _STOP]


def _claims(text: str) -> list[tuple[str, float, str | None, str]]:
    """Labeled percentages, with the direction word nearest the number."""
    lowered = text.lower()
    claims = []
    for match in _PERCENT.finditer(lowered):
        window = lowered[max(0, match.start() - 80) : match.start()]
        words = re.findall(r"[a-z]{3,}", window)
        label = None
        direction = None
        for word in reversed(words):
            if direction is None and word in _DIRECTION:
                direction = _DIRECTION[word]
            if label is None and word not in _STOP and word not in _DIRECTION and len(word) >= 4:
                label = word
        if label:
            claims.append((label, float(match.group(1)), direction, match.group(0)))
    return claims
