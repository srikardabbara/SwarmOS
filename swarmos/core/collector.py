"""Event collector for capturing LangGraph execution events."""

from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from swarmos.core.models import EventType, Trace, TraceEvent


class EventCollector:
    """Collects and normalizes events from LangGraph callbacks."""

    _EXCERPT_LIMIT = 240

    def __init__(self, trace: Trace):
        """Initialize event collector with a trace."""
        self.trace = trace
        self._node_stack: list[str] = []
        self._current_agent: Optional[str] = None
        self._state_keys: set[str] = set()
        # Keys that currently hold a non-empty value, plus a short excerpt of each.
        self._meaningful: set[str] = set()
        self._values: Dict[str, str] = {}
        self._tools_this_node: list[str] = []

    def on_node_start(self, node_name: str, state: Dict[str, Any]) -> TraceEvent:
        """Record when a node starts execution."""
        incoming = self._meaningful_snapshot(state if isinstance(state, dict) else {})
        dropped = sorted(self._meaningful - set(incoming))
        added = sorted(set(incoming) - self._meaningful)
        excerpt = self._excerpt(state if isinstance(state, dict) else {})
        passed_keys = sorted(k for k in incoming if k != "messages")

        previous = self._current_agent
        if previous and previous != node_name and not self._handoff_just_recorded(previous, node_name):
            # Fixed edges do not put a target on the node output. The next
            # node starting is the handoff.
            self.trace.add_event(
                TraceEvent(
                    trace_id=self.trace.id,
                    event_type=EventType.HANDOFF,
                    agent=previous,
                    data={
                        "from_agent": previous,
                        "to_agent": node_name,
                        "via": "edge",
                        "passed_keys": passed_keys,
                        "dropped_keys": dropped,
                        "excerpt": excerpt,
                    },
                )
            )

        self._meaningful = set(incoming)
        self._values = {
            key: self._value_excerpt(state.get(key))
            for key in incoming
            if isinstance(state, dict)
        }
        self._node_stack.append(node_name)
        self._current_agent = node_name
        self._tools_this_node = []
        self._remember_keys(state if isinstance(state, dict) else None)

        event = TraceEvent(
            trace_id=self.trace.id,
            event_type=EventType.NODE_ENTRY,
            agent=node_name,
            data={
                "node_name": node_name,
                "state_keys": sorted(self._state_keys),
                "meaningful_keys": sorted(self._meaningful),
                "dropped_keys": dropped,
                "added_keys": added,
                "excerpt": excerpt,
                "depth": len(self._node_stack),
            },
        )

        self.trace.add_event(event)
        return event

    def on_node_end(self, node_name: str, output: Any) -> TraceEvent:
        """Record when a node completes execution."""
        if self._node_stack and self._node_stack[-1] == node_name:
            self._node_stack.pop()

        before = dict(self._values)
        changed = self._apply_output(output if isinstance(output, dict) else None)
        cleared = [key for key in changed if key not in self._meaningful]
        handoff_data = self._extract_handoff(output)

        event = TraceEvent(
            trace_id=self.trace.id,
            event_type=EventType.NODE_EXIT,
            agent=node_name,
            data={
                "node_name": node_name,
                "output_type": type(output).__name__,
                "has_handoff": handoff_data is not None,
                "changed": bool(changed),
                "changed_keys": changed,
                "cleared_keys": cleared,
                "tool_calls": list(self._tools_this_node),
                "excerpt": self._excerpt(output if isinstance(output, dict) else {}),
                "previous_excerpt": self._clip(" | ".join(
                    f"{key}: {value}" for key, value in before.items() if key != "messages" and value
                )),
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

        self._remember_keys(output if isinstance(output, dict) else None)
        self.trace.add_event(
            TraceEvent(
                trace_id=self.trace.id,
                event_type=EventType.STATE_UPDATE,
                agent=node_name,
                data={
                    "node_name": node_name,
                    "state_keys": sorted(self._meaningful),
                    "excerpt": self._clip(" | ".join(
                        f"{key}: {value}"
                        for key, value in sorted(self._values.items())
                        if key != "messages" and value
                    )),
                },
                parent_event_id=event.id,
            )
        )

        return event

    def _meaningful_snapshot(self, state: Dict[str, Any]) -> set[str]:
        """Keys whose current value carries information."""
        return {key for key, value in state.items() if self._is_meaningful(key, value)}

    def _is_meaningful(self, key: Any, value: Any) -> bool:
        if not isinstance(key, str) or key.startswith("__"):
            return False
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, dict)):
            return len(value) > 0
        return True

    def _apply_output(self, output: Optional[Dict[str, Any]]) -> list[str]:
        """Merge a node return value into the meaningful snapshot.

        Returns the keys whose presence or excerpt changed.
        """
        if not output:
            return []
        changed: list[str] = []
        for key, value in output.items():
            if not isinstance(key, str) or key.startswith("__"):
                continue
            previous = self._values.get(key, "")
            if self._is_meaningful(key, value):
                excerpt = self._value_excerpt(value)
                if key not in self._meaningful or excerpt != previous:
                    changed.append(key)
                self._meaningful.add(key)
                self._values[key] = excerpt
            elif key in self._meaningful or previous:
                changed.append(key)
                self._meaningful.discard(key)
                self._values.pop(key, None)
        return sorted(changed)

    def _excerpt(self, state: Dict[str, Any]) -> str:
        """Short text of messages and string fields, capped so a trace stays small."""
        if not isinstance(state, dict):
            return ""
        parts: list[str] = []
        messages = state.get("messages") or []
        if isinstance(messages, (list, tuple)):
            for message in list(messages)[-2:]:
                content = getattr(message, "content", None)
                if content is None and isinstance(message, dict):
                    content = message.get("content")
                if content:
                    parts.append(self._clip(str(content)))
        for key, value in state.items():
            if key == "messages" or not isinstance(key, str) or key.startswith("__"):
                continue
            if isinstance(value, str) and value.strip():
                parts.append(f"{key}: {self._clip(value)}")
        return self._clip(" | ".join(parts))

    def _value_excerpt(self, value: Any) -> str:
        if isinstance(value, str):
            return self._clip(value)
        if isinstance(value, (list, tuple)):
            return self._clip(str(value))
        if isinstance(value, dict):
            return self._clip(str({k: value[k] for k in list(value)[:8]}))
        return self._clip(str(value))

    def _clip(self, text: str) -> str:
        text = " ".join(text.split())
        if len(text) <= self._EXCERPT_LIMIT:
            return text
        return text[: self._EXCERPT_LIMIT - 1] + "…"

    def _handoff_just_recorded(self, from_agent: str, to_agent: str) -> bool:
        """True when node exit already recorded this same handoff."""
        for event in reversed(self.trace.events):
            if event.event_type == EventType.HANDOFF:
                return (
                    event.data.get("from_agent") == from_agent
                    and event.data.get("to_agent") == to_agent
                )
            if event.event_type in {EventType.NODE_EXIT, EventType.STATE_UPDATE}:
                continue
            return False
        return False

    def _remember_keys(self, value: Optional[Dict[str, Any]]) -> None:
        """Keep the state keys seen so far, including keys a node just wrote."""
        if not value:
            return
        for key in value.keys():
            if isinstance(key, str) and not key.startswith("__"):
                self._state_keys.add(key)

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
        self._tools_this_node.append(tool_name)
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
