"""Handoff validator."""

from swarmos.core.models import EventType, Trace, ValidationResult
from swarmos.validators.base import BaseValidator


class HandoffValidator(BaseValidator):
    """Validates that a handoff occurred between specific agents."""

    def validate(self, trace: Trace) -> ValidationResult:
        """
        Validate handoff occurrence.
        
        Expects:
            {
                "type": "handoff_occurred",
                "from": "agent1",
                "to": "agent2"
            }
        """
        from_agent = self.expectation.get("from")
        to_agent = self.expectation.get("to")

        if not from_agent or not to_agent:
            return self._create_result(
                trace,
                passed=False,
                message="Missing 'from' or 'to' agent in expectation",
                details={"from": from_agent, "to": to_agent},
            )

        # Get all handoffs from trace
        handoffs = trace.get_handoffs()

        # Check if the specific handoff occurred
        handoff_found = (from_agent, to_agent) in handoffs

        if handoff_found:
            return self._create_result(
                trace,
                passed=True,
                message=f"Handoff occurred: {from_agent} → {to_agent}",
                details={
                    "expected_from": from_agent,
                    "expected_to": to_agent,
                    "all_handoffs": [(f, t) for f, t in handoffs],
                },
            )

        # Handoff not found - provide helpful details
        # Check if from_agent exists
        agent_sequence = trace.get_agent_sequence()
        
        if from_agent not in agent_sequence:
            message = f"Source agent '{from_agent}' never executed"
        elif to_agent not in agent_sequence:
            message = f"Target agent '{to_agent}' never executed"
        else:
            message = f"Handoff {from_agent} → {to_agent} did not occur"

        return self._create_result(
            trace,
            passed=False,
            message=message,
            details={
                "expected_from": from_agent,
                "expected_to": to_agent,
                "actual_handoffs": [(f, t) for f, t in handoffs],
                "agent_sequence": agent_sequence,
            },
        )
