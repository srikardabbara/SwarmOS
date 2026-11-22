"""
Simple multi-agent workflow example demonstrating SwarmOS instrumentation.

This example creates a 3-agent workflow:
1. Planner - Plans the research approach
2. Researcher - Conducts research
3. Writer - Writes the final output

Run with: python examples/simple_workflow.py
"""

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from swarmos import SwarmOSAdapter


# Define the state schema
class AgentState(TypedDict):
    """State passed between agents."""

    messages: Annotated[list, add_messages]
    research_topic: str
    research_findings: str
    final_report: str


# Define agent nodes
def planner_agent(state: AgentState) -> dict:
    """Plan the research approach."""
    user_message = state["messages"][-1].content
    
    # Simulate planning
    plan = f"Research plan for: {user_message}"
    topic = user_message
    
    return {
        "messages": [AIMessage(content=f"Planning: {plan}")],
        "research_topic": topic,
    }


def researcher_agent(state: AgentState) -> dict:
    """Conduct research."""
    topic = state.get("research_topic", "unknown")
    
    # Simulate research
    findings = f"Research findings about {topic}: [simulated data]"
    
    return {
        "messages": [AIMessage(content=f"Researching: {topic}")],
        "research_findings": findings,
    }


def writer_agent(state: AgentState) -> dict:
    """Write the final report."""
    findings = state.get("research_findings", "no findings")
    
    # Simulate writing
    report = f"Report: {findings}"
    
    return {
        "messages": [AIMessage(content="Writing final report")],
        "final_report": report,
    }


def create_workflow():
    """Create the multi-agent workflow."""
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("planner", planner_agent)
    workflow.add_node("researcher", researcher_agent)
    workflow.add_node("writer", writer_agent)
    
    # Add edges
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", END)
    
    # Set entry point
    workflow.set_entry_point("planner")
    
    return workflow.compile()


def main():
    """Run the workflow with SwarmOS instrumentation."""
    print("\n" + "="*60)
    print("SwarmOS Simple Workflow Example")
    print("="*60 + "\n")
    
    # Create SwarmOS adapter
    adapter = SwarmOSAdapter(workflow_id="simple-research-workflow")
    
    # Create workflow
    app = create_workflow()
    
    # Prepare input
    input_data = {
        "messages": [HumanMessage(content="quantum computing advances in 2026")],
        "research_topic": "",
        "research_findings": "",
        "final_report": "",
    }
    
    # Start trace
    adapter.start_trace(input_data)
    
    print("Running workflow...")
    print(f"Input: {input_data['messages'][0].content}\n")
    
    # Run workflow with SwarmOS callback
    try:
        result = app.invoke(
            input_data,
            config={"callbacks": [adapter.callback_handler]}
        )
        
        # End trace
        adapter.end_trace(result)
        
        print("\n" + "="*60)
        print("Workflow Complete!")
        print("="*60)
        print(f"\nFinal Report: {result.get('final_report', 'N/A')}\n")
        
        # Print SwarmOS summary
        adapter.print_summary()
        
        # Show detailed events
        print("Detailed Events:")
        print("-"*60)
        for i, event in enumerate(adapter.trace.events, 1):
            print(f"{i}. [{event.event_type.value}] {event.agent or 'system'}")
            if event.event_type.value == "node_entry":
                print(f"   → Entering node: {event.data.get('node_name')}")
            elif event.event_type.value == "node_exit":
                print(f"   → Exiting node: {event.data.get('node_name')}")
            elif event.event_type.value == "handoff":
                print(f"   → Handoff: {event.data.get('from_agent')} → {event.data.get('to_agent')}")
        
        print("\n" + "="*60)
        print("✓ SwarmOS successfully captured all agent interactions!")
        print("="*60 + "\n")
        
        # Save trace
        adapter.save_trace("example_trace.json")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        adapter.trace.mark_failed(str(e))


if __name__ == "__main__":
    main()
