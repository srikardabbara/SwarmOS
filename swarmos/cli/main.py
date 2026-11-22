"""SwarmOS CLI application."""

import os
import subprocess
import sys
from pathlib import Path

import click


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    SwarmOS - Testing and reliability for LangGraph multi-agent systems.
    
    Test whether your agents collaborate correctly—not just whether
    individual agents produce good answers.
    """
    pass


@cli.command()
@click.argument("directory", type=click.Path(exists=True), default="./tests")
@click.option("--workflow", "-w", help="Python module path to workflow (e.g., myapp.workflow)")
@click.option("--pattern", "-p", default="*.yaml", help="Test file pattern (default: *.yaml)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def test(directory: str, workflow: str, pattern: str, verbose: bool):
    """
    Run test scenarios from YAML files.
    
    Example:
        swarmos test ./tests
        swarmos test ./tests --workflow myapp.workflow
    """
    click.echo("SwarmOS Test Runner")
    click.echo("="*60)
    
    test_dir = Path(directory)
    
    if not test_dir.exists():
        click.echo(f"Error: Directory '{directory}' not found", err=True)
        sys.exit(1)
    
    # Find test files
    test_files = list(test_dir.glob(pattern))
    if pattern == "*.yaml":
        test_files.extend(test_dir.glob("*.yml"))
    
    if not test_files:
        click.echo(f"No test files found in '{directory}' matching '{pattern}'", err=True)
        sys.exit(1)
    
    click.echo(f"Found {len(test_files)} test file(s)")
    
    if not workflow:
        click.echo("\nError: --workflow is required", err=True)
        click.echo("Specify the Python module path to your workflow")
        click.echo("Example: swarmos test --workflow myapp.workflow")
        sys.exit(1)
    
    # TODO: Implement actual test execution
    click.echo(f"\nRunning tests with workflow: {workflow}")
    for test_file in test_files:
        click.echo(f"  - {test_file.name}")
    
    click.echo("\n" + "="*60)
    click.echo("Test execution not yet implemented in CLI")
    click.echo("Use Python API for now:")
    click.echo("  from swarmos.runner import TestExecutor, load_scenario")
    click.echo("="*60)


@cli.command()
@click.option("--port", "-p", default=8000, help="Port to run on (default: 8000)")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
def dashboard(port: int, host: str):
    """
    Start the SwarmOS dashboard (backend API).
    
    Opens the API server which serves the dashboard data.
    Frontend dashboard coming in next phase!
    
    Example:
        swarmos dashboard
        swarmos dashboard --port 3000
    """
    click.echo("Starting SwarmOS Dashboard...")
    click.echo("="*60)
    
    # Check if backend is available
    try:
        from backend.api.main import app
    except ImportError:
        click.echo("Error: Backend dependencies not installed", err=True)
        click.echo("Install with: pip install -e '.[backend]'", err=True)
        sys.exit(1)
    
    click.echo(f"API Server: http://{host}:{port}")
    click.echo(f"API Docs: http://{host}:{port}/docs")
    click.echo("="*60)
    click.echo("\nPress Ctrl+C to stop\n")
    
    try:
        import uvicorn
        uvicorn.run(app, host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        click.echo("\n\nShutting down...")
    except ImportError:
        click.echo("Error: uvicorn not installed", err=True)
        click.echo("Install with: pip install -e '.[backend]'", err=True)
        sys.exit(1)


@cli.command()
@click.option("--name", "-n", default="my-workflow", help="Workflow name")
def init(name: str):
    """
    Initialize a new SwarmOS project.
    
    Creates example workflow and test files to get started quickly.
    
    Example:
        swarmos init
        swarmos init --name my-workflow
    """
    click.echo("Initializing SwarmOS project...")
    click.echo("="*60)
    
    # Create directories
    os.makedirs("tests", exist_ok=True)
    os.makedirs("workflows", exist_ok=True)
    
    workflow_safe_name = name.replace("-", "_").replace(" ", "_")
    
    # Create example workflow
    workflow_path = f"workflows/{workflow_safe_name}.py"
    if not os.path.exists(workflow_path):
        with open(workflow_path, "w") as f:
            f.write(f'''"""
Example multi-agent workflow for {name}.

Modify this workflow to match your use case.
"""

from typing import Annotated, TypedDict
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """State passed between agents."""
    messages: Annotated[list, add_messages]
    # Add your state fields here


def agent_1(state: AgentState) -> dict:
    """First agent in the workflow."""
    return {{"messages": [AIMessage(content="Agent 1 output")]}}


def agent_2(state: AgentState) -> dict:
    """Second agent in the workflow."""
    return {{"messages": [AIMessage(content="Agent 2 output")]}}


def create_workflow():
    """Create the workflow graph."""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent_1", agent_1)
    workflow.add_node("agent_2", agent_2)
    
    workflow.add_edge("agent_1", "agent_2")
    workflow.add_edge("agent_2", END)
    
    workflow.set_entry_point("agent_1")
    
    return workflow.compile()
''')
        click.echo(f"✓ Created {workflow_path}")
    
    # Create example test
    test_path = f"tests/{workflow_safe_name}_test.yaml"
    if not os.path.exists(test_path):
        with open(test_path, "w") as f:
            f.write(f'''name: "{name} basic test"
description: "Test that agents execute in correct sequence"

input:
  messages:
    - role: user
      content: "Test input"

expectations:
  - type: agent_sequence
    agents: ["agent_1", "agent_2"]
  
  - type: handoff_occurred
    from: "agent_1"
    to: "agent_2"
''')
        click.echo(f"✓ Created {test_path}")
    
    click.echo("\n" + "="*60)
    click.echo("Project initialized!")
    click.echo("\nNext steps:")
    click.echo(f"  1. Edit workflows/{workflow_safe_name}.py")
    click.echo(f"  2. Run tests: swarmos test --workflow workflows.{workflow_safe_name}")
    click.echo("  3. Start dashboard: swarmos dashboard")
    click.echo("="*60)


@cli.command()
@click.argument("trace_file", type=click.Path(exists=True))
def show(trace_file: str):
    """
    Display a saved trace file.
    
    Example:
        swarmos show example_trace.json
    """
    import json
    
    click.echo(f"Loading trace from {trace_file}...")
    
    try:
        with open(trace_file, "r") as f:
            trace = json.load(f)
        
        click.echo("\n" + "="*60)
        click.echo(f"Trace: {trace.get('id')}")
        click.echo("="*60)
        click.echo(f"Workflow: {trace.get('workflow_id')}")
        click.echo(f"Status: {trace.get('status')}")
        click.echo(f"Events: {len(trace.get('events', []))}")
        
        agents = []
        for event in trace.get("events", []):
            if event.get("event_type") == "node_entry" and event.get("agent"):
                if event["agent"] not in agents:
                    agents.append(event["agent"])
        
        if agents:
            click.echo(f"\nAgent Sequence: {' → '.join(agents)}")
        
        click.echo("="*60)
        
    except Exception as e:
        click.echo(f"Error loading trace: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
