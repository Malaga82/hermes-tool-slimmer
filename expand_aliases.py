#!/usr/bin/env python3
"""Expand tool-slimmer Italian alias dictionary.

Reads unmapped Italian tokens from the aliases module, sends them to an LLM
with the current dictionary, and updates the YAML file with new entries.

Usage:
    python expand_aliases.py [--dry-run] [--path /path/to/aliases.yaml]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

# Add the src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from hermes_tool_slimmer.aliases import get_aliases, get_unmapped_tokens, reload_aliases

ALIAS_PATH = os.environ.get(
    "TOOL_SLIMMER_ALIASES",
    os.path.join(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")),
                 "tool-slimmer-it-aliases.yaml")
)

# Use the Go proxy for LLM calls
API_URL = os.environ.get("EXPAND_ALIASES_API_URL", "http://127.0.0.1:8421/v1/chat/completions")
API_KEY = os.environ.get("COMMANDCODE_API_KEY", "dummy")
MODEL = os.environ.get("EXPAND_ALIASES_MODEL", "deepseek/deepseek-v4-flash")

SYSTEM_PROMPT = """You are a bilingual Italian→English translation assistant.
Your job is to expand an Italian→English alias dictionary used for keyword matching.

Given:
1. The current dictionary (YAML format)
2. A list of unmapped Italian words found in user queries

Return ONLY a YAML block with NEW entries to add. Rules:
- Each Italian word maps to space-separated English equivalents
- Include synonyms, related terms, and technical equivalents
- Focus on words relevant to software tools, CLI, devops, web, AI
- Do NOT repeat entries that already exist in the current dictionary
- If no new entries are needed, return an empty YAML block: {}
- Keep translations concise (2-5 words max per entry)
"""

MAX_NEW_ENTRIES = 50


def call_llm(current_yaml: str, unmapped: list[str]) -> dict[str, str]:
    """Call the LLM to generate new alias entries."""
    user_msg = f"""Current dictionary:\n```yaml\n{current_yaml}\n```\n\nUnmapped Italian tokens: {json.dumps(unmapped)}\n\nReturn ONLY new YAML entries to add:"""

    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        "temperature": 0.3,
        "max_tokens": 1000,
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            content = result["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        print(f"ERROR: LLM call failed: {exc}", file=sys.stderr)
        return {}

    # Extract YAML from response (might be wrapped in ```yaml ... ```)
    import re
    yaml_match = re.search(r"```ya?ml\s*\n(.*?)```", content, re.DOTALL)
    if yaml_match:
        content = yaml_match.group(1).strip()

    if content.startswith("{") and content.endswith("}"):
        # Empty block
        return {}

    # Parse as YAML
    try:
        import yaml
        new_entries = yaml.safe_load(content)
        if isinstance(new_entries, dict):
            return {str(k): str(v) for k, v in new_entries.items() if v}
        return {}
    except Exception as exc:
        print(f"WARNING: Failed to parse LLM response as YAML: {exc}", file=sys.stderr)
        print(f"Raw response:\n{content}", file=sys.stderr)
        return {}


def main():
    parser = argparse.ArgumentParser(description="Expand Italian alias dictionary")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added without writing")
    parser.add_argument("--path", default=ALIAS_PATH, help="Path to alias YAML file")
    args = parser.parse_args()

    # Load current aliases
    aliases = get_aliases()
    unmapped = get_unmapped_tokens()

    # Filter out already-mapped tokens
    truly_unmapped = [t for t in unmapped if t not in aliases]

    if not truly_unmapped:
        print("No unmapped Italian tokens found. Dictionary is up to date.")
        return

    print(f"Found {len(truly_unmapped)} unmapped tokens: {truly_unmapped[:20]}{'...' if len(truly_unmapped) > 20 else ''}")

    # Read current YAML for context
    alias_path = Path(args.path)
    current_yaml = alias_path.read_text(encoding="utf-8") if alias_path.exists() else "{}"

    # Call LLM for new entries
    print(f"Asking {MODEL} for translations...")
    new_entries = call_llm(current_yaml, truly_unmapped[:MAX_NEW_ENTRIES])

    if not new_entries:
        print("No new entries generated.")
        return

    # Filter out duplicates
    current_keys = set(aliases.keys())
    fresh = {k: v for k, v in new_entries.items() if k not in current_keys}

    if not fresh:
        print("All generated entries already exist in dictionary.")
        return

    print(f"\nNew entries ({len(fresh)}):")
    for k, v in sorted(fresh.items()):
        print(f"  {k}: {v}")

    if args.dry_run:
        print("\n(dry-run: not writing to file)")
        return

    # Append to YAML file
    import yaml
    existing = {}
    if alias_path.exists():
        existing = yaml.safe_load(alias_path.read_text(encoding="utf-8")) or {}

    existing.update(fresh)
    alias_path.write_text(yaml.dump(existing, allow_unicode=True, default_flow_style=False, sort_keys=True), encoding="utf-8")
    print(f"\nWritten {len(fresh)} new entries to {alias_path}")

    # Reload aliases in the running module
    reload_aliases(alias_path)
    print("Aliases reloaded.")


if __name__ == "__main__":
    from pathlib import Path
    main()
