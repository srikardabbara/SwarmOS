"""SwarmOS CLI application."""

import importlib
import os
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
        click.echo("Specify the Python module that defines run_workflow(input_data, config)")
        click.echo("Example: swarmos test ./tests --workflow myapp.workflow")
        sys.exit(1)

    api_url = os.environ.get("SWARMOS_API_URL", "").strip() or None
    api_key = os.environ.get("SWARMOS_API_KEY", "").strip() or None
    if api_url and not api_key:
        click.echo("SWARMOS_API_URL is set but SWARMOS_API_KEY is missing.", err=True)
        sys.exit(1)

    try:
        run_workflow = _load_run_workflow(workflow)
    except click.ClickException as exc:
        click.echo(f"Error: {exc.message}", err=True)
        sys.exit(1)

    from swarmos.runner import TestExecutor, load_scenario

    executor = TestExecutor(api_url=api_url, api_key=api_key)
    failed = 0
    for test_file in test_files:
        click.echo(f"\nRunning {test_file}")
        try:
            scenario = load_scenario(str(test_file))
            result = executor.run_scenario(scenario, run_workflow, workflow_id=scenario.name)
        except Exception as exc:
            click.echo(f"Error: {exc}", err=True)
            failed += 1
            continue
        executor.print_result(result)
        if api_url:
            click.echo(f"Run stored: {result.trace.id}")
        if not result.passed:
            failed += 1

    click.echo("\n" + "=" * 60)
    click.echo(f"{len(test_files) - failed} passed, {failed} failed")
    click.echo("=" * 60)
    if failed:
        sys.exit(1)


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
    Add a collaboration check beside an existing LangGraph app.

    Writes a sample YAML file. The graph stays in the module you already have.
    """
    click.echo("Adding a SwarmOS collaboration check...")
    click.echo("=" * 60)

    os.makedirs("tests", exist_ok=True)
    workflow_safe_name = name.replace("-", "_").replace(" ", "_")
    test_path = f"tests/{workflow_safe_name}.yaml"
    if os.path.exists(test_path):
        click.echo(f"{test_path} already exists. Left it unchanged.")
    else:
        with open(test_path, "w") as f:
            f.write(f'''name: "{name} handoff"
description: "Research reaches the analyst, and the analyst's figure reaches the final report"

input:
  messages:
    - role: user
      content: "Prepare the briefing"

expectations:
  - type: agent_sequence
    agents: ["researcher", "analyst", "presenter"]

  - type: handoff_occurred
    from: "researcher"
    to: "analyst"

  - type: handoff_occurred
    from: "analyst"
    to: "presenter"

  - type: context_preserved
    required_keys: ["research_brief", "analysis", "exec_report"]
''')
        click.echo(f"Created {test_path}")

    click.echo("\nExpose the compiled graph from the module that already builds it:")
    click.echo("")
    click.echo("    def run_workflow(input_data, config):")
    click.echo("        return app.invoke(input_data, config)")
    click.echo("")
    click.echo("Agent names in the YAML must match the names passed to add_node.")
    click.echo("Then run:")
    click.echo(f"    swarmos test ./tests --workflow your_app.workflow")
    click.echo("=" * 60)


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


def _load_run_workflow(module_path: str):
    """Import run_workflow from the customer's module."""
    sys.path.insert(0, os.getcwd())
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        raise click.ClickException(
            f"Could not import {module_path}. Run this from the repo that contains that module."
        ) from exc
    run_workflow = getattr(module, "run_workflow", None)
    if not callable(run_workflow):
        raise click.ClickException(
            f"{module_path} must define run_workflow(input_data, config) that invokes the compiled graph."
        )
    return run_workflow


@cli.command()
@click.argument("trace_id")
@click.argument("finding_id")
def apply(trace_id: str, finding_id: str):
    """
    Apply one safe fix in this repo.

    Downloads the finding from the hosted API and edits the local workflow.
    The server never writes customer source.
    """
    import httpx

    from swarmos.review.fixes import apply_fix

    api_url = os.environ.get("SWARMOS_API_URL", "").strip().rstrip("/")
    api_key = os.environ.get("SWARMOS_API_KEY", "").strip()
    if not api_url or not api_key:
        click.echo("Set SWARMOS_API_URL and SWARMOS_API_KEY.", err=True)
        sys.exit(1)

    try:
        response = httpx.get(
            f"{api_url}/traces/{trace_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20.0,
        )
        response.raise_for_status()
    except Exception as exc:
        click.echo(f"Could not load the run: {exc}", err=True)
        sys.exit(1)

    review = (response.json().get("metadata") or {}).get("communication_review") or {}
    finding = next(
        (item for item in review.get("findings") or [] if item.get("id") == finding_id),
        None,
    )
    if finding is None:
        click.echo(f"Finding {finding_id} was not on this run.", err=True)
        sys.exit(1)

    for step in finding.get("steps") or []:
        click.echo(f"- {step}")

    fix = finding.get("fix")
    if not fix:
        click.echo("This finding has steps, but SwarmOS cannot edit it automatically.", err=True)
        sys.exit(1)

    try:
        result = apply_fix(fix, root=Path.cwd())
    except ValueError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)

    click.echo(result["summary"])
    click.echo(result["path"])
    click.echo("Re-run swarmos test to confirm the handoff check passes.")


if __name__ == "__main__":
    cli()
