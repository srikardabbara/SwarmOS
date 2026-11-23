"""Apply a communication fix to the workflow source when the edit is safe."""

import ast
import re
from pathlib import Path
from typing import Any, Optional


def steps_for_context_loss(agent: str, keys: list[str]) -> list[str]:
    """Steps SwarmOS follows when an agent clears state the next agent needs."""
    listed = ", ".join(keys)
    return [
        f"Open the function registered as the {agent} node.",
        f"Stop returning an empty {listed}. Leave the key out of the return value so LangGraph keeps what the previous agent wrote.",
        "Re-run the scenario. The context check should pass, and this finding should be gone.",
    ]


def steps_for_redundant(agent: str) -> list[str]:
    return [
        f"Remove the {agent} node from the graph. It runs and changes nothing.",
        f"Connect the agent before {agent} directly to the agent after it.",
        "Re-run the scenario and confirm the sequence still matches the work you care about.",
    ]


def steps_for_loop(left: str, right: str) -> list[str]:
    return [
        f"Stop {left} and {right} from handing control back to each other unless the return trip adds new state.",
        "Give one of them a finish condition, or have it call the tool it was bouncing instead of the other agent.",
        "Re-run and confirm the handoff happens once.",
    ]


def steps_for_empty_handoff(source: str, target: str) -> list[str]:
    return [
        f"Have {source} return the fields {target} reads, instead of an empty update.",
        f"If {target} does not need anything from {source}, delete the edge and call {target} only when there is something to say.",
        "Re-run and confirm the handoff excerpt is no longer empty.",
    ]


def fix_for_context_loss(agent: str, keys: list[str]) -> dict[str, Any]:
    return {"action": "preserve_keys", "agent": agent, "keys": keys}


def fix_for_redundant(agent: str) -> dict[str, Any]:
    return {"action": "remove_node", "agent": agent}


def apply_fix(fix: dict[str, Any], root: Optional[Path] = None) -> dict[str, str]:
    """Edit the workflow file. Raises ValueError when the edit is not safe."""
    root = root or Path(__file__).resolve().parents[2]
    action = fix.get("action")
    agent = fix.get("agent")
    if not agent or not isinstance(agent, str):
        raise ValueError("This finding has no agent to edit")

    if action == "preserve_keys":
        keys = [key for key in fix.get("keys") or [] if isinstance(key, str)]
        if not keys:
            raise ValueError("This finding has no keys to preserve")
        for path, func_name in _locate_nodes(root, agent):
            updated = _preserve_keys(path.read_text(), func_name, keys)
            if updated is None:
                continue
            path.write_text(updated)
            return {
                "path": str(path.relative_to(root)),
                "summary": f"Stopped {agent} from clearing {', '.join(keys)}.",
            }
        raise ValueError(
            f"Could not find an empty assignment of {', '.join(keys)} in {agent}"
        )

    if action == "remove_node":
        for path, _func_name in _locate_nodes(root, agent):
            updated = _remove_node(path.read_text(), agent)
            if updated is None:
                continue
            path.write_text(updated)
            return {
                "path": str(path.relative_to(root)),
                "summary": f"Removed {agent} and connected its neighbors directly.",
            }
        raise ValueError(
            f"Could not remove {agent}. Its edges are not a simple in-and-out pair."
        )

    raise ValueError(f"SwarmOS cannot apply this fix automatically ({action})")


def _locate_nodes(root: Path, agent: str) -> list[tuple[Path, str]]:
    """Find every file that registers this agent with add_node."""
    needle_double = f'add_node("{agent}"'
    needle_single = f"add_node('{agent}'"
    found: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*.py")):
        if _skipped(path):
            continue
        text = path.read_text()
        if needle_double not in text and needle_single not in text:
            continue
        func_name = _function_name(text, agent)
        if func_name:
            found.append((path, func_name))
    if not found:
        raise ValueError(f"Could not find add_node(\"{agent}\") in this project")
    return found


