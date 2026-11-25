"""Turn a LangSmith trace into the handoffs SwarmOS already reviews.

Fleet and Studio agents are instructions stored in LangSmith. The chat shows
the person and the main agent. A subagent call is a tool run on the trace,
and the instructions are the system message on the model call. This module
reads those and leaves the LangSmith API key out of the stored run.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable
from urllib.parse import parse_qs, quote, urlparse
from uuid import uuid4

import httpx

from swarmos.core.models import EventType, Trace, TraceEvent, TraceStatus
from swarmos.review import review_trace

_UUID = (
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_HOSTS = {"smith.langchain.com": "https://api.smith.langchain.com", "eu.smith.langchain.com": "https://eu.api.smith.langchain.com"}
_GENERIC = {
    "langgraph",
    "runnablesequence",
    "runnablelambda",
    "runnableparallel",
    "call_model",
    "agent",
    "tools",
    "model",
    "chatprompttemplate",
    "prompt",
}
_CLIP = 800
_ENV_ORDER = ("PRODUCTION", "STAGING", "DEVELOPMENT", "LOCAL")


class LangSmithImportError(Exception):
    """The trace link or the LangSmith response cannot be used."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def import_latest_langsmith(api_key: str, project: str) -> Trace:
    """Review the newest root run in a LangSmith project.

    ``project`` is the name on the LangSmith Tracing page,
    or the address of that Tracing page. The same value is reused on every run.
    """
    key = (api_key or "").strip()
    if not key:
        raise LangSmithImportError("Set LANGSMITH_API_KEY to the key from LangSmith Settings, API Keys.")
    target = tracing_project(project)
    headers = {"x-api-key": key}
    base = str(target["api_base"])
    try:
        with httpx.Client(timeout=30.0) as client:
            project_id = target["project_id"] or _project_id_by_name(
                client, base, headers, str(target["project_name"])
            )
            roots = _query_runs(client, base, headers, project_id=project_id, is_root=True, limit=5)
            if not roots:
                raise LangSmithImportError(
                    "That LangSmith project has no traces yet. Send the agent a message, then run this again."
                )
            root = max(roots, key=lambda item: str(item.get("start_time") or ""))
            trace_id = str(root.get("trace_id") or root.get("id"))
            runs = _query_runs(client, base, headers, project_id=project_id, trace_id=trace_id)
    except httpx.HTTPError as exc:
        raise LangSmithImportError(
            "SwarmOS could not reach LangSmith. Check the connection and run the command again.",
            status_code=502,
        ) from exc
    if not runs:
        runs = [root]
    trace = runs_to_trace(
        runs,
        source_url=f"https://smith.langchain.com/projects/p/{project_id}",
        project_id=project_id,
    )
    trace.metadata["communication_review"] = review_trace(trace)
    trace.metadata["langsmith"]["latest"] = True
    return trace


def tracing_project(value: str) -> dict[str, str | None]:
    """Accept an agent name, a project id, or the Tracing page address."""
    import re

    text = (value or "").strip()
    if not text:
        raise LangSmithImportError(
            "Set LANGSMITH_PROJECT to the name on your LangSmith Tracing page."
        )
    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlparse(text)
        api_base = _HOSTS.get((parsed.hostname or "").lower())
        if api_base is None:
            raise LangSmithImportError("Use the Tracing page address from smith.langchain.com.")
        project_id = _path_id([part for part in parsed.path.split("/") if part], "p")
        if not project_id:
            raise LangSmithImportError(
                "Open the agent's Tracing page, the list of runs, and copy that address into LANGSMITH_PROJECT."
            )
        return {"api_base": api_base, "project_id": project_id, "project_name": None}
    if re.fullmatch(_UUID, text):
        return {"api_base": "https://api.smith.langchain.com", "project_id": text, "project_name": None}
    return {"api_base": "https://api.smith.langchain.com", "project_id": None, "project_name": text}


def import_langsmith_trace(api_key: str, url: str, fetch: Callable[..., list[dict]] | None = None) -> Trace:
    """Fetch one trace and review what the agents passed to each other."""
    key = (api_key or "").strip()
    if not key:
        raise LangSmithImportError("Paste a LangSmith API key. SwarmOS uses it once and does not save it.")
    parsed = parse_langsmith_url(url)
    runs = (fetch or fetch_runs)(key, parsed)
    if not runs:
        raise LangSmithImportError("LangSmith returned no steps for that trace.")
    trace = runs_to_trace(runs, source_url=url.strip(), project_id=parsed.get("project_id"))
    trace.metadata["communication_review"] = review_trace(trace)
    return trace


