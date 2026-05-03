from __future__ import annotations

import json
from typing import Iterable

from .corpus import tool_name
from .types import Schema


def schema_bytes(schemas: Iterable[Schema]) -> int:
    return len(json.dumps(list(schemas), sort_keys=True, separators=(",", ":")).encode("utf-8"))


def approx_tokens(byte_count: int) -> int:
    return round(byte_count / 4)


def reduction_metrics(mode: str, original: list[Schema], selected: list[Schema], always_included: list[str] | None = None) -> dict[str, object]:
    before = schema_bytes(original)
    after = schema_bytes(selected)
    reduction = 0.0 if before == 0 else round(((before - after) / before) * 100, 1)
    return {
        "mode": mode,
        "total_tools": len(original),
        "selected_tools": len(selected),
        "schema_bytes_before": before,
        "schema_bytes_after": after,
        "approx_tokens_before": approx_tokens(before),
        "approx_tokens_after": approx_tokens(after),
        "estimated_reduction_percent": reduction,
        "always_included": always_included or [],
        "selected": [tool_name(schema) for schema in selected],
        "token_estimate_note": "Approximate tokens use serialized JSON bytes / 4.",
    }
