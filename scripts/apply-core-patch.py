#!/usr/bin/env python3
"""Apply hermes-tool-slimmer core patch to /opt/hermes/.

Supports both:
  - Monolithic layout (run_agent.py) — Hermes v0.13.0, v0.14.0
  - Modular layout (agent/conversation_loop.py) — future Hermes versions

Safety guarantees:
  1. ast.parse() verification after EACH file modification
  2. Automatic rollback on syntax error
  3. Idempotent — safe to run multiple times
  4. Dry-run mode to preview changes

Usage:
  python3 apply-core-patch.py           # Apply patch
  python3 apply-core-patch.py --dry-run # Preview only
  python3 apply-core-patch.py --check   # Check if already applied
"""
from __future__ import annotations

import ast
import os
import shutil
import sys

HERMES_DIR = "/opt/hermes"
BACKUP_DIR = "/tmp/hermes-tool-slimmer-backup"


def _backup(relpath: str) -> None:
    """Create backup of a file before modification."""
    src = os.path.join(HERMES_DIR, relpath)
    if not os.path.exists(src):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dst = os.path.join(BACKUP_DIR, relpath.replace("/", "_"))
    if not os.path.exists(dst):
        shutil.copy2(src, dst)


def _verify_ast(filepath: str, content: str) -> bool:
    """Verify content parses as valid Python."""
    try:
        ast.parse(content)
        return True
    except SyntaxError as e:
        print(f"  ❌ SyntaxError at line {e.lineno}: {e.msg}")
        return False


def _rollback(relpath: str) -> None:
    """Restore file from backup."""
    dst = os.path.join(HERMES_DIR, relpath)
    src = os.path.join(BACKUP_DIR, relpath.replace("/", "_"))
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"  ↩️  Rolled back {relpath}")


def patch_plugins_py(dry_run: bool = False) -> bool:
    """Add 'select_tool_schemas' to VALID_HOOKS in hermes_cli/plugins.py."""
    relpath = "hermes_cli/plugins.py"
    filepath = os.path.join(HERMES_DIR, relpath)

    if not os.path.exists(filepath):
        print(f"  ⚠️  {relpath} not found — skipping")
        return True

    with open(filepath) as f:
        content = f.read()

    if '"select_tool_schemas"' in content:
        print(f"  ✅ {relpath}: already patched")
        return True

    marker = '"pre_llm_call",'
    if marker not in content:
        print(f"  ❌ {relpath}: marker '{marker}' not found")
        return False

    # Find all occurrences of the marker — we want the one in VALID_HOOKS
    lines = content.splitlines(keepends=True)
    applied = False
    for i, line in enumerate(lines):
        if marker in line and i > 100:  # Skip comments
            # Check we're in VALID_HOOKS context (within 20 lines)
            context = "".join(lines[max(0, i - 20):i])
            if "VALID_HOOKS" in context:
                lines.insert(i + 1, '    "select_tool_schemas",\n')
                applied = True
                break

    if not applied:
        print(f"  ❌ {relpath}: could not find VALID_HOOKS insertion point")
        return False

    new_content = "".join(lines)

    if not _verify_ast(filepath, new_content):
        print(f"  ❌ {relpath}: syntax check failed — NOT writing")
        return False

    if dry_run:
        print(f"  🔄 {relpath}: would add 'select_tool_schemas' to VALID_HOOKS")
        return True

    _backup(relpath)
    with open(filepath, "w") as f:
        f.write(new_content)
    print(f"  ✅ {relpath}: added 'select_tool_schemas' to VALID_HOOKS")
    return True


