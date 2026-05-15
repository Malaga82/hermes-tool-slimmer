#!/usr/bin/env python3
"""Check if hermes-tool-slimmer core patch is applied to /opt/hermes/.

Returns exit code:
  0 = patch is applied
  1 = patch is NOT applied (writes status to stdout)
  2 = error during check

Designed to be called from gateway-wrapper.sh at startup.
If patch is missing, outputs a notification message for Discord.
"""
from __future__ import annotations

import sys

HERMES_DIR = "/opt/hermes"
PATCH_MARKERS = {
    "run_agent.py": [
        "_active_tools_for_request",
        "_select_tools_for_request",
        "tools_for_api = self._active_tools_for_request()",
    ],
    "hermes_cli/plugins.py": [
        "select_tool_schemas",
    ],
}


def check_patch() -> tuple[bool, list[str]]:
    """Check if all patch markers exist in the target files.
    
    Returns (is_applied, list_of_missing_markers).
    """
    import os
    
    missing = []
    for relpath, markers in PATCH_MARKERS.items():
        filepath = os.path.join(HERMES_DIR, relpath)
        if not os.path.exists(filepath):
            missing.append(f"{relpath}: FILE NOT FOUND")
            continue
        try:
            content = open(filepath).read()
        except Exception as exc:
            missing.append(f"{relpath}: READ ERROR: {exc}")
            continue
        for marker in markers:
            if marker not in content:
                missing.append(f"{relpath}: missing '{marker}'")
    
    return len(missing) == 0, missing


def main() -> int:
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
    print("TO FIX: cd /opt/hermes && patch -p1 -f -i /opt/data/hermes-tool-slimmer/docs/hermes-core-selector-hook.patch")
    
    # Write flag file for Hermes cron to pick up and send Discord notification
    flag = "/tmp/.slimmer-patch-missing"
    with open(flag, "w") as f:
        f.write("tool-slimmer core patch non applicata.\n")
        f.write("Per fixare:\n")
        f.write("cd /opt/hermes && patch -p1 -f -i /opt/data/hermes-tool-slimmer/docs/hermes-core-selector-hook.patch\n")
        f.write("Poi riavvia il gateway.\n")
    print(f"Flag written to {flag} — Hermes cron will notify on Discord")
    
    return 1


if __name__ == "__main__":
    import os
    sys.exit(main())