def parse_langsmith_url(url: str) -> dict[str, str | None]:
    """Pull the project, run, or thread id out of a LangSmith page address."""
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").lower()
    api_base = _HOSTS.get(host)
    if api_base is None:
        raise LangSmithImportError(
            "Paste the address from the LangSmith trace page. It starts with smith.langchain.com."
        )
    parts = [part for part in parsed.path.split("/") if part]
    query = parse_qs(parsed.query)
    run_id = _path_id(parts, "r")
    for key in ("peek", "peeked_trace", "trace_id", "run_id"):
        if not run_id and query.get(key):
            run_id = query[key][0]
    thread_id = _path_id(parts, "t")
    if not run_id and not thread_id:
        raise LangSmithImportError(
            "That page has no trace. In LangSmith, open View trace, then copy the address in the browser bar."
        )
    return {
        "api_base": api_base,
        "project_id": _path_id(parts, "p"),
        "run_id": run_id,
        "thread_id": thread_id,
    }


def fetch_runs(api_key: str, parsed: dict[str, str | None]) -> list[dict]:
    """Load every run in the trace. The API key is sent only to LangSmith."""
    headers = {"x-api-key": api_key}
    base = str(parsed["api_base"])
    try:
        with httpx.Client(timeout=30.0) as client:
            if parsed.get("run_id"):
                run = _get_json(client, f"{base}/api/v1/runs/{parsed['run_id']}", headers)
                trace_id = str(run.get("trace_id") or parsed["run_id"])
                project_id = parsed.get("project_id") or run.get("session_id")
                return _query_runs(client, base, headers, project_id=project_id, trace_id=trace_id)
            thread_id = parsed.get("thread_id")
            project_id = parsed.get("project_id")
            if not project_id or not thread_id:
                raise LangSmithImportError(
                    "That thread link is missing the LangSmith project. Open View trace and copy that address."
                )
            filter_string = (
                'and(in(metadata_key, ["session_id","thread_id"]), '
                f'eq(metadata_value, "{thread_id}"))'
            )
            roots = _query_runs(client, base, headers, project_id=project_id, filter_string=filter_string)
            if not roots:
                raise LangSmithImportError("LangSmith has no trace for that thread yet. Send the agent a message first.")
            root = max(roots, key=lambda item: str(item.get("start_time") or ""))
            trace_id = str(root.get("trace_id") or root.get("id"))
            return _query_runs(client, base, headers, project_id=project_id, trace_id=trace_id)
    except httpx.HTTPError as exc:
        raise LangSmithImportError(
            "SwarmOS could not reach LangSmith. Check the connection and try the trace address again.",
            status_code=502,
        ) from exc


def runs_to_trace(runs: list[dict], source_url: str, project_id: str | None) -> Trace:
    """Map LangSmith runs onto node exits and handoffs."""
    ordered = sorted(runs, key=lambda run: str(run.get("start_time") or ""))
    if any(_subagent_name(run) for run in ordered):
        trace = _from_subagents(ordered)
    elif any(_graph_node(run) for run in ordered):
        trace = _from_graph_nodes(ordered)
    else:
        trace = _from_single_agent(ordered)
    trace.metadata["langsmith"] = _configuration(ordered, source_url, project_id, trace)
    return trace


def _from_subagents(runs: list[dict]) -> Trace:
    main = _main_name(runs)
    trace = _new_trace(main, runs)
    _add(trace, EventType.NODE_ENTRY, main, {})
    for run in runs:
        subagent = _subagent_name(run)
        if not subagent:
            continue
        passed = _task_text(run.get("inputs"))
        returned = _best_text(run, runs)
        _add(
            trace,
            EventType.HANDOFF,
            main,
            {
                "from_agent": main,
                "to_agent": subagent,
                "passed_keys": ["task"] if passed else [],
                "passed_fields": {"task": passed} if passed else {},
                "excerpt": passed,
            },
        )
        _add(trace, EventType.NODE_ENTRY, subagent, {})
        _add(trace, EventType.NODE_EXIT, subagent, {"wrote": {"result": returned} if returned else {}, "excerpt": returned})
    reply = _final_reply(runs)
    _add(trace, EventType.NODE_EXIT, main, {"wrote": {"reply": reply} if reply else {}, "excerpt": reply})
    trace.output_data = {"reply": reply} if reply else {}
    return trace


