"""Unused research and a changed figure are findings even when the handoff happened."""

from swarmos.core.models import EventType, Trace, TraceEvent
from swarmos.review.heuristics import heuristic_findings


def _event(event_type: EventType, agent: str, data: dict) -> TraceEvent:
    return TraceEvent(trace_id="trace", event_type=event_type, agent=agent, data=data)


def test_unused_research_and_a_changed_figure():
    brief = (
        "Cloud infrastructure spend grew 18% year over year. "
        "The sample excludes the public sector and the figure is not a forecast. "
        + " ".join(f"Interview {index} covered renewals security reviews and budgets." for index in range(12))
    )
    trace = Trace(
        workflow_id="exec-report",
        events=[
            _event(
                EventType.HANDOFF,
                "researcher",
                {
                    "from_agent": "researcher",
                    "to_agent": "analyst",
                    "passed_fields": {"research_brief": brief},
                },
            ),
            _event(
                EventType.NODE_EXIT,
                "analyst",
                {"wrote": {"analysis": "Spend grew 18%. Forecast that same rate forward."}},
            ),
            _event(
                EventType.HANDOFF,
                "analyst",
                {
                    "from_agent": "analyst",
                    "to_agent": "presenter",
                    "passed_fields": {"analysis": "Spend grew 18%. Forecast that same rate forward."},
                },
            ),
            _event(
                EventType.NODE_EXIT,
                "presenter",
                {"wrote": {"exec_report": "Infrastructure spend fell 11%. Cut the budget."}},
            ),
        ],
    )

    findings = heuristic_findings(trace)
    categories = {finding.category for finding in findings}
    assert "unused_context" in categories
    assert "misread" in categories
    unused = next(finding for finding in findings if finding.category == "unused_context")
    assert unused.agents == ["researcher", "analyst"]
    misread = next(finding for finding in findings if finding.category == "misread")
    assert misread.agents == ["analyst", "presenter"]
    assert "11%" in misread.message
    assert "18%" in misread.message
