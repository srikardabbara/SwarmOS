"""
A research workflow used to demonstrate a context-loss fix.

The planner records draft findings. The researcher used to clear them.
SwarmOS rewrote that return so the researcher keeps the previous value.
The researcher still does no new work, so the review flags that waste and
explains the next change instead of deleting a node the test still expects.

Run with: python examples/dropped_context.py
"""

from typing import Annotated, Any, Dict, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from swarmos.runner import TestExecutor, load_scenario


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    research_topic: str
    research_findings: str
    final_report: str


def planner_agent(state: AgentState) -> dict:
    """Plan the research and leave draft findings for the researcher."""
    user_message = state["messages"][-1].content
    return {
        "research_topic": user_message,
        "research_findings": f"Draft notes for {user_message}",
    }


def researcher_agent(state: AgentState) -> dict:
    """Keep the findings the planner already wrote."""
    return {
        "research_findings": state.get("research_findings", ""),
    }


def writer_agent(state: AgentState) -> dict:
    """Write from whatever findings are still present."""
    findings = state.get("research_findings") or "no findings"
    return {
        "final_report": f"Report: {findings}",
    }


def create_workflow():
    """Create the workflow with a broken researcher handoff."""
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
    return app.invoke(input_data, config)


def main():
    """Run the dropped-context scenario."""
    print("\n" + "=" * 70)
    print("SwarmOS Dropped Context Example")
    print("=" * 70 + "\n")

    scenario = load_scenario("examples/test_scenarios/dropped_context.yaml")
    executor = TestExecutor(api_url="http://localhost:8000")
    result = executor.run_scenario(
        scenario=scenario,
        workflow=run_workflow,
        workflow_id="dropped-context",
    )
    executor.print_result(result)


if __name__ == "__main__":
    main()
