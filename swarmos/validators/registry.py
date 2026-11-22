"""Validator registry for mapping expectation types to validators."""

from typing import Dict, Type

from swarmos.validators.base import BaseValidator
from swarmos.validators.context import ContextPreservedValidator
from swarmos.validators.handoff import HandoffValidator
from swarmos.validators.sequence import AgentSequenceValidator


class ValidatorRegistry:
    """Registry for validator classes."""

    def __init__(self):
        """Initialize the registry with built-in validators."""
        self._validators: Dict[str, Type[BaseValidator]] = {}
        self._register_builtin_validators()

    def _register_builtin_validators(self) -> None:
        """Register built-in validators."""
        self.register("agent_sequence", AgentSequenceValidator)
        self.register("handoff_occurred", HandoffValidator)
        self.register("context_preserved", ContextPreservedValidator)

    def register(self, expectation_type: str, validator_class: Type[BaseValidator]) -> None:
        """
        Register a validator class for an expectation type.
        
        Args:
            expectation_type: The expectation type string
            validator_class: The validator class to use
        """
        self._validators[expectation_type] = validator_class

    def get_validator(self, expectation: dict) -> BaseValidator:
        """
        Get a validator instance for an expectation.
        
        Args:
            expectation: The expectation configuration
            
        Returns:
            Validator instance
            
        Raises:
            ValueError: If no validator is registered for the expectation type
        """
        expectation_type = expectation.get("type")
        
        if not expectation_type:
            raise ValueError("Expectation missing 'type' field")
        
        validator_class = self._validators.get(expectation_type)
        
        if not validator_class:
            raise ValueError(
                f"No validator registered for type '{expectation_type}'. "
                f"Available types: {list(self._validators.keys())}"
            )
        
        return validator_class(expectation)

    def list_types(self) -> list[str]:
        """List all registered expectation types."""
        return list(self._validators.keys())


# Global registry instance
_registry = ValidatorRegistry()


def get_registry() -> ValidatorRegistry:
    """Get the global validator registry."""
    return _registry
