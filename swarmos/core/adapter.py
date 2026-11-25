"""SwarmOS adapter for instrumenting LangGraph workflows."""

import json
from typing import Any, Dict, Optional
from uuid import uuid4

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from swarmos.core.collector import EventCollector
from swarmos.core.models import Trace, TraceStatus
from swarmos.core.serialize import to_jsonable


class SwarmOSCallbackHandler(BaseCallbackHandler):
    """Callback handler that captures LangGraph events."""

    def __init__(self, collector: EventCollector):
        """Initialize with an event collector."""
        super().__init__()
        self.collector = collector
        self._current_node: Optional[str] = None
        self._node_runs: Dict[Any, str] = {}

    def _graph_node_name(
        self,
        serialized: Optional[Dict[str, Any]],
        **kwargs: Any,
    ) -> Optional[str]:
        """Return the LangGraph node name, or None for graph-level chains.

        Current LangGraph calls ``on_chain_start(None, payload, name=...)`` and
        identifies a node when ``name`` matches ``metadata['langgraph_node']``.
        Older versions passed the name inside ``serialized``.
        """
        metadata = kwargs.get("metadata") or {}
        tags = kwargs.get("tags") or []
        name = kwargs.get("name")
        if not name and isinstance(serialized, dict):
            name = serialized.get("name") or serialized.get("id")

        if not name or not metadata or name != metadata.get("langgraph_node"):
            return None
        if "langsmith:hidden" in tags or name in {"__start__", "__end__"}:
            return None
        return name

    def on_chain_start(
        self,
        serialized: Optional[Dict[str, Any]],
        inputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a chain (node) starts."""
        node_name = self._graph_node_name(serialized, **kwargs)
        if node_name is None:
            return

        run_id = kwargs.get("run_id")
        if run_id is not None:
            self._node_runs[run_id] = node_name
        self._current_node = node_name
        state = inputs if isinstance(inputs, dict) else {}
        self.collector.on_node_start(node_name, state)

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when a chain (node) ends."""
        run_id = kwargs.get("run_id")
        node_name = self._node_runs.pop(run_id, None) if run_id is not None else None
        if node_name is None:
            return
        self.collector.on_node_end(node_name, outputs)
        if self._current_node == node_name:
            self._current_node = None

    def on_chain_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Called when a chain errors."""
        run_id = kwargs.get("run_id")
        if run_id is not None:
            self._node_runs.pop(run_id, None)
        self.collector.on_error(error, self._current_node)

    def on_tool_start(
        self,
        serialized: Optional[Dict[str, Any]],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Called when a tool starts."""
        if isinstance(serialized, dict):
            tool_name = serialized.get("name", "unknown_tool")
        else:
            tool_name = kwargs.get("name") or "unknown_tool"
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
        api_key: Optional[str] = None,
        auto_send: bool = False,
    ):
        """
        Initialize SwarmOS adapter.
        
        Args:
            workflow_id: Identifier for this workflow
            api_url: Optional URL to send traces to SwarmOS backend
            api_key: Project ingest key sent as a bearer token
            auto_send: Whether to automatically send traces when complete
        """
        self.workflow_id = workflow_id
        self.api_url = api_url
        self.api_key = api_key
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
            self.send_trace()

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

    def send_trace(self) -> None:
        """Send the current trace, including validation results, to the backend."""
        self._send_trace()

    def _send_trace(self) -> None:
        """Send trace to SwarmOS backend."""
        if not self.api_url:
            return

        try:
            import httpx

            # Prepare trace data. Workflow state can contain LangChain messages.
            trace_data = {
                "id": self.trace.id,
                "test_id": self.trace.test_id,
                "workflow_id": self.trace.workflow_id,
                "started_at": self.trace.started_at.isoformat(),
                "completed_at": self.trace.completed_at.isoformat() if self.trace.completed_at else None,
                "status": self.trace.status.value,
                "input_data": to_jsonable(self.trace.input_data),
                "output_data": to_jsonable(self.trace.output_data),
                "metadata": to_jsonable(self.trace.metadata),
                "events": [
                    {
                        "id": e.id,
                        "trace_id": e.trace_id,
                        "timestamp": e.timestamp.isoformat(),
                        "event_type": e.event_type.value,
                        "agent": e.agent,
                        "data": to_jsonable(e.data),
                        "parent_event_id": e.parent_event_id,
                    }
                    for e in self.trace.events
                ],
                "validation_results": [
                    {
                        "id": v.id,
                        "trace_id": v.trace_id,
                        "validation_type": v.validation_type,
                        "passed": v.passed,
                        "message": v.message,
                        "details": to_jsonable(v.details),
                        "timestamp": v.timestamp.isoformat(),
                    }
                    for v in self.trace.validation_results
                ],
            }

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            # Send to backend
            response = httpx.post(
                f"{self.api_url}/traces",
                json=trace_data,
                headers=headers,
                timeout=10.0,
            )
            response.raise_for_status()
            print(f"✓ Trace sent to {self.api_url}")

        except ImportError:
            print("Warning: httpx not installed. Run: pip install httpx")
        except Exception as e:
            print(f"Warning: Failed to send trace to backend: {e}")

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
