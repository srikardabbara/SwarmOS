"""Data models for SwarmOS traces, events, and validation results."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events that can be captured during workflow execution."""

    NODE_ENTRY = "node_entry"
    NODE_EXIT = "node_exit"
    STATE_UPDATE = "state_update"
    MESSAGE_ADDED = "message_added"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"
    HANDOFF = "handoff"
    ERROR = "error"


class TraceEvent(BaseModel):
    """A single event captured during workflow execution."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: EventType
    agent: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    parent_event_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "evt_123",
                "trace_id": "trace_456",
                "timestamp": "2024-01-01T12:00:00Z",
                "event_type": "node_entry",
                "agent": "research_agent",
                "data": {"node_name": "research_agent", "state_keys": ["messages"]},
            }
        }


class TraceStatus(str, Enum):
    """Status of a trace execution."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Trace(BaseModel):
    """A complete trace of a workflow execution."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    test_id: Optional[str] = None
    workflow_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: TraceStatus = TraceStatus.RUNNING
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    events: List[TraceEvent] = Field(default_factory=list)
    validation_results: List["ValidationResult"] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_event(self, event: TraceEvent) -> None:
        """Add an event to this trace."""
        event.trace_id = self.id
        self.events.append(event)

    def mark_completed(self, output_data: Optional[Dict[str, Any]] = None) -> None:
        """Mark trace as completed."""
        self.status = TraceStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if output_data:
            self.output_data = output_data

    def mark_failed(self, error: str) -> None:
        """Mark trace as failed."""
        self.status = TraceStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.metadata["error"] = error

    def get_agent_sequence(self) -> List[str]:
        """Extract the sequence of agents that executed."""
        agents = []
        seen = set()
        for event in self.events:
            if event.event_type == EventType.NODE_ENTRY and event.agent:
                if event.agent not in seen:
                    agents.append(event.agent)
                    seen.add(event.agent)
        return agents

    def get_handoffs(self) -> List[tuple[str, str]]:
        """Extract handoff transitions between agents."""
        handoffs = []
        for event in self.events:
            if event.event_type == EventType.HANDOFF:
                from_agent = event.data.get("from_agent")
                to_agent = event.data.get("to_agent")
                if from_agent and to_agent:
                    handoffs.append((from_agent, to_agent))
        return handoffs


class ValidationResult(BaseModel):
    """Result of a validation check."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str
    validation_type: str
    passed: bool
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "val_123",
                "trace_id": "trace_456",
                "validation_type": "handoff_occurred",
                "passed": False,
                "message": "Handoff from research_agent to writer_agent never occurred",
                "details": {
                    "expected_from": "research_agent",
                    "expected_to": "writer_agent",
                    "actual_handoffs": [],
                },
            }
        }


class TestScenario(BaseModel):
    """A test scenario definition."""

    name: str
    description: str
    workflow_path: Optional[str] = None
    input_data: Dict[str, Any]
    expectations: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Support handoff test",
                "description": "Verify support agent hands off to billing",
                "input_data": {
                    "messages": [{"role": "user", "content": "Cancel my subscription"}]
                },
                "expectations": [
                    {"type": "agent_sequence", "agents": ["support_agent", "billing_agent"]},
                    {
                        "type": "handoff_occurred",
                        "from": "support_agent",
                        "to": "billing_agent",
                    },
                ],
            }
        }


# Update forward refs for Trace validation_results
Trace.model_rebuild()
