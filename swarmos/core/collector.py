"""Event collector for capturing LangGraph execution events."""

from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from swarmos.core.models import EventType, Trace, TraceEvent


class EventCollector:
    """Collects and normalizes events from LangGraph callbacks."""

    def __init__(self, trace: Trace):
        """Initialize event collector with a trace."""
        self.trace = trace
        self._node_stack: list[str] = []
        self._current_agent: Optional[str] = None

    def on_node_start(self, node_name: str, state: Dict[str, Any]) -> TraceEvent:
        """Record when a node starts execution."""
        self._node_stack.append(node_name)
        self._current_agent = node_name

        event = TraceEvent(
            trace_id=self.trace.id,
            event_type=EventType.NODE_ENTRY,
            agent=node_name,
            data={
                "node_name": node_name,
                "state_keys": list(state.keys()) if state else [],
                "depth": len(self._node_stack),
            },
        )

        self.trace.add_event(event)
        return event

    def on_node_end(self, node_name: str, output: Any) -> TraceEvent:
        """Record when a node completes execution."""
        if self._node_stack and self._node_stack[-1] == node_name:
            self._node_stack.pop()

        handoff_data = self._extract_handoff(output)

        event = TraceEvent(
            trace_id=self.trace.id,
            event_type=EventType.NODE_EXIT,
            agent=node_name,
            data={
                "node_name": node_name,
                "output_type": type(output).__name__,
                "has_handoff": handoff_data is not None,
            },
        )

        self.trace.add_event(event)

        if handoff_data:
            handoff_event = TraceEvent(
                trace_id=self.trace.id,
                event_type=EventType.HANDOFF,
                agent=node_name,
                data=handoff_data,
                parent_event_id=event.id,
            )
            self.trace.add_event(handoff_event)

        return event

    def on_message_added(self, message: Any, agent: Optional[str] = None) -> TraceEvent:
        """Record when a message is added."""
        message_data = self._extract_message_data(message)

        event = TraceEvent(
            trace_id=self.trace.id,
            event_type=EventType.MESSAGE_ADDED,
            agent=agent or self._current_agent,
            data=message_data,
        )

        self.trace.add_event(event)
        return event

    def on_tool_call(
        self, tool_name: str, args: Dict[str, Any], agent: Optional[str] = None
    ) -> TraceEvent:
        """Record a tool call."""
        event = TraceEvent(
            trace_id=self.trace.id,
            event_type=EventType.TOOL_CALL,
            agent=agent or self._current_agent,
            data={"tool_name": tool_name, "arguments": self._sanitize_data(args)},
        )

        self.trace.add_event(event)
        return event

    def on_error(self, error: Exception, agent: Optional[str] = None) -> TraceEvent:
        """Record an error."""
        event = TraceEvent(
            trace_id=self.trace.id,
            event_type=EventType.ERROR,
            agent=agent or self._current_agent,
            data={
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )

        self.trace.add_event(event)
        return event

    def _extract_handoff(self, output: Any) -> Optional[Dict[str, Any]]:
        """Extract handoff information from node output."""
        if hasattr(output, "goto"):
            return {
                "from_agent": self._current_agent,
                "to_agent": output.goto,
                "update_data": getattr(output, "update", {}),
            }

        if isinstance(output, dict):
            if "goto" in output or "next_agent" in output:
                return {
                    "from_agent": self._current_agent,
                    "to_agent": output.get("goto") or output.get("next_agent"),
                }

        return None

    def _extract_message_data(self, message: Any) -> Dict[str, Any]:
        """Extract data from a LangChain message."""
        if isinstance(message, AIMessage):
            return {
                "type": "ai",
                "content": message.content,
                "tool_calls": [
                    {"name": tc.get("name"), "args": tc.get("args"), "id": tc.get("id")}
                    for tc in getattr(message, "tool_calls", [])
                ],
            }
        elif isinstance(message, HumanMessage):
            return {"type": "human", "content": message.content}
        elif isinstance(message, SystemMessage):
            return {"type": "system", "content": message.content}
        elif isinstance(message, ToolMessage):
            return {
                "type": "tool",
                "content": message.content,
                "tool_call_id": getattr(message, "tool_call_id", None),
            }
        else:
            return {"type": "unknown", "content": str(message)}

    def _sanitize_data(self, data: Any, max_depth: int = 3, current_depth: int = 0) -> Any:
        """Sanitize data for JSON serialization."""
        if current_depth >= max_depth:
            return f"<truncated at depth {max_depth}>"

        if isinstance(data, (str, int, float, bool, type(None))):
            return data
        elif isinstance(data, dict):
            return {
                k: self._sanitize_data(v, max_depth, current_depth + 1)
                for k, v in list(data.items())[:100]
            }
        elif isinstance(data, (list, tuple)):
            return [
                self._sanitize_data(item, max_depth, current_depth + 1)
                for item in list(data)[:100]
            ]
        else:
            if hasattr(data, "__dict__"):
                return self._sanitize_data(data.__dict__, max_depth, current_depth + 1)
            return str(data)[:1000]
