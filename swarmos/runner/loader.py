"""YAML test scenario loader."""

import os
from pathlib import Path
from typing import List

import yaml

from swarmos.core.models import TestScenario


def load_scenario(filepath: str) -> TestScenario:
    """
    Load a test scenario from a YAML file.
    
    Args:
        filepath: Path to the YAML file
        
    Returns:
        TestScenario object
        
    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is invalid
        ValueError: If scenario is missing required fields
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"Scenario file not found: {filepath}")
    
    with open(filepath, "r") as f:
        data = yaml.safe_load(f)
    
    if not data:
        raise ValueError(f"Empty scenario file: {filepath}")
    
    # Validate required fields
    required_fields = ["name", "input", "expectations"]
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        raise ValueError(
            f"Scenario missing required fields: {missing_fields}. "
            f"Required: {required_fields}"
        )
    
    # Extract fields
    scenario = TestScenario(
        name=data["name"],
        description=data.get("description", ""),
        workflow_path=data.get("workflow"),
        input_data=data["input"],
        expectations=data["expectations"],
        metadata={
            "filepath": str(filepath),
            **data.get("metadata", {})
        },
    )
    
    return scenario


def load_scenarios_from_directory(directory: str, pattern: str = "*.yaml") -> List[TestScenario]:
    """
    Load all test scenarios from a directory.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern for scenario files (default: *.yaml)
        
    Returns:
        List of TestScenario objects
    """
    directory = Path(directory)
    
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    
    scenarios = []
    
    for filepath in directory.glob(pattern):
        try:
            scenario = load_scenario(filepath)
            scenarios.append(scenario)
        except Exception as e:
            print(f"Warning: Failed to load {filepath}: {e}")
    
    # Also check .yml extension
    if pattern == "*.yaml":
        for filepath in directory.glob("*.yml"):
            try:
                scenario = load_scenario(filepath)
                scenarios.append(scenario)
            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}")
    
    return scenarios