def _from_graph_nodes(runs: list[dict]) -> Trace:
    visits: list[tuple[str, str]] = []
    current = None
    current_text = ""
    for run in runs:
        name = _graph_node(run)
        if not name:
            continue
        text = _message_text(run.get("outputs"))
        if name != current:
            if current:
                visits.append((current, current_text))
            current = name
            current_text = text or current_text
        elif text:
            current_text = text
    if current:
        visits.append((current, current_text))
    main = visits[0][0] if visits else "agent"
    trace = _new_trace(main, runs)
    previous = None
    for name, text in visits:
        if previous:
            _add(
                trace,
                EventType.HANDOFF,
                previous[0],
                {
                    "from_agent": previous[0],
                    "to_agent": name,
                    "passed_keys": ["output"] if previous[1] else [],
                    "passed_fields": {"output": previous[1]} if previous[1] else {},
                    "excerpt": previous[1],
                },
            )
        _add(trace, EventType.NODE_ENTRY, name, {})
        _add(trace, EventType.NODE_EXIT, name, {"wrote": {"output": text} if text else {}, "excerpt": text})
        previous = (name, text)
    if previous and previous[1]:
        trace.output_data = {"output": previous[1]}
    return trace


def _from_single_agent(runs: list[dict]) -> Trace:
    main = _main_name(runs)
    reply = _final_reply(runs)
    trace = _new_trace(main, runs)
    _add(trace, EventType.NODE_ENTRY, main, {})
    _add(trace, EventType.NODE_EXIT, main, {"wrote": {"reply": reply} if reply else {}, "excerpt": reply})
    trace.output_data = {"reply": reply} if reply else {}
    return trace


def _configuration(runs: list[dict], source_url: str, project_id: str | None, trace: Trace) -> dict[str, Any]:
    subagents = []
    for run in runs:
        name = _subagent_name(run)
        if name and name not in subagents:
            subagents.append(name)
    tools = []
    for run in runs:
        if run.get("run_type") != "tool":
            continue
        name = str(run.get("name") or "").strip()
        if name and name not in tools:
            tools.append(name)
    instructions = ""
    for run in runs:
        if run.get("run_type") != "llm":
            continue
        instructions = _system_text(run.get("inputs"))
        if instructions:
            break
    handoffs = trace.get_handoffs()
    if subagents:
        note = "Subagents are the task calls on this trace. The chat does not show those messages."
    elif handoffs:
        note = "These are the LangGraph nodes on this trace."
    else:
        note = "This trace is one agent talking to a model. A handoff appears when a second agent is called."
    root = _root(runs)
    return {
        "source_url": source_url,
        "project_id": project_id or root.get("session_id"),
        "trace_id": root.get("trace_id") or root.get("id"),
        "main_agent": _main_name(runs),
        "subagents": subagents,
        "tools": tools,
        "instructions": instructions,
        "note": note,
    }


def _new_trace(workflow_id: str, runs: list[dict]) -> Trace:
    root = _root(runs)
    started = _when(root.get("start_time")) or datetime.utcnow()
    user_text = _human_text(root.get("inputs"))
    failed = any(run.get("error") for run in runs)
    trace = Trace(
        id=str(uuid4()),
        workflow_id=workflow_id or "langsmith",
        started_at=started,
        completed_at=_when(root.get("end_time")) or datetime.utcnow(),
        status=TraceStatus.FAILED if failed else TraceStatus.COMPLETED,
        input_data={"message": user_text} if user_text else {},
        metadata={"source": "langsmith"},
    )
    return trace


def _add(trace: Trace, event_type: EventType, agent: str, data: dict) -> None:
    trace.add_event(
        TraceEvent(
            id=str(uuid4()),
            trace_id=trace.id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            agent=agent,
            data=data,
        )
    )