def patch_run_agent_py(dry_run: bool = False) -> bool:
    """Patch run_agent.py to add _select_tools_for_request and wrap _build_api_kwargs."""
    relpath = "run_agent.py"
    filepath = os.path.join(HERMES_DIR, relpath)

    if not os.path.exists(filepath):
        print(f"  ⚠️  {relpath} not found — skipping (may be modular layout)")
        return True

    with open(filepath) as f:
        lines = f.readlines()

    # Check if already patched
    content = "".join(lines)
    if "_select_tools_for_request" in content:
        print(f"  ✅ {relpath}: already patched")
        return True

    # MOD 1: Find the try: block that has _reset_stream_delivery_tracking in conversation loop
    target_try = None
    for i, line in enumerate(lines):
        if "_reset_stream_delivery_tracking" in line and i > 10000 and "def " not in line:
            # Walk back to find the enclosing try:
            for k in range(i - 1, max(i - 10, 0), -1):
                if lines[k].strip() == "try:":
                    target_try = k
                    break
            break

    if target_try is None:
        print(f"  ❌ {relpath}: could not find conversation loop try: block")
        return False

    # Determine the indent level of the try: block
    try_indent = len(lines[target_try]) - len(lines[target_try].lstrip())
    body_indent = try_indent + 4  # content inside try:
    func_indent = try_indent  # closure at same level as try:
    inner_indent = try_indent + 4  # inside closure

    # Build the closure function with correct indentation
    i_s = " " * func_indent
    b_s = " " * body_indent
    fi_s = " " * inner_indent

    func_lines = [
        f"{i_s}def _select_tools_for_request() -> list | None:\n",
        f"{fi_s}if not self.tools:\n",
        f"{fi_s}    return self.tools\n",
        f"{fi_s}tools_for_request = list(self.tools)\n",
        f"{fi_s}try:\n",
        f"{fi_s}    from hermes_cli.plugins import invoke_hook as _invoke_hook\n",
        f'{fi_s}    _schema_results = _invoke_hook(\n',
        f'{fi_s}        "select_tool_schemas",\n',
        f'{fi_s}        session_id=self.session_id or "",\n',
        f"{fi_s}        user_message=original_user_message,\n",
        f"{fi_s}        conversation_history=list(messages),\n",
        f"{fi_s}        schemas=tools_for_request,\n",
        f"{fi_s}        model=self.model,\n",
        f'{fi_s}        platform=getattr(self, "platform", None) or "",\n',
        f'{fi_s}        provider=getattr(self, "provider", None) or getattr(self, "model_provider", None),\n',
        f"{fi_s}    )\n",
        f"{fi_s}    _schema_lists = [result for result in _schema_results if isinstance(result, list)]\n",
        f"{fi_s}    if _schema_lists:\n",
        f"{fi_s}        if len(_schema_lists) > 1:\n",
        f"{fi_s}            logger.warning(\n",
        f'{fi_s}                "Multiple select_tool_schemas hooks returned schemas; using the first result"\n',
        f"{fi_s}            )\n",
        f"{fi_s}        return _schema_lists[0]\n",
        f"{fi_s}except Exception as exc:\n",
        f'{fi_s}    logger.warning("select_tool_schemas hook failed; using original tools: %s", exc)\n',
        f"{fi_s}return tools_for_request\n",
        "\n",
    ]

    # Insert function before the try: block
    for idx, fl in enumerate(func_lines):
        lines.insert(target_try + idx, fl)

    # MOD 2: Find _reset_stream_delivery_tracking again (line shifted) and wrap _build_api_kwargs
    mod2_done = False
    for i, line in enumerate(lines):
        if "_reset_stream_delivery_tracking" in line and i > 10000 and "def " not in line:
            if i + 1 < len(lines) and "_build_api_kwargs(api_messages)" in lines[i + 1]:
                # Get indent of the api_kwargs line
                api_indent = len(lines[i + 1]) - len(lines[i + 1].lstrip())
                a_s = " " * api_indent

                new_lines = [
                    f"{a_s}tools_for_request = _select_tools_for_request()\n",
                    f"{a_s}original_tools = self.tools\n",
                    f"{a_s}self.tools = tools_for_request\n",
                    f"{a_s}try:\n",
                    f"{a_s}    api_kwargs = self._build_api_kwargs(api_messages)\n",
                    f"{a_s}finally:\n",
                    f"{a_s}    self.tools = original_tools\n",
                ]
                lines[i + 1 : i + 2] = new_lines
                mod2_done = True
                break

    if not mod2_done:
        print(f"  ❌ {relpath}: could not find _build_api_kwargs call to wrap")
        return False

    # MOD 3: Fix tool_count in pre_api_request hook
    mod3_done = False
    for i, line in enumerate(lines):
        if "tool_count=len(self.tools" in line and i > 10000:
            lines[i] = line.replace(
                "tool_count=len(self.tools or [])",
                "tool_count=len(tools_for_request if tools_for_request is not None else (self.tools or []))",
            )
            mod3_done = True
            break

    if not mod3_done:
        print(f"  ⚠️  {relpath}: tool_count line not found (may already be patched)")

    # Verify
    new_content = "".join(lines)
    if not _verify_ast(filepath, new_content):
        print(f"  ❌ {relpath}: syntax check failed — rolling back")
        _rollback(relpath)
        return False

    if dry_run:
        print(f"  🔄 {relpath}: would insert _select_tools_for_request closure + wrap _build_api_kwargs")
        return True

    _backup(relpath)
    with open(filepath, "w") as f:
        f.writelines(lines)
    print(f"  ✅ {relpath}: patch applied (3 modifications)")
    return True




