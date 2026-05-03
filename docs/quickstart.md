# Quickstart

## 1. Install

```bash
pip install "git+https://github.com/alias8818/hermes-tool-slimmer.git@v0.1.0"
hermes plugins enable tool-slimmer
```

The package metadata is PyPI-ready, but this source release is distributed through GitHub until a package-index publish is completed.

## 2. Add configuration

Add a `tool_slimmer` section to `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - tool-slimmer

tool_slimmer:
  enabled: true
  mode: keyword
  top_k: 8
  always_include:
    - terminal
    - read_file
    - write_file
    - patch
    - search_files
  fail_open: true
  dry_run: true
```

Start with `dry_run: true`. This lets you inspect selections without changing provider requests.

## 3. Check installation

```bash
hermes tool-slimmer doctor
hermes tool-slimmer status
```

`doctor` reports whether Hermes is importable, the plugin is enabled, the index path is writable, and whether the core selector hook is available.

## 4. Preview selection

```bash
hermes tool-slimmer select "search this repo for MCP registration code" --schemas tools.yaml
```

A schema file can be a YAML list or an object containing `tools:` / `schemas:`.

## 5. Enable active schema slimming

Set `dry_run: false` only after `doctor` reports a Hermes core selector hook or after applying the patch in `docs/hermes-core-selector-hook.patch` to Hermes core.