def _project_id_by_name(client: httpx.Client, base: str, headers: dict[str, str], name: str) -> str:
    """Find the tracing project for a project name, an agent name, or an agent ID.

    The name on an agent page is a display name. Traces are stored on the
    tracing project for that agent's ID, so a display name has to be resolved
    before the runs can be read.
    """
    for project_type in ("AGENT", "PROJECT"):
        for params in ({"name": name, "type": project_type}, {"name_contains": name, "type": project_type}):
            chosen = _match_project(_list_sessions(client, base, headers, params), name)
            if chosen is not None:
                return str(chosen["id"])
    session_id = _project_id_from_agent(client, base, headers, name)
    if session_id:
        return session_id
    raise LangSmithImportError(
        f"LangSmith has no tracing project or agent named {name}. "
        "Use the agent name at the top of the page, or the ID beside that name."
    )


def _project_id_from_agent(client: httpx.Client, base: str, headers: dict[str, str], name: str) -> str | None:
    text = name.strip()
    if text and " " not in text and "/" not in text:
        session_id = _session_from_agent(_get_agent(client, base, headers, text)) or _resolve_agent(
            client, base, headers, text
        )
        if session_id:
            return session_id
    agents = _list_agents(client, base, headers, text)
    chosen = _match_agent(agents, text)
    if chosen is None:
        return None
    session_id = _session_from_agent(chosen)
    if session_id:
        return session_id
    agent_id = str(chosen.get("id") or "").strip()
    if not agent_id:
        return None
    return _session_from_agent(_get_agent(client, base, headers, agent_id)) or _resolve_agent(
        client, base, headers, agent_id
    )


def _list_agents(client: httpx.Client, base: str, headers: dict[str, str], name: str) -> list[dict]:
    rows = _agent_page(client, base, headers, {"search": name})
    if rows is None:
        rows = _agent_page(client, base, headers, {"name": name})
    return rows or []


def _agent_page(client: httpx.Client, base: str, headers: dict[str, str], params: dict) -> list[dict] | None:
    """Return matching agents. None means this query shape was rejected."""
    rows: list[dict] = []
    cursor = None
    for _page in range(5):
        query = {"page_size": 100, **params}
        if cursor:
            query["cursor"] = cursor
        response = client.get(f"{base}/api/v1/agents", headers=headers, params=query)
        if response.status_code == 400:
            return None
        if response.status_code == 404:
            return rows
        payload = _decode(response)
        page = payload.get("items") if isinstance(payload, dict) else payload
        if isinstance(page, list):
            rows.extend(row for row in page if isinstance(row, dict))
        cursor = payload.get("next_cursor") if isinstance(payload, dict) else None
        if not cursor:
            break
    return rows


def _get_agent(client: httpx.Client, base: str, headers: dict[str, str], agent_id: str) -> dict | None:
    response = client.get(f"{base}/api/v1/agents/{quote(agent_id, safe='')}", headers=headers)
    if response.status_code in {400, 404, 405}:
        return None
    payload = _decode(response)
    return payload if isinstance(payload, dict) else None


def _resolve_agent(client: httpx.Client, base: str, headers: dict[str, str], agent_id: str) -> str | None:
    for environment in _ENV_ORDER:
        response = client.get(
            f"{base}/api/v1/sessions/resolutions",
            headers=headers,
            params={"kind": "AGENT", "id": agent_id, "environment": environment},
        )
        if response.status_code == 404:
            continue
        if response.status_code in {400, 501}:
            return None
        payload = _decode(response)
        if isinstance(payload, dict) and payload.get("session_id"):
            return str(payload["session_id"])
    return None


def _session_from_agent(agent: dict | None) -> str | None:
    if not isinstance(agent, dict):
        return None
    environments = [item for item in (agent.get("environments") or []) if isinstance(item, dict)]
    ranked = []
    for env_name in _ENV_ORDER:
        ranked.extend(item for item in environments if str(item.get("environment") or "").upper() == env_name)
    known = set(_ENV_ORDER)
    ranked.extend(item for item in environments if str(item.get("environment") or "").upper() not in known)
    for env in ranked:
        if env.get("tracer_session_id"):
            return str(env["tracer_session_id"])
        for binding in env.get("runtime_bindings") or []:
            if isinstance(binding, dict) and binding.get("tracer_session_id"):
                return str(binding["tracer_session_id"])
    return None


