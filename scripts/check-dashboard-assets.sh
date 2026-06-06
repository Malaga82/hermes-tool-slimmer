#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MISSING=0

check_file() {
  local path="$1"
  if [[ -f "$ROOT_DIR/$path" ]]; then
    echo "OK  $path ($(wc -c < "$ROOT_DIR/$path") bytes)"
  else
    echo "FAIL missing $path"
    MISSING=1
  fi
}

check_file "dashboard/manifest.json"
check_file "dashboard/plugin_api.py"
check_file "dashboard/dist/index.js"
check_file "dashboard/dist/style.css"
check_file "dashboard-plugin/tool-slimmer/dashboard/manifest.json"
check_file "dashboard-plugin/tool-slimmer/dashboard/plugin_api.py"
check_file "dashboard-plugin/tool-slimmer/dashboard/dist/index.js"
check_file "dashboard-plugin/tool-slimmer/dashboard/dist/style.css"

if [[ "$MISSING" -eq 0 ]]; then
  echo "PASS dashboard assets are present"
else
  echo "FAIL dashboard asset check failed"
  exit 1
fi
