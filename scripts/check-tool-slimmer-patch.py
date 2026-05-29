#!/usr/bin/env python3
"""Check if hermes-tool-slimmer core patch is applied to /opt/hermes/.

Returns exit code:
  0 = patch is applied
  1 = patch is NOT applied (writes status to stdout)
  2 = error during check

Designed to be called from gateway-wrapper.sh at startup.
If patch is missing, outputs a notification message for Discord.

Supports both:
  - v0.13.0 patch: _active_tools_for_request method + tools_for_api swap
  - v0.14.0 patch: _select_tools_for_request closure + tools swap
"""
from __future__ import annotations

import sys

HERMES_DIR = "/opt/hermes"

# Markers for the v0.14.0+ patch (current)
PATCH_MARKERS_V14 = {
    "run_agent.py": [
        "_select_tools_for_request",
        "select_tool_schemas",
    ],
    "hermes_cli/plugins.py": [
        "select_tool_schemas",
    ],
}

# Markers for the v0.13.0 patch (legacy)
PATCH_MARKERS_V13 = {
    "run_agent.py": [
        "_active_tools_for_request",
        "tools_for_api = self._active_tools_for_request()",
    ],
    "hermes_cli/plugins.py": [
        "select_tool_schemas",
    ],
}


def _check_markers(markers: dict) -> tuple[bool, list[str]]:
    import os
    missing = []
    for relpath, file_markers in markers.items():
        filepath = os.path.join(HERMES_DIR, relpath)
        if not os.path.exists(filepath):
            missing.append(f"{relpath}: FILE NOT FOUND")
            continue
        try:
            content = open(filepath).read()
        except Exception as exc:
            missing.append(f"{relpath}: READ ERROR: {exc}")
            continue
        for marker in file_markers:
            if marker not in content:
                missing.append(f"{relpath}: missing '{marker}'")
    return len(missing) == 0, missing


def check_patch() -> tuple[bool, list[str]]:
    """Check if core patch markers exist. Supports v0.13.0 and v0.14.0 layouts."""

    # Try v0.14.0+ markers first (current)
    applied, missing = _check_markers(PATCH_MARKERS_V14)
    if applied:
        return True, []

    # Try v0.13.0 markers (legacy)
    applied_v13, missing_v13 = _check_markers(PATCH_MARKERS_V13)
    if applied_v13:
        return True, []

    # Return v0.14.0 missing markers (current expected layout)
    return False, missing


def main() -> int:
    import os

    applied, missing = check_patch()

    if applied:
        print("PATCH_CHECK: hermes-tool-slimmer patch is applied ✅")
        # Clean up flag if it exists
        flag = "/tmp/.slimmer-patch-missing"
        if os.path.exists(flag):
            os.remove(flag)
        return 0

    print("PATCH_CHECK: hermes-tool-slimmer patch is NOT applied ⚠️")
    print("MISSING_MARKERS:")
    for m in missing:
        print(f"  - {m}")
    print()
    print("TO FIX: Apply the core patch manually (see docs/hermes-core-selector-hook.patch)")
    print("Or run: /opt/hermes/.venv/bin/python3 -m hermes_tool_slimmer.cli doctor")

    # Write flag file for Hermes cron to pick up and send Discord notification
    flag = "/tmp/.slimmer-patch-missing"
    with open(flag, "w") as f:
        f.write("tool-slimmer core patch non applicata.\n")
        f.write("Per fixare: riapplica la patch come da documentazione.\n")
    print(f"Flag written to {flag} — Hermes cron will notify on Discord")

    return 1


if __name__ == "__main__":
    sys.exit(main())