def _match_agent(rows: list[dict], name: str) -> dict | None:
    wanted = name.strip().lower()
    folded = wanted.replace("-", "").replace(" ", "")
    exact = [
        row
        for row in rows
        if str(row.get("id") or "").strip().lower() == wanted or str(row.get("name") or "").strip().lower() == wanted
    ]
    if exact:
        return exact[0]
    partial = []
    for row in rows:
        label = str(row.get("name") or "").strip().lower()
        agent_id = str(row.get("id") or "").strip().lower()
        if wanted and (wanted in label or wanted in agent_id):
            partial.append(row)
            continue
        compact = label.replace("-", "").replace(" ", "")
        compact_id = agent_id.replace("-", "").replace(" ", "")
        if folded and (folded in compact or folded in compact_id):
            partial.append(row)
    if len(partial) == 1:
        return partial[0]
    return None


def _list_sessions(client: httpx.Client, base: str, headers: dict[str, str], params: dict) -> list[dict]:
    rows: list[dict] = []
    cursor = None
    for _page in range(5):
        query = {"page_size": 100, **params}
        if cursor:
            query["cursor"] = cursor
        response = client.get(f"{base}/api/v2/sessions", headers=headers, params=query)
        if response.status_code == 404:
            return rows
        payload = _decode(response)
        page = payload.get("items") if isinstance(payload, dict) else payload
        if isinstance(page, list):
            rows.extend(row for row in page if isinstance(row, dict))
        cursor = payload.get("next_cursor") if isinstance(payload, dict) else None
        if not cursor:
            break
    return rows


def _match_project(rows: list[dict], name: str) -> dict | None:
    wanted = name.strip().lower()
    exact = [row for row in rows if str(row.get("name") or "").strip().lower() == wanted and row.get("id")]
    if exact:
        return exact[0]
    partial = [
        row
        for row in rows
        if wanted and wanted in str(row.get("name") or "").strip().lower() and row.get("id")
    ]
    if len(partial) == 1:
        return partial[0]
    return None


def _query_runs(
    client: httpx.Client,
    base: str,
    headers: dict[str, str],
    project_id: str | None,
    trace_id: str | None = None,
    filter_string: str | None = None,
    is_root: bool | None = None,
    limit: int = 100,
) -> list[dict]:
    runs: list[dict] = []
    cursor = None
    for _page in range(5):
        body: dict[str, Any] = {"limit": limit}
        if is_root is not None:
            body["is_root"] = is_root
        if project_id:
            body["session"] = [str(project_id)]
        if trace_id:
            body["trace"] = str(trace_id)
        if filter_string:
            body["filter"] = filter_string
        if cursor:
            body["cursor"] = cursor
        payload = _post_json(client, f"{base}/api/v1/runs/query", headers, body)
        batch = payload.get("runs") if isinstance(payload, dict) else payload
        if not isinstance(batch, list):
            break
        runs.extend(item for item in batch if isinstance(item, dict))
        cursor = (payload.get("cursors") or {}).get("next") if isinstance(payload, dict) else None
        if not cursor or len(batch) < 100:
            break
    return runs


def _get_json(client: httpx.Client, url: str, headers: dict[str, str]) -> dict:
    response = client.get(url, headers=headers)
    return _decode(response)


def _post_json(client: httpx.Client, url: str, headers: dict[str, str], body: dict) -> Any:
    response = client.post(url, headers=headers, json=body)
    return _decode(response)


def _decode(response: httpx.Response) -> Any:
    if response.status_code in {401, 403}:
        raise LangSmithImportError("LangSmith did not accept that API key.")
    if response.status_code == 404:
        raise LangSmithImportError("LangSmith could not find that trace. Copy the address from View trace.")
    if response.status_code >= 400:
        raise LangSmithImportError(
            "LangSmith could not return that trace. Open View trace and copy the address again.",
            status_code=502,
        )
    try:
        return response.json()
    except json.JSONDecodeError as exc:
        raise LangSmithImportError("LangSmith returned something SwarmOS could not read.", status_code=502) from exc


def _path_id(parts: list[str], marker: str) -> str | None:
    import re

    if marker not in parts:
        return None
    index = parts.index(marker)
    if index + 1 >= len(parts):
        return None
    candidate = parts[index + 1]
    if re.fullmatch(_UUID, candidate):
        return candidate
    return None


