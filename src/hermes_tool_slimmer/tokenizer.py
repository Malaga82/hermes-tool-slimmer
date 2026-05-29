from __future__ import annotations

import os
import re

from .aliases import expand_tokens, reload_aliases

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_SPLIT_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

_ALIASES_ENABLED = os.environ.get("TOOL_SLIMMER_ALIASES_DISABLED", "").strip().lower() not in ("1", "true", "yes")


def normalize_text(text: object) -> str:
    return str(text or "").lower()


def tokenize(text: object, use_aliases: bool = True) -> list[str]:
    """Deterministic tokenizer for tool names, descriptions, and schema fields.

    When use_aliases=True and TOOL_SLIMMER_ALIASES_DISABLED is not set,
    Italian tokens are expanded with English equivalents from the alias dictionary.
    """
    raw = str(text or "")
    expanded = _SPLIT_BOUNDARY_RE.sub(" ", raw).replace("_", " ").replace("-", " ")
    tokens = [match.group(0).lower() for match in _TOKEN_RE.finditer(expanded)]

    if use_aliases and _ALIASES_ENABLED and tokens:
        tokens = expand_tokens(tokens)

    return tokens


def tokens_with_exact_identifier(identifier: object) -> list[str]:
    raw = str(identifier or "").strip().lower()
    parts = tokenize(raw)
    if raw and raw not in parts:
        return [raw, *parts]
    return parts
