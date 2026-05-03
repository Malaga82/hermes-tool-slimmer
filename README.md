# Hermes Tool Slimmer

Hermes Tool Slimmer reduces repeated tool-schema overhead by selecting the smallest useful tool set for a turn. It builds an indexable corpus from Hermes tool schemas, ranks candidate tools with local BM25 plus explicit boosts, and fails open to the original schema list when anything goes wrong.

## Why

Large Hermes installations can expose dozens of native and MCP tools. A 57-tool schema catalog can serialize to roughly 73 KB, or about 18K approximate prompt tokens using the documented `bytes / 4` estimate. Selecting 8-12 relevant tools for a repository-search turn can reduce that to about 15 KB / 3.7K approximate tokens while keeping configured safety tools hot.

Tool slimming is only a schema-selection optimization. It must not bypass Hermes approval prompts, tool execution controls, provider auth, disabled toolsets, or any runtime safety policy.

## Install

```bash
pip install hermes-tool-slimmer
hermes plugins enable tool-slimmer
hermes tool-slimmer status
```

For a guided setup, see [`docs/quickstart.md`](docs/quickstart.md).

For local development:

```bash
pip install -e ".[dev]"
pytest
```

## Configure

```yaml
plugins:
  enabled:
    - tool-slimmer

tool_slimmer:
  enabled: true
  mode: keyword        # eager | keyword | hybrid | anthropic_tool_search
  top_k: 8             # selected after always_include
  always_include: [terminal, read_file, write_file, patch, search_files]
  never_defer: [terminal, read_file]
  include_mcp_tools: true
  include_native_tools: true
  log_decisions: true
  fail_open: true      # selector errors preserve the original full schema list
  dry_run: false       # true logs/injects diagnostics but does not alter schemas
```

## Commands

```bash
hermes tool-slimmer status
hermes tool-slimmer doctor
hermes tool-slimmer index rebuild --schemas examples/tools.yaml
hermes tool-slimmer index show --top 20
hermes tool-slimmer select "search this repo for MCP registration code" --schemas tools.yaml
hermes tool-slimmer benchmark --prompts examples/prompts.yaml --schemas examples/tools.yaml
hermes tool-slimmer recommend-config
```

Slash commands:

```text
/tool-slimmer status
/tool-slimmer select search this repo for MCP registration code
/tool-slimmer dry-run on
/tool-slimmer dry-run off
```

## Provider behavior

| Provider path | Behavior |
|---|---|
| Anthropic native | Tool Search/defer loading if `mode: anthropic_tool_search` and Hermes core supports the required request serialization/headers. |
| Bedrock/Vertex/Azure Anthropic | Attempt only when the Hermes provider stack supports the Anthropic Tool Search path for that provider/model. |
| OpenRouter/OpenAI/local | Fall back to deterministic keyword selection, hybrid when implemented, or eager mode according to config; do not send Anthropic-only Tool Search definitions. |

## Integration status

The standalone plugin registers diagnostics tools, slash commands, CLI commands, a dry-run `pre_llm_call` diagnostic hook, and a `select_tool_schemas` callback when Hermes core supports it.

Supported/target core surfaces:

- `ctx.register_tool_schema_selector(callback)`
- `ctx.register_schema_selector(callback)`
- `ctx.register_hook("select_tool_schemas", callback)`

If none exists, the plugin does not monkeypatch provider internals. It remains useful for dry-run diagnostics, benchmarking, and configuration recommendations until Hermes core exposes a selector hook. See `docs/hermes-core-selector-hook.patch` for a minimal upstreamable Hermes core patch artifact based on current source inspection.

## Safety model

- `always_include` tools are selected first when present and not already disabled by Hermes.
- `top_k` applies after `always_include`.
- `disabled_tools`, `disabled_toolsets`, `include_mcp_tools`, and `include_native_tools` are respected before ranking.
- `fail_open: true` sends the original schema list on selector errors.
- `dry_run: true` logs decisions and returns `None` to preserve original behavior.
- Anthropic Tool Search helpers never defer every tool.


## Public release contents

- [`docs/quickstart.md`](docs/quickstart.md): install, dry-run, and activation walkthrough.
- [`docs/hermes-core-integration.md`](docs/hermes-core-integration.md): required Hermes core selector hook contract.
- [`docs/hermes-core-selector-hook.patch`](docs/hermes-core-selector-hook.patch): minimal upstreamable Hermes core patch artifact.
- [`docs/anthropic-tool-search.md`](docs/anthropic-tool-search.md): provider capability notes for Anthropic Tool Search.
- [`docs/troubleshooting.md`](docs/troubleshooting.md): common operational issues.
- [`examples/`](examples/): sample config, prompts, schemas, and expected output.

## Release validation

This repository is release-ready only when these checks pass:

```bash
ruff check .
mypy src tests
python -m compileall -q src tests
pytest -q
python -m build
```

When changing the Hermes core patch, also run the validation steps in [`docs/release-checklist.md`](docs/release-checklist.md).