def patch_conversation_loop_py(dry_run: bool = False) -> bool:
    """Patch agent/conversation_loop.py (Hermes v0.16.0+)."""
    relpath = "agent/conversation_loop.py"
    filepath = os.path.join(HERMES_DIR, relpath)
    
    if not os.path.exists(filepath):
        print(f"  ⚠️  {relpath} not found — skipping")
        return True
    
    with open(filepath) as f:
        lines = f.readlines()
    
    content = "".join(lines)
    if "_select_tools_for_request" in content:
        print(f"  ✅ {relpath}: already patched")
        return True
    
    # Find try: block with agent._reset_stream_delivery_tracking
    target_try = None
    for i, line in enumerate(lines):
        if "agent._reset_stream_delivery_tracking()" in line and "def " not in line and i > 1000:
            for k in range(i - 1, max(i - 5, 0), -1):
                if lines[k].strip() == "try:":
                    target_try = k
                    break
            if target_try:
                break
    
    if target_try is None:
        print(f"  ❌ {relpath}: could not find conversation loop try: block")
        return False
    
    # Insert closure
    try_indent = len(lines[target_try]) - len(lines[target_try].lstrip())
    i_s = " " * try_indent
    fi_s = " " * (try_indent + 4)
    
    func_lines = [
        f"{i_s}def _select_tools_for_request() -> list | None:\n",
        f"{fi_s}if not agent.tools:\n",
        f"{fi_s}    return agent.tools\n",
        f"{fi_s}tools_for_request = list(agent.tools)\n",
        f"{fi_s}try:\n",
        f"{fi_s}    from hermes_cli.plugins import invoke_hook as _invoke_hook\n",
        f'{fi_s}    _schema_results = _invoke_hook(\n',
        f'{fi_s}        "select_tool_schemas",\n',
        f'{fi_s}        session_id=agent.session_id or "",\n',
        f"{fi_s}        user_message=original_user_message,\n",
        f"{fi_s}        conversation_history=list(messages),\n",
        f"{fi_s}        schemas=tools_for_request,\n",
        f"{fi_s}        model=agent.model,\n",
        f'{fi_s}        platform=getattr(agent, "platform", None) or "",\n',
        f'{fi_s}        provider=getattr(agent, "provider", None) or getattr(agent, "model_provider", None),\n',
        f"{fi_s}    )\n",
        f"{fi_s}    _schema_lists = [result for result in _schema_results if isinstance(result, list)]\n",
        f"{fi_s}    if _schema_lists:\n",
        f"{fi_s}        if len(_schema_lists) > 1:\n",
        f"{fi_s}            logger.warning(\n",
        f'{fi_s}                "Multiple select_tool_schemas hooks returned schemas; using the first result"\n',
        f"{fi_s}            )\n",
        f"{fi_s}        return _schema_lists[0]\n",
        f"{fi_s}except Exception as exc:\n",
        f'{fi_s}    logger.warning("select_tool_schemas hook failed; using original tools: %s", exc)\n',
        f"{fi_s}return tools_for_request\n",
        "\n",
    ]
    
    for idx, fl in enumerate(func_lines):
        lines.insert(target_try + idx, fl)
    
    # Wrap _build_api_kwargs
    mod2_done = False
    for i, line in enumerate(lines):
        if "api_kwargs = agent._build_api_kwargs(api_messages)" in line and i > 1000:
            api_indent = len(line) - len(line.lstrip())
            a_s = " " * api_indent
            new_lines = [
                f"{a_s}tools_for_request = _select_tools_for_request()\n",
                f"{a_s}original_tools = agent.tools\n",
                f"{a_s}agent.tools = tools_for_request\n",
                f"{a_s}try:\n",
                f"{a_s}    api_kwargs = agent._build_api_kwargs(api_messages)\n",
                f"{a_s}finally:\n",
                f"{a_s}    agent.tools = original_tools\n",
            ]
            lines[i:i+1] = new_lines
            mod2_done = True
            break
    
    if not mod2_done:
        print(f"  ❌ {relpath}: could not find _build_api_kwargs call")
        return False
    
    # Update tool_count
    for i, line in enumerate(lines):
        if "tool_count=len(agent.tools or [])" in line and i > 1000:
            lines[i] = line.replace(
                "tool_count=len(agent.tools or [])",
                "tool_count=len(tools_for_request if tools_for_request is not None else (agent.tools or []))"
            )
            break
    
    new_content = "".join(lines)
    if not _verify_ast(filepath, new_content):
        print(f"  ❌ {relpath}: syntax check failed — rolling back")
        _rollback(relpath)
        return False
    
    if dry_run:
        print(f"  🔄 {relpath}: would insert _select_tools_for_request + wrap _build_api_kwargs")
        return True
    
    _backup(relpath)
    with open(filepath, "w") as f:
        f.write(new_content)
    print(f"  ✅ {relpath}: patch applied")
    return True


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    check_only = "--check" in sys.argv

    print(f"{'=== DRY RUN ===' if dry_run else '=== APPLYING CORE PATCH ==='}")
    print(f"Hermes dir: {HERMES_DIR}\n")

    if check_only:
        # Just check if already applied
        plugins_ok = '"select_tool_schemas"' in open(os.path.join(HERMES_DIR, "hermes_cli/plugins.py")).read()
        run_agent_path = os.path.join(HERMES_DIR, "run_agent.py")
        run_agent_ok = os.path.exists(run_agent_path) and "_select_tools_for_request" in open(run_agent_path).read()
        print(f"plugins.py: {'✅' if plugins_ok else '❌'}")
        print(f"run_agent.py: {'✅' if run_agent_ok else '❌'}")
        return 0 if (plugins_ok and run_agent_ok) else 1

    all_ok = True
    if not patch_plugins_py(dry_run):
        all_ok = False
    if not patch_run_agent_py(dry_run):
        all_ok = False
    if not patch_conversation_loop_py(dry_run):
        all_ok = False

    if all_ok:
        print(f"\n{'✅ All patches applied (or already present)' if not dry_run else '✅ All patches would apply cleanly'}")
    else:
        print(f"\n❌ Some patches failed — check errors above")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
