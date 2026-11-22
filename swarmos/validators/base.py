"""Base validator interface for SwarmOS."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from swarmos.core.models import Trace, ValidationResult


class BaseValidator(ABC):
    """Base class for all validators."""

    def __init__(self, expectation: Dict[str, Any]):
        """
        Initialize validator with an expectation.
        
        Args:
            expectation: The expectation configuration from test scenario
        """
        self.expectation = expectation
        self.validation_type = expectation.get("type", "unknown")

    @abstractmethod
    def validate(self, trace: Trace) -> ValidationResult:
        """
        Validate the trace against the expectation.
        
        Args:
            trace: The trace to validate
            
        Returns:
            ValidationResult with pass/fail status and details
        """
        pass

    def _create_result(
        self,
        trace: Trace,
        passed: bool,
        message: str,
        details: Dict[str, Any] = None,
    ) -> ValidationResult:
        """Helper to create a validation result."""
        return ValidationResult(
            trace_id=trace.id,
            validation_type=self.validation_type,
            passed=passed,
            message=message,
            details=details or {},
        )
