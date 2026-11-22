"""Test executor for running scenarios and validating results."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, List, Optional

from swarmos.core.adapter import SwarmOSAdapter
from swarmos.core.models import TestScenario, Trace, ValidationResult
from swarmos.validators.registry import get_registry


@dataclass
class TestResult:
    """Result of running a test scenario."""

    scenario_name: str
    passed: bool
    trace: Trace
    validation_results: List[ValidationResult]
    error: Optional[str] = None
    duration_seconds: float = 0.0

    @property
    def total_validations(self) -> int:
        """Total number of validations run."""
        return len(self.validation_results)

    @property
    def passed_validations(self) -> int:
        """Number of validations that passed."""
        return sum(1 for v in self.validation_results if v.passed)

    @property
    def failed_validations(self) -> int:
        """Number of validations that failed."""
        return sum(1 for v in self.validation_results if not v.passed)


class TestExecutor:
    """Executes test scenarios against workflows."""

    def __init__(self):
        """Initialize test executor."""
        self.validator_registry = get_registry()

    def run_scenario(
        self,
        scenario: TestScenario,
        workflow: Callable,
        workflow_id: Optional[str] = None,
    ) -> TestResult:
        """
        Run a single test scenario.
        
        Args:
            scenario: The test scenario to run
            workflow: Callable that takes input_data and config, returns output
            workflow_id: Optional workflow identifier
            
        Returns:
            TestResult with trace and validation results
        """
        start_time = datetime.utcnow()
        workflow_id = workflow_id or scenario.name

        # Create adapter and start trace
        adapter = SwarmOSAdapter(workflow_id=workflow_id)
        adapter.start_trace(scenario.input_data)

        error = None
        output = None

        try:
            # Run the workflow with SwarmOS callback
            output = workflow(
                scenario.input_data,
                config={"callbacks": [adapter.callback_handler]}
            )
            
            # End trace successfully
            adapter.end_trace(output)

        except Exception as e:
            # Capture error
            error = str(e)
            adapter.trace.mark_failed(error)

        # Run validations
        validation_results = self._run_validations(scenario, adapter.trace)

        # Determine overall pass/fail
        passed = error is None and all(v.passed for v in validation_results)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        return TestResult(
            scenario_name=scenario.name,
            passed=passed,
            trace=adapter.trace,
            validation_results=validation_results,
            error=error,
            duration_seconds=duration,
        )

    def run_scenarios(
        self,
        scenarios: List[TestScenario],
        workflow: Callable,
        workflow_id: Optional[str] = None,
    ) -> List[TestResult]:
        """
        Run multiple test scenarios.
        
        Args:
            scenarios: List of test scenarios
            workflow: Callable workflow
            workflow_id: Optional workflow identifier
            
        Returns:
            List of TestResult objects
        """
        results = []
        
        for scenario in scenarios:
            result = self.run_scenario(scenario, workflow, workflow_id)
            results.append(result)
        
        return results

    def _run_validations(
        self, scenario: TestScenario, trace: Trace
    ) -> List[ValidationResult]:
        """
        Run all validations for a scenario.
        
        Args:
            scenario: The test scenario
            trace: The execution trace
            
        Returns:
            List of ValidationResult objects
        """
        validation_results = []

        for expectation in scenario.expectations:
            try:
                validator = self.validator_registry.get_validator(expectation)
                result = validator.validate(trace)
                validation_results.append(result)
            except Exception as e:
                # Create error validation result
                error_result = ValidationResult(
                    trace_id=trace.id,
                    validation_type=expectation.get("type", "unknown"),
                    passed=False,
                    message=f"Validation error: {str(e)}",
                    details={"expectation": expectation, "error": str(e)},
                )
                validation_results.append(error_result)

        return validation_results

    def print_result(self, result: TestResult) -> None:
        """Print a formatted test result."""
        status = "✓ PASSED" if result.passed else "✗ FAILED"
        
        print(f"\n{'='*70}")
        print(f"{status}: {result.scenario_name}")
        print(f"{'='*70}")
        print(f"Duration: {result.duration_seconds:.2f}s")
        print(f"Validations: {result.passed_validations}/{result.total_validations} passed")
        
        if result.error:
            print(f"\nExecution Error: {result.error}")
        
        print(f"\nValidation Results:")
        print(f"-"*70)
        
        for i, validation in enumerate(result.validation_results, 1):
            status_symbol = "✓" if validation.passed else "✗"
            print(f"{i}. {status_symbol} {validation.validation_type}")
            print(f"   {validation.message}")
            
            if not validation.passed and validation.details:
                # Show relevant details for failed validations
                if "expected" in validation.details and "actual" in validation.details:
                    print(f"   Expected: {validation.details['expected']}")
                    print(f"   Actual:   {validation.details['actual']}")
                elif "missing_keys" in validation.details:
                    print(f"   Missing: {validation.details['missing_keys']}")
        
        print(f"{'='*70}\n")

    def print_summary(self, results: List[TestResult]) -> None:
        """Print a summary of all test results."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        print(f"\n{'='*70}")
        print(f"Test Summary")
        print(f"{'='*70}")
        print(f"Total Tests:  {total}")
        print(f"Passed:       {passed} ({passed/total*100:.1f}%)" if total > 0 else "Passed:       0")
        print(f"Failed:       {failed} ({failed/total*100:.1f}%)" if total > 0 else "Failed:       0")
        print(f"{'='*70}\n")

        if failed > 0:
            print("Failed Tests:")
            for result in results:
                if not result.passed:
                    print(f"  ✗ {result.scenario_name}")
                    if result.error:
                        print(f"    Error: {result.error}")
                    else:
                        print(f"    {result.failed_validations} validation(s) failed")
            print()