def _root(runs: list[dict]) -> dict:
    for run in runs:
        if not run.get("parent_run_id"):
            return run
    return runs[0] if runs else {}


def _main_name(runs: list[dict]) -> str:
    root = _root(runs)
    name = str(root.get("name") or "").strip()
    if name and name.lower() not in _GENERIC:
        return name
    for run in runs:
        node = _graph_node(run)
        if node and node.lower() not in _GENERIC:
            return node
    return name or "main"


def _graph_node(run: dict) -> str | None:
    """A LangGraph node that is its own agent.

    Middleware, the model step, and the tools step run inside one agent.
    Counting each of those as an agent turns one deep agent into a long chain.
    """
    metadata = (run.get("extra") or {}).get("metadata") or {}
    if not isinstance(metadata, dict):
        return None
    name = metadata.get("langgraph_node")
    if not isinstance(name, str) or name in {"__start__", "__end__"}:
        return None
    tags = run.get("tags") or []
    if "langsmith:hidden" in tags or _framework_node(name):
        return None
    return name


def _framework_node(name: str) -> bool:
    lowered = name.strip().lower()
    if lowered in _GENERIC:
        return True
    if "middleware" in lowered:
        return True
    hook = lowered.rsplit(".", 1)[-1]
    return hook in {"before_agent", "after_agent", "before_model", "after_model"}


def _subagent_name(run: dict) -> str | None:
    if run.get("run_type") != "tool":
        return None
    payload = _mapping(run.get("inputs"))
    name = payload.get("subagent_type") or payload.get("subagent")
    if isinstance(name, str) and name.strip():
        return name.strip()
    if str(run.get("name") or "") == "task":
        return "subagent"
    return None


def _task_text(inputs: Any) -> str:
    payload = _mapping(inputs)
    for key in ("description", "task", "instructions"):
        text = _clip(_plain(payload.get(key)))
        if text:
            return text
    return ""


def _final_reply(runs: list[dict]) -> str:
    """The main agent's last answer, not a subagent's longer child run."""
    text = _message_text(_root(runs).get("outputs"))
    if text:
        return text
    llms = [run for run in runs if run.get("run_type") == "llm"]
    if not llms:
        return ""
    return _message_text(llms[-1].get("outputs"))


def _best_text(run: dict, runs: list[dict]) -> str:
    texts = [_message_text(run.get("outputs"))]
    children = [item for item in runs if item.get("parent_run_id") == run.get("id")]
    for child in children:
        if child.get("run_type") in {"chain", "llm"}:
            texts.append(_message_text(child.get("outputs")))
    texts = [text for text in texts if text]
    if not texts:
        return ""
    return max(texts, key=len)


def _system_text(inputs: Any) -> str:
    for message in _message_list(inputs):
        if _role(message) in {"system", "systemmessage"}:
            return _clip(_plain(message))
    return ""


def _human_text(inputs: Any) -> str:
    for message in _message_list(inputs):
        if _role(message) in {"human", "user", "humanmessage"}:
            return _clip(_plain(message))
    return _clip(_plain(inputs))


def _message_text(value: Any) -> str:
    messages = _message_list(value)
    spoken = [message for message in messages if _role(message) in {"ai", "assistant", "aimessage"}]
    if spoken:
        return _clip(_plain(spoken[-1]))
    return _clip(_plain(value))


def _message_list(value: Any) -> list:
    if isinstance(value, dict) and isinstance(value.get("messages"), list):
        return value["messages"]
    if isinstance(value, list):
        return value
    return []


def _role(message: Any) -> str:
    if not isinstance(message, dict):
        return ""
    return str(message.get("role") or message.get("type") or "").lower()


def _mapping(value: Any) -> dict:
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}
    return value if isinstance(value, dict) else {}


def _plain(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(part for part in (_plain(item) for item in value) if part)
    if isinstance(value, dict):
        if "content" in value:
            content = _plain(value.get("content"))
            if content:
                return content
        if isinstance(value.get("text"), str) and value["text"].strip():
            return value["text"]
        for key in ("description", "output", "result"):
            if key in value:
                found = _plain(value.get(key))
                if found:
                    return found
        if "messages" in value:
            return _plain(value.get("messages"))
    return ""


def _clip(text: str) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= _CLIP:
        return cleaned
    return cleaned[:_CLIP].rstrip() + "…"


def _when(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
