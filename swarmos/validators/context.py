"""Context preservation validator."""

from typing import List, Optional

from swarmos.core.models import EventType, Trace, ValidationResult
from swarmos.validators.base import BaseValidator


class ContextPreservedValidator(BaseValidator):
    """Validates that context (state keys) are preserved after handoffs."""

    def validate(self, trace: Trace) -> ValidationResult:
        """
        Validate context preservation.
        
        Expects:
            {
                "type": "context_preserved",
                "required_keys": ["key1", "key2"],
                "after_handoff": {  # Optional
                    "from": "agent1",
                    "to": "agent2"
                }
            }
        """
        required_keys: List[str] = self.expectation.get("required_keys", [])
        after_handoff = self.expectation.get("after_handoff")

        if not required_keys:
            return self._create_result(
                trace,
                passed=False,
                message="No required_keys specified in expectation",
                details={},
            )

        # If specific handoff is specified, check context after that handoff
        if after_handoff:
            from_agent = after_handoff.get("from")
            to_agent = after_handoff.get("to")
            
            return self._validate_handoff_context(
                trace, from_agent, to_agent, required_keys
            )

        # Otherwise, check if keys are present in final state
        return self._validate_final_context(trace, required_keys)

    def _validate_handoff_context(
        self,
        trace: Trace,
        from_agent: str,
        to_agent: str,
        required_keys: List[str],
    ) -> ValidationResult:
        """Validate context is preserved after a specific handoff."""
        # Find the handoff event
        handoff_event = None
        for event in trace.events:
            if (
                event.event_type == EventType.HANDOFF
                and event.data.get("from_agent") == from_agent
                and event.data.get("to_agent") == to_agent
            ):
                handoff_event = event
                break

        if not handoff_event:
            return self._create_result(
                trace,
                passed=False,
                message=f"Handoff {from_agent} → {to_agent} not found",
                details={
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "required_keys": required_keys,
                },
            )

        # Find next node_entry after the handoff (when to_agent starts)
        next_state_keys = None
        found_handoff = False
        
        for event in trace.events:
            if event == handoff_event:
                found_handoff = True
                continue
            
            if found_handoff and event.event_type == EventType.NODE_ENTRY and event.agent == to_agent:
                next_state_keys = event.data.get("state_keys", [])
                break

        if next_state_keys is None:
            return self._create_result(
                trace,
                passed=False,
                message=f"Could not find state after handoff to {to_agent}",
                details={
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "required_keys": required_keys,
                },
            )

        # Check if required keys are present
        missing_keys = [key for key in required_keys if key not in next_state_keys]

        if not missing_keys:
            return self._create_result(
                trace,
                passed=True,
                message=f"All required keys preserved after {from_agent} → {to_agent}",
                details={
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "required_keys": required_keys,
                    "state_keys": next_state_keys,
                },
            )

        return self._create_result(
            trace,
            passed=False,
            message=f"Context loss detected: missing keys {missing_keys}",
            details={
                "from_agent": from_agent,
                "to_agent": to_agent,
                "required_keys": required_keys,
                "missing_keys": missing_keys,
                "present_keys": next_state_keys,
            },
        )

    def _validate_final_context(
        self, trace: Trace, required_keys: List[str]
    ) -> ValidationResult:
        """Validate required keys are present in final state."""
        # Get the last state_update or node_exit event
        final_state_keys = []
        
        for event in reversed(trace.events):
            if event.event_type in [EventType.STATE_UPDATE, EventType.NODE_ENTRY]:
                final_state_keys = event.data.get("state_keys", [])
                if final_state_keys:
                    break

        missing_keys = [key for key in required_keys if key not in final_state_keys]

        if not missing_keys:
            return self._create_result(
                trace,
                passed=True,
                message="All required keys present in final state",
                details={
                    "required_keys": required_keys,
                    "final_state_keys": final_state_keys,
                },
            )

        return self._create_result(
            trace,
            passed=False,
            message=f"Missing keys in final state: {missing_keys}",
            details={
                "required_keys": required_keys,
                "missing_keys": missing_keys,
                "present_keys": final_state_keys,
            },
        )
