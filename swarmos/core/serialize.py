"""Convert workflow values into JSON-safe data for storage and the API."""

from datetime import datetime
from enum import Enum
from typing import Any


def to_jsonable(value: Any) -> Any:
    """Return a JSON-serializable copy of a trace value.

    LangGraph state contains message objects. Those cannot be posted to the
    API as-is, so messages become small dicts and everything else is reduced
    to plain JSON types.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]

    message_type = getattr(value, "type", None)
    content = getattr(value, "content", None)
    if message_type in {"human", "ai", "system", "tool"} and content is not None:
        data: dict[str, Any] = {"type": message_type, "content": to_jsonable(content)}
        tool_calls = getattr(value, "tool_calls", None)
        if tool_calls:
            data["tool_calls"] = to_jsonable(tool_calls)
        return data

    if hasattr(value, "model_dump"):
        try:
            return to_jsonable(value.model_dump(mode="json"))
        except Exception:
            pass

    return str(value)
