#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if command -v uv >/dev/null 2>&1; then
  uv run --with build python -m build --outdir "$TMP_DIR" "$ROOT_DIR" >/dev/null
elif python -m build --version >/dev/null 2>&1; then
  python -m build --outdir "$TMP_DIR" "$ROOT_DIR" >/dev/null
else
  echo "FAIL python build module is unavailable; install build or uv"
  exit 1
fi

WHEEL="$(find "$TMP_DIR" -maxdepth 1 -name '*.whl' | head -n 1)"
SDIST="$(find "$TMP_DIR" -maxdepth 1 -name '*.tar.gz' | head -n 1)"
[[ -n "$WHEEL" ]] || { echo "FAIL wheel was not built"; exit 1; }
[[ -n "$SDIST" ]] || { echo "FAIL sdist was not built"; exit 1; }
SDIST_LIST="$TMP_DIR/sdist-members.txt"
tar tzf "$SDIST" > "$SDIST_LIST"

MISSING=0

check_wheel_member() {
  local member="$1"
  if python - "$WHEEL" "$member" <<'PY'
import sys
from zipfile import ZipFile

archive, member = sys.argv[1], sys.argv[2]
with ZipFile(archive) as zf:
    names = set(zf.namelist())
raise SystemExit(0 if member in names else 1)
PY
  then
    echo "OK  wheel contains $member"
  else
    echo "FAIL wheel missing $member"
    MISSING=1
  fi
}

check_sdist_member() {
  local suffix="$1"
  if grep -Eq "^[^/]+/${suffix}$" "$SDIST_LIST"; then
    echo "OK  sdist contains $suffix"
  else
    echo "FAIL sdist missing $suffix"
    MISSING=1
  fi
}

for member in \
  "dashboard/manifest.json" \
  "dashboard/plugin_api.py" \
  "dashboard/dist/index.js" \
  "dashboard/dist/style.css" \
  "dashboard-plugin/tool-slimmer/plugin.yaml" \
  "dashboard-plugin/tool-slimmer/dashboard/manifest.json" \
  "dashboard-plugin/tool-slimmer/dashboard/plugin_api.py" \
  "dashboard-plugin/tool-slimmer/dashboard/dist/index.js" \
  "dashboard-plugin/tool-slimmer/dashboard/dist/style.css"
do
  check_wheel_member "$member"
  check_sdist_member "$member"
done

if [[ "$MISSING" -eq 0 ]]; then
  echo "PASS wheel and sdist include required dashboard assets"
else
  echo "FAIL package asset check failed"
  exit 1
fi
