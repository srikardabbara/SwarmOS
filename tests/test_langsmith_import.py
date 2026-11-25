"""LangSmith traces become handoffs SwarmOS can review, without keeping the API key."""

import os
import tempfile
from pathlib import Path

_db_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_db_dir) / 'langsmith.db'}"
os.environ["SWARMOS_DASHBOARD_ORIGIN"] = "http://localhost:3000"

from fastapi.testclient import TestClient  # noqa: E402

from backend.api.main import app  # noqa: E402
from backend.models.database import init_db  # noqa: E402
from swarmos.langsmith.import_trace import (  # noqa: E402
    LangSmithImportError,
    import_latest_langsmith,
    parse_langsmith_url,
    runs_to_trace,
    tracing_project,
)

init_db()
client = TestClient(app)

_TRACE = "11111111-1111-4111-8111-111111111111"
_PROJECT = "22222222-2222-4222-8222-222222222222"
_URL = f"https://smith.langchain.com/o/org/projects/p/{_PROJECT}/r/{_TRACE}"

_TASK = (
    "Build a weekly priority list from the calendar and include the owners and dates "
    "for every launch interview note that the researcher collected yesterday morning."
)


def _runs() -> list[dict]:
    return [
        {
            "id": "root",
            "name": "Schedule manager",
            "run_type": "chain",
            "trace_id": _TRACE,
            "session_id": _PROJECT,
            "start_time": "2026-11-24T17:00:00Z",
            "end_time": "2026-11-24T17:00:05Z",
            "inputs": {"messages": [{"type": "human", "content": "Plan my week"}]},
            "outputs": {"messages": [{"type": "ai", "content": "Here is the plan."}]},
        },
        {
            "id": "llm",
            "name": "ChatAnthropic",
            "run_type": "llm",
            "parent_run_id": "root",
            "start_time": "2026-11-24T17:00:01Z",
            "inputs": {
                "messages": [
                    {
                        "type": "system",
                        "content": "You are a schedule manager. Ask weekly-priority-todo for the list.",
                    }
                ]
            },
            "outputs": {"messages": [{"type": "ai", "content": "Asking the todo agent."}]},
        },
        {
            "id": "task",
            "name": "task",
            "run_type": "tool",
            "parent_run_id": "root",
            "start_time": "2026-11-24T17:00:02Z",
            "inputs": {"subagent_type": "weekly-priority-todo", "description": _TASK},
            "outputs": {"output": "Three priorities. Launch on Friday."},
        },
        {
            "id": "write",
            "name": "write_file",
            "run_type": "tool",
            "parent_run_id": "root",
            "start_time": "2026-11-24T17:00:03Z",
            "inputs": {"path": "/tmp/plan.md"},
            "outputs": {"output": "wrote plan.md"},
        },
    ]


def test_trace_url_keeps_the_project_and_run():
    parsed = parse_langsmith_url(_URL)
    assert parsed["project_id"] == _PROJECT
    assert parsed["run_id"] == _TRACE
    assert parsed["api_base"] == "https://api.smith.langchain.com"


def test_other_sites_are_rejected():
    try:
        parse_langsmith_url("https://example.com/projects/p/" + _PROJECT)
    except LangSmithImportError as exc:
        assert "smith.langchain.com" in str(exc)
    else:
        raise AssertionError("expected a rejection")


def test_middleware_steps_stay_inside_one_agent():
    steps = [
        "SkillsMiddleware.before_agent",
        "PatchToolCallsMiddleware.before_agent",
        "model",
        "tools",
        "model_output_limit_guard.after_model",
        "TodoListMiddleware.after_model",
        "SkillsFlushMiddleware.after_agent",
    ]
    runs = [
        {
            "id": "root",
            "name": "deep_agent",
            "run_type": "chain",
            "start_time": "2026-11-24T17:00:00Z",
            "inputs": {"messages": [{"type": "human", "content": "This is a test"}]},
            "outputs": {"messages": [{"type": "ai", "content": "Got it."}]},
        }
    ]
    for index, name in enumerate(steps, start=1):
        runs.append(
            {
                "id": f"step-{index}",
                "name": name,
                "run_type": "chain",
                "parent_run_id": "root",
                "start_time": f"2026-11-24T17:00:0{index}Z",
                "extra": {"metadata": {"langgraph_node": name}},
            }
        )
    trace = runs_to_trace(runs, source_url=_URL, project_id=_PROJECT)
    assert trace.get_handoffs() == []
    assert {event.agent for event in trace.events} == {"deep_agent"}
    assert trace.metadata["langsmith"]["note"].startswith("This trace is one agent")


def test_named_graph_nodes_are_still_handoffs():
    def node(node_id: str, name: str, text: str, start: str) -> dict:
        return {
            "id": node_id,
            "name": name,
            "run_type": "chain",
            "start_time": start,
            "extra": {"metadata": {"langgraph_node": name}},
            "outputs": {"messages": [{"type": "ai", "content": text}]},
        }

    trace = runs_to_trace(
        [
            node("a", "researcher", "Found three interviews.", "2026-11-24T17:00:01Z"),
            node("b", "SkillsMiddleware.before_agent", "", "2026-11-24T17:00:02Z"),
            node("c", "writer", "The brief is ready.", "2026-11-24T17:00:03Z"),
        ],
        source_url=_URL,
        project_id=_PROJECT,
    )
    assert trace.get_handoffs() == [("researcher", "writer")]


