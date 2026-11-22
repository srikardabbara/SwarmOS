"""
Example demonstrating SwarmOS test runner with YAML scenarios.

This shows how to:
1. Load test scenarios from YAML files
2. Run automated tests against a workflow
3. Validate agent collaboration
4. Get detailed pass/fail results

Run with: python examples/test_with_yaml.py
"""

from typing import Annotated, Any, Dict, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from swarmos.runner import TestExecutor, load_scenario


# Define state (same as simple_workflow.py)
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    research_topic: str
    research_findings: str
    final_report: str


# Define agents (same as simple_workflow.py)
def planner_agent(state: AgentState) -> dict:
    """Plan the research approach."""
    user_message = state["messages"][-1].content
    return {
        "research_topic": user_message,
    }


def researcher_agent(state: AgentState) -> dict:
    """Conduct research."""
    topic = state.get("research_topic", "unknown")
    findings = f"Research findings about {topic}: [simulated data]"
    return {
        "research_findings": findings,
    }


def writer_agent(state: AgentState) -> dict:
    """Write the final report."""
    findings = state.get("research_findings", "no findings")
    report = f"Report: {findings}"
    return {
        "final_report": report,
    }


def create_workflow():
    """Create the multi-agent workflow."""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("planner", planner_agent)
    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("writer", writer_agent)
    
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", END)
    
    workflow.set_entry_point("planner")
    
    return workflow.compile()


def run_workflow(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper function for running the workflow."""
    app = create_workflow()
    result = app.invoke(input_data, config)
    return result


def main():
    """Run tests from YAML scenarios."""
    print("\n" + "="*70)
    print("SwarmOS Test Runner Example")
    print("="*70 + "\n")

    # Load test scenario from YAML
    print("Loading test scenario from YAML...")
    scenario = load_scenario("examples/test_scenarios/research_workflow.yaml")
    
    print(f"Loaded scenario: {scenario.name}")
    print(f"Description: {scenario.description}")
    print(f"Expectations: {len(scenario.expectations)} validations\n")

    # Create test executor
    executor = TestExecutor()

    # Run the test
    print("Running test...")
    result = executor.run_scenario(
        scenario=scenario,
        workflow=run_workflow,
        workflow_id="research-workflow"
    )

    # Print results
    executor.print_result(result)

    # Print trace summary
    print("Trace Details:")
    print("-"*70)
    print(f"Agent sequence: {' → '.join(result.trace.get_agent_sequence())}")
    print(f"Events captured: {len(result.trace.events)}")
    print(f"Handoffs: {len(result.trace.get_handoffs())}")
    
    for from_agent, to_agent in result.trace.get_handoffs():
        print(f"  - {from_agent} → {to_agent}")
    
    print("\n" + "="*70)
    
    if result.passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed - review validation results above")
    
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
