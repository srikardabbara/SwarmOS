"""
Researcher, analyst, and an executive-report presenter.

The handoffs succeed and the required keys are still there. The analyst
ignores most of the research, and the presenter states a different figure
than the analyst wrote. SwarmOS should show both.

Run with: python examples/exec_report.py
"""

import os
from typing import Annotated, Any, Dict, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from swarmos.runner import TestExecutor, load_scenario


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    research_brief: str
    analysis: str
    exec_report: str


_INTERVIEWS = " ".join(
    f"Interview {index}: the buyer described a renewal, a security review, and a budget meeting."
    for index in range(1, 9)
)


def researcher_agent(state: AgentState) -> dict:
    """Write the brief the analyst is supposed to use."""
    return {
        "research_brief": (
            "Cloud infrastructure spend grew 18% year over year. "
            "The growth is concentrated in three buyers. The sample excludes the public sector. "
            "Caveat: the 18% figure is a trailing observation, not a forecast. "
            f"Interview notes that did not change the figure: {_INTERVIEWS}"
        ),
    }


def analyst_agent(state: AgentState) -> dict:
    """Keep the headline number and drop the caveat and the interviews."""
    return {
        "analysis": "Spend grew 18%. Forecast that same rate forward for next year.",
    }


def presenter_agent(state: AgentState) -> dict:
    """State a different figure and the opposite direction."""
    return {
        "exec_report": "Infrastructure spend fell 11%. Cut the infrastructure budget.",
    }


def create_workflow():
    workflow = StateGraph(AgentState)
    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("analyst", analyst_agent)
    workflow.add_node("presenter", presenter_agent)
    workflow.add_edge("researcher", "analyst")
    workflow.add_edge("analyst", "presenter")
    workflow.add_edge("presenter", END)
    workflow.set_entry_point("researcher")
    return workflow.compile()


def run_workflow(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    app = create_workflow()
    return app.invoke(input_data, config)


def main():
    scenario = load_scenario("examples/test_scenarios/exec_report.yaml")
    executor = TestExecutor(
        api_url=os.environ.get("SWARMOS_API_URL", "http://localhost:8000"),
        api_key=os.environ.get("SWARMOS_API_KEY"),
    )
    result = executor.run_scenario(scenario, run_workflow, workflow_id="exec-report")
    executor.print_result(result)


if __name__ == "__main__":
    main()
