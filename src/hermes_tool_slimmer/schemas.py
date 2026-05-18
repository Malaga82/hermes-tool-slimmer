STATUS_SCHEMA = {
    "name": "tool_slimmer_status",
    "description": "Return Hermes Tool Slimmer status and configuration.",
    "parameters": {"type": "object", "properties": {}},
}

SELECT_SCHEMA = {
    "name": "tool_slimmer_select",
    "description": "Select likely relevant tools for a query from provided tool schemas.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "schemas": {"type": "array", "items": {"type": "object"}},
            "mode": {"type": "string", "enum": ["eager", "keyword", "hybrid", "anthropic_tool_search"]},
        },
        "required": ["query"],
    },
}

REQUEST_FULL_TOOLS_SCHEMA = {
    "name": "tool_slimmer_request_full_tools",
    "description": (
        "Request the full Hermes tool schema set for the next model call when "
        "a required tool is missing from the trimmed tool list."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "Short explanation of the missing tool or skill requirement.",
            }
        },
    },
}