def test_subagent_call_becomes_a_handoff_and_records_the_setup():
    trace = runs_to_trace(_runs(), source_url=_URL, project_id=_PROJECT)
    assert trace.get_handoffs() == [("Schedule manager", "weekly-priority-todo")]
    setup = trace.metadata["langsmith"]
    assert setup["main_agent"] == "Schedule manager"
    assert setup["subagents"] == ["weekly-priority-todo"]
    assert "write_file" in setup["tools"]
    assert "weekly-priority-todo" in setup["instructions"]
    from swarmos.review import review_trace

    findings = review_trace(trace)
    assert "unused_context" in {item["category"] for item in findings["findings"]}


def test_tracing_project_name_matches_a_reference_free_session():
    class _Response:
        status_code = 200

        def json(self):
            return {"items": [{"id": _PROJECT, "name": "Schedule Manager", "type": "AGENT"}], "next_cursor": None}

    class _Client:
        def get(self, url, headers=None, params=None):
            assert url.endswith("/api/v2/sessions")
            assert params["type"] == "AGENT"
            return _Response()

    from swarmos.langsmith.import_trace import _project_id_by_name

    assert _project_id_by_name(_Client(), "https://api.smith.langchain.com", {}, "schedule manager") == _PROJECT


def test_agent_display_name_resolves_to_the_tracing_project():
    agent_id = "fleet-5c9c5790231840c49d827ca12a1dc163"

    class _Response:
        def __init__(self, body):
            self.status_code = 200
            self._body = body

        def json(self):
            return self._body

    class _Client:
        def get(self, url, headers=None, params=None):
            if url.endswith("/api/v2/sessions"):
                return _Response({"items": [], "next_cursor": None})
            if url.endswith("/api/v1/agents") and (params or {}).get("search") == "Schedule Manager":
                return _Response({"items": [{"id": agent_id, "name": "Schedule Manager"}], "next_cursor": None})
            if url.endswith("/api/v1/agents/" + agent_id):
                return _Response(
                    {
                        "id": agent_id,
                        "name": "Schedule Manager",
                        "environments": [
                            {"environment": "DEVELOPMENT", "tracer_session_id": "33333333-3333-4333-8333-333333333333"},
                            {"environment": "PRODUCTION", "tracer_session_id": _PROJECT},
                        ],
                    }
                )
            raise AssertionError(url)

    from swarmos.langsmith.import_trace import _project_id_by_name

    assert _project_id_by_name(_Client(), "https://api.smith.langchain.com", {}, "Schedule Manager") == _PROJECT


def test_agent_id_resolves_to_the_tracing_project():
    agent_id = "fleet-5c9c5790231840c49d827ca12a1dc163"

    class _Response:
        def __init__(self, body):
            self.status_code = 200
            self._body = body

        def json(self):
            return self._body

    class _Client:
        def get(self, url, headers=None, params=None):
            if url.endswith("/api/v2/sessions"):
                return _Response({"items": [], "next_cursor": None})
            if url.endswith("/api/v1/agents/" + agent_id):
                return _Response(
                    {
                        "id": agent_id,
                        "name": "Schedule Manager",
                        "environments": [{"environment": "PRODUCTION", "tracer_session_id": _PROJECT}],
                    }
                )
            raise AssertionError(url)

    from swarmos.langsmith.import_trace import _project_id_by_name

    assert _project_id_by_name(_Client(), "https://api.smith.langchain.com", {}, agent_id) == _PROJECT


def test_tracing_page_address_is_the_project():
    parsed = tracing_project(f"https://smith.langchain.com/o/org/projects/p/{_PROJECT}")
    assert parsed["project_id"] == _PROJECT
    assert tracing_project("Schedule Manager")["project_name"] == "Schedule Manager"


def test_latest_command_reads_the_newest_root(monkeypatch):
    def fake_query(client, base, headers, project_id=None, trace_id=None, filter_string=None, is_root=None, limit=100):
        if is_root:
            return [
                {"id": "old", "trace_id": "old", "name": "deep_agent", "start_time": "2026-11-23T00:00:00Z"},
                {"id": "new", "trace_id": "new-trace", "name": "deep_agent", "start_time": "2026-11-24T17:22:00Z"},
            ]
        assert trace_id == "new-trace"
        return _runs()

    monkeypatch.setattr("swarmos.langsmith.import_trace._query_runs", fake_query)
    trace = import_latest_langsmith("ls-secret", f"https://smith.langchain.com/o/org/projects/p/{_PROJECT}")
    assert trace.metadata["langsmith"]["latest"] is True
    assert trace.workflow_id == "Schedule manager"


def test_import_stores_the_run_and_forgets_the_langsmith_key(monkeypatch):
    def fake_fetch(api_key, parsed):
        assert api_key == "ls-secret"
        assert parsed["run_id"] == _TRACE
        return _runs()

    monkeypatch.setattr("swarmos.langsmith.import_trace.fetch_runs", fake_fetch)
    created = client.post("/projects", json={"name": "Schedule manager"})
    key = created.json()["api_key"]
    response = client.post(
        "/langsmith/import",
        headers={"Authorization": f"Bearer {key}"},
        json={"api_key": "ls-secret", "url": _URL},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["workflow_id"] == "Schedule manager"
    dumped = str(body)
    assert "ls-secret" not in dumped
    loaded = client.get(f"/traces/{body['id']}", headers={"Authorization": f"Bearer {key}"})
    events = loaded.json()["events"]
    assert any(event["event_type"] == "handoff" for event in events)
    assert loaded.json()["metadata"]["langsmith"]["subagents"] == ["weekly-priority-todo"]
