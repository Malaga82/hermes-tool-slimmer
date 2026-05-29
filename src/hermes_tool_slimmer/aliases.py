"""Italian alias expansion for BM25 tokenizer.

Loads it→en mappings from a YAML file and expands query tokens
so Italian queries match English tool descriptions.

Logs unmapped Italian tokens for future dictionary expansion.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from importlib import resources
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger("hermes_tool_slimmer.aliases")

_ALIASES: dict[str, list[str]] | None = None
_ALIASES_LOCK = threading.Lock()
_UNMAPPED_LOG_MAX = 500
_unmapped_tokens: list[str] = []


def _default_alias_path() -> Path:
    """Resolve alias dictionary path.

    Priority:
      1. TOOL_SLIMMER_ALIASES env var
      2. <HERMES_HOME>/tool-slimmer-it-aliases.yaml
      3. <config_dir>/tool-slimmer-it-aliases.yaml
    """
    env = os.environ.get("TOOL_SLIMMER_ALIASES")
    if env:
        return Path(env).expanduser()

    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()
    candidate = hermes_home / "tool-slimmer-it-aliases.yaml"
    if candidate.exists():
        return candidate

    return candidate  # return even if doesn't exist yet


def _load_aliases(path: Path | None = None) -> dict[str, list[str]]:
    """Load alias dictionary from YAML. Returns empty dict on failure."""
    target = path or _default_alias_path()
    if not target.exists() or yaml is None:
        return {}

    try:
        data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        aliases: dict[str, list[str]] = {}
        for it_word, en_text in data.items():
            if isinstance(en_text, str) and en_text.strip():
                aliases[str(it_word).lower()] = en_text.lower().split()
        logger.debug("Loaded %d alias entries from %s", len(aliases), target)
        return aliases
    except Exception as exc:
        logger.warning("Failed to load alias dictionary: %s", exc)
        return {}


def get_aliases() -> dict[str, list[str]]:
    """Get cached aliases, loading on first call (thread-safe)."""
    global _ALIASES
    if _ALIASES is not None:
        return _ALIASES
    with _ALIASES_LOCK:
        if _ALIASES is not None:
            return _ALIASES
        _ALIASES = _load_aliases()
        return _ALIASES


def reload_aliases(path: Path | None = None) -> dict[str, list[str]]:
    """Force reload aliases from disk."""
    global _ALIASES
    with _ALIASES_LOCK:
        _ALIASES = _load_aliases(path)
        return _ALIASES


def expand_tokens(tokens: list[str]) -> list[str]:
    """Expand token list with English aliases for Italian tokens.

    Also logs unmapped tokens that look like Italian words for
    future dictionary expansion.
    """
    aliases = get_aliases()
    expanded = list(tokens)
    italian_pattern = re.compile(r"^[a-z]{3,}$")

    for token in tokens:
        low = token.lower()
        if low in aliases:
            expanded.extend(aliases[low])
        elif italian_pattern.match(low) and low not in aliases:
            # Potential unmapped Italian word — log it
            if len(_unmapped_tokens) < _UNMAPPED_LOG_MAX:
                _unmapped_tokens.append(low)

    return expanded


def get_unmapped_tokens() -> list[str]:
    """Return list of unmapped Italian tokens seen so far."""
    return list(set(_unmapped_tokens))


def clear_unmapped_tokens() -> None:
    """Clear the unmapped token log."""
    _unmapped_tokens.clear()
