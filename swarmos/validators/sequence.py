"""Agent sequence validator."""

from typing import List

from swarmos.core.models import Trace, ValidationResult
from swarmos.validators.base import BaseValidator


class AgentSequenceValidator(BaseValidator):
    """Validates that agents executed in the expected sequence."""

    def validate(self, trace: Trace) -> ValidationResult:
        """
        Validate agent execution sequence.
        
        Expects:
            {
                "type": "agent_sequence",
                "agents": ["agent1", "agent2", "agent3"]
            }
        """
        expected_agents: List[str] = self.expectation.get("agents", [])
        
        if not expected_agents:
            return self._create_result(
                trace,
                passed=False,
                message="No expected agents specified in expectation",
                details={"expected_agents": expected_agents},
            )

        actual_sequence = trace.get_agent_sequence()

        # Check if sequences match
        if actual_sequence == expected_agents:
            return self._create_result(
                trace,
                passed=True,
                message=f"Agent sequence matches: {' → '.join(actual_sequence)}",
                details={
                    "expected": expected_agents,
                    "actual": actual_sequence,
                },
            )

        # Provide detailed mismatch information
        missing_agents = [a for a in expected_agents if a not in actual_sequence]
        extra_agents = [a for a in actual_sequence if a not in expected_agents]
        wrong_order = actual_sequence != expected_agents and not missing_agents and not extra_agents

        message_parts = ["Agent sequence mismatch"]
        if missing_agents:
            message_parts.append(f"missing: {missing_agents}")
        if extra_agents:
            message_parts.append(f"unexpected: {extra_agents}")
        if wrong_order:
            message_parts.append("wrong order")

        return self._create_result(
            trace,
            passed=False,
            message=", ".join(message_parts),
            details={
                "expected": expected_agents,
                "actual": actual_sequence,
                "missing": missing_agents,
                "extra": extra_agents,
            },
        )
