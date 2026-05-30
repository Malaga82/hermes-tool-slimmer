from __future__ import annotations

import importlib.util
from typing import Any, Iterable

from .corpus import tool_name
from .types import Schema

NATIVE_TOOL_SEARCH_BRIDGE_NAMES = frozenset({"tool_search", "tool_describe", "tool_call"})


def native_tool_search_available() -> bool:
    try:
        return importlib.util.find_spec("tools.tool_search") is not None
    except (ImportError, ModuleNotFoundError, AttributeError, ValueError):
        return False


def native_tool_search_bridge_names(schemas: Iterable[Schema]) -> list[str]:
    names = {
        tool_name(schema)
        for schema in schemas
        if isinstance(schema, dict) and tool_name(schema) in NATIVE_TOOL_SEARCH_BRIDGE_NAMES
    }
    return sorted(names)


def native_tool_search_active(schemas: Iterable[Schema]) -> bool:
    # Hermes native progressive loading installs all three bridge tools when it
    # has already deferred MCP/plugin schemas. Two is enough to avoid a brittle
    # failure if a local checkout renames or temporarily drops one bridge.
    return len(native_tool_search_bridge_names(schemas)) >= 2


def native_tool_search_status(schemas: Iterable[Schema] | None = None) -> dict[str, Any]:
    bridge_names = native_tool_search_bridge_names(schemas or [])
    return {
        "available": native_tool_search_available(),
        "active": len(bridge_names) >= 2,
        "bridge_tools": bridge_names,
        "policy": "skip_tool_slimmer_when_active",
    }
