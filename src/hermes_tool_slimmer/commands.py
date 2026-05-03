from __future__ import annotations

import json
from typing import Any

from .tools import tool_slimmer_select, tool_slimmer_status


def handle_slash_command(command: str | dict[str, Any], **kwargs: Any) -> str:
    try:
        text = command.get("text", "") if isinstance(command, dict) else str(command or "")
        parts = text.strip().split(maxsplit=1)
        action = parts[0] if parts else "status"
        rest = parts[1] if len(parts) > 1 else ""
        if action == "status":
            return tool_slimmer_status({}, **kwargs)
        if action == "select":
            return tool_slimmer_select({"query": rest, "schemas": kwargs.get("schemas", [])}, **kwargs)
        if action == "dry-run":
            return json.dumps({"ok": True, "message": "Set tool_slimmer.dry_run in ~/.hermes/config.yaml", "requested": rest})
        return json.dumps({"ok": False, "error": f"Unknown /tool-slimmer action: {action}"})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)}, sort_keys=True)
