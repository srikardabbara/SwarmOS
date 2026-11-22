"""SwarmOS adapter for instrumenting LangGraph workflows."""

import json
from typing import Any, Dict, Optional
from uuid import uuid4

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from swarmos.core.collector import EventCollector
from swarmos.core.models import Trace, TraceStatus


class SwarmOSCallbackHandler(BaseCallbackHandler):
    """Callback handler that captures LangGraph events."""

    def __init__(self, collector: EventCollector):
        """Initialize with an event collector."""
        super().__init__()
        self.collector = collector
        self._current_node: Optional[str] = None

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a chain (node) starts."""
        node_name = serialized.get("name", serialized.get("id", "unknown"))
        self._current_node = node_name
        
        # Only track if this looks like a node (not nested chains)
        if kwargs.get("parent_run_id") is None:
            self.collector.on_node_start(node_name, inputs)

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a chain (node) ends."""
        if self._current_node and kwargs.get("parent_run_id") is None:
            self.collector.on_node_end(self._current_node, outputs)

    def on_chain_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Called when a chain errors."""
        self.collector.on_error(error, self._current_node)

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts."""
        tool_name = serialized.get("name", "unknown_tool")
        try:
            args = json.loads(input_str) if input_str else {}
        except json.JSONDecodeError:
            args = {"input": input_str}
        
        self.collector.on_tool_call(tool_name, args, self._current_node)

    def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Called when an LLM errors."""
        self.collector.on_error(error, self._current_node)


class SwarmOSAdapter:
    """
    Main adapter for instrumenting LangGraph workflows with SwarmOS.
    
    Example:
        ```python
        from swarmos import SwarmOSAdapter
        from langgraph.graph import StateGraph
        
        # Create your workflow
        graph = StateGraph(State)
        # ... add nodes and edges ...
        
        # Instrument with SwarmOS
        adapter = SwarmOSAdapter(workflow_id="my-workflow")
        app = graph.compile()
        
        # Run with tracing
        result = app.invoke(
            {"messages": [{"role": "user", "content": "Hello"}]},
            config={"callbacks": [adapter.callback_handler]}
        )
        
        # Access the trace
        print(f"Captured {len(adapter.trace.events)} events")
        print(f"Agent sequence: {adapter.trace.get_agent_sequence()}")
        ```
    """

    def __init__(
        self,
        workflow_id: str = "default",
        api_url: Optional[str] = None,
        auto_send: bool = False,
    ):
        """
        Initialize SwarmOS adapter.
        
        Args:
            workflow_id: Identifier for this workflow
            api_url: Optional URL to send traces to SwarmOS backend
            auto_send: Whether to automatically send traces when complete
        """
        self.workflow_id = workflow_id
        self.api_url = api_url
        self.auto_send = auto_send
        
        # Create a new trace
        self.trace = Trace(
            id=str(uuid4()),
            workflow_id=workflow_id,
            input_data={},
            events=[],
        )
        
        # Create event collector
        self.collector = EventCollector(self.trace)
        
        # Create callback handler
        self.callback_handler = SwarmOSCallbackHandler(self.collector)

    def start_trace(self, input_data: Dict[str, Any]) -> None:
        """Start a new trace with input data."""
        self.trace.input_data = input_data
        self.trace.status = TraceStatus.RUNNING

    def end_trace(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark the trace as complete."""
        self.trace.mark_completed(output_data)
        
        if self.auto_send and self.api_url:
            self._send_trace()

    def get_trace(self) -> Trace:
        """Get the current trace."""
        return self.trace

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the trace."""
        return {
            "trace_id": self.trace.id,
            "workflow_id": self.trace.workflow_id,
            "status": self.trace.status.value,
            "event_count": len(self.trace.events),
            "agent_sequence": self.trace.get_agent_sequence(),
            "handoffs": self.trace.get_handoffs(),
            "duration_seconds": (
                (self.trace.completed_at - self.trace.started_at).total_seconds()
                if self.trace.completed_at
                else None
            ),
        }

    def print_summary(self) -> None:
        """Print a human-readable summary."""
        summary = self.get_summary()
        
        print(f"\n{'='*60}")
        print(f"SwarmOS Trace Summary")
        print(f"{'='*60}")
        print(f"Trace ID:     {summary['trace_id']}")
        print(f"Workflow:     {summary['workflow_id']}")
        print(f"Status:       {summary['status']}")
        print(f"Events:       {summary['event_count']}")
        
        if summary['duration_seconds']:
            print(f"Duration:     {summary['duration_seconds']:.2f}s")
        
        print(f"\nAgent Sequence:")
        for i, agent in enumerate(summary['agent_sequence'], 1):
            print(f"  {i}. {agent}")
        
        if summary['handoffs']:
            print(f"\nHandoffs:")
            for from_agent, to_agent in summary['handoffs']:
                print(f"  {from_agent} → {to_agent}")
        
        print(f"{'='*60}\n")

    def _send_trace(self) -> None:
        """Send trace to SwarmOS backend (placeholder)."""
        # TODO: Implement HTTP request to backend API
        pass

    def save_trace(self, filepath: str) -> None:
        """Save trace to a JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.trace.model_dump(), f, indent=2, default=str)
        print(f"Trace saved to {filepath}")

    def load_trace(self, filepath: str) -> Trace:
        """Load trace from a JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)
        self.trace = Trace(**data)
        return self.trace