def _skipped(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & {".venv", "venv", "node_modules", "site-packages", "__pycache__"})


def _function_name(source: str, agent: str) -> Optional[str]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name != "add_node":
            continue
        label = node.args[0]
        if not isinstance(label, ast.Constant) or label.value != agent:
            continue
        target = node.args[1]
        if isinstance(target, ast.Name):
            return target.id
    return None


def _preserve_keys(source: str, func_name: str, keys: list[str]) -> Optional[str]:
    """Rewrite an empty assignment so the node keeps the previous agent's value."""
    span = _function_span(source, func_name)
    if span is None:
        return None
    start, end = span
    state_name = _state_arg(source, func_name) or "state"
    lines = source.splitlines(keepends=True)
    key_pattern = re.compile(
        r"""^(?P<indent>\s*)(?P<quote>["'])(?P<key>%s)(?P=quote)\s*:\s*(?:""|''|None)\s*,?\s*$"""
        % "|".join(re.escape(key) for key in keys)
    )
    changed = False
    new_lines = []
    for index, line in enumerate(lines, start=1):
        match = key_pattern.match(line.rstrip("\n")) if start <= index <= end else None
        if match:
            changed = True
            ending = "\n" if line.endswith("\n") else ""
            new_lines.append(
                f'{match.group("indent")}{match.group("quote")}{match.group("key")}{match.group("quote")}: '
                f'{state_name}.get("{match.group("key")}", ""),{ending}'
            )
            continue
        new_lines.append(line)
    if not changed:
        return None
    updated = "".join(new_lines)
    try:
        ast.parse(updated)
    except SyntaxError:
        return None
    return updated


def _state_arg(source: str, func_name: str) -> Optional[str]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name and node.args.args:
            return node.args.args[0].arg
    return None


def _remove_node(source: str, agent: str) -> Optional[str]:
    """Drop a node and bridge the edge into it with the edge out of it."""
    lines = source.splitlines(keepends=True)
    node_indexes = [
        index
        for index, line in enumerate(lines)
        if re.search(rf"""add_node\(\s*["']{re.escape(agent)}["']""", line)
    ]
    incoming = _edge_indexes(lines, target=agent)
    outgoing = _edge_indexes(lines, source_agent=agent)
    if len(node_indexes) != 1 or len(incoming) != 1 or len(outgoing) != 1:
        return None
    in_index, predecessor = incoming[0]
    out_index, successor = outgoing[0]
    if predecessor == agent or successor == agent or predecessor == successor:
        return None

    bridged = re.sub(
        rf"""(["']){re.escape(agent)}\1""",
        lambda match: f"{match.group(1)}{successor}{match.group(1)}",
        lines[in_index],
        count=1,
    )
    # The substitution above replaces the target of the incoming edge.
    # Confirm it now points at the successor and still starts at the predecessor.
    if successor not in bridged or predecessor not in bridged:
        return None

    drop = {node_indexes[0], out_index}
    new_lines = []
    for index, line in enumerate(lines):
        if index in drop:
            continue
        if index == in_index:
            new_lines.append(bridged)
            continue
        new_lines.append(line)
    updated = "".join(new_lines)
    try:
        ast.parse(updated)
    except SyntaxError:
        return None
    return updated


def _edge_indexes(lines: list[str], source_agent: Optional[str] = None, target: Optional[str] = None):
    found = []
    for index, line in enumerate(lines):
        match = re.search(
            r"""add_edge\(\s*(["'])([^"']+)\1\s*,\s*(["'])([^"']+)\3""",
            line,
        )
        if not match:
            continue
        src, dst = match.group(2), match.group(4)
        if source_agent is not None and src == source_agent:
            found.append((index, dst))
        if target is not None and dst == target:
            found.append((index, src))
    return found


def _function_span(source: str, func_name: str) -> Optional[tuple[int, int]]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            if node.end_lineno is None:
                return None
            return node.lineno, node.end_lineno
    return None
